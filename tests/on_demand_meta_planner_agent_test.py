# -*- coding: utf-8 -*-
"""Tests for the on-demand meta planner example helpers."""
import asyncio
import importlib.util
import inspect
import sys
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
    module_dir = str(module_path.parent)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    spec = importlib.util.spec_from_file_location(
        "on_demand_meta_planner_tool",
        module_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_config_module():
    """Load the example config module from its file path."""
    config_path = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "agent"
        / "on_demand_meta_planner_agent"
        / "config.py"
    )
    module_dir = str(config_path.parent)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    spec = importlib.util.spec_from_file_location(
        "on_demand_meta_planner_config",
        config_path,
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
        cls.config = _load_config_module()

    def test_create_worker_has_prewarm_flag_default_false(self) -> None:
        """`create_worker` prewarm default should come from shared config."""
        signature = inspect.signature(self.module.create_worker)

        self.assertIn("prewarm", signature.parameters)
        self.assertEqual(
            signature.parameters["prewarm"].default,
            self.config.ON_DEMAND_PREWARM_ENABLED,
        )

    def test_create_worker_exposes_stream_speculation_interval(self) -> None:
        """The example should expose the stream speculation threshold knob."""
        signature = inspect.signature(self.module.create_worker)

        self.assertIn(
            "stream_text_speculation_interval_tokens",
            signature.parameters,
        )
        self.assertEqual(
            signature.parameters[
                "stream_text_speculation_interval_tokens"
            ].default,
            self.config.ON_DEMAND_STREAM_TEXT_SPECULATION_INTERVAL_TOKENS,
        )
        self.assertEqual(
            self.config.normalize_stream_text_speculation_interval_tokens(20),
            20,
        )
        self.assertIsNone(
            self.config.normalize_stream_text_speculation_interval_tokens(0),
        )

    def test_main_planner_enables_stream_level_prewarm_scan(self) -> None:
        """Parent planner should wire stream-level scan from shared config."""
        main_path = (
            Path(__file__).resolve().parents[1]
            / "examples"
            / "agent"
            / "on_demand_meta_planner_agent"
            / "main.py"
        )
        source = main_path.read_text(encoding="utf-8")

        self.assertIn(
            "MCPPrewarmHybridRouter() if ON_DEMAND_PREWARM_ENABLED else None",
            source,
        )
        self.assertIn(
            "if ON_DEMAND_PREWARM_ENABLED",
            source,
        )
        self.assertIn(
            "stream_text_speculation_interval_tokens=(",
            source,
        )

    def test_worker_uses_hybrid_prewarm_router(self) -> None:
        """Worker helper should also wire Hybrid Router for L1->L2 prewarm."""
        tool_path = (
            Path(__file__).resolve().parents[1]
            / "examples"
            / "agent"
            / "on_demand_meta_planner_agent"
            / "tool.py"
        )
        source = tool_path.read_text(encoding="utf-8")

        self.assertIn(
            "base_prewarm_router = MCPPrewarmHybridRouter()",
            source,
        )

    def test_build_timing_summary_returns_expected_metrics(self) -> None:
        """Timing summary should compute key latencies from recorded events."""
        timing_run = {
            "events": [
                {
                    "step": "prewarm_router_enabled",
                    "elapsed_ms": 1.0,
                    "configured_router_method": "hybrid",
                },
                {
                    "step": "prewarm_router_matched",
                    "elapsed_ms": 5.0,
                    "configured_router_method": "hybrid",
                    "effective_route_method": "keyword",
                    "candidate_count": 1,
                    "candidates": "playwright-mcp",
                },
                {
                    "step": "prewarm_candidate_started",
                    "elapsed_ms": 12.0,
                    "candidate": "playwright-mcp",
                    "configured_router_method": "hybrid",
                    "effective_route_method": "keyword",
                },
                {
                    "step": "prewarm_candidate_finished",
                    "elapsed_ms": 80.0,
                    "candidate": "playwright-mcp",
                    "configured_router_method": "hybrid",
                    "effective_route_method": "keyword",
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
        self.assertNotIn("prewarm_router_method", summary)
        self.assertEqual(
            summary["prewarm_router_configured_method"],
            "hybrid",
        )
        self.assertEqual(
            summary["prewarm_router_effective_route_method"],
            "keyword",
        )
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

    def test_logged_candidate_events_include_effective_route_method(self) -> None:
        """Candidate-level prewarm events should expose the effective route."""

        class _FakeRouter:
            """Minimal router stub for timing event tests."""

            method = "hybrid"
            last_route_method = "semantic"

            def __call__(self, _msg: object) -> list[str]:
                """Return one normalized candidate."""
                return ["playwright-mcp"]

        class _FakeClient:
            """Minimal speculative client stub."""

            startup_mode = "resume"

        async def _fake_base_executor(_candidate: str) -> _FakeClient:
            """Return a resumed client for the selected candidate."""
            return _FakeClient()

        timing_run = self.module._create_mcp_timing_run(
            task_description="Open a documentation page",
            prewarm=True,
        )
        candidate_effective_route_methods: dict[str, str] = {}
        router = self.module._build_logged_prewarm_router(
            _FakeRouter(),
            timing_run,
            candidate_effective_route_methods,
        )

        original_builder = self.module.build_mcp_speculative_executor
        self.module.build_mcp_speculative_executor = (
            lambda _registrations: _fake_base_executor
        )
        try:
            executor = self.module._build_logged_prewarm_executor(
                registrations=[],
                timing_run=timing_run,
                configured_router_method="hybrid",
                candidate_effective_route_methods=candidate_effective_route_methods,
            )

            candidates = asyncio.run(router(None))
            self.assertEqual(candidates, ["playwright-mcp"])
            asyncio.run(executor("playwright-mcp"))
        finally:
            self.module.build_mcp_speculative_executor = original_builder

        started_event = next(
            event
            for event in timing_run["events"]
            if event.get("step") == "prewarm_candidate_started"
        )
        finished_event = next(
            event
            for event in timing_run["events"]
            if event.get("step") == "prewarm_candidate_finished"
        )

        self.assertEqual(
            candidate_effective_route_methods["playwright-mcp"],
            "semantic",
        )
        self.assertEqual(started_event["effective_route_method"], "semantic")
        self.assertEqual(finished_event["effective_route_method"], "semantic")
