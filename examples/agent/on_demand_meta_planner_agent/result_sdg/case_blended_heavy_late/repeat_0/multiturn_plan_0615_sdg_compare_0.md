# Multi-turn Plan SDG Comparison (One Page)

> Baseline artifact: `/mnt/d/Project/agentscope/examples/agent/on_demand_meta_planner_agent/result_sdg/case_blended_heavy_late/repeat_0/multiturn_plan_0615_c1_only_0.json`
> SDG artifact: `/mnt/d/Project/agentscope/examples/agent/on_demand_meta_planner_agent/result_sdg/case_blended_heavy_late/repeat_0/multiturn_plan_0615_c1_c2_0.json`

## Conclusion
C1+C2 increased average activation wait compared with C1 only.

## A/B Metrics
| Metric | C1 Only | C1 + C2 | Delta (C1+C2 - C1) |
| --- | --- | --- | --- |
| E2E Elapsed (ms) | 840884.242 | 1224892.407 | 384008.165 |
| Worker Calls | 10 | 5 | -5 |
| Avg Wait (ms) | 178.531 | 638.303 | 459.772 |
| P50 Wait (ms) | 151.083 | 154.589 | 3.506 |
| P95 Wait (ms) | 155.822 | 159.658 | 3.836 |
| Cold Starts | 1 | 0 | -1 |
| Non-cold Starts | 7 | 4 | -3 |
| Telemetry Predict Calls | 0 | 75 | 75 |
| Telemetry Schedule Accepted | 54 | 37 | -17 |
| Telemetry Executor Errors | 0 | 0 | 0 |

## Notes
- This comparison uses the same fixed multi-turn dialogue script.
- Keep model/provider settings and environment stable across two runs.
- Use multiple repeated A/B pairs for stronger statistical confidence.
