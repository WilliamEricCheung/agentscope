# -*- coding: utf-8 -*-
"""Helpers for request-scoped MCP container isolation in experiments."""

from __future__ import annotations

import fcntl
import hashlib
import os
import re
import socket
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from agentscope.mcp import _DockerMCPRegistrationConfig


# Use a higher dedicated range for experiment-scoped MCP host ports to avoid
# collisions with long-lived local services and stale docker allocations.
_DEFAULT_REQUEST_PORT_BASE = 40000
_MODE_PORT_OFFSETS = {
    "on_demand": 0,
    "laplace": 5000,
    "always_on": 10000,
}
_REQUEST_PORT_SEGMENT_SIZE = 512
_REQUEST_REPEAT_PORT_OFFSET = 2048
_REQUEST_QPS_PORT_OFFSET = 64
_PORT_ALLOCATION_LOCK_PATH = "/tmp/agentscope_mcp_port_allocation.lock"


def get_request_namespace(default: str | None = None) -> str | None:
    """Resolve the request namespace from the environment."""
    namespace = os.getenv("AGENTSCOPE_MCP_CONTAINER_NAMESPACE", "").strip()
    if namespace:
        return namespace
    return default


def get_request_port(default: int | None = None) -> int | None:
    """Resolve the request port from the environment."""
    port_value = os.getenv("AGENTSCOPE_MCP_CONTAINER_PORT", "").strip()
    if port_value:
        return int(port_value)
    return default


def build_request_namespace(
    mode: str,
    qps: int,
    repeat_id: int,
    request_id: int,
) -> str:
    """Build a stable namespace for one request wave slot."""
    return f"{mode}_qps{int(qps)}_r{int(repeat_id)}_req{int(request_id)}"


def build_request_port(
    mode: str,
    qps: int,
    repeat_id: int,
    request_id: int,
    base_port: int = _DEFAULT_REQUEST_PORT_BASE,
) -> int:
    """Build a stable host port for one request-scoped container."""
    mode_offset = _MODE_PORT_OFFSETS.get(str(mode), 15000)
    return int(
        base_port
        + mode_offset
        + (int(repeat_id) * _REQUEST_REPEAT_PORT_OFFSET)
        + (int(qps) * _REQUEST_QPS_PORT_OFFSET)
        + (int(request_id) * _REQUEST_PORT_SEGMENT_SIZE)
    )


def scope_registration_config(
    registration: _DockerMCPRegistrationConfig,
    namespace: str | None,
    port: int | None,
) -> _DockerMCPRegistrationConfig:
    """Clone one registration config with request-scoped container settings."""
    if not namespace and port is None:
        return registration

    server_config = registration.server_config
    scoped_suffix = _extract_request_index(namespace)
    scoped_container_name = f"{server_config.container_name}-{scoped_suffix}"
    scoped_client_name = f"{server_config.client_name}-{scoped_suffix}"

    scoped_server_config = replace(
        server_config,
        container_name=scoped_container_name,
        client_name=scoped_client_name,
        url=_rewrite_url_port(server_config.url, port),
    )

    scoped_docker_run_command = _rewrite_docker_run_command_port(
        list(registration.docker_run_command),
        scoped_container_name,
        port,
    )

    return replace(
        registration,
        server_config=scoped_server_config,
        docker_run_command=scoped_docker_run_command,
    )


def scope_registration_configs(
    registrations: list[_DockerMCPRegistrationConfig],
    namespace: str | None,
    port: int | None,
) -> list[_DockerMCPRegistrationConfig]:
    """Clone a registration list with request-scoped settings."""
    if port is None:
        return [scope_registration_config(reg, namespace, port) for reg in registrations]

    used_ports: set[int] = set()
    scoped_registrations: list[_DockerMCPRegistrationConfig] = []
    for reg in registrations:
        scoped_port = _allocate_server_scoped_port(
            registration=reg,
            request_port=int(port),
            used_ports=used_ports,
        )
        scoped_registrations.append(scope_registration_config(reg, namespace, scoped_port))
    return scoped_registrations


