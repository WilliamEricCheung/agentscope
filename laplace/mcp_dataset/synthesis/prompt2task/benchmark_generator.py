"""Unified task generator for AgentScope-based MCP-Bench synthesis."""

from __future__ import annotations

import asyncio
from dataclasses import replace
import json
import logging
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from laplace.mcp_server_profile.profile_mcp_servers import (
    _dependency_services_for_targets,
    _is_tcp_port_open,
    load_profile_targets,
)
from laplace.util.dashscope_provider import DashScopeCompletionProvider
from laplace.util.mcp_tool_discovery import MCPToolDiscoverer
from laplace.util.server_config import LaplaceMCPManifestSource, ServerConfig
from .task_synthesis import TaskSynthesizer

_logger = logging.getLogger(__name__)


class BenchmarkTaskGenerator:
    """Generate single-server and multi-server MCP benchmark tasks.

    Args:
        model_name (`str`, optional):
            DashScope model used for synthesis.
        api_key (`str | None`, optional):
            DashScope API key.
        filter_problematic (`bool`, optional):
            Whether to filter problematic tools.
        tasks_per_server (`int`, optional):
            Number of accepted tasks per server or server combination.
        max_retries (`int`, optional):
            Maximum retries for one server or one server combination.
        manifest_path (`str | None`, optional):
            Explicit path to ``laplace_mcp_manifest.json``.
        self_heal_on_discovery_failure (`bool`, optional):
            Whether to dynamically exclude servers that repeatedly fail during
            tool discovery.
    """

    def __init__(
        self,
        model_name: str = "qwen-plus",
        api_key: str | None = None,
        filter_problematic: bool = True,
        tasks_per_server: int = 1,
        max_retries: int = 3,
        manifest_path: str | None = None,
        self_heal_on_discovery_failure: bool = True,
    ) -> None:
        """Initialize the benchmark generator.

        Args:
            model_name (`str`, optional):
                DashScope model used for synthesis.
            api_key (`str | None`, optional):
                DashScope API key.
            filter_problematic (`bool`, optional):
                Whether to filter problematic tools.
            tasks_per_server (`int`, optional):
                Number of accepted tasks per server or server combination.
            max_retries (`int`, optional):
                Maximum retries for one server or one server combination.
            manifest_path (`str | None`, optional):
                Explicit path to ``laplace_mcp_manifest.json``.
            self_heal_on_discovery_failure (`bool`, optional):
                Whether to dynamically exclude servers that repeatedly fail
                during tool discovery.
        """
        self.model_name = model_name
        self.filter_problematic = filter_problematic
        self.tasks_per_server = tasks_per_server
        self.max_retries = max_retries
        self.self_heal_on_discovery_failure = self_heal_on_discovery_failure
        self._runtime_unhealthy_servers: set[str] = set()
        self.command_source = LaplaceMCPManifestSource(
            manifest_path=manifest_path,
        )
        self.server_configs = self.command_source.load_server_configs()
        self.profile_targets_by_name = {
            target.name: target
            for target in load_profile_targets(self.command_source.manifest_path)
        }
        self.all_server_names = self.command_source.load_server_names()
        self.problematic_tools = set(self.command_source.load_problematic_tools())
        self.discoverer = MCPToolDiscoverer()
        self.synthesizer = TaskSynthesizer(
            llm_provider=DashScopeCompletionProvider(
                model_name=model_name,
                api_key=api_key,
            ),
        )

    async def generate_single_server_tasks(
        self,
        servers: list[str] | None = None,
        limit: int | None = None,
        skip: int = 0,
        output_file: str | None = None,
    ) -> dict[str, Any]:
        """Generate tasks for single-server settings.

        Args:
            servers (`list[str] | None`, optional):
                Optional subset of server names.
            limit (`int | None`, optional):
                Optional server count limit after filtering.
            skip (`int`, optional):
                Number of filtered servers to skip.
            output_file (`str | None`, optional):
                Optional path for incremental JSON saving.

        Returns:
            `dict[str, Any]`:
                Raw generation result.
        """
        start_time = datetime.now()
        selected_configs = self._filter_server_configs(
            servers=servers,
            limit=limit,
            skip=skip,
        )
        _logger.info(
            "[single] starting generation for %d server(s)",
            len(selected_configs),
        )
        successful: list[str] = []
        failed: list[dict[str, Any]] = []
        all_results: list[dict[str, Any]] = []

        for index, server_config in enumerate(selected_configs, start=1):
            _logger.info(
                "[single] [%d/%d] processing server: %s",
                index,
                len(selected_configs),
                server_config.name,
            )
            generation = await self._generate_with_retry([server_config])
            server_record = {
                "server_name": server_config.name,
                "generation_status": generation["status"],
                "connection_attempts": generation["attempts"],
                "tasks": generation.get("tasks", []),
            }
            if generation["status"] == "success":
                successful.append(server_config.name)
                _logger.info(
                    "[single] [%d/%d] %s — SUCCESS (%d task(s))",
                    index,
                    len(selected_configs),
                    server_config.name,
                    len(generation.get("tasks", [])),
                )
            else:
                failed.append(
                    {
                        "server_name": server_config.name,
                        "error": generation.get("error", "Unknown error"),
                        "attempts": generation["attempts"],
                        "failure_stage": generation.get("failure_stage", "unknown"),
                    },
                )
                server_record["error_message"] = generation.get("error", "Unknown error")
                server_record["failure_stage"] = generation.get("failure_stage", "unknown")
                _logger.warning(
                    "[single] [%d/%d] %s — FAILED after %d attempt(s): %s",
                    index,
                    len(selected_configs),
                    server_config.name,
                    generation["attempts"],
                    generation.get("error", "Unknown error"),
                )
                self._maybe_mark_unhealthy_from_generation(
                    server_names=[server_config.name],
                    generation=generation,
                )

            all_results.append(server_record)
            if output_file:
                self._save_json(
                    {
                        "generation_info": self._build_single_generation_info(
                            total_servers=len(selected_configs),
                            processed_servers=index,
                            successful_servers=len(successful),
                            failed_servers=len(failed),
                            start_time=start_time,
                            status="in_progress" if index < len(selected_configs) else "completed",
                        ),
                        "server_tasks": all_results,
                        "failed_servers": failed,
                    },
                    output_file,
                )

        results = {
            "generation_info": self._build_single_generation_info(
                total_servers=len(selected_configs),
                processed_servers=len(selected_configs),
                successful_servers=len(successful),
                failed_servers=len(failed),
                start_time=start_time,
                status="completed",
            ),
            "server_tasks": all_results,
            "failed_servers": failed,
        }
        if output_file:
            self._save_json(results, output_file)
        return results

    async def generate_multi_server_tasks(
        self,
        combinations_file: str = "split_combinations/mcp_2server_combinations.json",
        start_from: str | None = None,
        output_file: str | None = None,
    ) -> dict[str, Any]:
        """Generate tasks for multi-server combinations.

        Args:
            combinations_file (`str`, optional):
                JSON file containing server combinations.
            start_from (`str | None`, optional):
                Optional combination name to resume from.
            output_file (`str | None`, optional):
                Optional path for incremental JSON saving.

        Returns:
            `dict[str, Any]`:
                Raw generation result.
        """
        start_time = datetime.now()
        combinations = self._prepare_combinations(combinations_file, start_from)
        _logger.info(
            "[multi] starting generation for %d combination(s)",
            len(combinations),
        )
        results: list[dict[str, Any]] = []

        for index, combination in enumerate(combinations, start=1):
            server_names = [str(name) for name in combination.get("servers", [])]
            unhealthy_servers = [
                name
                for name in server_names
                if name in self._runtime_unhealthy_servers
            ]
            if unhealthy_servers:
                _logger.warning(
                    "[multi] [%d/%d] skipping combination %s due to unhealthy server(s): %s",
                    index,
                    len(combinations),
                    combination.get("name", "?"),
                    ", ".join(unhealthy_servers),
                )
                record = {
                    "combination_name": combination.get("name", ""),
                    "combination_type": combination.get("combination_type", ""),
                    "servers": server_names,
                    "description": combination.get("description", ""),
                    "generated_tasks": [],
                    "task_count": 0,
                    "generation_success": False,
                    "skipped": True,
                    "skip_reason": "unhealthy_server",
                    "unhealthy_servers": unhealthy_servers,
                    "failure_stage": "skipped",
                }
                results.append(record)
                if output_file:
                    self._save_json(
                        {
                            "generation_info": self._build_multi_generation_info(
                                combinations=results,
                                total_combinations=len(combinations),
                                processed_combinations=index,
                                start_time=start_time,
                                status="in_progress" if index < len(combinations) else "completed",
                            ),
                            "combinations": results,
                        },
                        output_file,
                    )
                continue

            _logger.info(
                "[multi] [%d/%d] processing combination: %s (%s)",
                index,
                len(combinations),
                combination.get("name", "?"),
                " + ".join(str(s) for s in combination.get("servers", [])),
            )
            record = await self._process_combination(combination)
            results.append(record)
            self._maybe_mark_unhealthy_from_generation(
                server_names=server_names,
                generation={
                    "status": "success"
                    if record.get("generation_success")
                    else "failed",
                    "failure_stage": record.get("failure_stage", "unknown"),
                    "error": record.get("error_message"),
                },
            )
            status = "SUCCESS" if record.get("generation_success") else "FAILED"
            _logger.info(
                "[multi] [%d/%d] %s — %s (%d task(s))",
                index,
                len(combinations),
                combination.get("name", "?"),
                status,
                record.get("task_count", 0),
            )
            if output_file:
                self._save_json(
                    {
                        "generation_info": self._build_multi_generation_info(
                            combinations=results,
                            total_combinations=len(combinations),
                            processed_combinations=index,
                            start_time=start_time,
                            status="in_progress" if index < len(combinations) else "completed",
                        ),
                        "combinations": results,
                    },
                    output_file,
                )

        final_results = {
            "generation_info": self._build_multi_generation_info(
                combinations=results,
                total_combinations=len(combinations),
                processed_combinations=len(combinations),
                start_time=start_time,
                status="completed",
            ),
            "combinations": results,
        }
        if output_file:
            self._save_json(final_results, output_file)
        return final_results

    def convert_multi_to_runner_format(
        self,
        results: dict[str, Any],
        output_file: str,
    ) -> None:
        """Convert multi-server raw results into runner format.

        Args:
            results (`dict[str, Any]`):
                Raw multi-server generation result.
            output_file (`str`):
                Output JSON path.
        """
        server_tasks: list[dict[str, Any]] = []
        for combination in results.get("combinations", []):
            if not combination.get("generation_success"):
                continue
            servers = list(combination.get("servers", []))
            formatted_tasks = [self._format_task(task, servers) for task in combination.get("generated_tasks", [])]
            if not formatted_tasks:
                continue
            server_tasks.append(
                {
                    "server_name": "+".join(servers),
                    "servers": servers,
                    "combination_name": combination.get("combination_name", ""),
                    "combination_type": combination.get("combination_type", ""),
                    "tasks": formatted_tasks,
                },
            )

        generation_info = dict(results.get("generation_info", {}))
        generation_info.pop("total_combinations", None)
        generation_info.pop("processed_combinations", None)
        self._save_json(
            {
                "generation_info": generation_info,
                "server_tasks": server_tasks,
                "total_tasks": sum(len(item["tasks"]) for item in server_tasks),
            },
            output_file,
        )

    def convert_single_to_runner_format(
        self,
        results: dict[str, Any],
        output_file: str,
    ) -> None:
        """Convert single-server raw results into runner format.

        Args:
            results (`dict[str, Any]`):
                Raw single-server generation result.
            output_file (`str`):
                Output JSON path.
        """
        server_tasks: list[dict[str, Any]] = []
        for server_result in results.get("server_tasks", []):
            if server_result.get("generation_status") != "success":
                continue
            server_name = str(server_result.get("server_name", "Unknown"))
            formatted_tasks = [self._format_task(task, [server_name]) for task in server_result.get("tasks", [])]
            if not formatted_tasks:
                continue
            server_tasks.append(
                {
                    "server_name": server_name,
                    "servers": [server_name],
                    "combination_name": f"Single Server: {server_name}",
                    "combination_type": "single_server",
                    "tasks": formatted_tasks,
                },
            )

        generation_info = dict(results.get("generation_info", {}))
        generation_info.pop("total_servers", None)
        generation_info.pop("processed_servers", None)
        self._save_json(
            {
                "generation_info": generation_info,
                "server_tasks": server_tasks,
                "total_tasks": sum(len(item["tasks"]) for item in server_tasks),
            },
            output_file,
        )

    async def _generate_with_retry(
        self,
        server_configs: list[ServerConfig],
    ) -> dict[str, Any]:
        """Discover tools and synthesize tasks with retry support.

        Args:
            server_configs (`list[ServerConfig]`):
                One or more server configs used in this generation run.

        Returns:
            `dict[str, Any]`:
                Generation status, attempts, and raw tasks.
        """
        last_error = "Unknown error"
        last_failure_stage = "unknown"
        prepared_configs = self._prepare_discovery_configs(server_configs)
        managed_dependencies = await self._ensure_dependencies(prepared_configs)
        server_label = "+".join(c.name for c in prepared_configs)
        try:
            for attempt in range(1, self.max_retries + 1):
                _logger.info(
                    "[retry] %s — attempt %d/%d",
                    server_label,
                    attempt,
                    self.max_retries,
                )
                try:
                    tools = await self.discoverer.discover_tools(prepared_configs)
                    tools = self._filter_problematic_tools(tools)
                    if not tools:
                        raise RuntimeError("No tools discovered after filtering.")
                except Exception as exc:
                    last_error = str(exc)
                    last_failure_stage = "discovery"
                    _logger.warning(
                        "[retry] %s — attempt %d failed during discovery: %s",
                        server_label,
                        attempt,
                        exc,
                    )
                    if attempt < self.max_retries:
                        wait = min(5 * attempt, 15)
                        _logger.info(
                            "[retry] %s — waiting %ds before next attempt",
                            server_label,
                            wait,
                        )
                        await asyncio.sleep(wait)
                    continue

                try:
                    _logger.info(
                        "[retry] %s — %d tool(s) discovered, starting task synthesis",
                        server_label,
                        len(tools),
                    )
                    server_name = "+".join(config.name for config in prepared_configs)
                    tasks = await self.synthesizer.generate_tasks(
                        tools=tools,
                        server_name=server_name,
                        num_tasks=self.tasks_per_server,
                        distraction_candidates=self._candidate_distraction_servers(
                            [config.name for config in prepared_configs],
                        ),
                    )
                    if not tasks:
                        raise RuntimeError("DashScope did not produce accepted tasks.")

                    _logger.info(
                        "[retry] %s — synthesis complete (%d task(s) accepted)",
                        server_label,
                        len(tasks),
                    )
                    return {
                        "status": "success",
                        "attempts": attempt,
                        "tasks": tasks,
                    }
                except Exception as exc:
                    last_error = str(exc)
                    last_failure_stage = "synthesis"
                    _logger.warning(
                        "[retry] %s — attempt %d failed during synthesis: %s",
                        server_label,
                        attempt,
                        exc,
                    )
                    if attempt < self.max_retries:
                        wait = min(5 * attempt, 15)
                        _logger.info(
                            "[retry] %s — waiting %ds before next attempt",
                            server_label,
                            wait,
                        )
                        await asyncio.sleep(wait)
        finally:
            self._teardown_dependencies(managed_dependencies)

        _logger.error(
            "[retry] %s — all %d attempt(s) exhausted: %s",
            server_label,
            self.max_retries,
            last_error,
        )
        return {
            "status": "failed",
            "attempts": self.max_retries,
            "error": last_error,
            "failure_stage": last_failure_stage,
            "tasks": [],
        }

    def _prepare_discovery_configs(
        self,
        server_configs: list[ServerConfig],
    ) -> list[ServerConfig]:
        """Convert HTTP manifest targets into self-managed discovery configs."""

        return [
            replace(config, pre_warmed=False)
            if config.transport in {"streamable_http", "sse"}
            else config
            for config in server_configs
        ]

    async def _ensure_dependencies(
        self,
        server_configs: list[ServerConfig],
    ) -> list[Any]:
        """Start missing backend dependencies required by selected servers."""

        selected_targets = [
            self.profile_targets_by_name[config.name]
            for config in server_configs
            if config.name in self.profile_targets_by_name
        ]
        managed: list[Any] = []
        for dependency in _dependency_services_for_targets(selected_targets):
            if _is_tcp_port_open("127.0.0.1", dependency.port):
                if dependency.readiness_url:
                    try:
                        await self._wait_for_http_ready(
                            dependency.readiness_url,
                            dependency.startup_timeout,
                        )
                        continue
                    except TimeoutError:
                        pass
                else:
                    continue

            if dependency.container_name:
                self._remove_container_if_exists(dependency.container_name)

            result = subprocess.run(
                dependency.start_command,
                check=False,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=max(60.0, float(dependency.startup_timeout)),
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Failed to start dependency {dependency.name}: "
                    f"{(result.stderr or result.stdout).strip()}"
                )

            await self._wait_for_port(
                dependency.port,
                float(dependency.startup_timeout),
            )
            if dependency.readiness_url:
                await self._wait_for_http_ready(
                    dependency.readiness_url,
                    float(dependency.startup_timeout),
                )
            managed.append(dependency)
        return managed

    def _teardown_dependencies(self, dependencies: list[Any]) -> None:
        """Stop dependencies that were started for one generation run."""

        for dependency in reversed(dependencies):
            try:
                subprocess.run(
                    dependency.stop_command,
                    check=False,
                    capture_output=True,
                    text=True,
                    stdin=subprocess.DEVNULL,
                    timeout=120,
                )
            except Exception:  # noqa: BLE001
                pass

    async def _wait_for_port(
        self,
        port: int,
        timeout_seconds: float,
    ) -> None:
        """Wait until one localhost TCP port accepts connections."""

        loop = asyncio.get_running_loop()
        deadline = loop.time() + max(1.0, timeout_seconds)
        while loop.time() < deadline:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection("127.0.0.1", int(port)),
                    timeout=1.0,
                )
                del reader
                writer.close()
                await writer.wait_closed()
                return
            except Exception:  # noqa: BLE001
                await asyncio.sleep(0.5)

        raise TimeoutError(f"Timed out waiting for TCP port {port}")

    async def _wait_for_http_ready(
        self,
        url: str,
        timeout_seconds: float,
    ) -> None:
        """Wait until one HTTP health endpoint returns success."""

        loop = asyncio.get_running_loop()
        deadline = loop.time() + max(1.0, timeout_seconds)
        while loop.time() < deadline:
            try:
                status_code = await asyncio.to_thread(self._http_status_code, url)
                if 200 <= status_code < 400:
                    return
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(0.5)

        raise TimeoutError(f"Timed out waiting for dependency health endpoint: {url}")

    @staticmethod
    def _http_status_code(url: str) -> int:
        """Return one HTTP status code for a health probe URL."""

        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310
            return int(getattr(response, "status", 200))

    @staticmethod
    def _remove_container_if_exists(container_name: str | None) -> None:
        """Best-effort cleanup for one docker container name."""

        if not container_name:
            return
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    async def _process_combination(
        self,
        combination: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate tasks for one multi-server combination.

        Args:
            combination (`dict[str, Any]`):
                One combination record loaded from JSON.

        Returns:
            `dict[str, Any]`:
                Combination generation result.
        """
        server_names = [str(name) for name in combination.get("servers", [])]
        selected_configs: list[ServerConfig] = []
        for server_name in server_names:
            matched = next(
                (config for config in self.server_configs if config.name == server_name),
                None,
            )
            if matched is None:
                return {
                    "combination_name": combination.get("name", ""),
                    "combination_type": combination.get("combination_type", ""),
                    "servers": server_names,
                    "description": combination.get("description", ""),
                    "generated_tasks": [],
                    "task_count": 0,
                    "generation_success": False,
                    "failure_stage": "config",
                    "error_message": f"Server configuration not found: {server_name}",
                }
            selected_configs.append(matched)

        generation = await self._generate_with_retry(selected_configs)
        return {
            "combination_name": combination.get("name", ""),
            "combination_type": combination.get("combination_type", ""),
            "servers": server_names,
            "description": combination.get("description", ""),
            "generated_tasks": generation.get("tasks", []),
            "task_count": len(generation.get("tasks", [])),
            "generation_success": generation.get("status") == "success",
            "failure_stage": (
                "none"
                if generation.get("status") == "success"
                else generation.get("failure_stage", "unknown")
            ),
            **(
                {}
                if generation.get("status") == "success"
                else {"error_message": generation.get("error", "Unknown error")}
            ),
        }

    def _prepare_combinations(
        self,
        combinations_file: str,
        start_from: str | None,
    ) -> list[dict[str, Any]]:
        """Load and flatten combination definitions.

        Args:
            combinations_file (`str`):
                JSON file containing combination groups.
            start_from (`str | None`):
                Optional combination name to resume from.

        Returns:
            `list[dict[str, Any]]`:
                Flattened combination records.
        """
        combinations_path = Path(combinations_file)
        if not combinations_path.is_absolute():
            combinations_path = Path(__file__).resolve().parent / combinations_path
        data = json.loads(combinations_path.read_text(encoding="utf-8"))

        flattened: list[dict[str, Any]] = []
        for combination_type, items in data.get("mcp_server_combinations", {}).items():
            if not isinstance(items, list):
                continue
            for item in items:
                flattened.append({**item, "combination_type": combination_type})

        if start_from:
            for index, item in enumerate(flattened):
                if item.get("name") == start_from:
                    return flattened[index:]
        return flattened

    def _filter_server_configs(
        self,
        servers: list[str] | None,
        limit: int | None,
        skip: int,
    ) -> list[ServerConfig]:
        """Filter the loaded server config set.

        Args:
            servers (`list[str] | None`):
                Optional subset of server names.
            limit (`int | None`):
                Optional limit after filtering.
            skip (`int`):
                Number of filtered servers to skip.

        Returns:
            `list[ServerConfig]`:
                Filtered server config list.
        """
        selected = self.server_configs
        if servers:
            selected = [config for config in selected if config.name in set(servers)]
        if skip > 0:
            selected = selected[skip:]
        if limit is not None:
            selected = selected[:limit]
        return selected

    def _filter_problematic_tools(
        self,
        tools: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """Optionally filter known problematic tool names.

        Args:
            tools (`dict[str, dict[str, Any]]`):
                Discovered tool metadata.

        Returns:
            `dict[str, dict[str, Any]]`:
                Filtered tool metadata.
        """
        if not self.filter_problematic or not self.problematic_tools:
            return tools
        return {
            tool_name: tool_info
            for tool_name, tool_info in tools.items()
            if tool_name not in self.problematic_tools
        }

    def _maybe_mark_unhealthy_from_generation(
        self,
        server_names: list[str],
        generation: dict[str, Any],
    ) -> None:
        """Mark runtime unhealthy servers based on failed discovery outcomes.

        Args:
            server_names (`list[str]`):
                Servers involved in the generation attempt.
            generation (`dict[str, Any]`):
                Generation result object with status/failure_stage.
        """
        if not self.self_heal_on_discovery_failure:
            return
        if generation.get("status") != "failed":
            return
        if generation.get("failure_stage") != "discovery":
            return

        newly_added = [
            name
            for name in server_names
            if name not in self._runtime_unhealthy_servers
        ]
        if not newly_added:
            return
        self._runtime_unhealthy_servers.update(newly_added)
        _logger.warning(
            "[self-heal] marked server(s) unhealthy after discovery failure: %s",
            ", ".join(newly_added),
        )

    def _format_task(
        self,
        task: dict[str, Any],
        required_servers: list[str],
    ) -> dict[str, Any]:
        """Normalize one synthesized task into runner-compatible shape.

        Args:
            task (`dict[str, Any]`):
                Raw synthesized task record.
            required_servers (`list[str]`):
                Active server names for the task.

        Returns:
            `dict[str, Any]`:
                Runner-compatible task record.
        """
        return {
            "task_id": task.get("task_id", ""),
            "task_description": task.get("task_description", ""),
            "fuzzy_description": task.get("fuzzy_description", ""),
            "dependency_analysis": task.get("dependency_analysis", ""),
            "distraction_servers": self._select_distraction_servers(
                required_servers,
                suggested_servers=task.get("distraction_servers", []),
            ),
        }

    def _candidate_distraction_servers(
        self,
        required_servers: list[str],
        limit: int = 16,
    ) -> list[str]:
        """Build one candidate pool for hard-negative routing distractors.

        Args:
            required_servers (`list[str]`):
                Servers already used by the task.
            limit (`int`, optional):
                Maximum number of candidate server names.

        Returns:
            `list[str]`:
                Candidate server names sorted for prompt stability.
        """
        excluded = set(required_servers) | {"Time MCP"}
        candidates = [name for name in self.all_server_names if name not in excluded]
        candidates.sort()
        return candidates[:limit]

    def _select_distraction_servers(
        self,
        required_servers: list[str],
        suggested_servers: list[str] | None = None,
        count: int = 10,
    ) -> list[str]:
        """Select distraction servers for one task.

        Args:
            required_servers (`list[str]`):
                Servers already used in the task.
            count (`int`, optional):
                Maximum number of distraction servers.

        Returns:
            `list[str]`:
                Sorted distraction server names.
        """
        excluded = set(required_servers) | {"Time MCP"}
        candidates = [name for name in self.all_server_names if name not in excluded]
        if not candidates:
            return []
        selected: list[str] = []
        for name in suggested_servers or []:
            normalized = str(name).strip()
            if normalized not in candidates or normalized in selected:
                continue
            selected.append(normalized)
        remaining = [name for name in candidates if name not in selected]
        if len(selected) >= count:
            selected = selected[:count]
            selected.sort()
            return selected
        import random

        if remaining:
            selected.extend(
                random.sample(
                    remaining,
                    k=min(count - len(selected), len(remaining)),
                ),
            )
        selected.sort()
        return selected

    def _build_single_generation_info(
        self,
        total_servers: int,
        processed_servers: int,
        successful_servers: int,
        failed_servers: int,
        start_time: datetime,
        status: str,
    ) -> dict[str, Any]:
        """Build summary metadata for single-server generation.

        Args:
            total_servers (`int`):
                Total number of planned servers.
            processed_servers (`int`):
                Number of processed servers.
            successful_servers (`int`):
                Number of successful servers.
            failed_servers (`int`):
                Number of failed servers.
            start_time (`datetime`):
                Generation start timestamp.
            status (`str`):
                Current generation status.

        Returns:
            `dict[str, Any]`:
                Summary metadata.
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "total_servers": total_servers,
            "processed_servers": processed_servers,
            "successful_servers": successful_servers,
            "failed_servers": failed_servers,
            "runtime_unhealthy_servers": sorted(self._runtime_unhealthy_servers),
            "generation_model": self.model_name,
            "tasks_per_server": self.tasks_per_server,
            "duration": str(datetime.now() - start_time),
            "status": status,
        }

    def _build_multi_generation_info(
        self,
        combinations: list[dict[str, Any]],
        total_combinations: int,
        processed_combinations: int,
        start_time: datetime,
        status: str,
    ) -> dict[str, Any]:
        """Build summary metadata for multi-server generation.

        Args:
            combinations (`list[dict[str, Any]]`):
                Combination generation records accumulated so far.
            total_combinations (`int`):
                Total number of planned combinations.
            processed_combinations (`int`):
                Number of processed combinations.
            start_time (`datetime`):
                Generation start timestamp.
            status (`str`):
                Current generation status.

        Returns:
            `dict[str, Any]`:
                Summary metadata.
        """
        successful = sum(1 for item in combinations if item.get("generation_success"))
        total_tasks = sum(int(item.get("task_count", 0)) for item in combinations)
        return {
            "total_combinations": total_combinations,
            "processed_combinations": processed_combinations,
            "successful_combinations": successful,
            "failed_combinations": len(combinations) - successful,
            "runtime_unhealthy_servers": sorted(self._runtime_unhealthy_servers),
            "total_tasks": total_tasks,
            "generation_timestamp": datetime.now().isoformat(),
            "generation_duration": str(datetime.now() - start_time),
            "status": status,
        }

    @staticmethod
    def _save_json(data: dict[str, Any], output_file: str) -> None:
        """Write JSON output with UTF-8 encoding.

        Args:
            data (`dict[str, Any]`):
                JSON-serializable payload.
            output_file (`str`):
                Output file path.
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )