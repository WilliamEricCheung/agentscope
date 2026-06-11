# -*- coding: utf-8 -*-
"""Tool functions for on-demand meta planner example."""
import asyncio
import inspect
import json
import os
import time
from collections import OrderedDict
from typing import Any, AsyncGenerator, Callable

from pydantic import BaseModel, Field

from config import (
    ON_DEMAND_PREDICTIVE_PREWARM_ENABLED,
    ON_DEMAND_PREWARM_ENABLED,
    ON_DEMAND_PREWARM_TELEMETRY_ENABLED,
    ON_DEMAND_PREWARM_TELEMETRY_MAX_EVENTS,
    ON_DEMAND_STREAM_TEXT_SPECULATION_INTERVAL_TOKENS,
    normalize_stream_text_speculation_interval_tokens,
)

from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.mcp import (
    MCPLaplaceController,
    MCPLaplaceControllerConfig,
    MCPPrewarmHybridRouter,
    MCPPrewarmRouter,
    _DockerMCPRegistrationConfig,
    _MCPServerConfigFactory,
    _build_mcp_timing_summary,
    _create_mcp_timing_run,
    _ensure_local_docker_mcp_server,
    _record_mcp_timing_event,
    _save_mcp_timing_log,
    build_mcp_speculative_executor,
)
from agentscope.message import Msg, TextBlock
from agentscope.model import DashScopeChatModel
from agentscope.pipeline import stream_printing_messages
from agentscope.tool import (
    ToolResponse,
    Toolkit,
    insert_text_file,
    view_text_file,
    write_text_file,
)


_TIMING_LOG_PATH = os.path.join(
    os.path.dirname(__file__),
    "on_demand_timing.log.jsonl",
)


class ResultModel(BaseModel):
    """Result schema for worker output."""

    success: bool = Field(
        description="Whether the task was successful or not.",
    )
    message: str = Field(
        description=(
            "The specific task result, should include necessary details, "
            "e.g. the file path if any file is generated, the deviation, "
            "and the error message if any."
        ),
    )


def _convert_to_text_block(msgs: list[Msg]) -> list[TextBlock]:
    """Convert model messages into streamed text blocks."""
    blocks: list = []
    for msg in msgs:
        for block in msg.get_content_blocks():
            if block["type"] == "text":
                blocks.append(block)
            elif block["type"] == "tool_use":
                blocks.append(
                    TextBlock(
                        type="text",
                        text=f"Calling tool {block['name']} ...",
                    ),
                )

    return blocks


def _summarize_group_description(
    registration: _DockerMCPRegistrationConfig,
) -> str:
    """Build the pre-activation description shown in `reset_equipped_tools`.

    Args:
        registration (`_DockerMCPRegistrationConfig`):
            The MCP registration metadata.

    Returns:
        `str`:
            A concise description with representative tool names.
    """
    if not registration.tool_names:
        return registration.group_description

    preview = ", ".join(registration.tool_names[:5])
    return (
        f"{registration.group_description} Representative tools: {preview}."
    )


def _build_lazy_mcp_groups(
    toolkit: Toolkit,
) -> dict[str, _DockerMCPRegistrationConfig]:
    """Create all MCP tool groups as inactive and return the lazy registry.

    Groups are created without any tools registered.  Tools are added later
    in :func:`_make_lazy_mcp_postprocess` when the agent activates a group.

    Args:
        toolkit (`Toolkit`):
            Toolkit to create groups on.

    Returns:
        `dict[str, _DockerMCPRegistrationConfig]`:
            Mapping from group_name to registration config for lazy lookup.
    """
    registry: dict[str, _DockerMCPRegistrationConfig] = {}

    browser_reg = _MCPServerConfigFactory.build_playwright_registration_config()
    toolkit.create_tool_group(
        group_name=browser_reg.group_name,
        description=_summarize_group_description(browser_reg),
        notes=browser_reg.group_notes,
    )
    registry[browser_reg.group_name] = browser_reg

    github_reg = _MCPServerConfigFactory.build_github_registration_config()
    if github_reg is not None:
        toolkit.create_tool_group(
            group_name=github_reg.group_name,
            description=_summarize_group_description(github_reg),
            notes=github_reg.group_notes,
        )
        registry[github_reg.group_name] = github_reg

    return registry


