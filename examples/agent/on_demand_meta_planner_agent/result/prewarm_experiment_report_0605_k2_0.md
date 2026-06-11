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
| No Prewarm | 100 | 0 | 0.0% | 100 | 0 | - | - | 2164.210 | - | 2164.210 | 2164.210 | 722.426 | 2948.956 | cold:100 |
| Keyword Prewarm | 100 | 90 | 90.0% | 10 | 90 | 100.0% | L1:90 | 323.021 | 126.819 | 2088.840 | 2088.840 | 117.452 | 2878.706 | cold:10, running:90 |
| Semantic Prewarm | 100 | 100 | 100.0% | 0 | 100 | 100.0% | L2:100 | 131.594 | 131.594 | - | - | 115.546 | 244.818 | running:100 |
| Hybrid Prewarm | 100 | 95 | 95.0% | 5 | 95 | 100.0% | L1:90, L2:5 | 225.552 | 131.783 | 2007.167 | 2007.167 | 112.306 | 2884.165 | cold:5, running:95 |

## Per-task Comparison by Mode

| Server | Task ID | Mode | Runs | Target Match Rate | Effectiveness Rate | Avg Wait After Activation (ms) |
| --- | --- | --- | --- | --- | --- | --- |
| Bibliomantic | bibliomantic_003 | No Prewarm | 5 | 0.0% | - | 2020.892 |
| Bibliomantic | bibliomantic_003 | Keyword Prewarm | 5 | 100.0% | 100.0% | 126.174 |
| Bibliomantic | bibliomantic_003 | Semantic Prewarm | 5 | 100.0% | 100.0% | 124.594 |
| Bibliomantic | bibliomantic_003 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 124.514 |
| BioMCP | biomcp_001 | No Prewarm | 5 | 0.0% | - | 1902.818 |
| BioMCP | biomcp_001 | Keyword Prewarm | 5 | 100.0% | 100.0% | 130.872 |
| BioMCP | biomcp_001 | Semantic Prewarm | 5 | 100.0% | 100.0% | 133.499 |
| BioMCP | biomcp_001 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 136.413 |
| Call for Papers | call_for_papers_002 | No Prewarm | 5 | 0.0% | - | 2225.903 |
| Call for Papers | call_for_papers_002 | Keyword Prewarm | 5 | 100.0% | 100.0% | 125.497 |
| Call for Papers | call_for_papers_002 | Semantic Prewarm | 5 | 100.0% | 100.0% | 134.734 |
| Call for Papers | call_for_papers_002 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 124.797 |
| Car Price Evaluator | car_price_evaluator_006 | No Prewarm | 5 | 0.0% | - | 2013.636 |
| Car Price Evaluator | car_price_evaluator_006 | Keyword Prewarm | 5 | 0.0% | - | 2020.510 |
| Car Price Evaluator | car_price_evaluator_006 | Semantic Prewarm | 5 | 100.0% | 100.0% | 124.485 |
| Car Price Evaluator | car_price_evaluator_006 | Hybrid Prewarm | 5 | 0.0% | - | 2007.167 |
| Context7 | context7_000 | No Prewarm | 5 | 0.0% | - | 742.858 |
| Context7 | context7_000 | Keyword Prewarm | 5 | 100.0% | 100.0% | 119.569 |
| Context7 | context7_000 | Semantic Prewarm | 5 | 100.0% | 100.0% | 128.651 |
| Context7 | context7_000 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 123.039 |
| Game Trends | game_trends_000 | No Prewarm | 5 | 0.0% | - | 1937.072 |
| Game Trends | game_trends_000 | Keyword Prewarm | 5 | 100.0% | 100.0% | 125.418 |
| Game Trends | game_trends_000 | Semantic Prewarm | 5 | 100.0% | 100.0% | 126.400 |
| Game Trends | game_trends_000 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 124.383 |
| Google Maps | google_maps_003 | No Prewarm | 5 | 0.0% | - | 1812.512 |
| Google Maps | google_maps_003 | Keyword Prewarm | 5 | 100.0% | 100.0% | 126.328 |
| Google Maps | google_maps_003 | Semantic Prewarm | 5 | 100.0% | 100.0% | 124.106 |
| Google Maps | google_maps_003 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 124.509 |
| Medical Calculator | medical_calculator_005 | No Prewarm | 5 | 0.0% | - | 2902.961 |
| Medical Calculator | medical_calculator_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 132.990 |
| Medical Calculator | medical_calculator_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 126.045 |
| Medical Calculator | medical_calculator_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 127.745 |
| Metropolitan Museum | metropolitan_museum_005 | No Prewarm | 5 | 0.0% | - | 945.282 |
| Metropolitan Museum | metropolitan_museum_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 122.531 |
| Metropolitan Museum | metropolitan_museum_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 124.331 |
| Metropolitan Museum | metropolitan_museum_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 122.278 |
| NASA Data | nasa_data_004 | No Prewarm | 5 | 0.0% | - | 2869.711 |
| NASA Data | nasa_data_004 | Keyword Prewarm | 5 | 100.0% | 100.0% | 128.469 |
| NASA Data | nasa_data_004 | Semantic Prewarm | 5 | 100.0% | 100.0% | 135.109 |
| NASA Data | nasa_data_004 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 128.628 |
| National Parks | national_parks_003 | No Prewarm | 5 | 0.0% | - | 1817.516 |
| National Parks | national_parks_003 | Keyword Prewarm | 5 | 100.0% | 100.0% | 124.335 |
| National Parks | national_parks_003 | Semantic Prewarm | 5 | 100.0% | 100.0% | 125.746 |
| National Parks | national_parks_003 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 125.104 |
| NixOS | nixos_006 | No Prewarm | 5 | 0.0% | - | 2442.858 |
| NixOS | nixos_006 | Keyword Prewarm | 5 | 100.0% | 100.0% | 126.118 |
| NixOS | nixos_006 | Semantic Prewarm | 5 | 100.0% | 100.0% | 122.787 |
| NixOS | nixos_006 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 125.339 |
| OKX Exchange | okx_exchange_005 | No Prewarm | 5 | 0.0% | - | 1802.274 |
| OKX Exchange | okx_exchange_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 130.321 |
| OKX Exchange | okx_exchange_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 124.032 |
| OKX Exchange | okx_exchange_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 123.212 |
| OpenAPI Explorer | openapi_explorer_006 | No Prewarm | 5 | 0.0% | - | 2274.756 |
| OpenAPI Explorer | openapi_explorer_006 | Keyword Prewarm | 5 | 0.0% | - | 2157.170 |
| OpenAPI Explorer | openapi_explorer_006 | Semantic Prewarm | 5 | 100.0% | 100.0% | 231.293 |
| OpenAPI Explorer | openapi_explorer_006 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 229.205 |
| Paper Search | paper_search_001 | No Prewarm | 5 | 0.0% | - | 2888.606 |
| Paper Search | paper_search_001 | Keyword Prewarm | 5 | 100.0% | 100.0% | 127.358 |
| Paper Search | paper_search_001 | Semantic Prewarm | 5 | 100.0% | 100.0% | 125.535 |
| Paper Search | paper_search_001 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 129.001 |
| Scientific Computing | scientific_computing_004 | No Prewarm | 5 | 0.0% | - | 2914.934 |
| Scientific Computing | scientific_computing_004 | Keyword Prewarm | 5 | 100.0% | 100.0% | 133.943 |
| Scientific Computing | scientific_computing_004 | Semantic Prewarm | 5 | 100.0% | 100.0% | 124.036 |
| Scientific Computing | scientific_computing_004 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 134.426 |
| Time MCP | time_mcp_005 | No Prewarm | 5 | 0.0% | - | 2859.707 |
| Time MCP | time_mcp_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 124.626 |
| Time MCP | time_mcp_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 121.345 |
| Time MCP | time_mcp_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 123.437 |
| Unit Converter | unit_converter_002 | No Prewarm | 5 | 0.0% | - | 2226.936 |
| Unit Converter | unit_converter_002 | Keyword Prewarm | 5 | 100.0% | 100.0% | 125.597 |
| Unit Converter | unit_converter_002 | Semantic Prewarm | 5 | 100.0% | 100.0% | 123.952 |
| Unit Converter | unit_converter_002 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 126.486 |
| Weather Data | weather_data_001 | No Prewarm | 5 | 0.0% | - | 2663.170 |
| Weather Data | weather_data_001 | Keyword Prewarm | 5 | 100.0% | 100.0% | 127.500 |
| Weather Data | weather_data_001 | Semantic Prewarm | 5 | 100.0% | 100.0% | 125.290 |
| Weather Data | weather_data_001 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 124.979 |
| Wikipedia | wikipedia_007 | No Prewarm | 5 | 0.0% | - | 2019.794 |
| Wikipedia | wikipedia_007 | Keyword Prewarm | 5 | 100.0% | 100.0% | 125.098 |
| Wikipedia | wikipedia_007 | Semantic Prewarm | 5 | 100.0% | 100.0% | 125.912 |
| Wikipedia | wikipedia_007 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 126.370 |
