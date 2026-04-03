# -*- coding: utf-8 -*-
"""Tests for local MCP Docker server lifecycle helper."""
import asyncio
from unittest.mock import AsyncMock
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

import mcp.types

from agentscope.mcp import _mcp_server_helper as helper
from agentscope.mcp import _DockerMCPServerConfig


class MCPServerHelperLifecycleTest(IsolatedAsyncioTestCase):
    """Test idle lifecycle management for MCP Docker containers."""

    async def asyncSetUp(self) -> None:
        """Reset global lifecycle states before each test."""
        helper._CONTAINER_LIFECYCLE_STATES.clear()
        if helper._CONTAINER_LIFECYCLE_TASK is not None:
            helper._CONTAINER_LIFECYCLE_TASK.cancel()
            try:
                await helper._CONTAINER_LIFECYCLE_TASK
            except asyncio.CancelledError:
                pass
            helper._CONTAINER_LIFECYCLE_TASK = None

    async def asyncTearDown(self) -> None:
        """Clean up global lifecycle states after each test."""
        helper._CONTAINER_LIFECYCLE_STATES.clear()
        if helper._CONTAINER_LIFECYCLE_TASK is not None:
            helper._CONTAINER_LIFECYCLE_TASK.cancel()
            try:
                await helper._CONTAINER_LIFECYCLE_TASK
            except asyncio.CancelledError:
                pass
            helper._CONTAINER_LIFECYCLE_TASK = None

    async def test_lifecycle_stops_then_removes_container(self) -> None:
        """Stop after 5 minutes idle, then remove after 10 minutes idle."""
        container_name = "playwright-mcp"
        helper._CONTAINER_LIFECYCLE_STATES[container_name] = (
            helper._ContainerLifecycleState(
                created_at=0.0,
                last_used_at=0.0,
                stop_after_seconds=300.0,
                remove_after_seconds=600.0,
                in_use=0,
            )
        )

        running = True
        commands: list[list[str]] = []

        async def fake_run_command(
            command: list[str],
            env: dict[str, str] | None = None,
        ) -> tuple[int, str, str]:
            nonlocal running
            del env
            commands.append(command)

            if command[:2] == ["docker", "inspect"] and len(command) == 3:
                return 0, "", ""
            if command[:3] == ["docker", "inspect", "-f"]:
                return 0, "true" if running else "false", ""
            if command[:2] == ["docker", "stop"]:
                running = False
                return 0, "", ""
            if command[:3] == ["docker", "rm", "-f"]:
                return 0, "", ""

            return 0, "", ""

        with patch(
            "agentscope.mcp._mcp_server_helper._run_command",
            side_effect=fake_run_command,
        ):
            await helper._run_container_lifecycle_once(current_time=301.0)

            self.assertIn(["docker", "stop", container_name], commands)
            self.assertIn(container_name, helper._CONTAINER_LIFECYCLE_STATES)

            await helper._run_container_lifecycle_once(current_time=601.0)

            self.assertIn(["docker", "rm", "-f", container_name], commands)
            self.assertNotIn(container_name, helper._CONTAINER_LIFECYCLE_STATES)

    async def test_ensure_server_tracks_container_usage(self) -> None:
        """Track container usage after ensuring local server readiness."""
        config = _DockerMCPServerConfig(
            container_name="github-mcp",
            image="ghcr.io/github/github-mcp-server:latest",
            transport="streamable_http",
            url="http://localhost:8932/mcp",
            client_name="github",
        )

        async def fake_run_command(
            command: list[str],
            env: dict[str, str] | None = None,
        ) -> tuple[int, str, str]:
            del env
            if command[:2] == ["docker", "inspect"] and len(command) == 3:
                return 1, "", ""
            if command[:3] == ["docker", "run", "-d"]:
                return 0, "started", ""
            return 0, "", ""

        with (
            patch(
                "agentscope.mcp._mcp_server_helper._run_command",
                side_effect=fake_run_command,
            ),
            patch(
                "agentscope.mcp._mcp_server_helper._wait_for_mcp_server",
                return_value=None,
            ),
            patch(
                "agentscope.mcp._mcp_server_helper._get_idle_thresholds",
                return_value=(300.0, 600.0),
            ),
        ):
            client = await helper._ensure_local_docker_mcp_server(
                config=config,
                docker_run_command=[
                    "docker",
                    "run",
                    "-d",
                    "github-mcp",
                ],
            )

        self.assertEqual(client.name, "github")
        self.assertIn("github-mcp", helper._CONTAINER_LIFECYCLE_STATES)

    async def test_lifecycle_skips_container_while_in_use(self) -> None:
        """Do not stop or remove a container while a tool call is active."""
        container_name = "playwright-mcp"
        helper._CONTAINER_LIFECYCLE_STATES[container_name] = (
            helper._ContainerLifecycleState(
                created_at=0.0,
                last_used_at=0.0,
                stop_after_seconds=300.0,
                remove_after_seconds=600.0,
                in_use=1,
            )
        )

        commands: list[list[str]] = []

        async def fake_run_command(
            command: list[str],
            env: dict[str, str] | None = None,
        ) -> tuple[int, str, str]:
            del env
            commands.append(command)
            return 0, "", ""

        with patch(
            "agentscope.mcp._mcp_server_helper._run_command",
            side_effect=fake_run_command,
        ):
            await helper._run_container_lifecycle_once(current_time=601.0)

        self.assertEqual(commands, [])
        self.assertEqual(
            helper._CONTAINER_LIFECYCLE_STATES[container_name].in_use,
            1,
        )

    async def test_managed_tool_function_tracks_in_use(self) -> None:
        """Managed MCP tool function should balance in_use around calls."""
        tool = mcp.types.Tool(
            name="browser_navigate",
            description="Navigate to a page.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                },
                "required": ["url"],
            },
        )
        result = mcp.types.CallToolResult(content=[], meta={})

        tool_func = helper._ManagedMCPToolFunction(
            container_name="playwright-mcp",
            client_name="playwright-mcp",
            tool_name="browser_navigate",
            mcp_name="playwright-mcp",
            tool=tool,
            wrap_tool_result=False,
            session=AsyncMock(call_tool=AsyncMock(return_value=result)),
        )

        await helper._track_container_usage("playwright-mcp")
        before_last_used_at = helper._CONTAINER_LIFECYCLE_STATES[
            "playwright-mcp"
        ].last_used_at

        res = await tool_func(url="https://example.com")

        self.assertIs(res, result)
        self.assertEqual(
            helper._CONTAINER_LIFECYCLE_STATES["playwright-mcp"].in_use,
            0,
        )
        self.assertGreaterEqual(
            helper._CONTAINER_LIFECYCLE_STATES["playwright-mcp"].last_used_at,
            before_last_used_at,
        )

    async def test_bind_container_client_uses_set_semantics(self) -> None:
        """Container bindings should support many-to-many with deduplication."""
        await helper._bind_container_client(
            container_name="playwright-mcp",
            client_name="client-a",
        )
        await helper._bind_container_client(
            container_name="playwright-mcp",
            client_name="client-a",
        )
        await helper._bind_container_client(
            container_name="playwright-mcp",
            client_name="client-b",
        )

        state = helper._CONTAINER_LIFECYCLE_STATES["playwright-mcp"]
        self.assertEqual(state.bound_clients, {"client-a", "client-b"})

    async def test_usage_exit_includes_usage_duration_ms(self) -> None:
        """usage_exit metrics should include per-call duration in ms."""
        with patch(
            "agentscope.mcp._mcp_server_helper._record_lifecycle_snapshot_to_span",
        ) as mock_record:
            entered_at_s = await helper._enter_container_usage(
                container_name="playwright-mcp",
                client_name="playwright-mcp",
                tool_name="browser_type",
            )
            await asyncio.sleep(0.002)
            await helper._exit_container_usage(
                container_name="playwright-mcp",
                client_name="playwright-mcp",
                tool_name="browser_type",
                entered_at_s=entered_at_s,
            )

        exit_calls = [
            _.kwargs
            for _ in mock_record.call_args_list
            if _.kwargs.get("event") == "usage_exit"
        ]
        self.assertEqual(len(exit_calls), 1)
        self.assertIn("usage_duration_ms", exit_calls[0])
        assert exit_calls[0]["usage_duration_ms"] is not None
        self.assertGreater(exit_calls[0]["usage_duration_ms"], 0.0)

    async def test_ensure_server_records_cold_startup_time(self) -> None:
        """Record cold startup time when container is created from image."""
        config = _DockerMCPServerConfig(
            container_name="playwright-mcp",
            image="mcr.microsoft.com/playwright/mcp:latest",
            transport="streamable_http",
            url="http://localhost:8931/mcp",
            client_name="playwright-mcp",
        )

        async def fake_run_command(
            command: list[str],
            env: dict[str, str] | None = None,
        ) -> tuple[int, str, str]:
            del env
            if command[:2] == ["docker", "inspect"] and len(command) == 3:
                return 1, "", ""
            if command[:3] == ["docker", "run", "-d"]:
                return 0, "started", ""
            return 0, "", ""

        with (
            patch(
                "agentscope.mcp._mcp_server_helper._run_command",
                side_effect=fake_run_command,
            ),
            patch(
                "agentscope.mcp._mcp_server_helper._wait_for_mcp_server",
                return_value=None,
            ),
            patch(
                "agentscope.mcp._mcp_server_helper._record_startup_time_to_span",
            ) as mock_record_startup,
        ):
            await helper._ensure_local_docker_mcp_server(
                config=config,
                docker_run_command=["docker", "run", "-d", "playwright-mcp"],
            )

        self.assertEqual(mock_record_startup.call_count, 1)
        call_kwargs = mock_record_startup.call_args.kwargs
        self.assertEqual(call_kwargs["container_name"], "playwright-mcp")
        self.assertEqual(call_kwargs["startup_mode"], "cold")
        self.assertGreater(call_kwargs["startup_time_ms"], 0.0)

    async def test_ensure_server_records_resume_startup_time(self) -> None:
        """Record resume startup time when restarting a stopped container."""
        config = _DockerMCPServerConfig(
            container_name="github-mcp",
            image="ghcr.io/github/github-mcp-server:latest",
            transport="streamable_http",
            url="http://localhost:8932/mcp",
            client_name="github",
        )

        async def fake_run_command(
            command: list[str],
            env: dict[str, str] | None = None,
        ) -> tuple[int, str, str]:
            del env
            if command[:2] == ["docker", "inspect"] and len(command) == 3:
                return 0, "", ""
            if command[:3] == ["docker", "inspect", "-f"]:
                return 0, "false", ""
            if command[:2] == ["docker", "restart"]:
                return 0, "", ""
            return 0, "", ""

        with (
            patch(
                "agentscope.mcp._mcp_server_helper._run_command",
                side_effect=fake_run_command,
            ),
            patch(
                "agentscope.mcp._mcp_server_helper._wait_for_mcp_server",
                return_value=None,
            ),
            patch(
                "agentscope.mcp._mcp_server_helper._record_startup_time_to_span",
            ) as mock_record_startup,
        ):
            await helper._ensure_local_docker_mcp_server(
                config=config,
                docker_run_command=["docker", "run", "-d", "github-mcp"],
            )

        self.assertEqual(mock_record_startup.call_count, 1)
        call_kwargs = mock_record_startup.call_args.kwargs
        self.assertEqual(call_kwargs["container_name"], "github-mcp")
        self.assertEqual(call_kwargs["startup_mode"], "resume")
        self.assertGreater(call_kwargs["startup_time_ms"], 0.0)
