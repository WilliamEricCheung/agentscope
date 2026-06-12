# MCP Prewarm Experiment Report

> Source dataset: `/mnt/d/Project/agentscope/laplace/mcp_dataset/laplace_tasks_single_runner_format.json`

> Sample size: `20` distinct servers, repeats per mode: `5`, random seed: `42`.

> Each trial begins by forcibly removing all prewarm-ready Laplace MCP containers and their lifecycle state so speculative prewarm always starts from a clean container state.

> `Target Match Rate` measures whether the router selected the actual server required by the sampled task. `Effectiveness Rate` is computed as `effective target prewarm runs / target matched runs`, aligned with the earlier timing-report definition but made target-specific for this experiment.

> Wait metrics are split by startup outcome: `Non-Cold` (startup_mode != cold), `Cold` (startup_mode == cold), and `Route Mismatch` (router did not select the target server).

## Resume Progress

| Completed Trials | Remaining Trials | Skipped Resumed Trials |
| --- | --- | --- |
| 400 | 0 | 400 |

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
| No Prewarm | 100 | 0 | 0.0% | 100 | 0 | - | - | 2423.532 | - | 2423.532 | 2423.532 | 707.678 | 5010.441 | cold:100 |
| Keyword Prewarm | 100 | 95 | 95.0% | 5 | 94 | 98.9% | L1:94 | 786.619 | 126.730 | 11124.872 | 2302.439 | 114.513 | 55237.038 | cold:6, running:94 |
| Semantic Prewarm | 100 | 100 | 100.0% | 0 | 100 | 100.0% | L2:100 | 129.963 | 129.963 | - | - | 115.034 | 235.122 | running:100 |
| Hybrid Prewarm | 100 | 95 | 95.0% | 5 | 95 | 100.0% | L1:95 | 269.137 | 126.218 | 2984.583 | 2984.583 | 114.769 | 4091.626 | cold:5, running:95 |

## Per-task Comparison by Mode

