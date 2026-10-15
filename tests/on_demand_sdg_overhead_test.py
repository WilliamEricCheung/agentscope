"""Tests for the repeated SDG overhead measurement script."""

import importlib.util
import math
from datetime import datetime
from pathlib import Path
import time
from unittest import TestCase


def _load_module():
    """Load the SDG measurement script from the example directory."""
    module_path = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "agent"
        / "on_demand_meta_planner_agent"
        / "result_sdg"
        / "measure_sdg_overhead.py"
    )
    spec = importlib.util.spec_from_file_location(
        "on_demand_sdg_overhead",
        module_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OnDemandSDGOverheadTest(TestCase):
    """Test offline parsing and SDG warmup accounting."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the measurement script once."""
        cls.module = _load_module()

    def test_parse_docker_resource_units(self) -> None:
        """Docker resource values should convert to core and GiB units."""
        self.assertEqual(self.module._parse_cpu_cores("250.0%"), 2.5)
        self.assertTrue(
            math.isclose(
                self.module._parse_memory_gib("512MiB / 1GiB"),
                0.5,
            ),
        )
        with self.assertRaises(ValueError):
            self.module._parse_memory_gib("1XB / 2GiB")

    def test_normalize_string_stream_interval(self) -> None:
        """Tool-call string values should normalize to the configured integer."""
        import config

        self.assertEqual(
            config.normalize_stream_text_speculation_interval_tokens("20"),
            20,
        )
        with self.assertRaises(ValueError):
            config.normalize_stream_text_speculation_interval_tokens("invalid")

    def test_c2_only_mode_disables_prompt_prewarm(self) -> None:
        """C2-only mode should enable predictive but disable C1 prewarming."""
        import config

        self.module._runner._set_runtime_config(
            self.module._runner._MODE_C2_ONLY,
            20,
        )
        self.assertFalse(config.ON_DEMAND_PREWARM_ENABLED)
        self.assertTrue(config.ON_DEMAND_PREDICTIVE_PREWARM_ENABLED)
        self.module._runner._set_runtime_config(
            self.module._runner._MODE_C1_C2,
            20,
        )

    def test_event_epoch_uses_precise_worker_start(self) -> None:
        """Worker event time conversion should retain sub-second start precision."""
        self.assertEqual(
            self.module._event_epoch(
                "2026-10-09 18:31:50",
                1000,
                1791541910.898,
            ),
            1791541911.898,
        )

    def test_classify_used_and_discarded_predictive_warmups(self) -> None:
        """Only a completed warmup used by a non-cold request counts as a hit."""
        module = self.module
        started = datetime.now().replace(microsecond=0)
        base = time.mktime(started.timetuple())
        timestamp_ms = lambda offset: (base + offset) * 1000
        record = {
            "started_at": started.strftime("%Y-%m-%d %H:%M:%S"),
            "prewarm_controller_telemetry": {
                "events": [
                    {
                        "event": "predict_candidates",
                        "stage": "predictive",
                        "status": "completed",
                        "candidate_count": 1,
                        "ts": timestamp_ms(0.05),
                    },
                    {
                        "event": "prewarm_schedule",
                        "stage": "predictive",
                        "candidate": "Playwright",
                        "status": "accepted",
                        "ts": timestamp_ms(0.1),
                    },
                    {
                        "event": "prewarm_executor",
                        "stage": "predictive",
                        "candidate": "Playwright",
                        "status": "started",
                        "ts": timestamp_ms(0.2),
                    },
                    {
                        "event": "prewarm_executor",
                        "stage": "predictive",
                        "candidate": "Playwright",
                        "status": "completed",
                        "effective": True,
                        "startup_mode": "cold",
                        "ts": timestamp_ms(0.5),
                    },
                    {
                        "event": "predict_candidates",
                        "stage": "predictive",
                        "status": "completed",
                        "candidate_count": 1,
                        "ts": timestamp_ms(2.0),
                    },
                    {
                        "event": "prewarm_schedule",
                        "stage": "predictive",
                        "candidate": "GitHub",
                        "status": "accepted",
                        "ts": timestamp_ms(2.05),
                    },
                    {
                        "event": "prewarm_executor",
                        "stage": "predictive",
                        "candidate": "GitHub",
                        "status": "started",
                        "ts": timestamp_ms(2.1),
                    },
                    {
                        "event": "prewarm_executor",
                        "stage": "predictive",
                        "candidate": "GitHub",
                        "status": "completed",
                        "effective": True,
                        "startup_mode": "cold",
                        "ts": timestamp_ms(2.5),
                    },
                ],
            },
            "events": [
                {
                    "step": "tool_group_activation_requested",
                    "group_name": "browser_tools",
                    "elapsed_ms": 1000,
                },
                {
                    "step": "mcp_server_ready",
                    "group_name": "browser_tools",
                    "startup_mode": "running",
                    "elapsed_ms": 1200,
                },
                {
                    "step": "tool_group_activation_requested",
                    "group_name": "github_tools",
                    "elapsed_ms": 3000,
                },
                {
                    "step": "mcp_server_ready",
                    "group_name": "github_tools",
                    "startup_mode": "cold",
                    "elapsed_ms": 4000,
                },
            ],
        }
        finished_at = datetime.fromtimestamp(base + 10).strftime(
            "%Y-%m-%d %H:%M:%S",
        )
        warmups, demands, _ = module._read_predictive_events(
            [record],
            1,
            record["started_at"],
            finished_at,
            candidate_to_group={
                "Playwright": "browser_tools",
                "GitHub": "github_tools",
            },
        )
        by_target = {item["target"]: item for item in warmups}

        self.assertTrue(by_target["browser_tools"]["later_demand_use"])
        self.assertEqual(
            by_target["github_tools"]["discard_timestamp_basis"],
            "cold_demand_detected",
        )
        self.assertLess(
            by_target["github_tools"]["discard_timestamp_unix_s"],
            base + 10,
        )
        self.assertEqual(sum(item["prefetch_hit"] for item in demands), 1)

        samples = [
            {
                "timestamp_unix_s": base + second,
                "containers": {
                    "github_tools": {
                        "cpu_cores": 0.5,
                        "memory_gib": 2.0,
                    },
                },
            }
            for second in range(0, 11)
        ]
        module._integrate_discarded_resources(
            warmups,
            samples,
            {"github_tools": "github-container"},
        )
        self.assertTrue(
            math.isclose(
                by_target["github_tools"]["cpu_seconds"],
                0.45,
                abs_tol=1e-6,
            ),
        )
        self.assertTrue(
            math.isclose(
                by_target["github_tools"]["memory_gib_seconds"],
                1.8,
                abs_tol=1e-6,
            ),
        )

    def test_excludes_predictive_executor_with_no_new_container(self) -> None:
        """A C2 executor that reuses an existing MCP must not count as a warmup."""
        module = self.module
        started = datetime.now().replace(microsecond=0)
        base = time.mktime(started.timetuple())
        ts = (base + 0.2) * 1000
        record = {
            "started_at": started.strftime("%Y-%m-%d %H:%M:%S"),
            "prewarm_controller_telemetry": {
                "events": [
                    {
                        "event": "prewarm_schedule",
                        "stage": "predictive",
                        "candidate": "Playwright",
                        "status": "accepted",
                        "ts": ts - 100,
                    },
                    {
                        "event": "prewarm_executor",
                        "stage": "predictive",
                        "candidate": "Playwright",
                        "status": "started",
                        "ts": ts - 50,
                    },
                    {
                        "event": "prewarm_executor",
                        "stage": "predictive",
                        "candidate": "Playwright",
                        "status": "completed",
                        "ts": ts,
                    },
                ],
            },
            "events": [
                {
                    "step": "prewarm_candidate_finished",
                    "candidate": "Playwright",
                    "effective": False,
                    "startup_mode": "running",
                },
            ],
        }
        finished_at = datetime.fromtimestamp(base + 1).strftime(
            "%Y-%m-%d %H:%M:%S",
        )
        warmups, _, _ = module._read_predictive_events(
            [record],
            1,
            record["started_at"],
            finished_at,
            candidate_to_group={"Playwright": "browser_tools"},
        )
        self.assertEqual(warmups, [])

    def test_late_warmup_is_used_but_not_a_prefetch_hit(self) -> None:
        """A warmup that completes during demand is not a false positive."""
        module = self.module
        started = datetime.now().replace(microsecond=0)
        base = time.mktime(started.timetuple())
        timestamp_ms = lambda offset: (base + offset) * 1000
        record = {
            "started_at": started.strftime("%Y-%m-%d %H:%M:%S"),
            "started_at_unix_s": base,
            "prewarm_controller_telemetry": {
                "events": [
                    {
                        "event": "predict_candidates",
                        "stage": "predictive",
                        "status": "completed",
                        "candidate_count": 1,
                        "ts": timestamp_ms(0.05),
                    },
                    {
                        "event": "prewarm_schedule",
                        "stage": "predictive",
                        "candidate": "Unit Converter",
                        "status": "accepted",
                        "ts": timestamp_ms(0.1),
                    },
                    {
                        "event": "prewarm_executor",
                        "stage": "predictive",
                        "candidate": "Unit Converter",
                        "status": "started",
                        "ts": timestamp_ms(0.2),
                    },
                    {
                        "event": "prewarm_executor",
                        "stage": "predictive",
                        "candidate": "Unit Converter",
                        "status": "completed",
                        "ts": timestamp_ms(1.5),
                    },
                ],
            },
            "events": [
                {
                    "step": "tool_group_activation_requested",
                    "group_name": "unit_converter",
                    "elapsed_ms": 1_000,
                },
                {
                    "step": "mcp_server_ready",
                    "group_name": "unit_converter",
                    "startup_mode": "running",
                    "elapsed_ms": 1_200,
                },
                {
                    "step": "prewarm_candidate_finished",
                    "candidate": "Unit Converter",
                    "effective": True,
                    "startup_mode": "cold",
                },
            ],
        }
        finished_at = datetime.fromtimestamp(base + 2).strftime(
            "%Y-%m-%d %H:%M:%S",
        )
        warmups, demands, _ = module._read_predictive_events(
            [record],
            1,
            record["started_at"],
            finished_at,
            candidate_to_group={"Unit Converter": "unit_converter"},
        )
        self.assertEqual(len(warmups), 1)
        self.assertTrue(warmups[0]["later_demand_use"])
        self.assertEqual(warmups[0]["discard_timestamp_unix_s"], None)
        self.assertFalse(demands[0]["prefetch_hit"])

    def test_wrong_prediction_target_is_counted_as_a_miss(self) -> None:
        """An activation after a prediction counts even when its target differs."""
        module = self.module
        started = datetime.now().replace(microsecond=0)
        base = time.mktime(started.timetuple())
        timestamp_ms = lambda offset: (base + offset) * 1000
        prediction_record = {
            "started_at": started.strftime("%Y-%m-%d %H:%M:%S"),
            "started_at_unix_s": base,
            "prewarm_controller_telemetry": {
                "events": [
                    {
                        "event": "predict_candidates",
                        "stage": "predictive",
                        "status": "completed",
                        "candidate_count": 1,
                        "ts": timestamp_ms(0.1),
                    },
                    {
                        "event": "prewarm_schedule",
                        "stage": "predictive",
                        "candidate": "Unit Converter",
                        "status": "accepted",
                        "ts": timestamp_ms(0.2),
                    },
                    {
                        "event": "prewarm_executor",
                        "stage": "predictive",
                        "candidate": "Unit Converter",
                        "status": "started",
                        "ts": timestamp_ms(0.3),
                    },
                    {
                        "event": "prewarm_executor",
                        "stage": "predictive",
                        "candidate": "Unit Converter",
                        "status": "completed",
                        "effective": True,
                        "startup_mode": "cold",
                        "ts": timestamp_ms(0.5),
                    },
                ],
            },
            "events": [],
        }
        demand_record = {
            "started_at": started.strftime("%Y-%m-%d %H:%M:%S"),
            "started_at_unix_s": base + 1,
            "events": [
                {
                    "step": "tool_group_activation_requested",
                    "group_name": "github_tools",
                    "elapsed_ms": 200,
                },
                {
                    "step": "mcp_server_ready",
                    "group_name": "github_tools",
                    "startup_mode": "cold",
                    "elapsed_ms": 1_200,
                },
            ],
        }
        finished_at = datetime.fromtimestamp(base + 3).strftime(
            "%Y-%m-%d %H:%M:%S",
        )
        warmups, demands, _ = module._read_predictive_events(
            [prediction_record, demand_record],
            1,
            prediction_record["started_at"],
            finished_at,
            candidate_to_group={
                "Unit Converter": "unit_converter",
                "GitHub": "github_tools",
            },
        )
        self.assertEqual(len(demands), 1)
        self.assertEqual(demands[0]["target"], "github_tools")
        self.assertFalse(demands[0]["prefetch_hit"])
        self.assertEqual(len(warmups), 1)
        self.assertFalse(warmups[0]["later_demand_use"])


if __name__ == "__main__":
    import unittest

    unittest.main()
