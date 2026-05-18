# Router Model

这个目录用于 single-skill router 的训练、调参、延迟测试和效果对比。

配套数据集位于 `laplace/mcp_dataset`。

当前约定：

- 三个模型都只做 `single-only`
- 默认数据集为 `../mcp_dataset/mcpbench_tasks_single_runner_format.json` 和 `../mcp_dataset/laplace_tasks_single_runner_format.json`
- 默认训练文本使用 `text_mode=both`
- 推荐优先顺序：`retrieval` > `encoder` > `fasttext`

## 1. 目录说明

- `artifacts_*_router_deploy/`：模型产物和评估结果
- `train_*.py`：训练入口
- `grid_search_*.py`：阈值 / Top-K 搜索
- `benchmark_router_latency.py`：统一延迟测试
- `generate_router_model_report.py`：统一对比报告生成
- `router_model_report.md`：当前对比报告

## 2. 通用流程

```bash
cd laplace/router_model

# 训练
python train_retrieval_semantic_router.py

# 搜索部署参数
python grid_search_retrieval_topk.py

# 跑三模型延迟 benchmark
python benchmark_router_latency.py --repeats 20

# 生成统一报告
python generate_router_model_report.py
```

## 3. Retrieval Baseline

目标：使用零新增重依赖的 TF-IDF 检索式基线训练 router。

训练：

```bash
python train_retrieval_semantic_router.py \
	--datasets ../mcp_dataset/mcpbench_tasks_single_runner_format.json,../mcp_dataset/laplace_tasks_single_runner_format.json \
	--output-dir artifacts_retrieval_router_deploy \
	--text-mode both \
	--train-ratio 0.8 \
	--max-features 20000 \
	--char-ngram-min 3 \
	--char-ngram-max 5 \
	--top-neighbors 16
```

调参：

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

产物：

- `artifacts_retrieval_router_deploy/semantic_router_retrieval.npz`
- `artifacts_retrieval_router_deploy/semantic_router_retrieval.json`
- `artifacts_retrieval_router_deploy/metadata.json`
- `artifacts_retrieval_router_deploy/eval_samples.jsonl`
- `artifacts_retrieval_router_deploy/grid_search_results.json`

建议：

- 默认保持 `text_mode=both`
- 首先搜索 `top_k=1`
- 这是当前最推荐的轻量基线

## 4. Encoder Baseline

目标：使用小型 sentence-transformers 编码器做语义检索式 router。

安装依赖：

```bash
uv pip install -r requirements.txt
```

训练：

```bash
python train_encoder_semantic_router.py \
	--datasets ../mcp_dataset/mcpbench_tasks_single_runner_format.json,../mcp_dataset/laplace_tasks_single_runner_format.json \
	--output-dir artifacts_encoder_router_deploy \
	--text-mode both \
	--train-ratio 0.8 \
	--model-name sentence-transformers/all-MiniLM-L6-v2 \
	--epochs 2 \
	--batch-size 16 \
	--learning-rate 2e-5
```

调参：

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

产物：

- `artifacts_encoder_router_deploy/semantic_router_encoder_model/`
- `artifacts_encoder_router_deploy/semantic_router_encoder_prototypes.npz`
- `artifacts_encoder_router_deploy/metadata.json`
- `artifacts_encoder_router_deploy/eval_samples.jsonl`
- `artifacts_encoder_router_deploy/grid_search_results.json`

说明：

- 训练阶段构造正负 query 对做轻量监督微调
- 推理阶段仍然走 prototype cosine retrieval
- 适合和 retrieval baseline 做直接对比

## 5. FastText Baseline

说明：FastText 保留为历史分类基线，不再是首推方案。

安装依赖：

```bash
pip install fasttext
```

训练：

```bash
python train_fasttext_semantic_router.py \
	--datasets ../mcp_dataset/mcpbench_tasks_single_runner_format.json,../mcp_dataset/laplace_tasks_single_runner_format.json \
	--output-dir artifacts_fasttext_router_deploy \
	--text-mode both \
	--train-ratio 0.8 \
	--epoch 60 \
	--lr 0.5 \
	--word-ngrams 2 \
	--dim 100
```

调参：

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

产物：

- `artifacts_fasttext_router_deploy/semantic_router_fasttext.bin`
- `artifacts_fasttext_router_deploy/metadata.json`
- `artifacts_fasttext_router_deploy/eval_samples.jsonl`
- `artifacts_fasttext_router_deploy/grid_search_results.json`

建议：

- 追求召回时优先试 `top_k=2`
- 追求稳定时优先试 `top_k=1`
- 主要用来做历史对照，不建议作为首选部署模型

## 6. 统一对比

延迟测试：

```bash
python benchmark_router_latency.py --repeats 20
```

生成报告：

```bash
python generate_router_model_report.py
```

主要输出：

- `router_latency_summary.json`
- `router_model_report.md`