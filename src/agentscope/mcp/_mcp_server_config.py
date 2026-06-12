# -*- coding: utf-8 -*-
"""Backward-compatible re-export for MCP server configs.

This module keeps the historical import path while the implementation has
been split into per-server files under `agentscope.mcp.server_config`.
"""

from .server_config import (
    _DockerMCPRegistrationConfig,
    build_laplace_registration_config,
    build_laplace_speculative_executor,
    load_laplace_registration_bundle,
    load_laplace_registration_configs,
)

__all__ = [
    "_DockerMCPRegistrationConfig",
    "build_laplace_registration_config",
    "build_laplace_speculative_executor",
    "load_laplace_registration_bundle",
    "load_laplace_registration_configs",
]
