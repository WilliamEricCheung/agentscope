# FastText Semantic Router (MCP-Bench Dataset)

说明：FastText 仍保留为历史分类基线，但当前更推荐优先使用 [README_retrieval_router.md](README_retrieval_router.md) 里的 retrieval baseline。

目标：训练一个统一 FastText 路由模型（单个 `.bin`），并通过阈值 + Top-K 网格搜索得到部署参数。

当前实现约定：
- FastText 训练只做 `single-only`
- 当前训练数据使用 `mcpbench_tasks_single_runner_format.json` 和 `laplace_tasks_single_runner_format.json`
- 训练与部署默认使用 `text_mode=both`

## 1. 安装依赖

```bash
pip install fasttext
```

## 2. 训练统一模型（部署主流程）

```bash
cd laplace/mcpbench_dataset/router_model
python train_fasttext_semantic_router.py \
  --datasets mcpbench_tasks_single_runner_format.json,laplace_tasks_single_runner_format.json \
  --output-dir artifacts_fasttext_router_deploy \
  --text-mode both \
  --train-ratio 0.8 \
  --epoch 60 \
  --lr 0.5 \
  --word-ngrams 2 \
  --dim 100
```

主要产物：
- `artifacts_fasttext_router_deploy/semantic_router_fasttext.bin`
- `artifacts_fasttext_router_deploy/metadata.json`
- `artifacts_fasttext_router_deploy/eval_samples.jsonl`

注意：
- 训练脚本现在会在加载阶段校验数据集是否为单技能标注
- 如果误传 `multi_2` 或 `multi_3` 数据集，会直接报错而不是继续训练

## 3. 部署参数搜索（阈值 + Top-K）

```bash
python grid_search_threshold_topk.py \
  --artifact-dir artifacts_fasttext_router_deploy \
  --thresholds 0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40,0.45,0.50,0.55,0.60 \
  --topk-list 1,2,3 \
  --objective composite_score \
  --composite-weight-f1 1.0 \
  --composite-weight-distraction 0.3 \
  --ensure-non-empty
```

结果：
- `artifacts_fasttext_router_deploy/grid_search_results.json`

综合分定义：

`composite_score = w_f1 * micro_f1 - w_distraction * distraction_fp_rate`

其中：
- `distraction_fp_rate = distraction_false_positive_count / samples`
- `w_f1` 对应 `--composite-weight-f1`
- `w_distraction` 对应 `--composite-weight-distraction`

## 4. 生产候选参数（当前一次实验结果）

在 `text_mode=both, epoch=60` 的一次搜索中：
- Balanced（`w_distraction=0.3`）最优：`threshold=0.05, top_k=2`
- 稳定优先（`w_distraction=0.8`）最优：`threshold=0.05, top_k=1`

建议：
- 追求召回：优先试 `top_k=2`
- 追求稳定：优先试 `top_k=1`
