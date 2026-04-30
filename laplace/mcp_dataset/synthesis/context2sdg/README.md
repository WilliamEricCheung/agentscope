# Context2SDG

This subpackage contains the Contribution 2 pipeline that synthesizes SDG-oriented prompts and execution traces.

It is designed as a standalone synthesis workflow over the Laplace MCP server catalog, not as an extension of `task_synthesis.py` and not as a consumer of `prompt2task` task files.

## What It Produces

- generic batch SDG prompts over the Laplace MCP server catalog
- standalone SDG execution traces synthesized directly from the MCP server catalog
- server-level and state-level transition statistics for first-order Markov modeling

## SDG Trace Schema

Each generated trace contains:

- `trace_id`
- `source_server_scope`
- `user_request`
- `execution_trace` with `server_name`, `server_type`, `tool_name`, `tool_category`, `source_nodes`, `target_node`, and `depends_on`
- `sdg_summary.server_path`
- `sdg_summary.tool_path`
- `sdg_summary.state_artifacts`
- `sdg_summary.state_path`
- `sdg_summary.successor_candidates`
- `sdg_summary.next_server_labels`
- `sdg_summary.next_state_labels`
- `sdg_summary.parallel_server_groups`
- `sdg_summary.inferred_edges`

## Emit A Generic SDG Prompt

```bash
cd ../..
python -m laplace.mcp_dataset.synthesis.context2sdg.generate_sdg_traces \
  --emit-prompt-only \
  --batch-trace-count 200
```

## Generate Standalone SDG Traces

```bash
cd ../..
python -m laplace.mcp_dataset.synthesis.context2sdg.generate_sdg_traces \
  --trace-count 200 \
  --output laplace/mcp_dataset/laplace_sdg_traces.json \
  --checkpoint-dir laplace/mcp_dataset/synthesis/context2sdg/laplace_sdg_generation_checkpoint \
  --transition-matrix-output laplace/mcp_dataset/laplace_sdg_transition_matrices.json
```

This command is an integrated flow: it builds and saves standalone prompts into prompt shards under the checkpoint directory, then immediately calls the model to synthesize the corresponding traces into trace shards.

The final trace count is determined by `--trace-count`, subject to successful model generation.

Generation is resumable by design:

- prompts are saved incrementally under `checkpoint_dir/prompts/`
- prompt shard files use the archive-friendly pattern `sdg_prompt_shard_00000_to_00049_of_00200.json`
- traces are saved incrementally under `checkpoint_dir/traces/`
- trace shard files use the matching pattern `sdg_trace_shard_00000_to_00049_of_00200.json`
- each prompt shard and each trace shard stores up to 50 records to avoid excessive small files
- the consolidated trace JSON and transition-matrix JSON are refreshed after each newly completed trace
- `generation_manifest.json` records collection-level metadata, artifact paths, file-naming rules, timestamps, and completed trace ids
- if the network fails after 150 traces in a 200-trace run, re-running the same command resumes from trace 151 instead of regenerating the first 150

If `--transition-matrix-output` is provided, the same run also writes one JSON file containing:

- `server_transition_counts`
- `server_transition_matrix`
- `state_transition_counts`
- `state_transition_matrix`

This makes the standalone SDG workflow a one-command path from prompt generation to trace generation to Markov transition estimation.

## First-Order Markov Matrices

For server transitions, aggregate all traces by `sdg_summary.server_path` and compute:

$$
P(S_j \mid S_i) = \frac{\mathrm{Count}(S_i \rightarrow S_j)}{\sum_{k \in S} \mathrm{Count}(S_i \rightarrow S_k)}
$$

The package exposes both count-table and matrix helpers:

- `build_server_transition_counts`
- `build_server_transition_matrix`
- `build_state_transition_counts`
- `build_state_transition_matrix`

The state-level matrix uses `sdg_summary.state_path`, where each state is represented as `(Server_Type, Tool_Category)`.
