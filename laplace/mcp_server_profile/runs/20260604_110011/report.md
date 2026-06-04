# MCP Server Profile Report

## Overview

- Manifest: /mnt/d/Project/agentscope/src/agentscope/mcp/server_config/laplace_mcp_manifest.json
- Started: 2026-06-04T03:00:21.415299+00:00
- Completed: 2026-06-04T03:26:51.530167+00:00
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
| BioMCP | 10 | 0 | 0 | 2124.57 | 675.89 | 0.75 | 780.67 | 81.28 |
| Bibliomantic | 10 | 0 | 0 | 2392.63 | 601.47 | 0.61 | 1173.03 | 78.13 |
| Playwright | 10 | 0 | 0 | 2402.61 | 632.50 | 0.69 | 584.75 | 649.15 |
| Jupyter MCP | 10 | 0 | 0 | 8966.38 | 605.12 | 0.64 | 1725.59 | 6104.92 |
| Neo4j Cypher | 10 | 0 | 0 | 2469.69 | 610.67 | 0.69 | 1140.53 | 171.92 |
| Call for Papers | 10 | 0 | 0 | 3519.48 | 604.41 | 0.66 | 1204.00 | 1180.57 |
| Car Price Evaluator | 10 | 0 | 0 | 3565.33 | 610.15 | 0.69 | 1147.82 | 1262.27 |
| Context7 | 10 | 0 | 0 | 2705.38 | 613.89 | 0.73 | 573.41 | 976.31 |
| DEX Paprika | 9 | 0 | 1 | 14825.91 | 600.94 | 0.61 | 578.38 | 1237.50 |
| FruityVice | 10 | 0 | 0 | 4013.94 | 614.55 | 0.77 | 1199.45 | 1653.55 |
| Game Trends | 10 | 0 | 0 | 1835.23 | 606.53 | 0.63 | 617.39 | 79.10 |
| Google Maps | 10 | 0 | 0 | 1791.56 | 605.67 | 0.66 | 576.96 | 77.49 |
| Huge Icons | 10 | 0 | 0 | 3317.04 | 614.58 | 0.73 | 575.93 | 1607.05 |
| Hugging Face | 10 | 0 | 0 | 2245.47 | 608.98 | 0.77 | 617.58 | 491.80 |
| Math MCP | 10 | 0 | 0 | 1779.22 | 602.33 | 0.66 | 574.68 | 74.24 |
| Medical Calculator | 10 | 0 | 0 | 3028.80 | 622.82 | 2.17 | 1759.36 | 84.35 |
| Milvus MCP | 10 | 0 | 0 | 2260.87 | 615.64 | 0.69 | 1010.61 | 73.73 |
| Metropolitan Museum | 10 | 0 | 0 | 2485.41 | 601.26 | 0.69 | 571.10 | 770.35 |
| Movie Recommender | 10 | 0 | 0 | 3092.64 | 609.07 | 0.69 | 1148.75 | 793.80 |
| NASA Data | 7 | 0 | 3 | 19074.08 | 603.91 | 0.59 | 1312.74 | 10862.87 |
| National Parks | 10 | 0 | 0 | 3118.74 | 614.64 | 0.65 | 574.84 | 1397.51 |
| NixOS | 10 | 0 | 0 | 16100.21 | 602.55 | 0.68 | 1147.24 | 13819.31 |
| OKX Exchange | 10 | 0 | 0 | 1754.76 | 580.61 | 0.73 | 569.59 | 73.58 |
| OpenAPI Explorer | 10 | 0 | 0 | 2827.01 | 598.99 | 0.70 | 954.73 | 763.81 |
| OSINT Intelligence | 10 | 0 | 0 | 2336.66 | 594.67 | 0.62 | 1146.11 | 78.63 |
| Paper Search | 6 | 0 | 4 | 23547.99 | 610.81 | 0.70 | 1686.95 | 6036.42 |
| Reddit | 10 | 0 | 0 | 3518.14 | 606.92 | 0.73 | 1202.58 | 1150.94 |
| Scientific Computing | 10 | 0 | 0 | 3849.20 | 612.42 | 0.62 | 2595.96 | 100.62 |
| Time MCP | 10 | 0 | 0 | 3029.28 | 616.48 | 0.74 | 1733.70 | 137.53 |
| Unit Converter | 10 | 0 | 0 | 2469.59 | 615.33 | 0.70 | 1204.14 | 82.80 |
| Weather Data | 10 | 0 | 0 | 2818.11 | 630.24 | 0.86 | 1202.18 | 424.88 |
| Wikipedia | 10 | 0 | 0 | 2747.69 | 619.84 | 0.69 | 1151.32 | 433.06 |

## BioMCP

- Container: laplace-biomcp
- Image: laplace/biomcp:local
- URL: http://localhost:8830/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 675.89 | 581.14 | 798.27 | 10 |
| wait_tcp_ms | 0.75 | 0.55 | 1.02 | 10 |
| mcp_handshake_ms | 780.67 | 656.64 | 1686.98 | 10 |
| interface_test_ms | 81.28 | 71.44 | 116.32 | 10 |
| total_ms | 2124.57 | 1873.87 | 3277.08 | 10 |
| tcp_ready_elapsed_ms | 700.53 | 605.61 | 817.19 | 10 |
| handshake_elapsed_ms | 1481.20 | 1281.64 | 2504.17 | 10 |
| interface_test_elapsed_ms | 1562.48 | 1354.56 | 2620.50 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3277.08 | 798.27 | 1.02 | 1686.98 | 116.32 | think |
| 2 | pass | - | 2122.30 | 679.00 | 0.74 | 703.76 | 81.88 | think |
| 3 | pass | - | 2150.12 | 750.01 | 0.55 | 683.41 | 91.37 | think |
| 4 | pass | - | 2155.92 | 723.01 | 0.70 | 700.38 | 80.55 | think |
| 5 | pass | - | 1942.74 | 673.47 | 0.57 | 671.18 | 78.65 | think |
| 6 | pass | - | 1873.87 | 581.14 | 0.89 | 676.03 | 72.92 | think |
| 7 | pass | - | 1970.78 | 639.63 | 0.78 | 656.64 | 71.80 | think |
| 8 | pass | - | 1907.13 | 614.84 | 0.72 | 676.33 | 73.77 | think |
| 9 | pass | - | 1919.80 | 662.73 | 0.64 | 670.71 | 71.44 | think |
| 10 | pass | - | 1925.96 | 636.78 | 0.92 | 681.30 | 74.10 | think |

## Bibliomantic

- Container: laplace-bibliomantic
- Image: laplace/bibliomantic:local
- URL: http://localhost:8801/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 601.47 | 584.84 | 618.53 | 10 |
| wait_tcp_ms | 0.61 | 0.54 | 0.74 | 10 |
| mcp_handshake_ms | 1173.03 | 1087.92 | 1628.48 | 10 |
| interface_test_ms | 78.13 | 72.43 | 89.13 | 10 |
| total_ms | 2392.63 | 2268.24 | 2843.21 | 10 |
| tcp_ready_elapsed_ms | 623.98 | 606.31 | 640.60 | 10 |
| handshake_elapsed_ms | 1797.02 | 1696.77 | 2257.13 | 10 |
| interface_test_elapsed_ms | 1875.15 | 1769.20 | 2343.75 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 2843.21 | 604.71 | 0.63 | 1628.48 | 86.63 | i_ching_divination |
| 2 | pass | - | 2301.44 | 609.87 | 0.63 | 1089.28 | 73.99 | i_ching_divination |
| 3 | pass | - | 2362.03 | 618.53 | 0.55 | 1087.92 | 75.10 | i_ching_divination |
| 4 | pass | - | 2357.43 | 616.00 | 0.65 | 1096.93 | 74.55 | i_ching_divination |
| 5 | pass | - | 2305.03 | 584.84 | 0.56 | 1090.46 | 72.43 | i_ching_divination |
| 6 | pass | - | 2280.84 | 602.24 | 0.62 | 1090.05 | 76.14 | i_ching_divination |
| 7 | pass | - | 2342.37 | 586.12 | 0.74 | 1090.86 | 89.13 | i_ching_divination |
| 8 | pass | - | 2589.52 | 608.35 | 0.60 | 1373.00 | 75.41 | i_ching_divination |
| 9 | pass | - | 2268.24 | 595.72 | 0.54 | 1088.50 | 82.81 | i_ching_divination |
| 10 | pass | - | 2276.22 | 588.35 | 0.62 | 1094.87 | 75.17 | i_ching_divination |

## Playwright

