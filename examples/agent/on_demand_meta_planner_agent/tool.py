# -*- coding: utf-8 -*-
"""Tool functions for on-demand meta planner example."""
import asyncio
import json
import os
from collections import OrderedDict
from typing import Any, AsyncGenerator, Callable

from pydantic import BaseModel, Field

from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.mcp import (
    MCPPrewarmRouter,
    _DockerMCPRegistrationConfig,
    _MCPServerConfigFactory,
    _ensure_local_docker_mcp_server,
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
            # Skip if tools are already registered for this group
            if any(t.group == group_name for t in toolkit.tools.values()):
                continue
            reg = registry[group_name]
            client = await _ensure_local_docker_mcp_server(
                config=reg.server_config,
                docker_run_command=reg.docker_run_command,
                headers=reg.headers,
            )
            await toolkit.register_mcp_client(client, group_name=group_name)
        return None

    return _postprocess


async def create_worker(
    task_description: str,
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

    Returns:
        `AsyncGenerator[ToolResponse, None]`:
            Streamed tool response.
    """
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
        postprocess_func=_make_lazy_mcp_postprocess(toolkit, lazy_registry),
    )

    # Phase 4: Build speculative executor covering ALL registrations so that
    # any predicted container is pre-warmed in the background while the agent
    # reasons.  This is purely an optimisation: even if pre-warming is skipped
    # the lazy postprocess will start the container on first activation.
    all_registrations = list(lazy_registry.values())
    prewarm_router = MCPPrewarmRouter()
    prewarm_executor = build_mcp_speculative_executor(all_registrations)
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
        ),
        enable_meta_tool=False,
        formatter=DashScopeChatFormatter(),
        toolkit=toolkit,
        max_iters=20,
        prompt_prewarm_router=prewarm_router,
        prompt_prewarm_executor=prewarm_executor,
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
            raise asyncio.CancelledError()

    if result:
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
