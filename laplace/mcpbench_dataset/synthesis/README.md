# DashScope Task Synthesis

This directory contains an AgentScope-native rewrite of the MCP-Bench task
synthesis pipeline.

The pipeline:

- loads server definitions from `src/agentscope/mcp/server_config/laplace_mcp_manifest.json`
- starts each Docker container in the foreground for the duration of tool
  discovery, then stops it
- discovers tool schemas via AgentScope's `HttpStatelessClient`
- uses DashScope through AgentScope's `DashScopeChatModel` to generate and
  quality-filter tasks
- exports runner-format JSON consumable by the router-model experiments under `laplace/mcpbench_dataset/router_model`

## Prerequisites

```bash
export DASHSCOPE_API_KEY=sk-...

# API-key-gated servers also need their keys in the environment
export NCI_API_KEY=...          # BioMCP
export NASA_API_KEY=...         # NASA Data
export NPS_API_KEY=...          # National Parks
export HF_TOKEN=...             # Hugging Face
export GOOGLE_MAPS_API_KEY=...  # Google Maps
```

Docker must be running and all 28 `laplace/*:local` images must be built.

## Data Volume

Each run produces at most **`--tasks-per-combination` × N** accepted tasks,
where N depends on the mode:

| Mode | N (default) | Example with `--tasks-per-combination 5` |
|------|------------|------------------------------------------|
| `single` | 28 (one per server) | ≤ 140 tasks |
| `multi` (2-server) | 5 curated combos | ≤ 25 tasks |
| `multi` (3-server) | 5 curated combos | ≤ 25 tasks |
| `all` (default) | 33 | ≤ 165 tasks |

Tasks that fail the quality threshold (solvability ≥ 8.5, utility ≥ 5.0) are
retried up to `--max-retries` times.  The actual yield is typically 80-95 % of
the maximum.

### Start/Stop All MCP Servers (WSL/Linux)

在数据合成前，推荐先批量启动所有 MCP server 容器，避免 retry 时容器未启动导致任务失败。
批量启动/停止脚本已放在 `laplace/mcp_lifecycle` 目录下：

```bash
# 启动全部 MCP server 容器（需先设置好所有 API KEY 环境变量）
cd laplace/mcp_lifecycle
bash start_all_mcp_servers.sh

# 停止全部 MCP server 容器
bash stop_all_mcp_servers.sh
```

依赖 jq 工具（`sudo apt install jq`）。

脚本会自动读取 `src/agentscope/mcp/server_config/laplace_mcp_manifest.json`，
按配置批量启动/停止所有 server。
已经在运行且端口映射正常的容器会被自动跳过；如果启动后端口未成功发布，
脚本会自动重试，默认重试 3 次。可通过环境变量 `START_RETRIES` 调整重试次数。

如需在 Windows 下运行，请在 WSL 环境中执行。

### Validate MCP Server Reliability Before Synthesis

建议在合成前先运行一次端到端验证，确认每个 server 不仅端口可达，而且
能成功完成 MCP `list_tools`（可选再做一次 tool call 冒烟调用）：

```bash
cd ../..
# Validate all servers and write a JSON report
python -m laplace.mcpbench_dataset.synthesis.validate_mcp_servers \
  --output laplace/mcpbench_dataset/server_validation_report.json \
  --fail-on-error

# Validate specific servers only
python -m laplace.mcpbench_dataset.synthesis.validate_mcp_servers \
  --servers BioMCP "Paper Search" \
  --output laplace/mcpbench_dataset/server_validation_report_partial.json

# Optional: enable one-tool smoke call (higher confidence, more intrusive)
python -m laplace.mcpbench_dataset.synthesis.validate_mcp_servers \
  --enable-smoke-call \
  --timeout 30 \
  --output laplace/mcpbench_dataset/server_validation_report_smoke.json
```

验证报告会包含：

- 容器是否在运行（docker ps）
- 端口映射是否匹配 manifest 中的 host port
- TCP 连通性检查
- MCP `list_tools` 是否成功、返回工具数量
- 可选的 tool call 冒烟结果

可以将报告中 `status != "pass"` 的 server 先排除，再进入任务合成流程。

### One-Command Validated Synthesis

现在可以直接在生成脚本里启用“先验证，再白名单合成”的一体化流程：

```bash
cd ../..
# Validate all servers -> generate whitelist -> run single-server synthesis on pass servers only
python -m laplace.mcpbench_dataset.synthesis.generate_benchmark_tasks \
  --mode single \
  --auto-validate-servers \
  --validation-timeout 20 \
  --validation-concurrency 8 \
  --output laplace/mcpbench_dataset \
  --tasks-per-combination 2 \
  --dashscope-model qwen3-max

# Same flow for multi-server synthesis (combinations containing unavailable servers are auto-dropped)
python -m laplace.mcpbench_dataset.synthesis.generate_benchmark_tasks \
  --mode multi \
  --auto-validate-servers \
  --output laplace/mcpbench_dataset \
  --combinations-file split_combinations/mcp_2server_combinations.json
```

新增参数：

- `--auto-validate-servers`：先运行服务器验证，仅对 `pass` 服务进行合成。
- `--validation-timeout`：验证阶段的超时秒数。
- `--validation-concurrency`：验证阶段并发度。
- `--validation-enable-smoke-call`：验证时增加一次可选 tool call 冒烟检查。
- `--validation-output`：自定义验证报告输出路径。
- `--server-whitelist-file`：从 JSON/TXT 白名单文件读取可用服务。
- `--whitelist-output`：保存最终生效白名单 JSON。
- `--disable-self-heal-on-discovery-failure`：关闭运行时自愈（默认开启）。

