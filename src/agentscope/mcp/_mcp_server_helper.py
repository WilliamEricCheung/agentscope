# -*- coding: utf-8 -*-
"""Helpers for managing local MCP servers started by Docker."""
import asyncio
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .. import _config
from ._http_stateless_client import HttpStatelessClient
from ._mcp_function import MCPToolFunction
from ..tracing import trace
from ..tracing._setup import _get_tracer
from .._logging import logger


_DEFAULT_IDLE_STOP_SECONDS = 60.0 * 2
_DEFAULT_IDLE_REMOVE_SECONDS = 60.0 * 5
_LIFECYCLE_CHECK_INTERVAL_SECONDS = 30.0
_MCP_LIFECYCLE_SPAN_NAME = "mcp.lifecycle.metrics"
_MCP_TIMING_SPAN_NAME = "mcp.execution.timing"


@dataclass
class _ContainerLifecycleState:
    """The in-memory lifecycle state for one MCP container.

    Args:
        created_at (`float`):
            Monotonic timestamp when the lifecycle state was created.
        last_used_at (`float`):
            Monotonic timestamp of the last usage.
        stop_after_seconds (`float`):
            Idle time threshold to stop the container.
        remove_after_seconds (`float`):
            Idle time threshold to remove the container.
        in_use (`int`):
            Active tool call count that is currently using the container.
        bound_clients (`set[str]`):
            Distinct MCP client names associated with this container.
        owner_pids (`set[int]`):
            Process ids that recently touched this lifecycle state. This is
            used by the external daemon to reclaim stale `in_use` counters
            after an agent process exits unexpectedly.

    Returns:
        `None`:
            This dataclass stores runtime state only.
    """

    created_at: float
    last_used_at: float
    stop_after_seconds: float
    remove_after_seconds: float
    in_use: int = 0
    bound_clients: set[str] = field(default_factory=set)
    owner_pids: set[int] = field(default_factory=set)


