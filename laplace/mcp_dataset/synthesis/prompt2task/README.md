# Prompt2Task

This subpackage contains the Contribution 1 pipeline that synthesizes MCP-Bench style tasks and exports runner-format datasets used by the router-model experiments under `laplace/router_model`.

The pipeline:

- loads server definitions from `src/agentscope/mcp/server_config/laplace_mcp_manifest.json`
- starts and validates MCP servers before discovery when requested
- discovers tool schemas via AgentScope's MCP client path
- uses DashScope to generate and quality-filter tasks
- exports runner-format JSON consumable by router-model experiments

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

## Validate MCP Servers

```bash
cd ../..
python -m laplace.util.validate_mcp_servers \
  --output laplace/mcp_dataset/server_validation_report.json \
  --fail-on-error
```

## Generate Router-Model Tasks

```bash
cd ../..
python -m laplace.mcp_dataset.synthesis.prompt2task.generate_benchmark_tasks \
  --mode single \
  --tasks-per-combination 2 \
  --dashscope-model qwen3-max

python -m laplace.mcp_dataset.synthesis.prompt2task.generate_benchmark_tasks \
  --mode multi \
  --combinations-file split_combinations/mcp_2server_combinations.json \
  --tasks-per-combination 2 \
  --dashscope-model qwen3-max
```

## One-Command Validated Synthesis

```bash
cd ../..
python -m laplace.mcp_dataset.synthesis.prompt2task.generate_benchmark_tasks \
  --mode single \
  --auto-validate-servers \
  --validation-timeout 20 \
  --validation-concurrency 8 \
  --output laplace/mcp_dataset \
  --tasks-per-combination 2 \
  --dashscope-model qwen3-max
```

## Merge Runner-Format Outputs

```bash
cd ../..
python -m laplace.mcp_dataset.synthesis.prompt2task.merge_single_runner_format \
  --search-root laplace/mcp_dataset \
  --output laplace/mcp_dataset/laplace_tasks_single_runner_format.json

python -m laplace.mcp_dataset.synthesis.prompt2task.merge_multi_runner_format \
  --search-root laplace/mcp_dataset \
  --glob 'benchmark_tasks_multi_*_runner_format.json' \
  --output laplace/mcp_dataset/laplace_tasks_multi_runner_format.json
```

## Outputs

Each run saves two files per mode:

- `benchmark_tasks_{mode}_{timestamp}.json`: raw synthesis result
- `benchmark_tasks_{mode}_{timestamp}_runner_format.json`: runner-format payload with `server_tasks`, `task_description`, `fuzzy_description`, `dependency_analysis`, and `distraction_servers`
