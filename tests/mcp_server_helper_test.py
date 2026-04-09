# -*- coding: utf-8 -*-
"""Tests for local MCP Docker server lifecycle helper."""
import asyncio
import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import patch

import mcp.types

from agentscope.mcp import _mcp_server_helper as helper
from agentscope.mcp import _DockerMCPServerConfig


class MCPServerHelperLifecycleTest(IsolatedAsyncioTestCase):
    """Test idle lifecycle management for MCP Docker containers."""

    async def asyncSetUp(self) -> None:
        """Reset global lifecycle states before each test."""
        self._state_dir = tempfile.TemporaryDirectory()
        self._state_dir_patcher = patch(
            "agentscope.mcp._mcp_server_helper._get_lifecycle_state_dir",
            return_value=self._state_dir.name,
        )
        self._state_dir_patcher.start()
        self._daemon_patcher = patch(
            "agentscope.mcp._mcp_server_helper._ensure_mcp_lifecycle_daemon",
        )
        self._daemon_patcher.start()

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

        self._daemon_patcher.stop()
        self._state_dir_patcher.stop()
        self._state_dir.cleanup()

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

    async def test_client_orchestrated_usage_tracks_in_use(self) -> None:
        """Client orchestrated enter/exit should balance in_use around calls."""
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
        await helper._bind_container_client(
            container_name="playwright-mcp",
            client_name="playwright-mcp",
        )

        before_last_used_at = helper._CONTAINER_LIFECYCLE_STATES[
            "playwright-mcp"
        ].last_used_at

        container_name, entered_at_s = await helper._enter_container_usage_by_client(
            client_name="playwright-mcp",
            tool_name="browser_navigate",
        )
        res = await tool_func(url="https://example.com")
        await helper._exit_container_usage_by_client(
            client_name="playwright-mcp",
            container_name=container_name,
            tool_name="browser_navigate",
            entered_at_s=entered_at_s,
        )

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

    async def test_ensure_server_uses_single_inspect_for_state_check(self) -> None:
        """Ensure path should use a single docker inspect for state lookup."""
        config = _DockerMCPServerConfig(
            container_name="playwright-mcp",
            image="mcr.microsoft.com/playwright/mcp:latest",
            transport="streamable_http",
            url="http://localhost:8931/mcp",
            client_name="playwright-mcp",
        )
        inspect_calls: list[list[str]] = []

        async def fake_run_command(
            command: list[str],
            env: dict[str, str] | None = None,
        ) -> tuple[int, str, str]:
            del env
            if command[:3] == ["docker", "inspect", "-f"]:
                inspect_calls.append(command)
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
        ):
            await helper._ensure_local_docker_mcp_server(
                config=config,
                docker_run_command=["docker", "run", "-d", "playwright-mcp"],
            )

        self.assertEqual(len(inspect_calls), 1)

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

    async def test_ensure_server_records_running_startup_time(self) -> None:
        """Record running mode explicitly when container is already up."""
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
            if command[:3] == ["docker", "inspect", "-f"]:
                return 0, "true", ""
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
                "agentscope.mcp._mcp_server_helper._record_lifecycle_snapshot_to_span",
            ) as mock_record_snapshot,
        ):
            await helper._ensure_local_docker_mcp_server(
                config=config,
                docker_run_command=["docker", "run", "-d", "github-mcp"],
            )

        startup_calls = [
            _.kwargs
            for _ in mock_record_snapshot.call_args_list
            if _.kwargs.get("event") in {"container_already_running", "container_startup"}
        ]
        self.assertTrue(startup_calls)
        self.assertEqual(startup_calls[-1]["startup_mode"], "running")
        self.assertEqual(startup_calls[-1]["startup_time_ms"], 0.0)

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

    async def test_speculative_ensure_skips_formal_usage_tracking(self) -> None:
        """Speculative ensure should not update formal usage tracking."""
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
                "agentscope.mcp._mcp_server_helper._track_container_usage",
                new_callable=AsyncMock,
            ) as mock_track_usage,
            patch(
                "agentscope.mcp._mcp_server_helper._bind_container_client",
                new_callable=AsyncMock,
            ) as mock_bind_client,
        ):
            client = await helper._speculative_ensure_local_docker_mcp_server(
                config=config,
                docker_run_command=["docker", "run", "-d", "playwright-mcp"],
            )

        self.assertEqual(client.name, "playwright-mcp")
        mock_track_usage.assert_not_called()
        mock_bind_client.assert_awaited_once_with(
            container_name="playwright-mcp",
            client_name="playwright-mcp",
        )

    async def test_speculative_ensure_records_resume_startup_time(self) -> None:
        """Speculative ensure should still record startup timing metrics."""
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
            await helper._speculative_ensure_local_docker_mcp_server(
                config=config,
                docker_run_command=["docker", "run", "-d", "github-mcp"],
            )

        self.assertEqual(mock_record_startup.call_count, 1)
        call_kwargs = mock_record_startup.call_args.kwargs
        self.assertEqual(call_kwargs["container_name"], "github-mcp")
        self.assertEqual(call_kwargs["startup_mode"], "resume")
        self.assertGreater(call_kwargs["startup_time_ms"], 0.0)

    async def test_daemon_tick_reclaims_stale_usage_from_persisted_state(self) -> None:
        """Standalone daemon should clean up stale in-use state after owner exit."""
        container_name = "playwright-mcp"
        helper._persist_container_lifecycle_state(
            container_name,
            helper._ContainerLifecycleState(
                created_at=0.0,
                last_used_at=0.0,
                stop_after_seconds=300.0,
                remove_after_seconds=600.0,
                in_use=1,
                owner_pids={999999},
            ),
        )
        helper._CONTAINER_LIFECYCLE_STATES.clear()
        commands: list[list[str]] = []

        async def fake_run_command(
            command: list[str],
            env: dict[str, str] | None = None,
        ) -> tuple[int, str, str]:
            del env
            commands.append(command)
            if command[:3] == ["docker", "inspect", "-f"]:
                return 0, "true", ""
            if command[:3] == ["docker", "rm", "-f"]:
                return 0, "", ""
            return 0, "", ""

        with (
            patch(
                "agentscope.mcp._mcp_server_helper._run_command",
                side_effect=fake_run_command,
            ),
            patch(
                "agentscope.mcp._mcp_server_helper._is_process_alive",
                return_value=False,
            ),
        ):
            await helper._run_mcp_lifecycle_daemon_once(current_time=601.0)

        self.assertIn(["docker", "rm", "-f", container_name], commands)
        self.assertNotIn(container_name, helper._CONTAINER_LIFECYCLE_STATES)
        self.assertFalse(
            os.path.exists(helper._get_container_state_path(container_name)),
        )

    def test_record_mcp_timing_event_writes_trace_attributes(self) -> None:
        """Timing events should be appended and emitted as tracing spans."""
        timing_run = helper._create_mcp_timing_run(
            task_description="Check Beijing weather",
            prewarm=True,
        )
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = (
            mock_span
        )
        mock_tracer.start_as_current_span.return_value.__exit__.return_value = (
            None
        )

        with (
            patch(
                "agentscope.mcp._mcp_server_helper._get_tracer",
                return_value=mock_tracer,
            ),
            patch(
                "agentscope.mcp._mcp_server_helper._config",
                MagicMock(trace_enabled=True),
            ),
        ):
            helper._record_mcp_timing_event(
                timing_run,
                "tool_group_activation_requested",
                group_name="browser_tools",
            )
            helper._record_mcp_timing_event(
                timing_run,
                "mcp_server_ready",
                group_name="browser_tools",
                tool_name="browser_navigate",
            )

        self.assertEqual(len(timing_run["events"]), 2)
        self.assertEqual(timing_run["events"][1]["step"], "mcp_server_ready")
        self.assertEqual(mock_tracer.start_as_current_span.call_count, 2)
        call_kwargs = mock_tracer.start_as_current_span.call_args.kwargs
        self.assertEqual(call_kwargs["name"], "mcp.execution.timing")
        self.assertEqual(
            call_kwargs["attributes"]["mcp.timing.event"],
            "mcp_server_ready",
        )
        self.assertTrue(call_kwargs["attributes"]["mcp.timing.prewarm"])
        self.assertIn(
            "mcp.timing.summary.wait_for_mcp_ready_after_activation_ms",
            call_kwargs["attributes"],
        )

    def test_save_mcp_timing_log_persists_summary(self) -> None:
        """Timing log should be written as one JSONL row with summary."""
        timing_run = {
            "run_id": "worker-test",
            "prewarm": False,
            "events": [
                {"step": "tool_group_activation_requested", "elapsed_ms": 100.0},
                {"step": "mcp_server_ready", "elapsed_ms": 260.0},
                {"step": "final_result_ready", "elapsed_ms": 800.0},
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = f"{temp_dir}/timing.jsonl"
            saved_path = helper._save_mcp_timing_log(timing_run, log_path)
            with open(saved_path, encoding="utf-8") as file:
                rows = [json.loads(line) for line in file if line.strip()]

        self.assertEqual(saved_path, log_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["run_id"], "worker-test")
        self.assertIsNone(rows[0]["summary"]["startup_mode"])
        self.assertEqual(
            rows[0]["summary"]["wait_for_mcp_ready_after_activation_ms"],
            160.0,
        )


class MCPServerHelperDaemonTest(TestCase):
    """Test external MCP lifecycle daemon process helpers."""

    def setUp(self) -> None:
        """Create an isolated state directory for daemon process tests."""
        self._state_dir = tempfile.TemporaryDirectory()
        self._state_dir_patcher = patch(
            "agentscope.mcp._mcp_server_helper._get_lifecycle_state_dir",
            return_value=self._state_dir.name,
        )
        self._state_dir_patcher.start()

    def tearDown(self) -> None:
        """Clean up the isolated daemon state directory."""
        self._state_dir_patcher.stop()
        self._state_dir.cleanup()

    def test_ensure_mcp_lifecycle_daemon_starts_detached_process(self) -> None:
        """A detached MCP daemon process should be spawned when absent."""
        with (
            patch.dict(os.environ, {}, clear=False),
            patch(
                "agentscope.mcp._mcp_server_helper._read_daemon_pid_file",
                return_value=None,
            ),
            patch("subprocess.Popen") as mock_popen,
        ):
            helper._ensure_mcp_lifecycle_daemon()

        mock_popen.assert_called_once()
        popen_args, popen_kwargs = mock_popen.call_args
        self.assertEqual(
            popen_args[0],
            [helper.sys.executable, "-m", "agentscope.mcp._mcp_daemon"],
        )
        self.assertEqual(
            popen_kwargs["env"]["AGENTSCOPE_MCP_DAEMON_PROCESS"],
            "1",
        )
