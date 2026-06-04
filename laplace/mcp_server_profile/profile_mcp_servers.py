"""Profile Laplace MCP server cold-start readiness and smoke connectivity.

This script loads all prewarm-ready MCP servers from the Laplace manifest and
profiles each server repeatedly from a cold-start state. Every trial removes
the previous container, launches the service using the manifest's
``docker_run_command``, waits for TCP port readiness, performs MCP
``list_tools`` handshake, and optionally executes one low-risk tool call as an
interface smoke test.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import socket
import statistics
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


_SCRIPT_PATH = Path(__file__).resolve()
_SCRIPT_DIR = _SCRIPT_PATH.parent
_REPO_ROOT = _SCRIPT_PATH.parents[2]
_SRC_ROOT = _REPO_ROOT / "src"
for _path in (str(_REPO_ROOT), str(_SRC_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from laplace.util.mcp_tool_discovery import (  # noqa: E402
    HttpStatelessClient,
)
from laplace.util.server_config import (  # noqa: E402
    _resolve_env_placeholders,
)
from laplace.util.validate_mcp_servers import (  # noqa: E402
    _pick_smoke_tool_and_args,
)


_LOGGER = logging.getLogger(__name__)
_DEFAULT_MANIFEST_PATH = (
    _REPO_ROOT
    / "src"
    / "agentscope"
    / "mcp"
    / "server_config"
    / "laplace_mcp_manifest.json"
)
_DEFAULT_RESULTS_PATH = _SCRIPT_DIR / "profile_results.json"
_DEFAULT_REPORT_PATH = _SCRIPT_DIR / "report.md"

_TARGETED_SMOKE_CALLS: dict[str, tuple[tuple[str, dict[str, Any], str], ...]] = {
    "Neo4j Cypher": (
        (
            "read_neo4j_cypher",
            {"query": "RETURN 1 AS ok"},
            "Use a trivial read-only Cypher query instead of schema inference.",
        ),
        (
            "get_neo4j_schema",
            {},
            "Fallback to schema introspection when the read tool is unavailable.",
        ),
    ),
    "Milvus MCP": (
        (
            "milvus_list_databases",
            {},
            "Use a metadata-only Milvus smoke call.",
        ),
        (
            "milvus_list_collections",
            {},
            "Fallback to listing collections when database listing is unavailable.",
        ),
    ),
}


@dataclass(slots=True)
class ProfileTarget:
    """One MCP server target loaded from the manifest.

    Args:
        name (`str`):
            Human-readable server name.
        container_name (`str`):
            Docker container name used by the manifest.
        image (`str`):
            Docker image configured in the manifest.
        original_image (`str | None`):
            Optional upstream image name retained in the manifest.
        transport (`str`):
            MCP transport name.
        url (`str`):
            Full MCP endpoint URL.
        port (`int`):
            Host-side HTTP port extracted from the URL.
        endpoint (`str`):
            MCP endpoint path extracted from the URL.
        client_name (`str`):
            MCP client name used by AgentScope.
        docker_run_command (`list[str]`):
            Resolved ``docker run`` command.
        tool_names (`tuple[str, ...]`):
            Tool names declared in the manifest.
        profile_dependencies (`tuple[dict[str, Any], ...]`, optional):
            Optional backend dependencies declared in the manifest.
    """

    name: str
    container_name: str
    image: str
    original_image: str | None
    transport: str
    url: str
    port: int
    endpoint: str
    client_name: str
    docker_run_command: list[str]
    tool_names: tuple[str, ...]
    profile_dependencies: tuple[dict[str, Any], ...] = ()


@dataclass(slots=True)
class MetricSummary:
    """Summary statistics for one latency metric.

    Args:
        avg_ms (`float | None`):
            Arithmetic mean in milliseconds.
        min_ms (`float | None`):
            Minimum in milliseconds.
        max_ms (`float | None`):
            Maximum in milliseconds.
        count (`int`):
            Number of samples contributing to the summary.
    """

    avg_ms: float | None
    min_ms: float | None
    max_ms: float | None
    count: int

    def to_dict(self) -> dict[str, Any]:
        """Convert the summary to a JSON-serializable dictionary.

        Returns:
            `dict[str, Any]`:
                Dictionary form of the summary.
        """

        return {
            "avg_ms": self.avg_ms,
            "min_ms": self.min_ms,
            "max_ms": self.max_ms,
            "count": self.count,
        }


STAGE_METRIC_ORDER = (
    "docker_run_ms",
    "wait_tcp_ms",
    "mcp_handshake_ms",
    "interface_test_ms",
    "total_ms",
)

MILESTONE_METRIC_ORDER = (
    "tcp_ready_elapsed_ms",
    "handshake_elapsed_ms",
    "interface_test_elapsed_ms",
)

METRIC_TIME_ORDER = (
    *STAGE_METRIC_ORDER[:-1],
    *MILESTONE_METRIC_ORDER,
    STAGE_METRIC_ORDER[-1],
)


@dataclass(slots=True)
class DependencyService:
    """One optional backend dependency managed by the profiler.

    Args:
        name (`str`):
            Human-readable dependency name.
        target_names (`tuple[str, ...]`):
            MCP servers that depend on this backend.
        port (`int`):
            Host-side port that indicates readiness.
        startup_timeout (`float`):
            Maximum seconds to wait for readiness.
        start_command (`list[str]`):
            Command used to start the dependency.
        stop_command (`list[str]`):
            Command used to stop the dependency.
        container_name (`str | None`, optional):
            Main container name when one container is used.
        readiness_url (`str | None`, optional):
            Optional HTTP endpoint that must become healthy after port readiness.
    """

    name: str
    target_names: tuple[str, ...]
    port: int
    startup_timeout: float
    start_command: list[str]
    stop_command: list[str]
    container_name: str | None = None
    readiness_url: str | None = None


def load_profile_targets(manifest_path: Path) -> list[ProfileTarget]:
    """Load all prewarm-ready profiling targets from one manifest.

    Args:
        manifest_path (`Path`):
            Path to ``laplace_mcp_manifest.json``.

    Returns:
        `list[ProfileTarget]`:
            Targets in manifest order.
    """

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    targets: list[ProfileTarget] = []
    for server_name, payload in manifest.get("servers", {}).items():
        if not bool(payload.get("ready_for_prewarm", False)):
            continue

        server_config = payload.get("server_config", {})
        url = _resolve_env_placeholders(str(server_config.get("url", "")).strip())
        parsed = urlparse(url)
        if parsed.port is None:
            raise ValueError(
                f"Server '{server_name}' does not expose an HTTP port: {url}",
            )

        targets.append(
            ProfileTarget(
                name=server_name,
                container_name=str(server_config.get("container_name", "")).strip(),
                image=str(server_config.get("image", payload.get("image", ""))).strip(),
                original_image=(
                    str(payload.get("original_image", "")).strip() or None
                ),
                transport=str(server_config.get("transport", "streamable_http")).strip(),
                url=url,
                port=int(parsed.port),
                endpoint=parsed.path or "/mcp",
                client_name=str(server_config.get("client_name", server_name)).strip(),
                docker_run_command=[
                    _resolve_env_placeholders(str(token))
                    for token in payload.get("docker_run_command", [])
                ],
                tool_names=tuple(str(item) for item in payload.get("tool_names", [])),
                profile_dependencies=tuple(
                    {
                        "name": str(item.get("name", "")).strip(),
                        "port": int(item.get("port", 0)),
                        "startup_timeout": float(item.get("startup_timeout", 120.0)),
                        "container_name": str(item.get("container_name", "")).strip()
                        or None,
                        "readiness_url": str(item.get("readiness_url", "")).strip()
                        or None,
                        "start_command": [
                            _resolve_env_placeholders(str(token))
                            for token in item.get("start_command", [])
                        ],
                        "stop_command": [
                            _resolve_env_placeholders(str(token))
                            for token in item.get("stop_command", [])
                        ],
                    }
                    for item in payload.get("profile_dependencies", [])
                    if isinstance(item, dict)
                ),
            ),
        )
    return targets


def _dependency_services_for_targets(
    targets: list[ProfileTarget],
) -> list[DependencyService]:
    """Build dependency bootstrap specs for the selected targets.

    Args:
        targets (`list[ProfileTarget]`):
            Selected profiling targets.

    Returns:
        `list[DependencyService]`:
            Dependencies that should be bootstrapped.
    """

    selected_names = {target.name for target in targets}
    dependencies: list[DependencyService] = []
    for target in targets:
        for spec in target.profile_dependencies:
            dependency_name = str(spec.get("name", "")).strip()
            start_command = [str(token) for token in spec.get("start_command", [])]
            stop_command = [str(token) for token in spec.get("stop_command", [])]
            port = int(spec.get("port", 0))
            if not dependency_name or not start_command or not stop_command or port <= 0:
                continue
            dependencies.append(
                DependencyService(
                    name=dependency_name,
                    target_names=(target.name,),
                    port=port,
                    startup_timeout=float(spec.get("startup_timeout", 120.0)),
                    start_command=start_command,
                    stop_command=stop_command,
                    container_name=spec.get("container_name"),
                    readiness_url=spec.get("readiness_url"),
                ),
            )

    if "Neo4j Cypher" in selected_names:
        dependencies.append(
            DependencyService(
                name="Neo4j",
                target_names=("Neo4j Cypher",),
                port=7687,
                startup_timeout=120.0,
                start_command=[
                    "docker",
                    "run",
                    "-d",
                    "--rm",
                    "--name",
                    "laplace-profile-neo4j",
                    "-p",
                    "7687:7687",
                    "-p",
                    "7474:7474",
                    "-e",
                    "NEO4J_AUTH=neo4j/password",
                    os.environ.get("PROFILE_NEO4J_IMAGE", "neo4j:5"),
                ],
                stop_command=[
                    "docker",
                    "rm",
                    "-f",
                    "laplace-profile-neo4j",
                ],
                container_name="laplace-profile-neo4j",
            ),
        )

    return dependencies


def _is_tcp_port_open(
    host: str,
    port: int,
    timeout: float = 1.0,
) -> bool:
    """Return whether one TCP port is already reachable.

    Args:
        host (`str`):
            Hostname or IP address.
        port (`int`):
            TCP port.
        timeout (`float`, optional):
            Connection timeout in seconds.

    Returns:
        `bool`:
            Whether the port is currently reachable.
    """

    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def _pick_targeted_smoke_tool_and_args(
    target: ProfileTarget,
    tool_specs: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any], str]:
    """Prefer server-specific smoke calls before the generic heuristic.

    Args:
        target (`ProfileTarget`):
            Server target under test.
        tool_specs (`list[dict[str, Any]]`):
            Tool metadata collected from ``list_tools``.

    Returns:
        `tuple[dict[str, Any] | None, dict[str, Any], str]`:
            Selected tool spec, call arguments and diagnostic reason.
    """

    by_name = {str(spec.get("name", "")): spec for spec in tool_specs}
    for tool_name, arguments, reason in _TARGETED_SMOKE_CALLS.get(target.name, ()): 
        selected = by_name.get(tool_name)
        if selected is None:
            continue
        input_schema = selected.get("input_schema") or {}
        required = set(input_schema.get("required", []))
        if not required.issubset(arguments.keys()):
            continue
        return selected, dict(arguments), reason
    return _pick_smoke_tool_and_args(tool_specs)


def compute_metric_summary(values: list[float | None]) -> MetricSummary:
    """Compute average/minimum/maximum over non-null values.

    Args:
        values (`list[float | None]`):
            Raw metric values.

    Returns:
        `MetricSummary`:
            Summary statistics over present values.
    """

    filtered = [float(value) for value in values if value is not None]
    if not filtered:
        return MetricSummary(avg_ms=None, min_ms=None, max_ms=None, count=0)
    return MetricSummary(
        avg_ms=statistics.fmean(filtered),
        min_ms=min(filtered),
        max_ms=max(filtered),
        count=len(filtered),
    )


def _stage_summary(trials: list["TrialMeasurement"], field_name: str) -> MetricSummary:
    """Aggregate one field over successful trials only.

    Args:
        trials (`list[TrialMeasurement]`):
            Trial measurements.
        field_name (`str`):
            Dataclass field name to summarize.

    Returns:
        `MetricSummary`:
            Summary over successful non-null values.
    """

    return compute_metric_summary(
        [
            getattr(trial, field_name)
            for trial in trials
            if trial.status == "pass"
        ],
    )


def _format_ms(value: float | None) -> str:
    """Format one latency value for Markdown and console output.

    Args:
        value (`float | None`):
            Raw value in milliseconds.

    Returns:
        `str`:
            Formatted string.
    """

    if value is None:
        return "-"
    return f"{float(value):.2f}"


@dataclass(slots=True)
class TrialMeasurement:
    """Result of one server cold-start trial.

    Args:
        server_name (`str`):
            Server name.
        trial_index (`int`):
            1-based trial index.
        status (`str`):
            One of ``pass``, ``partial`` or ``fail``.
        cleanup_ms (`float`):
            Time spent removing the previous container.
        docker_run_ms (`float | None`):
            Time spent in detached ``docker run``.
        tcp_ready_wait_ms (`float | None`):
            Wait time until the TCP port opens.
        mcp_handshake_ms (`float | None`):
            Handshake duration for ``list_tools``.
        interface_test_ms (`float | None`):
            Duration of the smoke tool call.
        total_ms (`float`):
            End-to-end elapsed time.
        tcp_ready_elapsed_ms (`float | None`):
            Cumulative elapsed time until TCP ready.
        handshake_elapsed_ms (`float | None`):
            Cumulative elapsed time until handshake success.
        interface_test_elapsed_ms (`float | None`):
            Cumulative elapsed time until smoke completion.
        smoke_attempted (`bool`, optional):
            Whether a smoke call was attempted.
        smoke_tool_name (`str | None`, optional):
            Selected smoke tool name.
        smoke_note (`str | None`, optional):
            Smoke-call note or skip reason.
        diagnostics (`dict[str, Any]`, optional):
            Extra diagnostics collected for the trial.
    """

    server_name: str
    trial_index: int
    status: str
    cleanup_ms: float
    docker_run_ms: float | None
    tcp_ready_wait_ms: float | None
    mcp_handshake_ms: float | None
    interface_test_ms: float | None
    total_ms: float
    tcp_ready_elapsed_ms: float | None
    handshake_elapsed_ms: float | None
    interface_test_elapsed_ms: float | None
    smoke_attempted: bool = False
    smoke_tool_name: str | None = None
    smoke_note: str | None = None
    diagnostics: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the trial to a JSON-serializable dictionary.

        Returns:
            `dict[str, Any]`:
                Dictionary form of the trial.
        """

        return {
            "trial": self.trial_index,
            "server_name": self.server_name,
            "status": self.status,
            "failure_stage": self.diagnostics.get("failure_stage") if self.diagnostics else None,
            "cleanup_ms": self.cleanup_ms,
            "docker_run_ms": self.docker_run_ms,
            "wait_tcp_ms": self.tcp_ready_wait_ms,
            "mcp_handshake_ms": self.mcp_handshake_ms,
            "interface_test_ms": self.interface_test_ms,
            "tcp_ready_elapsed_ms": self.tcp_ready_elapsed_ms,
            "handshake_elapsed_ms": self.handshake_elapsed_ms,
            "interface_test_elapsed_ms": self.interface_test_elapsed_ms,
            "total_ms": self.total_ms,
            "smoke_attempted": self.smoke_attempted,
            "smoke_tool_name": self.smoke_tool_name,
            "smoke_note": self.smoke_note,
            "diagnostics": self.diagnostics or {},
        }