def _make_lazy_mcp_postprocess(
    toolkit: Toolkit,
    registry: dict[str, _DockerMCPRegistrationConfig],
    timing_run: dict[str, Any],
) -> Callable[[Any, ToolResponse], Any]:
    """Create a postprocess_func that lazily starts MCP servers on activation.

    The returned callable is used as the ``postprocess_func`` argument when
    registering ``reset_equipped_tools``.  Each time the agent calls
    ``reset_equipped_tools`` to activate a tool group, this function checks
    whether the group belongs to an MCP server that has not been started yet.
    If so, it starts the Docker container, connects the MCP client, and
    registers the tools into the group before the result is returned to the
    agent.

    Args:
        toolkit (`Toolkit`):
            The toolkit to register MCP tools into.
        registry (`dict[str, _DockerMCPRegistrationConfig]`):
            Mapping from group_name to registration config.

    Returns:
        `Callable[[Any, ToolResponse], Any]`:
            Async postprocess function compatible with ``register_tool_function``.
    """

    async def _postprocess(
        tool_call: Any,
        response: ToolResponse,
    ) -> ToolResponse | None:
        input_kwargs: dict[str, bool] = tool_call.get("input", {}) or {}
        for group_name, activate in input_kwargs.items():
            if not activate or group_name not in registry:
                continue

            _record_mcp_timing_event(
                timing_run,
                "tool_group_activation_requested",
                group_name=group_name,
            )

            # Skip if tools are already registered for this group
            if any(t.group == group_name for t in toolkit.tools.values()):
                _record_mcp_timing_event(
                    timing_run,
                    "mcp_group_already_registered",
                    group_name=group_name,
                )
                continue

            reg = registry[group_name]
            client = await _ensure_local_docker_mcp_server(
                config=reg.server_config,
                docker_run_command=reg.docker_run_command,
                headers=reg.headers,
            )
            _record_mcp_timing_event(
                timing_run,
                "mcp_server_ready",
                group_name=group_name,
                startup_mode=getattr(client, "startup_mode", None),
            )
            await toolkit.register_mcp_client(client, group_name=group_name)
            _record_mcp_timing_event(
                timing_run,
                "mcp_tools_registered",
                group_name=group_name,
                tool_count=sum(
                    1
                    for tool in toolkit.tools.values()
                    if tool.group == group_name
                ),
            )
        return None

    return _postprocess


def _build_logged_prewarm_router(
    router: MCPPrewarmRouter,
    timing_run: dict[str, Any],
    candidate_effective_route_methods: dict[str, str],
) -> Callable[[Msg | list[Msg] | None], Any]:
    """Wrap a prewarm router so routing decisions are recorded.

    Args:
        router (`MCPPrewarmRouter`):
            The underlying prewarm router.
        timing_run (`dict[str, Any]`):
            Mutable timing context for the current run.
        candidate_effective_route_methods (`dict[str, str]`):
            Mutable mapping from candidate name to the effective route method
            that selected it.

    Returns:
        `Callable[[Msg | list[Msg] | None], Any]`:
            A router wrapper that records method and matched candidates.
    """
    configured_router_method = str(getattr(router, "method", "unknown"))
    _record_mcp_timing_event(
        timing_run,
        "prewarm_router_enabled",
        configured_router_method=configured_router_method,
    )

    async def _router(msg: Msg | list[Msg] | None) -> list[str]:
        candidates_or_awaitable = router(msg)
        if inspect.isawaitable(candidates_or_awaitable):
            candidates = await candidates_or_awaitable
        else:
            candidates = candidates_or_awaitable

        router_method = str(
            getattr(router, "last_route_method", configured_router_method),
        )

        normalized_candidates = sorted(
            {str(candidate).strip() for candidate in candidates or [] if candidate},
        )
        if normalized_candidates:
            for candidate in normalized_candidates:
                candidate_effective_route_methods[candidate] = router_method
            _record_mcp_timing_event(
                timing_run,
                "prewarm_router_matched",
                configured_router_method=configured_router_method,
                effective_route_method=router_method,
                candidate_count=len(normalized_candidates),
                candidates=",".join(normalized_candidates),
            )
        else:
            _record_mcp_timing_event(
                timing_run,
                "prewarm_router_no_match",
                configured_router_method=configured_router_method,
                effective_route_method=router_method,
                candidate_count=0,
            )

        return normalized_candidates

    return _router


