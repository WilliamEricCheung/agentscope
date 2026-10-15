# Multi-turn Plan SDG Comparison (One Page)

> Baseline artifact: `/mnt/d/Project/agentscope/examples/agent/on_demand_meta_planner_agent/result_sdg/case_blended_heavy_late/repeat_1/multiturn_plan_0615_c1_only_0.json`
> SDG artifact: `/mnt/d/Project/agentscope/examples/agent/on_demand_meta_planner_agent/result_sdg/case_blended_heavy_late/repeat_1/multiturn_plan_0615_c1_c2_0.json`

## Conclusion
C1+C2 reduced average activation wait compared with C1 only.

## A/B Metrics
| Metric | C1 Only | C1 + C2 | Delta (C1+C2 - C1) |
| --- | --- | --- | --- |
| E2E Elapsed (ms) | 1032286.627 | 634405.351 | -397881.276 |
| Worker Calls | 11 | 7 | -4 |
| Avg Wait (ms) | 688.987 | 596.815 | -92.173 |
| P50 Wait (ms) | 153.704 | 148.470 | -5.234 |
| P95 Wait (ms) | 2172.102 | 148.876 | -2023.226 |
| Cold Starts | 0 | 1 | 1 |
| Non-cold Starts | 9 | 4 | -5 |
| Telemetry Predict Calls | 0 | 52 | 52 |
| Telemetry Schedule Accepted | 70 | 43 | -27 |
| Telemetry Executor Errors | 0 | 0 | 0 |

## Notes
- This comparison uses the same fixed multi-turn dialogue script.
- Keep model/provider settings and environment stable across two runs.
- Use multiple repeated A/B pairs for stronger statistical confidence.
