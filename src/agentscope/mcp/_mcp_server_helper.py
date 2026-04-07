# -*- coding: utf-8 -*-
"""Helpers for managing local MCP servers started by Docker."""
import asyncio
import os
from dataclasses import dataclass, field
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

    def __init__(self, container_name: str, **kwargs: Any) -> None:
        """Initialize the managed HTTP stateless MCP client.

        Args:
            container_name (`str`):
                The Docker container name associated with this client.
            **kwargs (`Any`):
                Keyword arguments forwarded to `HttpStatelessClient`.
        """
        super().__init__(**kwargs)
        self.container_name = container_name

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
            },
        )

        if state.bound_clients:
            attributes["mcp.lifecycle.binding.clients"] = ",".join(
                sorted(state.bound_clients),
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
        if client_name is not None:
            state.bound_clients.add(client_name)
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
        state.in_use += 1
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
        if state.in_use == 0:
            logger.warning(
                "Container '%s' usage counter is already zero on exit.",
                container_name,
            )
        else:
            state.in_use -= 1
        state.last_used_at = now
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
        existing_state.last_used_at = now
        existing_state.stop_after_seconds = stop_after
        existing_state.remove_after_seconds = remove_after
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
            if state.in_use > 0:
                continue

            idle_seconds = now - state.last_used_at
            age_seconds = now - state.created_at

            if not await _container_exists(container_name):
                to_untrack.add(container_name)
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
                continue

            if idle_seconds >= state.stop_after_seconds:
                if await _is_container_running(container_name):
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


async def _container_exists(container_name: str) -> bool:
    """Check whether a Docker container exists.

    Args:
        container_name (`str`):
            The Docker container name.

    Returns:
        `bool`:
            Whether the container exists.
    """
    return_code, _, _ = await _run_command(
        ["docker", "inspect", container_name],
    )
    return return_code == 0


async def _is_container_running(container_name: str) -> bool:
    """Check whether a Docker container is running.

    Args:
        container_name (`str`):
            The Docker container name.

    Returns:
        `bool`:
            Whether the container is running.
    """
    return_code, stdout, _ = await _run_command(
        ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
    )
    return return_code == 0 and stdout == "true"


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
    startup_mode = "none"
    startup_started_at = None

    container_exists = await _container_exists(config.container_name)
    if container_exists:
        if not await _is_container_running(config.container_name):
            startup_mode = "resume"
            startup_started_at = loop.time()
            await _restart_container(config.container_name)
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
        if await _container_exists(config.container_name):
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

    return _ManagedHttpStatelessClient(
        container_name=config.container_name,
        name=config.client_name,
        transport=config.transport,
        url=config.url,
        headers=headers,
    )