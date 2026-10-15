# Multi-turn Plan Experiment (Single Run)

> Run artifact: `/mnt/d/Project/agentscope/examples/agent/on_demand_meta_planner_agent/result_sdg/case_blended_heavy_late/repeat_0/multiturn_plan_0615_c1_only_0.json`

## Fixed Dialogue Script
1. 先把任务拆为三阶段：问题定义、证据检索、复现实验建议；第一轮只给计划，不要调用工具。
2. 先做问题定义：针对'多轮规划代理在真实工具环境中的稳健性'，给出评估维度和可观测指标。
3. 进入证据检索：先用 Paper Search 找到相关工作，再补充一个可复现实验环境建议（需要时参考 NixOS）。
4. 最后生成可执行分析方案：给出一个 Jupyter MCP 中可落地的 notebook 结构草案与最小代码块说明。

## Metrics
| Metric | Value |
| --- | --- |
| Mode | c1_only |
| E2E Elapsed (ms) | 840884.242 |
| Worker Calls | 10 |
| Avg Wait (ms) | 178.531 |
| P50 Wait (ms) | 151.083 |
| P95 Wait (ms) | 155.822 |
| Cold Starts | 1 |
| Non-cold Starts | 7 |
| Telemetry Prompt Route Calls | 305 |
| Telemetry Predict Calls | 0 |
| Telemetry Schedule Attempts | 337 |
| Telemetry Schedule Accepted | 54 |
| Telemetry Executor Runs | 54 |
| Telemetry Executor Errors | 0 |