运行时自愈默认开启：当某个服务在任务生成中连续出现 `discovery` 失败时，
会被动态标记为不健康，后续包含该服务的组合会自动跳过，避免长跑任务被
同一个坏服务重复拖慢。

当 `--server-whitelist-file` 与 `--auto-validate-servers` 同时启用时，会取两者交集作为最终白名单。
## Quick Start

From the AgentScope repository root:

```bash
# Single-server tasks (28 servers, 2 tasks each → up to 56 tasks)
python -m laplace.mcpbench_dataset.synthesis.generate_benchmark_tasks \
  --mode single \
  --tasks-per-combination 2 \
  --dashscope-model qwen3-max

# Multi-server tasks (5 curated 2-server combos, 2 tasks each → up to 10 tasks)
python -m laplace.mcpbench_dataset.synthesis.generate_benchmark_tasks \
  --mode multi \
  --combinations-file split_combinations/mcp_2server_combinations.json \
  --tasks-per-combination 2 \
  --dashscope-model qwen3-max

# Both modes in one run (up to 66 tasks with default settings)
python -m laplace.mcpbench_dataset.synthesis.generate_benchmark_tasks \
  --mode all \
  --tasks-per-combination 2 \
  --dashscope-model qwen3-max

# Single specific server
python -m laplace.mcpbench_dataset.synthesis.generate_benchmark_tasks \
  --server "Wikipedia" \
  --tasks-per-combination 2

# Merge multiple single-server runner-format outputs into one dataset
python -m laplace.mcpbench_dataset.synthesis.merge_single_runner_format \
  laplace/mcpbench_dataset/benchmark_tasks_single_20260420_runner_format.json \
  laplace/mcpbench_dataset/benchmark_tasks_single_20260423_runner_format.json \
  laplace/mcpbench_dataset/benchmark_tasks_single_04231516_runner_format.json \
  --output laplace/mcpbench_dataset/laplace_tasks_single_runner_format.json

# Auto-discover all matching single runner-format outputs under the mcpbench_dataset directory
python -m laplace.mcpbench_dataset.synthesis.merge_single_runner_format \
  --search-root laplace/mcpbench_dataset \
  --glob 'benchmark_tasks_single_*_runner_format.json' \
  --output laplace/mcpbench_dataset/laplace_tasks_single_runner_format.json

# Incremental update: if laplace_tasks_single_runner_format.json already exists,
# it is reused as the baseline and only newly discovered benchmark_tasks_single_* files are appended
python -m laplace.mcpbench_dataset.synthesis.merge_single_runner_format \
  --search-root laplace/mcpbench_dataset \
  --output laplace/mcpbench_dataset/laplace_tasks_single_runner_format.json

# Auto-discover all matching multi runner-format outputs and merge into one file
python -m laplace.mcpbench_dataset.synthesis.merge_multi_runner_format \
  --search-root laplace/mcpbench_dataset \
  --glob 'benchmark_tasks_multi_*_runner_format.json' \
  --output laplace/mcpbench_dataset/laplace_tasks_multi_runner_format.json
```

合并时会按文件顺序聚合同一 server 的任务，并自动将 `task_id` 重编号为
连续的 incremental 形式，例如 `biomcp_000`, `biomcp_001`, `biomcp_002`。
这样即使不同批次里原始 `task_id` 重名，也会在最终合并文件中变成唯一值。

当输出文件已经存在时，脚本会优先把该 merged 文件作为基线输入，读取其中
记录的 `merged_from_files`，然后只追加此前尚未并入的新 raw runner-format 文件。

## CLI Reference

| Argument | Default | Description |
|----------|---------|-------------|
| `--mode` | `all` | `single` / `multi` / `all` |
| `--tasks-per-combination` | `1` | Accepted tasks per server or combo |
| `--max-retries` | `3` | Retries per server when quality threshold not met |
| `--dashscope-model` | `qwen3-max` | DashScope model name |
| `--combinations-file` | `split_combinations/mcp_2server_combinations.json` | JSON file with server combos |
| `--server` | — | Generate for one named server only |
| `--output` | `laplace/mcpbench_dataset/` | Output directory |
| `--manifest-path` | auto-detected | Override path to `src/agentscope/mcp/server_config/laplace_mcp_manifest.json` |
| `--disable-filter-problematic` | off | Skip quality filtering |

DashScope authentication uses `DASHSCOPE_API_KEY` from the environment.

## Outputs

Each run saves two files per mode:

- `benchmark_tasks_{mode}_{timestamp}.json` — raw synthesis result
- `benchmark_tasks_{mode}_{timestamp}_runner_format.json` — runner-format JSON with
  `server_tasks`, `task_description`, `fuzzy_description`,
  `dependency_analysis`, and `distraction_servers`

The default `timestamp` format is `MMDDHHMM` (for example, `04231645`). This
prevents repeated runs on the same day from overwriting earlier artifacts unless
they start within the same minute.

The runner-format files are compatible with the fastText training scripts in
`laplace/mcpbench_dataset`.

## Extending Combinations

To add more multi-server combinations, edit the JSON files under
`split_combinations/`.  The 2-server file currently has **5 curated combos**
and the 3-server file has **5 curated combos**; you can add as many as needed.
