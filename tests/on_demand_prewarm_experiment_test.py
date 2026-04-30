# -*- coding: utf-8 -*-
"""Tests for the prompt-prewarm experiment runner."""

import importlib.util
import json
import tempfile
import time
from unittest.mock import AsyncMock, patch
from pathlib import Path
from unittest import TestCase

from agentscope.mcp._mcp_server_helper import _DockerMCPServerConfig


def _load_module():
    """Load the experiment runner module from the example directory."""
    module_path = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "agent"
        / "on_demand_meta_planner_agent"
        / "run_prewarm_experiment.py"
    )
    spec = importlib.util.spec_from_file_location(
        "on_demand_prewarm_experiment",
        module_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OnDemandPrewarmExperimentTest(TestCase):
    """Test pure helpers in the prompt-prewarm experiment runner."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the experiment runner once."""
        cls.module = _load_module()

    def test_sample_unique_server_tasks_keeps_servers_distinct(self) -> None:
        """Sampling should choose at most one task per server."""
        grouped_tasks = {
            "Alpha": [
                {"server_name": "Alpha", "task_id": "alpha_0", "fuzzy_description": "a"},
                {"server_name": "Alpha", "task_id": "alpha_1", "fuzzy_description": "b"},
            ],
            "Beta": [
                {"server_name": "Beta", "task_id": "beta_0", "fuzzy_description": "c"},
            ],
            "Gamma": [
                {"server_name": "Gamma", "task_id": "gamma_0", "fuzzy_description": "d"},
            ],
        }

        sampled = self.module._sample_unique_server_tasks(
            grouped_tasks=grouped_tasks,
            sample_size=2,
            seed=7,
        )

        self.assertEqual(len(sampled), 2)
        self.assertEqual(
            len({task["server_name"] for task in sampled}),
            2,
        )

    def test_collect_target_metrics_uses_registration_aliases(self) -> None:
        """Target metrics should match server name and client name aliases."""
        registration = self.module._DockerMCPRegistrationConfig(
            server_config=_DockerMCPServerConfig(
                container_name="laplace-weather-data",
                image="laplace/weather-data:local",
                transport="streamable_http",
                url="http://localhost:8899/mcp",
                client_name="laplace-weather-data",
            ),
            docker_run_command=["docker", "run", "laplace/weather-data:local"],
            group_name="laplace_weather_data",
            group_description="Weather data tools.",
            server_name="Weather Data",
        )
        events = [
            {
                "step": "prewarm_router_matched",
                "candidates": "Weather Data",
                "effective_route_method": "semantic",
            },
            {
                "step": "prewarm_candidate_finished",
                "candidate": "laplace-weather-data",
                "effective_route_method": "semantic",
                "effective": True,
                "duration_ms": 123.4,
            },
        ]

        metrics = self.module._collect_target_metrics(events, registration)

        self.assertTrue(metrics["target_router_matched"])
        self.assertTrue(metrics["target_effective_prewarm"])
        self.assertEqual(metrics["target_effective_route_method"], "semantic")
        self.assertEqual(metrics["target_prewarm_duration_ms"], 123.4)

    def test_build_mode_rows_computes_rates_and_waits(self) -> None:
        """Mode-level aggregation should summarize waits and effectiveness."""
        records = [
            {
                "experiment_mode": "keyword",
                "summary": {
                    "target_router_matched": True,
                    "target_effective_prewarm": True,
                    "target_effective_route_method": "keyword",
                    "wait_for_mcp_ready_after_activation_ms": 10.0,
                    "startup_mode": "running",
                },
            },
            {
                "experiment_mode": "keyword",
                "summary": {
                    "target_router_matched": True,
                    "target_effective_prewarm": False,
                    "wait_for_mcp_ready_after_activation_ms": 30.0,
                    "startup_mode": "cold",
                },
            },
            {
                "experiment_mode": "none",
                "summary": {
                    "target_router_matched": False,
                    "target_effective_prewarm": False,
                    "wait_for_mcp_ready_after_activation_ms": 50.0,
                    "startup_mode": "cold",
                },
            },
        ]

        rows = self.module._build_mode_rows(records)
        self.assertEqual(rows[0][0], "No Prewarm")
        self.assertEqual(rows[1][0], "Keyword Prewarm")
        self.assertEqual(rows[1][2], "2")
        self.assertEqual(rows[1][3], "100.0%")
        self.assertEqual(rows[1][4], "1")
        self.assertEqual(rows[1][5], "50.0%")
        self.assertEqual(rows[1][6], "L1:1")
        self.assertEqual(rows[1][7], "20.000")

    def test_completed_trial_keys_extracts_resume_index(self) -> None:
        """Resume index should use task, mode, and repeat as the stable key."""
        records = [
            {
                "trial_key": "weather_001::hybrid::3",
                "task_id": "weather_001",
                "experiment_mode": "hybrid",
                "repeat_index": 3,
                "trial_status": "completed",
            },
            {
                "trial_key": "weather_001::keyword::1",
                "task_id": "weather_001",
                "experiment_mode": "keyword",
                "repeat_index": 1,
                "trial_status": "started",
            },
        ]

        completed = self.module._completed_trial_keys(records)

        self.assertEqual(
            completed,
            {
                "weather_001::hybrid::3",
            },
        )

    def test_completed_trial_records_uses_latest_terminal_status(self) -> None:
        """Only latest completed trial records should feed report aggregation."""
        records = [
            {
                "trial_key": "weather_001::hybrid::1",
                "task_id": "weather_001",
                "experiment_mode": "hybrid",
                "repeat_index": 1,
                "trial_status": "started",
            },
            {
                "trial_key": "weather_001::hybrid::1",
                "task_id": "weather_001",
                "experiment_mode": "hybrid",
                "repeat_index": 1,
                "trial_status": "completed",
                "summary": {
                    "wait_for_mcp_ready_after_activation_ms": 12.0,
                },
            },
            {
                "trial_key": "weather_002::semantic::1",
                "task_id": "weather_002",
                "experiment_mode": "semantic",
                "repeat_index": 1,
                "trial_status": "failed",
            },
        ]

        completed = self.module._completed_trial_records(records)

        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0]["trial_key"], "weather_001::hybrid::1")

    def test_build_report_includes_resume_progress_section(self) -> None:
        """Report should expose completed, remaining, and skipped resumed counts."""
        report = self.module._build_report(
            records=[
                {
                    "trial_key": "weather_001::keyword::1",
                    "task_id": "weather_001",
                    "server_name": "Weather Data",
                    "experiment_mode": "keyword",
                    "trial_status": "completed",
                    "summary": {
                        "target_router_matched": True,
                        "target_effective_prewarm": True,
                        "target_effective_route_method": "semantic",
                        "wait_for_mcp_ready_after_activation_ms": 10.0,
                        "startup_mode": "running",
                    },
                },
            ],
            sampled_tasks=[
                {
                    "server_name": "Weather Data",
                    "task_id": "weather_001",
                    "fuzzy_description": "get forecast",
                },
            ],
            task_file=Path("tasks.json"),
            repeats=20,
            seed=42,
            completed_trial_count=1,
            total_trial_count=4,
            skipped_resumed_trial_count=2,
        )

        self.assertIn("## Resume Progress", report)
        self.assertIn("Completed Trials", report)
        self.assertIn("Remaining Trials", report)
        self.assertIn("Skipped Resumed Trials", report)
        self.assertIn("| 1 | 3 | 2 |", report)
        self.assertIn("Effective Route Breakdown", report)
        self.assertIn("L2:1", report)

    def test_run_single_trial_continues_after_speculative_candidate_failure(self) -> None:
        """One failed speculative candidate should not abort the whole trial."""
        task = {
            "server_name": "OpenAPI Explorer",
            "task_id": "openapi_explorer_001",
            "fuzzy_description": (
                "library documentation stripe openapi create payment intent"
            ),
        }
        registration = self.module._DockerMCPRegistrationConfig(
            server_config=_DockerMCPServerConfig(
                container_name="laplace-openapi-explorer",
                image="laplace/openapi-explorer:local",
                transport="streamable_http",
                url="http://localhost:8816/mcp",
                client_name="laplace-openapi-explorer",
            ),
            docker_run_command=["docker", "run", "laplace/openapi-explorer:local"],
            group_name="laplace_openapi_explorer",
            group_description="OpenAPI explorer tools.",
            server_name="OpenAPI Explorer",
        )

        async def _failing_executor(candidate: str) -> object:
            if candidate == "laplace-context7":
                raise RuntimeError("context7 timed out")

            class _SpeculativeClient:
                startup_mode = "cold"

            return _SpeculativeClient()

        class _FormalClient:
            startup_mode = "cold"

        with patch.object(self.module, "_cleanup_experiment_containers", AsyncMock()), patch.object(
            self.module,
            "_ensure_local_docker_mcp_server",
            AsyncMock(return_value=_FormalClient()),
        ):
            record = __import__("asyncio").run(
                self.module._run_single_trial(
                    task=task,
                    mode="keyword",
                    repeat_index=1,
                    registration=registration,
                    registrations=[registration],
                    speculative_executor=_failing_executor,
                ),
            )

        steps = [event["step"] for event in record["events"]]
        failed_candidates = [
            event["candidate"]
            for event in record["events"]
            if event["step"] == "prewarm_candidate_failed"
        ]

        self.assertIn("prewarm_candidate_failed", steps)
        self.assertIn("tool_group_activation_requested", steps)
        self.assertIn("mcp_server_ready", steps)
        self.assertIn("laplace-context7", failed_candidates)
        self.assertEqual(record["trial_status"], "completed")

    def test_load_or_initialize_plan_reuses_existing_sample(self) -> None:
        """Resume plan loading should preserve the original sampled tasks."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plan_path = Path(temp_dir) / "experiment.plan.json"
            task_file = Path(temp_dir) / "tasks.json"
            task_file.write_text(
                json.dumps(
                    {
                        "server_tasks": [
                            {
                                "server_name": "Alpha",
                                "tasks": [
                                    {
                                        "task_id": "alpha_0",
                                        "task_description": "Alpha task",
                                        "fuzzy_description": "do alpha",
                                    },
                                ],
                            },
                            {
                                "server_name": "Beta",
                                "tasks": [
                                    {
                                        "task_id": "beta_0",
                                        "task_description": "Beta task",
                                        "fuzzy_description": "do beta",
                                    },
                                ],
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            created = self.module._load_or_initialize_plan(
                plan_path=plan_path,
                task_file=task_file,
                sample_size=2,
                repeats=20,
                seed=11,
                modes=["none", "keyword"],
                manifest_path=None,
                resume=True,
            )
            loaded = self.module._load_or_initialize_plan(
                plan_path=plan_path,
                task_file=task_file,
                sample_size=2,
                repeats=20,
                seed=11,
                modes=["none", "keyword"],
                manifest_path=None,
                resume=True,
            )

        self.assertEqual(created["sampled_tasks"], loaded["sampled_tasks"])

    def test_load_or_initialize_plan_rejects_incompatible_resume_args(self) -> None:
        """Resume should fail fast when the previous plan uses other args."""
        with tempfile.TemporaryDirectory() as temp_dir:
            plan_path = Path(temp_dir) / "experiment.plan.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "task_file": str((Path(temp_dir) / "tasks.json").resolve()),
                        "manifest_path": None,
                        "sample_size": 5,
                        "repeats": 20,
                        "seed": 42,
                        "modes": ["none", "keyword"],
                        "sampled_tasks": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                self.module._load_or_initialize_plan(
                    plan_path=plan_path,
                    task_file=Path(temp_dir) / "tasks.json",
                    sample_size=5,
                    repeats=20,
                    seed=42,
                    modes=["none", "hybrid"],
                    manifest_path=None,
                    resume=True,
                )

    def test_default_output_paths_use_daily_zero_index_when_free(self) -> None:
        """Default outputs should start from mmdd_0 when no files exist."""
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            self.module.time,
            "strftime",
            return_value="0428",
        ), patch.object(
            self.module.time,
            "localtime",
            return_value=time.localtime(),
        ):
            log_path, report_path, plan_path = self.module._default_output_paths(
                Path(temp_dir),
            )

        self.assertEqual(log_path.name, "prewarm_experiment_results_0428_0.jsonl")
        self.assertEqual(report_path.name, "prewarm_experiment_report_0428_0.md")
        self.assertEqual(
            plan_path.name,
            "prewarm_experiment_results_0428_0.plan.json",
        )

    def test_default_output_paths_advance_index_after_existing_outputs(self) -> None:
        """Default outputs should use the next daily index when earlier files exist."""
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            self.module.time,
            "strftime",
            return_value="0428",
        ), patch.object(
            self.module.time,
            "localtime",
            return_value=time.localtime(),
        ):
            base_dir = Path(temp_dir)
            (base_dir / "prewarm_experiment_results_0428_0.jsonl").write_text(
                "",
                encoding="utf-8",
            )
            (base_dir / "prewarm_experiment_report_0428_0.md").write_text(
                "",
                encoding="utf-8",
            )
            (base_dir / "prewarm_experiment_results_0428_0.plan.json").write_text(
                "{}",
                encoding="utf-8",
            )

            log_path, report_path, plan_path = self.module._default_output_paths(
                base_dir,
            )

        self.assertEqual(log_path.name, "prewarm_experiment_results_0428_1.jsonl")
        self.assertEqual(report_path.name, "prewarm_experiment_report_0428_1.md")
        self.assertEqual(
            plan_path.name,
            "prewarm_experiment_results_0428_1.plan.json",
        )