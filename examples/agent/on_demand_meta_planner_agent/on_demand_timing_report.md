# On-demand MCP Timing Report

> Source log: `/mnt/wsl/docker-desktop-bind-mounts/Ubuntu/70330fca55b62ee15286e7e065a7808da43373482f67f8078d12663d9c01eae4/agentscope/examples/agent/on_demand_meta_planner_agent/on_demand_timing.log.jsonl`

> Primary KPI: `Wait After Activation (ms)`. The prewarm-start / prewarm-duration / ready-before-activation fields are useful only for low-level debugging and are often absent, so the main comparison now focuses on the actual post-activation container-ready wait time.

> `Prewarm Effective` means the speculative prewarm itself changed the container from `cold` or `resume` into a running state before formal activation.

## Aggregated Comparison by Prewarm Mode

| Mode | Runs | Avg Wait After Activation (ms) | Min Wait (ms) | Max Wait (ms) |
| --- | --- | --- | --- | --- |
| prewarm=false | 1 | 2648.398 | 2648.398 | 2648.398 |
| prewarm=true | 1 | 2487.931 | 2487.931 | 2487.931 |

## Prewarm Router Effectiveness

| Mode | Router Method | Runs | Router Matched Runs | Effective Prewarm Runs | Effectiveness Rate |
| --- | --- | --- | --- | --- | --- |
| prewarm=false | disabled | 1 | 0 | 0 | - |
| prewarm=true | keyword | 1 | 0 | 0 | - |

## Aggregated Comparison by Prewarm + Startup Mode

| Mode | Startup Mode | Runs | Avg Wait After Activation (ms) | Min Wait (ms) | Max Wait (ms) |
| --- | --- | --- | --- | --- | --- |
| prewarm=false | cold | 1 | 2648.398 | 2648.398 | 2648.398 |
| prewarm=true | cold | 1 | 2487.931 | 2487.931 | 2487.931 |

## Per-run Details

| Run ID | Started At | Prewarm | Router Method | Router Matched | Prewarm Effective | Startup Mode | Wait After Activation (ms) | Task |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| worker-1775721937393 | 2026-04-09 16:05:37 | no | disabled | - | - | cold | 2648.398 | 查询北京明天的气温预报。 |
| worker-1775722647241 | 2026-04-09 16:17:27 | yes | keyword | no | no | cold | 2487.931 | 查询北京明天的气温预报。 |