def _summarize_server_trials(trials: list[TrialMeasurement]) -> dict[str, Any]:
    """Aggregate repeated measurements for one server.

    Args:
        trials (`list[TrialMeasurement]`):
            Repeated trial measurements.

    Returns:
        `dict[str, Any]`:
            Summary with counts and metric statistics.
    """

    pass_count = sum(1 for trial in trials if trial.status == "pass")
    partial_count = sum(1 for trial in trials if trial.status == "partial")
    fail_count = sum(1 for trial in trials if trial.status == "fail")
    smoke_attempted_count = sum(1 for trial in trials if trial.smoke_attempted)
    smoke_skipped_count = sum(
        1 for trial in trials if not trial.smoke_attempted and trial.smoke_note
    )
    failure_counts: dict[str, int] = {}
    failure_messages: dict[str, int] = {}
    for trial in trials:
        diagnostics = trial.diagnostics or {}
        failure_stage = diagnostics.get("failure_stage")
        if failure_stage:
            failure_counts[str(failure_stage)] = failure_counts.get(str(failure_stage), 0) + 1
        error = diagnostics.get("error")
        if error:
            failure_messages[str(error)] = failure_messages.get(str(error), 0) + 1

    def _failure_notes() -> list[dict[str, Any]]:
        items = sorted(
            failure_messages.items(),
            key=lambda item: (-item[1], item[0]),
        )
        return [
            {"message": message, "count": count}
            for message, count in items[:5]
        ]

    return {
        "trial_count": len(trials),
        "pass_count": pass_count,
        "partial_count": partial_count,
        "fail_count": fail_count,
        "success_runs": pass_count,
        "partial_runs": partial_count,
        "failed_runs": fail_count,
        "success_rate": pass_count / len(trials) if trials else 0.0,
        "smoke_attempted_count": smoke_attempted_count,
        "smoke_skipped_count": smoke_skipped_count,
        "failure_stages": failure_counts,
        "metrics": {
            "docker_run_ms": compute_metric_summary(
                [trial.docker_run_ms for trial in trials],
            ).to_dict(),
            "wait_tcp_ms": compute_metric_summary(
                [trial.tcp_ready_wait_ms for trial in trials],
            ).to_dict(),
            "tcp_ready_elapsed_ms": compute_metric_summary(
                [trial.tcp_ready_elapsed_ms for trial in trials],
            ).to_dict(),
            "mcp_handshake_ms": compute_metric_summary(
                [trial.mcp_handshake_ms for trial in trials],
            ).to_dict(),
            "handshake_elapsed_ms": compute_metric_summary(
                [trial.handshake_elapsed_ms for trial in trials],
            ).to_dict(),
            "interface_test_ms": compute_metric_summary(
                [trial.interface_test_ms for trial in trials],
            ).to_dict(),
            "interface_test_elapsed_ms": compute_metric_summary(
                [trial.interface_test_elapsed_ms for trial in trials],
            ).to_dict(),
            "total_ms": compute_metric_summary(
                [trial.total_ms for trial in trials],
            ).to_dict(),
        },
        "stage_stats": {
            "docker_run_ms": _stage_summary(trials, "docker_run_ms").to_dict(),
            "tcp_ready_wait_ms": _stage_summary(trials, "tcp_ready_wait_ms").to_dict(),
            "tcp_ready_elapsed_ms": _stage_summary(trials, "tcp_ready_elapsed_ms").to_dict(),
            "mcp_handshake_ms": _stage_summary(trials, "mcp_handshake_ms").to_dict(),
            "handshake_elapsed_ms": _stage_summary(trials, "handshake_elapsed_ms").to_dict(),
            "interface_test_ms": _stage_summary(trials, "interface_test_ms").to_dict(),
            "interface_test_elapsed_ms": _stage_summary(
                trials,
                "interface_test_elapsed_ms",
            ).to_dict(),
            "total_ms": _stage_summary(trials, "total_ms").to_dict(),
        },
        "failure_notes": _failure_notes(),
    }


