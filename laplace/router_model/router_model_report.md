# Router Model Report

## Overview

- Compared models: fasttext, retrieval, encoder
- Datasets: laplace_tasks_single_runner_format.json, mcpbench_tasks_single_runner_format.json
- Current winner by grid-search objective: encoder

## Best Grid-Search Results

| Rank | Model | Router Family | Text Mode | Objective | Best Score | Micro F1 | Hit Rate | Precision | Recall | Threshold | Top-K | Avg Latency (ms) | Distraction FP | Artifact |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | encoder | encoder_sentence_transformer | task | composite_score | 0.977273 | 0.977273 | 0.977273 | 0.977273 | 0.977273 | 0.050000 | 1 | 5.626751 | 0 | /mnt/d/Project/agentscope/laplace/router_model/artifacts_encoder_router_deploy |
| 2 | retrieval | retrieval_tfidf | task | composite_score | 0.970455 | 0.977273 | 0.977273 | 0.977273 | 0.977273 | 0.050000 | 1 | 1.230233 | 1 | /mnt/d/Project/agentscope/laplace/router_model/artifacts_retrieval_router_deploy |
| 3 | fasttext | fasttext | both | composite_score | -0.095455 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.050000 | 1 | 0.133352 | 14 | /mnt/d/Project/agentscope/laplace/router_model/artifacts_fasttext_router_deploy |

## Inference Latency

| Model | Repeats | Query Source | Min Latency (ms) | Avg Latency (ms) | Max Latency (ms) |
| --- | --- | --- | --- | --- | --- |
| encoder | 20 | artifacts_retrieval_router_deploy/eval_samples.jsonl:dex_paprika_000 | 2.767544 | 5.626751 | 16.121036 |
| retrieval | 20 | artifacts_retrieval_router_deploy/eval_samples.jsonl:dex_paprika_000 | 0.627934 | 1.230233 | 5.030044 |
| fasttext | 20 | artifacts_retrieval_router_deploy/eval_samples.jsonl:dex_paprika_000 | 0.111456 | 0.133352 | 0.169775 |

## Training-Time Eval Snapshot

| Model | Eval Micro F1 | Eval Hit Rate | Eval Precision | Eval Recall | Eval Threshold | Eval Top-K |
| --- | --- | --- | --- | --- | --- | --- |
| encoder | 0.888889 | 1.000000 | 0.800000 | 1.000000 | 0.350000 | 3 |
| retrieval | 0.988506 | 0.977273 | 1.000000 | 0.977273 | 0.350000 | 3 |
| fasttext | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.350000 | 3 |

## Notes

- encoder ranks first on `composite_score` with a margin of 0.006818 over retrieval.
- FastText best `micro_f1` is 0.000000.
- Retrieval best `micro_f1` is 0.977273.
- Encoder best `micro_f1` is 0.977273.
- fasttext has the lowest average single-query latency at 0.133352 ms.
- This report compares each model at its own best grid-search operating point, not at one shared threshold/top-k.