def _build_logged_prewarm_executor(
    registrations: list[_DockerMCPRegistrationConfig],
    timing_run: dict[str, Any],
    configured_router_method: str,
    candidate_effective_route_methods: dict[str, str],
) -> Callable[[str], Any]:
    """Wrap the speculative pre-warm executor with timing logs.

    Args:
        registrations (`list[_DockerMCPRegistrationConfig]`):
            The MCP registrations that can be pre-warmed.
        timing_run (`dict[str, Any]`):
            Mutable timing context for the current run.
        configured_router_method (`str`):
            The configured prewarm routing method for this run.
        candidate_effective_route_methods (`dict[str, str]`):
            Mutable mapping from candidate name to the effective route method
            that selected it.

    Returns:
        `Callable[[str], Any]`:
            An async executor that records candidate-level timings.
    """
    base_executor = build_mcp_speculative_executor(registrations)

    async def _executor(candidate: str) -> None:
        effective_route_method = candidate_effective_route_methods.get(
            candidate,
            configured_router_method,
        )
        _record_mcp_timing_event(
            timing_run,
            "prewarm_candidate_started",
            candidate=candidate,
            configured_router_method=configured_router_method,
            effective_route_method=effective_route_method,
        )
        started_at = time.perf_counter()
        try:
            client = await base_executor(candidate)
            startup_mode = getattr(client, "startup_mode", None)
            effective = startup_mode in {"cold", "resume"}
            _record_mcp_timing_event(
                timing_run,
                "prewarm_candidate_finished",
                candidate=candidate,
                configured_router_method=configured_router_method,
                effective_route_method=effective_route_method,
                startup_mode=startup_mode,
                effective=effective,
                duration_ms=round(
                    (time.perf_counter() - started_at) * 1000,
                    3,
                ),
            )
        except Exception as exc:
            _record_mcp_timing_event(
                timing_run,
                "prewarm_candidate_failed",
                candidate=candidate,
                configured_router_method=configured_router_method,
                effective_route_method=effective_route_method,
                duration_ms=round(
                    (time.perf_counter() - started_at) * 1000,
                    3,
                ),
                error=str(exc),
            )
            raise

    return _executor