class MCPServerProfiler:
    """Run repeated cold-start profiling for Laplace MCP servers.

    Args:
        manifest_path (`Path`):
            Path to the Laplace manifest.
        targets (`list[ProfileTarget]`):
            Targets selected for profiling.
        iterations (`int`, optional):
            Number of profiling trials per server.
        startup_timeout (`float`, optional):
            Maximum seconds to wait for TCP port readiness.
        request_timeout (`float`, optional):
            Maximum seconds to wait for MCP handshake and smoke calls.
        startup_interval (`float`, optional):
            Poll interval in seconds while waiting for TCP readiness.
        keep_containers (`bool`, optional):
            Whether to keep the last started container after profiling.
        enable_smoke_call (`bool`, optional):
            Whether to perform a low-risk tool smoke call.
        auto_bootstrap_dependencies (`bool`, optional):
            Whether to auto-start required backend dependencies.
        keep_dependencies (`bool`, optional):
            Whether to leave auto-started backend dependencies running.
    """

    def __init__(
        self,
        manifest_path: Path,
        targets: list[ProfileTarget],
        iterations: int = 10,
        startup_timeout: float = 120.0,
        request_timeout: float = 30.0,
        startup_interval: float = 0.5,
        keep_containers: bool = False,
        enable_smoke_call: bool = True,
        auto_bootstrap_dependencies: bool = True,
        keep_dependencies: bool = False,
    ) -> None:
        """Initialize profiler parameters.

        Args:
            manifest_path (`Path`):
                Path to the Laplace manifest.
            targets (`list[ProfileTarget]`):
                Targets selected for profiling.
            iterations (`int`, optional):
                Number of profiling trials per server.
            startup_timeout (`float`, optional):
                Maximum seconds to wait for TCP port readiness.
            request_timeout (`float`, optional):
                Maximum seconds to wait for MCP handshake and smoke calls.
            startup_interval (`float`, optional):
                Poll interval in seconds while waiting for TCP readiness.
            keep_containers (`bool`, optional):
                Whether to keep the last started container after profiling.
            enable_smoke_call (`bool`, optional):
                Whether to perform a low-risk tool smoke call.
            auto_bootstrap_dependencies (`bool`, optional):
                Whether to auto-start required backend dependencies.
            keep_dependencies (`bool`, optional):
                Whether to leave auto-started backend dependencies running.
        """

        self.manifest_path = manifest_path
        self.targets = list(targets)
        self.iterations = max(1, int(iterations))
        self.startup_timeout = max(1.0, float(startup_timeout))
        self.request_timeout = max(1.0, float(request_timeout))
        self.startup_interval = max(0.1, float(startup_interval))
        self.keep_containers = keep_containers
        self.enable_smoke_call = enable_smoke_call
        self.auto_bootstrap_dependencies = auto_bootstrap_dependencies
        self.keep_dependencies = keep_dependencies

    async def profile_all(self) -> dict[str, Any]:
        """Profile all configured servers sequentially.

        Returns:
            `dict[str, Any]`:
                Full JSON-serializable report.
        """

        started_at = datetime.now(timezone.utc).isoformat()
        server_reports: list[dict[str, Any]] = []
        managed_dependencies: list[DependencyService] = []
        if self.auto_bootstrap_dependencies:
            managed_dependencies = await self._ensure_dependencies()

        try:
            for index, target in enumerate(self.targets, start=1):
                _LOGGER.info(
                    "[profile] %d/%d %s (%d trial(s))",
                    index,
                    len(self.targets),
                    target.name,
                    self.iterations,
                )
                server_reports.append(await self._profile_server(target))
        finally:
            if self.auto_bootstrap_dependencies and not self.keep_dependencies:
                self._teardown_dependencies(managed_dependencies)

        completed_at = datetime.now(timezone.utc).isoformat()
        success_servers = sum(
            1 for server in server_reports if server["summary"]["success_runs"] > 0
        )
        return {
            "summary": {
                "manifest_path": str(self.manifest_path),
                "started_at": started_at,
                "completed_at": completed_at,
                "total_servers": len(server_reports),
                "iterations_per_server": self.iterations,
                "startup_timeout_s": self.startup_timeout,
                "request_timeout_s": self.request_timeout,
                "enable_smoke_call": self.enable_smoke_call,
                "keep_containers": self.keep_containers,
                "auto_bootstrap_dependencies": self.auto_bootstrap_dependencies,
                "keep_dependencies": self.keep_dependencies,
                "managed_dependencies": [dependency.name for dependency in managed_dependencies],
                "servers_with_successes": success_servers,
            },
            "servers": server_reports,
        }

    async def _ensure_dependencies(self) -> list[DependencyService]:
        """Start missing backend services required by selected targets.

        Returns:
            `list[DependencyService]`:
                Dependencies that were started by this profiler instance.
        """

        managed: list[DependencyService] = []
        for dependency in _dependency_services_for_targets(self.targets):
            if _is_tcp_port_open("127.0.0.1", dependency.port):
                _LOGGER.info(
                    "[dependency] Reusing %s on port %d for %s",
                    dependency.name,
                    dependency.port,
                    ", ".join(dependency.target_names),
                )
                continue

            if dependency.container_name:
                self._remove_container_if_exists(dependency.container_name)

            _LOGGER.info(
                "[dependency] Starting %s for %s",
                dependency.name,
                ", ".join(dependency.target_names),
            )
            result = subprocess.run(
                dependency.start_command,
                check=False,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=max(60.0, dependency.startup_timeout),
            )
            if result.returncode != 0:
                hint = ""
                if dependency.name == "Milvus":
                    hint = (
                        " The default backend image is "
                        "laplace/milvus-backend:official-v3.0-beta; set "
                        "PROFILE_MILVUS_IMAGE to another reachable image only "
                        "if you want to override it."
                    )
                raise RuntimeError(
                    f"Failed to start dependency {dependency.name}: "
                    f"{(result.stderr or result.stdout).strip()}{hint}"
                )

            await self._wait_for_port(
                dependency.port,
                dependency.startup_timeout,
                dependency.name,
            )
            if dependency.readiness_url:
                await self._wait_for_http_ready(
                    dependency.readiness_url,
                    dependency.startup_timeout,
                    dependency.name,
                )
            managed.append(dependency)

        return managed

    def _teardown_dependencies(self, dependencies: list[DependencyService]) -> None:
        """Stop dependencies that were auto-started by this profiler.

        Args:
            dependencies (`list[DependencyService]`):
                Dependencies started by the profiler.

        Returns:
            `None`:
                Best-effort teardown.
        """

        for dependency in reversed(dependencies):
            _LOGGER.info("[dependency] Stopping %s", dependency.name)
            try:
                subprocess.run(
                    dependency.stop_command,
                    check=False,
                    capture_output=True,
                    text=True,
                    stdin=subprocess.DEVNULL,
                    timeout=120,
                )
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning(
                    "[dependency] Failed to stop %s: %s",
                    dependency.name,
                    exc,
                )

    async def _profile_server(self, target: ProfileTarget) -> dict[str, Any]:
        """Profile one server across repeated trials.

        Args:
            target (`ProfileTarget`):
                Server target under test.

        Returns:
            `dict[str, Any]`:
                Per-server report.
        """

        trials: list[TrialMeasurement] = []
        for trial_index in range(1, self.iterations + 1):
            _LOGGER.info(
                "[profile] %s trial %d/%d",
                target.name,
                trial_index,
                self.iterations,
            )
            trials.append(await self._profile_trial(target, trial_index))

        if not self.keep_containers:
            self._remove_container_if_exists(target.container_name)

        return {
            "server_name": target.name,
            "container_name": target.container_name,
            "image": target.image,
            "original_image": target.original_image,
            "transport": target.transport,
            "url": target.url,
            "tool_names": list(target.tool_names),
            "summary": _summarize_server_trials(trials),
            "trials": [trial.to_dict() for trial in trials],
        }

    async def _profile_trial(
        self,
        target: ProfileTarget,
        trial_index: int,
    ) -> TrialMeasurement:
        """Run one cold-start profiling trial.

        Args:
            target (`ProfileTarget`):
                Server target under test.
            trial_index (`int`):
                1-based trial index.

        Returns:
            `TrialMeasurement`:
                Raw trial result with stage timings and diagnostics.
        """

        diagnostics: dict[str, Any] = {}
        run_started_at = time.perf_counter()

        cleanup_started_at = time.perf_counter()
        self._remove_container_if_exists(target.container_name)
        cleanup_ms = (time.perf_counter() - cleanup_started_at) * 1000.0

        docker_run_ms: float | None = None
        tcp_ready_wait_ms: float | None = None
        mcp_handshake_ms: float | None = None
        interface_test_ms: float | None = None
        tcp_ready_elapsed_ms: float | None = None
        handshake_elapsed_ms: float | None = None
        interface_test_elapsed_ms: float | None = None
        smoke_attempted = False
        smoke_tool_name: str | None = None
        smoke_note: str | None = None
        status = "fail"

        try:
            docker_started_at = time.perf_counter()
            run_result = subprocess.run(
                target.docker_run_command,
                check=False,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=max(30.0, self.startup_timeout),
            )
            docker_run_ms = (time.perf_counter() - docker_started_at) * 1000.0
            diagnostics["docker_run_stdout"] = (run_result.stdout or "").strip()
            diagnostics["docker_run_stderr"] = (run_result.stderr or "").strip()
            diagnostics["docker_run_returncode"] = run_result.returncode
            diagnostics["failure_stage"] = None
            if run_result.returncode != 0:
                diagnostics["failure_stage"] = "docker_run"
                raise RuntimeError(
                    f"docker run failed with code {run_result.returncode}: "
                    f"{(run_result.stderr or run_result.stdout).strip()}"
                )

            tcp_started_at = time.perf_counter()
            await self._wait_for_tcp(target.port)
            tcp_ready_wait_ms = (time.perf_counter() - tcp_started_at) * 1000.0
            tcp_ready_elapsed_ms = (time.perf_counter() - run_started_at) * 1000.0

            handshake_started_at = time.perf_counter()
            tools = await self._wait_for_mcp_ready(target)
            mcp_handshake_ms = (time.perf_counter() - handshake_started_at) * 1000.0
            handshake_elapsed_ms = (time.perf_counter() - run_started_at) * 1000.0
            diagnostics["tool_count"] = len(tools)

            if self.enable_smoke_call:
                interface_started_at = time.perf_counter()
                smoke_attempted, smoke_note, smoke_tool_name = await self._smoke_call(
                    target,
                    tools,
                )
                interface_test_ms = (time.perf_counter() - interface_started_at) * 1000.0
                interface_test_elapsed_ms = (time.perf_counter() - run_started_at) * 1000.0
                diagnostics["smoke_note"] = smoke_note
                diagnostics["smoke_tool_name"] = smoke_tool_name
                if smoke_attempted:
                    status = "pass"
                else:
                    diagnostics["failure_stage"] = "interface_test"
                    status = "partial"
            else:
                status = "pass"
        except Exception as exc:  # noqa: BLE001
            diagnostics["error"] = f"{type(exc).__name__}: {exc}"
            if diagnostics.get("failure_stage") is None:
                if tcp_ready_wait_ms is None:
                    diagnostics["failure_stage"] = "tcp_ready"
                elif mcp_handshake_ms is None:
                    diagnostics["failure_stage"] = "mcp_handshake"
                else:
                    diagnostics["failure_stage"] = "interface_test"
        finally:
            if not self.keep_containers:
                self._remove_container_if_exists(target.container_name)

        return TrialMeasurement(
            server_name=target.name,
            trial_index=trial_index,
            status=status,
            cleanup_ms=cleanup_ms,
            docker_run_ms=docker_run_ms,
            tcp_ready_wait_ms=tcp_ready_wait_ms,
            mcp_handshake_ms=mcp_handshake_ms,
            interface_test_ms=interface_test_ms,
            total_ms=(time.perf_counter() - run_started_at) * 1000.0,
            tcp_ready_elapsed_ms=tcp_ready_elapsed_ms,
            handshake_elapsed_ms=handshake_elapsed_ms,
            interface_test_elapsed_ms=interface_test_elapsed_ms,
            smoke_attempted=smoke_attempted,
            smoke_tool_name=smoke_tool_name,
            smoke_note=smoke_note,
            diagnostics=diagnostics,
        )

    async def _wait_for_tcp(self, port: int) -> None:
        """Wait until a local TCP port accepts connections.

        Args:
            port (`int`):
                Host-side TCP port.

        Returns:
            `None`:
                Returns once the TCP probe succeeds.
        """

        await self._wait_for_port(port, self.startup_timeout, f"TCP port {port}")

    async def _wait_for_port(
        self,
        port: int,
        timeout_seconds: float,
        label: str,
    ) -> None:
        """Wait until one local TCP port accepts connections.

        Args:
            port (`int`):
                Host-side TCP port.
            timeout_seconds (`float`):
                Maximum seconds to wait.
            label (`str`):
                Human-readable label for timeout diagnostics.

        Returns:
            `None`:
                Returns once the TCP probe succeeds.
        """

        loop = asyncio.get_running_loop()
        deadline = loop.time() + max(1.0, timeout_seconds)
        while loop.time() < deadline:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection("127.0.0.1", int(port)),
                    timeout=min(5.0, max(1.0, timeout_seconds)),
                )
                del reader
                writer.close()
                await writer.wait_closed()
                return
            except Exception:  # noqa: BLE001
                await asyncio.sleep(self.startup_interval)

        raise TimeoutError(f"Timed out waiting for {label}")

    async def _wait_for_http_ready(
        self,
        url: str,
        timeout_seconds: float,
        label: str,
    ) -> None:
        """Wait until one HTTP health endpoint returns a successful response.

        Args:
            url (`str`):
                Health endpoint URL.
            timeout_seconds (`float`):
                Maximum seconds to wait.
            label (`str`):
                Human-readable dependency label.

        Returns:
            `None`:
                Returns once the endpoint replies with one 2xx/3xx response.
        """

        loop = asyncio.get_running_loop()
        deadline = loop.time() + max(1.0, timeout_seconds)
        while loop.time() < deadline:
            try:
                status_code = await asyncio.to_thread(self._http_status_code, url)
                if 200 <= status_code < 400:
                    return
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(self.startup_interval)

        raise TimeoutError(f"Timed out waiting for {label} health endpoint: {url}")

    @staticmethod
    def _http_status_code(url: str) -> int:
        """Return one HTTP status code for a health probe URL.

        Args:
            url (`str`):
                Health endpoint URL.

        Returns:
            `int`:
                HTTP status code.
        """

        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310
            return int(getattr(response, "status", 200))

    async def _list_tools(self, target: ProfileTarget) -> list[Any]:
        """Perform the MCP ``list_tools`` handshake.

        Args:
            target (`ProfileTarget`):
                Server target under test.

        Returns:
            `list[Any]`:
                Discovered tool list.
        """

        client = HttpStatelessClient(
            name=target.client_name,
            transport=target.transport,
            url=target.url,
            timeout=self.request_timeout,
        )
        return await asyncio.wait_for(
            client.list_tools(),
            timeout=self.request_timeout,
        )

    async def _wait_for_mcp_ready(self, target: ProfileTarget) -> list[Any]:
        """Wait until MCP ``list_tools`` succeeds after TCP becomes reachable.

        Args:
            target (`ProfileTarget`):
                Server target under test.

        Returns:
            `list[Any]`:
                Discovered tool list.

        Raises:
            `RuntimeError`:
                Raised when MCP handshake never succeeds before timeout.
        """

        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.startup_timeout
        last_error: Exception | None = None
        while loop.time() < deadline:
            try:
                return await self._list_tools(target)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                await asyncio.sleep(self.startup_interval)

        message = f"Timed out waiting for MCP readiness at {target.url}"
        if last_error is not None:
            raise RuntimeError(message) from last_error
        raise RuntimeError(message)

    async def _smoke_call(
        self,
        target: ProfileTarget,
        tools: list[Any],
    ) -> tuple[bool, str, str | None]:
        """Perform one low-risk MCP tool call when possible.

        Args:
            target (`ProfileTarget`):
                Server target under test.
            tools (`list[Any]`):
                Tools returned by ``list_tools``.

        Returns:
            `tuple[bool, str, str | None]`:
                Success flag, diagnostic note and selected tool name.
        """

        tool_specs = [
            {
                "name": getattr(tool, "name", ""),
                "input_schema": getattr(tool, "inputSchema", {}) or {},
            }
            for tool in tools
        ]
        selected, arguments, reason = _pick_targeted_smoke_tool_and_args(
            target,
            tool_specs,
        )
        if selected is None:
            return False, f"No low-risk smoke tool available: {reason}", None

        client = HttpStatelessClient(
            name=target.client_name,
            transport=target.transport,
            url=target.url,
            timeout=self.request_timeout,
        )
        fn = await client.get_callable_function(
            func_name=str(selected["name"]),
            wrap_tool_result=True,
            execution_timeout=self.request_timeout,
        )
        await asyncio.wait_for(fn(**arguments), timeout=self.request_timeout)
        return True, f"Smoke tool called: {selected['name']}", str(selected["name"])

    @staticmethod
    def _remove_container_if_exists(container_name: str) -> None:
        """Remove one Docker container if it exists.

        Args:
            container_name (`str`):
                Docker container name.

        Returns:
            `None`:
                The operation is best-effort.
        """

        if not container_name:
            return
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                check=False,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=30,
            )
        except Exception:  # noqa: BLE001
            return


