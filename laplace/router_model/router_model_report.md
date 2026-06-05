# Router Model Report

## Overview

- Compared models: fasttext, retrieval, encoder
- Datasets: /mnt/d/Project/agentscope/laplace/mcp_dataset/laplace_tasks_single_runner_format.json
- Eval split policy: grouped_by_server_similarity + exact_text_per_server
- Current winner by grid-search objective: retrieval

## Best Grid-Search Results

| Rank | Model | Router Family | Text Mode | Objective | Best Score | Micro F1 | Hit Rate | Precision | Recall | Threshold | Top-K | Avg Latency (ms) | Distraction FP | Artifact |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | retrieval | retrieval_tfidf | split_both | composite_score | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.050000 | 1 | 2.115544 | 0 | /mnt/d/Project/agentscope/laplace/router_model/artifacts_retrieval_router_deploy |
| 2 | encoder | encoder_sentence_transformer | split_both | composite_score | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.050000 | 1 | 7.822463 | 0 | /mnt/d/Project/agentscope/laplace/router_model/artifacts_encoder_router_deploy |
| 3 | fasttext | fasttext | split_both | composite_score | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.070000 | 1 | 0.171108 | 0 | /mnt/d/Project/agentscope/laplace/router_model/artifacts_fasttext_router_deploy |

## Inference Latency

| Model | Repeats | Query Source | Min Latency (ms) | Avg Latency (ms) | Max Latency (ms) |
| --- | --- | --- | --- | --- | --- |
| retrieval | 20 | /mnt/d/Project/agentscope/laplace/router_model/artifacts_retrieval_router_deploy/eval_samples.jsonl:bibliomantic_002__fuzzy | 0.939577 | 2.115544 | 5.451272 |
| encoder | 20 | /mnt/d/Project/agentscope/laplace/router_model/artifacts_retrieval_router_deploy/eval_samples.jsonl:bibliomantic_002__fuzzy | 3.154896 | 7.822463 | 9.686201 |
| fasttext | 20 | /mnt/d/Project/agentscope/laplace/router_model/artifacts_retrieval_router_deploy/eval_samples.jsonl:bibliomantic_002__fuzzy | 0.157791 | 0.171108 | 0.211037 |

## Training-Time Eval Snapshot

| Model | Eval Micro F1 | Eval Hit Rate | Eval Precision | Eval Recall | Eval Threshold | Eval Top-K |
| --- | --- | --- | --- | --- | --- | --- |
| retrieval | 0.970000 | 1.000000 | 0.941748 | 1.000000 | 0.350000 | 3 |
| encoder | 0.776000 | 1.000000 | 0.633987 | 1.000000 | 0.350000 | 3 |
| fasttext | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.350000 | 3 |

## Notes

- retrieval ranks first on `composite_score` with a margin of 0.000000 over encoder.
- FastText best `micro_f1` is 0.000000.
- FastText argmax baseline `micro_f1` is 0.030928 at top_k=1.
- Retrieval best `micro_f1` is 1.000000.
- Encoder best `micro_f1` is 1.000000.
- fasttext has the lowest average single-query latency at 0.171108 ms.
- This report compares each model at its own best grid-search operating point, not at one shared threshold/top-k.
