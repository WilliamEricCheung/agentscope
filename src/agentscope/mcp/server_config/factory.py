# -*- coding: utf-8 -*-
"""Factory interface for per-server MCP registration config builders."""

from .base import _DockerMCPRegistrationConfig
from .github_mcp import build_github_registration_config
from .playwright_mcp import build_playwright_registration_config


class _MCPServerConfigFactory:
    """Factory methods for local Docker MCP server registration configs."""

    @staticmethod
    def build_playwright_registration_config() -> _DockerMCPRegistrationConfig:
        """Build the Playwright MCP Docker registration config.

        Returns:
            `_DockerMCPRegistrationConfig`:
                The registration config for Playwright MCP.
        """
        return build_playwright_registration_config()

    @staticmethod
    def build_github_registration_config(
        github_token: str | None = None,
    ) -> _DockerMCPRegistrationConfig | None:
        """Build the GitHub MCP Docker registration config.

        Args:
            github_token (`str | None`, optional):
                The GitHub token used by both server and client.

        Returns:
            `_DockerMCPRegistrationConfig | None`:
                The registration config for GitHub MCP, or `None`.
        """
        return build_github_registration_config(github_token=github_token)
