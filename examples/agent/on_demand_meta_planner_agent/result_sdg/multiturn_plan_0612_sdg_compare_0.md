# Multi-turn Plan SDG Comparison (One Page)

> Baseline artifact: `/mnt/d/Project/agentscope/examples/agent/on_demand_meta_planner_agent/result_sdg/multiturn_plan_0612_c1_only_0.json`
> SDG artifact: `/mnt/d/Project/agentscope/examples/agent/on_demand_meta_planner_agent/result_sdg/multiturn_plan_0612_c1_c2_0.json`

## Conclusion
C1+C2 reduced average activation wait compared with C1 only.

## A/B Metrics
| Metric | C1 Only | C1 + C2 | Delta (C1+C2 - C1) |
| --- | --- | --- | --- |
| Worker Calls | 6 | 2 | -4 |
| Avg Wait (ms) | 540.058 | 92.143 | -447.914 |
| P50 Wait (ms) | 96.112 | 92.143 | -3.969 |
| P95 Wait (ms) | 97.904 | 86.202 | -11.702 |
| Cold Starts | 0 | 0 | 0 |
| Non-cold Starts | 6 | 2 | -4 |
| Telemetry Predict Calls | 0 | 26 | 26 |
| Telemetry Schedule Accepted | 45 | 9 | -36 |
| Telemetry Executor Errors | 0 | 0 | 0 |

## Notes
- This comparison uses the same fixed multi-turn dialogue script.
- Keep model/provider settings and environment stable across two runs.
- Use multiple repeated A/B pairs for stronger statistical confidence.
