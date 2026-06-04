# MCP Server Profile Report

## Overview

- Manifest: /mnt/d/Project/agentscope/src/agentscope/mcp/server_config/laplace_mcp_manifest.json
- Started: 2026-06-04T03:43:02.326704+00:00
- Completed: 2026-06-04T04:25:33.234514+00:00
- Servers: 32
- Iterations per server: 10
- TCP startup timeout: 120.0 s
- MCP request timeout: 30.0 s
- Smoke call enabled: True
- Dependency bootstrap enabled: True
- Managed dependencies: Milvus Backend, Neo4j

## Summary Table

| Server | Success | Partial | Fail | Total Avg (ms) | Launch Avg (ms) | Port Wait Avg (ms) | Handshake Avg (ms) | Interface Avg (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BioMCP | 10 | 0 | 0 | 2126.57 | 669.82 | 0.69 | 776.08 | 83.64 |
| Bibliomantic | 0 | 0 | 10 | 121576.17 | 637.79 | - | - | - |
| Playwright | 10 | 0 | 0 | 2463.92 | 627.83 | 0.87 | 601.51 | 679.54 |
| Jupyter MCP | 10 | 0 | 0 | 9015.40 | 632.90 | 0.67 | 1729.29 | 6111.09 |
| Neo4j Cypher | 10 | 0 | 0 | 2700.10 | 622.58 | 0.64 | 1147.62 | 376.10 |
| Call for Papers | 10 | 0 | 0 | 3392.46 | 612.21 | 0.74 | 1255.13 | 983.67 |
| Car Price Evaluator | 10 | 0 | 0 | 3476.89 | 604.58 | 0.74 | 1147.24 | 1183.99 |
| Context7 | 10 | 0 | 0 | 2714.41 | 615.13 | 0.63 | 573.21 | 988.02 |
| DEX Paprika | 10 | 0 | 0 | 2957.32 | 596.67 | 0.66 | 578.08 | 1236.98 |
| FruityVice | 10 | 0 | 0 | 4005.93 | 613.41 | 0.63 | 1148.05 | 1702.51 |
| Game Trends | 10 | 0 | 0 | 1812.07 | 593.27 | 0.59 | 618.31 | 74.66 |
| Google Maps | 10 | 0 | 0 | 1798.29 | 617.17 | 0.66 | 581.22 | 78.50 |
| Huge Icons | 10 | 0 | 0 | 3383.49 | 617.42 | 0.85 | 580.34 | 1650.32 |
| Hugging Face | 10 | 0 | 0 | 2181.90 | 599.88 | 0.61 | 615.25 | 442.80 |
| Math MCP | 10 | 0 | 0 | 1788.72 | 609.84 | 0.72 | 582.05 | 77.87 |
| Medical Calculator | 10 | 0 | 0 | 3025.86 | 619.39 | 1.20 | 1772.48 | 87.11 |
| Milvus MCP | 10 | 0 | 0 | 2281.07 | 599.38 | 0.73 | 1065.09 | 76.43 |
| Metropolitan Museum | 10 | 0 | 0 | 2726.61 | 612.24 | 0.59 | 571.89 | 1020.28 |
| Movie Recommender | 10 | 0 | 0 | 3019.46 | 605.77 | 0.69 | 1149.49 | 712.67 |
| NASA Data | 8 | 0 | 2 | 12568.13 | 607.57 | 0.68 | 1258.60 | 5191.74 |
| National Parks | 10 | 0 | 0 | 3091.49 | 620.13 | 0.66 | 574.71 | 1364.11 |
| NixOS | 10 | 0 | 0 | 16383.17 | 616.43 | 0.66 | 1164.63 | 14086.43 |
| OKX Exchange | 10 | 0 | 0 | 1805.77 | 617.52 | 0.68 | 573.10 | 78.85 |
| OpenAPI Explorer | 10 | 0 | 0 | 2762.89 | 614.20 | 0.67 | 898.62 | 730.73 |
| OSINT Intelligence | 10 | 0 | 0 | 2402.67 | 621.15 | 1.33 | 1151.40 | 81.05 |
| Paper Search | 7 | 0 | 3 | 22111.90 | 603.66 | 0.65 | 1682.44 | 9235.62 |
| Reddit | 10 | 0 | 0 | 3588.35 | 629.84 | 0.66 | 1204.39 | 1208.51 |
| Scientific Computing | 10 | 0 | 0 | 3197.24 | 597.45 | 0.71 | 1952.86 | 102.22 |
| Time MCP | 10 | 0 | 0 | 2885.73 | 596.78 | 0.68 | 1628.83 | 139.71 |
| Unit Converter | 10 | 0 | 0 | 2495.82 | 603.17 | 0.73 | 1256.37 | 84.12 |
| Weather Data | 10 | 0 | 0 | 2757.22 | 606.26 | 0.75 | 1151.81 | 455.01 |
| Wikipedia | 10 | 0 | 0 | 2637.36 | 601.63 | 0.75 | 1155.85 | 362.67 |

## BioMCP

- Container: laplace-biomcp
- Image: laplace/biomcp:local
- URL: http://localhost:8830/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 669.82 | 599.80 | 815.01 | 10 |
| wait_tcp_ms | 0.69 | 0.58 | 0.77 | 10 |
| mcp_handshake_ms | 776.08 | 669.34 | 1638.71 | 10 |
| interface_test_ms | 83.64 | 73.10 | 116.45 | 10 |
| total_ms | 2126.57 | 1861.80 | 3265.93 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 700.42 | 626.34 | 838.12 | 10 |
| handshake_elapsed_ms | 1476.49 | 1301.59 | 2476.82 | 10 |
| interface_test_elapsed_ms | 1560.13 | 1375.62 | 2593.27 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3265.93 | 815.01 | 0.65 | 1638.71 | 116.45 | think |
| 2 | pass | - | 2215.02 | 773.00 | 0.76 | 694.87 | 91.59 | think |
| 3 | pass | - | 2113.53 | 725.35 | 0.68 | 680.51 | 91.31 | think |
| 4 | pass | - | 2226.73 | 680.31 | 0.74 | 704.88 | 78.64 | think |
| 5 | pass | - | 1942.43 | 641.41 | 0.58 | 674.19 | 81.19 | think |
| 6 | pass | - | 1916.84 | 599.80 | 0.63 | 675.25 | 74.02 | think |
| 7 | pass | - | 1906.52 | 624.82 | 0.73 | 674.70 | 73.10 | think |
| 8 | pass | - | 1906.29 | 621.30 | 0.67 | 675.00 | 82.05 | think |
| 9 | pass | - | 1861.80 | 604.20 | 0.77 | 669.34 | 73.93 | think |
| 10 | pass | - | 1910.60 | 612.98 | 0.69 | 673.32 | 74.07 | think |

## Bibliomantic

- Container: laplace-bibliomantic
- Image: laplace/bibliomantic:local
- URL: http://localhost:8801/mcp
- Success / Partial / Fail: 0 / 0 / 10
- Failure stages: {"tcp_ready": 10}

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 637.79 | 604.72 | 689.28 | 10 |
| wait_tcp_ms | - | - | - | 0 |
| mcp_handshake_ms | - | - | - | 0 |
| interface_test_ms | - | - | - | 0 |
| total_ms | 121576.17 | 121427.92 | 121717.99 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | - | - | - | 0 |
| handshake_elapsed_ms | - | - | - | 0 |
| interface_test_elapsed_ms | - | - | - | 0 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | fail | tcp_ready | 121585.58 | 604.72 | - | - | - | - |
| 2 | fail | tcp_ready | 121641.75 | 613.39 | - | - | - | - |
| 3 | fail | tcp_ready | 121618.55 | 613.30 | - | - | - | - |
| 4 | fail | tcp_ready | 121427.92 | 668.08 | - | - | - | - |
| 5 | fail | tcp_ready | 121568.99 | 631.57 | - | - | - | - |
| 6 | fail | tcp_ready | 121680.91 | 623.85 | - | - | - | - |
| 7 | fail | tcp_ready | 121450.28 | 644.92 | - | - | - | - |
| 8 | fail | tcp_ready | 121627.83 | 666.68 | - | - | - | - |
| 9 | fail | tcp_ready | 121717.99 | 689.28 | - | - | - | - |
| 10 | fail | tcp_ready | 121441.85 | 622.15 | - | - | - | - |

## Playwright

- Container: playwright-mcp
- Image: laplace/playwright-mcp:local
- Original image: mcr.microsoft.com/playwright/mcp:latest
- URL: http://localhost:8804/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 627.83 | 609.29 | 639.85 | 10 |
| wait_tcp_ms | 0.87 | 0.60 | 2.56 | 10 |
| mcp_handshake_ms | 601.51 | 578.94 | 742.97 | 10 |
| interface_test_ms | 679.54 | 474.02 | 1865.78 | 10 |
| total_ms | 2463.92 | 2200.78 | 3801.94 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 655.58 | 636.65 | 665.86 | 10 |
| handshake_elapsed_ms | 1257.09 | 1224.42 | 1408.83 | 10 |
| interface_test_elapsed_ms | 1936.63 | 1698.45 | 3274.60 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3801.94 | 639.85 | 2.56 | 742.97 | 1865.78 | browser_close |
| 2 | pass | - | 2338.99 | 609.29 | 0.72 | 601.05 | 517.24 | browser_close |
| 3 | pass | - | 2321.70 | 633.44 | 0.63 | 593.67 | 539.28 | browser_close |
| 4 | pass | - | 2243.62 | 630.57 | 0.71 | 583.41 | 476.00 | browser_close |
| 5 | pass | - | 2259.70 | 637.05 | 0.81 | 581.87 | 499.12 | browser_close |
| 6 | pass | - | 2672.60 | 625.50 | 0.60 | 584.82 | 945.15 | browser_close |
| 7 | pass | - | 2287.10 | 632.49 | 0.69 | 581.40 | 497.27 | browser_close |
| 8 | pass | - | 2237.57 | 624.53 | 0.65 | 580.16 | 489.85 | browser_close |
| 9 | pass | - | 2200.78 | 618.58 | 0.62 | 578.94 | 474.02 | browser_close |
| 10 | pass | - | 2275.23 | 626.99 | 0.70 | 586.80 | 491.68 | browser_close |

## Jupyter MCP

- Container: laplace-jupyter-mcp
- Image: laplace/jupyter-mcp-server:local
- Original image: datalayer/jupyter-mcp-server:latest
- URL: http://localhost:8828/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 632.90 | 614.22 | 658.17 | 10 |
| wait_tcp_ms | 0.67 | 0.46 | 0.87 | 10 |
| mcp_handshake_ms | 1729.29 | 1617.27 | 2677.14 | 10 |
| interface_test_ms | 6111.09 | 6098.82 | 6121.48 | 10 |
| total_ms | 9015.40 | 8866.92 | 9967.49 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 661.55 | 642.71 | 688.52 | 10 |
| handshake_elapsed_ms | 2390.84 | 2262.40 | 3362.89 | 10 |
| interface_test_elapsed_ms | 8501.93 | 8361.23 | 9477.14 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 9967.49 | 658.17 | 0.87 | 2677.14 | 6114.26 | list_files |
| 2 | pass | - | 8922.07 | 619.82 | 0.77 | 1623.04 | 6118.43 | list_files |
| 3 | pass | - | 8925.20 | 637.49 | 0.61 | 1625.90 | 6100.34 | list_files |
| 4 | pass | - | 8926.46 | 651.21 | 0.56 | 1630.13 | 6102.67 | list_files |
| 5 | pass | - | 8905.76 | 614.22 | 0.77 | 1624.39 | 6121.38 | list_files |
| 6 | pass | - | 8904.69 | 635.76 | 0.72 | 1624.90 | 6118.37 | list_files |
| 7 | pass | - | 8866.92 | 618.70 | 0.46 | 1617.72 | 6098.82 | list_files |
| 8 | pass | - | 8943.78 | 655.89 | 0.61 | 1622.94 | 6113.04 | list_files |
| 9 | pass | - | 8882.41 | 617.88 | 0.66 | 1617.27 | 6121.48 | list_files |
| 10 | pass | - | 8909.24 | 619.84 | 0.62 | 1629.50 | 6102.07 | list_files |

## Neo4j Cypher

- Container: laplace-neo4j-cypher
- Image: laplace/neo4j-cypher:local
- Original image: mcp/neo4j-cypher:latest
- URL: http://localhost:8829/mcp/
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 622.58 | 599.23 | 649.08 | 10 |
| wait_tcp_ms | 0.64 | 0.55 | 0.78 | 10 |
| mcp_handshake_ms | 1147.62 | 1089.72 | 1609.51 | 10 |
| interface_test_ms | 376.10 | 93.71 | 2815.81 | 10 |
| total_ms | 2700.10 | 2314.59 | 5599.33 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 650.93 | 626.83 | 683.60 | 10 |
| handshake_elapsed_ms | 1798.56 | 1718.72 | 2241.11 | 10 |
| interface_test_elapsed_ms | 2174.66 | 1815.83 | 5056.92 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 5599.33 | 609.43 | 0.64 | 1609.51 | 2815.81 | read_neo4j_cypher |
| 2 | pass | - | 2479.03 | 649.08 | 0.78 | 1091.84 | 147.37 | read_neo4j_cypher |
| 3 | pass | - | 2399.94 | 630.88 | 0.65 | 1092.33 | 99.22 | read_neo4j_cypher |
| 4 | pass | - | 2398.00 | 630.69 | 0.55 | 1089.72 | 105.66 | read_neo4j_cypher |
| 5 | pass | - | 2367.24 | 635.92 | 0.60 | 1094.29 | 101.47 | read_neo4j_cypher |
| 6 | pass | - | 2360.92 | 613.00 | 0.57 | 1098.97 | 102.89 | read_neo4j_cypher |
| 7 | pass | - | 2314.59 | 606.82 | 0.60 | 1098.00 | 93.71 | read_neo4j_cypher |
| 8 | pass | - | 2358.04 | 599.23 | 0.65 | 1091.89 | 97.11 | read_neo4j_cypher |
| 9 | pass | - | 2364.84 | 634.05 | 0.72 | 1101.62 | 98.83 | read_neo4j_cypher |
| 10 | pass | - | 2359.07 | 616.68 | 0.70 | 1108.03 | 98.98 | read_neo4j_cypher |

## Call for Papers

- Container: laplace-call-for-papers
- Image: laplace/call-for-papers:local
- URL: http://localhost:8802/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 612.21 | 589.63 | 644.08 | 10 |
| wait_tcp_ms | 0.74 | 0.48 | 1.11 | 10 |
| mcp_handshake_ms | 1255.13 | 1089.92 | 2167.35 | 10 |
| interface_test_ms | 983.67 | 604.19 | 1218.03 | 10 |
| total_ms | 3392.46 | 2883.84 | 4513.80 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 640.61 | 614.37 | 672.13 | 10 |
| handshake_elapsed_ms | 1895.73 | 1716.06 | 2781.72 | 10 |
| interface_test_elapsed_ms | 2879.40 | 2337.96 | 3999.75 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 4513.80 | 589.63 | 0.81 | 2167.35 | 1218.03 | get_events |
| 2 | pass | - | 3401.80 | 605.04 | 0.65 | 1100.76 | 1189.15 | get_events |
| 3 | pass | - | 3331.46 | 625.22 | 0.78 | 1093.62 | 1042.83 | get_events |
| 4 | pass | - | 3098.74 | 610.87 | 0.77 | 1098.53 | 880.17 | get_events |
| 5 | pass | - | 3078.55 | 644.08 | 0.67 | 1097.83 | 817.12 | get_events |
| 6 | pass | - | 3907.78 | 618.51 | 1.11 | 1619.68 | 1128.98 | get_events |
| 7 | pass | - | 3199.87 | 610.59 | 0.73 | 1097.57 | 953.36 | get_events |
| 8 | pass | - | 2883.84 | 612.67 | 0.76 | 1094.93 | 604.19 | get_events |
| 9 | pass | - | 3276.78 | 596.21 | 0.48 | 1089.92 | 1027.64 | get_events |
| 10 | pass | - | 3231.99 | 609.30 | 0.63 | 1091.07 | 975.24 | get_events |

## Car Price Evaluator

- Container: laplace-car-price-evaluator
- Image: laplace/car-price-evaluator:local
- URL: http://localhost:8803/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 604.58 | 587.66 | 627.19 | 10 |
| wait_tcp_ms | 0.74 | 0.56 | 1.12 | 10 |
| mcp_handshake_ms | 1147.24 | 1087.77 | 1620.83 | 10 |
| interface_test_ms | 1183.99 | 631.84 | 1906.68 | 10 |
| total_ms | 3476.89 | 2862.36 | 4666.65 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 630.68 | 612.96 | 652.86 | 10 |
| handshake_elapsed_ms | 1777.92 | 1706.22 | 2243.76 | 10 |
| interface_test_elapsed_ms | 2961.90 | 2355.97 | 4150.43 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 4666.65 | 599.89 | 0.56 | 1620.83 | 1906.68 | get_car_brands |
| 2 | pass | - | 3917.65 | 605.96 | 0.68 | 1093.13 | 1676.73 | get_car_brands |
| 3 | pass | - | 3012.23 | 596.27 | 0.69 | 1103.79 | 729.81 | get_car_brands |
| 4 | pass | - | 2862.36 | 587.66 | 0.70 | 1098.92 | 656.30 | get_car_brands |
| 5 | pass | - | 3931.76 | 604.20 | 0.72 | 1096.97 | 1669.32 | get_car_brands |
| 6 | pass | - | 3907.22 | 616.89 | 0.71 | 1093.41 | 1662.78 | get_car_brands |
| 7 | pass | - | 2871.02 | 605.78 | 0.95 | 1092.47 | 631.84 | get_car_brands |
| 8 | pass | - | 2886.99 | 592.02 | 0.70 | 1088.84 | 662.25 | get_car_brands |
| 9 | pass | - | 2892.26 | 609.91 | 0.60 | 1087.77 | 654.53 | get_car_brands |
| 10 | pass | - | 3820.73 | 627.19 | 1.12 | 1096.23 | 1589.62 | get_car_brands |

## Context7

- Container: laplace-context7
- Image: laplace/context7:local
- URL: http://localhost:8904/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 615.13 | 592.28 | 634.27 | 10 |
| wait_tcp_ms | 0.63 | 0.51 | 0.90 | 10 |
| mcp_handshake_ms | 573.21 | 564.40 | 581.31 | 10 |
| interface_test_ms | 988.02 | 902.43 | 1143.55 | 10 |
| total_ms | 2714.41 | 2586.62 | 2900.71 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 643.82 | 617.86 | 662.67 | 10 |
| handshake_elapsed_ms | 1217.03 | 1193.40 | 1232.59 | 10 |
| interface_test_elapsed_ms | 2205.05 | 2107.62 | 2370.82 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 2821.08 | 607.27 | 0.74 | 579.86 | 1123.09 | resolve-library-id |
| 2 | pass | - | 2707.52 | 618.54 | 0.59 | 580.03 | 939.58 | resolve-library-id |
| 3 | pass | - | 2691.85 | 634.27 | 0.65 | 569.92 | 950.92 | resolve-library-id |
| 4 | pass | - | 2900.71 | 627.75 | 0.90 | 569.96 | 1143.55 | resolve-library-id |
| 5 | pass | - | 2687.94 | 616.13 | 0.72 | 581.31 | 952.58 | resolve-library-id |
| 6 | pass | - | 2790.14 | 610.59 | 0.51 | 569.31 | 1095.88 | resolve-library-id |
| 7 | pass | - | 2586.62 | 592.28 | 0.63 | 575.53 | 939.47 | resolve-library-id |
| 8 | pass | - | 2635.76 | 613.38 | 0.55 | 564.40 | 902.43 | resolve-library-id |
| 9 | pass | - | 2664.84 | 626.09 | 0.51 | 569.40 | 909.65 | resolve-library-id |
| 10 | pass | - | 2657.60 | 605.01 | 0.54 | 572.35 | 923.06 | resolve-library-id |

## DEX Paprika

- Container: laplace-dex-paprika
- Image: laplace/dex-paprika:local
- URL: http://localhost:8805/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 596.67 | 563.80 | 628.70 | 10 |
| wait_tcp_ms | 0.66 | 0.54 | 0.84 | 10 |
| mcp_handshake_ms | 578.08 | 570.26 | 594.60 | 10 |
| interface_test_ms | 1236.98 | 800.83 | 1669.98 | 10 |
| total_ms | 2957.32 | 2541.48 | 3400.72 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 622.40 | 591.71 | 659.28 | 10 |
| handshake_elapsed_ms | 1200.48 | 1163.34 | 1243.96 | 10 |
| interface_test_elapsed_ms | 2437.46 | 1998.30 | 2877.17 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3400.72 | 605.03 | 0.84 | 579.77 | 1669.98 | getNetworks |
| 2 | pass | - | 3170.26 | 597.14 | 0.60 | 573.93 | 1413.79 | getNetworks |
| 3 | pass | - | 3161.36 | 628.70 | 0.69 | 584.67 | 1415.80 | getNetworks |
| 4 | pass | - | 3086.38 | 595.78 | 0.64 | 575.50 | 1412.51 | getNetworks |
| 5 | pass | - | 3169.12 | 603.98 | 0.63 | 594.60 | 1441.18 | getNetworks |
| 6 | pass | - | 3100.88 | 599.90 | 0.63 | 575.74 | 1395.52 | getNetworks |
| 7 | pass | - | 2553.02 | 563.80 | 0.81 | 575.69 | 891.64 | getNetworks |
| 8 | pass | - | 2587.41 | 569.82 | 0.55 | 570.75 | 891.45 | getNetworks |
| 9 | pass | - | 2541.48 | 591.88 | 0.65 | 579.84 | 800.83 | getNetworks |
| 10 | pass | - | 2802.54 | 610.64 | 0.54 | 570.26 | 1037.08 | getNetworks |

## FruityVice

- Container: laplace-fruityvice
- Image: laplace/fruityvice:local
- URL: http://localhost:8806/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 613.41 | 594.58 | 692.49 | 10 |
| wait_tcp_ms | 0.63 | 0.52 | 0.78 | 10 |
| mcp_handshake_ms | 1148.05 | 1091.43 | 1617.78 | 10 |
| interface_test_ms | 1702.51 | 1508.42 | 1986.32 | 10 |
| total_ms | 4005.93 | 3723.90 | 4827.73 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 641.59 | 621.98 | 724.13 | 10 |
| handshake_elapsed_ms | 1789.65 | 1721.15 | 2265.20 | 10 |
| interface_test_elapsed_ms | 3492.16 | 3233.98 | 4251.53 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 4827.73 | 624.35 | 0.64 | 1617.78 | 1986.32 | get_fruit_nutrition |
| 2 | pass | - | 4022.97 | 692.49 | 0.55 | 1094.41 | 1724.16 | get_fruit_nutrition |
| 3 | pass | - | 4111.02 | 596.38 | 0.65 | 1100.25 | 1881.93 | get_fruit_nutrition |
| 4 | pass | - | 3931.56 | 594.58 | 0.60 | 1097.42 | 1726.04 | get_fruit_nutrition |
| 5 | pass | - | 4046.61 | 617.21 | 0.52 | 1094.76 | 1753.95 | get_fruit_nutrition |
| 6 | pass | - | 3813.68 | 601.68 | 0.78 | 1093.69 | 1574.60 | get_fruit_nutrition |
| 7 | pass | - | 4032.37 | 599.43 | 0.66 | 1101.04 | 1772.37 | get_fruit_nutrition |
| 8 | pass | - | 3723.90 | 599.59 | 0.62 | 1094.36 | 1508.42 | get_fruit_nutrition |
| 9 | pass | - | 3792.50 | 603.76 | 0.63 | 1091.43 | 1573.48 | get_fruit_nutrition |
| 10 | pass | - | 3756.95 | 604.64 | 0.62 | 1095.38 | 1523.86 | get_fruit_nutrition |

## Game Trends

- Container: laplace-game-trends
- Image: laplace/game-trends:local
- URL: http://localhost:8807/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 593.27 | 560.43 | 647.10 | 10 |
| wait_tcp_ms | 0.59 | 0.47 | 0.79 | 10 |
| mcp_handshake_ms | 618.31 | 553.55 | 1105.30 | 10 |
| interface_test_ms | 74.66 | 67.05 | 84.50 | 10 |
| total_ms | 1812.07 | 1686.12 | 2330.19 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 618.59 | 583.63 | 672.91 | 10 |
| handshake_elapsed_ms | 1236.90 | 1137.49 | 1723.72 | 10 |
| interface_test_elapsed_ms | 1311.56 | 1204.60 | 1800.44 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 2330.19 | 593.11 | 0.56 | 1105.30 | 76.72 | health_check |
| 2 | pass | - | 1752.83 | 612.34 | 0.55 | 564.19 | 76.00 | health_check |
| 3 | pass | - | 1803.89 | 596.34 | 0.64 | 567.01 | 84.50 | health_check |
| 4 | pass | - | 1785.86 | 601.47 | 0.79 | 565.29 | 75.97 | health_check |
| 5 | pass | - | 1788.09 | 647.10 | 0.55 | 575.25 | 75.38 | health_check |
| 6 | pass | - | 1794.76 | 604.07 | 0.60 | 567.97 | 77.98 | health_check |
| 7 | pass | - | 1686.12 | 560.53 | 0.63 | 554.87 | 67.05 | health_check |
| 8 | pass | - | 1692.35 | 560.43 | 0.51 | 553.55 | 67.11 | health_check |
| 9 | pass | - | 1753.69 | 568.17 | 0.47 | 567.76 | 70.09 | health_check |
| 10 | pass | - | 1732.94 | 589.16 | 0.58 | 561.96 | 75.78 | health_check |

## Google Maps

- Container: laplace-google-maps
- Image: laplace/google-maps:local
- URL: http://localhost:8808/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 617.17 | 588.89 | 649.09 | 10 |
| wait_tcp_ms | 0.66 | 0.62 | 0.72 | 10 |
| mcp_handshake_ms | 581.22 | 572.48 | 599.90 | 10 |
| interface_test_ms | 78.50 | 70.79 | 97.20 | 10 |
| total_ms | 1798.29 | 1751.81 | 1873.74 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 645.03 | 614.58 | 679.44 | 10 |
| handshake_elapsed_ms | 1226.25 | 1187.76 | 1276.75 | 10 |
| interface_test_elapsed_ms | 1304.75 | 1260.86 | 1361.58 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 1756.89 | 594.69 | 0.67 | 574.29 | 72.88 | echo |
| 2 | pass | - | 1751.81 | 588.89 | 0.68 | 573.18 | 73.10 | echo |
| 3 | pass | - | 1770.98 | 608.40 | 0.64 | 590.59 | 77.12 | echo |
| 4 | pass | - | 1788.28 | 603.87 | 0.64 | 572.48 | 70.79 | echo |
| 5 | pass | - | 1782.79 | 612.76 | 0.70 | 572.49 | 73.61 | echo |
| 6 | pass | - | 1782.89 | 616.86 | 0.64 | 581.17 | 78.67 | echo |
| 7 | pass | - | 1873.74 | 649.09 | 0.72 | 599.90 | 84.83 | echo |
| 8 | pass | - | 1842.10 | 648.26 | 0.70 | 582.74 | 78.21 | echo |
| 9 | pass | - | 1807.79 | 633.77 | 0.63 | 583.16 | 78.63 | echo |
| 10 | pass | - | 1825.61 | 615.12 | 0.62 | 582.14 | 97.20 | echo |

## Huge Icons

- Container: laplace-huge-icons
- Image: laplace/huge-icons:local
- URL: http://localhost:8809/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 617.42 | 587.12 | 665.73 | 10 |
| wait_tcp_ms | 0.85 | 0.65 | 1.16 | 10 |
| mcp_handshake_ms | 580.34 | 572.24 | 593.60 | 10 |
| interface_test_ms | 1650.32 | 1549.57 | 1996.76 | 10 |
| total_ms | 3383.49 | 3258.00 | 3684.47 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 645.42 | 613.91 | 693.63 | 10 |
| handshake_elapsed_ms | 1225.76 | 1186.14 | 1276.83 | 10 |
| interface_test_elapsed_ms | 2876.08 | 2744.56 | 3201.04 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3684.47 | 593.64 | 0.71 | 585.02 | 1996.76 | list_icons |
| 2 | pass | - | 3333.17 | 618.41 | 0.77 | 578.50 | 1630.20 | list_icons |
| 3 | pass | - | 3507.49 | 616.58 | 0.83 | 577.73 | 1755.32 | list_icons |
| 4 | pass | - | 3318.11 | 640.68 | 1.08 | 573.72 | 1587.35 | list_icons |
| 5 | pass | - | 3406.91 | 607.63 | 1.16 | 575.69 | 1667.57 | list_icons |
| 6 | pass | - | 3400.69 | 639.82 | 1.10 | 589.99 | 1620.27 | list_icons |
| 7 | pass | - | 3258.00 | 606.42 | 0.77 | 593.60 | 1549.57 | list_icons |
| 8 | pass | - | 3297.28 | 598.20 | 0.67 | 573.75 | 1564.08 | list_icons |
| 9 | pass | - | 3258.29 | 587.12 | 0.65 | 572.24 | 1558.41 | list_icons |
| 10 | pass | - | 3370.47 | 665.73 | 0.71 | 583.20 | 1573.63 | list_icons |

## Hugging Face

- Container: laplace-huggingface
- Image: laplace/huggingface:local
- URL: http://localhost:8810/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 599.88 | 584.61 | 632.40 | 10 |
| wait_tcp_ms | 0.61 | 0.42 | 1.18 | 10 |
| mcp_handshake_ms | 615.25 | 559.39 | 1092.29 | 10 |
| interface_test_ms | 442.80 | 427.05 | 468.55 | 10 |
| total_ms | 2181.90 | 2102.92 | 2663.18 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 627.62 | 610.07 | 661.12 | 10 |
| handshake_elapsed_ms | 1242.87 | 1171.23 | 1719.44 | 10 |
| interface_test_elapsed_ms | 1685.67 | 1602.05 | 2166.97 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 2663.18 | 602.71 | 0.64 | 1092.29 | 447.53 | search-models |
| 2 | pass | - | 2107.71 | 585.51 | 0.49 | 559.39 | 430.82 | search-models |
| 3 | pass | - | 2173.17 | 593.96 | 0.51 | 573.44 | 445.03 | search-models |
| 4 | pass | - | 2136.89 | 632.40 | 0.42 | 562.28 | 442.90 | search-models |
| 5 | pass | - | 2135.34 | 617.71 | 0.55 | 560.36 | 435.69 | search-models |
| 6 | pass | - | 2108.17 | 584.61 | 0.56 | 561.67 | 460.52 | search-models |
| 7 | pass | - | 2102.92 | 591.69 | 1.18 | 563.15 | 427.05 | search-models |
| 8 | pass | - | 2133.34 | 600.47 | 0.59 | 560.38 | 468.55 | search-models |
| 9 | pass | - | 2128.43 | 590.42 | 0.56 | 559.71 | 440.67 | search-models |
| 10 | pass | - | 2129.86 | 599.29 | 0.60 | 559.85 | 429.25 | search-models |

## Math MCP

- Container: laplace-math-mcp
- Image: laplace/math-mcp:local
- URL: http://localhost:8811/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 609.84 | 588.55 | 641.76 | 10 |
| wait_tcp_ms | 0.72 | 0.59 | 1.06 | 10 |
| mcp_handshake_ms | 582.05 | 576.38 | 600.97 | 10 |
| interface_test_ms | 77.87 | 71.99 | 86.32 | 10 |
| total_ms | 1788.72 | 1759.01 | 1816.89 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 636.37 | 615.34 | 662.72 | 10 |
| handshake_elapsed_ms | 1218.42 | 1192.38 | 1241.91 | 10 |
| interface_test_elapsed_ms | 1296.29 | 1274.75 | 1318.71 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 1778.48 | 641.76 | 0.59 | 576.53 | 77.33 | sum |
| 2 | pass | - | 1801.11 | 606.00 | 0.72 | 600.97 | 77.87 | sum |
| 3 | pass | - | 1800.19 | 613.35 | 0.75 | 581.94 | 79.74 | sum |
| 4 | pass | - | 1784.94 | 590.97 | 0.60 | 580.47 | 74.17 | sum |
| 5 | pass | - | 1816.89 | 591.33 | 0.76 | 582.68 | 71.99 | sum |
| 6 | pass | - | 1782.18 | 615.02 | 0.72 | 576.38 | 83.48 | sum |
| 7 | pass | - | 1815.42 | 629.48 | 0.66 | 583.54 | 76.80 | sum |
| 8 | pass | - | 1783.16 | 611.65 | 0.65 | 583.02 | 76.94 | sum |
| 9 | pass | - | 1759.01 | 610.26 | 1.06 | 577.90 | 74.09 | sum |
| 10 | pass | - | 1765.82 | 588.55 | 0.73 | 577.04 | 86.32 | sum |

## Medical Calculator

- Container: laplace-medical-calculator
- Image: laplace/medical-calculator:local
- URL: http://localhost:18812/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 619.39 | 586.53 | 656.04 | 10 |
| wait_tcp_ms | 1.20 | 0.68 | 2.01 | 10 |
| mcp_handshake_ms | 1772.48 | 1646.94 | 2701.07 | 10 |
| interface_test_ms | 87.11 | 78.24 | 105.13 | 10 |
| total_ms | 3025.86 | 2849.98 | 3945.22 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 647.78 | 616.23 | 683.27 | 10 |
| handshake_elapsed_ms | 2420.26 | 2263.17 | 3327.50 | 10 |
| interface_test_elapsed_ms | 2507.37 | 2353.56 | 3411.39 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3945.22 | 600.85 | 0.68 | 2701.07 | 83.89 | wells_pe_criteria |
| 2 | pass | - | 2959.99 | 633.15 | 1.17 | 1653.75 | 80.92 | wells_pe_criteria |
| 3 | pass | - | 2875.31 | 608.73 | 0.97 | 1665.88 | 84.48 | wells_pe_criteria |
| 4 | pass | - | 2892.27 | 635.03 | 1.05 | 1665.43 | 78.24 | wells_pe_criteria |
| 5 | pass | - | 2970.76 | 623.35 | 1.46 | 1706.32 | 105.13 | wells_pe_criteria |
| 6 | pass | - | 2961.97 | 629.85 | 1.43 | 1671.01 | 92.91 | wells_pe_criteria |
| 7 | pass | - | 2972.56 | 619.92 | 0.69 | 1675.32 | 88.01 | wells_pe_criteria |
| 8 | pass | - | 2943.43 | 656.04 | 1.15 | 1670.52 | 84.03 | wells_pe_criteria |
| 9 | pass | - | 2887.15 | 600.42 | 1.40 | 1668.60 | 83.08 | wells_pe_criteria |
| 10 | pass | - | 2849.98 | 586.53 | 2.01 | 1646.94 | 90.39 | wells_pe_criteria |

## Milvus MCP

- Container: laplace-mcp-server-milvus
- Image: laplace/mcp-server-milvus:local
- URL: http://localhost:8832/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 599.38 | 575.33 | 612.15 | 10 |
| wait_tcp_ms | 0.73 | 0.54 | 1.44 | 10 |
| mcp_handshake_ms | 1065.09 | 573.34 | 1722.54 | 10 |
| interface_test_ms | 76.43 | 72.86 | 85.73 | 10 |
| total_ms | 2281.07 | 1802.58 | 2930.02 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 625.83 | 603.07 | 639.53 | 10 |
| handshake_elapsed_ms | 1690.93 | 1209.90 | 2347.51 | 10 |
| interface_test_elapsed_ms | 1767.36 | 1283.87 | 2433.24 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 2930.02 | 602.17 | 0.74 | 1722.54 | 85.73 | milvus_list_databases |
| 2 | pass | - | 2317.54 | 610.71 | 0.78 | 1109.48 | 72.86 | milvus_list_databases |
| 3 | pass | - | 2278.70 | 578.22 | 0.70 | 1106.85 | 73.27 | milvus_list_databases |
| 4 | pass | - | 1829.04 | 608.80 | 0.60 | 585.57 | 74.05 | milvus_list_databases |
| 5 | pass | - | 2359.49 | 607.45 | 1.44 | 1108.56 | 77.60 | milvus_list_databases |
| 6 | pass | - | 1802.58 | 610.00 | 0.62 | 573.34 | 73.97 | milvus_list_databases |
| 7 | pass | - | 2299.28 | 587.55 | 0.54 | 1106.43 | 75.83 | milvus_list_databases |
| 8 | pass | - | 2325.06 | 575.33 | 0.62 | 1118.13 | 81.68 | milvus_list_databases |
| 9 | pass | - | 2311.14 | 601.44 | 0.54 | 1105.06 | 75.19 | milvus_list_databases |
| 10 | pass | - | 2357.87 | 612.15 | 0.72 | 1115.01 | 74.14 | milvus_list_databases |

## Metropolitan Museum

- Container: laplace-metmuseum
- Image: laplace/metmuseum:local
- URL: http://localhost:8813/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 612.24 | 582.48 | 628.87 | 10 |
| wait_tcp_ms | 0.59 | 0.41 | 0.74 | 10 |
| mcp_handshake_ms | 571.89 | 567.04 | 579.09 | 10 |
| interface_test_ms | 1020.28 | 704.33 | 1588.88 | 10 |
| total_ms | 2726.61 | 2364.35 | 3276.34 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 638.38 | 608.10 | 657.49 | 10 |
| handshake_elapsed_ms | 1210.28 | 1177.52 | 1228.79 | 10 |
| interface_test_elapsed_ms | 2230.55 | 1881.85 | 2809.72 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3276.34 | 622.96 | 0.68 | 573.58 | 1588.88 | list-departments |
| 2 | pass | - | 2894.76 | 627.61 | 0.57 | 571.31 | 1186.36 | list-departments |
| 3 | pass | - | 2820.41 | 608.57 | 0.74 | 567.04 | 1131.85 | list-departments |
| 4 | pass | - | 2802.05 | 599.48 | 0.61 | 572.84 | 1132.63 | list-departments |
| 5 | pass | - | 2472.84 | 613.88 | 0.62 | 573.51 | 746.18 | list-departments |
| 6 | pass | - | 2489.73 | 610.32 | 0.41 | 571.39 | 799.25 | list-departments |
| 7 | pass | - | 2364.35 | 582.48 | 0.61 | 569.42 | 704.33 | list-departments |
| 8 | pass | - | 2586.44 | 628.87 | 0.42 | 569.54 | 828.96 | list-departments |
| 9 | pass | - | 2621.57 | 610.88 | 0.55 | 571.21 | 865.24 | list-departments |
| 10 | pass | - | 2937.60 | 617.30 | 0.72 | 579.09 | 1219.09 | list-departments |

## Movie Recommender

- Container: laplace-movie-recommender
- Image: laplace/movie-recommender:local
- URL: http://localhost:8814/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 605.77 | 582.92 | 640.74 | 10 |
| wait_tcp_ms | 0.69 | 0.55 | 1.39 | 10 |
| mcp_handshake_ms | 1149.49 | 1090.00 | 1623.29 | 10 |
| interface_test_ms | 712.67 | 661.60 | 981.76 | 10 |
| total_ms | 3019.46 | 2892.44 | 3506.28 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 631.84 | 606.25 | 668.08 | 10 |
| handshake_elapsed_ms | 1781.32 | 1706.58 | 2263.78 | 10 |
| interface_test_elapsed_ms | 2493.99 | 2380.76 | 2925.38 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3506.28 | 617.74 | 0.63 | 1623.29 | 661.60 | get_movies |
| 2 | pass | - | 2948.73 | 625.63 | 0.61 | 1090.00 | 678.01 | get_movies |
| 3 | pass | - | 2892.44 | 582.92 | 0.63 | 1105.39 | 669.11 | get_movies |
| 4 | pass | - | 3008.81 | 640.74 | 0.60 | 1099.94 | 682.87 | get_movies |
| 5 | pass | - | 2977.19 | 602.05 | 0.61 | 1093.56 | 710.29 | get_movies |
| 6 | pass | - | 2936.44 | 598.68 | 1.39 | 1094.69 | 683.67 | get_movies |
| 7 | pass | - | 2923.35 | 605.30 | 0.70 | 1103.59 | 689.30 | get_movies |
| 8 | pass | - | 2901.85 | 601.27 | 0.57 | 1093.42 | 682.90 | get_movies |
| 9 | pass | - | 3185.34 | 585.76 | 0.55 | 1097.23 | 981.76 | get_movies |
| 10 | pass | - | 2914.22 | 597.62 | 0.63 | 1093.73 | 687.14 | get_movies |

## NASA Data

- Container: laplace-nasa-data
- Image: laplace/nasa-data:local
- URL: http://localhost:8815/mcp
- Success / Partial / Fail: 8 / 0 / 2
- Failure stages: {"interface_test": 2}

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 607.57 | 576.90 | 624.21 | 10 |
| wait_tcp_ms | 0.68 | 0.54 | 0.85 | 10 |
| mcp_handshake_ms | 1258.60 | 1090.90 | 1635.32 | 10 |
| interface_test_ms | 5191.74 | 970.79 | 21228.27 | 8 |
| total_ms | 12568.13 | 3229.28 | 32844.11 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 634.40 | 602.32 | 653.54 | 10 |
| handshake_elapsed_ms | 1892.99 | 1699.11 | 2277.63 | 10 |
| interface_test_elapsed_ms | 7060.90 | 2715.32 | 23502.81 | 8 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 23984.33 | 618.04 | 0.54 | 1635.32 | 21228.27 | get_astronomy_picture_of_day |
| 2 | pass | - | 3336.65 | 598.21 | 0.66 | 1114.32 | 1090.64 | get_astronomy_picture_of_day |
| 3 | pass | - | 5839.79 | 604.58 | 0.76 | 1622.18 | 3083.19 | get_astronomy_picture_of_day |
| 4 | pass | - | 3229.28 | 602.20 | 0.74 | 1090.90 | 999.38 | get_astronomy_picture_of_day |
| 5 | pass | - | 11432.44 | 623.21 | 0.57 | 1091.26 | 9184.81 | get_astronomy_picture_of_day |
| 6 | fail | interface_test | 32844.11 | 614.35 | 0.76 | 1629.70 | - | - |
| 7 | pass | - | 4067.33 | 619.25 | 0.65 | 1112.60 | 1817.79 | get_astronomy_picture_of_day |
| 8 | pass | - | 5434.72 | 594.73 | 0.85 | 1093.74 | 3159.08 | get_astronomy_picture_of_day |
| 9 | pass | - | 3248.51 | 624.21 | 0.66 | 1099.17 | 970.79 | get_astronomy_picture_of_day |
| 10 | fail | interface_test | 32264.18 | 576.90 | 0.59 | 1096.79 | - | - |

## National Parks

- Container: laplace-national-parks
- Image: laplace/national-parks:local
- URL: http://localhost:8816/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 620.13 | 595.76 | 659.35 | 10 |
| wait_tcp_ms | 0.66 | 0.52 | 1.00 | 10 |
| mcp_handshake_ms | 574.71 | 570.93 | 578.70 | 10 |
| interface_test_ms | 1364.11 | 1187.65 | 1931.93 | 10 |
| total_ms | 3091.49 | 2877.33 | 3660.82 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 648.40 | 623.57 | 688.31 | 10 |
| handshake_elapsed_ms | 1223.11 | 1201.41 | 1267.01 | 10 |
| interface_test_elapsed_ms | 2587.22 | 2389.07 | 3150.98 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3660.82 | 622.59 | 0.65 | 570.93 | 1931.93 | findParks |
| 2 | pass | - | 3157.69 | 632.58 | 0.67 | 573.98 | 1422.80 | findParks |
| 3 | pass | - | 2881.39 | 601.34 | 0.70 | 575.56 | 1191.11 | findParks |
| 4 | pass | - | 3226.38 | 596.88 | 1.00 | 576.24 | 1519.81 | findParks |
| 5 | pass | - | 2877.33 | 595.76 | 0.72 | 577.84 | 1187.65 | findParks |
| 6 | pass | - | 3133.21 | 609.01 | 0.56 | 573.23 | 1442.78 | findParks |
| 7 | pass | - | 3057.25 | 608.30 | 0.54 | 575.23 | 1326.98 | findParks |
| 8 | pass | - | 2950.33 | 659.35 | 0.71 | 578.70 | 1193.91 | findParks |
| 9 | pass | - | 2959.34 | 637.08 | 0.52 | 572.55 | 1194.78 | findParks |
| 10 | pass | - | 3011.13 | 638.45 | 0.55 | 572.83 | 1229.33 | findParks |

## NixOS

- Container: laplace-nixos
- Image: laplace/nixos:local
- URL: http://localhost:8817/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 616.43 | 586.33 | 647.08 | 10 |
| wait_tcp_ms | 0.66 | 0.58 | 0.79 | 10 |
| mcp_handshake_ms | 1164.63 | 1092.25 | 1761.82 | 10 |
| interface_test_ms | 14086.43 | 13437.02 | 15440.52 | 10 |
| total_ms | 16383.17 | 15635.17 | 17954.60 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 643.93 | 616.92 | 673.06 | 10 |
| handshake_elapsed_ms | 1808.56 | 1711.84 | 2385.83 | 10 |
| interface_test_elapsed_ms | 15894.99 | 15148.86 | 17498.92 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 17954.60 | 602.11 | 0.58 | 1761.82 | 15113.09 | nixos_channels |
| 2 | pass | - | 15717.81 | 624.19 | 0.63 | 1096.23 | 13483.95 | nixos_channels |
| 3 | pass | - | 16923.12 | 596.72 | 0.59 | 1093.49 | 14697.36 | nixos_channels |
| 4 | pass | - | 15880.31 | 612.41 | 0.71 | 1104.28 | 13670.64 | nixos_channels |
| 5 | pass | - | 16264.10 | 616.91 | 0.71 | 1092.25 | 14075.63 | nixos_channels |
| 6 | pass | - | 15955.66 | 647.08 | 0.58 | 1094.58 | 13696.40 | nixos_channels |
| 7 | pass | - | 15957.95 | 638.65 | 0.66 | 1102.15 | 13635.00 | nixos_channels |
| 8 | pass | - | 17668.83 | 623.93 | 0.73 | 1100.98 | 15440.52 | nixos_channels |
| 9 | pass | - | 15635.17 | 586.33 | 0.66 | 1094.92 | 13437.02 | nixos_channels |
| 10 | pass | - | 15874.18 | 615.96 | 0.79 | 1105.59 | 13614.73 | nixos_channels |

## OKX Exchange

- Container: laplace-okx-exchange
- Image: laplace/okx-exchange:local
- URL: http://localhost:8818/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 617.52 | 587.54 | 648.41 | 10 |
| wait_tcp_ms | 0.68 | 0.55 | 0.81 | 10 |
| mcp_handshake_ms | 573.10 | 566.98 | 578.59 | 10 |
| interface_test_ms | 78.85 | 73.06 | 95.85 | 10 |
| total_ms | 1805.77 | 1763.98 | 1847.79 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 643.54 | 613.12 | 676.81 | 10 |
| handshake_elapsed_ms | 1216.64 | 1188.53 | 1243.79 | 10 |
| interface_test_elapsed_ms | 1295.49 | 1262.34 | 1318.30 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 1810.30 | 613.95 | 0.60 | 572.33 | 77.63 | health_check |
| 2 | pass | - | 1800.94 | 608.78 | 0.60 | 571.13 | 95.85 | health_check |
| 3 | pass | - | 1810.13 | 638.54 | 0.77 | 575.50 | 76.10 | health_check |
| 4 | pass | - | 1780.49 | 621.00 | 0.81 | 578.59 | 75.73 | health_check |
| 5 | pass | - | 1763.98 | 613.66 | 0.55 | 574.12 | 77.69 | health_check |
| 6 | pass | - | 1846.65 | 618.40 | 0.77 | 570.64 | 73.06 | health_check |
| 7 | pass | - | 1847.79 | 635.94 | 0.64 | 569.30 | 74.70 | health_check |
| 8 | pass | - | 1797.75 | 588.95 | 0.67 | 577.00 | 89.38 | health_check |
| 9 | pass | - | 1767.19 | 587.54 | 0.58 | 575.41 | 73.81 | health_check |
| 10 | pass | - | 1832.51 | 648.41 | 0.77 | 566.98 | 74.50 | health_check |

## OpenAPI Explorer

- Container: laplace-openapi-explorer
- Image: laplace/openapi-explorer:local
- URL: http://localhost:8819/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 614.20 | 589.98 | 624.77 | 10 |
| wait_tcp_ms | 0.67 | 0.53 | 1.08 | 10 |
| mcp_handshake_ms | 898.62 | 763.36 | 1214.14 | 10 |
| interface_test_ms | 730.73 | 448.27 | 1363.77 | 10 |
| total_ms | 2762.89 | 2338.20 | 3704.89 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 643.54 | 619.88 | 663.91 | 10 |
| handshake_elapsed_ms | 1542.16 | 1399.65 | 1857.94 | 10 |
| interface_test_elapsed_ms | 2272.90 | 1847.92 | 3221.71 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3704.89 | 621.98 | 1.08 | 1214.14 | 1363.77 | getApiOverview |
| 2 | pass | - | 2741.88 | 614.82 | 0.58 | 903.86 | 716.02 | getApiOverview |
| 3 | pass | - | 2818.02 | 619.45 | 0.55 | 867.48 | 792.83 | getApiOverview |
| 4 | pass | - | 2970.69 | 609.17 | 0.63 | 1010.47 | 822.23 | getApiOverview |
| 5 | pass | - | 2730.29 | 620.21 | 0.55 | 865.28 | 737.34 | getApiOverview |
| 6 | pass | - | 2750.69 | 623.10 | 0.57 | 772.39 | 826.50 | getApiOverview |
| 7 | pass | - | 2338.20 | 609.96 | 0.77 | 763.36 | 448.27 | getApiOverview |
| 8 | pass | - | 2421.82 | 624.77 | 0.53 | 856.64 | 457.34 | getApiOverview |
| 9 | pass | - | 2520.69 | 589.98 | 0.66 | 952.74 | 452.08 | getApiOverview |
| 10 | pass | - | 2631.73 | 608.52 | 0.74 | 779.88 | 690.93 | getApiOverview |

## OSINT Intelligence

- Container: laplace-osint-intelligence
- Image: laplace/osint-intelligence:local
- URL: http://localhost:8820/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 621.15 | 581.81 | 699.41 | 10 |
| wait_tcp_ms | 1.33 | 0.49 | 7.68 | 10 |
| mcp_handshake_ms | 1151.40 | 1094.27 | 1620.99 | 10 |
| interface_test_ms | 81.05 | 73.60 | 88.67 | 10 |
| total_ms | 2402.67 | 2292.93 | 2829.38 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 649.93 | 609.28 | 738.14 | 10 |
| handshake_elapsed_ms | 1801.34 | 1711.67 | 2265.20 | 10 |
| interface_test_elapsed_ms | 1882.39 | 1794.87 | 2353.87 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 2829.38 | 618.04 | 0.77 | 1620.99 | 88.67 | whois_lookup |
| 2 | pass | - | 2299.06 | 602.27 | 0.64 | 1097.25 | 77.97 | whois_lookup |
| 3 | pass | - | 2366.04 | 630.36 | 0.56 | 1112.23 | 79.66 | whois_lookup |
| 4 | pass | - | 2294.24 | 581.81 | 0.59 | 1102.39 | 83.45 | whois_lookup |
| 5 | pass | - | 2292.93 | 594.45 | 0.63 | 1096.01 | 78.95 | whois_lookup |
| 6 | pass | - | 2350.90 | 586.83 | 7.68 | 1102.02 | 85.87 | whois_lookup |
| 7 | pass | - | 2405.20 | 645.14 | 0.49 | 1094.27 | 78.33 | whois_lookup |
| 8 | pass | - | 2474.35 | 699.41 | 0.74 | 1098.04 | 73.60 | whois_lookup |
| 9 | pass | - | 2348.80 | 622.64 | 0.60 | 1096.17 | 78.86 | whois_lookup |
| 10 | pass | - | 2365.82 | 630.57 | 0.59 | 1094.64 | 85.14 | whois_lookup |

## Paper Search

- Container: laplace-paper-search
- Image: laplace/paper-search:local
- URL: http://localhost:8831/mcp
- Success / Partial / Fail: 7 / 0 / 3
- Failure stages: {"interface_test": 3}

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 603.66 | 585.10 | 641.20 | 10 |
| wait_tcp_ms | 0.65 | 0.50 | 0.72 | 10 |
| mcp_handshake_ms | 1682.44 | 1620.98 | 2173.25 | 10 |
| interface_test_ms | 9235.62 | 820.45 | 16877.65 | 7 |
| total_ms | 22111.90 | 3638.34 | 50836.73 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 631.68 | 610.86 | 669.61 | 10 |
| handshake_elapsed_ms | 2314.12 | 2240.52 | 2807.67 | 10 |
| interface_test_elapsed_ms | 11572.98 | 3117.13 | 19118.17 | 7 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 4155.43 | 609.73 | 0.58 | 2173.25 | 820.45 | search_arxiv |
| 2 | fail | interface_test | 35096.42 | 602.03 | 0.71 | 1622.37 | - | - |
| 3 | pass | - | 19394.77 | 591.86 | 0.50 | 1628.78 | 16632.62 | search_arxiv |
| 4 | pass | - | 3645.95 | 585.93 | 0.67 | 1628.53 | 884.42 | search_arxiv |
| 5 | pass | - | 14672.02 | 641.20 | 0.72 | 1628.80 | 11867.73 | search_arxiv |
| 6 | pass | - | 3638.34 | 596.39 | 0.70 | 1626.86 | 866.16 | search_arxiv |
| 7 | pass | - | 19624.78 | 594.83 | 0.65 | 1620.98 | 16877.65 | search_arxiv |
| 8 | pass | - | 19566.27 | 610.62 | 0.60 | 1629.54 | 16700.32 | search_arxiv |
| 9 | fail | interface_test | 50836.73 | 618.96 | 0.66 | 1628.01 | - | - |
| 10 | fail | interface_test | 50488.30 | 585.10 | 0.69 | 1637.31 | - | - |

## Reddit

- Container: laplace-reddit
- Image: laplace/reddit:local
- URL: http://localhost:8822/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 629.84 | 601.58 | 692.85 | 10 |
| wait_tcp_ms | 0.66 | 0.57 | 0.96 | 10 |
| mcp_handshake_ms | 1204.39 | 1087.76 | 1641.52 | 10 |
| interface_test_ms | 1208.51 | 1109.38 | 1610.65 | 10 |
| total_ms | 3588.35 | 3346.44 | 3964.55 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 657.78 | 628.89 | 720.61 | 10 |
| handshake_elapsed_ms | 1862.16 | 1720.89 | 2292.48 | 10 |
| interface_test_elapsed_ms | 3070.67 | 2830.27 | 3463.77 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3964.36 | 635.28 | 0.62 | 1629.44 | 1156.72 | fetch_reddit_hot_threads |
| 2 | pass | - | 3520.90 | 602.81 | 0.64 | 1103.11 | 1241.59 | fetch_reddit_hot_threads |
| 3 | pass | - | 3964.55 | 613.11 | 0.96 | 1641.52 | 1181.41 | fetch_reddit_hot_threads |
| 4 | pass | - | 3374.54 | 626.92 | 0.57 | 1095.98 | 1153.49 | fetch_reddit_hot_threads |
| 5 | pass | - | 3348.82 | 605.33 | 0.66 | 1096.46 | 1115.58 | fetch_reddit_hot_threads |
| 6 | pass | - | 3346.44 | 608.60 | 0.62 | 1087.76 | 1109.38 | fetch_reddit_hot_threads |
| 7 | pass | - | 3878.97 | 601.58 | 0.60 | 1094.20 | 1610.65 | fetch_reddit_hot_threads |
| 8 | pass | - | 3564.19 | 674.19 | 0.58 | 1101.37 | 1198.82 | fetch_reddit_hot_threads |
| 9 | pass | - | 3503.11 | 692.85 | 0.61 | 1095.64 | 1165.38 | fetch_reddit_hot_threads |
| 10 | pass | - | 3417.64 | 637.71 | 0.70 | 1098.38 | 1152.07 | fetch_reddit_hot_threads |

## Scientific Computing

- Container: laplace-scientific-computing
- Image: laplace/scientific-computing:local
- URL: http://localhost:8823/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 597.45 | 581.45 | 607.40 | 10 |
| wait_tcp_ms | 0.71 | 0.56 | 1.02 | 10 |
| mcp_handshake_ms | 1952.86 | 1622.51 | 2721.33 | 10 |
| interface_test_ms | 102.22 | 95.83 | 117.51 | 10 |
| total_ms | 3197.24 | 2861.35 | 3983.41 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 624.47 | 611.08 | 636.06 | 10 |
| handshake_elapsed_ms | 2577.33 | 2240.01 | 3347.18 | 10 |
| interface_test_elapsed_ms | 2679.56 | 2336.46 | 3454.84 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3983.41 | 602.34 | 0.69 | 2721.33 | 107.66 | view_tensor |
| 2 | pass | - | 2861.35 | 591.58 | 0.70 | 1626.97 | 97.80 | view_tensor |
| 3 | pass | - | 2881.73 | 588.75 | 1.02 | 1622.51 | 96.45 | view_tensor |
| 4 | pass | - | 2924.21 | 599.34 | 0.65 | 1671.37 | 98.20 | view_tensor |
| 5 | pass | - | 3407.07 | 607.40 | 0.59 | 2162.83 | 96.28 | view_tensor |
| 6 | pass | - | 3352.55 | 581.45 | 0.69 | 2149.94 | 110.14 | view_tensor |
| 7 | pass | - | 2888.43 | 599.11 | 0.71 | 1649.30 | 104.04 | view_tensor |
| 8 | pass | - | 3382.44 | 603.51 | 0.91 | 2146.19 | 98.32 | view_tensor |
| 9 | pass | - | 2883.16 | 597.71 | 0.59 | 1629.94 | 117.51 | view_tensor |
| 10 | pass | - | 3408.02 | 603.33 | 0.56 | 2148.22 | 95.83 | view_tensor |

## Time MCP

- Container: laplace-time-mcp
- Image: laplace/time-mcp:local
- URL: http://localhost:8824/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 596.78 | 581.12 | 611.61 | 10 |
| wait_tcp_ms | 0.68 | 0.58 | 0.76 | 10 |
| mcp_handshake_ms | 1628.83 | 1615.56 | 1649.03 | 10 |
| interface_test_ms | 139.71 | 125.84 | 160.07 | 10 |
| total_ms | 2885.73 | 2847.84 | 2922.51 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 623.77 | 609.28 | 640.37 | 10 |
| handshake_elapsed_ms | 2252.60 | 2236.41 | 2274.19 | 10 |
| interface_test_elapsed_ms | 2392.30 | 2362.25 | 2424.91 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 2922.51 | 611.61 | 0.60 | 1618.06 | 160.07 | get_current_time |
| 2 | pass | - | 2884.60 | 589.35 | 0.73 | 1626.83 | 157.22 | get_current_time |
| 3 | pass | - | 2847.84 | 584.97 | 0.65 | 1626.31 | 125.84 | get_current_time |
| 4 | pass | - | 2907.36 | 609.35 | 0.65 | 1632.23 | 156.21 | get_current_time |
| 5 | pass | - | 2852.38 | 611.06 | 0.72 | 1615.56 | 130.05 | get_current_time |
| 6 | pass | - | 2878.31 | 588.67 | 0.67 | 1649.03 | 130.11 | get_current_time |
| 7 | pass | - | 2915.24 | 585.53 | 0.69 | 1629.79 | 132.93 | get_current_time |
| 8 | pass | - | 2901.06 | 605.16 | 0.76 | 1638.71 | 136.10 | get_current_time |
| 9 | pass | - | 2873.20 | 600.97 | 0.74 | 1620.91 | 138.56 | get_current_time |
| 10 | pass | - | 2874.79 | 581.12 | 0.58 | 1630.89 | 129.96 | get_current_time |

## Unit Converter

- Container: laplace-unit-converter
- Image: laplace/unit-converter:local
- URL: http://localhost:8825/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 603.17 | 575.96 | 621.80 | 10 |
| wait_tcp_ms | 0.73 | 0.55 | 0.98 | 10 |
| mcp_handshake_ms | 1256.37 | 1090.25 | 1642.99 | 10 |
| interface_test_ms | 84.12 | 72.96 | 96.56 | 10 |
| total_ms | 2495.82 | 2297.40 | 2869.11 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 632.24 | 605.47 | 650.53 | 10 |
| handshake_elapsed_ms | 1888.62 | 1703.42 | 2270.52 | 10 |
| interface_test_elapsed_ms | 1972.74 | 1783.91 | 2359.72 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 2852.09 | 603.73 | 0.83 | 1642.99 | 83.78 | list_supported_units |
| 2 | pass | - | 2346.25 | 621.80 | 0.65 | 1096.83 | 87.58 | list_supported_units |
| 3 | pass | - | 2367.33 | 605.49 | 0.69 | 1096.87 | 82.27 | list_supported_units |
| 4 | pass | - | 2319.25 | 575.96 | 0.66 | 1097.94 | 80.49 | list_supported_units |
| 5 | pass | - | 2869.11 | 609.93 | 0.68 | 1625.56 | 93.25 | list_supported_units |
| 6 | pass | - | 2346.15 | 619.68 | 0.74 | 1106.61 | 81.55 | list_supported_units |
| 7 | pass | - | 2352.68 | 603.66 | 0.98 | 1094.37 | 96.56 | list_supported_units |
| 8 | pass | - | 2340.11 | 585.82 | 0.65 | 1090.25 | 82.61 | list_supported_units |
| 9 | pass | - | 2297.40 | 594.63 | 0.55 | 1098.15 | 80.15 | list_supported_units |
| 10 | pass | - | 2867.84 | 611.04 | 0.85 | 1614.16 | 72.96 | list_supported_units |

## Weather Data

- Container: laplace-weather-data
- Image: laplace/weather-data:local
- URL: http://localhost:8826/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 606.26 | 577.76 | 645.09 | 10 |
| wait_tcp_ms | 0.75 | 0.51 | 1.15 | 10 |
| mcp_handshake_ms | 1151.81 | 1091.67 | 1645.95 | 10 |
| interface_test_ms | 455.01 | 425.36 | 497.91 | 10 |
| total_ms | 2757.22 | 2637.82 | 3271.62 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 633.00 | 600.63 | 669.41 | 10 |
| handshake_elapsed_ms | 1784.81 | 1705.41 | 2246.58 | 10 |
| interface_test_elapsed_ms | 2239.82 | 2160.12 | 2744.50 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3271.62 | 577.76 | 0.51 | 1645.95 | 497.91 | get_current_weather_tool |
| 2 | pass | - | 2637.82 | 594.23 | 0.55 | 1114.89 | 425.36 | get_current_weather_tool |
| 3 | pass | - | 2694.14 | 624.06 | 0.61 | 1093.36 | 447.59 | get_current_weather_tool |
| 4 | pass | - | 2711.42 | 609.03 | 0.78 | 1094.23 | 438.06 | get_current_weather_tool |
| 5 | pass | - | 2750.92 | 626.26 | 0.77 | 1091.67 | 472.76 | get_current_weather_tool |
| 6 | pass | - | 2683.49 | 580.78 | 0.61 | 1096.55 | 458.15 | get_current_weather_tool |
| 7 | pass | - | 2776.20 | 645.09 | 0.91 | 1094.98 | 480.57 | get_current_weather_tool |
| 8 | pass | - | 2643.58 | 605.21 | 0.65 | 1094.03 | 435.70 | get_current_weather_tool |
| 9 | pass | - | 2715.59 | 595.09 | 0.96 | 1093.28 | 459.54 | get_current_weather_tool |
| 10 | pass | - | 2687.39 | 605.09 | 1.15 | 1099.20 | 434.42 | get_current_weather_tool |

## Wikipedia

- Container: laplace-wikipedia
- Image: laplace/wikipedia:local
- URL: http://localhost:8827/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 601.63 | 579.53 | 628.89 | 10 |
| wait_tcp_ms | 0.75 | 0.55 | 1.33 | 10 |
| mcp_handshake_ms | 1155.85 | 1093.86 | 1641.19 | 10 |
| interface_test_ms | 362.67 | 339.26 | 378.77 | 10 |
| total_ms | 2637.36 | 2538.90 | 3132.07 | 10 |

### Milestones

| Milestone | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| tcp_ready_elapsed_ms | 628.52 | 605.69 | 657.67 | 10 |
| handshake_elapsed_ms | 1784.37 | 1699.55 | 2259.13 | 10 |
| interface_test_elapsed_ms | 2147.04 | 2061.10 | 2633.27 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3132.07 | 594.49 | 0.62 | 1641.19 | 374.14 | search_wikipedia |
| 2 | pass | - | 2564.18 | 605.36 | 0.63 | 1094.80 | 365.20 | search_wikipedia |
| 3 | pass | - | 2556.58 | 586.45 | 0.70 | 1108.54 | 339.26 | search_wikipedia |
| 4 | pass | - | 2578.19 | 595.25 | 0.70 | 1097.75 | 366.95 | search_wikipedia |
| 5 | pass | - | 2601.83 | 628.89 | 1.07 | 1105.92 | 378.77 | search_wikipedia |
| 6 | pass | - | 2569.32 | 592.83 | 0.58 | 1107.13 | 357.87 | search_wikipedia |
| 7 | pass | - | 2630.73 | 625.81 | 0.75 | 1094.84 | 371.95 | search_wikipedia |
| 8 | pass | - | 2562.14 | 579.53 | 0.55 | 1093.86 | 363.25 | search_wikipedia |
| 9 | pass | - | 2538.90 | 601.10 | 0.56 | 1095.94 | 347.83 | search_wikipedia |
| 10 | pass | - | 2639.72 | 606.57 | 1.33 | 1118.58 | 361.47 | search_wikipedia |
