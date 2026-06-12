# MCP Prewarm Experiment Report

> Source dataset: `/mnt/d/Project/agentscope/laplace/mcp_dataset/laplace_tasks_single_runner_format.json`

> Sample size: `20` distinct servers, repeats per mode: `5`, random seed: `42`.

> Each trial begins by forcibly removing all prewarm-ready Laplace MCP containers and their lifecycle state so speculative prewarm always starts from a clean container state.

> `Target Match Rate` measures whether the router selected the actual server required by the sampled task. `Effectiveness Rate` is computed as `effective target prewarm runs / target matched runs`, aligned with the earlier timing-report definition but made target-specific for this experiment.

> Wait metrics are split by startup outcome: `Non-Cold` (startup_mode != cold), `Cold` (startup_mode == cold), and `Route Mismatch` (router did not select the target server).

## Resume Progress

| Completed Trials | Remaining Trials | Skipped Resumed Trials |
| --- | --- | --- |
| 100 | 0 | 0 |

## Sampled Tasks

| Server | Task ID | Fuzzy Description |
| --- | --- | --- |
| Game Trends | game_trends_000 | Can you give me a detailed, up-to-date overview of what games are trending right... |
| Bibliomantic | bibliomantic_003 | I’m trying to decide whether I should accept a new job offer sometime in the nex... |
| OpenAPI Explorer | openapi_explorer_006 | Hey, I'm trying to figure out if we can use the official X (Twitter) API for our... |
| Google Maps | google_maps_003 | I'm near the Empire State Building in New York City and looking for the best cof... |
| Wikipedia | wikipedia_007 | I'm putting together a presentation on how our understanding of black holes has ... |
| Scientific Computing | scientific_computing_004 | I need help with a linear algebra calculation. Start with a 2×2 matrix A = [[4, ... |
| Context7 | context7_000 | I'm building a real-time dashboard with React and think I'll go with Next.js, th... |
| Unit Converter | unit_converter_002 | I need help with a multi-part unit conversion and calculation task. First, conve... |
| Car Price Evaluator | car_price_evaluator_006 | Hey, I’m helping my cousin figure out which new car to buy in Brazil, and we’re ... |
| OKX Exchange | okx_exchange_005 | Can you check if the OKX exchange is currently operational and then get me the l... |
| NASA Data | nasa_data_004 | Can you put together a detailed space weather and planetary observation report c... |
| Call for Papers | call_for_papers_002 | Can you find up to five academic conferences happening in the next three months ... |
| National Parks | national_parks_003 | I'm planning a Pacific Northwest trip through California, Oregon, and Washington... |
| Medical Calculator | medical_calculator_005 | I’m preparing for an upcoming elective intraperitoneal surgery in the next three... |
| BioMCP | biomcp_001 | My relative was just diagnosed with metastatic melanoma and tested positive for ... |
| Weather Data | weather_data_001 | I need a weather consistency report for the first three cities whose names start... |
| NixOS | nixos_006 | Hey, I’m trying to get a consistent dev setup going for my team on NixOS, and we... |
| Paper Search | paper_search_001 | I'm part of a research group looking into the latest privacy-preserving federate... |
| Metropolitan Museum | metropolitan_museum_005 | I’m looking for the painting titled “The Harvesters” at the Metropolitan Museum ... |
| Time MCP | time_mcp_005 | What time will it be in Tokyo when it’s 14:30 in London three days from today? T... |

## Overall Comparison by Mode

| Mode | Runs | Target Match Runs | Target Match Rate | Route Mismatch Runs | Effective Prewarm Runs | Effectiveness Rate | Effective Route Breakdown | Avg Wait (All, ms) | Avg Wait (Non-Cold, ms) | Avg Wait (Cold, ms) | Avg Wait (Route Mismatch, ms) | Min Wait (ms) | Max Wait (ms) | Activation Startup Modes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hybrid Prewarm | 100 | 55 | 55.0% | 45 | 55 | 100.0% | weighted:55 | 1308.378 | 112.693 | 2769.769 | 2769.769 | 90.544 | 6239.558 | cold:45, running:55 |

## Per-task Comparison by Mode

| Server | Task ID | Mode | Runs | Target Match Rate | Effectiveness Rate | Avg Wait After Activation (ms) |
| --- | --- | --- | --- | --- | --- | --- |
| Bibliomantic | bibliomantic_003 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 113.856 |
| BioMCP | biomcp_001 | Hybrid Prewarm | 5 | 0.0% | - | 1994.068 |
| Call for Papers | call_for_papers_002 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 120.347 |
| Car Price Evaluator | car_price_evaluator_006 | Hybrid Prewarm | 5 | 0.0% | - | 2922.589 |
| Context7 | context7_000 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 107.894 |
| Game Trends | game_trends_000 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 112.018 |
| Google Maps | google_maps_003 | Hybrid Prewarm | 5 | 0.0% | - | 1893.123 |
| Medical Calculator | medical_calculator_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 113.510 |
| Metropolitan Museum | metropolitan_museum_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 108.984 |
| NASA Data | nasa_data_004 | Hybrid Prewarm | 5 | 0.0% | - | 4004.147 |
| National Parks | national_parks_003 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 110.918 |
| NixOS | nixos_006 | Hybrid Prewarm | 5 | 0.0% | - | 2921.058 |
| OKX Exchange | okx_exchange_005 | Hybrid Prewarm | 5 | 0.0% | - | 1893.509 |
| OpenAPI Explorer | openapi_explorer_006 | Hybrid Prewarm | 5 | 0.0% | - | 3028.218 |
| Paper Search | paper_search_001 | Hybrid Prewarm | 5 | 0.0% | - | 3151.042 |
| Scientific Computing | scientific_computing_004 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 115.314 |
| Time MCP | time_mcp_005 | Hybrid Prewarm | 5 | 0.0% | - | 3120.170 |
| Unit Converter | unit_converter_002 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 111.486 |
| Weather Data | weather_data_001 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 112.679 |
| Wikipedia | wikipedia_007 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 112.621 |
