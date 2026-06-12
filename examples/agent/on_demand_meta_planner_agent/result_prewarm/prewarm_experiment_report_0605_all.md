# MCP Prewarm Experiment Side-by-Side Report

> Source dataset: `/mnt/d/Project/agentscope/laplace/mcp_dataset/laplace_tasks_single_runner_format.json`
>
> These three runs use the same sampled task set and differ only in `keyword_min_matches_per_client`:
> - `prewarm_experiment_results_0605_k1_0.jsonl`: min matches = `1`
> - `prewarm_experiment_results_0605_k2_0.jsonl`: min matches = `2`
> - `prewarm_experiment_results_0605_k3_0.jsonl`: min matches = `3`
>
> The sampled tasks, mode definitions, and trial isolation policy are the same as the per-run reports.
>
> Read this report as a threshold comparison, not as a new experiment run.

## Bottom Line

- `min matches = 1` is the most permissive setting, but it also produces the weakest hybrid fallback behavior and the largest tail risk.
- `min matches = 2` is the most balanced setting if you want keyword routing to stay active while still allowing some semantic fallback.
- `min matches = 3` is the most stable setting overall for hybrid routing in these runs: it preserves the same non-cold wait profile while eliminating route mismatches in the hybrid path.

## Side-by-Side Summary

| Metric | min matches = 1 | min matches = 2 | min matches = 3 |
| --- | --- | --- | --- |
| Source report | `0605_k1_0` | `0605_k2_0` | `0605_k3_0` |
| Keyword target match rate | 95.0% | 90.0% | 80.0% |
| Keyword target match runs | 95 | 90 | 80 |
| Keyword route mismatch runs | 5 | 10 | 20 |
| Keyword effective prewarm runs | 94 | 90 | 80 |
| Keyword effectiveness rate | 98.9% | 100.0% | 100.0% |
| Keyword effective route breakdown | L1:94 | L1:90 | L1:80 |
| Keyword avg wait all (ms) | 786.619 | 323.021 | 621.812 |
| Keyword avg wait non-cold (ms) | 126.730 | 126.819 | 127.163 |
| Keyword avg wait cold (ms) | 11124.872 | 2088.840 | 2600.406 |
| Keyword avg wait route mismatch (ms) | 2302.439 | 2088.840 | 2600.406 |
| Keyword max wait (ms) | 55237.038 | 2878.706 | 3931.656 |
| Keyword activation startup modes | cold:6, running:94 | cold:10, running:90 | cold:20, running:80 |
| Semantic target match rate | 100.0% | 100.0% | 100.0% |
| Semantic effectiveness rate | 100.0% | 100.0% | 100.0% |
| Semantic avg wait all (ms) | 129.963 | 131.594 | 135.698 |
| Semantic avg wait non-cold (ms) | 129.963 | 131.594 | 135.698 |
| Semantic max wait (ms) | 235.122 | 244.818 | 521.677 |
| Hybrid target match rate | 95.0% | 95.0% | 100.0% |
| Hybrid target match runs | 95 | 95 | 100 |
| Hybrid route mismatch runs | 5 | 5 | 0 |
| Hybrid effective prewarm runs | 95 | 95 | 100 |
| Hybrid effectiveness rate | 100.0% | 100.0% | 100.0% |
| Hybrid effective route breakdown | L1:95 | L1:90, L2:5 | L1:80, L2:20 |
| Hybrid avg wait all (ms) | 269.137 | 225.552 | 133.887 |
| Hybrid avg wait non-cold (ms) | 126.218 | 131.783 | 133.887 |
| Hybrid avg wait cold (ms) | 2984.583 | 2007.167 | - |
| Hybrid avg wait route mismatch (ms) | 2984.583 | 2007.167 | - |
| Hybrid max wait (ms) | 4091.626 | 2884.165 | 306.083 |
| Hybrid activation startup modes | cold:5, running:95 | cold:5, running:95 | running:100 |
| No-prewarm avg wait all (ms) | 2423.532 | 2164.210 | 2409.128 |
| No-prewarm max wait (ms) | 5010.441 | 2948.956 | 5050.577 |

## What Changed Across Thresholds

### 1. Keyword routing becomes stricter as expected

The keyword path gets narrower as `min matches` increases:

- `1`: 95 target matches, 5 mismatches
- `2`: 90 target matches, 10 mismatches
- `3`: 80 target matches, 20 mismatches

That is the expected tradeoff. The threshold does not improve raw keyword coverage; it intentionally reduces how often L1 is allowed to claim a match.

### 2. Hybrid behavior improves most at `min matches = 3`

Hybrid is the important comparison here because it reflects the L1-first, L2-fallback design:

- `1`: Hybrid still has 5 route mismatches and retains a few cold-path outliers.
- `2`: Hybrid still has 5 route mismatches, but the tail gets smaller than `1`.
- `3`: Hybrid reaches 100% target match and removes route mismatches entirely in this sample.

For these runs, `3` is the best choice if the goal is to keep hybrid predictable and avoid bad tail behavior.

### 3. Non-cold latency is already stable

Across all three runs, the non-cold wait is clustered tightly around roughly 126-134 ms for keyword, semantic, and hybrid modes. The real difference is not the average non-cold case; it is whether the run stays on the correct path and avoids cold or mismatch-driven outliers.

### 4. Semantic is the most stable baseline

Semantic routing is consistently high-quality across all three reports:

- 100% target match rate
- 100% effectiveness rate
- Stable wait distribution

If you want the safest baseline, semantic remains the cleanest option. The threshold question mainly matters for hybrid, not semantic.

## Recommendation

- Use `min matches = 3` when you want the safest hybrid rollout and the smallest tail risk.
- Use `min matches = 2` only if you want a more permissive keyword gate and are willing to accept a little more mismatch exposure.
- Keep `min matches = 1` only as an exploratory setting; it is too permissive for the hybrid path in this sample.

## Source Artifacts

- `prewarm_experiment_results_0605_k1_0.jsonl`
- `prewarm_experiment_results_0605_k2_0.jsonl`
- `prewarm_experiment_results_0605_k3_0.jsonl`
- `prewarm_experiment_report_0605_k1_0.md`
- `prewarm_experiment_report_0605_k2_0.md`
- `prewarm_experiment_report_0605_k3_0.md`
