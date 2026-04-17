# -*- coding: utf-8 -*-
"""Tests for the DashScope-based MCP-Bench synthesis pipeline."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, TestCase

from laplace.mcpbench_dataset.synthesis._server_config import MCPBenchCommandSource
from laplace.mcpbench_dataset.synthesis.benchmark_generator import (
    BenchmarkTaskGenerator,
)
from laplace.mcpbench_dataset.synthesis.generate_benchmark_tasks import (
    _filter_combinations_payload,
    _load_server_whitelist,
)
from laplace.mcpbench_dataset.synthesis.task_synthesis import TaskSynthesizer


class _FakeLLMProvider:
    """Minimal fake LLM provider for synthesis tests."""

    def __init__(self, responses: list[str]) -> None:
        """Initialize fake responses.

        Args:
            responses (`list[str]`):
                Ordered response list consumed by each completion call.
        """
        self.responses = list(responses)

    async def get_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
    ) -> str:
        """Return the next prepared fake response.

        Args:
            system_prompt (`str`):
                Unused fake system prompt.
            user_prompt (`str`):
                Unused fake user prompt.
            max_tokens (`int`):
                Unused fake token limit.

        Returns:
            `str`:
                Next fake response.
        """
        del system_prompt, user_prompt, max_tokens
        return self.responses.pop(0)

    @staticmethod
    def clean_and_parse_json(raw_json: str) -> dict:
        """Parse fake JSON payload.

        Args:
            raw_json (`str`):
                Raw JSON string.

        Returns:
            `dict`:
                Parsed JSON object.
        """
        return json.loads(raw_json)


class TaskSynthesizerTest(IsolatedAsyncioTestCase):
    """Test task synthesis flow with a fake LLM provider."""

    async def test_generate_tasks_accepts_quality_checked_task(self) -> None:
        """Task generation should keep one accepted task."""
        provider = _FakeLLMProvider(
            responses=[
                json.dumps(
                    {
                        "task_id": "task_000",
                        "task_description": "Use Wikipedia to compare two cities over the past 7 days.",
                        "dependency_analysis": "Search results determine the detail lookup sequence.",
                    },
                ),
                "I am comparing two cities and I need concrete supporting facts and numbers.",
                json.dumps(
                    {
                        "solvability_score": 9,
                        "utility_score": 7,
                        "solvability_feedback": "Tool coverage is sufficient.",
                        "utility_feedback": "Useful comparison task.",
                    },
                ),
            ],
        )
        synthesizer = TaskSynthesizer(llm_provider=provider)
        tools = {
            "Wikipedia:search": {
                "server": "Wikipedia",
                "description": "Search encyclopedia entries.",
                "input_schema": {"type": "object"},
            },
        }

        tasks = await synthesizer.generate_tasks(
            tools=tools,
            server_name="Wikipedia",
            num_tasks=1,
        )

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["task_id"], "wikipedia_000")
        self.assertIn("fuzzy_description", tasks[0])


class MCPBenchCommandSourceTest(TestCase):
    """Test loading MCP-Bench command and benchmark configs."""

    def test_load_problematic_tools_from_yaml(self) -> None:
        """Problematic tools should be parsed from the YAML block."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            commands_file = temp_path / "commands.json"
            commands_file.write_text("{}", encoding="utf-8")
            api_key_file = temp_path / "api_key"
            api_key_file.write_text("", encoding="utf-8")
            config_file = temp_path / "benchmark_config.yaml"
            config_file.write_text(
                "execution:\n  problematic_tools:\n    - \"A:bad_tool\"\n    - \"B:other_bad_tool\"\nbenchmark:\n  filter_problematic_tools: true\n",
                encoding="utf-8",
            )

            source = MCPBenchCommandSource(
                commands_json_path=str(commands_file),
                api_key_path=str(api_key_file),
                problematic_tools_path=str(config_file),
            )

            self.assertEqual(
                source.load_problematic_tools(),
                ["A:bad_tool", "B:other_bad_tool"],
            )


