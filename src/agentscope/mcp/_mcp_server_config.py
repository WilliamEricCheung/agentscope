# -*- coding: utf-8 -*-
"""Configuration builders for local Docker-based MCP servers."""
import os
from dataclasses import dataclass

from ._mcp_server_helper import _DockerMCPServerConfig


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


class _MCPServerConfigFactory:
    """Factory methods for local Docker MCP server registration configs."""

    @staticmethod
    def build_playwright_registration_config() -> _DockerMCPRegistrationConfig:
        """Build the Playwright MCP Docker registration config.

        Returns:
            `_DockerMCPRegistrationConfig`:
                The registration config for Playwright MCP.
        """
        playwright_port = os.getenv("PLAYWRIGHT_MCP_PORT", "8931")
        container_name = os.getenv(
            "PLAYWRIGHT_MCP_CONTAINER_NAME",
            "playwright-mcp",
        )
        image = os.getenv(
            "PLAYWRIGHT_MCP_IMAGE",
            "mcr.microsoft.com/playwright/mcp:latest",
        )
        browser = os.getenv("PLAYWRIGHT_MCP_BROWSER", "chromium")

        server_config = _DockerMCPServerConfig(
            container_name=container_name,
            image=image,
            transport="streamable_http",
            url=os.getenv(
                "PLAYWRIGHT_MCP_URL",
                f"http://localhost:{playwright_port}/mcp",
            ),
            client_name="playwright-mcp",
        )

        docker_run_command = [
            "docker",
            "run",
            "-d",
            "-i",
            "--rm",
            "--init",
            "--entrypoint",
            "node",
            "--name",
            container_name,
            "-p",
            f"{playwright_port}:{playwright_port}",
            image,
            "cli.js",
            "--headless",
            "--browser",
            browser,
            "--no-sandbox",
            "--port",
            playwright_port,
            "--host",
            "0.0.0.0",
        ]
        tool_names = (
            "browser_click",
            "browser_close",
            "browser_console_messages",
            "browser_drag",
            "browser_evaluate",
            "browser_file_upload",
            "browser_fill_form",
            "browser_handle_dialog",
            "browser_hover",
            "browser_navigate",
            "browser_navigate_back",
            "browser_network_requests",
            "browser_press_key",
            "browser_resize",
            "browser_run_code",
            "browser_select_option",
            "browser_snapshot",
            "browser_tabs",
            "browser_take_screenshot",
            "browser_type",
            "browser_wait_for",
        )

        return _DockerMCPRegistrationConfig(
            server_config=server_config,
            docker_run_command=docker_run_command,
            group_name="browser_tools",
            group_description=(
                "Web browsing and live Internet access tools. Activate this "
                "group for weather, news, searching webpages, opening URLs, "
                "or extracting online page content."
            ),
            tool_names=tool_names,
            group_notes=(
                "Use this group whenever the task needs current online "
                "information or website interaction. Representative tools: "
                + ", ".join(tool_names)
                + ". Do not claim that web access is unavailable before "
                "trying to activate `browser_tools`."
            ),
        )

    @staticmethod
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