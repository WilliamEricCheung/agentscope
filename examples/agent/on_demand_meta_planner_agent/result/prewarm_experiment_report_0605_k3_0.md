# MCP Prewarm Experiment Report

> Source dataset: `/mnt/d/Project/agentscope/laplace/mcp_dataset/laplace_tasks_single_runner_format.json`

> Sample size: `20` distinct servers, repeats per mode: `5`, random seed: `42`.

> Each trial begins by forcibly removing all prewarm-ready Laplace MCP containers and their lifecycle state so speculative prewarm always starts from a clean container state.

> `Target Match Rate` measures whether the router selected the actual server required by the sampled task. `Effectiveness Rate` is computed as `effective target prewarm runs / target matched runs`, aligned with the earlier timing-report definition but made target-specific for this experiment.

> Wait metrics are split by startup outcome: `Non-Cold` (startup_mode != cold), `Cold` (startup_mode == cold), and `Route Mismatch` (router did not select the target server).

## Resume Progress

| Completed Trials | Remaining Trials | Skipped Resumed Trials |
| --- | --- | --- |
| 400 | 0 | 0 |

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
| No Prewarm | 100 | 0 | 0.0% | 100 | 0 | - | - | 2409.128 | - | 2409.128 | 2409.128 | 708.914 | 5050.577 | cold:100 |
| Keyword Prewarm | 100 | 80 | 80.0% | 20 | 80 | 100.0% | L1:80 | 621.812 | 127.163 | 2600.406 | 2600.406 | 114.407 | 3931.656 | cold:20, running:80 |
| Semantic Prewarm | 100 | 100 | 100.0% | 0 | 100 | 100.0% | L2:100 | 135.698 | 135.698 | - | - | 108.657 | 521.677 | running:100 |
| Hybrid Prewarm | 100 | 100 | 100.0% | 0 | 100 | 100.0% | L1:80, L2:20 | 133.887 | 133.887 | - | - | 109.593 | 306.083 | running:100 |

## Per-task Comparison by Mode

