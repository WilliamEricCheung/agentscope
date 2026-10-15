# Multi-turn Plan SDG Comparison (One Page)

> Baseline artifact: `/mnt/d/Project/agentscope/examples/agent/on_demand_meta_planner_agent/result_sdg/case_blended_heavy_late/repeat_2/multiturn_plan_0615_c1_only_0.json`
> SDG artifact: `/mnt/d/Project/agentscope/examples/agent/on_demand_meta_planner_agent/result_sdg/case_blended_heavy_late/repeat_2/multiturn_plan_0615_c1_c2_0.json`

## Conclusion
C1+C2 increased average activation wait compared with C1 only.

## A/B Metrics
| Metric | C1 Only | C1 + C2 | Delta (C1+C2 - C1) |
| --- | --- | --- | --- |
| E2E Elapsed (ms) | 1122677.392 | 728087.421 | -394589.971 |
| Worker Calls | 10 | 11 | 1 |
| Avg Wait (ms) | 425.647 | 695.620 | 269.973 |
| P50 Wait (ms) | 158.634 | 144.824 | -13.810 |
| P95 Wait (ms) | 173.660 | 148.413 | -25.247 |
| Cold Starts | 1 | 0 | -1 |
| Non-cold Starts | 7 | 5 | -2 |
| Telemetry Predict Calls | 0 | 56 | 56 |
| Telemetry Schedule Accepted | 68 | 59 | -9 |
| Telemetry Executor Errors | 0 | 0 | 0 |

## Notes
- This comparison uses the same fixed multi-turn dialogue script.
- Keep model/provider settings and environment stable across two runs.
- Use multiple repeated A/B pairs for stronger statistical confidence.