def build_markdown_report(report: dict[str, Any]) -> str:
    """Render a Markdown profiling report.

    Args:
        report (`dict[str, Any]`):
            JSON-style profiling report.

    Returns:
        `str`:
            Markdown report text.
    """

    lines: list[str] = []
    summary = report["summary"]
    servers = report["servers"]

    lines.append("# MCP Server Profile Report")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(f"- Manifest: {summary['manifest_path']}")
    lines.append(f"- Started: {summary['started_at']}")
    lines.append(f"- Completed: {summary['completed_at']}")
    lines.append(f"- Servers: {summary['total_servers']}")
    lines.append(f"- Iterations per server: {summary['iterations_per_server']}")
    lines.append(f"- TCP startup timeout: {summary['startup_timeout_s']} s")
    lines.append(f"- MCP request timeout: {summary['request_timeout_s']} s")
    lines.append(f"- Smoke call enabled: {summary['enable_smoke_call']}")
    lines.append(
        f"- Dependency bootstrap enabled: {summary.get('auto_bootstrap_dependencies', True)}",
    )
    lines.append(
        f"- Managed dependencies: {', '.join(summary.get('managed_dependencies', [])) or '-'}",
    )
    lines.append("")
    lines.append("## Summary Table")
    lines.append("")
    lines.append(
        "| Server | Success | Partial | Fail | Total Avg (ms) | Launch Avg (ms) | Port Wait Avg (ms) | Handshake Avg (ms) | Interface Avg (ms) |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for server in servers:
        metrics = server["summary"]["metrics"]
        lines.append(
            "| {name} | {success} | {partial} | {fail} | {total} | {launch} | {port} | {handshake} | {interface} |".format(
                name=server["server_name"],
                success=server["summary"]["success_runs"],
                partial=server["summary"]["partial_runs"],
                fail=server["summary"]["failed_runs"],
                total=_format_ms(metrics["total_ms"]["avg_ms"]),
                launch=_format_ms(metrics["docker_run_ms"]["avg_ms"]),
                port=_format_ms(metrics["wait_tcp_ms"]["avg_ms"]),
                handshake=_format_ms(metrics["mcp_handshake_ms"]["avg_ms"]),
                interface=_format_ms(metrics["interface_test_ms"]["avg_ms"]),
            ),
        )

    for server in servers:
        lines.append("")
        lines.append(f"## {server['server_name']}")
        lines.append("")
        lines.append(f"- Container: {server['container_name']}")
        lines.append(f"- Image: {server['image']}")
        if server.get("original_image"):
            lines.append(f"- Original image: {server['original_image']}")
        lines.append(f"- URL: {server['url']}")
        lines.append(
            f"- Success / Partial / Fail: {server['summary']['success_runs']} / {server['summary']['partial_runs']} / {server['summary']['failed_runs']}",
        )
        if server["summary"].get("failure_stages"):
            lines.append(
                f"- Failure stages: {json.dumps(server['summary']['failure_stages'], ensure_ascii=False)}",
            )
        lines.append("")
        lines.append("### Metric Stats")
        lines.append("")
        lines.append("| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |")
        lines.append("| --- | ---: | ---: | ---: | ---: |")
        metrics = server["summary"]["metrics"]
        for metric_name in STAGE_METRIC_ORDER:
            metric = metrics.get(metric_name)
            if metric is None:
                continue
            lines.append(
                "| {metric_name} | {avg} | {min_v} | {max_v} | {count} |".format(
                    metric_name=metric_name,
                    avg=_format_ms(metric["avg_ms"]),
                    min_v=_format_ms(metric["min_ms"]),
                    max_v=_format_ms(metric["max_ms"]),
                    count=metric["count"],
                ),
            )
        lines.append("")
        milestone_metrics = [
            (metric_name, metrics.get(metric_name))
            for metric_name in MILESTONE_METRIC_ORDER
            if metrics.get(metric_name) is not None
        ]
        if milestone_metrics:
            lines.append("### Milestones")
            lines.append("")
            lines.append("| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |")
            lines.append("| --- | ---: | ---: | ---: | ---: |")
            for metric_name, metric in milestone_metrics:
                lines.append(
                    "| {metric_name} | {avg} | {min_v} | {max_v} | {count} |".format(
                        metric_name=metric_name,
                        avg=_format_ms(metric["avg_ms"]),
                        min_v=_format_ms(metric["min_ms"]),
                        max_v=_format_ms(metric["max_ms"]),
                        count=metric["count"],
                    ),
                )
            lines.append("")
        lines.append("### Trial Results")
        lines.append("")
        lines.append(
            "| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |"
        )
        lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |")
        for trial in server["trials"]:
            lines.append(
                "| {trial} | {status} | {failure_stage} | {total} | {launch} | {port} | {handshake} | {interface} | {smoke_tool} |".format(
                    trial=trial["trial"],
                    status=trial["status"],
                    failure_stage=trial.get("failure_stage") or "-",
                    total=_format_ms(trial.get("total_ms")),
                    launch=_format_ms(trial.get("docker_run_ms")),
                    port=_format_ms(trial.get("wait_tcp_ms")),
                    handshake=_format_ms(trial.get("mcp_handshake_ms")),
                    interface=_format_ms(trial.get("interface_test_ms")),
                    smoke_tool=trial.get("smoke_tool_name") or "-",
                ),
            )

    lines.append("")
    return "\n".join(lines)


def _build_report(report_payload: dict[str, Any]) -> str:
    """Backward-compatible alias used by tests.

    Args:
        report_payload (`dict[str, Any]`):
            JSON-style profiling report.

    Returns:
        `str`:
            Markdown report text.
    """

    if "server_summaries" in report_payload:
        summary = report_payload["metadata"]
        servers = []
        for server_name, server_summary in report_payload["server_summaries"].items():
            servers.append(
                {
                    "server_name": server_name,
                    "container_name": "-",
                    "image": "-",
                    "original_image": None,
                    "url": "-",
                    "summary": {
                        "success_runs": server_summary["pass_count"],
                        "partial_runs": server_summary["partial_count"],
                        "failed_runs": server_summary["fail_count"],
                        "failure_stages": {},
                        "metrics": {
                            "docker_run_ms": {
                                "avg_ms": server_summary["stage_stats"]["docker_run_ms"]["average_ms"],
                                "min_ms": server_summary["stage_stats"]["docker_run_ms"]["minimum_ms"],
                                "max_ms": server_summary["stage_stats"]["docker_run_ms"]["maximum_ms"],
                                "count": server_summary["stage_stats"]["docker_run_ms"]["count"],
                            },
                            "wait_tcp_ms": {
                                "avg_ms": server_summary["stage_stats"]["tcp_ready_wait_ms"]["average_ms"],
                                "min_ms": server_summary["stage_stats"]["tcp_ready_wait_ms"]["minimum_ms"],
                                "max_ms": server_summary["stage_stats"]["tcp_ready_wait_ms"]["maximum_ms"],
                                "count": server_summary["stage_stats"]["tcp_ready_wait_ms"]["count"],
                            },
                            "tcp_ready_elapsed_ms": {
                                "avg_ms": server_summary["stage_stats"]["tcp_ready_elapsed_ms"]["average_ms"],
                                "min_ms": server_summary["stage_stats"]["tcp_ready_elapsed_ms"]["minimum_ms"],
                                "max_ms": server_summary["stage_stats"]["tcp_ready_elapsed_ms"]["maximum_ms"],
                                "count": server_summary["stage_stats"]["tcp_ready_elapsed_ms"]["count"],
                            },
                            "mcp_handshake_ms": {
                                "avg_ms": server_summary["stage_stats"]["mcp_handshake_ms"]["average_ms"],
                                "min_ms": server_summary["stage_stats"]["mcp_handshake_ms"]["minimum_ms"],
                                "max_ms": server_summary["stage_stats"]["mcp_handshake_ms"]["maximum_ms"],
                                "count": server_summary["stage_stats"]["mcp_handshake_ms"]["count"],
                            },
                            "handshake_elapsed_ms": {
                                "avg_ms": server_summary["stage_stats"]["handshake_elapsed_ms"]["average_ms"],
                                "min_ms": server_summary["stage_stats"]["handshake_elapsed_ms"]["minimum_ms"],
                                "max_ms": server_summary["stage_stats"]["handshake_elapsed_ms"]["maximum_ms"],
                                "count": server_summary["stage_stats"]["handshake_elapsed_ms"]["count"],
                            },
                            "interface_test_ms": {
                                "avg_ms": server_summary["stage_stats"]["interface_test_ms"]["average_ms"],
                                "min_ms": server_summary["stage_stats"]["interface_test_ms"]["minimum_ms"],
                                "max_ms": server_summary["stage_stats"]["interface_test_ms"]["maximum_ms"],
                                "count": server_summary["stage_stats"]["interface_test_ms"]["count"],
                            },
                            "interface_test_elapsed_ms": {
                                "avg_ms": server_summary["stage_stats"]["interface_test_elapsed_ms"]["average_ms"],
                                "min_ms": server_summary["stage_stats"]["interface_test_elapsed_ms"]["minimum_ms"],
                                "max_ms": server_summary["stage_stats"]["interface_test_elapsed_ms"]["maximum_ms"],
                                "count": server_summary["stage_stats"]["interface_test_elapsed_ms"]["count"],
                            },
                            "total_ms": {
                                "avg_ms": server_summary["stage_stats"]["total_ms"]["average_ms"],
                                "min_ms": server_summary["stage_stats"]["total_ms"]["minimum_ms"],
                                "max_ms": server_summary["stage_stats"]["total_ms"]["maximum_ms"],
                                "count": server_summary["stage_stats"]["total_ms"]["count"],
                            },
                        },
                    },
                    "trials": [],
                },
            )
        report_payload = {
            "summary": {
                "manifest_path": summary["manifest_path"],
                "started_at": summary["generated_at_utc"],
                "completed_at": summary["generated_at_utc"],
                "total_servers": summary["server_count"],
                "iterations_per_server": summary["repeats"],
                "startup_timeout_s": summary["tcp_ready_timeout_seconds"],
                "request_timeout_s": summary["request_timeout_seconds"],
                "enable_smoke_call": True,
            },
            "servers": servers,
        }
    return build_markdown_report(report_payload)


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments.

    Returns:
        `argparse.Namespace`:
            Parsed command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description="Profile Laplace MCP server cold-start and readiness latency.",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=_DEFAULT_MANIFEST_PATH,
        help="Path to laplace_mcp_manifest.json.",
    )
    parser.add_argument(
        "--servers",
        nargs="*",
        help="Optional subset of server names to profile.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=10,
        help="Number of profiling trials per server.",
    )
    parser.add_argument(
        "--startup-timeout",
        type=float,
        default=120.0,
        help="Seconds to wait for TCP port readiness.",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=30.0,
        help="Seconds to wait for MCP handshake and smoke calls.",
    )
    parser.add_argument(
        "--startup-interval",
        type=float,
        default=0.5,
        help="TCP readiness polling interval in seconds.",
    )
    parser.add_argument(
        "--disable-smoke-call",
        action="store_true",
        help="Disable post-handshake low-risk tool smoke call.",
    )
    parser.add_argument(
        "--keep-containers",
        action="store_true",
        help="Keep the last started container for each server after profiling.",
    )
    parser.add_argument(
        "--disable-dependency-bootstrap",
        action="store_true",
        help="Do not auto-start Neo4j and Milvus backend dependencies.",
    )
    parser.add_argument(
        "--keep-dependencies",
        action="store_true",
        help="Keep auto-started backend dependencies running after profiling.",
    )
    parser.add_argument(
        "--results-path",
        type=Path,
        default=_DEFAULT_RESULTS_PATH,
        help="Path for JSON profiling output.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=_DEFAULT_REPORT_PATH,
        help="Path for Markdown report output.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console log level.",
    )
    return parser.parse_args()


