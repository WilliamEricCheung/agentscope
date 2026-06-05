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

## Controlled Prewarm Experiment

This folder also includes a dedicated experiment runner for controlled MCP
prewarm evaluation:

```bash
python run_prewarm_experiment.py
```

The runner evaluates four experiment modes on sampled Laplace MCP tasks:

1. `none`: No Prewarm. The target MCP server is started only when formally activated.
2. `keyword`: Only L1 keyword prewarm is enabled.
3. `semantic`: Only L2 semantic prewarm is enabled.
4. `hybrid`: L1 keyword first, then L2 semantic fallback.

### Experiment Setting

- Task source: `laplace/mcp_dataset/laplace_tasks_single_runner_format.json`
- Sampling rule: randomly sample `sample_size` fuzzy descriptions from distinct servers, one task per server
- Default sample size: `20`
- Default repeats per mode and task: `5`
- Default random seed: `42`
- Default modes: `none keyword semantic hybrid`
- Execution model: strictly sequential. No parallel trials are used, so one trial cannot warm a container for another trial.
- Container isolation: before each single trial, the script forcibly removes all prewarm-ready Laplace MCP containers and clears persisted lifecycle state.
- Default output naming: auto-incremented daily files under `result/`, such as `result/prewarm_experiment_results_0428_0.jsonl`, `result/prewarm_experiment_report_0428_0.md`, and `result/prewarm_experiment_results_0428_0.plan.json`. If `0428_0` already exists, the next default run uses `0428_1`.

This means a full default run executes:

```text
20 sampled tasks x 4 modes x 5 repeats = 400 trials
```

### Required Environment

Besides the model/API settings used by `main.py`, the experiment runner also assumes:

- Docker CLI is available in the current shell
- The prewarm-ready Laplace MCP images declared in `agentscope/mcp/server_config/laplace_mcp_manifest.json` are already available locally or can be started successfully
- Semantic router artifacts are available at the default retrieval artifact directory, or you provide the corresponding environment/config used by `MCPPrewarmSemanticRouter`

### Basic Run

Run the full default experiment:

```bash
python run_prewarm_experiment.py \
	--sample-size 20 \
	--repeats 5 \
	--seed 42
```

Run only selected modes:

```bash
python run_prewarm_experiment.py \
	--modes none keyword semantic hybrid
```

Use custom output paths:

```bash
python run_prewarm_experiment.py \
	--output-log-path ./custom_prewarm_results.jsonl \
	--output-report-path ./custom_prewarm_report.md \
	--plan-path ./custom_prewarm_results.plan.json
```

### Resume And Restart

The experiment runner supports resumable execution because the full run can be long.

It writes three artifacts:

- JSONL results file: one or more records per trial
- Markdown report: rebuilt incrementally during execution
- Plan file: fixed sampled-task plan used for resume consistency

By default, rerunning the same command resumes automatically:

```bash
python run_prewarm_experiment.py \
	--sample-size 20 \
	--repeats 5 \
	--seed 42
```

When you do not provide explicit output paths, the runner allocates the next daily output slot automatically, for example `0428_0`, then `0428_1` after the earlier run artifacts already exist.

Resume behavior:

- Previously sampled tasks are reused from the persisted plan file
- Already completed trials are skipped
- Trials that only reached `started`, `failed`, or `interrupted` are not treated as completed and will run again
- If key arguments differ from the existing plan, the script raises an error instead of mixing incompatible runs

Start from scratch and discard previous artifacts:

```bash
python run_prewarm_experiment.py \
	--sample-size 20 \
	--repeats 5 \
	--seed 42 \
	--reset-output
```

Disable resume behavior explicitly:

```bash
python run_prewarm_experiment.py --no-resume --reset-output
```

### Recommended Checklist (Keyword Min-Matches)

The `keyword_min_matches_per_client` gate controls how strict L1 keyword matching is before hybrid falls back to L2 semantic routing.

Latest side-by-side comparison based on:

- `result/prewarm_experiment_results_0605_0.jsonl` (min matches = 1)
- `result/prewarm_experiment_results_0605_4.jsonl` (min matches = 2)
- `result/prewarm_experiment_results_0605_5.jsonl` (min matches = 3)

| min matches | Hybrid L1 count | Hybrid L2 fallback count | Hybrid mismatch | Hybrid cold | Hybrid avg non-cold wait (ms) | Hybrid max wait (ms) | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 95 | 0 | 5.0% | 5.0% | 126.218 | 4091.626 | Too permissive; almost no L2 fallback |
| 2 | 90 | 5 | 5.0% | 5.0% | 131.783 | 2884.165 | Balanced transition option |
| 3 | 80 | 20 | 0.0% | 0.0% | 133.887 | 306.083 | Best stability; recommended default for hybrid |

Operational checklist:

1. Start from `--keyword-min-matches-per-client 2` if you want a conservative rollout.
2. Use `--keyword-min-matches-per-client 3` when you prioritize stability and lower tail latency.
3. Always run with `--no-resume --reset-output` when comparing different threshold settings.
4. Keep experiment artifacts under `result/` to simplify review and cleanup.

### JSONL Trial Status

The JSONL output records trial lifecycle states explicitly through `trial_status`:

- `started`: the trial has begun and the script has written the initial checkpoint record
- `completed`: the trial finished successfully and includes the final timing summary
- `failed`: the trial raised an exception during execution
- `interrupted`: the trial was interrupted, for example by `KeyboardInterrupt` or task cancellation

This makes it easier to inspect partial progress in raw logs and understand what happened before a resume.

### Report Contents

The generated Markdown report includes:

- `Resume Progress`: completed trials, remaining trials, skipped resumed trials
- `Sampled Tasks`: the exact sampled fuzzy descriptions used in this run
- `Overall Comparison by Mode`: aggregate comparison across `none`, `keyword`, `semantic`, and `hybrid`
- `Per-task Comparison by Mode`: per-server/per-task breakdown across the four modes

The main metrics include:

- `Avg Wait After Activation (ms)`
- `Target Match Rate`
- `Effectiveness Rate`
- activation `startup_mode` distribution

### Notes

- The experiment runner is separate from `main.py`. It is intended for controlled benchmark-style evaluation rather than interactive demonstration.
- The report aggregates only the latest `completed` record for each trial. `started`, `failed`, and `interrupted` records are preserved in JSONL for debugging, but they do not pollute the summary metrics.
- Because each trial removes all managed Laplace MCP containers first, this experiment can be slow but gives cleaner prewarm measurements.

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
