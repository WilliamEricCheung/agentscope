# -*- coding: utf-8 -*-
"""Shared data structures for MCP server registration configs."""

from dataclasses import dataclass

from .._mcp_server_helper import _DockerMCPServerConfig


@dataclass(frozen=True)
class _DockerMCPRegistrationConfig:
    """The full registration config for a local Docker MCP server.

    Args:
        server_config (`_DockerMCPServerConfig`):
            The basic MCP server config used by the helper.
        docker_run_command (`list[str]`):
            The docker run command used for cold start.
        group_name (`str`):
            The toolkit group name.
        group_description (`str`):
            A concise description shown to the agent before activation.
        headers (`dict[str, str] | None`, optional):
            Optional client headers for MCP requests.
        tool_names (`tuple[str, ...]`, optional):
            Representative MCP tool names exposed by this server.
        group_notes (`str | None`, optional):
            Extra usage guidance shown to the agent after activation.
        server_name (`str | None`, optional):
            Human-readable server name, when available.

    Returns:
        `None`:
            This dataclass stores configuration only.
    """

    server_config: _DockerMCPServerConfig
    docker_run_command: list[str]
    group_name: str
    group_description: str
    headers: dict[str, str] | None = None
    tool_names: tuple[str, ...] = ()
    group_notes: str | None = None
    server_name: str | None = None