- Container: playwright-mcp
- Image: laplace/playwright-mcp:local
- Original image: mcr.microsoft.com/playwright/mcp:latest
- URL: http://localhost:8804/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 632.50 | 605.21 | 669.87 | 10 |
| wait_tcp_ms | 0.69 | 0.61 | 0.81 | 10 |
| mcp_handshake_ms | 584.75 | 577.04 | 595.81 | 10 |
| interface_test_ms | 649.15 | 472.69 | 1862.62 | 10 |
| total_ms | 2402.61 | 2169.51 | 3631.22 | 10 |
| tcp_ready_elapsed_ms | 655.17 | 626.69 | 691.40 | 10 |
| handshake_elapsed_ms | 1239.92 | 1206.79 | 1268.77 | 10 |
| interface_test_elapsed_ms | 1889.07 | 1679.48 | 3090.03 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3631.22 | 618.34 | 0.67 | 589.56 | 1862.62 | browser_close |
| 2 | pass | - | 2291.79 | 625.60 | 0.68 | 582.97 | 541.62 | browser_close |
| 3 | pass | - | 2231.21 | 627.90 | 0.61 | 582.23 | 516.55 | browser_close |
| 4 | pass | - | 2311.05 | 632.06 | 0.81 | 587.40 | 530.07 | browser_close |
| 5 | pass | - | 2270.95 | 669.87 | 0.69 | 577.04 | 510.61 | browser_close |
| 6 | pass | - | 2169.51 | 605.21 | 0.63 | 580.10 | 472.69 | browser_close |
| 7 | pass | - | 2243.87 | 634.51 | 0.70 | 583.89 | 481.89 | browser_close |
| 8 | pass | - | 2283.68 | 652.43 | 0.76 | 580.87 | 496.53 | browser_close |
| 9 | pass | - | 2326.02 | 648.25 | 0.65 | 595.81 | 543.99 | browser_close |
| 10 | pass | - | 2266.82 | 610.82 | 0.69 | 587.58 | 534.94 | browser_close |

## Jupyter MCP

- Container: laplace-jupyter-mcp
- Image: laplace/jupyter-mcp-server:local
- Original image: datalayer/jupyter-mcp-server:latest
- URL: http://localhost:8828/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 605.12 | 573.10 | 642.47 | 10 |
| wait_tcp_ms | 0.64 | 0.52 | 0.79 | 10 |
| mcp_handshake_ms | 1725.59 | 1610.25 | 2677.47 | 10 |
| interface_test_ms | 6104.92 | 6093.98 | 6121.20 | 10 |
| total_ms | 8966.38 | 8829.44 | 9960.28 | 10 |
| tcp_ready_elapsed_ms | 626.93 | 592.66 | 663.94 | 10 |
| handshake_elapsed_ms | 2352.52 | 2208.02 | 3341.41 | 10 |
| interface_test_elapsed_ms | 8457.44 | 8315.74 | 9440.50 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 9960.28 | 642.47 | 0.77 | 2677.47 | 6099.09 | list_files |
| 2 | pass | - | 8829.44 | 597.22 | 0.58 | 1626.75 | 6103.19 | list_files |
| 3 | pass | - | 8871.25 | 593.55 | 0.54 | 1614.35 | 6110.52 | list_files |
| 4 | pass | - | 8837.13 | 610.79 | 0.73 | 1625.76 | 6109.82 | list_files |
| 5 | pass | - | 8888.06 | 622.63 | 0.59 | 1610.25 | 6121.20 | list_files |
| 6 | pass | - | 8842.12 | 605.43 | 0.66 | 1621.77 | 6093.98 | list_files |
| 7 | pass | - | 8874.28 | 601.58 | 0.58 | 1624.78 | 6100.26 | list_files |
| 8 | pass | - | 8867.70 | 608.75 | 0.67 | 1621.77 | 6102.01 | list_files |
| 9 | pass | - | 8844.85 | 595.71 | 0.79 | 1617.69 | 6101.38 | list_files |
| 10 | pass | - | 8848.73 | 573.10 | 0.52 | 1615.36 | 6107.72 | list_files |

## Neo4j Cypher

- Container: laplace-neo4j-cypher
- Image: laplace/neo4j-cypher:local
- Original image: mcp/neo4j-cypher:latest
- URL: http://localhost:8829/mcp/
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 610.67 | 599.83 | 638.90 | 10 |
| wait_tcp_ms | 0.69 | 0.58 | 1.02 | 10 |
| mcp_handshake_ms | 1140.53 | 1083.87 | 1600.91 | 10 |
| interface_test_ms | 171.92 | 85.84 | 887.43 | 10 |
| total_ms | 2469.69 | 2279.72 | 3631.19 | 10 |
| tcp_ready_elapsed_ms | 632.69 | 622.68 | 659.77 | 10 |
| handshake_elapsed_ms | 1773.21 | 1707.21 | 2226.87 | 10 |
| interface_test_elapsed_ms | 1945.13 | 1794.11 | 3114.31 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3631.19 | 608.65 | 0.66 | 1600.91 | 887.43 | read_neo4j_cypher |
| 2 | pass | - | 2343.35 | 613.83 | 0.64 | 1094.40 | 92.59 | read_neo4j_cypher |
| 3 | pass | - | 2347.42 | 602.13 | 0.71 | 1099.13 | 94.11 | read_neo4j_cypher |
| 4 | pass | - | 2376.01 | 623.67 | 0.61 | 1087.82 | 96.85 | read_neo4j_cypher |
| 5 | pass | - | 2345.85 | 610.34 | 0.60 | 1087.45 | 99.44 | read_neo4j_cypher |
| 6 | pass | - | 2386.21 | 638.90 | 1.02 | 1089.51 | 92.02 | read_neo4j_cypher |
| 7 | pass | - | 2279.72 | 601.94 | 0.58 | 1091.07 | 91.40 | read_neo4j_cypher |
| 8 | pass | - | 2336.05 | 599.83 | 0.75 | 1083.87 | 86.89 | read_neo4j_cypher |
| 9 | pass | - | 2361.96 | 606.21 | 0.67 | 1084.88 | 92.58 | read_neo4j_cypher |
| 10 | pass | - | 2289.18 | 601.22 | 0.67 | 1086.22 | 85.84 | read_neo4j_cypher |

## Call for Papers

- Container: laplace-call-for-papers
- Image: laplace/call-for-papers:local
- URL: http://localhost:8802/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 604.41 | 586.41 | 628.11 | 10 |
| wait_tcp_ms | 0.66 | 0.56 | 1.14 | 10 |
| mcp_handshake_ms | 1204.00 | 1088.84 | 2191.08 | 10 |
| interface_test_ms | 1180.57 | 802.58 | 1806.74 | 10 |
| total_ms | 3519.48 | 3020.91 | 5083.63 | 10 |
| tcp_ready_elapsed_ms | 626.61 | 606.98 | 650.33 | 10 |
| handshake_elapsed_ms | 1830.62 | 1702.93 | 2798.06 | 10 |
| interface_test_elapsed_ms | 3011.19 | 2520.78 | 4604.80 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 5083.63 | 588.99 | 0.57 | 2191.08 | 1806.74 | get_events |
| 2 | pass | - | 3693.80 | 628.11 | 0.56 | 1090.80 | 1446.16 | get_events |
| 3 | pass | - | 3423.53 | 599.09 | 0.58 | 1096.28 | 1204.77 | get_events |
| 4 | pass | - | 3444.60 | 618.54 | 0.62 | 1096.58 | 1214.35 | get_events |
| 5 | pass | - | 3283.36 | 590.33 | 0.65 | 1092.43 | 1063.85 | get_events |
| 6 | pass | - | 3278.38 | 626.66 | 0.68 | 1092.55 | 1006.96 | get_events |
| 7 | pass | - | 3294.92 | 601.13 | 0.61 | 1099.98 | 1067.30 | get_events |
| 8 | pass | - | 3020.91 | 605.38 | 1.14 | 1088.84 | 802.58 | get_events |
| 9 | pass | - | 3440.97 | 599.50 | 0.60 | 1097.73 | 1192.38 | get_events |
| 10 | pass | - | 3230.71 | 586.41 | 0.56 | 1093.75 | 1000.62 | get_events |

## Car Price Evaluator

