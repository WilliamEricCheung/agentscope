# -*- coding: utf-8 -*-
"""The MCP streamable HTTP server."""
import asyncio
from contextlib import _AsyncGeneratorContextManager
from typing import Any, Callable, Awaitable, Literal, List

import httpx
import mcp.types
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client

from . import MCPToolFunction
from ._client_base import MCPClientBase
from ..tool import ToolResponse


class HttpStatelessClient(MCPClientBase):
    """The sse/streamable HTTP MCP client implementation in AgentScope.

    .. note:: Note this client is stateless, meaning it won't maintain the
     session state across multiple tool calls. Each tool call will start a
     new session and close it after the call is done.

    """

    stateful: bool = False
    """Whether the MCP server is stateful, meaning it will maintain the
    session state across multiple tool calls, or stateless, meaning it
    will start a new session for each tool call."""

    def __init__(
        self,
        name: str,
        transport: Literal["streamable_http", "sse"],
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 30,
        sse_read_timeout: float = 60 * 5,
        list_tools_retry_attempts: int = 2,
        list_tools_retry_delay: float = 0.5,
        **client_kwargs: Any,
    ) -> None:
        """Initialize the streamable HTTP MCP server.

        Args:
            name (`str`):
                The name to identify the MCP server, which should be unique
                across the MCP servers.
            transport (`Literal["streamable_http", "sse"]`):
                The transport type of MCP server. Generally, the URL of sse
                transport should end with `/sse`, while the streamable HTTP
                URL ends with `/mcp`.
            url (`str`):
                The URL of the MCP server.
            headers (`dict[str, str] | None`, optional):
                Additional headers to include in the HTTP request.
            timeout (`float`, optional):
                The timeout for the HTTP request in seconds. Defaults to 30.
            sse_read_timeout (`float`, optional):
                The timeout for reading Server-Sent Events (SSE) in seconds.
                Defaults to 300 (5 minutes).
            list_tools_retry_attempts (`int`, optional):
                Maximum attempts for `list_tools` when the HTTP transport hits
                a transient fetch failure. Defaults to 2.
            list_tools_retry_delay (`float`, optional):
                Delay in seconds between `list_tools` retries. Defaults to 0.5.
            **client_kwargs (`Any`):
                The additional keyword arguments to pass to the streamable
                HTTP client.
        """
        super().__init__(name=name)

        assert transport in ["streamable_http", "sse"]

        self.transport = transport
        self.list_tools_retry_attempts = max(1, list_tools_retry_attempts)
        self.list_tools_retry_delay = max(0.0, list_tools_retry_delay)

        self.client_config = {
            "url": url,
            "headers": headers or {},
            "timeout": timeout,
            "sse_read_timeout": sse_read_timeout,
            **client_kwargs,
        }

        self._tools = None

    @staticmethod
    def _is_transient_list_tools_error(exc: BaseException) -> bool:
        """Check whether a `list_tools` failure looks transient.

        Args:
            exc (`BaseException`):
                The raised exception.

        Returns:
            `bool`:
                Whether the failure should be retried.
        """
        if isinstance(exc, BaseExceptionGroup):
            return any(
                HttpStatelessClient._is_transient_list_tools_error(sub_exc)
                for sub_exc in exc.exceptions
            )

        return "fetch failed" in str(exc).lower()

    def get_client(self) -> _AsyncGeneratorContextManager[Any]:
        """The disposable MCP client object, which is a context manager."""
        if self.transport == "sse":
            return sse_client(**self.client_config)

        if self.transport == "streamable_http":
            # MCP TypeScript SDK validates the Origin header to prevent
            # DNS rebinding attacks. httpx does not set Origin automatically
            # (unlike browsers), so we derive it from the URL when the caller
            # has not provided one.
            from urllib.parse import urlparse

            parsed = urlparse(self.client_config["url"])
            derived_origin = f"{parsed.scheme}://{parsed.netloc}"
            headers = {
                "Origin": derived_origin,
                **self.client_config.get("headers", {}),
            }
            http_client = httpx.AsyncClient(
                headers=headers,
                timeout=self.client_config.get("timeout", 30),
            )

            # New MCP Python SDK expects streamable_http_client(url, http_client)
            # and no longer accepts headers/timeout directly.
            streamable_http_kwargs = {
                key: value
                for key, value in self.client_config.items()
                if key not in {"headers", "timeout", "sse_read_timeout"}
            }
            streamable_http_kwargs["http_client"] = http_client

            return streamable_http_client(**streamable_http_kwargs,)

        raise ValueError(
            f"Unsupported transport type: {self.transport}. "
            "Supported types are 'sse' and 'streamable_http'.",
        )

    async def get_callable_function(
        self,
        func_name: str,
        wrap_tool_result: bool = True,
        execution_timeout: float | None = None,
    ) -> Callable[..., Awaitable[mcp.types.CallToolResult | ToolResponse]]:
        """Get a tool function by its name.

        Args:
            func_name (`str`):
                The name of the tool function.
            wrap_tool_result (`bool`, defaults to `True`):
                Whether to wrap the tool result into agentscope's
                `ToolResponse` object. If `False`, the raw result type
                `mcp.types.CallToolResult` will be returned.
            execution_timeout (`float | None`, optional):
                The preset timeout in seconds for calling the tool function.

        Returns:
            `Callable[..., Awaitable[mcp.types.CallToolResult | \
            ToolResponse]]`:
                An async tool function that returns either
                `mcp.types.CallToolResult` or `ToolResponse` when called.
        """

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

        return MCPToolFunction(
            mcp_name=self.name,
            tool=target_tool,
            wrap_tool_result=wrap_tool_result,
            client_gen=self.get_client,
            timeout=execution_timeout,
        )

    async def list_tools(self) -> List[mcp.types.Tool]:
        """List all tools available on the MCP server.

        Returns:
            `mcp.types.ListToolsResult`:
                The result containing the list of tools.
        """
        last_exception: Exception | None = None

        for attempt in range(1, self.list_tools_retry_attempts + 1):
            try:
                async with self.get_client() as cli:
                    read_stream, write_stream = cli[0], cli[1]
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        res = await session.list_tools()
                        self._tools = res.tools
                        return res.tools
            except Exception as exc:
                last_exception = exc
                if (
                    attempt >= self.list_tools_retry_attempts
                    or not self._is_transient_list_tools_error(exc)
                ):
                    raise
                await asyncio.sleep(self.list_tools_retry_delay)

        if last_exception is not None:
            raise last_exception
        raise RuntimeError("list_tools failed without an exception")
