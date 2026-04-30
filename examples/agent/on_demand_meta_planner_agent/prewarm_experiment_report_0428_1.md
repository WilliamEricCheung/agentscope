# MCP Prewarm Experiment Report

> Source dataset: `/mnt/d/Project/agentscope/laplace/mcp_dataset/laplace_tasks_single_runner_format.json`

> Sample size: `20` distinct servers, repeats per mode: `5`, random seed: `42`.

> Each trial begins by forcibly removing all prewarm-ready Laplace MCP containers and their lifecycle state so speculative prewarm always starts from a clean container state.

> `Target Match Rate` measures whether the router selected the actual server required by the sampled task. `Effectiveness Rate` is computed as `effective target prewarm runs / target matched runs`, aligned with the earlier timing-report definition but made target-specific for this experiment.

## Resume Progress

| Completed Trials | Remaining Trials | Skipped Resumed Trials |
| --- | --- | --- |
| 400 | 0 | 0 |

## Sampled Tasks

| Server | Task ID | Fuzzy Description |
| --- | --- | --- |
| OpenAPI Explorer | openapi_explorer_001 | I need a clear summary of key details from the Stripe API’s OpenAPI specificatio... |
| Car Price Evaluator | car_price_evaluator_005 | Can you find the average price of all Toyota car models listed in the FIPE datab... |
| Bibliomantic | bibliomantic_005 | I’m trying to decide whether to accept a job offer in Berlin that starts next mo... |
| Scientific Computing | scientific_computing_005 | I have a 2×2 matrix A with entries [4, 1, 2, 3] (so the first row is [4, 1] and ... |
| Google Maps | google_maps_004 | I'm standing near the Empire State Building in New York City and looking for the... |
| Game Trends | game_trends_003 | Can you run a full check to make sure everything’s working properly and then pul... |
| Reddit | reddit_001 | Can you find the most engaging discussion in the r/science subreddit from the pa... |
| Context7 | context7_003 | I'm building a web app that needs real-time collaborative editing, and I'm serio... |
| Weather Data | weather_data_004 | I'm helping a travel agency design a new "Weather-Responsive Getaway" package, a... |
| NixOS | nixos_002 | I need help finding a stable NixOS package for Neovim that’s been updated in the... |
| Call for Papers | call_for_papers_000 | Can you find up to five academic conferences happening in the next three months ... |
| Metropolitan Museum | metropolitan_museum_001 | Can you find the painting titled *The Harvesters* at the Metropolitan Museum of ... |
| BioMCP | biomcp_005 | I'm researching the clinical significance of the BRAF V600E mutation (HGVS: NM_0... |
| Unit Converter | unit_converter_003 | I'm working on a physics experiment report due in the next three months and need... |
| NASA Data | nasa_data_002 | Can you look into space weather activity from the past 7 days and see if it line... |
| OSINT Intelligence | osint_intelligence_002 | I need a comprehensive security assessment of the domain example-corp.net. Pleas... |
| Medical Calculator | medical_calculator_001 | I’m preparing for an elective abdominal aortic aneurysm repair on a 68-year-old ... |
| Time MCP | time_mcp_001 | What time will it be in Tokyo when it’s 14:30 in London three days from today? A... |
| Huge Icons | huge_icons_002 | I'm working on a cross-platform dashboard app and need to pick the right icons f... |
| Movie Recommender | movie_recommender_000 | Can you give me a list of three highly rated science fiction movies from the las... |

## Overall Comparison by Mode

| Mode | Runs | Target Match Runs | Target Match Rate | Effective Prewarm Runs | Effectiveness Rate | Effective Route Breakdown | Avg Wait After Activation (ms) | Min Wait (ms) | Max Wait (ms) | Activation Startup Modes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| No Prewarm | 100 | 0 | 0.0% | 0 | - | - | 2643.743 | 1754.752 | 5714.254 | cold:100 |
| Keyword Prewarm | 100 | 100 | 100.0% | 100 | 100.0% | L1:100 | 119.648 | 83.892 | 1126.218 | running:100 |
| Semantic Prewarm | 100 | 100 | 100.0% | 100 | 100.0% | L2:100 | 104.248 | 79.422 | 204.524 | running:100 |
| Hybrid Prewarm | 100 | 100 | 100.0% | 100 | 100.0% | L1:100 | 108.055 | 83.509 | 236.162 | running:100 |

## Per-task Comparison by Mode

| Server | Task ID | Mode | Runs | Target Match Rate | Effectiveness Rate | Avg Wait After Activation (ms) |
| --- | --- | --- | --- | --- | --- | --- |
| Bibliomantic | bibliomantic_005 | No Prewarm | 5 | 0.0% | - | 2839.950 |
| Bibliomantic | bibliomantic_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 92.249 |
| Bibliomantic | bibliomantic_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 88.440 |
| Bibliomantic | bibliomantic_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 89.054 |
| BioMCP | biomcp_005 | No Prewarm | 5 | 0.0% | - | 1879.892 |
| BioMCP | biomcp_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 97.258 |
| BioMCP | biomcp_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 92.073 |
| BioMCP | biomcp_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 98.591 |
| Call for Papers | call_for_papers_000 | No Prewarm | 5 | 0.0% | - | 2956.955 |
| Call for Papers | call_for_papers_000 | Keyword Prewarm | 5 | 100.0% | 100.0% | 101.284 |
| Call for Papers | call_for_papers_000 | Semantic Prewarm | 5 | 100.0% | 100.0% | 94.615 |
| Call for Papers | call_for_papers_000 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 94.064 |
| Car Price Evaluator | car_price_evaluator_005 | No Prewarm | 5 | 0.0% | - | 2841.651 |
| Car Price Evaluator | car_price_evaluator_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 96.565 |
| Car Price Evaluator | car_price_evaluator_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 91.316 |
| Car Price Evaluator | car_price_evaluator_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 93.014 |
| Context7 | context7_003 | No Prewarm | 5 | 0.0% | - | 1938.009 |
| Context7 | context7_003 | Keyword Prewarm | 5 | 100.0% | 100.0% | 118.540 |
| Context7 | context7_003 | Semantic Prewarm | 5 | 100.0% | 100.0% | 101.228 |
| Context7 | context7_003 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 115.330 |
| Game Trends | game_trends_003 | No Prewarm | 5 | 0.0% | - | 2348.093 |
| Game Trends | game_trends_003 | Keyword Prewarm | 5 | 100.0% | 100.0% | 397.075 |
| Game Trends | game_trends_003 | Semantic Prewarm | 5 | 100.0% | 100.0% | 178.055 |
| Game Trends | game_trends_003 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 189.981 |
| Google Maps | google_maps_004 | No Prewarm | 5 | 0.0% | - | 1788.621 |
| Google Maps | google_maps_004 | Keyword Prewarm | 5 | 100.0% | 100.0% | 118.903 |
| Google Maps | google_maps_004 | Semantic Prewarm | 5 | 100.0% | 100.0% | 99.105 |
| Google Maps | google_maps_004 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 131.821 |
| Huge Icons | huge_icons_002 | No Prewarm | 5 | 0.0% | - | 1785.718 |
| Huge Icons | huge_icons_002 | Keyword Prewarm | 5 | 100.0% | 100.0% | 91.224 |
| Huge Icons | huge_icons_002 | Semantic Prewarm | 5 | 100.0% | 100.0% | 90.691 |
| Huge Icons | huge_icons_002 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 94.219 |
| Medical Calculator | medical_calculator_001 | No Prewarm | 5 | 0.0% | - | 3059.635 |
| Medical Calculator | medical_calculator_001 | Keyword Prewarm | 5 | 100.0% | 100.0% | 94.568 |
| Medical Calculator | medical_calculator_001 | Semantic Prewarm | 5 | 100.0% | 100.0% | 93.335 |
| Medical Calculator | medical_calculator_001 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 96.546 |
| Metropolitan Museum | metropolitan_museum_001 | No Prewarm | 5 | 0.0% | - | 1789.972 |
| Metropolitan Museum | metropolitan_museum_001 | Keyword Prewarm | 5 | 100.0% | 100.0% | 88.814 |
| Metropolitan Museum | metropolitan_museum_001 | Semantic Prewarm | 5 | 100.0% | 100.0% | 88.481 |
| Metropolitan Museum | metropolitan_museum_001 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 89.607 |
| Movie Recommender | movie_recommender_000 | No Prewarm | 5 | 0.0% | - | 2813.550 |
| Movie Recommender | movie_recommender_000 | Keyword Prewarm | 5 | 100.0% | 100.0% | 91.893 |
| Movie Recommender | movie_recommender_000 | Semantic Prewarm | 5 | 100.0% | 100.0% | 88.829 |
| Movie Recommender | movie_recommender_000 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 86.547 |
| NASA Data | nasa_data_002 | No Prewarm | 5 | 0.0% | - | 2838.883 |
| NASA Data | nasa_data_002 | Keyword Prewarm | 5 | 100.0% | 100.0% | 93.189 |
| NASA Data | nasa_data_002 | Semantic Prewarm | 5 | 100.0% | 100.0% | 95.274 |
| NASA Data | nasa_data_002 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 95.988 |
| NixOS | nixos_002 | No Prewarm | 5 | 0.0% | - | 3796.705 |
| NixOS | nixos_002 | Keyword Prewarm | 5 | 100.0% | 100.0% | 102.272 |
| NixOS | nixos_002 | Semantic Prewarm | 5 | 100.0% | 100.0% | 101.956 |
| NixOS | nixos_002 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 105.895 |
| OSINT Intelligence | osint_intelligence_002 | No Prewarm | 5 | 0.0% | - | 2011.412 |
| OSINT Intelligence | osint_intelligence_002 | Keyword Prewarm | 5 | 100.0% | 100.0% | 89.828 |
| OSINT Intelligence | osint_intelligence_002 | Semantic Prewarm | 5 | 100.0% | 100.0% | 88.422 |
| OSINT Intelligence | osint_intelligence_002 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 89.343 |
| OpenAPI Explorer | openapi_explorer_001 | No Prewarm | 5 | 0.0% | - | 2473.976 |
| OpenAPI Explorer | openapi_explorer_001 | Keyword Prewarm | 5 | 100.0% | 100.0% | 203.571 |
| OpenAPI Explorer | openapi_explorer_001 | Semantic Prewarm | 5 | 100.0% | 100.0% | 202.430 |
| OpenAPI Explorer | openapi_explorer_001 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 195.690 |
| Reddit | reddit_001 | No Prewarm | 5 | 0.0% | - | 3743.057 |
| Reddit | reddit_001 | Keyword Prewarm | 5 | 100.0% | 100.0% | 121.806 |
| Reddit | reddit_001 | Semantic Prewarm | 5 | 100.0% | 100.0% | 116.281 |
| Reddit | reddit_001 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 110.248 |
| Scientific Computing | scientific_computing_005 | No Prewarm | 5 | 0.0% | - | 3062.163 |
| Scientific Computing | scientific_computing_005 | Keyword Prewarm | 5 | 100.0% | 100.0% | 93.183 |
| Scientific Computing | scientific_computing_005 | Semantic Prewarm | 5 | 100.0% | 100.0% | 90.929 |
| Scientific Computing | scientific_computing_005 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 89.907 |
| Time MCP | time_mcp_001 | No Prewarm | 5 | 0.0% | - | 2812.650 |
| Time MCP | time_mcp_001 | Keyword Prewarm | 5 | 100.0% | 100.0% | 87.826 |
| Time MCP | time_mcp_001 | Semantic Prewarm | 5 | 100.0% | 100.0% | 90.239 |
| Time MCP | time_mcp_001 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 86.935 |
| Unit Converter | unit_converter_003 | No Prewarm | 5 | 0.0% | - | 2813.983 |
| Unit Converter | unit_converter_003 | Keyword Prewarm | 5 | 100.0% | 100.0% | 93.192 |
| Unit Converter | unit_converter_003 | Semantic Prewarm | 5 | 100.0% | 100.0% | 86.491 |
| Unit Converter | unit_converter_003 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 90.466 |
| Weather Data | weather_data_004 | No Prewarm | 5 | 0.0% | - | 3279.977 |
| Weather Data | weather_data_004 | Keyword Prewarm | 5 | 100.0% | 100.0% | 119.711 |
| Weather Data | weather_data_004 | Semantic Prewarm | 5 | 100.0% | 100.0% | 106.770 |
| Weather Data | weather_data_004 | Hybrid Prewarm | 5 | 100.0% | 100.0% | 117.858 |