- Container: laplace-car-price-evaluator
- Image: laplace/car-price-evaluator:local
- URL: http://localhost:8803/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 610.15 | 573.65 | 640.84 | 10 |
| wait_tcp_ms | 0.69 | 0.59 | 0.83 | 10 |
| mcp_handshake_ms | 1147.82 | 1089.50 | 1618.87 | 10 |
| interface_test_ms | 1262.27 | 613.47 | 2105.64 | 10 |
| total_ms | 3565.33 | 2892.39 | 4818.25 | 10 |
| tcp_ready_elapsed_ms | 632.96 | 592.82 | 665.12 | 10 |
| handshake_elapsed_ms | 1780.78 | 1715.49 | 2211.69 | 10 |
| interface_test_elapsed_ms | 3043.05 | 2362.45 | 4317.33 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 4818.25 | 573.65 | 0.67 | 1618.87 | 2105.64 | get_car_brands |
| 2 | pass | - | 3916.89 | 606.08 | 0.60 | 1096.46 | 1674.33 | get_car_brands |
| 3 | pass | - | 2958.38 | 605.21 | 0.80 | 1101.75 | 681.75 | get_car_brands |
| 4 | pass | - | 3879.81 | 614.77 | 0.69 | 1091.67 | 1593.73 | get_car_brands |
| 5 | pass | - | 3167.55 | 598.61 | 0.69 | 1094.29 | 910.15 | get_car_brands |
| 6 | pass | - | 3867.36 | 621.02 | 0.59 | 1089.50 | 1630.73 | get_car_brands |
| 7 | pass | - | 2892.39 | 633.95 | 0.70 | 1091.48 | 613.47 | get_car_brands |
| 8 | pass | - | 2996.12 | 640.84 | 0.61 | 1091.41 | 736.02 | get_car_brands |
| 9 | pass | - | 3209.78 | 604.57 | 0.83 | 1110.44 | 958.69 | get_car_brands |
| 10 | pass | - | 3946.81 | 602.79 | 0.79 | 1092.36 | 1718.15 | get_car_brands |

## Context7

- Container: laplace-context7
- Image: laplace/context7:local
- URL: http://localhost:8904/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 613.89 | 588.89 | 638.74 | 10 |
| wait_tcp_ms | 0.73 | 0.59 | 1.30 | 10 |
| mcp_handshake_ms | 573.41 | 565.53 | 584.14 | 10 |
| interface_test_ms | 976.31 | 895.09 | 1087.23 | 10 |
| total_ms | 2705.38 | 2591.93 | 2837.31 | 10 |
| tcp_ready_elapsed_ms | 636.39 | 611.59 | 661.17 | 10 |
| handshake_elapsed_ms | 1209.80 | 1183.09 | 1230.17 | 10 |
| interface_test_elapsed_ms | 2186.11 | 2088.45 | 2314.73 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 2807.10 | 624.39 | 0.67 | 583.21 | 1087.23 | resolve-library-id |
| 2 | pass | - | 2763.08 | 616.30 | 0.61 | 569.72 | 1023.82 | resolve-library-id |
| 3 | pass | - | 2654.46 | 618.09 | 0.74 | 584.14 | 928.45 | resolve-library-id |
| 4 | pass | - | 2680.43 | 588.89 | 0.62 | 571.50 | 954.35 | resolve-library-id |
| 5 | pass | - | 2637.59 | 614.83 | 0.59 | 565.53 | 917.84 | resolve-library-id |
| 6 | pass | - | 2591.93 | 604.86 | 0.68 | 574.06 | 907.08 | resolve-library-id |
| 7 | pass | - | 2646.30 | 602.85 | 0.64 | 568.51 | 895.09 | resolve-library-id |
| 8 | pass | - | 2657.72 | 638.74 | 0.62 | 569.00 | 923.70 | resolve-library-id |
| 9 | pass | - | 2837.31 | 634.29 | 1.30 | 572.15 | 1071.37 | resolve-library-id |
| 10 | pass | - | 2777.86 | 595.64 | 0.79 | 576.26 | 1054.21 | resolve-library-id |

## DEX Paprika

- Container: laplace-dex-paprika
- Image: laplace/dex-paprika:local
- URL: http://localhost:8805/mcp
- Success / Partial / Fail: 9 / 0 / 1
- Failure stages: {"tcp_ready": 1}

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 600.94 | 580.47 | 618.49 | 10 |
| wait_tcp_ms | 0.61 | 0.52 | 0.72 | 9 |
| mcp_handshake_ms | 578.38 | 572.85 | 594.48 | 9 |
| interface_test_ms | 1237.50 | 869.35 | 1813.96 | 9 |
| total_ms | 14825.91 | 2599.55 | 121640.16 | 10 |
| tcp_ready_elapsed_ms | 621.66 | 602.46 | 642.74 | 9 |
| handshake_elapsed_ms | 1200.04 | 1175.31 | 1218.11 | 9 |
| interface_test_elapsed_ms | 2437.54 | 2076.42 | 2995.39 | 9 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | fail | tcp_ready | 121640.16 | 614.69 | - | - | - | - |
| 2 | pass | - | 3526.88 | 583.65 | 0.57 | 577.38 | 1813.96 | getNetworks |
| 3 | pass | - | 2599.55 | 618.49 | 0.54 | 577.23 | 872.25 | getNetworks |
| 4 | pass | - | 3060.63 | 586.26 | 0.60 | 594.48 | 1376.78 | getNetworks |
| 5 | pass | - | 3224.29 | 580.47 | 0.60 | 572.85 | 1540.84 | getNetworks |
| 6 | pass | - | 2687.13 | 592.83 | 0.52 | 575.09 | 1017.27 | getNetworks |
| 7 | pass | - | 2602.74 | 609.64 | 0.67 | 577.44 | 869.35 | getNetworks |
| 8 | pass | - | 3125.72 | 600.28 | 0.72 | 578.53 | 1395.57 | getNetworks |
| 9 | pass | - | 3100.78 | 607.19 | 0.70 | 577.06 | 1358.93 | getNetworks |
| 10 | pass | - | 2691.20 | 615.93 | 0.60 | 575.37 | 892.52 | getNetworks |

## FruityVice

- Container: laplace-fruityvice
- Image: laplace/fruityvice:local
- URL: http://localhost:8806/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 614.55 | 592.23 | 644.58 | 10 |
| wait_tcp_ms | 0.77 | 0.53 | 1.54 | 10 |
| mcp_handshake_ms | 1199.45 | 1090.13 | 2163.21 | 10 |
| interface_test_ms | 1653.55 | 1092.82 | 2012.77 | 10 |
| total_ms | 4013.94 | 3298.82 | 5329.55 | 10 |
| tcp_ready_elapsed_ms | 638.68 | 611.99 | 668.47 | 10 |
| handshake_elapsed_ms | 1838.13 | 1702.55 | 2831.68 | 10 |
| interface_test_elapsed_ms | 3491.68 | 2816.27 | 4844.45 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 5329.55 | 644.58 | 1.54 | 2163.21 | 2012.77 | get_fruit_nutrition |
| 2 | pass | - | 3905.73 | 621.43 | 0.53 | 1093.97 | 1611.50 | get_fruit_nutrition |
| 3 | pass | - | 4059.13 | 632.49 | 0.64 | 1093.36 | 1741.42 | get_fruit_nutrition |
| 4 | pass | - | 4039.53 | 617.91 | 0.70 | 1090.13 | 1779.48 | get_fruit_nutrition |
| 5 | pass | - | 3761.79 | 604.30 | 0.90 | 1091.58 | 1520.91 | get_fruit_nutrition |
| 6 | pass | - | 3958.36 | 592.23 | 0.66 | 1090.56 | 1712.30 | get_fruit_nutrition |
| 7 | pass | - | 3298.82 | 606.85 | 0.55 | 1091.20 | 1092.82 | get_fruit_nutrition |
| 8 | pass | - | 3969.92 | 606.37 | 0.68 | 1095.75 | 1738.78 | get_fruit_nutrition |
| 9 | pass | - | 4013.47 | 610.03 | 0.66 | 1093.58 | 1774.23 | get_fruit_nutrition |
| 10 | pass | - | 3803.14 | 609.27 | 0.81 | 1091.20 | 1551.33 | get_fruit_nutrition |

## Game Trends

- Container: laplace-game-trends
- Image: laplace/game-trends:local
- URL: http://localhost:8807/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 606.53 | 583.73 | 629.42 | 10 |
| wait_tcp_ms | 0.63 | 0.53 | 1.00 | 10 |
| mcp_handshake_ms | 617.39 | 561.73 | 1092.58 | 10 |
| interface_test_ms | 79.10 | 72.26 | 93.25 | 10 |
| total_ms | 1835.23 | 1728.57 | 2238.78 | 10 |
| tcp_ready_elapsed_ms | 628.15 | 605.34 | 654.22 | 10 |
| handshake_elapsed_ms | 1245.54 | 1169.83 | 1699.10 | 10 |
| interface_test_elapsed_ms | 1324.64 | 1251.77 | 1774.95 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 2238.78 | 586.33 | 0.55 | 1092.58 | 75.85 | health_check |
| 2 | pass | - | 1781.15 | 611.68 | 0.71 | 566.50 | 83.46 | health_check |
| 3 | pass | - | 1765.02 | 628.63 | 1.00 | 564.52 | 74.46 | health_check |
| 4 | pass | - | 1772.16 | 583.73 | 0.60 | 564.48 | 81.94 | health_check |
| 5 | pass | - | 1799.71 | 604.78 | 0.53 | 561.93 | 73.57 | health_check |
| 6 | pass | - | 1816.38 | 598.68 | 0.55 | 567.28 | 89.27 | health_check |
| 7 | pass | - | 1792.69 | 614.94 | 0.53 | 561.73 | 73.33 | health_check |
| 8 | pass | - | 1728.57 | 600.11 | 0.65 | 563.66 | 73.61 | health_check |
| 9 | pass | - | 1781.64 | 629.42 | 0.56 | 562.99 | 72.26 | health_check |
| 10 | pass | - | 1876.23 | 606.98 | 0.57 | 568.22 | 93.25 | health_check |