| Server | Task ID | Mode | Runs | Target Match Rate | Effectiveness Rate | Avg Wait After Activation (ms) |
| --- | --- | --- | --- | --- | --- | --- |
| Bibliomantic | bibliomantic_003 | No Prewarm | 5 | 0.0% | - | 2434.035 |
| Bibliomantic | bibliomantic_003 | Keyword Prewarm | 5 | 100.0% | 100.0% | 131.218 |
| Bibliomantic | bibliomantic_003 | Semantic Prewarm | 5 | 100.0% | 100.0% | 129.120 |
| Bibliomantic | bibliomantic_003 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 123.026 |
| BioMCP | biomcp_001 | No Prewarm | 5 | 0.0% | - | 1917.213 |
| BioMCP | biomcp_001 | Keyword Prewarm | 5 | 100.0% | 100.0% | 134.838 |
| BioMCP | biomcp_001 | Semantic Prewarm | 5 | 100.0% | 100.0% | 125.160 |
| BioMCP | biomcp_001 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 128.944 |
| Call for Papers | call_for_papers_002 | No Prewarm | 5 | 0.0% | - | 2874.219 |
| Call for Papers | call_for_papers_002 | Keyword Prewarm | 5 | 100.0% | 100.0% | 127.821 |
| Call for Papers | call_for_papers_002 | Semantic Prewarm | 5 | 100.0% | 100.0% | 126.078 |
| Call for Papers | call_for_papers_002 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 125.071 |
| Car Price Evaluator | car_price_evaluator_006 | No Prewarm | 5 | 0.0% | - | 2447.718 |
| Car Price Evaluator | car_price_evaluator_006 | Keyword Prewarm | 5 | 0.0% | - | 3289.079 |
| Car Price Evaluator | car_price_evaluator_006 | Semantic Prewarm | 5 | 100.0% | 100.0% | 125.145 |
| Car Price Evaluator | car_price_evaluator_006 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 125.749 |
| Context7 | context7_000 | No Prewarm | 5 | 0.0% | - | 726.976 |
| Context7 | context7_000 | Keyword Prewarm | 5 | 100.0% | 100.0% | 124.793 |
| Context7 | context7_000 | Semantic Prewarm | 5 | 100.0% | 100.0% | 120.668 |
| Context7 | context7_000 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 124.763 |
| Game Trends | game_trends_000 | No Prewarm | 5 | 0.0% | - | 1912.370 |
| Game Trends | game_trends_000 | Keyword Prewarm | 5 | 100.0% | 100.0% | 128.329 |
| Game Trends | game_trends_000 | Semantic Prewarm | 5 | 100.0% | 100.0% | 129.330 |
| Game Trends | game_trends_000 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 125.741 |
| Google Maps | google_maps_003 | No Prewarm | 5 | 0.0% | - | 1833.066 |
| Google Maps | google_maps_003 | Keyword Prewarm | 5 | 100.0% | 100.0% | 125.408 |
| Google Maps | google_maps_003 | Semantic Prewarm | 5 | 100.0% | 100.0% | 124.579 |
| Google Maps | google_maps_003 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 123.947 |
| Medical Calculator | medical_calculator_005 | No Prewarm | 5 | 0.0% | - | 3542.034 |
| Medical Calculator | medical_calculator_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 129.321 |
| Medical Calculator | medical_calculator_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 128.981 |
| Medical Calculator | medical_calculator_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 124.611 |
| Metropolitan Museum | metropolitan_museum_005 | No Prewarm | 5 | 0.0% | - | 947.367 |
| Metropolitan Museum | metropolitan_museum_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 123.158 |
| Metropolitan Museum | metropolitan_museum_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 127.825 |
| Metropolitan Museum | metropolitan_museum_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 126.736 |
| NASA Data | nasa_data_004 | No Prewarm | 5 | 0.0% | - | 2878.906 |
| NASA Data | nasa_data_004 | Keyword Prewarm | 5 | 100.0% | 100.0% | 127.455 |
| NASA Data | nasa_data_004 | Semantic Prewarm | 5 | 100.0% | 100.0% | 132.448 |
| NASA Data | nasa_data_004 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 129.601 |
| National Parks | national_parks_003 | No Prewarm | 5 | 0.0% | - | 1800.673 |
| National Parks | national_parks_003 | Keyword Prewarm | 5 | 100.0% | 100.0% | 128.361 |
| National Parks | national_parks_003 | Semantic Prewarm | 5 | 100.0% | 100.0% | 126.390 |
| National Parks | national_parks_003 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 127.636 |
| NixOS | nixos_006 | No Prewarm | 5 | 0.0% | - | 3080.901 |
| NixOS | nixos_006 | Keyword Prewarm | 5 | 100.0% | 100.0% | 127.767 |
| NixOS | nixos_006 | Semantic Prewarm | 5 | 100.0% | 100.0% | 125.631 |
| NixOS | nixos_006 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 123.387 |
| OKX Exchange | okx_exchange_005 | No Prewarm | 5 | 0.0% | - | 1806.324 |
| OKX Exchange | okx_exchange_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 126.049 |
| OKX Exchange | okx_exchange_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 123.394 |
| OKX Exchange | okx_exchange_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 125.737 |
| OpenAPI Explorer | openapi_explorer_006 | No Prewarm | 5 | 0.0% | - | 2295.578 |
| OpenAPI Explorer | openapi_explorer_006 | Keyword Prewarm | 5 | 0.0% | - | 2636.671 |
| OpenAPI Explorer | openapi_explorer_006 | Semantic Prewarm | 5 | 100.0% | 100.0% | 314.698 |
| OpenAPI Explorer | openapi_explorer_006 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 270.631 |
| Paper Search | paper_search_001 | No Prewarm | 5 | 0.0% | - | 3086.728 |
| Paper Search | paper_search_001 | Keyword Prewarm | 5 | 100.0% | 100.0% | 121.012 |
| Paper Search | paper_search_001 | Semantic Prewarm | 5 | 100.0% | 100.0% | 127.925 |
| Paper Search | paper_search_001 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 126.185 |
| Scientific Computing | scientific_computing_004 | No Prewarm | 5 | 0.0% | - | 2889.831 |
| Scientific Computing | scientific_computing_004 | Keyword Prewarm | 5 | 100.0% | 100.0% | 129.853 |
| Scientific Computing | scientific_computing_004 | Semantic Prewarm | 5 | 100.0% | 100.0% | 126.388 |
| Scientific Computing | scientific_computing_004 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 129.634 |
| Time MCP | time_mcp_005 | No Prewarm | 5 | 0.0% | - | 3086.052 |
| Time MCP | time_mcp_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 123.534 |
| Time MCP | time_mcp_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 124.745 |
| Time MCP | time_mcp_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 122.774 |
| Unit Converter | unit_converter_002 | No Prewarm | 5 | 0.0% | - | 2873.091 |
| Unit Converter | unit_converter_002 | Keyword Prewarm | 5 | 100.0% | 100.0% | 125.687 |
| Unit Converter | unit_converter_002 | Semantic Prewarm | 5 | 100.0% | 100.0% | 125.680 |
| Unit Converter | unit_converter_002 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 127.104 |
| Weather Data | weather_data_001 | No Prewarm | 5 | 0.0% | - | 3084.679 |
| Weather Data | weather_data_001 | Keyword Prewarm | 5 | 0.0% | - | 2665.363 |
| Weather Data | weather_data_001 | Semantic Prewarm | 5 | 100.0% | 100.0% | 124.575 |
| Weather Data | weather_data_001 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 136.775 |
| Wikipedia | wikipedia_007 | No Prewarm | 5 | 0.0% | - | 2664.794 |
| Wikipedia | wikipedia_007 | Keyword Prewarm | 5 | 0.0% | - | 1810.511 |
| Wikipedia | wikipedia_007 | Semantic Prewarm | 5 | 100.0% | 100.0% | 125.204 |
| Wikipedia | wikipedia_007 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 129.690 |
