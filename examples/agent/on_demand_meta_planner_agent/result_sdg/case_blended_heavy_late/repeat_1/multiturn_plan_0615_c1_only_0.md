# Multi-turn Plan Experiment (Single Run)

> Run artifact: `/mnt/d/Project/agentscope/examples/agent/on_demand_meta_planner_agent/result_sdg/case_blended_heavy_late/repeat_1/multiturn_plan_0615_c1_only_0.json`

## Fixed Dialogue Script
1. 先把任务拆为三阶段：问题定义、证据检索、复现实验建议；第一轮只给计划，不要调用工具。
2. 先做问题定义：针对'多轮规划代理在真实工具环境中的稳健性'，给出评估维度和可观测指标。
3. 进入证据检索：先用 Paper Search 找到相关工作，再补充一个可复现实验环境建议（需要时参考 NixOS）。
4. 最后生成可执行分析方案：给出一个 Jupyter MCP 中可落地的 notebook 结构草案与最小代码块说明。

## Metrics
| Metric | Value |
| --- | --- |
| Mode | c1_only |
| E2E Elapsed (ms) | 1032286.627 |
| Worker Calls | 11 |
| Avg Wait (ms) | 688.987 |
| P50 Wait (ms) | 153.704 |
| P95 Wait (ms) | 2172.102 |
| Cold Starts | 0 |
| Non-cold Starts | 9 |
| Telemetry Prompt Route Calls | 535 |
| Telemetry Predict Calls | 0 |
| Telemetry Schedule Attempts | 624 |
| Telemetry Schedule Accepted | 70 |
| Telemetry Executor Runs | 70 |
| Telemetry Executor Errors | 0 |
