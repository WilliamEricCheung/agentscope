# -*- coding: utf-8 -*-
"""Tests for MCP server validation helpers."""

from __future__ import annotations

from unittest import TestCase

from laplace.mcp_dataset.synthesis.validate_mcp_servers import (
    _build_mock_arguments,
    _compute_overall_status,
    _is_low_risk_tool_name,
    _is_port_mapping_present,
    _mock_value_from_schema,
    _pick_smoke_tool_and_args,
)


class MCPServerValidationHelpersTest(TestCase):
    """Test helper functions used by MCP server validator."""

    def test_port_mapping_detection(self) -> None:
        """Port mapping parser should detect expected host port."""
        ports = "0.0.0.0:8800->8000/tcp, [::]:8800->8000/tcp"
        self.assertTrue(_is_port_mapping_present(ports, 8800))
        self.assertFalse(_is_port_mapping_present(ports, 8801))

    def test_mock_value_generation(self) -> None:
        """Schema-based mock value generation should cover common types."""
        self.assertEqual(_mock_value_from_schema({"type": "string"}), "health_check")
        self.assertEqual(_mock_value_from_schema({"type": "integer"}), 0)
        self.assertEqual(_mock_value_from_schema({"type": "number"}), 0)
        self.assertFalse(_mock_value_from_schema({"type": "boolean"}))
        self.assertEqual(_mock_value_from_schema({"type": "array"}), [])
        self.assertEqual(_mock_value_from_schema({"type": "object"}), {})

    def test_build_mock_arguments_required_only(self) -> None:
        """Mock arguments should fill only required fields from schema."""
        schema = {
            "type": "object",
            "required": ["query", "limit"],
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
                "optional": {"type": "boolean"},
            },
        }
        self.assertEqual(
            _build_mock_arguments(schema),
            {
                "query": "health_check",
                "limit": 0,
            },
        )

    def test_smoke_tool_selection_prefers_safe_names(self) -> None:
        """Smoke selector should avoid risky names and pick satisfiable tools."""
        tool_specs = [
            {
                "name": "delete_record",
                "input_schema": {
                    "type": "object",
                    "required": ["id"],
                    "properties": {"id": {"type": "string"}},
                },
            },
            {
                "name": "think",
                "input_schema": {
                    "type": "object",
                    "required": ["thought"],
                    "properties": {"thought": {"type": "string"}},
                },
            },
        ]

        selected, arguments, reason = _pick_smoke_tool_and_args(tool_specs)
        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual(selected["name"], "think")
        self.assertEqual(arguments, {"thought": "health_check"})
        self.assertEqual(reason, "")

    def test_low_risk_tool_name_heuristics(self) -> None:
        """Risky operation keywords should be rejected."""
        self.assertTrue(_is_low_risk_tool_name("search_papers"))
        self.assertFalse(_is_low_risk_tool_name("delete_paper"))
        self.assertFalse(_is_low_risk_tool_name("create_order"))

    def test_overall_status_computation(self) -> None:
        """Overall status should follow mandatory checks and smoke option."""
        self.assertEqual(
            _compute_overall_status(True, True, True, True, False, None),
            "pass",
        )
        self.assertEqual(
            _compute_overall_status(True, True, True, True, True, False),
            "partial",
        )
        self.assertEqual(
            _compute_overall_status(True, False, True, True, False, None),
            "partial",
        )
        self.assertEqual(
            _compute_overall_status(True, True, False, False, False, None),
            "fail",
        )
