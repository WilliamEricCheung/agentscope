# -*- coding: utf-8 -*-
"""Laplace Docker MCP server registration config loader.

Loads per-server registration configs from the Laplace MCP manifest bundled
inside the server_config package
(``agentscope/mcp/server_config/laplace_mcp_manifest.json``).

Args:
    manifest_path (`str | None`, optional):
        Explicit path to the Laplace MCP manifest.
    server_name (`str`):
        Human-readable server name as it appears in the manifest.
    ready_only (`bool`, optional):
        Whether to skip entries not marked as prewarm-ready.

Returns:
    `None`:
        This module exposes factory helpers only.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

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


def build_laplace_registration_config(
    server_name: str,
    manifest_path: str | None = None,
) -> _DockerMCPRegistrationConfig:
    """Build one Laplace Docker MCP registration config.

    Args:
        server_name (`str`):
            Human-readable server name as it appears in the manifest.
        manifest_path (`str | None`, optional):
            Explicit path to the Laplace MCP manifest.  When omitted the
            default manifest bundled inside the ``agentscope.mcp`` package
            is used (``agentscope/mcp/server_config/``
            ``laplace_mcp_manifest.json``).

    Returns:
        `_DockerMCPRegistrationConfig`:
            The registration config for the requested server.

    Raises:
        `FileNotFoundError`:
            Raised when the manifest cannot be found.
        `KeyError`:
            Raised when ``server_name`` is absent from the manifest.
        `ValueError`:
            Raised when the server exists but ``ready_for_prewarm`` is
            ``false``.
    """
    manifest = _load_manifest(manifest_path)
    servers = manifest.get("servers", {})
    if server_name not in servers:
        raise KeyError(f"Server not defined in Laplace manifest: {server_name}")

    payload = servers[server_name]
    if not bool(payload.get("ready_for_prewarm", False)):
        raise ValueError(
            f"Server is not marked as prewarm-ready: {server_name}",
        )

    server_config_payload = payload["server_config"]
    server_config = _DockerMCPServerConfig(
        container_name=_resolve_placeholders(
            server_config_payload["container_name"]
        ),
        image=_resolve_placeholders(server_config_payload["image"]),
        transport=server_config_payload["transport"],
        url=_resolve_placeholders(server_config_payload["url"]),
        client_name=_resolve_placeholders(server_config_payload["client_name"]),
    )
    docker_run_command = [
        _resolve_placeholders(str(item))
        for item in payload.get("docker_run_command", [])
    ]

    return _DockerMCPRegistrationConfig(
        server_config=server_config,
        docker_run_command=docker_run_command,
        group_name=str(
            payload.get("group_name", _normalize_group_name(server_name))
        ),
        group_description=str(
            payload.get("group_description", "Laplace MCP server tools.")
        ),
        headers=_string_dict(payload.get("headers")),
        tool_names=tuple(str(t) for t in payload.get("tool_names", [])),
        group_notes=str(payload["notes"]) if "notes" in payload else None,
        server_name=server_name,
    )


def load_laplace_registration_configs(
    manifest_path: str | None = None,
    ready_only: bool = True,
) -> dict[str, _DockerMCPRegistrationConfig]:
    """Load all Laplace Docker MCP registration configs from the manifest.

    Args:
        manifest_path (`str | None`, optional):
            Explicit path to the Laplace MCP manifest.  When omitted the
            default manifest bundled inside the agentscope repository is
            used.
        ready_only (`bool`, optional):
            When ``True`` (default) only entries with
            ``ready_for_prewarm: true`` are returned.

    Returns:
        `dict[str, _DockerMCPRegistrationConfig]`:
            Mapping from server name to registration config.
    """
    manifest = _load_manifest(manifest_path)
    configs: dict[str, _DockerMCPRegistrationConfig] = {}
    for server_name, payload in manifest.get("servers", {}).items():
        if ready_only and not bool(payload.get("ready_for_prewarm", False)):
            continue
        if "server_config" not in payload:
            continue
        configs[server_name] = build_laplace_registration_config(
            server_name=server_name,
            manifest_path=manifest_path,
        )
    return configs


def build_laplace_speculative_executor(
    manifest_path: str | None = None,
    ready_only: bool = True,
) -> Callable[[str], Awaitable[object | None]]:
    """Build a speculative prewarm executor for manifest-defined servers.

    Args:
        manifest_path (`str | None`, optional):
            Explicit path to the Laplace MCP manifest.  When omitted the
            bundled package manifest is used.
        ready_only (`bool`, optional):
            Whether to include only entries marked as prewarm-ready.

    Returns:
        `Callable[[str], Awaitable[object | None]]`:
            An executor compatible with prompt prewarming.
    """
    registrations = list(
        load_laplace_registration_configs(
            manifest_path=manifest_path,
            ready_only=ready_only,
        ).values(),
    )

    from .._prewarm_router import build_mcp_speculative_executor

    return build_mcp_speculative_executor(registrations)


def load_laplace_registration_bundle(
    manifest_path: str | None = None,
    ready_only: bool = True,
) -> tuple[
    dict[str, _DockerMCPRegistrationConfig],
    Callable[[str], Awaitable[object | None]],
]:
    """Load all Laplace registrations together with a prewarm executor.

    This is the batch entry point for experiment code.  The returned
    registrations can be passed around as normal registration configs, while
    the paired executor plugs into the existing speculative prewarm pathway
    and therefore reuses the same Docker start/resume/idle-stop lifecycle.

    Args:
        manifest_path (`str | None`, optional):
            Explicit path to the Laplace MCP manifest.  When omitted the
            bundled package manifest is used.
        ready_only (`bool`, optional):
            Whether to include only entries marked as prewarm-ready.

    Returns:
        `tuple[dict[str, _DockerMCPRegistrationConfig], Callable[[str], Awaitable[object | None]]]`:
            The loaded registrations plus an executor for speculative
            prewarming.
    """
    configs = load_laplace_registration_configs(
        manifest_path=manifest_path,
        ready_only=ready_only,
    )
    return configs, build_laplace_speculative_executor(
        manifest_path=manifest_path,
        ready_only=ready_only,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_manifest(manifest_path: str | None) -> dict[str, Any]:
    """Load the Laplace MCP manifest from disk.

    Args:
        manifest_path (`str | None`):
            Explicit path to the manifest, or ``None`` to use the default.

    Returns:
        `dict[str, Any]`:
            Parsed manifest content.
    """
    resolved_path = (
        Path(manifest_path)
        if manifest_path is not None
        else _resolve_default_manifest_path()
    )
    if not resolved_path.exists():
        raise FileNotFoundError(
            f"Laplace MCP manifest not found: {resolved_path}",
        )
    return json.loads(resolved_path.read_text(encoding="utf-8"))


def _resolve_default_manifest_path() -> Path:
    """Resolve the default Laplace MCP manifest path.

    The manifest lives next to this module inside the ``server_config``
    package directory.

    Returns:
        `Path`:
            The resolved manifest path.
    """
    return Path(__file__).resolve().with_name("laplace_mcp_manifest.json")


def _resolve_placeholders(value: str) -> str:
    """Resolve ``${VAR}`` and ``${VAR:-default}`` placeholders in a string.

    Args:
        value (`str`):
            String that may contain shell-style placeholders.

    Returns:
        `str`:
            String with placeholders resolved from ``os.environ``.
    """
    output = value
    while "${" in output and "}" in output:
        start = output.index("${")
        end = output.index("}", start)
        token = output[start + 2 : end]
        if ":-" in token:
            key, default = token.split(":-", maxsplit=1)
            replacement = os.getenv(key, default)
        else:
            replacement = os.getenv(token, "")
        output = output[:start] + replacement + output[end + 1 :]
    return output


def _normalize_group_name(server_name: str) -> str:
    """Derive a group identifier from a human-readable server name.

    Args:
        server_name (`str`):
            Human-readable server name.

    Returns:
        `str`:
            Normalized group name prefixed with ``laplace_``.
    """
    return "laplace_" + server_name.strip().lower().replace(" ", "_")


def _string_dict(value: Any) -> dict[str, str] | None:
    """Normalize an optional dictionary of string pairs.

    Args:
        value (`Any`):
            Raw value from the manifest.

    Returns:
        `dict[str, str] | None`:
            Normalized string dict, or ``None``.
    """
    if not isinstance(value, dict):
        return None
    return {str(k): str(v) for k, v in value.items()}
