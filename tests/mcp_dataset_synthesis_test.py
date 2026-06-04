# -*- coding: utf-8 -*-
"""Tests for the DashScope-based MCP-Bench synthesis pipeline."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, TestCase

from laplace.mcp_dataset.synthesis._dashscope_provider import (
    DashScopeCompletionProvider,
)
from laplace.mcp_dataset.synthesis._server_config import (
    LaplaceMCPManifestSource,
    MCPBenchCommandSource,
)
from laplace.mcp_dataset.synthesis.prompt2task.benchmark_generator import (
    BenchmarkTaskGenerator,
)
from laplace.mcp_dataset.synthesis.context2sdg.sdg_trace_synthesis import (
    SDGTraceSynthesizer,
    build_server_transition_counts,
    build_server_transition_matrix,
    build_state_transition_counts,
    build_state_transition_matrix,
    build_batch_trace_prompt,
    load_laplace_server_catalog,
)
from laplace.mcp_dataset.synthesis.context2sdg.generate_sdg_traces import (
    _build_prompt_shard_filename,
    _build_trace_shard_filename,
    _build_transition_matrix_payload,
    _load_checkpointed_traces,
    _persist_outputs,
    _resolve_run_paths,
    _write_prompt_to_shard,
    _write_trace_to_shard,
)
from laplace.mcp_dataset.synthesis.prompt2task.generate_benchmark_tasks import (
    _build_run_stamp,
    _filter_combinations_payload,
    _load_server_whitelist,
)
from laplace.mcp_dataset.synthesis.prompt2task.merge_single_runner_format import (
    merge_single_runner_files,
    merge_single_runner_payloads,
    resolve_input_files,
    resolve_merge_sources,
)
from laplace.mcp_dataset.synthesis.prompt2task.merge_multi_runner_format import (
    merge_multi_runner_files,
    resolve_merge_sources as resolve_multi_merge_sources,
)
from laplace.mcp_dataset.synthesis.prompt2task.task_synthesis import (
    TaskQualityEvaluator,
    TaskSynthesizer,
)
from laplace.util.server_config import ServerConfig


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


class SDGTraceSynthesizerTest(IsolatedAsyncioTestCase):
    """Test SDG trace prompt and normalization behavior."""

    def test_build_batch_trace_prompt_lists_servers_and_schema(self) -> None:
        """Batch prompt should expose server names, tools, and schema fields."""
        prompt = build_batch_trace_prompt(
            server_catalog={
                "Google Maps": {
                    "group_description": "Maps and routing tools.",
                    "tool_names": ["maps_geocode", "search_nearby"],
                },
                "Wikipedia": {
                    "group_description": "Knowledge lookup tools.",
                    "tool_names": ["search", "get_page"],
                },
            },
            trace_count=12,
        )

        self.assertIn("Generate 12 diverse execution traces", prompt)
        self.assertIn("Server: Google Maps", prompt)
        self.assertIn("Type:", prompt)
        self.assertIn("maps_geocode", prompt)
        self.assertIn("next_server_labels", prompt)
        self.assertIn("parallel_server_groups", prompt)

    async def test_generate_batch_traces_normalizes_transition_fields(self) -> None:
        """Standalone batch trace generation should backfill summary fields."""
        provider = _FakeLLMProvider(
            responses=[
                json.dumps(
                    {
                        "traces": [
                            {
                                "source_server_scope": ["Wikipedia", "BioMCP"],
                                "user_request": "Please look up a topic and summarize it.",
                                "execution_trace": [
                                    {
                                        "step_index": 1,
                                        "server_name": "Wikipedia",
                                        "server_type": "Academic",
                                        "tool_name": "search",
                                        "tool_category": "Search",
                                        "intent": "Find relevant entities.",
                                        "source_nodes": ["user_request"],
                                        "target_node": "search_hits",
                                        "depends_on": [],
                                    },
                                    {
                                        "step_index": 2,
                                        "server_name": "Wikipedia",
                                        "server_type": "Academic",
                                        "tool_name": "get_page",
                                        "tool_category": "Fetch",
                                        "intent": "Read the selected page.",
                                        "source_nodes": ["search_hits"],
                                        "target_node": "page_content",
                                        "depends_on": [1],
                                    },
                                ],
                                "sdg_summary": {
                                    "parallel_server_groups": [["Wikipedia", "BioMCP"]],
                                },
                            },
                        ],
                    },
                ),
            ],
        )
        synthesizer = SDGTraceSynthesizer(llm_provider=provider)
        traces = await synthesizer.generate_batch_traces(
            trace_count=1,
            server_catalog={
                "Wikipedia": {
                    "group_description": "Knowledge lookup tools.",
                    "server_type": "Academic",
                    "tool_names": ["search", "get_page"],
                },
                "BioMCP": {
                    "group_description": "Biomedical lookup tools.",
                    "server_type": "Academic",
                    "tool_names": ["search_bio"],
                },
            },
        )
        trace = traces[0]

        self.assertEqual(trace["trace_id"], "sdg_trace_00000")
        self.assertEqual(trace["source_server_scope"], ["Wikipedia", "BioMCP"])
        self.assertEqual(trace["sdg_summary"]["server_path"], ["Wikipedia", "Wikipedia"])
        self.assertEqual(trace["sdg_summary"]["tool_path"], ["search", "get_page"])
        self.assertEqual(
            trace["sdg_summary"]["state_path"],
            ["Academic::Search", "Academic::Fetch"],
        )
        self.assertEqual(trace["sdg_summary"]["next_server_labels"], ["Wikipedia", "END"])
        self.assertEqual(
            trace["sdg_summary"]["next_state_labels"],
            ["Academic::Fetch", "END"],
        )
        self.assertEqual(
            trace["sdg_summary"]["successor_candidates"],
            ["Wikipedia"],
        )
        self.assertEqual(
            trace["sdg_summary"]["parallel_server_groups"],
            [["Wikipedia", "BioMCP"]],
        )
        self.assertEqual(trace["execution_trace"][0]["source_nodes"], ["user_request"])
        self.assertEqual(trace["execution_trace"][0]["target_node"], "search_hits")
        self.assertEqual(trace["execution_trace"][0]["server_type"], "Academic")
        self.assertEqual(trace["execution_trace"][0]["tool_category"], "Search")
        self.assertEqual(
            trace["sdg_summary"]["inferred_edges"],
            [
                {
                    "source_node": "user_request",
                    "target_node": "search_hits",
                    "source_step_index": None,
                    "target_step_index": 1,
                    "edge_type": "data_dependency",
                },
                {
                    "source_node": "search_hits",
                    "target_node": "page_content",
                    "source_step_index": 1,
                    "target_step_index": 2,
                    "edge_type": "data_dependency",
                },
            ],
        )

    def test_build_batch_trace_prompt_mentions_standalone_batch_requirements(self) -> None:
        """Batch prompt should stand alone without task-conditioned inputs."""
        prompt = build_batch_trace_prompt(
            server_catalog={
                "Google Maps": {
                    "group_description": "Maps tools.",
                    "tool_names": ["maps_geocode", "search_nearby", "get_place_details"],
                },
            },
            trace_count=8,
        )

        self.assertIn("Generate 8 diverse execution traces", prompt)
        self.assertIn("maps_geocode", prompt)
        self.assertIn("tool_category", prompt)
        self.assertIn("parallel_server_groups", prompt)

    def test_load_laplace_server_catalog_uses_repo_default_manifest(self) -> None:
        """Default catalog loading should resolve the repository manifest path."""
        catalog = load_laplace_server_catalog(ready_only=False)

        self.assertTrue(catalog)

    def test_transition_matrix_helpers_build_server_and_state_matrices(self) -> None:
        """Transition helpers should build counts and probabilities from traces."""
        traces = [
            {
                "sdg_summary": {
                    "server_path": ["Wikipedia", "BioMCP", "Wikipedia"],
                    "state_path": [
                        "Academic::Search",
                        "Academic::Fetch",
                        "Academic::Summarize",
                    ],
                },
            },
            {
                "sdg_summary": {
                    "server_path": ["Wikipedia", "BioMCP"],
                    "state_path": ["Academic::Search", "Academic::Fetch"],
                },
            },
        ]

        self.assertEqual(
            build_server_transition_counts(traces),
            {
                "Wikipedia": {"BioMCP": 2},
                "BioMCP": {"Wikipedia": 1},
            },
        )
        self.assertEqual(
            build_state_transition_counts(traces),
            {
                "Academic::Search": {"Academic::Fetch": 2},
                "Academic::Fetch": {"Academic::Summarize": 1},
            },
        )
        self.assertEqual(
            build_server_transition_matrix(traces),
            {
                "Wikipedia": {"BioMCP": 1.0},
                "BioMCP": {"Wikipedia": 1.0},
            },
        )
        self.assertEqual(
            build_state_transition_matrix(traces),
            {
                "Academic::Search": {"Academic::Fetch": 1.0},
                "Academic::Fetch": {"Academic::Summarize": 1.0},
            },
        )

    def test_transition_matrix_payload_helper_builds_combined_json(self) -> None:
        """CLI helper should package both counts and normalized matrices."""
        traces = [
            {
                "sdg_summary": {
                    "server_path": ["Wikipedia", "BioMCP"],
                    "state_path": ["Academic::Search", "Academic::Fetch"],
                },
            },
        ]

        payload = _build_transition_matrix_payload(traces)

        self.assertEqual(payload["trace_count"], 1)
        self.assertEqual(
            payload["server_transition_counts"],
            {"Wikipedia": {"BioMCP": 1}},
        )
        self.assertEqual(
            payload["server_transition_matrix"],
            {"Wikipedia": {"BioMCP": 1.0}},
        )
        self.assertEqual(
            payload["state_transition_counts"],
            {"Academic::Search": {"Academic::Fetch": 1}},
        )
        self.assertEqual(
            payload["state_transition_matrix"],
            {"Academic::Search": {"Academic::Fetch": 1.0}},
        )

    def test_resumable_run_paths_default_to_output_stem_checkpoint(self) -> None:
        """Checkpoint paths should default under the context2sdg module directory."""
        paths = _resolve_run_paths(
            output_path=Path("laplace/mcp_dataset/laplace_sdg_traces.json"),
            checkpoint_dir=None,
        )
        expected_root = (
            Path("d:/Project/agentscope/laplace/mcp_dataset/synthesis/context2sdg")
            if os.name == "nt"
            else Path("/mnt/d/Project/agentscope/laplace/mcp_dataset/synthesis/context2sdg")
        ) / "laplace_sdg_traces_checkpoint"

        self.assertEqual(
            paths["root"],
            expected_root,
        )
        self.assertEqual(
            paths["prompt_dir"],
            expected_root / "prompts",
        )
        self.assertEqual(
            paths["trace_dir"],
            expected_root / "traces",
        )

    def test_build_prompt_shard_filename_is_archive_friendly(self) -> None:
        """Prompt checkpoint shards should encode shard range and run size."""
        self.assertEqual(
            _build_prompt_shard_filename(0, 49, 200),
            "sdg_prompt_shard_00000_to_00049_of_00200.json",
        )

    def test_build_trace_shard_filename_is_archive_friendly(self) -> None:
        """Trace checkpoint shards should encode shard range and run size."""
        self.assertEqual(
            _build_trace_shard_filename(0, 49, 200),
            "sdg_trace_shard_00000_to_00049_of_00200.json",
        )

    def test_prompt_and_trace_shards_store_multiple_records(self) -> None:
        """Checkpoint shards should group multiple prompt and trace records."""
        with tempfile.TemporaryDirectory() as temp_dir:
            prompt_dir = Path(temp_dir) / "prompts"
            trace_dir = Path(temp_dir) / "traces"
            prompt_dir.mkdir(parents=True, exist_ok=True)
            trace_dir.mkdir(parents=True, exist_ok=True)

            _write_prompt_to_shard(prompt_dir, 0, 200, "prompt zero")
            _write_prompt_to_shard(prompt_dir, 1, 200, "prompt one")
            _write_trace_to_shard(trace_dir, 0, 200, {"trace_id": "sdg_trace_00000"})
            _write_trace_to_shard(trace_dir, 1, 200, {"trace_id": "sdg_trace_00001"})

            prompt_shard = json.loads(
                (prompt_dir / "sdg_prompt_shard_00000_to_00049_of_00200.json").read_text(encoding="utf-8"),
            )
            trace_shard = json.loads(
                (trace_dir / "sdg_trace_shard_00000_to_00049_of_00200.json").read_text(encoding="utf-8"),
            )

        self.assertEqual(len(prompt_shard["records"]), 2)
        self.assertEqual(len(trace_shard["records"]), 2)

    def test_load_checkpointed_traces_reads_contiguous_prefix(self) -> None:
        """Resume helper should load only the contiguous completed prefix of traces."""
        with tempfile.TemporaryDirectory() as temp_dir:
            trace_dir = Path(temp_dir)
            (trace_dir / "sdg_trace_shard_00000_to_00004_of_00005.json").write_text(
                json.dumps(
                    {
                        "records": [
                            {"trace_index": 0, "trace": {"trace_id": "sdg_trace_00000"}},
                            {"trace_index": 1, "trace": {"trace_id": "sdg_trace_00001"}},
                            {"trace_index": 3, "trace": {"trace_id": "sdg_trace_00003"}},
                        ],
                    },
                ),
                encoding="utf-8",
            )

            traces = _load_checkpointed_traces(
                trace_dir=trace_dir,
                requested_trace_count=5,
            )

        self.assertEqual(
            traces,
            [
                {"trace_id": "sdg_trace_00000"},
                {"trace_id": "sdg_trace_00001"},
            ],
        )

    def test_persist_outputs_writes_archive_manifest_fields(self) -> None:
        """Manifest should record archive-oriented metadata for paper artifacts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "laplace_sdg_traces.json"
            matrix_path = Path(temp_dir) / "laplace_sdg_transition_matrices.json"
            run_paths = _resolve_run_paths(
                output_path=output_path,
                checkpoint_dir=None,
            )
            run_paths["root"].mkdir(parents=True, exist_ok=True)
            run_paths["prompt_dir"].mkdir(parents=True, exist_ok=True)
            run_paths["trace_dir"].mkdir(parents=True, exist_ok=True)

            _persist_outputs(
                traces=[{"trace_id": "sdg_trace_00000"}],
                requested_trace_count=2,
                output_path=output_path,
                transition_matrix_output=str(matrix_path),
                run_paths=run_paths,
            )

            manifest = json.loads(
                run_paths["manifest"].read_text(encoding="utf-8"),
            )

        self.assertEqual(
            manifest["manifest_schema"],
            "laplace.context2sdg.checkpoint_manifest.v1",
        )
        self.assertEqual(manifest["collection_id"], "laplace_sdg_traces")
        self.assertEqual(manifest["status"], "in_progress")
        self.assertEqual(
            manifest["artifact_paths"]["consolidated_trace_output"],
            str(output_path),
        )
        self.assertEqual(
            manifest["file_naming"]["prompt_file_pattern"],
            "sdg_prompt_shard_{trace_index_start:05d}_to_{trace_index_end:05d}_of_{requested_trace_count:05d}.json",
        )
        self.assertEqual(
            manifest["file_naming"]["trace_file_pattern"],
            "sdg_trace_shard_{trace_index_start:05d}_to_{trace_index_end:05d}_of_{requested_trace_count:05d}.json",
        )
        self.assertEqual(manifest["checkpoint_shard_size"], 50)
        self.assertEqual(
            manifest["completed_trace_ids"],
            ["sdg_trace_00000"],
        )