async def _run() -> int:
    """Run the CLI workflow.

    Returns:
        `int`:
            Process exit code.
    """

    args = _parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )

    targets = load_profile_targets(args.manifest_path)
    if args.servers:
        wanted = {item.strip() for item in args.servers if item.strip()}
        known = {target.name for target in targets}
        unknown = sorted(wanted - known)
        if unknown:
            raise ValueError(f"Unknown server name(s): {', '.join(unknown)}")
        targets = [target for target in targets if target.name in wanted]

    profiler = MCPServerProfiler(
        manifest_path=args.manifest_path,
        targets=targets,
        iterations=args.iterations,
        startup_timeout=args.startup_timeout,
        request_timeout=args.request_timeout,
        startup_interval=args.startup_interval,
        keep_containers=args.keep_containers,
        enable_smoke_call=not args.disable_smoke_call,
        auto_bootstrap_dependencies=not args.disable_dependency_bootstrap,
        keep_dependencies=args.keep_dependencies,
    )
    report = await profiler.profile_all()

    args.results_path.parent.mkdir(parents=True, exist_ok=True)
    args.results_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(
        build_markdown_report(report),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "manifest_path": str(args.manifest_path),
                "total_servers": report["summary"]["total_servers"],
                "iterations_per_server": report["summary"]["iterations_per_server"],
                "results_path": str(args.results_path),
                "report_path": str(args.report_path),
            },
            indent=2,
            ensure_ascii=False,
        ),
    )
    return 0


def main() -> int:
    """CLI entrypoint.

    Returns:
        `int`:
            Process exit code.
    """

    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
