# -*- coding: utf-8 -*-
"""Tests for MCP server profiling helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import TestCase


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from laplace.mcp_server_profile.profile_mcp_servers import (
    ProfileTarget,
    TrialMeasurement,
    _build_report,
    _dependency_services_for_targets,
    _pick_targeted_smoke_tool_and_args,
    _stage_summary,
    _summarize_server_trials,
)


class MCPServerProfileHelpersTest(TestCase):
    """Test helper functions used by the MCP server profiler."""

    def test_stage_summary_uses_successful_trials_only(self) -> None:
        """Stage aggregation should ignore failed trials and missing values."""
        trials = [
            TrialMeasurement(
                server_name="Playwright",
                trial_index=1,
                status="pass",
                cleanup_ms=1.0,
                docker_run_ms=10.0,
                tcp_ready_wait_ms=20.0,
                mcp_handshake_ms=30.0,
                interface_test_ms=40.0,
                total_ms=100.0,
                tcp_ready_elapsed_ms=30.0,
                handshake_elapsed_ms=60.0,
                interface_test_elapsed_ms=100.0,
            ),
            TrialMeasurement(
                server_name="Playwright",
                trial_index=2,
                status="fail",
                cleanup_ms=1.0,
                docker_run_ms=999.0,
                tcp_ready_wait_ms=None,
                mcp_handshake_ms=None,
                interface_test_ms=None,
                total_ms=999.0,
                tcp_ready_elapsed_ms=None,
                handshake_elapsed_ms=None,
                interface_test_elapsed_ms=None,
            ),
            TrialMeasurement(
                server_name="Playwright",
                trial_index=3,
                status="pass",
                cleanup_ms=1.0,
                docker_run_ms=14.0,
                tcp_ready_wait_ms=24.0,
                mcp_handshake_ms=34.0,
                interface_test_ms=44.0,
                total_ms=116.0,
                tcp_ready_elapsed_ms=38.0,
                handshake_elapsed_ms=72.0,
                interface_test_elapsed_ms=116.0,
            ),
        ]

        summary = _stage_summary(trials, "docker_run_ms")
        self.assertEqual(summary.count, 2)
        self.assertEqual(summary.avg_ms, 12.0)
        self.assertEqual(summary.min_ms, 10.0)
        self.assertEqual(summary.max_ms, 14.0)

    def test_server_summary_tracks_failures_and_smoke_skips(self) -> None:
        """Server summary should expose pass/fail counts and failure notes."""
        trials = [
            TrialMeasurement(
                server_name="Jupyter MCP",
                trial_index=1,
                status="partial",
                cleanup_ms=0.0,
                docker_run_ms=20.0,
                tcp_ready_wait_ms=30.0,
                mcp_handshake_ms=40.0,
                interface_test_ms=None,
                total_ms=90.0,
                tcp_ready_elapsed_ms=50.0,
                handshake_elapsed_ms=90.0,
                interface_test_elapsed_ms=None,
                smoke_attempted=False,
                smoke_note="Smoke call skipped",
            ),
            TrialMeasurement(
                server_name="Jupyter MCP",
                trial_index=2,
                status="fail",
                cleanup_ms=0.0,
                docker_run_ms=10.0,
                tcp_ready_wait_ms=None,
                mcp_handshake_ms=None,
                interface_test_ms=None,
                total_ms=10.0,
                tcp_ready_elapsed_ms=None,
                handshake_elapsed_ms=None,
                interface_test_elapsed_ms=None,
                diagnostics={"error": "TCP readiness timed out"},
            ),
        ]

        summary = _summarize_server_trials(trials)
        self.assertEqual(summary["trial_count"], 2)
        self.assertEqual(summary["pass_count"], 0)
        self.assertEqual(summary["partial_count"], 1)
        self.assertEqual(summary["fail_count"], 1)
        self.assertEqual(summary["smoke_skipped_count"], 1)
        self.assertEqual(summary["failure_notes"][0]["message"], "TCP readiness timed out")

    def test_build_report_contains_summary_table_and_details(self) -> None:
        """Markdown report should render summary and per-server sections."""
        payload = {
            "metadata": {
                "generated_at_utc": "2026-06-03T00:00:00+00:00",
                "manifest_path": "/tmp/laplace_mcp_manifest.json",
                "server_count": 1,
                "repeats": 10,
                "request_timeout_seconds": 20.0,
                "tcp_ready_timeout_seconds": 90.0,
                "docker_command_timeout_seconds": 60.0,
                "tcp_poll_interval_seconds": 0.2,
            },
            "server_summaries": {
                "Playwright": {
                    "trial_count": 10,
                    "pass_count": 10,
                    "partial_count": 0,
                    "fail_count": 0,
                    "smoke_attempted_count": 10,
                    "smoke_skipped_count": 0,
                    "stage_stats": {
                        "docker_run_ms": {"count": 10, "average_ms": 10.0, "minimum_ms": 8.0, "maximum_ms": 12.0},
                        "tcp_ready_wait_ms": {"count": 10, "average_ms": 20.0, "minimum_ms": 18.0, "maximum_ms": 22.0},
                        "mcp_handshake_ms": {"count": 10, "average_ms": 30.0, "minimum_ms": 29.0, "maximum_ms": 31.0},
                        "interface_test_ms": {"count": 10, "average_ms": 40.0, "minimum_ms": 39.0, "maximum_ms": 41.0},
                        "total_ms": {"count": 10, "average_ms": 100.0, "minimum_ms": 95.0, "maximum_ms": 105.0},
                        "tcp_ready_elapsed_ms": {"count": 10, "average_ms": 30.0, "minimum_ms": 26.0, "maximum_ms": 34.0},
                        "handshake_elapsed_ms": {"count": 10, "average_ms": 60.0, "minimum_ms": 55.0, "maximum_ms": 65.0},
                        "interface_test_elapsed_ms": {"count": 10, "average_ms": 100.0, "minimum_ms": 95.0, "maximum_ms": 105.0},
                    },
                    "failure_notes": [],
                },
            },
            "trials": {},
        }

        report = _build_report(payload)
        self.assertIn("# MCP Server Profile Report", report)
        self.assertIn("## Summary Table", report)
        self.assertIn("## Playwright", report)
        self.assertIn("Total Avg (ms)", report)
        self.assertIn("### Metric Stats", report)
        self.assertIn("### Milestones", report)
        self.assertLess(report.index("| docker_run_ms |"), report.index("| wait_tcp_ms |"))
        self.assertLess(report.index("| wait_tcp_ms |"), report.index("| mcp_handshake_ms |"))
        self.assertLess(report.index("| mcp_handshake_ms |"), report.index("| interface_test_ms |"))
        self.assertLess(report.index("| interface_test_ms |"), report.index("| total_ms |"))
        self.assertLess(report.index("### Metric Stats"), report.index("| total_ms |"))
        self.assertLess(report.index("| total_ms |"), report.index("### Milestones"))
        self.assertLess(report.index("### Milestones"), report.index("| tcp_ready_elapsed_ms |"))
        self.assertLess(report.index("| tcp_ready_elapsed_ms |"), report.index("| handshake_elapsed_ms |"))
        self.assertLess(report.index("| handshake_elapsed_ms |"), report.index("| interface_test_elapsed_ms |"))

    def test_targeted_smoke_prefers_neo4j_read_query(self) -> None:
        """Neo4j smoke calls should avoid slow schema inference by default."""
        target = ProfileTarget(
            name="Neo4j Cypher",
            container_name="laplace-neo4j-cypher",
            image="laplace/neo4j-cypher:local",
            original_image="mcp/neo4j-cypher:latest",
            transport="streamable_http",
            url="http://localhost:8829/mcp/",
            port=8829,
            endpoint="/mcp/",
            client_name="laplace-neo4j-cypher",
            docker_run_command=["docker", "run"],
            tool_names=("get_neo4j_schema", "read_neo4j_cypher"),
        )

        selected, arguments, reason = _pick_targeted_smoke_tool_and_args(
            target,
            [
                {"name": "get_neo4j_schema", "input_schema": {"type": "object", "properties": {}}},
                {
                    "name": "read_neo4j_cypher",
                    "input_schema": {
                        "type": "object",
                        "required": ["query"],
                        "properties": {"query": {"type": "string"}},
                    },
                },
            ],
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected["name"], "read_neo4j_cypher")
        self.assertEqual(arguments, {"query": "RETURN 1 AS ok"})
        self.assertIn("Cypher", reason)

    def test_dependency_selection_includes_neo4j_and_milvus(self) -> None:
        """Profiler should auto-bootstrap the heavy backend dependencies."""
        targets = [
            ProfileTarget(
                name="Neo4j Cypher",
                container_name="laplace-neo4j-cypher",
                image="laplace/neo4j-cypher:local",
                original_image="mcp/neo4j-cypher:latest",
                transport="streamable_http",
                url="http://localhost:8829/mcp/",
                port=8829,
                endpoint="/mcp/",
                client_name="laplace-neo4j-cypher",
                docker_run_command=["docker", "run"],
                tool_names=("read_neo4j_cypher",),
            ),
            ProfileTarget(
                name="Milvus MCP",
                container_name="laplace-mcp-server-milvus",
                image="laplace/mcp-server-milvus:local",
                original_image=None,
                transport="streamable_http",
                url="http://localhost:8832/mcp",
                port=8832,
                endpoint="/mcp",
                client_name="laplace-mcp-server-milvus",
                docker_run_command=["docker", "run"],
                tool_names=("milvus_list_databases",),
                profile_dependencies=(
                    {
                        "name": "Milvus Backend",
                        "container_name": "laplace-profile-milvus-backend",
                        "port": 19530,
                        "startup_timeout": 240.0,
                        "readiness_url": "http://127.0.0.1:9091/healthz",
                        "start_command": ["docker", "run", "laplace/milvus-backend:official-v3.0-beta"],
                        "stop_command": ["docker", "rm", "-f", "laplace-profile-milvus-backend"],
                    },
                ),
            ),
        ]

        dependencies = _dependency_services_for_targets(targets)
        by_name = {dependency.name: dependency for dependency in dependencies}
        self.assertEqual(sorted(by_name), ["Milvus Backend", "Neo4j"])
        self.assertEqual(by_name["Neo4j"].port, 7687)
        self.assertEqual(by_name["Milvus Backend"].port, 19530)
        self.assertEqual(
            by_name["Milvus Backend"].readiness_url,
            "http://127.0.0.1:9091/healthz",
        )
        self.assertEqual(
            by_name["Milvus Backend"].start_command,
            ["docker", "run", "laplace/milvus-backend:official-v3.0-beta"],
        )