class TaskQualityEvaluatorTest(IsolatedAsyncioTestCase):
    """Test quality threshold behavior for different tool counts."""

    async def test_single_tool_uses_relaxed_solvability_threshold(self) -> None:
        """Single-tool servers should use a lower solvability threshold."""
        provider = _FakeLLMProvider(
            responses=[
                json.dumps(
                    {
                        "solvability_score": 6,
                        "utility_score": 6,
                        "solvability_feedback": "single-tool task",
                        "utility_feedback": "useful enough",
                    },
                ),
            ],
        )
        evaluator = TaskQualityEvaluator(llm_provider=provider)
        evaluation = await evaluator.evaluate_task_quality(
            task={"task_description": "x"},
            tools={"Call for Papers:get_events": {}},
        )

        self.assertTrue(
            evaluator.meets_quality_threshold(
                evaluation=evaluation,
                tools={"Call for Papers:get_events": {}},
            ),
        )
        self.assertFalse(
            evaluator.meets_quality_threshold(
                evaluation=evaluation,
                tools={
                    "Call for Papers:get_events": {},
                    "Call for Papers:get_event_detail": {},
                },
            ),
        )

    async def test_search_only_toolset_uses_relaxed_solvability_threshold(self) -> None:
        """Search-only toolsets should use a lower solvability threshold."""
        provider = _FakeLLMProvider(
            responses=[
                json.dumps(
                    {
                        "solvability_score": 7,
                        "utility_score": 6,
                        "solvability_feedback": "search-only task",
                        "utility_feedback": "useful enough",
                    },
                ),
            ],
        )
        evaluator = TaskQualityEvaluator(llm_provider=provider)
        tools = {
            "Paper Search:search_arxiv": {},
            "Paper Search:search_pubmed": {},
            "Paper Search:search_semantic": {},
        }
        evaluation = await evaluator.evaluate_task_quality(
            task={"task_description": "x"},
            tools=tools,
        )

        self.assertTrue(
            evaluator.meets_quality_threshold(
                evaluation=evaluation,
                tools=tools,
            ),
        )


