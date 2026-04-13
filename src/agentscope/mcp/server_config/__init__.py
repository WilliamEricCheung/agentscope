# -*- coding: utf-8 -*-
"""Per-server MCP registration configuration modules."""

from .base import _DockerMCPRegistrationConfig
from .factory import _MCPServerConfigFactory
from .github_mcp import build_github_registration_config
from .playwright_mcp import build_playwright_registration_config

__all__ = [
    "_DockerMCPRegistrationConfig",
    "_MCPServerConfigFactory",
    "build_playwright_registration_config",
    "build_github_registration_config",
]