async def create_worker(
    task_description: str,
    prewarm: bool = ON_DEMAND_PREWARM_ENABLED,
    stream_text_speculation_interval_tokens: int | None = (
        ON_DEMAND_STREAM_TEXT_SPECULATION_INTERVAL_TOKENS
    ),
) -> AsyncGenerator[ToolResponse, None]:
    """Create a sub-worker and execute task with on-demand MCP strategy.

    The agent is aware of **all** available tool groups from the start
    (they appear in the ``reset_equipped_tools`` schema).  MCP servers are
    started and tools are registered only when the agent explicitly activates
    a group, keeping idle containers off.

    Additionally, a speculative pre-warming task runs in the background based
    on the task description so that the Docker container is likely already
    running by the time the agent activates the corresponding group.

    Args:
        task_description (`str`):
            The sub-task assigned by planner.
        prewarm (`bool`, defaults to `False`):
            Whether to enable prompt-level speculative pre-warming before the
            worker explicitly activates a tool group. Set this to `True` to
            compare the latency difference between pure on-demand mode and
            on-demand + prewarm mode.
        stream_text_speculation_interval_tokens (`int | None`, optional):
            The example-level periodic speculation threshold used during token
            streaming. Smaller values speculate earlier and more often; `None`
            or non-positive values disable the periodic text-based path while
            keeping explicit tool-name speculation available.

    Returns:
        `AsyncGenerator[ToolResponse, None]`:
            Streamed tool response.
    """
    timing_run = _create_mcp_timing_run(
        task_description=task_description,
        prewarm=prewarm,
    )
    resolved_stream_text_speculation_interval_tokens = (
        normalize_stream_text_speculation_interval_tokens(
            stream_text_speculation_interval_tokens,
        )
    )
    timing_run["stream_text_speculation_interval_tokens"] = (
        resolved_stream_text_speculation_interval_tokens
    )

    toolkit = Toolkit()

    # Phase 1: Pre-create all MCP tool groups as inactive (no tools yet).
    # The agent sees these group names and descriptions through the
    # reset_equipped_tools schema and can decide which ones to activate.
    lazy_registry = _build_lazy_mcp_groups(toolkit)

    # Phase 2: Register basic file operation tools (always available).
    toolkit.register_tool_function(write_text_file)
    toolkit.register_tool_function(insert_text_file)
    toolkit.register_tool_function(view_text_file)

    # Phase 3: Register reset_equipped_tools with a lazy MCP postprocess hook.
    # enable_meta_tool=False is used below so that ReActAgent does not
    # register a plain reset_equipped_tools without the postprocess.
    toolkit.register_tool_function(
        toolkit.reset_equipped_tools,
        postprocess_func=_make_lazy_mcp_postprocess(
            toolkit,
            lazy_registry,
            timing_run,
        ),
    )

    # Phase 4: Optionally enable speculative executor for comparison.
    all_registrations = list(lazy_registry.values())
    if prewarm:
        base_prewarm_router = MCPPrewarmHybridRouter()
        candidate_effective_route_methods: dict[str, str] = {}
        router_method = str(
            getattr(base_prewarm_router, "method", "unknown"),
        )
        prewarm_router = _build_logged_prewarm_router(
            base_prewarm_router,
            timing_run,
            candidate_effective_route_methods,
        )
        prewarm_executor = _build_logged_prewarm_executor(
            all_registrations,
            timing_run,
            configured_router_method=router_method,
            candidate_effective_route_methods=candidate_effective_route_methods,
        )
        laplace_controller = MCPLaplaceController(
            prompt_prewarm_router=prewarm_router,
            prompt_prewarm_executor=prewarm_executor,
            config=MCPLaplaceControllerConfig(
                prompt_prewarm_enabled=ON_DEMAND_PREWARM_ENABLED,
                predictive_warmer_enabled=ON_DEMAND_PREDICTIVE_PREWARM_ENABLED,
                telemetry_enabled=ON_DEMAND_PREWARM_TELEMETRY_ENABLED,
                telemetry_max_events=ON_DEMAND_PREWARM_TELEMETRY_MAX_EVENTS,
                telemetry_name="on_demand_worker",
            ),
        )
        _record_mcp_timing_event(
            timing_run,
            "stream_text_speculation_configured",
            interval_tokens=resolved_stream_text_speculation_interval_tokens,
        )
    else:
        laplace_controller = MCPLaplaceController(
            config=MCPLaplaceControllerConfig(
                prompt_prewarm_enabled=False,
                predictive_warmer_enabled=False,
                telemetry_enabled=ON_DEMAND_PREWARM_TELEMETRY_ENABLED,
                telemetry_max_events=ON_DEMAND_PREWARM_TELEMETRY_MAX_EVENTS,
                telemetry_name="on_demand_worker",
            ),
        )

    available_groups = "\n".join(
        f"- {reg.group_name}: {_summarize_group_description(reg)}"
        for reg in all_registrations
    )

    sub_agent = ReActAgent(
        name="Worker",
        # pylint: disable=C0301
        sys_prompt=f"""You're an agent named Worker.

## Your Target
Your target is to finish the given task with your tools.

## Available Tool Groups
Some tool groups are available but initially inactive. You can activate them by calling `reset_equipped_tools`.

{available_groups}

## Current Mode
- Prompt pre-warm enabled: {prewarm}
- Stream-level speculation interval (tokens): {resolved_stream_text_speculation_interval_tokens if prewarm else 'disabled'}
- Even when pre-warm is disabled, you can still activate tool groups on demand.

## Activation Rules
- If the task needs live or current online information (such as weather, news, prices, maps, or website content), activate `browser_tools` first.
- If the task involves GitHub repositories, files, issues, commits, branches, or pull requests, activate `github_tools` first.
- Do not say you lack internet or GitHub access until you have checked whether a relevant tool group can be activated.
- After activating a group, continue the task using the newly available tools.

## IMPORTANT
You MUST use `reset_equipped_tools` whenever the task requires an inactive tool group.
You MUST use the {ReActAgent.finish_function_name} to generate the final answer after finishing the task.
""",
        model=DashScopeChatModel(
            model_name="qwen3-max",
            api_key=os.environ["DASHSCOPE_API_KEY"],
            stream_text_speculation_interval_tokens=(
                resolved_stream_text_speculation_interval_tokens
                if prewarm
                else None
            ),
        ),
        enable_meta_tool=False,
        formatter=DashScopeChatFormatter(),
        toolkit=toolkit,
        max_iters=20,
        mcp_laplace_controller=laplace_controller,
    )

    sub_agent.set_console_output_enabled(False)

    msgs = OrderedDict()
    result = []

    async def call_sub_agent() -> None:
        msg_res = await sub_agent(
            Msg(
                "user",
                content=task_description,
                role="user",
            ),
            structured_model=ResultModel,
        )
        result.append(msg_res)

    try:
        async for msg, _ in stream_printing_messages(
            agents=[sub_agent],
            coroutine_task=call_sub_agent(),
        ):
            msgs[msg.id] = msg

            yield ToolResponse(
                content=_convert_to_text_block(list(msgs.values())),
                stream=True,
                is_last=False,
            )

            if msg.metadata and msg.metadata.get("_is_interrupted", False):
                _record_mcp_timing_event(timing_run, "worker_interrupted")
                raise asyncio.CancelledError()
    except Exception as exc:
        _record_mcp_timing_event(
            timing_run,
            "worker_failed",
            error=str(exc),
        )
        _save_mcp_timing_log(timing_run, _TIMING_LOG_PATH)
        raise

    if result:
        timing_summary = _build_mcp_timing_summary(timing_run)
        prewarm_telemetry = laplace_controller.get_telemetry_snapshot()
        timing_run["prewarm_controller_telemetry"] = prewarm_telemetry
        log_path = _save_mcp_timing_log(timing_run, _TIMING_LOG_PATH)

        # Report which MCP tool groups were actually activated (lazy-started).
        activated_groups = [
            group_name
            for group_name in lazy_registry
            if any(t.group == group_name for t in toolkit.tools.values())
        ]
        yield ToolResponse(
            content=[
                *_convert_to_text_block(list(msgs.values())),
                TextBlock(
                    type="text",
                    text=(
                        "On-demand activated tool groups: "
                        f"{json.dumps(activated_groups, ensure_ascii=False)}"
                    ),
                ),
                TextBlock(
                    type="text",
                    text=(
                        "MCP readiness summary (ms): "
                        f"{json.dumps(timing_summary, ensure_ascii=False)}"
                    ),
                ),
                TextBlock(
                    type="text",
                    text=(
                        "Prewarm controller telemetry stats: "
                        f"{json.dumps(prewarm_telemetry.get('stats', {}), ensure_ascii=False)}"
                    ),
                ),
                TextBlock(
                    type="text",
                    text=f"Timing log saved to: {log_path}",
                ),
                TextBlock(
                    type="text",
                    text=json.dumps(
                        result[0].metadata,
                        indent=2,
                        ensure_ascii=False,
                    ),
                ),
            ],
            stream=True,
            is_last=True,
        )
