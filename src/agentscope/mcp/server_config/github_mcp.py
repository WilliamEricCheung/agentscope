# -*- coding: utf-8 -*-
"""GitHub MCP server registration configuration."""

import os

from .._mcp_server_helper import _DockerMCPServerConfig
from .base import _DockerMCPRegistrationConfig


def build_github_registration_config(
    github_token: str | None = None,
) -> _DockerMCPRegistrationConfig | None:
    """Build the GitHub MCP Docker registration config.

    Args:
        github_token (`str | None`, optional):
            The GitHub token used by both server and client. If not
            provided, it will be loaded from
            `GITHUB_PERSONAL_ACCESS_TOKEN`.

    Returns:
        `_DockerMCPRegistrationConfig | None`:
            The registration config for GitHub MCP, or `None` when token
            is missing.
    """
    github_token = github_token or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not github_token:
        return None

    github_port = os.getenv("GITHUB_MCP_PORT", "8932")
    container_name = os.getenv(
        "GITHUB_MCP_CONTAINER_NAME",
        "github-mcp",
    )
    image = os.getenv(
        "GITHUB_MCP_IMAGE",
        "ghcr.io/github/github-mcp-server:latest",
    )
    github_tools = os.getenv(
        "GITHUB_MCP_TOOLS",
        "get_file_contents,issue_read,create_pull_request",
    )
    tool_names = tuple(
        _.strip() for _ in github_tools.split(",") if _.strip()
    )

    server_config = _DockerMCPServerConfig(
        container_name=container_name,
        image=image,
        transport="streamable_http",
        url=os.getenv(
            "GITHUB_MCP_URL",
            f"http://localhost:{github_port}/mcp",
        ),
        client_name="github",
    )

    docker_run_command = [
        "docker",
        "run",
        "-d",
        "-i",
        "--rm",
        "--name",
        container_name,
        "-e",
        f"GITHUB_PERSONAL_ACCESS_TOKEN={github_token}",
        "-e",
        f"GITHUB_TOOLS={github_tools}",
        "-p",
        f"{github_port}:{github_port}",
        image,
        "http",
        "--port",
        github_port,
        "--base-url",
        "0.0.0.0",
    ]

    return _DockerMCPRegistrationConfig(
        server_config=server_config,
        docker_run_command=docker_run_command,
        group_name="github_tools",
        group_description=(
            "GitHub repository tools. Activate this group for repository "
            "files, issues, commits, branches, pull requests, or code "
            "review tasks."
        ),
        headers={"Authorization": f"Bearer {github_token}"},
        tool_names=tool_names,
        group_notes=(
            "Use this group for GitHub-related operations such as reading "
            "repository files, checking issues, or creating pull requests. "
            "Representative tools: "
            + ", ".join(tool_names)
            + "."
        ),
    )