## Google Maps

- Container: laplace-google-maps
- Image: laplace/google-maps:local
- URL: http://localhost:8808/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 605.67 | 584.63 | 618.76 | 10 |
| wait_tcp_ms | 0.66 | 0.52 | 0.81 | 10 |
| mcp_handshake_ms | 576.96 | 574.50 | 579.39 | 10 |
| interface_test_ms | 77.49 | 71.66 | 93.45 | 10 |
| total_ms | 1791.56 | 1753.65 | 1838.98 | 10 |
| tcp_ready_elapsed_ms | 627.45 | 606.89 | 639.34 | 10 |
| handshake_elapsed_ms | 1204.40 | 1184.70 | 1218.24 | 10 |
| interface_test_elapsed_ms | 1281.90 | 1257.60 | 1311.69 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 1758.71 | 599.75 | 0.81 | 577.22 | 77.82 | echo |
| 2 | pass | - | 1789.70 | 612.92 | 0.69 | 574.85 | 71.66 | echo |
| 3 | pass | - | 1753.65 | 613.44 | 0.62 | 577.17 | 72.25 | echo |
| 4 | pass | - | 1814.40 | 618.76 | 0.67 | 578.90 | 93.45 | echo |
| 5 | pass | - | 1794.58 | 616.25 | 0.52 | 575.12 | 72.33 | echo |
| 6 | pass | - | 1838.98 | 584.63 | 0.71 | 577.80 | 72.90 | echo |
| 7 | pass | - | 1807.14 | 608.45 | 0.60 | 574.50 | 73.03 | echo |
| 8 | pass | - | 1772.61 | 604.42 | 0.62 | 579.39 | 86.22 | echo |
| 9 | pass | - | 1810.62 | 605.18 | 0.62 | 577.35 | 75.27 | echo |
| 10 | pass | - | 1775.25 | 592.91 | 0.72 | 577.26 | 80.02 | echo |

## Huge Icons

- Container: laplace-huge-icons
- Image: laplace/huge-icons:local
- URL: http://localhost:8809/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 614.58 | 590.80 | 629.93 | 10 |
| wait_tcp_ms | 0.73 | 0.58 | 0.98 | 10 |
| mcp_handshake_ms | 575.93 | 572.08 | 580.93 | 10 |
| interface_test_ms | 1607.05 | 1442.07 | 1923.48 | 10 |
| total_ms | 3317.04 | 3125.84 | 3678.95 | 10 |
| tcp_ready_elapsed_ms | 637.69 | 614.98 | 654.85 | 10 |
| handshake_elapsed_ms | 1213.62 | 1188.02 | 1235.76 | 10 |
| interface_test_elapsed_ms | 2820.68 | 2630.09 | 3126.69 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3678.95 | 609.45 | 0.73 | 572.37 | 1923.48 | list_icons |
| 2 | pass | - | 3323.71 | 609.07 | 0.58 | 572.76 | 1615.43 | list_icons |
| 3 | pass | - | 3357.28 | 629.93 | 0.98 | 580.91 | 1604.56 | list_icons |
| 4 | pass | - | 3286.68 | 610.21 | 0.74 | 574.38 | 1609.00 | list_icons |
| 5 | pass | - | 3269.22 | 629.51 | 0.79 | 579.19 | 1577.86 | list_icons |
| 6 | pass | - | 3259.62 | 616.12 | 0.72 | 572.08 | 1533.22 | list_icons |
| 7 | pass | - | 3319.91 | 618.62 | 0.63 | 580.82 | 1628.71 | list_icons |
| 8 | pass | - | 3125.84 | 590.80 | 0.67 | 573.04 | 1442.07 | list_icons |
| 9 | pass | - | 3272.37 | 623.59 | 0.85 | 572.86 | 1547.64 | list_icons |
| 10 | pass | - | 3276.85 | 608.53 | 0.59 | 580.93 | 1588.54 | list_icons |

## Hugging Face

- Container: laplace-huggingface
- Image: laplace/huggingface:local
- URL: http://localhost:8810/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 608.98 | 575.78 | 649.61 | 10 |
| wait_tcp_ms | 0.77 | 0.62 | 1.19 | 10 |
| mcp_handshake_ms | 617.58 | 561.79 | 1090.51 | 10 |
| interface_test_ms | 491.80 | 435.52 | 629.75 | 10 |
| total_ms | 2245.47 | 2103.85 | 2643.27 | 10 |
| tcp_ready_elapsed_ms | 631.12 | 598.88 | 670.38 | 10 |
| handshake_elapsed_ms | 1248.70 | 1162.77 | 1717.51 | 10 |
| interface_test_elapsed_ms | 1740.50 | 1619.21 | 2171.11 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 2643.27 | 609.49 | 0.68 | 1090.51 | 453.60 | search-models |
| 2 | pass | - | 2332.39 | 587.47 | 0.64 | 561.79 | 629.75 | search-models |
| 3 | pass | - | 2231.93 | 649.61 | 0.69 | 567.44 | 452.14 | search-models |
| 4 | pass | - | 2206.73 | 624.56 | 0.62 | 563.64 | 454.74 | search-models |
| 5 | pass | - | 2147.26 | 615.61 | 0.65 | 563.62 | 448.58 | search-models |
| 6 | pass | - | 2115.85 | 612.20 | 1.19 | 562.74 | 448.94 | search-models |
| 7 | pass | - | 2277.25 | 575.78 | 0.74 | 563.89 | 580.44 | search-models |
| 8 | pass | - | 2103.85 | 591.23 | 1.01 | 563.90 | 441.80 | search-models |
| 9 | pass | - | 2109.07 | 605.48 | 0.85 | 562.89 | 435.52 | search-models |
| 10 | pass | - | 2287.09 | 618.36 | 0.64 | 575.41 | 572.44 | search-models |

## Math MCP

- Container: laplace-math-mcp
- Image: laplace/math-mcp:local
- URL: http://localhost:8811/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 602.33 | 575.33 | 617.51 | 10 |
| wait_tcp_ms | 0.66 | 0.53 | 0.81 | 10 |
| mcp_handshake_ms | 574.68 | 569.22 | 581.90 | 10 |
| interface_test_ms | 74.24 | 69.05 | 81.01 | 10 |
| total_ms | 1779.22 | 1760.39 | 1802.13 | 10 |
| tcp_ready_elapsed_ms | 624.76 | 598.03 | 640.82 | 10 |
| handshake_elapsed_ms | 1199.43 | 1169.71 | 1214.96 | 10 |
| interface_test_elapsed_ms | 1273.67 | 1245.42 | 1294.26 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 1772.65 | 598.26 | 0.72 | 581.90 | 75.58 | sum |
| 2 | pass | - | 1802.13 | 601.34 | 0.57 | 576.81 | 74.29 | sum |
| 3 | pass | - | 1789.54 | 615.14 | 0.53 | 575.80 | 79.42 | sum |
| 4 | pass | - | 1777.30 | 575.33 | 0.81 | 571.68 | 75.71 | sum |
| 5 | pass | - | 1760.39 | 609.93 | 0.64 | 576.96 | 69.79 | sum |
| 6 | pass | - | 1791.92 | 610.72 | 0.66 | 574.76 | 73.24 | sum |
| 7 | pass | - | 1771.46 | 599.59 | 0.64 | 573.27 | 81.01 | sum |
| 8 | pass | - | 1780.76 | 602.97 | 0.60 | 572.21 | 69.05 | sum |
| 9 | pass | - | 1781.73 | 592.50 | 0.66 | 569.22 | 69.72 | sum |
| 10 | pass | - | 1764.27 | 617.51 | 0.79 | 574.14 | 74.58 | sum |

## Medical Calculator

