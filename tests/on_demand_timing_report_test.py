# -*- coding: utf-8 -*-
"""Tests for the on-demand timing report formatter script."""
import importlib.util
import json
import tempfile
from pathlib import Path
from unittest import TestCase


def _load_module():
    """Load the formatter script from the example directory."""
    module_path = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "agent"
        / "on_demand_meta_planner_agent"
        / "format_timing_log.py"
    )
    spec = importlib.util.spec_from_file_location(
        "on_demand_timing_formatter",
        module_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OnDemandTimingReportTest(TestCase):
    """Test the offline timing log report generator."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the formatter script once."""
        cls.module = _load_module()

    def test_generate_report_outputs_markdown_tables(self) -> None:
        """The formatter should write readable Markdown comparison tables."""
        sample_records = [
            {
                "run_id": "worker-1",
                "started_at": "2026-04-08 18:00:00",
                "prewarm": False,
                "task_description": "Get the weather forecast for Beijing tomorrow",
                "summary": {
                    "startup_mode": "cold",
                    "prewarm_router_method": None,
                    "prewarm_router_matched": None,
                    "prewarm_effective": None,
                    "time_to_prewarm_start_ms": None,
                    "prewarm_duration_ms": None,
                    "prewarm_ready_before_activation_ms": None,
                    "wait_for_mcp_ready_after_activation_ms": 2310.4,
                },
            },
            {
                "run_id": "worker-2",
                "started_at": "2026-04-08 18:02:00",
                "prewarm": True,
                "task_description": "Get the weather forecast for Beijing tomorrow",
                "summary": {
                    "startup_mode": "running",
                    "prewarm_router_method": "keyword",
                    "prewarm_router_matched": True,
                    "prewarm_effective": False,
                    "time_to_prewarm_start_ms": 45.2,
                    "prewarm_duration_ms": 710.5,
                    "prewarm_ready_before_activation_ms": 920.0,
                    "wait_for_mcp_ready_after_activation_ms": 3.9,
                },
            },
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "timing.jsonl"
            output_path = Path(temp_dir) / "timing_report.md"
            with log_path.open("w", encoding="utf-8") as file:
                for record in sample_records:
                    file.write(json.dumps(record, ensure_ascii=False) + "\n")

            report = self.module.generate_report(log_path, output_path)
            saved_text = output_path.read_text(encoding="utf-8")

        self.assertIn("# On-demand MCP Timing Report", report)
        self.assertIn("## Aggregated Comparison by Prewarm Mode", report)
        self.assertIn("## Prewarm Router Effectiveness", report)
        self.assertIn("## Aggregated Comparison by Prewarm + Startup Mode", report)
        self.assertIn("## Per-run Details", report)
        self.assertIn("prewarm=false", report)
        self.assertIn("prewarm=true", report)
        self.assertIn("keyword", report)
        self.assertIn("running", report)
        self.assertIn("2310.400", report)
        self.assertIn("3.900", report)
        self.assertEqual(report, saved_text)
