# -*- coding: utf-8 -*-
"""Tests for Laplace manifest-based MCP server config loading."""
import os
from unittest import TestCase
from unittest.mock import patch

from agentscope.mcp import (
    load_laplace_registration_bundle,
    load_laplace_registration_configs,
)


class LaplaceMCPServerConfigTest(TestCase):
    """Test class for manifest-based MCP registration loading."""

    @patch.dict(os.environ, {}, clear=True)
    def test_load_laplace_registration_configs_defaults(self) -> None:
        """Playwright config should be loaded from the bundled manifest."""
        configs = load_laplace_registration_configs()
        playwright = configs["Playwright"]

        self.assertEqual(playwright.group_name, "browser_tools")
        self.assertEqual(
            playwright.server_config.container_name,
            "laplace-playwright-mcp",
        )
        self.assertEqual(
            playwright.server_config.image,
            "laplace/playwright-mcp:local",
        )
        self.assertEqual(playwright.server_config.url, "http://localhost:8804/mcp")
        self.assertIn("browser_navigate", playwright.tool_names)
        self.assertIn("browser_click", playwright.tool_names)
        self.assertEqual(playwright.docker_run_command[0:3], ["docker", "run", "-d"])

    @patch.dict(
        os.environ,
        {"JUPYTER_URL": "http://example-host:9999"},
        clear=True,
    )
    def test_load_laplace_registration_configs_resolve_placeholders(self) -> None:
        """Manifest placeholders should resolve using environment variables."""
        configs = load_laplace_registration_configs()
        jupyter = configs["Jupyter MCP"]

        self.assertIn("JUPYTER_URL=http://example-host:9999", jupyter.docker_run_command)

    @patch.dict(os.environ, {}, clear=True)
    def test_load_laplace_registration_bundle(self) -> None:
        """Registration bundle should return configs and an executor."""
        configs, executor = load_laplace_registration_bundle()

        self.assertIn("Playwright", configs)
        self.assertTrue(callable(executor))