- Container: laplace-medical-calculator
- Image: laplace/medical-calculator:local
- URL: http://localhost:18812/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 622.82 | 576.39 | 652.27 | 10 |
| wait_tcp_ms | 2.17 | 0.68 | 4.50 | 10 |
| mcp_handshake_ms | 1759.36 | 1642.68 | 2695.02 | 10 |
| interface_test_ms | 84.35 | 75.81 | 94.71 | 10 |
| total_ms | 3028.80 | 2853.54 | 3984.69 | 10 |
| tcp_ready_elapsed_ms | 647.80 | 601.43 | 684.14 | 10 |
| handshake_elapsed_ms | 2407.16 | 2252.80 | 3374.90 | 10 |
| interface_test_elapsed_ms | 2491.51 | 2329.77 | 3458.76 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3984.69 | 651.35 | 0.68 | 2695.02 | 83.85 | wells_pe_criteria |
| 2 | pass | - | 2936.45 | 648.76 | 3.50 | 1653.80 | 86.18 | wells_pe_criteria |
| 3 | pass | - | 2967.68 | 637.03 | 4.50 | 1674.15 | 87.91 | wells_pe_criteria |
| 4 | pass | - | 2904.56 | 594.91 | 1.14 | 1663.59 | 82.49 | wells_pe_criteria |
| 5 | pass | - | 2952.14 | 626.00 | 1.36 | 1660.97 | 87.76 | wells_pe_criteria |
| 6 | pass | - | 2854.94 | 576.39 | 3.68 | 1651.37 | 76.97 | wells_pe_criteria |
| 7 | pass | - | 2853.54 | 594.01 | 1.15 | 1642.68 | 78.52 | wells_pe_criteria |
| 8 | pass | - | 2895.75 | 630.29 | 0.99 | 1643.80 | 89.26 | wells_pe_criteria |
| 9 | pass | - | 2979.41 | 652.27 | 3.67 | 1647.60 | 75.81 | wells_pe_criteria |
| 10 | pass | - | 2958.81 | 617.13 | 0.98 | 1660.61 | 94.71 | wells_pe_criteria |

## Milvus MCP

- Container: laplace-mcp-server-milvus
- Image: laplace/mcp-server-milvus:local
- URL: http://localhost:8832/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 615.64 | 582.82 | 684.89 | 10 |
| wait_tcp_ms | 0.69 | 0.48 | 1.17 | 10 |
| mcp_handshake_ms | 1010.61 | 571.88 | 1199.48 | 10 |
| interface_test_ms | 73.73 | 68.65 | 79.97 | 10 |
| total_ms | 2260.87 | 1788.04 | 2540.78 | 10 |
| tcp_ready_elapsed_ms | 637.37 | 603.50 | 706.20 | 10 |
| handshake_elapsed_ms | 1647.98 | 1175.38 | 1905.68 | 10 |
| interface_test_elapsed_ms | 1721.71 | 1252.94 | 1985.65 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 2540.78 | 684.89 | 1.17 | 1199.48 | 79.97 | milvus_list_databases |
| 2 | pass | - | 2364.34 | 622.34 | 0.59 | 1105.41 | 71.15 | milvus_list_databases |
| 3 | pass | - | 2361.82 | 623.34 | 0.58 | 1103.51 | 72.37 | milvus_list_databases |
| 4 | pass | - | 2338.97 | 598.31 | 0.64 | 1114.07 | 77.43 | milvus_list_databases |
| 5 | pass | - | 2403.12 | 615.42 | 1.03 | 1114.15 | 76.13 | milvus_list_databases |
| 6 | pass | - | 2317.26 | 591.56 | 0.60 | 1112.48 | 74.16 | milvus_list_databases |
| 7 | pass | - | 2341.29 | 619.88 | 0.55 | 1106.55 | 68.65 | milvus_list_databases |
| 8 | pass | - | 1788.04 | 582.82 | 0.48 | 571.88 | 77.56 | milvus_list_databases |
| 9 | pass | - | 1843.42 | 607.64 | 0.62 | 573.81 | 70.80 | milvus_list_databases |
| 10 | pass | - | 2309.70 | 610.26 | 0.63 | 1104.74 | 69.07 | milvus_list_databases |

## Metropolitan Museum

- Container: laplace-metmuseum
- Image: laplace/metmuseum:local
- URL: http://localhost:8813/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 601.26 | 576.19 | 629.05 | 10 |
| wait_tcp_ms | 0.69 | 0.57 | 1.31 | 10 |
| mcp_handshake_ms | 571.10 | 567.16 | 576.53 | 10 |
| interface_test_ms | 770.35 | 670.46 | 1330.96 | 10 |
| total_ms | 2485.41 | 2346.85 | 3035.97 | 10 |
| tcp_ready_elapsed_ms | 622.72 | 596.91 | 651.46 | 10 |
| handshake_elapsed_ms | 1193.82 | 1165.32 | 1220.89 | 10 |
| interface_test_elapsed_ms | 1964.17 | 1862.72 | 2519.10 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 2461.36 | 594.27 | 0.57 | 570.82 | 721.67 | list-departments |
| 2 | pass | - | 2346.85 | 580.10 | 0.58 | 569.37 | 691.30 | list-departments |
| 3 | pass | - | 2397.45 | 592.25 | 0.65 | 575.39 | 707.74 | list-departments |
| 4 | pass | - | 2412.69 | 629.05 | 0.80 | 569.43 | 670.46 | list-departments |
| 5 | pass | - | 2391.47 | 620.63 | 0.60 | 571.33 | 702.75 | list-departments |
| 6 | pass | - | 2481.83 | 606.58 | 0.62 | 567.16 | 716.37 | list-departments |
| 7 | pass | - | 3035.97 | 597.31 | 0.67 | 570.66 | 1330.96 | list-departments |
| 8 | pass | - | 2435.53 | 615.49 | 0.57 | 571.89 | 714.54 | list-departments |
| 9 | pass | - | 2474.58 | 576.19 | 0.58 | 568.41 | 766.75 | list-departments |
| 10 | pass | - | 2416.34 | 600.69 | 1.31 | 576.53 | 680.91 | list-departments |

## Movie Recommender

- Container: laplace-movie-recommender
- Image: laplace/movie-recommender:local
- URL: http://localhost:8814/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 609.07 | 582.90 | 634.32 | 10 |
| wait_tcp_ms | 0.69 | 0.48 | 1.07 | 10 |
| mcp_handshake_ms | 1148.75 | 1088.86 | 1633.28 | 10 |
| interface_test_ms | 793.80 | 658.12 | 1273.72 | 10 |
| total_ms | 3092.64 | 2881.80 | 3595.37 | 10 |
| tcp_ready_elapsed_ms | 632.69 | 604.29 | 659.05 | 10 |
| handshake_elapsed_ms | 1781.44 | 1697.27 | 2244.59 | 10 |
| interface_test_elapsed_ms | 2575.24 | 2389.59 | 3055.23 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3595.37 | 588.03 | 0.78 | 1633.28 | 810.63 | get_movies |
| 2 | pass | - | 2933.55 | 582.90 | 0.62 | 1092.97 | 692.33 | get_movies |
| 3 | pass | - | 3517.01 | 617.09 | 0.65 | 1091.76 | 1273.72 | get_movies |
| 4 | pass | - | 2961.55 | 622.89 | 0.67 | 1103.79 | 690.63 | get_movies |
| 5 | pass | - | 2901.08 | 632.97 | 0.67 | 1095.49 | 663.27 | get_movies |
| 6 | pass | - | 3338.52 | 613.25 | 0.61 | 1091.92 | 1088.14 | get_movies |
| 7 | pass | - | 2941.26 | 605.61 | 1.07 | 1090.61 | 673.86 | get_movies |
| 8 | pass | - | 2881.80 | 592.31 | 0.48 | 1103.09 | 685.55 | get_movies |
| 9 | pass | - | 2933.13 | 601.28 | 0.69 | 1095.75 | 701.76 | get_movies |
| 10 | pass | - | 2923.09 | 634.32 | 0.65 | 1088.86 | 658.12 | get_movies |

## NASA Data

