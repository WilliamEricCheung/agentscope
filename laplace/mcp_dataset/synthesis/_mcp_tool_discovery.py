"""MCP tool discovery helpers for local synthesis workflows."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from ._server_config import ServerConfig

_logger = logging.getLogger(__name__)


def _import_agentscope_mcp() -> tuple[Any, Any]:
    """Import AgentScope MCP clients with a local source fallback.

    Returns:
        `tuple[Any, Any]`:
            The `StdIOStatefulClient` and `HttpStatelessClient` classes.
    """
    try:
        from agentscope.mcp import HttpStatelessClient, StdIOStatefulClient

        return StdIOStatefulClient, HttpStatelessClient
    except ImportError:
        repo_root = Path(__file__).resolve().parents[3]
        src_path = repo_root / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

        from agentscope.mcp import HttpStatelessClient, StdIOStatefulClient

        return StdIOStatefulClient, HttpStatelessClient


StdIOStatefulClient, HttpStatelessClient = _import_agentscope_mcp()


class MCPToolDiscoverer:
    """Discover MCP tool schemas from local server configurations.

    Args:
        startup_wait_seconds (`float`, optional):
            Wait time after spawning local HTTP MCP servers.
        tool_discovery_timeout (`float`, optional):
            Maximum seconds to wait for ``list_tools`` to respond.  If the
            server does not reply within this window the call is cancelled
            and the server is treated as unavailable.
    """

    def __init__(
        self,
        startup_wait_seconds: float = 5.0,
        tool_discovery_timeout: float = 30.0,
    ) -> None:
        """Initialize the discoverer.

        Args:
            startup_wait_seconds (`float`, optional):
                Wait time after spawning local HTTP MCP servers.
            tool_discovery_timeout (`float`, optional):
                Maximum seconds to wait for ``list_tools`` to respond.
        """
        self.startup_wait_seconds = startup_wait_seconds
        self.tool_discovery_timeout = tool_discovery_timeout

    async def discover_tools(
        self,
        server_configs: list[ServerConfig],
    ) -> dict[str, dict[str, Any]]:
        """Discover tools from multiple MCP servers concurrently.

        Args:
            server_configs (`list[ServerConfig]`):
                Server configs that should be queried.

        Returns:
            `dict[str, dict[str, Any]]`:
                Mapping from fully qualified tool name to tool metadata.
        """
        names = ", ".join(c.name for c in server_configs)
        _logger.info("[discovery] starting tool discovery for: %s", names)

        tasks = [self._discover_tools_for_server(config) for config in server_configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        merged: dict[str, dict[str, Any]] = {}
        errors: list[str] = []
        for index, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(f"{server_configs[index].name}: {result}")
                _logger.warning(
                    "[discovery] %s — FAILED: %s",
                    server_configs[index].name,
                    result,
                )
                continue
            _logger.info(
                "[discovery] %s — OK (%d tools)",
                server_configs[index].name,
                len(result),
            )
            merged.update(result)

        if not merged and errors:
            raise RuntimeError("; ".join(errors))

        _logger.info(
            "[discovery] finished — %d tools total, %d server(s) failed",
            len(merged),
            len(errors),
        )
        return merged

    async def _discover_tools_for_server(
        self,
        server_config: ServerConfig,
    ) -> dict[str, dict[str, Any]]:
        """Discover tools for one server.

        Args:
            server_config (`ServerConfig`):
                One normalized local MCP server config.

        Returns:
            `dict[str, dict[str, Any]]`:
                Tool metadata keyed by fully qualified tool name.
        """
        if server_config.transport == "stdio":
            return await self._discover_stdio_tools(server_config)
        return await self._discover_http_tools(server_config)

    async def _discover_stdio_tools(
        self,
        server_config: ServerConfig,
    ) -> dict[str, dict[str, Any]]:
        """Discover tools from one stdio-based MCP server.

        Args:
            server_config (`ServerConfig`):
                One stdio server config.

        Returns:
            `dict[str, dict[str, Any]]`:
                Tool metadata keyed by fully qualified tool name.
        """
        _logger.info("[discovery] %s — connecting via stdio", server_config.name)
        client = StdIOStatefulClient(
            name=server_config.name,
            command=server_config.command,
            args=server_config.args,
            env=server_config.env or None,
            cwd=server_config.cwd,
        )
        await client.connect()
        try:
            _logger.debug("[discovery] %s — calling list_tools (timeout=%.0fs)", server_config.name, self.tool_discovery_timeout)
            tools = await asyncio.wait_for(
                client.list_tools(),
                timeout=self.tool_discovery_timeout,
            )
            return self._tools_to_mapping(server_config.name, tools)
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"list_tools timed out after {self.tool_discovery_timeout:.0f}s",
            )
        finally:
            await client.close()

    async def _discover_http_tools(
        self,
        server_config: ServerConfig,
    ) -> dict[str, dict[str, Any]]:
        """Discover tools from one HTTP-based MCP server.

        Args:
            server_config (`ServerConfig`):
                One HTTP server config.

        Returns:
            `dict[str, dict[str, Any]]`:
                Tool metadata keyed by fully qualified tool name.
        """
        if server_config.port is None:
            raise ValueError(
                f"HTTP transport for {server_config.name} requires a port.",
            )

        transport = "sse" if server_config.transport == "sse" else "streamable_http"
        url = f"http://127.0.0.1:{server_config.port}{server_config.endpoint}"
        if server_config.pre_warmed:
            # 预热模式：直接请求 HTTP，不再尝试拉起/关闭容器
            _logger.info(
                "[discovery] %s — pre-warmed mode, directly calling list_tools at %s (timeout=%.0fs)",
                server_config.name,
                url,
                self.tool_discovery_timeout,
            )
            client = HttpStatelessClient(
                name=server_config.name,
                transport=transport,
                url=url,
            )
            try:
                tools = await asyncio.wait_for(
                    client.list_tools(),
                    timeout=self.tool_discovery_timeout,
                )
            except asyncio.TimeoutError:
                raise RuntimeError(
                    f"list_tools timed out after {self.tool_discovery_timeout:.0f}s "
                    f"(url={url})",
                )
            return self._tools_to_mapping(server_config.name, tools)
        else:
            _logger.info(
                "[discovery] %s — spawning docker container (port %s)",
                server_config.name,
                server_config.port,
            )
            container_name = self._extract_container_name(server_config)
            process = self._spawn_http_process(server_config)
            try:
                _logger.debug(
                    "[discovery] %s — waiting %.0fs for container to be ready",
                    server_config.name,
                    self.startup_wait_seconds,
                )
                await asyncio.sleep(self.startup_wait_seconds)
                if process.poll() is not None:
                    stderr = process.stderr.read() if process.stderr else ""
                    raise RuntimeError(
                        f"Container exited before discovery. stderr: {stderr}",
                    )

                _logger.info(
                    "[discovery] %s — calling list_tools at %s (timeout=%.0fs)",
                    server_config.name,
                    url,
                    self.tool_discovery_timeout,
                )
                client = HttpStatelessClient(
                    name=server_config.name,
                    transport=transport,
                    url=url,
                )
                try:
                    tools = await asyncio.wait_for(
                        client.list_tools(),
                        timeout=self.tool_discovery_timeout,
                    )
                except asyncio.TimeoutError:
                    raise RuntimeError(
                        f"list_tools timed out after {self.tool_discovery_timeout:.0f}s "
                        f"(url={url})",
                    )
                return self._tools_to_mapping(server_config.name, tools)
            finally:
                _logger.debug("[discovery] %s — stopping container", server_config.name)
                self._stop_process(process, container_name)

    @staticmethod
    def _spawn_http_process(server_config: ServerConfig) -> subprocess.Popen[str]:
        """Spawn a local HTTP MCP server process.

        Args:
            server_config (`ServerConfig`):
                One HTTP server config.

        Returns:
            `subprocess.Popen[str]`:
                Spawned child process.
        """
        env = os.environ.copy()
        env.update(server_config.env)
        return subprocess.Popen(
            [server_config.command, *server_config.args],
            cwd=server_config.cwd,
            env=env,
            # Discard stdout to prevent pipe buffer exhaustion (Docker
            # containers can emit large amounts of output).  stderr is kept
            # as a pipe so that early-exit errors can be surfaced.
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

    @staticmethod
    def _extract_container_name(server_config: ServerConfig) -> str | None:
        """Extract the Docker container name from server args.

        Args:
            server_config (`ServerConfig`):
                One HTTP server config.

        Returns:
            `str | None`:
                Container name if ``--name`` is present, else ``None``.
        """
        try:
            idx = server_config.args.index("--name")
            return server_config.args[idx + 1]
        except (ValueError, IndexError):
            return None

    @staticmethod
    def _stop_process(
        process: subprocess.Popen[str],
        container_name: str | None = None,
    ) -> None:
        """Terminate a spawned MCP server process and its Docker container.

        Args:
            process (`subprocess.Popen[str]`):
                Spawned child process.
            container_name (`str | None`, optional):
                Docker container name to force-remove after termination.
                Required to handle cases where the ``docker run`` process
                exits (e.g. in WSL) but the container keeps running.
        """
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

        # Always force-remove the named container.  In WSL the daemon may
        # keep the container alive even after the docker-run process exits.
        if container_name:
            try:
                subprocess.run(
                    ["docker", "rm", "-f", container_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                )
            except Exception:  # noqa: BLE001
                pass

    @staticmethod
    def _tools_to_mapping(
        server_name: str,
        tools: list[Any],
    ) -> dict[str, dict[str, Any]]:
        """Convert MCP tool objects into synthesis metadata.

        Args:
            server_name (`str`):
                Human-readable MCP server name.
            tools (`list[Any]`):
                MCP tool objects returned by one client.

        Returns:
            `dict[str, dict[str, Any]]`:
                Tool metadata keyed by fully qualified tool name.
        """
        tool_map: dict[str, dict[str, Any]] = {}
        for tool in tools:
            qualified_name = f"{server_name}:{tool.name}"
            tool_map[qualified_name] = {
                "name": tool.name,
                "original_name": tool.name,
                "server": server_name,
                "description": getattr(tool, "description", "") or "",
                "input_schema": getattr(tool, "inputSchema", {}) or {},
            }
        return tool_map