# MCP Prewarm Experiment Report

> Source dataset: `/mnt/d/Project/agentscope/laplace/mcp_dataset/laplace_tasks_single_runner_format.json`

> Sample size: `5` distinct servers, repeats per mode: `20`, random seed: `42`.

> Each trial begins by forcibly removing all prewarm-ready Laplace MCP containers and their lifecycle state so speculative prewarm always starts from a clean container state.

> `Target Match Rate` measures whether the router selected the actual server required by the sampled task. `Effectiveness Rate` is computed as `effective target prewarm runs / target matched runs`, aligned with the earlier timing-report definition but made target-specific for this experiment.

## Resume Progress

| Completed Trials | Remaining Trials | Skipped Resumed Trials |
| --- | --- | --- |
| 400 | 0 | 400 |

## Sampled Tasks

| Server | Task ID | Fuzzy Description |
| --- | --- | --- |
| OpenAPI Explorer | openapi_explorer_001 | I need a clear summary of key details from the Stripe API’s OpenAPI specificatio... |
| Car Price Evaluator | car_price_evaluator_001 | I need a detailed report on car brands and their models’ current market prices. ... |
| Bibliomantic | bibliomantic_001 | I’m trying to decide whether I should accept a new job offer sometime in the nex... |
| Scientific Computing | scientific_computing_005 | I have a 2×2 matrix A with entries [4, 1, 2, 3] (so the first row is [4, 1] and ... |
| Google Maps | google_maps_000 | I'm looking for the highest-rated coffee shop that’s currently open within 1,500... |

## Overall Comparison by Mode

| Mode | Runs | Target Match Runs | Target Match Rate | Effective Prewarm Runs | Effectiveness Rate | Effective Route Breakdown | Avg Wait After Activation (ms) | Min Wait (ms) | Max Wait (ms) | Activation Startup Modes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| No Prewarm | 100 | 0 | 0.0% | 0 | - | - | 2382.734 | 1757.053 | 4882.283 | cold:100 |
| Keyword Prewarm | 100 | 100 | 100.0% | 100 | 100.0% | L1:100 | 102.270 | 82.994 | 159.480 | running:100 |
| Semantic Prewarm | 100 | 100 | 100.0% | 100 | 100.0% | L2:100 | 101.603 | 80.563 | 155.016 | running:100 |
| Hybrid Prewarm | 100 | 100 | 100.0% | 100 | 100.0% | L1:100 | 102.795 | 76.618 | 159.777 | running:100 |

## Per-task Comparison by Mode

| Server | Task ID | Mode | Runs | Target Match Rate | Effectiveness Rate | Avg Wait After Activation (ms) |
| --- | --- | --- | --- | --- | --- | --- |
| Bibliomantic | bibliomantic_001 | No Prewarm | 20 | 0.0% | - | 2408.603 |
| Bibliomantic | bibliomantic_001 | Keyword Prewarm | 20 | 100.0% | 100.0% | 92.364 |
| Bibliomantic | bibliomantic_001 | Semantic Prewarm | 20 | 100.0% | 100.0% | 89.885 |
| Bibliomantic | bibliomantic_001 | Hybrid Prewarm | 20 | 100.0% | 100.0% | 97.391 |
| Car Price Evaluator | car_price_evaluator_001 | No Prewarm | 20 | 0.0% | - | 1839.879 |
| Car Price Evaluator | car_price_evaluator_001 | Keyword Prewarm | 20 | 100.0% | 100.0% | 90.008 |
| Car Price Evaluator | car_price_evaluator_001 | Semantic Prewarm | 20 | 100.0% | 100.0% | 89.944 |
| Car Price Evaluator | car_price_evaluator_001 | Hybrid Prewarm | 20 | 100.0% | 100.0% | 90.694 |
| Google Maps | google_maps_000 | No Prewarm | 20 | 0.0% | - | 1795.460 |
| Google Maps | google_maps_000 | Keyword Prewarm | 20 | 100.0% | 100.0% | 89.370 |
| Google Maps | google_maps_000 | Semantic Prewarm | 20 | 100.0% | 100.0% | 89.329 |
| Google Maps | google_maps_000 | Hybrid Prewarm | 20 | 100.0% | 100.0% | 88.247 |
| OpenAPI Explorer | openapi_explorer_001 | No Prewarm | 20 | 0.0% | - | 2852.589 |
| OpenAPI Explorer | openapi_explorer_001 | Keyword Prewarm | 20 | 100.0% | 100.0% | 147.642 |
| OpenAPI Explorer | openapi_explorer_001 | Semantic Prewarm | 20 | 100.0% | 100.0% | 148.754 |
| OpenAPI Explorer | openapi_explorer_001 | Hybrid Prewarm | 20 | 100.0% | 100.0% | 147.664 |
| Scientific Computing | scientific_computing_005 | No Prewarm | 20 | 0.0% | - | 3017.140 |
| Scientific Computing | scientific_computing_005 | Keyword Prewarm | 20 | 100.0% | 100.0% | 91.966 |
| Scientific Computing | scientific_computing_005 | Semantic Prewarm | 20 | 100.0% | 100.0% | 90.100 |
| Scientific Computing | scientific_computing_005 | Hybrid Prewarm | 20 | 100.0% | 100.0% | 89.978 |