- Container: laplace-nasa-data
- Image: laplace/nasa-data:local
- URL: http://localhost:8815/mcp
- Success / Partial / Fail: 7 / 0 / 3
- Failure stages: {"interface_test": 3}

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 603.91 | 581.09 | 630.31 | 10 |
| wait_tcp_ms | 0.59 | 0.47 | 0.68 | 10 |
| mcp_handshake_ms | 1312.74 | 1092.78 | 2154.17 | 10 |
| interface_test_ms | 10862.87 | 3708.06 | 29715.77 | 7 |
| total_ms | 19074.08 | 5963.32 | 33007.16 | 10 |
| tcp_ready_elapsed_ms | 625.67 | 601.81 | 652.23 | 10 |
| handshake_elapsed_ms | 1938.41 | 1697.08 | 2767.42 | 10 |
| interface_test_elapsed_ms | 12882.93 | 5414.56 | 32483.20 | 7 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 33007.16 | 593.78 | 0.56 | 2154.17 | 29715.77 | get_astronomy_picture_of_day |
| 2 | pass | - | 6205.21 | 599.08 | 0.64 | 1092.78 | 3973.39 | get_astronomy_picture_of_day |
| 3 | fail | interface_test | 32288.15 | 630.31 | 0.62 | 1105.54 | - | - |
| 4 | pass | - | 20701.64 | 600.32 | 0.58 | 1653.44 | 17866.38 | get_astronomy_picture_of_day |
| 5 | pass | - | 9404.27 | 581.09 | 0.47 | 1095.27 | 7153.49 | get_astronomy_picture_of_day |
| 6 | pass | - | 11962.64 | 585.13 | 0.63 | 1628.63 | 9244.42 | get_astronomy_picture_of_day |
| 7 | fail | interface_test | 32303.44 | 626.99 | 0.60 | 1097.69 | - | - |
| 8 | fail | interface_test | 32306.41 | 618.79 | 0.68 | 1099.23 | - | - |
| 9 | pass | - | 5963.32 | 586.03 | 0.56 | 1097.42 | 3708.06 | get_astronomy_picture_of_day |
| 10 | pass | - | 6598.57 | 617.54 | 0.53 | 1103.22 | 4378.56 | get_astronomy_picture_of_day |

## National Parks

- Container: laplace-national-parks
- Image: laplace/national-parks:local
- URL: http://localhost:8816/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 614.64 | 576.28 | 688.01 | 10 |
| wait_tcp_ms | 0.65 | 0.54 | 1.06 | 10 |
| mcp_handshake_ms | 574.84 | 569.46 | 582.87 | 10 |
| interface_test_ms | 1397.51 | 1191.77 | 2007.67 | 10 |
| total_ms | 3118.74 | 2870.46 | 3766.24 | 10 |
| tcp_ready_elapsed_ms | 635.33 | 596.25 | 711.64 | 10 |
| handshake_elapsed_ms | 1210.17 | 1165.70 | 1289.10 | 10 |
| interface_test_elapsed_ms | 2607.68 | 2368.64 | 3215.92 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3766.24 | 611.63 | 0.62 | 577.89 | 2007.67 | findParks |
| 2 | pass | - | 3223.10 | 688.01 | 0.60 | 577.46 | 1390.10 | findParks |
| 3 | pass | - | 3189.29 | 656.43 | 0.66 | 582.87 | 1370.67 | findParks |
| 4 | pass | - | 3041.28 | 642.70 | 0.54 | 575.85 | 1317.96 | findParks |
| 5 | pass | - | 3094.94 | 587.35 | 0.65 | 576.35 | 1408.27 | findParks |
| 6 | pass | - | 2941.79 | 576.28 | 0.61 | 569.46 | 1317.27 | findParks |
| 7 | pass | - | 3059.12 | 595.72 | 1.06 | 570.35 | 1368.40 | findParks |
| 8 | pass | - | 2887.74 | 585.40 | 0.60 | 573.91 | 1194.09 | findParks |
| 9 | pass | - | 2870.46 | 587.00 | 0.61 | 570.27 | 1191.77 | findParks |
| 10 | pass | - | 3113.46 | 615.85 | 0.59 | 573.98 | 1408.91 | findParks |

## NixOS

- Container: laplace-nixos
- Image: laplace/nixos:local
- URL: http://localhost:8817/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 602.55 | 578.02 | 629.96 | 10 |
| wait_tcp_ms | 0.68 | 0.58 | 1.09 | 10 |
| mcp_handshake_ms | 1147.24 | 1087.78 | 1633.81 | 10 |
| interface_test_ms | 13819.31 | 13057.12 | 17206.73 | 10 |
| total_ms | 16100.21 | 15289.04 | 20012.00 | 10 |
| tcp_ready_elapsed_ms | 623.41 | 598.61 | 652.11 | 10 |
| handshake_elapsed_ms | 1770.65 | 1695.89 | 2282.22 | 10 |
| interface_test_elapsed_ms | 15589.96 | 14753.20 | 19488.95 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 20012.00 | 628.88 | 0.58 | 1633.81 | 17206.73 | nixos_channels |
| 2 | pass | - | 15552.58 | 583.75 | 0.68 | 1088.84 | 13365.80 | nixos_channels |
| 3 | pass | - | 15388.79 | 600.96 | 0.67 | 1089.35 | 13177.54 | nixos_channels |
| 4 | pass | - | 15568.31 | 629.96 | 0.62 | 1100.33 | 13311.22 | nixos_channels |
| 5 | pass | - | 15289.04 | 582.32 | 0.61 | 1091.96 | 13057.12 | nixos_channels |
| 6 | pass | - | 15428.23 | 598.35 | 0.61 | 1091.87 | 13241.69 | nixos_channels |
| 7 | pass | - | 15379.37 | 578.02 | 1.09 | 1104.82 | 13125.73 | nixos_channels |
| 8 | pass | - | 16406.15 | 601.67 | 0.58 | 1087.78 | 14217.46 | nixos_channels |
| 9 | pass | - | 15488.49 | 621.84 | 0.67 | 1092.51 | 13283.14 | nixos_channels |
| 10 | pass | - | 16489.18 | 599.70 | 0.74 | 1091.11 | 14206.67 | nixos_channels |

## OKX Exchange

- Container: laplace-okx-exchange
- Image: laplace/okx-exchange:local
- URL: http://localhost:8818/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 580.61 | 556.41 | 603.92 | 10 |
| wait_tcp_ms | 0.73 | 0.61 | 0.99 | 10 |
| mcp_handshake_ms | 569.59 | 567.25 | 574.92 | 10 |
| interface_test_ms | 73.58 | 68.59 | 91.29 | 10 |
| total_ms | 1754.76 | 1724.61 | 1781.65 | 10 |
| tcp_ready_elapsed_ms | 602.01 | 577.18 | 623.74 | 10 |
| handshake_elapsed_ms | 1171.60 | 1147.32 | 1196.58 | 10 |
| interface_test_elapsed_ms | 1245.18 | 1220.25 | 1268.89 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 1752.25 | 594.87 | 0.63 | 574.92 | 72.30 | health_check |
| 2 | pass | - | 1754.34 | 586.04 | 0.87 | 570.33 | 76.12 | health_check |
| 3 | pass | - | 1773.61 | 587.66 | 0.69 | 568.30 | 68.59 | health_check |
| 4 | pass | - | 1741.11 | 567.49 | 0.68 | 568.15 | 91.29 | health_check |
| 5 | pass | - | 1764.68 | 584.81 | 0.85 | 567.63 | 71.50 | health_check |
| 6 | pass | - | 1781.65 | 571.23 | 0.75 | 567.25 | 72.75 | health_check |
| 7 | pass | - | 1766.36 | 577.18 | 0.61 | 567.26 | 69.70 | health_check |
| 8 | pass | - | 1737.01 | 603.92 | 0.63 | 567.31 | 68.72 | health_check |
| 9 | pass | - | 1752.02 | 576.46 | 0.99 | 574.63 | 71.88 | health_check |
| 10 | pass | - | 1724.61 | 556.41 | 0.63 | 570.14 | 72.93 | health_check |

## OpenAPI Explorer

- Container: laplace-openapi-explorer
- Image: laplace/openapi-explorer:local
- URL: http://localhost:8819/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 598.99 | 576.29 | 622.87 | 10 |
| wait_tcp_ms | 0.70 | 0.57 | 1.17 | 10 |
| mcp_handshake_ms | 954.73 | 758.03 | 1478.65 | 10 |
| interface_test_ms | 763.81 | 449.11 | 1390.70 | 10 |
| total_ms | 2827.01 | 2428.67 | 3935.60 | 10 |
| tcp_ready_elapsed_ms | 620.76 | 597.16 | 645.37 | 10 |
| handshake_elapsed_ms | 1575.48 | 1395.23 | 2099.02 | 10 |
| interface_test_elapsed_ms | 2339.30 | 1921.39 | 3489.72 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3935.60 | 599.09 | 0.58 | 1478.65 | 1390.70 | getApiOverview |
| 2 | pass | - | 2677.45 | 590.22 | 0.60 | 1034.06 | 561.61 | getApiOverview |
| 3 | pass | - | 2718.57 | 591.65 | 0.75 | 895.64 | 715.40 | getApiOverview |
| 4 | pass | - | 2914.23 | 613.69 | 0.65 | 1026.40 | 785.37 | getApiOverview |
| 5 | pass | - | 2560.27 | 608.49 | 0.77 | 909.44 | 553.49 | getApiOverview |
| 6 | pass | - | 2428.67 | 594.26 | 0.65 | 856.10 | 449.11 | getApiOverview |
| 7 | pass | - | 2498.20 | 622.87 | 0.57 | 758.03 | 574.72 | getApiOverview |
| 8 | pass | - | 3147.92 | 591.60 | 1.17 | 781.39 | 1271.70 | getApiOverview |
| 9 | pass | - | 2836.19 | 601.72 | 0.63 | 900.29 | 826.37 | getApiOverview |
| 10 | pass | - | 2552.97 | 576.29 | 0.61 | 907.28 | 509.68 | getApiOverview |

