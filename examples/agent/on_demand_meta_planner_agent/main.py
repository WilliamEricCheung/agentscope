# -*- coding: utf-8 -*-
"""On Demand Meta Planner agent example."""
import asyncio
import os

from config import (
    ON_DEMAND_PREDICTIVE_PREWARM_ENABLED,
    ON_DEMAND_PREWARM_ENABLED,
    ON_DEMAND_PREWARM_TELEMETRY_ENABLED,
    ON_DEMAND_PREWARM_TELEMETRY_MAX_EVENTS,
    ON_DEMAND_STREAM_TEXT_SPECULATION_INTERVAL_TOKENS,
    normalize_stream_text_speculation_interval_tokens,
)
from tool import create_worker

from agentscope.agent import ReActAgent, UserAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.mcp import (
    MCPLaplaceController,
    MCPLaplaceControllerConfig,
    MCPPrewarmHybridRouter,
    build_mcp_speculative_executor,
    load_laplace_registration_configs,
)
from agentscope.model import DashScopeChatModel
from agentscope.plan import PlanNotebook
from agentscope.tool import Toolkit


async def main() -> None:
    """Run the on-demand planner example."""
    # Connect to studio for better visualization (optional).
    import agentscope

    agentscope.init(
        project="on_demand_meta_planner_agent",
        studio_url="http://localhost:3000",
    )

    toolkit = Toolkit()
    toolkit.register_tool_function(create_worker)

    planner_stream_text_interval = normalize_stream_text_speculation_interval_tokens(
        ON_DEMAND_STREAM_TEXT_SPECULATION_INTERVAL_TOKENS,
    )
    all_registrations = load_laplace_registration_configs()
    planner_prewarm_registrations = [
        reg
        for reg in all_registrations.values()
        if reg.group_name in {"browser_tools", "github_tools"}
    ]
    if "GITHUB_PERSONAL_ACCESS_TOKEN" not in os.environ:
        planner_prewarm_registrations = [
            reg
            for reg in planner_prewarm_registrations
            if reg.group_name != "github_tools"
        ]
    if not any(
        reg.group_name == "browser_tools"
        for reg in planner_prewarm_registrations
    ):
        raise ValueError(
            "`browser_tools` registration is missing in laplace_mcp_manifest.json.",
        )

    planner_controller = MCPLaplaceController(
        prompt_prewarm_router=(
            MCPPrewarmHybridRouter() if ON_DEMAND_PREWARM_ENABLED else None
        ),
        prompt_prewarm_executor=(
            build_mcp_speculative_executor(planner_prewarm_registrations)
            if ON_DEMAND_PREWARM_ENABLED
            else None
        ),
        config=MCPLaplaceControllerConfig(
            prompt_prewarm_enabled=ON_DEMAND_PREWARM_ENABLED,
            predictive_warmer_enabled=ON_DEMAND_PREDICTIVE_PREWARM_ENABLED,
            telemetry_enabled=ON_DEMAND_PREWARM_TELEMETRY_ENABLED,
            telemetry_max_events=ON_DEMAND_PREWARM_TELEMETRY_MAX_EVENTS,
            telemetry_name="on_demand_planner",
        ),
    )

    planner = ReActAgent(
        name="Friday",
        # pylint: disable=C0301
        sys_prompt="""You are Friday, a multifunctional agent that can help people solving different complex tasks. You act like a meta planner to solve complicated tasks by decomposing the task and building/orchestrating different worker agents to finish the sub-tasks.

## Core Mission
Your primary purpose is to break down complicated tasks into manageable subtasks (a plan), create worker agents to finish the subtask, and coordinate their execution to achieve the user's goal efficiently.

### Important Constraints
1. DO NOT TRY TO SOLVE THE SUBTASKS DIRECTLY yourself.
2. Always follow the plan sequence.
3. DO NOT finish the plan until all subtasks are finished.
""",  # noqa: E501
        model=DashScopeChatModel(
            model_name="qwen3-max",
            api_key=os.environ["DASHSCOPE_API_KEY"],
            stream_text_speculation_interval_tokens=(
                planner_stream_text_interval
                if ON_DEMAND_PREWARM_ENABLED
                else None
            ),
        ),
        formatter=DashScopeChatFormatter(),
        plan_notebook=PlanNotebook(),
        toolkit=toolkit,
        max_iters=20,
        mcp_laplace_controller=planner_controller,
    )

    user = UserAgent(name="user")

    msg = None
    while True:
        msg = await planner(msg)
        msg = await user(msg)
        if msg.get_text_content() == "exit":
            break


asyncio.run(main())