| Server | Task ID | Mode | Runs | Target Match Rate | Effectiveness Rate | Avg Wait After Activation (ms) |
| --- | --- | --- | --- | --- | --- | --- |
| Bibliomantic | bibliomantic_003 | No Prewarm | 5 | 0.0% | - | 2246.596 |
| Bibliomantic | bibliomantic_003 | Keyword Prewarm | 5 | 100.0% | 100.0% | 122.666 |
| Bibliomantic | bibliomantic_003 | Semantic Prewarm | 5 | 100.0% | 100.0% | 125.165 |
| Bibliomantic | bibliomantic_003 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 125.510 |
| BioMCP | biomcp_001 | No Prewarm | 5 | 0.0% | - | 1887.234 |
| BioMCP | biomcp_001 | Keyword Prewarm | 5 | 100.0% | 100.0% | 130.356 |
| BioMCP | biomcp_001 | Semantic Prewarm | 5 | 100.0% | 100.0% | 128.575 |
| BioMCP | biomcp_001 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 130.285 |
| Call for Papers | call_for_papers_002 | No Prewarm | 5 | 0.0% | - | 3115.211 |
| Call for Papers | call_for_papers_002 | Keyword Prewarm | 5 | 100.0% | 80.0% | 11149.436 |
| Call for Papers | call_for_papers_002 | Semantic Prewarm | 5 | 100.0% | 100.0% | 120.980 |
| Call for Papers | call_for_papers_002 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 126.958 |
| Car Price Evaluator | car_price_evaluator_006 | No Prewarm | 5 | 0.0% | - | 3098.998 |
| Car Price Evaluator | car_price_evaluator_006 | Keyword Prewarm | 5 | 100.0% | 100.0% | 126.596 |
| Car Price Evaluator | car_price_evaluator_006 | Semantic Prewarm | 5 | 100.0% | 100.0% | 125.661 |
| Car Price Evaluator | car_price_evaluator_006 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 125.814 |
| Context7 | context7_000 | No Prewarm | 5 | 0.0% | - | 744.242 |
| Context7 | context7_000 | Keyword Prewarm | 5 | 100.0% | 100.0% | 118.778 |
| Context7 | context7_000 | Semantic Prewarm | 5 | 100.0% | 100.0% | 120.211 |
| Context7 | context7_000 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 122.145 |
| Game Trends | game_trends_000 | No Prewarm | 5 | 0.0% | - | 1958.262 |
| Game Trends | game_trends_000 | Keyword Prewarm | 5 | 100.0% | 100.0% | 127.879 |
| Game Trends | game_trends_000 | Semantic Prewarm | 5 | 100.0% | 100.0% | 125.137 |
| Game Trends | game_trends_000 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 124.463 |
| Google Maps | google_maps_003 | No Prewarm | 5 | 0.0% | - | 1832.665 |
| Google Maps | google_maps_003 | Keyword Prewarm | 5 | 100.0% | 100.0% | 123.234 |
| Google Maps | google_maps_003 | Semantic Prewarm | 5 | 100.0% | 100.0% | 122.167 |
| Google Maps | google_maps_003 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 126.050 |
| Medical Calculator | medical_calculator_005 | No Prewarm | 5 | 0.0% | - | 3108.230 |
| Medical Calculator | medical_calculator_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 131.935 |
| Medical Calculator | medical_calculator_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 126.753 |
| Medical Calculator | medical_calculator_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 132.006 |
| Metropolitan Museum | metropolitan_museum_005 | No Prewarm | 5 | 0.0% | - | 746.127 |
| Metropolitan Museum | metropolitan_museum_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 122.137 |
| Metropolitan Museum | metropolitan_museum_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 128.573 |
| Metropolitan Museum | metropolitan_museum_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 121.594 |
| NASA Data | nasa_data_004 | No Prewarm | 5 | 0.0% | - | 2448.886 |
| NASA Data | nasa_data_004 | Keyword Prewarm | 5 | 100.0% | 100.0% | 132.218 |
| NASA Data | nasa_data_004 | Semantic Prewarm | 5 | 100.0% | 100.0% | 127.261 |
| NASA Data | nasa_data_004 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 129.368 |
| National Parks | national_parks_003 | No Prewarm | 5 | 0.0% | - | 1814.451 |
| National Parks | national_parks_003 | Keyword Prewarm | 5 | 100.0% | 100.0% | 127.626 |
| National Parks | national_parks_003 | Semantic Prewarm | 5 | 100.0% | 100.0% | 122.916 |
| National Parks | national_parks_003 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 125.799 |
| NixOS | nixos_006 | No Prewarm | 5 | 0.0% | - | 2876.106 |
| NixOS | nixos_006 | Keyword Prewarm | 5 | 100.0% | 100.0% | 131.210 |
| NixOS | nixos_006 | Semantic Prewarm | 5 | 100.0% | 100.0% | 125.204 |
| NixOS | nixos_006 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 129.767 |
| OKX Exchange | okx_exchange_005 | No Prewarm | 5 | 0.0% | - | 1824.995 |
| OKX Exchange | okx_exchange_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 123.083 |
| OKX Exchange | okx_exchange_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 125.856 |
| OKX Exchange | okx_exchange_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 124.969 |
| OpenAPI Explorer | openapi_explorer_006 | No Prewarm | 5 | 0.0% | - | 2816.727 |
| OpenAPI Explorer | openapi_explorer_006 | Keyword Prewarm | 5 | 0.0% | - | 2302.439 |
| OpenAPI Explorer | openapi_explorer_006 | Semantic Prewarm | 5 | 100.0% | 100.0% | 225.204 |
| OpenAPI Explorer | openapi_explorer_006 | Hybrid Prewarm | 5 | 0.0% | - | 2984.583 |
| Paper Search | paper_search_001 | No Prewarm | 5 | 0.0% | - | 3304.760 |
| Paper Search | paper_search_001 | Keyword Prewarm | 5 | 100.0% | 100.0% | 135.195 |
| Paper Search | paper_search_001 | Semantic Prewarm | 5 | 100.0% | 100.0% | 125.502 |
| Paper Search | paper_search_001 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 131.619 |
| Scientific Computing | scientific_computing_004 | No Prewarm | 5 | 0.0% | - | 3540.491 |
| Scientific Computing | scientific_computing_004 | Keyword Prewarm | 5 | 100.0% | 100.0% | 127.294 |
| Scientific Computing | scientific_computing_004 | Semantic Prewarm | 5 | 100.0% | 100.0% | 136.405 |
| Scientific Computing | scientific_computing_004 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 122.016 |
| Time MCP | time_mcp_005 | No Prewarm | 5 | 0.0% | - | 2876.337 |
| Time MCP | time_mcp_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 129.350 |
| Time MCP | time_mcp_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 122.033 |
| Time MCP | time_mcp_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 126.522 |
| Unit Converter | unit_converter_002 | No Prewarm | 5 | 0.0% | - | 3100.602 |
| Unit Converter | unit_converter_002 | Keyword Prewarm | 5 | 100.0% | 100.0% | 127.738 |
| Unit Converter | unit_converter_002 | Semantic Prewarm | 5 | 100.0% | 100.0% | 127.487 |
| Unit Converter | unit_converter_002 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 122.855 |
| Weather Data | weather_data_001 | No Prewarm | 5 | 0.0% | - | 2673.953 |
| Weather Data | weather_data_001 | Keyword Prewarm | 5 | 100.0% | 100.0% | 122.011 |
| Weather Data | weather_data_001 | Semantic Prewarm | 5 | 100.0% | 100.0% | 118.974 |
| Weather Data | weather_data_001 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 124.785 |
| Wikipedia | wikipedia_007 | No Prewarm | 5 | 0.0% | - | 2455.778 |
| Wikipedia | wikipedia_007 | Keyword Prewarm | 5 | 100.0% | 100.0% | 121.190 |
| Wikipedia | wikipedia_007 | Semantic Prewarm | 5 | 100.0% | 100.0% | 119.188 |
| Wikipedia | wikipedia_007 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 125.625 |
