# -*- coding: utf-8 -*-
"""The MCP module in AgentScope, that provides fine-grained control over
the MCP servers."""

from ._client_base import MCPClientBase
from ._mcp_function import MCPToolFunction
from ._stateful_client_base import StatefulClientBase
from ._stdio_stateful_client import StdIOStatefulClient
from ._http_stateless_client import HttpStatelessClient
from ._http_stateful_client import HttpStatefulClient
from ._mcp_server_helper import (
    _DockerMCPServerConfig,
    _ensure_local_docker_mcp_server,
)
from ._mcp_server_config import (
    _DockerMCPRegistrationConfig,
    _MCPServerConfigFactory,
)


__all__ = [
    "MCPToolFunction",
    "MCPClientBase",
    "StatefulClientBase",
    "StdIOStatefulClient",
    "HttpStatelessClient",
    "HttpStatefulClient",
    "_DockerMCPServerConfig",
    "_ensure_local_docker_mcp_server",
    "_DockerMCPRegistrationConfig",
    "_MCPServerConfigFactory",
]