def cleanup_scoped_containers(
    registrations: list[_DockerMCPRegistrationConfig],
) -> None:
    """Force-remove the containers defined by the provided registrations."""
    container_names = sorted(
        {
            str(reg.server_config.container_name)
            for reg in registrations
            if getattr(reg, "server_config", None) is not None
        },
    )

    for container_name in container_names:
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
            )
        except subprocess.TimeoutExpired:
            pass

    lifecycle_dir = _resolve_lifecycle_dir()
    if not lifecycle_dir.exists():
        return

    for container_name in container_names:
        safe_name = container_name.replace(os.sep, "_").replace(":", "_")
        state_file = lifecycle_dir / f"{safe_name}.json"
        if state_file.exists():
            state_file.unlink()


def _resolve_lifecycle_dir() -> Path:
    """Resolve the local MCP lifecycle directory."""
    configured = os.getenv("AGENTSCOPE_MCP_LIFECYCLE_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    repo_root = Path(__file__).resolve().parents[4]
    return repo_root / "laplace" / "mcp_lifecycle"


def _sanitize_suffix(value: str) -> str:
    """Convert a namespace string into a docker-safe suffix."""
    safe_value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return safe_value.strip("._-") or "request"


def _extract_request_index(namespace: str | None) -> int:
    """Extract the request index from a generated namespace string."""
    if not namespace:
        return 0

    match = re.search(r"_req(?P<request>\d+)(?:_|$)", namespace)
    if match is not None:
        return int(match.group("request"))

    tail_match = re.search(r"(?P<request>\d+)$", namespace)
    if tail_match is not None:
        return int(tail_match.group("request"))

    return 0


def _rewrite_url_port(url: str, port: int | None) -> str:
    """Rewrite a local MCP URL to the request-scoped host port."""
    if port is None:
        return url

    parts = urlsplit(url)
    hostname = parts.hostname or "localhost"
    netloc = f"{hostname}:{int(port)}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _rewrite_docker_run_command_port(
    docker_run_command: list[str],
    container_name: str,
    port: int | None,
) -> list[str]:
    """Rewrite request-scoped name and host port in docker run command."""
    updated_command = list(docker_run_command)

    for index, item in enumerate(updated_command):
        if item != "--name" or index + 1 >= len(updated_command):
            continue
        updated_command[index + 1] = container_name
        break

    if port is None:
        return updated_command

    for index, item in enumerate(updated_command):
        if item != "-p" or index + 1 >= len(updated_command):
            continue

        port_mapping = updated_command[index + 1]
        if ":" not in port_mapping:
            continue

        _, container_port = port_mapping.split(":", maxsplit=1)
        updated_command[index + 1] = f"{int(port)}:{container_port}"
        return updated_command

    raise ValueError("docker_run_command does not contain a -p host port mapping")


def _allocate_server_scoped_port(
    registration: _DockerMCPRegistrationConfig,
    request_port: int,
    used_ports: set[int],
) -> int:
    """Allocate a deterministic unique host port for one server within a request."""
    lock_path = _resolve_port_allocation_lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            server_name = str(getattr(registration, "server_name", "") or "")
            container_name = str(registration.server_config.container_name)
            key = f"{server_name}|{container_name}"
            digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
            offset = int(digest[:4], 16) % 400
            candidate = int(request_port) + offset

            # Probe host availability to avoid stale docker/network port conflicts
            # that can persist across retries for a deterministic fixed candidate.
            while candidate in used_ports or not _is_host_port_available(candidate):
                candidate += 1

            used_ports.add(candidate)
            return candidate
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _resolve_port_allocation_lock_path() -> Path:
    """Resolve cross-process lock path for host port allocation."""
    configured = os.getenv("AGENTSCOPE_MCP_PORT_ALLOCATION_LOCK", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(_PORT_ALLOCATION_LOCK_PATH)


def _is_host_port_available(port: int) -> bool:
    """Return whether a host TCP port can be bound on 0.0.0.0."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("0.0.0.0", int(port)))
        return True
    except OSError:
        return False
    finally:
        sock.close()