class BenchmarkTaskGeneratorFormatTest(TestCase):
    """Test runner-format conversion without network calls."""

    def test_convert_single_to_runner_format(self) -> None:
        """Single-server conversion should emit runner-compatible JSON."""
        generator = BenchmarkTaskGenerator.__new__(BenchmarkTaskGenerator)
        generator.all_server_names = ["Wikipedia", "NASA Data", "Time MCP"]

        results = {
            "generation_info": {
                "total_servers": 1,
                "processed_servers": 1,
                "successful_servers": 1,
                "failed_servers": 0,
                "generation_model": "qwen-plus",
                "tasks_per_server": 1,
                "status": "completed",
            },
            "server_tasks": [
                {
                    "server_name": "Wikipedia",
                    "generation_status": "success",
                    "tasks": [
                        {
                            "task_id": "wikipedia_000",
                            "task_description": "Detailed task.",
                            "fuzzy_description": "Fuzzy task.",
                            "dependency_analysis": "Dependency chain.",
                        },
                    ],
                },
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "runner.json"
            generator.convert_single_to_runner_format(results, str(output_file))
            saved = json.loads(output_file.read_text(encoding="utf-8"))

        self.assertEqual(saved["total_tasks"], 1)
        self.assertEqual(saved["server_tasks"][0]["servers"], ["Wikipedia"])
        self.assertEqual(
            saved["server_tasks"][0]["tasks"][0]["task_id"],
            "wikipedia_000",
        )


class SynthesisCliWhitelistHelperTest(TestCase):
    """Test whitelist helpers used by synthesis CLI."""

    def test_load_server_whitelist_from_json_and_text(self) -> None:
        """Whitelist loader should support both JSON and plain text formats."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            json_file = temp_path / "whitelist.json"
            txt_file = temp_path / "whitelist.txt"

            json_file.write_text(
                json.dumps(
                    {
                        "servers": [
                            "BioMCP",
                            "Paper Search",
                            "BioMCP",
                        ],
                    },
                ),
                encoding="utf-8",
            )
            txt_file.write_text(
                "Wikipedia\nNASA Data\nWikipedia\n",
                encoding="utf-8",
            )

            from_json = _load_server_whitelist(str(json_file))
            from_text = _load_server_whitelist(str(txt_file))

            self.assertEqual(from_json, ["BioMCP", "Paper Search"])
            self.assertEqual(from_text, ["Wikipedia", "NASA Data"])

    def test_filter_combinations_payload_by_whitelist(self) -> None:
        """Combination groups should drop items containing unavailable servers."""
        payload = {
            "mcp_server_combinations": {
                "two_server_combinations": [
                    {"name": "A", "servers": ["BioMCP", "Paper Search"]},
                    {"name": "B", "servers": ["BioMCP", "Wikipedia"]},
                    {"name": "C", "servers": ["Wikipedia", "NASA Data"]},
                ],
            },
        }
        filtered, kept, dropped = _filter_combinations_payload(
            payload=payload,
            allowed_servers={"BioMCP", "Paper Search", "Wikipedia"},
        )

        self.assertEqual(kept, 2)
        self.assertEqual(dropped, 1)
        names = [
            item["name"]
            for item in filtered["mcp_server_combinations"]["two_server_combinations"]
        ]
        self.assertEqual(names, ["A", "B"])


class BenchmarkTaskGeneratorSelfHealTest(IsolatedAsyncioTestCase):
    """Test dynamic exclusion of unhealthy servers during long runs."""

    async def test_mark_unhealthy_on_discovery_failure(self) -> None:
        """Discovery-stage failures should mark servers as runtime unhealthy."""
        generator = BenchmarkTaskGenerator.__new__(BenchmarkTaskGenerator)
        generator.self_heal_on_discovery_failure = True
        generator._runtime_unhealthy_servers = set()

        generator._maybe_mark_unhealthy_from_generation(
            server_names=["BioMCP"],
            generation={
                "status": "failed",
                "failure_stage": "discovery",
                "error": "connection failed",
            },
        )
        self.assertEqual(generator._runtime_unhealthy_servers, {"BioMCP"})

        # Non-discovery failure should not expand unhealthy set.
        generator._maybe_mark_unhealthy_from_generation(
            server_names=["Paper Search"],
            generation={
                "status": "failed",
                "failure_stage": "synthesis",
                "error": "llm parse error",
            },
        )
        self.assertEqual(generator._runtime_unhealthy_servers, {"BioMCP"})

    async def test_multi_generation_skips_unhealthy_servers(self) -> None:
        """Combinations containing unhealthy servers should be skipped."""
        generator = BenchmarkTaskGenerator.__new__(BenchmarkTaskGenerator)
        generator.model_name = "qwen-plus"
        generator.tasks_per_server = 1
        generator.self_heal_on_discovery_failure = True
        generator._runtime_unhealthy_servers = {"BioMCP"}

        # Reuse production summary helper and avoid file writes.
        generator._save_json = lambda data, output_file: None

        combinations = [
            {
                "name": "combo_skip",
                "combination_type": "two",
                "servers": ["BioMCP", "Wikipedia"],
                "description": "should skip",
            },
            {
                "name": "combo_run",
                "combination_type": "two",
                "servers": ["Wikipedia", "NASA Data"],
                "description": "should run",
            },
        ]
        generator._prepare_combinations = lambda combinations_file, start_from: combinations

        async def _fake_process_combination(combination: dict[str, Any]) -> dict[str, Any]:
            return {
                "combination_name": combination.get("name", ""),
                "combination_type": combination.get("combination_type", ""),
                "servers": combination.get("servers", []),
                "description": combination.get("description", ""),
                "generated_tasks": [{"task_id": "ok_001"}],
                "task_count": 1,
                "generation_success": True,
                "failure_stage": "none",
            }

        generator._process_combination = _fake_process_combination

        results = await generator.generate_multi_server_tasks(
            combinations_file="unused.json",
            output_file=None,
        )

        self.assertEqual(len(results["combinations"]), 2)
        self.assertFalse(results["combinations"][0]["generation_success"])
        self.assertTrue(results["combinations"][0]["skipped"])
        self.assertEqual(results["combinations"][0]["skip_reason"], "unhealthy_server")
        self.assertTrue(results["combinations"][1]["generation_success"])