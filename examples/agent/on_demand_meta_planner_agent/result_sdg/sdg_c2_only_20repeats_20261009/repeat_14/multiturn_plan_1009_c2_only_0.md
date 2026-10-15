# Multi-turn Plan Experiment (Single Run)

> Run artifact: `/mnt/d/Project/agentscope/examples/agent/on_demand_meta_planner_agent/result_sdg/sdg_c2_only_20repeats_20261009/repeat_14/multiturn_plan_1009_c2_only_0.json`

## Fixed Dialogue Script
1. Create one worker task and make the tool calls in this exact order: first use the Math MCP group to calculate the mean of 12 and 24; next activate and use the Unit Converter group to convert 3 kilometers to meters. Do not skip either tool call or compute the answers mentally. Return only the two tool results.

## Metrics
| Metric | Value |
| --- | --- |
| Mode | c2_only |
| E2E Elapsed (ms) | 18743.641 |
| Worker Calls | 1 |
| Avg Wait (ms) | 1789.542 |
| P50 Wait (ms) | 1789.542 |
| P95 Wait (ms) | 1789.542 |
| Cold Starts | 0 |
| Non-cold Starts | 1 |
| Telemetry Prompt Route Calls | 0 |
| Telemetry Predict Calls | 2 |
| Telemetry Schedule Attempts | 2 |
| Telemetry Schedule Accepted | 2 |
| Telemetry Executor Runs | 2 |
| Telemetry Executor Errors | 0 |