class _ManagedMCPToolFunction(MCPToolFunction):
    """MCP tool function wrapper that tracks active container usage."""

    def __init__(
        self,
        container_name: str,
        client_name: str,
        tool_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize the managed MCP tool function.

        Args:
            container_name (`str`):
                The Docker container name associated with this tool.
            client_name (`str`):
                The MCP client name associated with this tool.
            tool_name (`str`):
                The MCP tool name.
            *args (`Any`):
                Positional arguments forwarded to `MCPToolFunction`.
            **kwargs (`Any`):
                Keyword arguments forwarded to `MCPToolFunction`.
        """
        super().__init__(*args, **kwargs)
        self.container_name = container_name
        self.client_name = client_name
        self.tool_name = tool_name

    async def __call__(
        self,
        **kwargs: Any,
    ) -> Any:
        """Call the MCP tool function directly.

        .. note:: Lifecycle usage enter/exit is orchestrated by toolkit level
         wrappers to ensure expected tracing order.
        """
        return await super().__call__(**kwargs)


class _ManagedHttpStatelessClient(HttpStatelessClient):
    """HTTP stateless MCP client with active usage tracking."""

    def __init__(
        self,
        container_name: str,
        startup_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the managed HTTP stateless MCP client.

        Args:
            container_name (`str`):
                The Docker container name associated with this client.
            startup_mode (`str | None`, optional):
                The startup mode observed when ensuring the container, such as
                `cold`, `resume`, or `running`.
            **kwargs (`Any`):
                Keyword arguments forwarded to `HttpStatelessClient`.
        """
        super().__init__(**kwargs)
        self.container_name = container_name
        self.startup_mode = startup_mode

    async def get_callable_function(
        self,
        func_name: str,
        wrap_tool_result: bool = True,
        execution_timeout: float | None = None,
    ) -> MCPToolFunction:
        """Get a managed MCP tool function bound to this container."""
        if self._tools is None:
            await self.list_tools()

        target_tool = None
        for tool in self._tools:
            if tool.name == func_name:
                target_tool = tool
                break

        if target_tool is None:
            raise ValueError(
                f"Tool '{func_name}' not found in the MCP server ",
            )

        return _ManagedMCPToolFunction(
            container_name=self.container_name,
            client_name=self.name,
            tool_name=target_tool.name,
            mcp_name=self.name,
            tool=target_tool,
            wrap_tool_result=wrap_tool_result,
            client_gen=self.get_client,
            timeout=execution_timeout,
        )


_CONTAINER_LIFECYCLE_STATES: dict[str, _ContainerLifecycleState] = {}
_CONTAINER_LIFECYCLE_LOCK = asyncio.Lock()
_CONTAINER_LIFECYCLE_TASK: asyncio.Task | None = None
_LIFECYCLE_STATE_DIR_NAME = "mcp_lifecycle"
_DAEMON_PID_FILE_NAME = "daemon.pid"


def _get_lifecycle_state_dir() -> str:
    """Get the directory used for persisted MCP lifecycle state files.

    The default location is the repository-local directory
    ``laplace/mcp_lifecycle`` so users can inspect the daemon state directly.
    Set ``AGENTSCOPE_MCP_LIFECYCLE_DIR`` to override this location.

    Returns:
        `str`:
            The absolute state directory path.
    """
    configured_path = os.getenv("AGENTSCOPE_MCP_LIFECYCLE_DIR")
    if configured_path:
        path = Path(configured_path).expanduser().resolve()
    else:
        repo_root = Path(__file__).resolve().parents[3]
        path = repo_root / "laplace" / _LIFECYCLE_STATE_DIR_NAME

    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def _get_container_state_path(container_name: str) -> str:
    """Get the persisted JSON file path for one container state.

    Args:
        container_name (`str`):
            The Docker container name.

    Returns:
        `str`:
            The JSON state file path.
    """
    safe_name = container_name.replace(os.sep, "_").replace(":", "_")
    return os.path.join(_get_lifecycle_state_dir(), f"{safe_name}.json")


def _get_daemon_pid_file() -> str:
    """Get the PID file path for the external MCP lifecycle daemon.

    Returns:
        `str`:
            The daemon PID file path.
    """
    return os.path.join(_get_lifecycle_state_dir(), _DAEMON_PID_FILE_NAME)


def _persist_container_lifecycle_state(
    container_name: str,
    state: _ContainerLifecycleState,
) -> None:
    """Persist one container lifecycle state for cross-process management.

    Args:
        container_name (`str`):
            The Docker container name.
        state (`_ContainerLifecycleState`):
            The lifecycle state snapshot.

    Returns:
        `None`:
            The state is written atomically to disk.
    """
    state_path = _get_container_state_path(container_name)
    temp_path = f"{state_path}.tmp"
    payload = {
        "container_name": container_name,
        "created_at": state.created_at,
        "last_used_at": state.last_used_at,
        "stop_after_seconds": state.stop_after_seconds,
        "remove_after_seconds": state.remove_after_seconds,
        "in_use": state.in_use,
        "bound_clients": sorted(state.bound_clients),
        "owner_pids": sorted(state.owner_pids),
    }
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    os.replace(temp_path, state_path)


def _remove_persisted_container_state(container_name: str) -> None:
    """Remove one persisted lifecycle state file if it exists.

    Args:
        container_name (`str`):
            The Docker container name.

    Returns:
        `None`:
            The state file is removed when present.
    """
    state_path = _get_container_state_path(container_name)
    if os.path.exists(state_path):
        os.remove(state_path)


def _load_persisted_lifecycle_states() -> dict[str, _ContainerLifecycleState]:
    """Load all persisted lifecycle states from disk.

    Returns:
        `dict[str, _ContainerLifecycleState]`:
            The loaded lifecycle states keyed by container name.
    """
    states: dict[str, _ContainerLifecycleState] = {}
    state_dir = _get_lifecycle_state_dir()

    for file_name in os.listdir(state_dir):
        if not file_name.endswith(".json"):
            continue

        file_path = os.path.join(state_dir, file_name)
        try:
            with open(file_path, encoding="utf-8") as file:
                payload = json.load(file)

            container_name = str(payload["container_name"])
            states[container_name] = _ContainerLifecycleState(
                created_at=float(payload["created_at"]),
                last_used_at=float(payload["last_used_at"]),
                stop_after_seconds=float(payload["stop_after_seconds"]),
                remove_after_seconds=float(payload["remove_after_seconds"]),
                in_use=int(payload.get("in_use", 0)),
                bound_clients=set(payload.get("bound_clients", [])),
                owner_pids={int(_) for _ in payload.get("owner_pids", [])},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to load persisted MCP lifecycle state from '%s': %s",
                file_path,
                exc,
            )

    return states


def _is_process_alive(pid: int) -> bool:
    """Check whether a process id is still alive.

    Args:
        pid (`int`):
            The process id to check.

    Returns:
        `bool`:
            Whether the process appears to be alive.
    """
    if pid <= 0:
        return False

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _touch_state_owner(
    state: _ContainerLifecycleState,
    now: float,
    owner_pid: int | None = None,
) -> None:
    """Record that a live agent process currently owns this lifecycle state.

    Args:
        state (`_ContainerLifecycleState`):
            The lifecycle state to update.
        now (`float`):
            Current monotonic timestamp.
        owner_pid (`int | None`, optional):
            The process id to record. Defaults to the current process.

    Returns:
        `None`:
            The state is updated in place.
    """
    owner_pid = owner_pid if owner_pid is not None else os.getpid()
    state.owner_pids.add(owner_pid)
    state.last_used_at = now


async def _load_persisted_lifecycle_states_into_memory() -> None:
    """Load persisted lifecycle states into the current process memory.

    Returns:
        `None`:
            The in-memory lifecycle registry is refreshed from disk.
    """
    async with _CONTAINER_LIFECYCLE_LOCK:
        _CONTAINER_LIFECYCLE_STATES.clear()
        _CONTAINER_LIFECYCLE_STATES.update(_load_persisted_lifecycle_states())


def _write_daemon_pid_file() -> None:
    """Write the current process id to the MCP daemon PID file."""
    with open(_get_daemon_pid_file(), "w", encoding="utf-8") as file:
        file.write(str(os.getpid()))


def _remove_daemon_pid_file() -> None:
    """Remove the MCP daemon PID file if it exists."""
    pid_file = _get_daemon_pid_file()
    if os.path.exists(pid_file):
        os.remove(pid_file)


def _read_daemon_pid_file() -> int | None:
    """Read the MCP daemon PID file if available.

    Returns:
        `int | None`:
            The daemon pid, or `None` when unavailable.
    """
    pid_file = _get_daemon_pid_file()
    if not os.path.exists(pid_file):
        return None

    try:
        with open(pid_file, encoding="utf-8") as file:
            return int(file.read().strip())
    except Exception:  # noqa: BLE001
        return None


def _ensure_mcp_lifecycle_daemon() -> None:
    """Ensure the external MCP lifecycle daemon is running in background.

    Returns:
        `None`:
            A detached daemon process is started when needed.
    """
    if os.getenv("AGENTSCOPE_MCP_DAEMON_ENABLED", "true").lower() in {
        "0",
        "false",
        "no",
        "off",
    }:
        return

    if os.getenv("AGENTSCOPE_MCP_DAEMON_PROCESS") == "1":
        return

    existing_pid = _read_daemon_pid_file()
    if existing_pid is not None and _is_process_alive(existing_pid):
        return

    daemon_env = {
        **os.environ,
        "AGENTSCOPE_MCP_DAEMON_PROCESS": "1",
    }
    popen_kwargs: dict[str, Any] = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "env": daemon_env,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = (
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
    else:
        popen_kwargs["start_new_session"] = True

    subprocess.Popen(
        [sys.executable, "-m", "agentscope.mcp._mcp_daemon"],
        **popen_kwargs,
    )


@trace(name="mcp.lifecycle.run_daemon_once")
async def _run_mcp_lifecycle_daemon_once(
    current_time: float | None = None,
) -> None:
    """Run one external-daemon lifecycle tick using persisted state.

    Args:
        current_time (`float | None`, optional):
            Optional current monotonic time for testing.

    Returns:
        `None`:
            Persisted lifecycle states are loaded and processed once.
    """
    await _load_persisted_lifecycle_states_into_memory()
    await _run_container_lifecycle_once(current_time=current_time)


async def _run_mcp_lifecycle_daemon_forever(
    poll_interval_seconds: float | None = None,
) -> None:
    """Run the MCP lifecycle daemon loop in a standalone process.

    Args:
        poll_interval_seconds (`float | None`, optional):
            Poll interval override in seconds.

    Returns:
        `None`:
            The daemon loop runs until the process exits.
    """
    poll_interval_seconds = (
        poll_interval_seconds
        if poll_interval_seconds is not None
        else _LIFECYCLE_CHECK_INTERVAL_SECONDS
    )
    _write_daemon_pid_file()
    logger.info(
        "Started AgentScope MCP lifecycle daemon (pid=%s).",
        os.getpid(),
    )
    try:
        while True:
            await _run_mcp_lifecycle_daemon_once()
            await asyncio.sleep(poll_interval_seconds)
    finally:
        _remove_daemon_pid_file()


def _get_idle_thresholds() -> tuple[float, float]:
    """Get idle stop/remove thresholds from environment.

    Returns:
        `tuple[float, float]`:
            The stop-after and remove-after thresholds in seconds.
    """

    stop_after = float(
        os.getenv("MCP_CONTAINER_IDLE_STOP_SECONDS", _DEFAULT_IDLE_STOP_SECONDS),
    )
    remove_after = float(
        os.getenv(
            "MCP_CONTAINER_IDLE_REMOVE_SECONDS",
            _DEFAULT_IDLE_REMOVE_SECONDS,
        ),
    )

    if stop_after <= 0:
        stop_after = _DEFAULT_IDLE_STOP_SECONDS
    if remove_after <= stop_after:
        remove_after = max(_DEFAULT_IDLE_REMOVE_SECONDS, stop_after + 60.0)

    return stop_after, remove_after


def _record_startup_time_to_span(
    container_name: str,
    startup_mode: str,
    startup_time_ms: float,
) -> None:
    """Record startup timing metrics to the current tracing span.

    Args:
        container_name (`str`):
            The Docker container name.
        startup_mode (`str`):
            The startup mode, e.g., `cold` or `resume`.
        startup_time_ms (`float`):
            Startup time in milliseconds.

    Returns:
        `None`:
            Span attributes are set when tracing span is active.
    """
    _record_lifecycle_snapshot_to_span(
        event="container_startup",
        container_name=container_name,
        startup_mode=startup_mode,
        startup_time_ms=startup_time_ms,
    )


def _build_lifecycle_attributes(
    event: str,
    container_name: str,
    state: _ContainerLifecycleState | None = None,
    startup_mode: str | None = None,
    startup_time_ms: float | None = None,
    idle_time_ms: float | None = None,
    age_ms: float | None = None,
    usage_duration_ms: float | None = None,
    usage_client_name: str | None = None,
    usage_tool_name: str | None = None,
) -> dict[str, str | int | float]:
    """Build standardized lifecycle tracing attributes."""

    attributes: dict[str, str | int | float] = {
        "mcp.lifecycle.event": event,
        "mcp.lifecycle.container.name": container_name,
    }

    if state is not None:
        attributes.update(
            {
                "mcp.lifecycle.container.in_use": state.in_use,
                "mcp.lifecycle.container.created_at_monotonic_s": (
                    state.created_at
                ),
                "mcp.lifecycle.container.last_used_at_monotonic_s": (
                    state.last_used_at
                ),
                "mcp.lifecycle.threshold.stop_after_ms": (
                    state.stop_after_seconds * 1000.0
                ),
                "mcp.lifecycle.threshold.remove_after_ms": (
                    state.remove_after_seconds * 1000.0
                ),
                "mcp.lifecycle.binding.client_count": len(state.bound_clients),
                "mcp.lifecycle.owner.pid_count": len(state.owner_pids),
            },
        )

        if state.bound_clients:
            attributes["mcp.lifecycle.binding.clients"] = ",".join(
                sorted(state.bound_clients),
            )
        if state.owner_pids:
            attributes["mcp.lifecycle.owner.pids"] = ",".join(
                str(pid) for pid in sorted(state.owner_pids)
            )

    if startup_mode is not None:
        attributes["mcp.lifecycle.startup.mode"] = startup_mode
    if startup_time_ms is not None:
        attributes["mcp.lifecycle.startup.duration_ms"] = startup_time_ms
    if idle_time_ms is not None:
        attributes["mcp.lifecycle.idle.duration_ms"] = idle_time_ms
    if age_ms is not None:
        attributes["mcp.lifecycle.container.age_ms"] = age_ms
    if usage_duration_ms is not None:
        attributes["mcp.lifecycle.usage.duration_ms"] = usage_duration_ms
    if usage_client_name is not None:
        attributes["mcp.lifecycle.usage.client_name"] = usage_client_name
    if usage_tool_name is not None:
        attributes["mcp.lifecycle.usage.tool_name"] = usage_tool_name

    return attributes


def _record_lifecycle_snapshot_to_span(
    event: str,
    container_name: str,
    state: _ContainerLifecycleState | None = None,
    startup_mode: str | None = None,
    startup_time_ms: float | None = None,
    idle_time_ms: float | None = None,
    age_ms: float | None = None,
    usage_duration_ms: float | None = None,
    usage_client_name: str | None = None,
    usage_tool_name: str | None = None,
) -> None:
    """Record a standardized lifecycle snapshot to tracing span."""
    if not _config.trace_enabled:
        return

    tracer = _get_tracer()
    with tracer.start_as_current_span(
        name=_MCP_LIFECYCLE_SPAN_NAME,
        attributes=_build_lifecycle_attributes(
            event=event,
            container_name=container_name,
            state=state,
            startup_mode=startup_mode,
            startup_time_ms=startup_time_ms,
            idle_time_ms=idle_time_ms,
            age_ms=age_ms,
            usage_duration_ms=usage_duration_ms,
            usage_client_name=usage_client_name,
            usage_tool_name=usage_tool_name,
        ),
    ):
        return


def _create_mcp_timing_run(
    task_description: str,
    prewarm: bool,
) -> dict[str, Any]:
    """Create one timing context for an MCP-driven worker execution.

    Args:
        task_description (`str`):
            The task passed into the worker.
        prewarm (`bool`):
            Whether prompt-level speculative pre-warming is enabled.

    Returns:
        `dict[str, Any]`:
            Mutable timing context for recording step-level events.
    """
    return {
        "run_id": f"worker-{int(time.time() * 1000)}",
        "task_description": task_description,
        "prewarm": prewarm,
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "events": [],
        "_started_perf": time.perf_counter(),
    }


def _record_mcp_timing_event(
    timing_run: dict[str, Any],
    step: str,
    **metadata: Any,
) -> None:
    """Record one MCP timing event to in-memory context and tracing spans.

    Args:
        timing_run (`dict[str, Any]`):
            The mutable timing context created by
            :func:`_create_mcp_timing_run`.
        step (`str`):
            The step name to record.
        **metadata (`Any`):
            Optional structured fields such as `group_name`, `tool_name`, or
            `candidate`.

    Returns:
        `None`:
            The event is appended to the timing context in place.
    """
    elapsed_ms = round(
        (time.perf_counter() - timing_run["_started_perf"]) * 1000,
        3,
    )
    event = {
        "step": step,
        "elapsed_ms": elapsed_ms,
        **metadata,
    }
    timing_run.setdefault("events", []).append(event)

    if not _config.trace_enabled:
        return

    attributes: dict[str, str | bool | int | float] = {
        "mcp.timing.event": step,
        "mcp.timing.run_id": timing_run.get("run_id", "unknown"),
        "mcp.timing.prewarm": bool(timing_run.get("prewarm", False)),
        "mcp.timing.elapsed_ms": elapsed_ms,
    }
    for key, value in metadata.items():
        if isinstance(value, (str, bool, int, float)):
            attributes[f"mcp.timing.{key}"] = value

    for key, value in _build_mcp_timing_summary(timing_run).items():
        if value is not None:
            attributes[f"mcp.timing.summary.{key}"] = value

    tracer = _get_tracer()
    with tracer.start_as_current_span(
        name=_MCP_TIMING_SPAN_NAME,
        attributes=attributes,
    ):
        return


def _build_mcp_timing_summary(
    timing_run: dict[str, Any],
) -> dict[str, str | float | bool | int | None]:
    """Summarize key MCP execution latencies from recorded timing events.

    Args:
        timing_run (`dict[str, Any]`):
            The timing context with recorded events.

    Returns:
        `dict[str, str | float | bool | int | None]`:
            A compact latency and effectiveness summary.
    """

    events = timing_run.get("events", [])

    def _first_elapsed(step: str) -> float | None:
        for event in events:
            if event.get("step") == step:
                return float(event["elapsed_ms"])
        return None

    def _normalize_startup_mode(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if text in {"", "None", "null"}:
            return None
        return text

    activation_ms = _first_elapsed("tool_group_activation_requested")
    ready_ms = _first_elapsed("mcp_server_ready")
    prewarm_started_ms = _first_elapsed("prewarm_candidate_started")
    prewarm_ready_ms = _first_elapsed("prewarm_candidate_finished")

    startup_mode = None
    for event in reversed(events):
        if event.get("step") in {
            "prewarm_candidate_finished",
            "mcp_server_ready",
        } and event.get("startup_mode") is not None:
            startup_mode = _normalize_startup_mode(event.get("startup_mode"))
            break

    prewarm_router_method = None
    for event in reversed(events):
        router_method = event.get("router_method")
        if router_method is not None:
            prewarm_router_method = str(router_method).strip() or None
            break

    router_candidates: list[str] = []
    for event in events:
        if event.get("step") != "prewarm_router_matched":
            continue
        if event.get("candidates"):
            router_candidates.extend(
                [
                    _.strip()
                    for _ in str(event["candidates"]).split(",")
                    if _.strip()
                ],
            )
        elif event.get("candidate"):
            router_candidates.append(str(event["candidate"]).strip())

    router_candidates = list(dict.fromkeys(router_candidates))
    prewarm_router_matched = None
    prewarm_router_candidate_count = None
    if prewarm_router_method is not None:
        prewarm_router_matched = bool(router_candidates)
        prewarm_router_candidate_count = len(router_candidates)

    effective_candidates: list[str] = []
    effective_modes: list[str] = []
    for event in events:
        if event.get("step") != "prewarm_candidate_finished":
            continue
        event_startup_mode = _normalize_startup_mode(event.get("startup_mode"))
        effective = event.get("effective")
        if effective is None:
            effective = event_startup_mode in {"cold", "resume"}
        if effective:
            candidate = str(event.get("candidate", "")).strip()
            if candidate:
                effective_candidates.append(candidate)
            if event_startup_mode is not None:
                effective_modes.append(event_startup_mode)

    effective_candidates = list(dict.fromkeys(effective_candidates))
    effective_modes = list(dict.fromkeys(effective_modes))
    prewarm_effective = None
    prewarm_effective_candidate_count = None
    if prewarm_router_method is not None:
        prewarm_effective = bool(effective_candidates)
        prewarm_effective_candidate_count = len(effective_candidates)

    return {
        "startup_mode": startup_mode,
        "prewarm_router_method": prewarm_router_method,
        "prewarm_router_matched": prewarm_router_matched,
        "prewarm_router_candidate_count": prewarm_router_candidate_count,
        "prewarm_router_candidates": (
            ",".join(router_candidates) if router_candidates else None
        ),
        "prewarm_effective": prewarm_effective,
        "prewarm_effective_candidate_count": (
            prewarm_effective_candidate_count
        ),
        "prewarm_effective_candidates": (
            ",".join(effective_candidates) if effective_candidates else None
        ),
        "prewarm_effective_startup_modes": (
            ",".join(effective_modes) if effective_modes else None
        ),
        "time_to_prewarm_start_ms": prewarm_started_ms,
        "prewarm_duration_ms": (
            round(prewarm_ready_ms - prewarm_started_ms, 3)
            if prewarm_started_ms is not None and prewarm_ready_ms is not None
            else None
        ),
        "prewarm_ready_before_activation_ms": (
            round(activation_ms - prewarm_ready_ms, 3)
            if activation_ms is not None and prewarm_ready_ms is not None
            else None
        ),
        "wait_for_mcp_ready_after_activation_ms": (
            round(ready_ms - activation_ms, 3)
            if activation_ms is not None and ready_ms is not None
            else None
        ),
    }


def _save_mcp_timing_log(
    timing_run: dict[str, Any],
    log_path: str,
) -> str:
    """Persist one timing record into a JSONL log file.

    Args:
        timing_run (`dict[str, Any]`):
            The timing context with recorded events.
        log_path (`str`):
            The output JSONL file path.

    Returns:
        `str`:
            The same log path for downstream reporting.
    """
    serializable = {
        key: value
        for key, value in timing_run.items()
        if not key.startswith("_")
    }
    serializable["summary"] = _build_mcp_timing_summary(timing_run)

    with open(log_path, "a", encoding="utf-8") as file:
        file.write(json.dumps(serializable, ensure_ascii=False) + "\n")

    return log_path


@trace(name="mcp.bind_container_client")
async def _bind_container_client(
    container_name: str,
    client_name: str | None = None,
) -> None:
    """Bind client/tool names to a container lifecycle state."""
    loop = asyncio.get_running_loop()
    now = loop.time()
    async with _CONTAINER_LIFECYCLE_LOCK:
        state = _ensure_lifecycle_state(container_name, now)
        _touch_state_owner(state, now)
        if client_name is not None:
            state.bound_clients.add(client_name)
        _persist_container_lifecycle_state(container_name, state)
        _record_lifecycle_snapshot_to_span(
            event="binding_update",
            container_name=container_name,
            state=state,
            usage_client_name=client_name,
        )


def _ensure_lifecycle_state(
    container_name: str,
    now: float,
) -> _ContainerLifecycleState:
    """Ensure lifecycle state exists for a managed container."""
    existing_state = _CONTAINER_LIFECYCLE_STATES.get(container_name)
    stop_after, remove_after = _get_idle_thresholds()

    if existing_state is not None:
        return existing_state

    state = _ContainerLifecycleState(
        created_at=now,
        last_used_at=now,
        stop_after_seconds=stop_after,
        remove_after_seconds=remove_after,
        in_use=0,
    )
    _CONTAINER_LIFECYCLE_STATES[container_name] = state
    return state


async def _resolve_container_name_by_client(
    client_name: str,
) -> str | None:
    """Resolve one container name by client name from lifecycle state.

    Args:
        client_name (`str`):
            The MCP client name.

    Returns:
        `str | None`:
            The resolved container name, or `None` if not found.
    """
    async with _CONTAINER_LIFECYCLE_LOCK:
        matches = [
            container_name
            for container_name, state in _CONTAINER_LIFECYCLE_STATES.items()
            if client_name in state.bound_clients
        ]

    if not matches:
        return None

    if len(matches) > 1:
        logger.warning(
            "Found multiple containers for client '%s': %s. "
            "Using the first one.",
            client_name,
            matches,
        )

    return sorted(matches)[0]


@trace(name="mcp.lifecycle.enter")
async def _enter_container_usage_by_client(
    client_name: str,
    tool_name: str | None = None,
) -> tuple[str | None, float | None]:
    """Enter container usage by resolving container from client name.

    Args:
        client_name (`str`):
            The MCP client name.
        tool_name (`str | None`, optional):
            The MCP tool name.

    Returns:
        `tuple[str | None, float | None]`:
            The resolved container name and enter timestamp.
    """
    container_name = await _resolve_container_name_by_client(client_name)
    if container_name is None:
        return None, None

    entered_at_s = await _enter_container_usage(
        container_name=container_name,
        client_name=client_name,
        tool_name=tool_name,
    )
    return container_name, entered_at_s


@trace(name="mcp.lifecycle.exit")
async def _exit_container_usage_by_client(
    client_name: str,
    container_name: str | None = None,
    tool_name: str | None = None,
    entered_at_s: float | None = None,
) -> None:
    """Exit container usage by client name.

    Args:
        client_name (`str`):
            The MCP client name.
        container_name (`str | None`, optional):
            The resolved container name from enter stage.
        tool_name (`str | None`, optional):
            The MCP tool name.
        entered_at_s (`float | None`, optional):
            The enter timestamp for duration calculation.
    """
    if container_name is None:
        container_name = await _resolve_container_name_by_client(client_name)

    if container_name is None:
        return

    await _exit_container_usage(
        container_name=container_name,
        client_name=client_name,
        tool_name=tool_name,
        entered_at_s=entered_at_s,
    )


async def _enter_container_usage(
    container_name: str,
    client_name: str | None = None,
    tool_name: str | None = None,
) -> float:
    """Increase the active usage counter for a managed container."""
    global _CONTAINER_LIFECYCLE_TASK

    loop = asyncio.get_running_loop()
    now = loop.time()

    async with _CONTAINER_LIFECYCLE_LOCK:
        state = _ensure_lifecycle_state(container_name, now)
        _touch_state_owner(state, now)
        state.in_use += 1
        _persist_container_lifecycle_state(container_name, state)
        _record_lifecycle_snapshot_to_span(
            event="usage_enter",
            container_name=container_name,
            state=state,
            usage_client_name=client_name,
            usage_tool_name=tool_name,
        )

        if _CONTAINER_LIFECYCLE_TASK is None or _CONTAINER_LIFECYCLE_TASK.done():
            _CONTAINER_LIFECYCLE_TASK = asyncio.create_task(
                _lifecycle_daemon_loop(),
            )

        return now


async def _exit_container_usage(
    container_name: str,
    client_name: str | None = None,
    tool_name: str | None = None,
    entered_at_s: float | None = None,
) -> None:
    """Decrease the active usage counter and refresh last-used time."""
    loop = asyncio.get_running_loop()
    now = loop.time()
    usage_duration_ms = None
    if entered_at_s is not None:
        usage_duration_ms = max(0.0, (now - entered_at_s) * 1000.0)

    async with _CONTAINER_LIFECYCLE_LOCK:
        state = _ensure_lifecycle_state(container_name, now)
        _touch_state_owner(state, now)
        if state.in_use == 0:
            logger.warning(
                "Container '%s' usage counter is already zero on exit.",
                container_name,
            )
        else:
            state.in_use -= 1
        state.last_used_at = now
        _persist_container_lifecycle_state(container_name, state)
        _record_lifecycle_snapshot_to_span(
            event="usage_exit",
            container_name=container_name,
            state=state,
            usage_duration_ms=usage_duration_ms,
            usage_client_name=client_name,
            usage_tool_name=tool_name,
        )


@trace(name="mcp.stop_container")
async def _stop_container(container_name: str) -> None:
    """Stop a running Docker container.

    Args:
        container_name (`str`):
            The Docker container name.

    Returns:
        `None`:
            The target container is stopped.
    """

    return_code, _, stderr = await _run_command(
        ["docker", "stop", container_name],
    )
    if return_code != 0:
        raise RuntimeError(
            f"Failed to stop MCP container '{container_name}': {stderr}",
        )


@trace(name="mcp.track_container_usage")
async def _track_container_usage(container_name: str) -> None:
    """Track the last usage time of one managed MCP container.

    Args:
        container_name (`str`):
            The Docker container name.

    Returns:
        `None`:
            The in-memory usage timestamp is updated.
    """

    global _CONTAINER_LIFECYCLE_TASK

    loop = asyncio.get_running_loop()
    now = loop.time()
    async with _CONTAINER_LIFECYCLE_LOCK:
        existing_state = _ensure_lifecycle_state(container_name, now)
        stop_after, remove_after = _get_idle_thresholds()
        _touch_state_owner(existing_state, now)
        existing_state.stop_after_seconds = stop_after
        existing_state.remove_after_seconds = remove_after
        _persist_container_lifecycle_state(container_name, existing_state)
        _record_lifecycle_snapshot_to_span(
            event="usage_track",
            container_name=container_name,
            state=existing_state,
        )

        if _CONTAINER_LIFECYCLE_TASK is None or _CONTAINER_LIFECYCLE_TASK.done():
            _CONTAINER_LIFECYCLE_TASK = asyncio.create_task(
                _lifecycle_daemon_loop(),
            )


@trace(name="mcp.run_container_lifecycle_once")
async def _run_container_lifecycle_once(current_time: float | None = None) -> None:
    """Run one lifecycle management tick for tracked containers.

    Args:
        current_time (`float | None`, optional):
            Monotonic current time. If `None`, obtain from event loop.

    Returns:
        `None`:
            Containers can be stopped/removed according to idle thresholds.
    """

    loop = asyncio.get_running_loop()
    now = current_time if current_time is not None else loop.time()

    async with _CONTAINER_LIFECYCLE_LOCK:
        states = list(_CONTAINER_LIFECYCLE_STATES.items())

    to_untrack = set()
    for container_name, state in states:
        try:
            live_owner_pids = {
                pid for pid in state.owner_pids if _is_process_alive(pid)
            }
            if live_owner_pids != state.owner_pids:
                state.owner_pids = live_owner_pids
                if not live_owner_pids and state.in_use > 0:
                    logger.info(
                        "Recovered stale lifecycle ownership for MCP container '%s' "
                        "after agent process exit.",
                        container_name,
                    )
                    state.in_use = 0
                    _record_lifecycle_snapshot_to_span(
                        event="owner_process_missing",
                        container_name=container_name,
                        state=state,
                    )
                _persist_container_lifecycle_state(container_name, state)

            if state.in_use > 0:
                continue

            idle_seconds = now - state.last_used_at
            age_seconds = now - state.created_at

            exists, is_running = await _get_container_status(container_name)
            if not exists:
                to_untrack.add(container_name)
                _remove_persisted_container_state(container_name)
                continue

            if idle_seconds >= state.remove_after_seconds:
                await _remove_container_if_exists(container_name)
                _record_lifecycle_snapshot_to_span(
                    event="container_removed",
                    container_name=container_name,
                    state=state,
                    idle_time_ms=idle_seconds * 1000.0,
                    age_ms=age_seconds * 1000.0,
                )
                logger.info(
                    "Removed MCP container '%s' after idle %.1fs (age %.1fs).",
                    container_name,
                    idle_seconds,
                    age_seconds,
                )
                to_untrack.add(container_name)
                _remove_persisted_container_state(container_name)
                continue

            if idle_seconds >= state.stop_after_seconds:
                if is_running:
                    await _stop_container(container_name)
                    _record_lifecycle_snapshot_to_span(
                        event="container_stopped",
                        container_name=container_name,
                        state=state,
                        idle_time_ms=idle_seconds * 1000.0,
                        age_ms=age_seconds * 1000.0,
                    )
                    logger.info(
                        "Stopped MCP container '%s' after idle %.1fs (age %.1fs).",
                        container_name,
                        idle_seconds,
                        age_seconds,
                    )

            _persist_container_lifecycle_state(container_name, state)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed lifecycle management for MCP container '%s': %s",
                container_name,
                exc,
            )

    if to_untrack:
        async with _CONTAINER_LIFECYCLE_LOCK:
            for container_name in to_untrack:
                _CONTAINER_LIFECYCLE_STATES.pop(container_name, None)
                _remove_persisted_container_state(container_name)


@trace(name="mcp.lifecycle_daemon_loop")
async def _lifecycle_daemon_loop() -> None:
    """Background loop for MCP container idle lifecycle management."""

    global _CONTAINER_LIFECYCLE_TASK

    try:
        while True:
            await asyncio.sleep(_LIFECYCLE_CHECK_INTERVAL_SECONDS)
            await _run_container_lifecycle_once()

            async with _CONTAINER_LIFECYCLE_LOCK:
                if not _CONTAINER_LIFECYCLE_STATES:
                    _CONTAINER_LIFECYCLE_TASK = None
                    return
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("MCP lifecycle daemon stopped unexpectedly: %s", exc)
        async with _CONTAINER_LIFECYCLE_LOCK:
            _CONTAINER_LIFECYCLE_TASK = None


@dataclass(frozen=True)
class _DockerMCPServerConfig:
    """The configuration for a local MCP Docker server.

    Args:
        container_name (`str`):
            The Docker container name.
        image (`str`):
            The Docker image name.
        transport (`str`):
            The MCP transport type.
        url (`str`):
            The MCP endpoint URL.
        client_name (`str`):
            The MCP client name.
        startup_timeout (`float`, optional):
            The timeout in seconds while waiting for the server to become
            available.
        startup_interval (`float`, optional):
            The retry interval in seconds while waiting for the server.

    Returns:
        `None`:
            This dataclass stores configuration only.
    """

    container_name: str
    image: str
    transport: str
    url: str
    client_name: str
    startup_timeout: float = 45.0
    startup_interval: float = 1.0


async def _run_command(
    command: list[str],
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """Run a subprocess command asynchronously.

    Args:
        command (`list[str]`):
            The command and arguments to execute.
        env (`dict[str, str] | None`, optional):
            The environment variables for the subprocess.

    Returns:
        `tuple[int, str, str]`:
            The return code, stdout, and stderr.
    """
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await process.communicate()
    return (
        process.returncode,
        stdout.decode("utf-8", errors="replace").strip(),
        stderr.decode("utf-8", errors="replace").strip(),
    )


async def _get_container_status(container_name: str) -> tuple[bool, bool]:
    """Inspect whether a Docker container exists and is running.

    This helper intentionally uses a single ``docker inspect`` call so callers
    that need both pieces of information can avoid duplicated subprocess work.

    Args:
        container_name (`str`):
            The Docker container name.

    Returns:
        `tuple[bool, bool]`:
            A tuple ``(exists, is_running)``.
    """
    return_code, stdout, _ = await _run_command(
        ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
    )
    if return_code != 0 or stdout not in {"true", "false"}:
        return False, False
    return True, stdout == "true"


async def _container_exists(container_name: str) -> bool:
    """Check whether a Docker container exists.

    Args:
        container_name (`str`):
            The Docker container name.

    Returns:
        `bool`:
            Whether the container exists.
    """
    exists, _ = await _get_container_status(container_name)
    return exists


async def _is_container_running(container_name: str) -> bool:
    """Check whether a Docker container is running.

    Args:
        container_name (`str`):
            The Docker container name.

    Returns:
        `bool`:
            Whether the container is running.
    """
    _, is_running = await _get_container_status(container_name)
    return is_running


async def _restart_container(container_name: str) -> None:
    """Restart an existing Docker container.

    Args:
        container_name (`str`):
            The Docker container name.

    Returns:
        `None`:
            The target container is restarted.
    """
    return_code, _, stderr = await _run_command(
        ["docker", "restart", container_name],
    )
    if return_code != 0:
        raise RuntimeError(
            f"Failed to restart MCP container '{container_name}': {stderr}",
        )


async def _remove_container_if_exists(container_name: str) -> None:
    """Remove a Docker container if it exists.

    Args:
        container_name (`str`):
            The Docker container name.

    Returns:
        `None`:
            The container is removed when present.
    """
    await _run_command(["docker", "rm", "-f", container_name])


@trace(name="mcp.wait_for_server")
async def _wait_for_mcp_server(
    config: _DockerMCPServerConfig,
    headers: dict[str, str] | None = None,
) -> None:
    """Wait until an MCP server is reachable and lists tools.

    Args:
        config (`_DockerMCPServerConfig`):
            The MCP server configuration.
        headers (`dict[str, str] | None`, optional):
            Extra HTTP headers for the MCP client.

    Returns:
        `None`:
            The function returns once the server is ready.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + config.startup_timeout
    last_error = ""

    while loop.time() < deadline:
        try:
            client = HttpStatelessClient(
                name=config.client_name,
                transport=config.transport,
                url=config.url,
                headers=headers,
                timeout=5,
            )
            await client.list_tools()
            return
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            await asyncio.sleep(config.startup_interval)

    raise RuntimeError(
        f"Timed out waiting for MCP server '{config.container_name}' at "
        f"{config.url}. Last error: {last_error}",
    )


@trace(name="mcp.ensure_local_docker_server")
async def _ensure_local_docker_mcp_server(
    config: _DockerMCPServerConfig,
    docker_run_command: list[str],
    headers: dict[str, str] | None = None,
) -> HttpStatelessClient:
    """Ensure a local MCP Docker container is running and reachable.

    Args:
        config (`_DockerMCPServerConfig`):
            The MCP server configuration.
        docker_run_command (`list[str]`):
            The docker run command used for cold start.
        headers (`dict[str, str] | None`, optional):
            Extra HTTP headers for the MCP client.

    Returns:
        `HttpStatelessClient`:
            The connected MCP client configuration ready to be registered.
    """
    return await _ensure_local_docker_mcp_server_impl(
        config=config,
        docker_run_command=docker_run_command,
        headers=headers,
        track_usage=True,
    )


@trace(name="mcp.speculative_ensure_local_docker_server")
async def _speculative_ensure_local_docker_mcp_server(
    config: _DockerMCPServerConfig,
    docker_run_command: list[str],
    headers: dict[str, str] | None = None,
) -> HttpStatelessClient:
    """Warm up a local MCP Docker server without formal usage tracking.

    This API is intended for prompt-level or stream-level speculative
    pre-warming. It ensures the container is started/restarted and reachable,
    but does not emit formal usage tracking events.

    Args:
        config (`_DockerMCPServerConfig`):
            The MCP server configuration.
        docker_run_command (`list[str]`):
            The docker run command used for cold start.
        headers (`dict[str, str] | None`, optional):
            Extra HTTP headers for the MCP client.

    Returns:
        `HttpStatelessClient`:
            A connected MCP client for the warmed server.
    """
    return await _ensure_local_docker_mcp_server_impl(
        config=config,
        docker_run_command=docker_run_command,
        headers=headers,
        track_usage=False,
    )


async def _ensure_local_docker_mcp_server_impl(
    config: _DockerMCPServerConfig,
    docker_run_command: list[str],
    headers: dict[str, str] | None,
    track_usage: bool,
) -> HttpStatelessClient:
    """Internal shared ensure implementation with optional usage tracking.

    Args:
        config (`_DockerMCPServerConfig`):
            The MCP server configuration.
        docker_run_command (`list[str]`):
            The docker run command used for cold start.
        headers (`dict[str, str] | None`):
            Extra HTTP headers for the MCP client.
        track_usage (`bool`):
            Whether to update formal usage tracking timestamps.

    Returns:
        `HttpStatelessClient`:
            The connected MCP client configuration ready to be registered.
    """
    loop = asyncio.get_running_loop()
    startup_mode = "running"
    startup_started_at = None

    container_exists, is_running = await _get_container_status(
        config.container_name,
    )
    if container_exists:
        if not is_running:
            startup_mode = "resume"
            startup_started_at = loop.time()
            await _restart_container(config.container_name)
        else:
            _record_lifecycle_snapshot_to_span(
                event="container_already_running",
                container_name=config.container_name,
                startup_mode=startup_mode,
                usage_client_name=config.client_name,
            )
    else:
        startup_mode = "cold"
        startup_started_at = loop.time()
        return_code, _, stderr = await _run_command(docker_run_command)
        if return_code != 0:
            raise RuntimeError(
                f"Failed to start MCP container '{config.container_name}': "
                f"{stderr}",
            )

    try:
        await _wait_for_mcp_server(config, headers=headers)
    except Exception:  # noqa: BLE001
        exists_after_failure, _ = await _get_container_status(
            config.container_name,
        )
        if exists_after_failure:
            await _remove_container_if_exists(config.container_name)

        # Container recreation behaves like a cold start from image.
        startup_mode = "cold"
        startup_started_at = loop.time()
        return_code, _, stderr = await _run_command(docker_run_command)
        if return_code != 0:
            raise RuntimeError(
                f"Failed to recreate MCP container '{config.container_name}': "
                f"{stderr}",
            )
        await _wait_for_mcp_server(config, headers=headers)

    if startup_started_at is not None:
        startup_time_ms = (loop.time() - startup_started_at) * 1000.0
        _record_startup_time_to_span(
            container_name=config.container_name,
            startup_mode=startup_mode,
            startup_time_ms=startup_time_ms,
        )
    else:
        _record_lifecycle_snapshot_to_span(
            event="container_startup",
            container_name=config.container_name,
            startup_mode=startup_mode,
            startup_time_ms=0.0,
            usage_client_name=config.client_name,
        )

    if track_usage:
        await _track_container_usage(config.container_name)
    else:
        _record_lifecycle_snapshot_to_span(
            event="speculative_warmup_ready",
            container_name=config.container_name,
            usage_client_name=config.client_name,
        )

    await _bind_container_client(
        container_name=config.container_name,
        client_name=config.client_name,
    )
    _ensure_mcp_lifecycle_daemon()

    return _ManagedHttpStatelessClient(
        container_name=config.container_name,
        startup_mode=startup_mode,
        name=config.client_name,
        transport=config.transport,
        url=config.url,
        headers=headers,
    )