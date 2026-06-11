# -*- coding: utf-8 -*-
"""Tests for SDG-based MCP predictive warmer."""

import json
import tempfile
from pathlib import Path
from unittest import TestCase

from agentscope.mcp import MCPPredictiveWarmer


class MCPPredictiveWarmerTest(TestCase):
    """Validate core predictive warmer behaviors."""

    def test_predict_next_servers_from_matrix_file(self) -> None:
        """Matrix file should drive top-k server prediction."""
        with tempfile.TemporaryDirectory() as tmpdir:
            matrix_path = Path(tmpdir) / "matrix.json"
            matrix_path.write_text(
                json.dumps(
                    {
                        "server_transition_counts": {
                            "Google Maps": {
                                "Weather Data": 3,
                                "Wikipedia": 1,
                            },
                        },
                        "server_transition_matrix": {
                            "Google Maps": {
                                "Weather Data": 0.75,
                                "Wikipedia": 0.25,
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            warmer = MCPPredictiveWarmer.from_json(matrix_path, top_k=2)
            self.assertEqual(
                warmer.predict_next_servers("Google Maps"),
                ["Weather Data", "Wikipedia"],
            )

    def test_probability_threshold_filters_candidates(self) -> None:
        """Probability threshold should remove low-confidence transitions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            matrix_path = Path(tmpdir) / "matrix.json"
            matrix_path.write_text(
                json.dumps(
                    {
                        "server_transition_matrix": {
                            "Wikipedia": {
                                "Paper Search": 0.4,
                                "Google Maps": 0.3,
                                "Weather Data": 0.3,
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            warmer = MCPPredictiveWarmer.from_json(
                matrix_path,
                top_k=3,
                probability_threshold=0.35,
            )
            self.assertEqual(
                warmer.predict_next_servers("Wikipedia"),
                ["Paper Search"],
            )

    def test_self_transition_can_be_excluded(self) -> None:
        """Self-transitions should be skipped when policy disables them."""
        with tempfile.TemporaryDirectory() as tmpdir:
            matrix_path = Path(tmpdir) / "matrix.json"
            matrix_path.write_text(
                json.dumps(
                    {
                        "server_transition_matrix": {
                            "Context7": {
                                "Context7": 0.7,
                                "Hugging Face": 0.3,
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            warmer = MCPPredictiveWarmer.from_json(
                matrix_path,
                top_k=2,
                include_self_transition=False,
            )
            self.assertEqual(
                warmer.predict_next_servers("Context7"),
                ["Hugging Face"],
            )

    def test_trace_fallback_builds_transition_matrix(self) -> None:
        """When matrix is absent, warmer should build from SDG traces."""
        with tempfile.TemporaryDirectory() as tmpdir:
            traces_path = Path(tmpdir) / "traces.json"
            traces_path.write_text(
                json.dumps(
                    {
                        "traces": [
                            {
                                "sdg_summary": {
                                    "server_path": [
                                        "Google Maps",
                                        "Weather Data",
                                        "Wikipedia",
                                    ],
                                    "state_path": [
                                        "Maps::Resolve",
                                        "Maps::Forecast",
                                        "General::Fetch",
                                    ],
                                },
                            },
                            {
                                "sdg_summary": {
                                    "server_path": [
                                        "Google Maps",
                                        "Weather Data",
                                    ],
                                    "state_path": [
                                        "Maps::Resolve",
                                        "Maps::Forecast",
                                    ],
                                },
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            warmer = MCPPredictiveWarmer(
                transition_matrix_path=Path(tmpdir) / "not_found.json",
                traces_path=traces_path,
                top_k=1,
            )
            self.assertEqual(
                warmer.predict_next_servers("Google Maps"),
                ["Weather Data"],
            )

    def test_online_update_refreshes_probability(self) -> None:
        """Online transition updates should change prediction ordering."""
        with tempfile.TemporaryDirectory() as tmpdir:
            matrix_path = Path(tmpdir) / "matrix.json"
            matrix_path.write_text(
                json.dumps(
                    {
                        "server_transition_counts": {
                            "Wikipedia": {
                                "Paper Search": 1,
                            },
                        },
                        "server_transition_matrix": {
                            "Wikipedia": {
                                "Paper Search": 1.0,
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            warmer = MCPPredictiveWarmer.from_json(matrix_path, top_k=2)
            warmer.update_transition("Wikipedia", "Google Maps")
            warmer.update_transition("Wikipedia", "Google Maps")
            self.assertEqual(
                warmer.predict_next_servers("Wikipedia"),
                ["Google Maps", "Paper Search"],
            )
