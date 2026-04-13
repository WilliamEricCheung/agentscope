# On Demand Meta Planner Agent Example

This example refactors the meta planner pattern into an on-demand mode where the
sub-worker agent is always **aware of all available tool groups** but MCP servers
are only started when the agent decides it needs them.

## Behavioral Difference

| Aspect | Meta Planner (preload) | On Demand Meta Planner (this example) |
|---|---|---|
| Tool visibility | Agent sees all tools immediately | Agent sees all **tool groups** immediately; individual tools appear after group activation |
| MCP startup | All MCP servers start at worker creation | MCP server starts only when the agent activates the corresponding group |
| Decision maker | Framework pre-starts everything | Agent decides which groups it needs via `reset_equipped_tools` |
| Architecture | Preload | Agent-driven lazy registration |
| Resource usage | Higher (all servers idle) | Lower (only used servers run) |

## How It Works

1. All MCP tool groups (`browser_tools`, `github_tools`) are created as **inactive** at worker startup — no MCP server is started.
2. The worker agent always has `reset_equipped_tools` available, which lists every group with its description.
3. When the agent decides it needs a tool group, it calls `reset_equipped_tools(browser_tools=True)`.
4. A lazy `postprocess_func` fires: starts the Docker container, connects the MCP client, and registers the tools into that group.
5. The activated group's tools appear in the agent's next prompt; the agent proceeds with the real tools.
6. As an optimisation, a speculative pre-warming task runs in the background based on the task description so the Docker container is likely already warm by the time the agent activates it.

## Quick Start

Install AgentScope if needed:

```bash
pip install agentscope
```

Set environment variable:

```bash
export DASHSCOPE_API_KEY=your_key
```

Optional GitHub MCP (only when selected by task):

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN=your_token
```

Unified experiment config now lives in `config.py` in this folder:

- `ON_DEMAND_PREWARM_ENABLED`: one switch for both parent planner and sub-worker
	agents.
- `ON_DEMAND_STREAM_TEXT_SPECULATION_INTERVAL_TOKENS`: one threshold for both
	planner and worker stream-level periodic speculation.

Edit `config.py` directly before each experiment run.

Run:

```bash
python main.py
```

## Architecture Diagram

```
create_worker(task_description)
│
├── _build_lazy_mcp_groups(toolkit)
│   ├── create_tool_group("browser_tools", active=False)  ← no server started
│   └── create_tool_group("github_tools",  active=False)  ← no server started
│
├── register_tool_function(reset_equipped_tools,
│       postprocess_func=_make_lazy_mcp_postprocess(...))  ← lazy hook
│
├── [background] speculative pre-warm containers from task text
│
└── ReActAgent (enable_meta_tool=False)
	│
	├── sees reset_equipped_tools schema listing all groups
	├── calls reset_equipped_tools(browser_tools=True)
	│   └── postprocess_func fires:
	│       ├── _ensure_local_docker_mcp_server(playwright)  ← start NOW
	│       └── toolkit.register_mcp_client(...)             ← register NOW
	│
	└── next prompt includes all playwright tool schemas → agent uses tools
```
