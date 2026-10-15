# Multi-turn Plan Experiment (Single Run)

> Run artifact: `/mnt/d/Project/agentscope/examples/agent/on_demand_meta_planner_agent/result_sdg/sdg_holdout_k2_20261010_retry2/repeat_12/multiturn_plan_1010_c2_only_0.json`

## Fixed Dialogue Script
1. Complete this request: I'm researching how AI models interpret classical art. Find a famous Greek vase in the Met collection, locate its physical display location, retrieve its documentation ID, then find any Hugging Face models trained on similar artifacts, and finally pull academic papers that cite those models.

For this controlled trace-replay experiment, make exactly the following two MCP calls in order. Actually call both tools and use the first result when carrying out the second step. Do not call any other tools. If a call returns an error or times out, state that it was skipped and continue to the next step without retrying or inventing results. If a listed tool is unavailable, say so explicitly.

1. Activate MCP group "laplace_huggingface" (server: Hugging Face) and call tool "search-models". Goal: Search for Hugging Face models trained on classical art or museum artifact datasets using the canonical doc ID as a semantic hint.
2. Activate MCP group "laplace_paper_search" (server: Paper Search) and call tool "search_semantic". Goal: Search Semantic Scholar for papers that cite or use the identified Hugging Face models.

Return a concise result based on the tool outputs.

## Metrics
| Metric | Value |
| --- | --- |
| Mode | c2_only |
| E2E Elapsed (ms) | 85837.402 |
| Worker Calls | 2 |
| Avg Wait (ms) | 2825.324 |
| P50 Wait (ms) | 2825.324 |
| P95 Wait (ms) | 1816.477 |
| Cold Starts | 1 |
| Non-cold Starts | 1 |
| Telemetry Prompt Route Calls | 0 |
| Telemetry Predict Calls | 3 |
| Telemetry Schedule Attempts | 4 |
| Telemetry Schedule Accepted | 3 |
| Telemetry Executor Runs | 3 |
| Telemetry Executor Errors | 0 |