## OSINT Intelligence

- Container: laplace-osint-intelligence
- Image: laplace/osint-intelligence:local
- URL: http://localhost:8820/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 594.67 | 580.70 | 614.05 | 10 |
| wait_tcp_ms | 0.62 | 0.54 | 0.71 | 10 |
| mcp_handshake_ms | 1146.11 | 1087.58 | 1621.32 | 10 |
| interface_test_ms | 78.63 | 73.43 | 86.52 | 10 |
| total_ms | 2336.66 | 2249.04 | 2831.33 | 10 |
| tcp_ready_elapsed_ms | 615.09 | 600.77 | 635.52 | 10 |
| handshake_elapsed_ms | 1761.20 | 1695.06 | 2241.67 | 10 |
| interface_test_elapsed_ms | 1839.84 | 1772.35 | 2324.79 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 2831.33 | 601.41 | 0.58 | 1621.32 | 83.13 | whois_lookup |
| 2 | pass | - | 2285.12 | 580.70 | 0.54 | 1094.30 | 77.28 | whois_lookup |
| 3 | pass | - | 2284.05 | 589.37 | 0.69 | 1089.60 | 86.52 | whois_lookup |
| 4 | pass | - | 2288.91 | 588.71 | 0.54 | 1095.55 | 75.80 | whois_lookup |
| 5 | pass | - | 2266.60 | 600.05 | 0.61 | 1090.67 | 76.52 | whois_lookup |
| 6 | pass | - | 2308.38 | 614.05 | 0.68 | 1099.75 | 75.34 | whois_lookup |
| 7 | pass | - | 2305.87 | 602.01 | 0.71 | 1099.52 | 79.08 | whois_lookup |
| 8 | pass | - | 2249.04 | 588.51 | 0.62 | 1093.34 | 76.06 | whois_lookup |
| 9 | pass | - | 2265.92 | 597.17 | 0.61 | 1087.58 | 73.43 | whois_lookup |
| 10 | pass | - | 2281.35 | 584.72 | 0.58 | 1089.51 | 83.16 | whois_lookup |

## Paper Search

- Container: laplace-paper-search
- Image: laplace/paper-search:local
- URL: http://localhost:8831/mcp
- Success / Partial / Fail: 6 / 0 / 4
- Failure stages: {"interface_test": 4}

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 610.81 | 579.12 | 643.04 | 10 |
| wait_tcp_ms | 0.70 | 0.55 | 1.44 | 10 |
| mcp_handshake_ms | 1686.95 | 1624.33 | 2161.34 | 10 |
| interface_test_ms | 6036.42 | 823.30 | 16511.11 | 6 |
| total_ms | 23547.99 | 3650.94 | 62857.75 | 10 |
| tcp_ready_elapsed_ms | 634.86 | 601.59 | 668.58 | 10 |
| handshake_elapsed_ms | 2321.81 | 2226.80 | 2778.45 | 10 |
| interface_test_elapsed_ms | 8391.22 | 3112.45 | 19015.12 | 6 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 19556.49 | 598.09 | 0.76 | 2161.34 | 16236.67 | search_arxiv |
| 2 | pass | - | 3665.41 | 632.13 | 0.74 | 1627.83 | 823.30 | search_arxiv |
| 3 | fail | interface_test | 62857.75 | 609.54 | 0.63 | 1635.55 | - | - |
| 4 | pass | - | 3669.61 | 604.00 | 0.55 | 1662.42 | 865.60 | search_arxiv |
| 5 | fail | interface_test | 34717.80 | 579.12 | 0.61 | 1625.21 | - | - |
| 6 | fail | interface_test | 50059.23 | 623.41 | 0.56 | 1638.29 | - | - |
| 7 | pass | - | 3650.94 | 612.09 | 0.56 | 1629.41 | 849.64 | search_arxiv |
| 8 | fail | interface_test | 34300.46 | 643.04 | 1.44 | 1640.61 | - | - |
| 9 | pass | - | 3685.58 | 583.99 | 0.63 | 1624.49 | 932.21 | search_arxiv |
| 10 | pass | - | 19316.64 | 622.71 | 0.57 | 1624.33 | 16511.11 | search_arxiv |

## Reddit

- Container: laplace-reddit
- Image: laplace/reddit:local
- URL: http://localhost:8822/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 606.92 | 579.30 | 640.85 | 10 |
| wait_tcp_ms | 0.73 | 0.60 | 1.00 | 10 |
| mcp_handshake_ms | 1202.58 | 1090.15 | 2146.42 | 10 |
| interface_test_ms | 1150.94 | 1113.37 | 1185.80 | 10 |
| total_ms | 3518.14 | 3337.99 | 4459.78 | 10 |
| tcp_ready_elapsed_ms | 631.19 | 599.25 | 665.40 | 10 |
| handshake_elapsed_ms | 1833.77 | 1692.40 | 2753.02 | 10 |
| interface_test_elapsed_ms | 2984.71 | 2830.71 | 3926.95 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 4459.78 | 585.47 | 0.67 | 2146.42 | 1173.93 | fetch_reddit_hot_threads |
| 2 | pass | - | 3395.25 | 579.30 | 1.00 | 1093.15 | 1148.18 | fetch_reddit_hot_threads |
| 3 | pass | - | 3421.30 | 640.85 | 0.72 | 1090.15 | 1136.56 | fetch_reddit_hot_threads |
| 4 | pass | - | 3420.36 | 599.27 | 0.60 | 1110.16 | 1179.65 | fetch_reddit_hot_threads |
| 5 | pass | - | 3433.45 | 616.45 | 0.64 | 1096.64 | 1148.74 | fetch_reddit_hot_threads |
| 6 | pass | - | 3385.70 | 603.09 | 0.78 | 1095.09 | 1145.46 | fetch_reddit_hot_threads |
| 7 | pass | - | 3452.07 | 618.96 | 0.70 | 1100.15 | 1145.26 | fetch_reddit_hot_threads |
| 8 | pass | - | 3429.95 | 624.05 | 0.71 | 1101.74 | 1132.45 | fetch_reddit_hot_threads |
| 9 | pass | - | 3445.59 | 605.91 | 0.81 | 1094.66 | 1185.80 | fetch_reddit_hot_threads |
| 10 | pass | - | 3337.99 | 595.87 | 0.68 | 1097.62 | 1113.37 | fetch_reddit_hot_threads |

## Scientific Computing

- Container: laplace-scientific-computing
- Image: laplace/scientific-computing:local
- URL: http://localhost:8823/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 612.42 | 586.04 | 638.12 | 10 |
| wait_tcp_ms | 0.62 | 0.52 | 0.72 | 10 |
| mcp_handshake_ms | 2595.96 | 1627.91 | 3823.72 | 10 |
| interface_test_ms | 100.62 | 94.61 | 116.33 | 10 |
| total_ms | 3849.20 | 2900.15 | 5028.42 | 10 |
| tcp_ready_elapsed_ms | 634.68 | 605.77 | 665.77 | 10 |
| handshake_elapsed_ms | 3230.63 | 2261.89 | 4448.66 | 10 |
| interface_test_elapsed_ms | 3331.26 | 2358.97 | 4547.19 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 4470.00 | 611.36 | 0.58 | 3223.13 | 116.11 | view_tensor |
| 2 | pass | - | 3397.97 | 597.15 | 0.70 | 2163.48 | 97.13 | view_tensor |
| 3 | pass | - | 3398.23 | 611.95 | 0.60 | 2158.89 | 95.98 | view_tensor |
| 4 | pass | - | 3456.96 | 630.07 | 0.72 | 2185.36 | 97.88 | view_tensor |
| 5 | pass | - | 2931.89 | 638.12 | 0.64 | 1627.91 | 94.61 | view_tensor |
| 6 | pass | - | 2900.15 | 586.04 | 0.60 | 1656.11 | 97.09 | view_tensor |
| 7 | pass | - | 2920.40 | 612.16 | 0.68 | 1634.46 | 116.33 | view_tensor |
| 8 | pass | - | 4993.59 | 620.45 | 0.62 | 3739.54 | 96.01 | view_tensor |
| 9 | pass | - | 5028.42 | 604.95 | 0.60 | 3823.72 | 98.52 | view_tensor |
| 10 | pass | - | 4994.39 | 611.95 | 0.52 | 3746.95 | 96.55 | view_tensor |

