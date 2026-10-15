# Multi-turn Plan Experiment (Single Run)

> Run artifact: `/mnt/d/Project/agentscope/examples/agent/on_demand_meta_planner_agent/result_sdg/sdg_on_demand_20repeats_20261009/repeat_10/multiturn_plan_1009_on_demand_0.json`

## Fixed Dialogue Script
1. Create one worker task and make the tool calls in this exact order: first use the Math MCP group to calculate the mean of 12 and 24; next activate and use the Unit Converter group to convert 3 kilometers to meters. Do not skip either tool call or compute the answers mentally. Return only the two tool results.

## Metrics
| Metric | Value |
| --- | --- |
| Mode | on_demand |
| E2E Elapsed (ms) | 19890.911 |
| Worker Calls | 1 |
| Avg Wait (ms) | 1817.826 |
| P50 Wait (ms) | 1817.826 |
| P95 Wait (ms) | 1817.826 |
| Cold Starts | 1 |
| Non-cold Starts | 0 |
| Telemetry Prompt Route Calls | 0 |
| Telemetry Predict Calls | 0 |
| Telemetry Schedule Attempts | 0 |
| Telemetry Schedule Accepted | 0 |
| Telemetry Executor Runs | 0 |
| Telemetry Executor Errors | 0 |