class _NeverReturnsModel:
    """Fake model that never returns before the timeout."""

    async def __call__(self, messages: list[dict], max_tokens: int) -> object:
        """Block long enough to trigger timeout in tests.

        Args:
            messages (`list[dict]`):
                Unused message payload.
            max_tokens (`int`):
                Unused token limit.

        Returns:
            `object`:
                Never reached.
        """
        del messages, max_tokens
        await asyncio.sleep(1)
        return object()


class DashScopeCompletionProviderTimeoutTest(IsolatedAsyncioTestCase):
    """Test timeout protection around DashScope completion calls."""

    async def test_get_completion_times_out(self) -> None:
        """Provider should raise TimeoutError when model call exceeds timeout."""
        provider = DashScopeCompletionProvider.__new__(DashScopeCompletionProvider)
        provider.model_name = "qwen-plus"
        provider.request_timeout_seconds = 0.01
        provider.model = _NeverReturnsModel()

        with self.assertRaises(TimeoutError):
            await provider.get_completion(
                system_prompt="system",
                user_prompt="user",
                max_tokens=32,
            )


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


class LaplaceMCPManifestSourceProblematicToolsTest(TestCase):
    """Test that LaplaceMCPManifestSource reads problematic_tools from the manifest."""

    def _make_manifest(self, temp_path: Path) -> Path:
        """Write a minimal manifest fixture with problematic_tools.

        Args:
            temp_path (`Path`):
                Temporary directory for fixture files.

        Returns:
            `Path`:
                Path to the written manifest file.
        """
        manifest = {
            "manifest_version": 1,
            "servers": {
                "Paper Search": {
                    "image": "laplace/paper-search:local",
                    "ready_for_prewarm": True,
                    "server_config": {
                        "container_name": "laplace-paper-search",
                        "image": "laplace/paper-search:local",
                        "transport": "streamable_http",
                        "url": "http://localhost:8831/mcp",
                        "client_name": "laplace-paper-search",
                    },
                    "docker_run_command": [
                        "docker", "run", "-d", "--rm",
                        "--name", "laplace-paper-search",
                        "-p", "8831:8000",
                        "laplace/paper-search:local",
                    ],
                    "tool_names": [
                        "search_arxiv", "download_arxiv", "read_arxiv_paper",
                    ],
                    "problematic_tools": ["download_arxiv", "read_arxiv_paper"],
                },
                "Bibliomantic": {
                    "image": "laplace/bibliomantic:local",
                    "ready_for_prewarm": True,
                    "server_config": {
                        "container_name": "laplace-bibliomantic",
                        "image": "laplace/bibliomantic:local",
                        "transport": "streamable_http",
                        "url": "http://localhost:8801/mcp",
                        "client_name": "laplace-bibliomantic",
                    },
                    "docker_run_command": [
                        "docker", "run", "-d", "--rm",
                        "--name", "laplace-bibliomantic",
                        "-p", "8801:8000",
                        "laplace/bibliomantic:local",
                    ],
                    "tool_names": ["bibliomantic_consultation"],
                },
            },
        }
        manifest_file = temp_path / "laplace_mcp_manifest.json"
        manifest_file.write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        return manifest_file

    def test_load_problematic_tools_from_manifest(self) -> None:
        """load_problematic_tools should return qualified names from manifest."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_file = self._make_manifest(Path(temp_dir))
            source = LaplaceMCPManifestSource(manifest_path=str(manifest_file))
            tools = source.load_problematic_tools()

        self.assertEqual(
            sorted(tools),
            ["Paper Search:download_arxiv", "Paper Search:read_arxiv_paper"],
        )

    def test_load_problematic_tools_empty_when_not_declared(self) -> None:
        """Servers without problematic_tools should contribute no entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = {
                "manifest_version": 1,
                "servers": {
                    "Bibliomantic": {
                        "image": "laplace/bibliomantic:local",
                        "ready_for_prewarm": True,
                        "server_config": {
                            "container_name": "laplace-bibliomantic",
                            "image": "laplace/bibliomantic:local",
                            "transport": "streamable_http",
                            "url": "http://localhost:8801/mcp",
                            "client_name": "laplace-bibliomantic",
                        },
                        "docker_run_command": [
                            "docker", "run", "-d", "--rm",
                            "--name", "laplace-bibliomantic",
                            "-p", "8801:8000",
                            "laplace/bibliomantic:local",
                        ],
                        "tool_names": ["bibliomantic_consultation"],
                    },
                },
            }
            manifest_file = Path(temp_dir) / "laplace_mcp_manifest.json"
            manifest_file.write_text(
                json.dumps(manifest, indent=2), encoding="utf-8"
            )
            source = LaplaceMCPManifestSource(manifest_path=str(manifest_file))
            self.assertEqual(source.load_problematic_tools(), [])


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


