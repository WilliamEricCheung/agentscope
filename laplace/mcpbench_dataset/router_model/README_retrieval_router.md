# Retrieval Semantic Router (MCP-Bench Dataset)

目标：使用零新增重依赖的 TF-IDF 检索式基线训练 single-skill MCP router，并通过阈值 + Top-K 网格搜索得到部署参数。

当前实现约定：
- 检索基线只做 `single-only`
- 当前训练数据使用 `mcpbench_tasks_single_runner_format.json` 和 `laplace_tasks_single_runner_format.json`
- 训练与部署默认使用 `text_mode=both`
- 当前推荐优先尝试 retrieval baseline，再把 FastText 当作历史对照

## 1. 训练统一模型（部署主流程）

```bash
cd laplace/mcpbench_dataset/router_model
python train_retrieval_semantic_router.py \
  --datasets mcpbench_tasks_single_runner_format.json,laplace_tasks_single_runner_format.json \
  --output-dir artifacts_retrieval_router_deploy \
  --text-mode both \
  --train-ratio 0.8 \
  --max-features 20000 \
  --char-ngram-min 3 \
  --char-ngram-max 5 \
  --top-neighbors 16
```

主要产物：
- `artifacts_retrieval_router_deploy/semantic_router_retrieval.npz`
- `artifacts_retrieval_router_deploy/semantic_router_retrieval.json`
- `artifacts_retrieval_router_deploy/metadata.json`
- `artifacts_retrieval_router_deploy/eval_samples.jsonl`

注意：
- 训练脚本会在加载阶段校验数据集是否为单技能标注
- 如果误传 `multi_2` 或 `multi_3` 数据集，会直接报错而不是继续训练
- 如果你希望 query 至少返回一个候选，可以加 `--ensure-non-empty`

## 2. 部署参数搜索（阈值 + Top-K）

```bash
python grid_search_retrieval_topk.py \
  --artifact-dir artifacts_retrieval_router_deploy \
  --thresholds 0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40 \
  --topk-list 1,2,3 \
  --objective composite_score \
  --composite-weight-f1 1.0 \
  --composite-weight-distraction 0.3 \
  --ensure-non-empty
```

结果：
- `artifacts_retrieval_router_deploy/grid_search_results.json`

综合分定义：

`composite_score = w_f1 * micro_f1 - w_distraction * distraction_fp_rate`

其中：
- `distraction_fp_rate = distraction_false_positive_count / samples`
- `w_f1` 对应 `--composite-weight-f1`
- `w_distraction` 对应 `--composite-weight-distraction`

## 3. 当前建议

- 默认保持 `text_mode=both`
- 首先搜索 `top_k=1`
- 如果后续要接更强 encoder，可以保留当前检索流程作为无外部依赖基线
