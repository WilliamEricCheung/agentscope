# -*- coding: utf-8 -*-
"""Tests for the on-demand meta planner example helpers."""
import importlib.util
import inspect
from pathlib import Path
from unittest import TestCase


def _load_module():
    """Load the example tool module from its file path."""
    module_path = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "agent"
        / "on_demand_meta_planner_agent"
        / "tool.py"
    )
    spec = importlib.util.spec_from_file_location(
        "on_demand_meta_planner_tool",
        module_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OnDemandMetaPlannerToolTest(TestCase):
    """Test helpers for the on-demand meta planner example."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the example module once for all tests."""
        cls.module = _load_module()

    def test_create_worker_has_prewarm_flag_default_false(self) -> None:
        """`create_worker` should expose a `prewarm=False` comparison flag."""
        signature = inspect.signature(self.module.create_worker)

        self.assertIn("prewarm", signature.parameters)
        self.assertFalse(signature.parameters["prewarm"].default)

    def test_build_timing_summary_returns_expected_metrics(self) -> None:
        """Timing summary should compute key latencies from recorded events."""
        timing_run = {
            "events": [
                {
                    "step": "prewarm_router_matched",
                    "elapsed_ms": 5.0,
                    "router_method": "keyword",
                    "candidate_count": 1,
                    "candidates": "playwright-mcp",
                },
                {
                    "step": "prewarm_candidate_started",
                    "elapsed_ms": 12.0,
                    "candidate": "playwright-mcp",
                    "router_method": "keyword",
                },
                {
                    "step": "prewarm_candidate_finished",
                    "elapsed_ms": 80.0,
                    "candidate": "playwright-mcp",
                    "router_method": "keyword",
                    "startup_mode": "resume",
                    "effective": True,
                },
                {
                    "step": "tool_group_activation_requested",
                    "elapsed_ms": 100.0,
                },
                {
                    "step": "mcp_server_ready",
                    "elapsed_ms": 340.0,
                    "startup_mode": "resume",
                },
            ],
        }

        summary = self.module._build_mcp_timing_summary(timing_run)

        self.assertEqual(summary["startup_mode"], "resume")
        self.assertEqual(summary["prewarm_router_method"], "keyword")
        self.assertTrue(summary["prewarm_router_matched"])
        self.assertEqual(summary["prewarm_router_candidate_count"], 1)
        self.assertEqual(summary["prewarm_router_candidates"], "playwright-mcp")
        self.assertTrue(summary["prewarm_effective"])
        self.assertEqual(summary["prewarm_effective_candidate_count"], 1)
        self.assertEqual(summary["prewarm_effective_candidates"], "playwright-mcp")
        self.assertEqual(summary["prewarm_effective_startup_modes"], "resume")
        self.assertEqual(summary["time_to_prewarm_start_ms"], 12.0)
        self.assertEqual(summary["prewarm_duration_ms"], 68.0)
        self.assertEqual(summary["prewarm_ready_before_activation_ms"], 20.0)
        self.assertEqual(summary["wait_for_mcp_ready_after_activation_ms"], 240.0)