## Time MCP

- Container: laplace-time-mcp
- Image: laplace/time-mcp:local
- URL: http://localhost:8824/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 616.48 | 589.22 | 630.05 | 10 |
| wait_tcp_ms | 0.74 | 0.54 | 1.20 | 10 |
| mcp_handshake_ms | 1733.70 | 1093.93 | 3770.32 | 10 |
| interface_test_ms | 137.53 | 130.11 | 144.98 | 10 |
| total_ms | 3029.28 | 2376.21 | 5087.05 | 10 |
| tcp_ready_elapsed_ms | 642.02 | 617.70 | 654.09 | 10 |
| handshake_elapsed_ms | 2375.73 | 1742.17 | 4389.13 | 10 |
| interface_test_elapsed_ms | 2513.25 | 1875.84 | 4534.11 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 5087.05 | 599.49 | 0.64 | 3770.32 | 144.98 | get_current_time |
| 2 | pass | - | 2915.18 | 624.34 | 0.54 | 1625.46 | 140.51 | get_current_time |
| 3 | pass | - | 2376.21 | 629.48 | 0.74 | 1096.10 | 130.11 | get_current_time |
| 4 | pass | - | 2903.30 | 615.53 | 0.74 | 1620.79 | 142.90 | get_current_time |
| 5 | pass | - | 2899.47 | 619.39 | 0.57 | 1625.59 | 132.04 | get_current_time |
| 6 | pass | - | 2422.71 | 618.79 | 1.20 | 1093.93 | 134.91 | get_current_time |
| 7 | pass | - | 3447.07 | 589.22 | 1.05 | 2145.61 | 143.73 | get_current_time |
| 8 | pass | - | 2412.96 | 630.05 | 0.54 | 1115.80 | 134.86 | get_current_time |
| 9 | pass | - | 2944.72 | 613.29 | 0.62 | 1622.99 | 139.55 | get_current_time |
| 10 | pass | - | 2884.17 | 625.22 | 0.81 | 1620.45 | 131.68 | get_current_time |

## Unit Converter

- Container: laplace-unit-converter
- Image: laplace/unit-converter:local
- URL: http://localhost:8825/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 615.33 | 579.19 | 678.36 | 10 |
| wait_tcp_ms | 0.70 | 0.62 | 0.90 | 10 |
| mcp_handshake_ms | 1204.14 | 1094.50 | 2153.04 | 10 |
| interface_test_ms | 82.80 | 73.24 | 93.43 | 10 |
| total_ms | 2469.59 | 2273.57 | 3412.69 | 10 |
| tcp_ready_elapsed_ms | 642.97 | 608.24 | 708.69 | 10 |
| handshake_elapsed_ms | 1847.11 | 1705.24 | 2794.29 | 10 |
| interface_test_elapsed_ms | 1929.91 | 1788.51 | 2887.72 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3412.69 | 617.38 | 0.69 | 2153.04 | 93.43 | list_supported_units |
| 2 | pass | - | 2357.16 | 632.95 | 0.63 | 1109.55 | 78.27 | list_supported_units |
| 3 | pass | - | 2297.05 | 588.69 | 0.84 | 1096.49 | 78.85 | list_supported_units |
| 4 | pass | - | 2273.57 | 579.19 | 0.65 | 1097.00 | 83.27 | list_supported_units |
| 5 | pass | - | 2282.70 | 609.59 | 0.63 | 1096.46 | 78.33 | list_supported_units |
| 6 | pass | - | 2421.53 | 615.42 | 0.62 | 1096.49 | 84.04 | list_supported_units |
| 7 | pass | - | 2375.82 | 584.19 | 0.66 | 1101.36 | 86.06 | list_supported_units |
| 8 | pass | - | 2393.03 | 614.68 | 0.67 | 1094.50 | 73.24 | list_supported_units |
| 9 | pass | - | 2387.66 | 632.84 | 0.90 | 1095.53 | 84.72 | list_supported_units |
| 10 | pass | - | 2494.70 | 678.36 | 0.67 | 1100.93 | 87.82 | list_supported_units |

## Weather Data

- Container: laplace-weather-data
- Image: laplace/weather-data:local
- URL: http://localhost:8826/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 630.24 | 605.49 | 690.77 | 10 |
| wait_tcp_ms | 0.86 | 0.52 | 2.03 | 10 |
| mcp_handshake_ms | 1202.18 | 1093.04 | 2150.57 | 10 |
| interface_test_ms | 424.88 | 390.85 | 465.82 | 10 |
| total_ms | 2818.11 | 2675.34 | 3878.62 | 10 |
| tcp_ready_elapsed_ms | 658.09 | 633.39 | 719.43 | 10 |
| handshake_elapsed_ms | 1860.27 | 1727.15 | 2870.00 | 10 |
| interface_test_elapsed_ms | 2285.16 | 2132.58 | 3335.82 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3878.62 | 690.77 | 0.65 | 2150.57 | 465.82 | get_current_weather_tool |
| 2 | pass | - | 2752.38 | 623.38 | 0.70 | 1095.23 | 454.44 | get_current_weather_tool |
| 3 | pass | - | 2688.23 | 619.38 | 0.58 | 1093.36 | 416.62 | get_current_weather_tool |
| 4 | pass | - | 2698.42 | 606.51 | 0.69 | 1105.94 | 455.85 | get_current_weather_tool |
| 5 | pass | - | 2712.21 | 647.25 | 0.65 | 1095.60 | 409.42 | get_current_weather_tool |
| 6 | pass | - | 2675.34 | 618.23 | 0.52 | 1094.84 | 423.82 | get_current_weather_tool |
| 7 | pass | - | 2682.39 | 623.57 | 1.26 | 1105.00 | 425.30 | get_current_weather_tool |
| 8 | pass | - | 2675.44 | 615.24 | 2.03 | 1094.99 | 401.24 | get_current_weather_tool |
| 9 | pass | - | 2709.29 | 652.54 | 0.61 | 1093.04 | 390.85 | get_current_weather_tool |
| 10 | pass | - | 2708.77 | 605.49 | 0.89 | 1093.22 | 405.44 | get_current_weather_tool |

## Wikipedia

- Container: laplace-wikipedia
- Image: laplace/wikipedia:local
- URL: http://localhost:8827/mcp
- Success / Partial / Fail: 10 / 0 / 0

### Metric Stats

| Metric | Avg (ms) | Min (ms) | Max (ms) | Samples |
| --- | ---: | ---: | ---: | ---: |
| docker_run_ms | 619.84 | 588.42 | 643.88 | 10 |
| wait_tcp_ms | 0.69 | 0.54 | 1.13 | 10 |
| mcp_handshake_ms | 1151.32 | 1091.12 | 1620.34 | 10 |
| interface_test_ms | 433.06 | 316.43 | 1342.93 | 10 |
| total_ms | 2747.69 | 2536.28 | 3630.41 | 10 |
| tcp_ready_elapsed_ms | 648.81 | 615.83 | 672.27 | 10 |
| handshake_elapsed_ms | 1800.13 | 1728.77 | 2259.59 | 10 |
| interface_test_elapsed_ms | 2233.19 | 2050.54 | 3121.56 | 10 |

### Trial Results

| Trial | Status | Failure Stage | Total (ms) | Launch (ms) | Port Wait (ms) | Handshake (ms) | Interface (ms) | Smoke Tool |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | pass | - | 3144.10 | 616.22 | 0.69 | 1620.34 | 349.92 | search_wikipedia |
| 2 | pass | - | 2603.87 | 615.94 | 0.54 | 1092.42 | 327.86 | search_wikipedia |
| 3 | pass | - | 2621.79 | 638.80 | 0.56 | 1093.79 | 337.82 | search_wikipedia |
| 4 | pass | - | 2566.02 | 618.53 | 0.61 | 1095.09 | 316.43 | search_wikipedia |
| 5 | pass | - | 2545.10 | 588.42 | 0.57 | 1114.46 | 331.55 | search_wikipedia |
| 6 | pass | - | 2594.86 | 620.59 | 1.13 | 1096.12 | 327.28 | search_wikipedia |
| 7 | pass | - | 3630.41 | 643.88 | 0.74 | 1106.36 | 1342.93 | search_wikipedia |
| 8 | pass | - | 2636.89 | 633.07 | 0.75 | 1095.68 | 336.70 | search_wikipedia |
| 9 | pass | - | 2597.61 | 612.12 | 0.71 | 1107.89 | 338.29 | search_wikipedia |
| 10 | pass | - | 2536.28 | 610.86 | 0.60 | 1091.12 | 321.77 | search_wikipedia |
