"""Compatibility wrapper for the shared MCP tool discovery implementation."""

from laplace.util.mcp_tool_discovery import (
    HttpStatelessClient,
    MCPToolDiscoverer,
    StdIOStatefulClient,
)

__all__ = [
    "HttpStatelessClient",
    "MCPToolDiscoverer",
    "StdIOStatefulClient",
]