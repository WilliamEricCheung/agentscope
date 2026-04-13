# On-demand MCP Timing Report

> Source log: `/mnt/d/Project/agentscope/examples/agent/on_demand_meta_planner_agent/on_demand_timing.log.jsonl`

> Primary KPI: `Wait After Activation (ms)`. The prewarm-start / prewarm-duration / ready-before-activation fields are useful only for low-level debugging and are often absent, so the main comparison now focuses on the actual post-activation container-ready wait time.

> `Prewarm Effective` means the speculative prewarm itself changed the container from `cold` or `resume` into a running state before formal activation.

## Aggregated Comparison by Prewarm Mode

| Mode | Runs | Avg Wait After Activation (ms) | Min Wait (ms) | Max Wait (ms) |
| --- | --- | --- | --- | --- |
| prewarm=false | 2 | 1295.479 | 89.495 | 2501.463 |
| prewarm=true | 5 | 834.590 | 89.464 | 2119.663 |

## Prewarm Router Effectiveness

| Mode | Router Method | Runs | Router Matched Runs | Effective Prewarm Runs | Effectiveness Rate |
| --- | --- | --- | --- | --- | --- |
| prewarm=false | disabled | 2 | 0 | 0 | - |
| prewarm=true | keyword | 5 | 5 | 2 | 40.0% |

## Aggregated Comparison by Prewarm + Startup Mode

| Mode | Startup Mode | Runs | Avg Wait After Activation (ms) | Min Wait (ms) | Max Wait (ms) |
| --- | --- | --- | --- | --- | --- |
| prewarm=false | cold | 1 | 2501.463 | 2501.463 | 2501.463 |
| prewarm=false | running | 1 | 89.495 | 89.495 | 89.495 |
| prewarm=true | cold | 1 | 89.464 | 89.464 | 89.464 |
| prewarm=true | resume | 1 | 2119.663 | 2119.663 | 2119.663 |
| prewarm=true | running | 3 | 654.607 | 90.016 | 1779.678 |

## Per-run Details

| Run ID | Started At | Prewarm | Router Method | Router Matched | Prewarm Effective | Startup Mode | Wait After Activation (ms) | Task |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| worker-1776044652638 | 2026-04-13 09:44:12 | no | disabled | - | - | cold | 2501.463 | Get the weather forecast for Beijing for tomo... |
| worker-1776044745165 | 2026-04-13 09:45:45 | no | disabled | - | - | running | 89.495 | Find the temperature forecast for Beijing for... |
| worker-1776045244763 | 2026-04-13 09:54:04 | yes | keyword | yes | yes | resume | 2119.663 | Get the weather forecast for Beijing for tomo... |
| worker-1776045477558 | 2026-04-13 09:57:57 | yes | keyword | yes | no | running | 1779.678 | 访问欧米茄官方网站(omegawatches.com)，导航到星座(Constellati... |
| worker-1776045612722 | 2026-04-13 10:00:12 | yes | keyword | yes | no | running | 90.016 | 搜索主要电商平台（如京东、天猫国际等）上的欧米茄星座系列腕表，查找最新款的详细参数信息，包... |
| worker-1776045909073 | 2026-04-13 10:05:09 | yes | keyword | yes | no | running | 94.127 | 从腕表之家等专业手表媒体网站提取欧米茄最新款星座腕表的详细技术参数，包括具体机芯型号、精确... |
| worker-1776046061197 | 2026-04-13 10:07:41 | yes | keyword | yes | yes | cold | 89.464 | Get the weather forecast for Beijing for tomo... |
