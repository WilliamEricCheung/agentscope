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
| No Prewarm | 100 | 0 | 0.0% | 100 | 0 | - | - | 2437.517 | - | 2437.517 | 2437.517 | 714.811 | 3976.284 | cold:100 |
| Keyword Prewarm | 100 | 95 | 95.0% | 5 | 95 | 100.0% | L1:95 | 241.416 | 128.182 | 2392.866 | 2392.866 | 118.378 | 2637.237 | cold:5, running:95 |
| Semantic Prewarm | 100 | 100 | 100.0% | 0 | 100 | 100.0% | L2:100 | 136.012 | 136.012 | - | - | 112.969 | 511.505 | running:100 |
| Hybrid Prewarm | 100 | 95 | 95.0% | 5 | 95 | 100.0% | L1:95 | 246.865 | 128.457 | 2496.604 | 2496.604 | 108.384 | 3302.978 | cold:5, running:95 |

## Per-task Comparison by Mode

| Server | Task ID | Mode | Runs | Target Match Rate | Effectiveness Rate | Avg Wait After Activation (ms) |
| --- | --- | --- | --- | --- | --- | --- |
| Bibliomantic | bibliomantic_003 | No Prewarm | 5 | 0.0% | - | 2873.088 |
| Bibliomantic | bibliomantic_003 | Keyword Prewarm | 5 | 100.0% | 100.0% | 124.865 |
| Bibliomantic | bibliomantic_003 | Semantic Prewarm | 5 | 100.0% | 100.0% | 126.592 |
| Bibliomantic | bibliomantic_003 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 124.696 |
| BioMCP | biomcp_001 | No Prewarm | 5 | 0.0% | - | 1878.314 |
| BioMCP | biomcp_001 | Keyword Prewarm | 5 | 100.0% | 100.0% | 133.877 |
| BioMCP | biomcp_001 | Semantic Prewarm | 5 | 100.0% | 100.0% | 124.584 |
| BioMCP | biomcp_001 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 133.558 |
| Call for Papers | call_for_papers_002 | No Prewarm | 5 | 0.0% | - | 3089.994 |
| Call for Papers | call_for_papers_002 | Keyword Prewarm | 5 | 100.0% | 100.0% | 132.527 |
| Call for Papers | call_for_papers_002 | Semantic Prewarm | 5 | 100.0% | 100.0% | 127.430 |
| Call for Papers | call_for_papers_002 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 133.041 |
| Car Price Evaluator | car_price_evaluator_006 | No Prewarm | 5 | 0.0% | - | 2872.005 |
| Car Price Evaluator | car_price_evaluator_006 | Keyword Prewarm | 5 | 100.0% | 100.0% | 131.321 |
| Car Price Evaluator | car_price_evaluator_006 | Semantic Prewarm | 5 | 100.0% | 100.0% | 129.435 |
| Car Price Evaluator | car_price_evaluator_006 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 131.472 |
| Context7 | context7_000 | No Prewarm | 5 | 0.0% | - | 746.677 |
| Context7 | context7_000 | Keyword Prewarm | 5 | 100.0% | 100.0% | 122.478 |
| Context7 | context7_000 | Semantic Prewarm | 5 | 100.0% | 100.0% | 124.004 |
| Context7 | context7_000 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 123.395 |
| Game Trends | game_trends_000 | No Prewarm | 5 | 0.0% | - | 1869.287 |
| Game Trends | game_trends_000 | Keyword Prewarm | 5 | 100.0% | 100.0% | 124.972 |
| Game Trends | game_trends_000 | Semantic Prewarm | 5 | 100.0% | 100.0% | 123.575 |
| Game Trends | game_trends_000 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 137.439 |
| Google Maps | google_maps_003 | No Prewarm | 5 | 0.0% | - | 1807.521 |
| Google Maps | google_maps_003 | Keyword Prewarm | 5 | 100.0% | 100.0% | 127.082 |
| Google Maps | google_maps_003 | Semantic Prewarm | 5 | 100.0% | 100.0% | 125.116 |
| Google Maps | google_maps_003 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 126.326 |
| Medical Calculator | medical_calculator_005 | No Prewarm | 5 | 0.0% | - | 2897.742 |
| Medical Calculator | medical_calculator_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 130.255 |
| Medical Calculator | medical_calculator_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 127.040 |
| Medical Calculator | medical_calculator_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 128.831 |
| Metropolitan Museum | metropolitan_museum_005 | No Prewarm | 5 | 0.0% | - | 743.408 |
| Metropolitan Museum | metropolitan_museum_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 121.448 |
| Metropolitan Museum | metropolitan_museum_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 132.354 |
| Metropolitan Museum | metropolitan_museum_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 118.875 |
| NASA Data | nasa_data_004 | No Prewarm | 5 | 0.0% | - | 3293.368 |
| NASA Data | nasa_data_004 | Keyword Prewarm | 5 | 100.0% | 100.0% | 133.087 |
| NASA Data | nasa_data_004 | Semantic Prewarm | 5 | 100.0% | 100.0% | 129.004 |
| NASA Data | nasa_data_004 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 132.198 |
| National Parks | national_parks_003 | No Prewarm | 5 | 0.0% | - | 1811.682 |
| National Parks | national_parks_003 | Keyword Prewarm | 5 | 100.0% | 100.0% | 131.032 |
| National Parks | national_parks_003 | Semantic Prewarm | 5 | 100.0% | 100.0% | 123.886 |
| National Parks | national_parks_003 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 131.565 |
| NixOS | nixos_006 | No Prewarm | 5 | 0.0% | - | 2866.527 |
| NixOS | nixos_006 | Keyword Prewarm | 5 | 100.0% | 100.0% | 127.606 |
| NixOS | nixos_006 | Semantic Prewarm | 5 | 100.0% | 100.0% | 127.101 |
| NixOS | nixos_006 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 128.180 |
| OKX Exchange | okx_exchange_005 | No Prewarm | 5 | 0.0% | - | 1811.633 |
| OKX Exchange | okx_exchange_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 126.818 |
| OKX Exchange | okx_exchange_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 126.264 |
| OKX Exchange | okx_exchange_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 123.666 |
| OpenAPI Explorer | openapi_explorer_006 | No Prewarm | 5 | 0.0% | - | 2912.094 |
| OpenAPI Explorer | openapi_explorer_006 | Keyword Prewarm | 5 | 0.0% | - | 2392.866 |
| OpenAPI Explorer | openapi_explorer_006 | Semantic Prewarm | 5 | 100.0% | 100.0% | 318.888 |
| OpenAPI Explorer | openapi_explorer_006 | Hybrid Prewarm | 5 | 0.0% | - | 2496.604 |
| Paper Search | paper_search_001 | No Prewarm | 5 | 0.0% | - | 3090.638 |
| Paper Search | paper_search_001 | Keyword Prewarm | 5 | 100.0% | 100.0% | 138.785 |
| Paper Search | paper_search_001 | Semantic Prewarm | 5 | 100.0% | 100.0% | 126.379 |
| Paper Search | paper_search_001 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 129.381 |
| Scientific Computing | scientific_computing_004 | No Prewarm | 5 | 0.0% | - | 3336.503 |
| Scientific Computing | scientific_computing_004 | Keyword Prewarm | 5 | 100.0% | 100.0% | 125.944 |
| Scientific Computing | scientific_computing_004 | Semantic Prewarm | 5 | 100.0% | 100.0% | 126.234 |
| Scientific Computing | scientific_computing_004 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 127.117 |
| Time MCP | time_mcp_005 | No Prewarm | 5 | 0.0% | - | 3092.976 |
| Time MCP | time_mcp_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 124.712 |
| Time MCP | time_mcp_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 124.748 |
| Time MCP | time_mcp_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 126.696 |
| Unit Converter | unit_converter_002 | No Prewarm | 5 | 0.0% | - | 2654.343 |
| Unit Converter | unit_converter_002 | Keyword Prewarm | 5 | 100.0% | 100.0% | 127.153 |
| Unit Converter | unit_converter_002 | Semantic Prewarm | 5 | 100.0% | 100.0% | 127.890 |
| Unit Converter | unit_converter_002 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 130.991 |
| Weather Data | weather_data_001 | No Prewarm | 5 | 0.0% | - | 2665.957 |
| Weather Data | weather_data_001 | Keyword Prewarm | 5 | 100.0% | 100.0% | 125.098 |
| Weather Data | weather_data_001 | Semantic Prewarm | 5 | 100.0% | 100.0% | 125.343 |
| Weather Data | weather_data_001 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 126.944 |
| Wikipedia | wikipedia_007 | No Prewarm | 5 | 0.0% | - | 2436.592 |
| Wikipedia | wikipedia_007 | Keyword Prewarm | 5 | 100.0% | 100.0% | 126.399 |
| Wikipedia | wikipedia_007 | Semantic Prewarm | 5 | 100.0% | 100.0% | 124.377 |
| Wikipedia | wikipedia_007 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 126.315 |
