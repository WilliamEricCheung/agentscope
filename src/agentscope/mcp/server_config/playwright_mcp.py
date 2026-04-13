# -*- coding: utf-8 -*-
"""Playwright MCP server registration configuration."""

import os

from .._mcp_server_helper import _DockerMCPServerConfig
from .base import _DockerMCPRegistrationConfig


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
