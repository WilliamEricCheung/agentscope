# -*- coding: utf-8 -*-
"""Factory interface for per-server MCP registration config builders."""

from .base import _DockerMCPRegistrationConfig
from .github_mcp import build_github_registration_config
from ._laplace_mcp import (
    build_laplace_registration_config,
    build_laplace_speculative_executor,
    load_laplace_registration_bundle,
    load_laplace_registration_configs,
)
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

    @staticmethod
    def build_laplace_registration_config(
        server_name: str,
        manifest_path: str | None = None,
    ) -> _DockerMCPRegistrationConfig:
        """Build one Laplace Docker MCP registration config.

        Args:
            server_name (`str`):
                Human-readable server name as it appears in the manifest.
            manifest_path (`str | None`, optional):
                Explicit path to the Laplace MCP manifest.  When omitted
                the default manifest bundled inside the agentscope
                repository is used.

        Returns:
            `_DockerMCPRegistrationConfig`:
                The registration config for the requested server.
        """
        return build_laplace_registration_config(
            server_name=server_name,
            manifest_path=manifest_path,
        )

    @staticmethod
    def load_laplace_registration_configs(
        manifest_path: str | None = None,
        ready_only: bool = True,
    ) -> dict[str, _DockerMCPRegistrationConfig]:
        """Load all Laplace Docker registration configs.

        Args:
            manifest_path (`str | None`, optional):
                Explicit path to the Laplace MCP manifest.
            ready_only (`bool`, optional):
                Whether to include only entries marked as prewarm-ready.

        Returns:
            `dict[str, _DockerMCPRegistrationConfig]`:
                Mapping from server name to registration config.
        """
        return load_laplace_registration_configs(
            manifest_path=manifest_path,
            ready_only=ready_only,
        )

    @staticmethod
    def build_laplace_speculative_executor(
        manifest_path: str | None = None,
        ready_only: bool = True,
    ) -> object:
        """Build a speculative executor for all Laplace registrations.

        Args:
            manifest_path (`str | None`, optional):
                Explicit path to the Laplace MCP manifest.
            ready_only (`bool`, optional):
                Whether to include only entries marked as prewarm-ready.

        Returns:
            `object`:
                Async callable used by prompt prewarming.
        """
        return build_laplace_speculative_executor(
            manifest_path=manifest_path,
            ready_only=ready_only,
        )

    @staticmethod
    def load_laplace_registration_bundle(
        manifest_path: str | None = None,
        ready_only: bool = True,
    ) -> tuple[dict[str, _DockerMCPRegistrationConfig], object]:
        """Load all Laplace registrations together with an executor.

        Args:
            manifest_path (`str | None`, optional):
                Explicit path to the Laplace MCP manifest.
            ready_only (`bool`, optional):
                Whether to include only entries marked as prewarm-ready.

        Returns:
            `tuple[dict[str, _DockerMCPRegistrationConfig], object]`:
                Registration configs plus a speculative executor.
        """
        return load_laplace_registration_bundle(
            manifest_path=manifest_path,
            ready_only=ready_only,
        )