class MergeSingleRunnerFormatTest(TestCase):
    """Test merging pre-generated single runner-format payloads."""

    def test_resolve_input_files_with_glob_and_output_exclusion(self) -> None:
        """Glob discovery should find matching files and skip the output target."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            file_a = temp_path / "benchmark_tasks_single_20260420_runner_format.json"
            file_b = temp_path / "benchmark_tasks_single_04231516_runner_format.json"
            output_file = temp_path / "laplace_tasks_single_runner_format.json"
            ignored = temp_path / "benchmark_tasks_multi_runner_format.json"

            file_a.write_text("{}", encoding="utf-8")
            file_b.write_text("{}", encoding="utf-8")
            output_file.write_text("{}", encoding="utf-8")
            ignored.write_text("{}", encoding="utf-8")

            resolved = resolve_input_files(
                glob_pattern="benchmark_tasks_single_*_runner_format.json",
                search_root=str(temp_path),
                output_file=str(output_file),
            )

        self.assertEqual(
            resolved,
            [str(file_b.resolve()), str(file_a.resolve())],
        )

    def test_resolve_merge_sources_includes_existing_output_baseline(self) -> None:
        """Existing merged output should be reused and only new sources appended."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            old_a = temp_path / "old_a.json"
            old_b = temp_path / "old_b.json"
            merged_payload = {
                "generation_info": {
                    "merged_from_files": [str(old_a.resolve()), str(old_b.resolve())],
                },
                "server_tasks": [],
                "total_tasks": 0,
            }
            output_file = temp_path / "laplace_tasks_single_runner_format.json"
            new_file = temp_path / "benchmark_tasks_single_20260424_runner_format.json"
            output_file.write_text(json.dumps(merged_payload), encoding="utf-8")
            new_file.write_text("{}", encoding="utf-8")
            old_a.write_text("{}", encoding="utf-8")
            old_b.write_text("{}", encoding="utf-8")

            input_files, source_files = resolve_merge_sources(
                inputs=[str(old_a)],
                glob_pattern="benchmark_tasks_single_*_runner_format.json",
                search_root=str(temp_path),
                output_file=str(output_file),
            )

        self.assertEqual(input_files[0], str(output_file.resolve()))
        self.assertEqual(input_files[1:], [str(new_file.resolve())])
        self.assertEqual(
            source_files,
            [
                str(old_a.resolve()),
                str(old_b.resolve()),
                str(new_file.resolve()),
            ],
        )

    def test_merge_single_runner_payloads_reindexes_duplicate_task_ids(self) -> None:
        """Merged output should retain all tasks and reindex ids per server."""
        payloads = [
            {
                "generation_info": {
                    "generation_model": "qwen3-max",
                    "runtime_unhealthy_servers": [],
                },
                "server_tasks": [
                    {
                        "server_name": "BioMCP",
                        "servers": ["BioMCP"],
                        "combination_name": "Single Server: BioMCP",
                        "combination_type": "single_server",
                        "tasks": [
                            {
                                "task_id": "biomcp_000",
                                "task_description": "task a",
                            },
                            {
                                "task_id": "biomcp_001",
                                "task_description": "task b",
                            },
                        ],
                    },
                ],
                "total_tasks": 2,
            },
            {
                "generation_info": {
                    "generation_model": "qwen3-max",
                    "runtime_unhealthy_servers": ["Paper Search"],
                },
                "server_tasks": [
                    {
                        "server_name": "BioMCP",
                        "servers": ["BioMCP"],
                        "combination_name": "Single Server: BioMCP",
                        "combination_type": "single_server",
                        "tasks": [
                            {
                                "task_id": "biomcp_000",
                                "task_description": "task c",
                            },
                        ],
                    },
                    {
                        "server_name": "Wikipedia",
                        "servers": ["Wikipedia"],
                        "combination_name": "Single Server: Wikipedia",
                        "combination_type": "single_server",
                        "tasks": [
                            {
                                "task_id": "wikipedia_000",
                                "task_description": "task d",
                            },
                        ],
                    },
                ],
                "total_tasks": 2,
            },
        ]

        merged = merge_single_runner_payloads(
            payloads,
            source_names=["a.json", "b.json"],
        )

        self.assertEqual(merged["total_tasks"], 4)
        self.assertEqual(merged["generation_info"]["successful_servers"], 2)
        self.assertEqual(
            merged["generation_info"]["runtime_unhealthy_servers"],
            ["Paper Search"],
        )
        self.assertEqual(
            [task["task_id"] for task in merged["server_tasks"][0]["tasks"]],
            ["biomcp_000", "biomcp_001", "biomcp_002"],
        )
        self.assertEqual(
            [task["task_id"] for task in merged["server_tasks"][1]["tasks"]],
            ["wikipedia_000"],
        )

    def test_merge_single_runner_files_writes_output(self) -> None:
        """File-based merge should save a valid runner-format JSON."""
        payload = {
            "generation_info": {
                "generation_model": "qwen3-max",
                "runtime_unhealthy_servers": [],
            },
            "server_tasks": [
                {
                    "server_name": "Wikipedia",
                    "servers": ["Wikipedia"],
                    "combination_name": "Single Server: Wikipedia",
                    "combination_type": "single_server",
                    "tasks": [
                        {
                            "task_id": "wikipedia_000",
                            "task_description": "task a",
                        },
                    ],
                },
            ],
            "total_tasks": 1,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_a = temp_path / "a.json"
            input_b = temp_path / "b.json"
            output_file = temp_path / "merged.json"
            input_a.write_text(json.dumps(payload), encoding="utf-8")
            input_b.write_text(json.dumps(payload), encoding="utf-8")

            saved = merge_single_runner_files(
                input_files=[str(input_a), str(input_b)],
                output_file=str(output_file),
            )
            loaded = json.loads(output_file.read_text(encoding="utf-8"))

        self.assertEqual(saved["total_tasks"], 2)
        self.assertEqual(loaded["total_tasks"], 2)
        self.assertEqual(
            [task["task_id"] for task in loaded["server_tasks"][0]["tasks"]],
            ["wikipedia_000", "wikipedia_001"],
        )

    def test_resolve_input_files_keeps_explicit_then_appends_glob(self) -> None:
        """Explicit inputs should retain order before unique glob matches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            explicit = temp_path / "manual.json"
            globbed = temp_path / "benchmark_tasks_single_20260420_runner_format.json"

            explicit.write_text("{}", encoding="utf-8")
            globbed.write_text("{}", encoding="utf-8")

            resolved = resolve_input_files(
                inputs=[str(explicit)],
                glob_pattern="benchmark_tasks_single_*_runner_format.json",
                search_root=str(temp_path),
            )

        self.assertEqual(
            resolved,
            [str(explicit.resolve()), str(globbed.resolve())],
        )

    def test_merge_multi_runner_files_reindexes_duplicate_task_ids(self) -> None:
        """Multi-server merge should also reindex duplicate task ids."""
        payload = {
            "generation_info": {
                "generation_model": "qwen3-max",
                "runtime_unhealthy_servers": [],
            },
            "server_tasks": [
                {
                    "server_name": "Google Maps+Weather Data",
                    "servers": ["Google Maps", "Weather Data"],
                    "combination_name": "Maps + Weather",
                    "combination_type": "multi_server",
                    "tasks": [
                        {
                            "task_id": "maps_weather_000",
                            "task_description": "task a",
                        },
                    ],
                },
            ],
            "total_tasks": 1,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_a = temp_path / "benchmark_tasks_multi_20260420_runner_format.json"
            input_b = temp_path / "benchmark_tasks_multi_20260421_runner_format.json"
            output_file = temp_path / "laplace_tasks_multi_runner_format.json"
            input_a.write_text(json.dumps(payload), encoding="utf-8")
            input_b.write_text(json.dumps(payload), encoding="utf-8")

            saved = merge_multi_runner_files(
                input_files=[str(input_a), str(input_b)],
                output_file=str(output_file),
                source_names=[str(input_a.resolve()), str(input_b.resolve())],
            )
            loaded = json.loads(output_file.read_text(encoding="utf-8"))

        self.assertEqual(saved["total_tasks"], 2)
        self.assertEqual(loaded["generation_info"]["source_file_count"], 2)
        self.assertEqual(
            [task["task_id"] for task in loaded["server_tasks"][0]["tasks"]],
            ["google_maps_weather_data_000", "google_maps_weather_data_001"],
        )

    def test_resolve_multi_merge_sources_includes_existing_output_baseline(self) -> None:
        """Multi merge should reuse existing merged output and append new raw files."""
        merged_payload = {
            "generation_info": {
                "merged_from_files": ["/tmp/multi_old.json"],
            },
            "server_tasks": [],
            "total_tasks": 0,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            output_file = temp_path / "laplace_tasks_multi_runner_format.json"
            new_file = temp_path / "benchmark_tasks_multi_20260424_runner_format.json"
            output_file.write_text(json.dumps(merged_payload), encoding="utf-8")
            new_file.write_text("{}", encoding="utf-8")

            input_files, source_files = resolve_multi_merge_sources(
                glob_pattern="benchmark_tasks_multi_*_runner_format.json",
                search_root=str(temp_path),
                output_file=str(output_file),
            )

        self.assertEqual(input_files[0], str(output_file.resolve()))
        self.assertEqual(input_files[1:], [str(new_file.resolve())])
        self.assertEqual(
            source_files,
            [str(Path("/tmp/multi_old.json").resolve()), str(new_file.resolve())],
        )


class SynthesisCliWhitelistHelperTest(TestCase):
    """Test whitelist helpers used by synthesis CLI."""

    def test_build_run_stamp_uses_month_day_hour_minute(self) -> None:
        """Run stamp should include month/day/hour/minute to avoid same-day overwrite."""
        stamp = _build_run_stamp(datetime(2026, 4, 23, 16, 45))

        self.assertEqual(stamp, "04231645")

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


class BenchmarkTaskGeneratorDiscoveryConfigTest(TestCase):
    """Test discovery config preparation for HTTP manifest servers."""

    def test_prepare_discovery_configs_switches_http_to_managed_mode(self) -> None:
        """HTTP servers should be converted from pre-warmed to spawned mode."""
        generator = BenchmarkTaskGenerator.__new__(BenchmarkTaskGenerator)
        configs = [
            ServerConfig(
                name="Milvus MCP",
                command="docker",
                args=["run"],
                env={},
                cwd=None,
                transport="streamable_http",
                port=8832,
                endpoint="/mcp",
                pre_warmed=True,
            ),
            ServerConfig(
                name="Local StdIO",
                command="python",
                args=["server.py"],
                env={},
                cwd=None,
                transport="stdio",
                port=None,
                endpoint="/mcp",
                pre_warmed=False,
            ),
        ]

        prepared = generator._prepare_discovery_configs(configs)

        self.assertFalse(prepared[0].pre_warmed)
        self.assertEqual(prepared[0].args, ["run"])
        self.assertIsNot(prepared[0], configs[0])
        self.assertFalse(prepared[1].pre_warmed)
        self.assertIs(prepared[1], configs[1])
