"""Compatibility wrapper for the moved MCP server validation utility."""

from laplace.util.validate_mcp_servers import (
    MCPServerValidator,
    _build_mock_arguments,
    _build_server_url,
    _compute_overall_status,
    _extract_required_fields,
    _is_low_risk_tool_name,
    _is_port_mapping_present,
    _mock_value_from_schema,
    _pick_smoke_tool_and_args,
    _tcp_probe,
    main,
)

__all__ = [
    "MCPServerValidator",
    "_build_mock_arguments",
    "_build_server_url",
    "_compute_overall_status",
    "_extract_required_fields",
    "_is_low_risk_tool_name",
    "_is_port_mapping_present",
    "_mock_value_from_schema",
    "_pick_smoke_tool_and_args",
    "_tcp_probe",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
