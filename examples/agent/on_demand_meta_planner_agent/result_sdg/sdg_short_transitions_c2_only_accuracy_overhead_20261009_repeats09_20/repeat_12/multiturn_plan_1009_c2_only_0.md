# Multi-turn Plan Experiment (Single Run)

> Run artifact: `/mnt/d/Project/agentscope/examples/agent/on_demand_meta_planner_agent/result_sdg/sdg_short_transitions_c2_only_accuracy_overhead_20261009_repeats09_20/repeat_12/multiturn_plan_1009_c2_only_0.json`

## Fixed Dialogue Script
1. Complete this request: I'm designing an educational AR app about ancient Egyptian artifacts. Find a prominent artifact from the Met's collection, get its location, identify nearby subway stations, find a matching open-source icon for 'ancient Egypt', and locate a recent scholarly paper discussing its cultural significance.

For this controlled trace-replay experiment, make exactly the following two MCP calls in order. Actually call both tools and use the first result when carrying out the second step. Do not call any other tools. If a call returns an error or times out, state that it was skipped and continue to the next step without retrying or inventing results. If a listed tool is unavailable, say so explicitly.

1. Activate MCP group "laplace_huge_icons" (server: Huge Icons) and call tool "search_icons". Goal: Search for an open-source icon representing 'ancient Egypt' for UI use.
2. Activate MCP group "laplace_wikipedia" (server: Wikipedia) and call tool "search_wikipedia". Goal: Find a Wikipedia article about the specific artifact to extract scholarly context.

Return a concise result based on the tool outputs.

## Metrics
| Metric | Value |
| --- | --- |
| Mode | c2_only |
| E2E Elapsed (ms) | 108804.783 |
| Worker Calls | 2 |
| Avg Wait (ms) | 935.714 |
| P50 Wait (ms) | 935.714 |
| P95 Wait (ms) | 78.863 |
| Cold Starts | 2 |
| Non-cold Starts | 0 |
| Telemetry Prompt Route Calls | 0 |
| Telemetry Predict Calls | 11 |
| Telemetry Schedule Attempts | 11 |
| Telemetry Schedule Accepted | 2 |
| Telemetry Executor Runs | 2 |
| Telemetry Executor Errors | 0 |
