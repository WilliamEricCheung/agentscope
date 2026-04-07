# -*- coding: utf-8 -*-
"""Tests for MCP server config builders."""
import os
from unittest import TestCase
from unittest.mock import patch

from agentscope.mcp import _MCPServerConfigFactory


class MCPServerConfigFactoryTest(TestCase):
    """Test class for `_MCPServerConfigFactory`."""

    @patch.dict(os.environ, {}, clear=True)
    def test_build_playwright_registration_config_defaults(self) -> None:
        """Test default Playwright config values."""
        config = _MCPServerConfigFactory.build_playwright_registration_config()

        self.assertEqual(config.group_name, "browser_tools")
        self.assertEqual(config.server_config.container_name, "playwright-mcp")
        self.assertEqual(
            config.server_config.image,
            "mcr.microsoft.com/playwright/mcp:latest",
        )
        self.assertEqual(
            config.server_config.url,
            "http://localhost:8931/mcp",
        )
        self.assertIsNone(config.headers)
        self.assertIn("browser_navigate", config.tool_names)
        self.assertIn("browser_click", config.tool_names)
        self.assertIn("weather", config.group_description)
        self.assertIn("browser_tools", config.group_notes)
        self.assertEqual(config.docker_run_command[0:4], ["docker", "run", "-d", "-i"])
        self.assertIn("--entrypoint", config.docker_run_command)
        self.assertIn("node", config.docker_run_command)
        self.assertIn("--host", config.docker_run_command)
        self.assertIn("0.0.0.0", config.docker_run_command)

    @patch.dict(
        os.environ,
        {
            "PLAYWRIGHT_MCP_PORT": "9011",
            "PLAYWRIGHT_MCP_CONTAINER_NAME": "pw-mcp-x",
            "PLAYWRIGHT_MCP_IMAGE": "my/pw-mcp:dev",
            "PLAYWRIGHT_MCP_URL": "http://localhost:9011/mcp",
            "PLAYWRIGHT_MCP_BROWSER": "firefox",
        },
        clear=True,
    )
    def test_build_playwright_registration_config_with_env(self) -> None:
        """Test Playwright config with environment overrides."""
        config = _MCPServerConfigFactory.build_playwright_registration_config()

        self.assertEqual(config.server_config.container_name, "pw-mcp-x")
        self.assertEqual(config.server_config.image, "my/pw-mcp:dev")
        self.assertEqual(config.server_config.url, "http://localhost:9011/mcp")
        self.assertIn("9011:9011", config.docker_run_command)
        self.assertIn("firefox", config.docker_run_command)

    @patch.dict(os.environ, {}, clear=True)
    def test_build_github_registration_config_without_token(self) -> None:
        """Test GitHub config returns None when token is missing."""
        config = _MCPServerConfigFactory.build_github_registration_config(
            github_token=None,
        )

        self.assertIsNone(config)

    @patch.dict(
        os.environ,
        {"GITHUB_PERSONAL_ACCESS_TOKEN": "token-123"},
        clear=True,
    )
    def test_build_github_registration_config_defaults(self) -> None:
        """Test default GitHub config values."""
        config = _MCPServerConfigFactory.build_github_registration_config()
        assert config is not None

        self.assertEqual(config.group_name, "github_tools")
        self.assertEqual(config.server_config.container_name, "github-mcp")
        self.assertEqual(
            config.server_config.image,
            "ghcr.io/github/github-mcp-server:latest",
        )
        self.assertEqual(
            config.server_config.url,
            "http://localhost:8932/mcp",
        )
        self.assertEqual(
            config.headers,
            {"Authorization": "Bearer token-123"},
        )
        self.assertIn("get_file_contents", config.tool_names)
        self.assertIn("create_pull_request", config.tool_names)
        self.assertIn("pull requests", config.group_description)
        self.assertIn("Representative tools", config.group_notes)
        self.assertIn(
            "GITHUB_PERSONAL_ACCESS_TOKEN=token-123",
            config.docker_run_command,
        )
        self.assertIn(
            "GITHUB_TOOLS=get_file_contents,issue_read,create_pull_request",
            config.docker_run_command,
        )

    @patch.dict(
        os.environ,
        {
            "GITHUB_PERSONAL_ACCESS_TOKEN": "token-abc",
            "GITHUB_MCP_PORT": "9012",
            "GITHUB_MCP_CONTAINER_NAME": "gh-mcp-x",
            "GITHUB_MCP_IMAGE": "my/gh-mcp:dev",
            "GITHUB_MCP_URL": "http://localhost:9012/mcp",
            "GITHUB_MCP_TOOLS": "issue_read",
        },
        clear=True,
    )
    def test_build_github_registration_config_with_env(self) -> None:
        """Test GitHub config with environment overrides."""
        config = _MCPServerConfigFactory.build_github_registration_config()
        assert config is not None

        self.assertEqual(config.server_config.container_name, "gh-mcp-x")
        self.assertEqual(config.server_config.image, "my/gh-mcp:dev")
        self.assertEqual(config.server_config.url, "http://localhost:9012/mcp")
        self.assertEqual(config.tool_names, ("issue_read",))
        self.assertIn("9012:9012", config.docker_run_command)
        self.assertIn("GITHUB_TOOLS=issue_read", config.docker_run_command)
