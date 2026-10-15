"""Test MCP execution-timeout forwarding through the toolkit."""

from collections.abc import Callable
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

import mcp.types

from agentscope.mcp import MCPClientBase
from agentscope.tool import Toolkit, ToolResponse


class _RecordingMCPClient(MCPClientBase):
    """Minimal MCP client that records the configured execution timeout."""

    def __init__(self) -> None:
        """Initialize the recording client."""
        super().__init__("timeout-test")
        self.execution_timeout: float | None = None

    async def list_tools(self) -> list[mcp.types.Tool]:
        """Return one mock tool definition."""
        return [
            mcp.types.Tool(
                name="slow_tool",
                description="A mock tool.",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    async def get_callable_function(
        self,
        func_name: str,
        wrap_tool_result: bool = True,
        execution_timeout: float | None = None,
    ) -> Callable[..., ToolResponse]:
        """Record the timeout and return a mock callable.

        Args:
            func_name (`str`):
                Mock MCP tool name.
            wrap_tool_result (`bool`, defaults to `True`):
                Whether AgentScope should wrap the result.
            execution_timeout (`float | None`, optional):
                Timeout forwarded by the toolkit.

        Returns:
            `Callable`:
                A mock async MCP tool.
        """
        del func_name, wrap_tool_result
        self.execution_timeout = execution_timeout

        async def _tool() -> ToolResponse:
            """Return an empty mock tool response."""
            return ToolResponse(content=[])

        return _tool


class ToolkitMCPExecutionTimeoutTest(IsolatedAsyncioTestCase):
    """Test MCP registration timeout configuration."""

    async def test_register_mcp_client_forwards_execution_timeout(self) -> None:
        """The configured timeout reaches each registered MCP tool."""
        toolkit = Toolkit()
        client = _RecordingMCPClient()

        with patch.object(toolkit, "register_tool_function"):
            await toolkit.register_mcp_client(
                client,
                execution_timeout=30.0,
            )

        self.assertEqual(client.execution_timeout, 30.0)
