# Encoder Semantic Router (MCP-Bench Dataset)

目标：使用一个小型 sentence-transformers 语义编码器作为 single-skill router 基线，并和当前 TF-IDF 检索基线做直接对比。

当前实现约定：
- encoder 基线只做 `single-only`
- 当前训练数据使用 `mcpbench_tasks_single_runner_format.json` 和 `laplace_tasks_single_runner_format.json`
- 训练与部署默认使用 `text_mode=both`
- 默认初始化模型是 `sentence-transformers/all-MiniLM-L6-v2`
- 推理阶段仍然使用 server prototype cosine retrieval，保证和 TF-IDF baseline 评估接口一致

## 1. 安装依赖

```bash
cd laplace/mcpbench_dataset/router_model
uv pip install -r requirements.txt
```

## 2. 训练统一模型（部署主流程）

```bash
python train_encoder_semantic_router.py \
  --datasets mcpbench_tasks_single_runner_format.json,laplace_tasks_single_runner_format.json \
  --output-dir artifacts_encoder_router_deploy \
  --text-mode both \
  --train-ratio 0.8 \
  --model-name sentence-transformers/all-MiniLM-L6-v2 \
  --epochs 2 \
  --batch-size 16 \
  --learning-rate 2e-5
```

主要产物：
- `artifacts_encoder_router_deploy/semantic_router_encoder_model/`
- `artifacts_encoder_router_deploy/semantic_router_encoder_prototypes.npz`
- `artifacts_encoder_router_deploy/metadata.json`
- `artifacts_encoder_router_deploy/eval_samples.jsonl`

## 3. 部署参数搜索（阈值 + Top-K）

```bash
python grid_search_encoder_topk.py \
  --artifact-dir artifacts_encoder_router_deploy \
  --thresholds 0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40 \
  --topk-list 1,2,3 \
  --objective composite_score \
  --composite-weight-f1 1.0 \
  --composite-weight-distraction 0.3 \
  --ensure-non-empty
```

结果：
- `artifacts_encoder_router_deploy/grid_search_results.json`

## 4. 说明

- 训练阶段会用同 server 的 query 对构造正样本，不同 server 的 query 对构造负样本，对 encoder 做轻量监督微调
- 推理阶段不会走分类头，而是把 train embedding 聚合成每个 server 的 prototype，再用 cosine similarity 做检索
- 这样可以和当前 TF-IDF 检索基线保持同样的部署形状，便于做公平对比