# result_e2e 使用说明

这个目录当前包含三类实验：

1. cumulative latency（模拟值）
- 含义：工具等待就绪时间的累积，不包含大模型推理时间。
- 脚本：run_cumulative_latency_experiment.py
- 对比对象：on_demand / laplace / always_on

2. E2E QPS sweep（模拟值）
- 含义：在闭环并发压测（QPS 递增）下，输出 E2E、工具 cumulative、CPU、内存指标。
- 脚本：run_e2e_latency_experiment.py
- 对比对象：on_demand / laplace / always_on

3. real E2E QPS sweep（真实值）
- 含义：真实调用模型和工具的并发压测，输出真实 E2E、工具 cumulative、CPU、内存指标。
- 脚本：run_real_e2e_latency_experiment.py
- 对比对象：on_demand / laplace / always_on

## 一、先进入目录

cd /mnt/d/Project/agentscope/examples/agent/on_demand_meta_planner_agent/result_e2e

## 二、跑 cumulative latency（模拟）

python run_cumulative_latency_experiment.py --sample-size 100 --seed 20260621 --resume

输出文件：
- cumulative_trace_results.jsonl
- cumulative_trace_metrics.csv
- cumulative_summary.json

说明：
- on_demand：对应 cold start（不启用 SDG/prewarm）
- laplace：对应 SDG + prewarm
- always_on：模拟 MCP 常驻，整体比 laplace 略好一点，分布走势接近

## 三、画 cumulative CDF 图

python plot_e2e_cdf.py

默认输出：
- cumulative_latency_cdf.png
- cumulative_latency_cdf.pdf

如果要指定输入和输出前缀：
python plot_e2e_cdf.py --input-csv cumulative_trace_metrics.csv --output-prefix cumulative_latency_cdf

## 四、画 E2E QPS sweep 图

python plot_e2e_qps.py

默认输入：
- `real_e2e_scalability_metrics.csv`
- `formal_qps1to20_r2_strict_replay/real_e2e_resource_metrics.csv`

默认输出（每个都有 png/pdf）：
- `e2e_scalability_latency`（无 legend 的单图）
- `e2e_scalability_tool_cumulative`
- `e2e_resource_cpu`
- `e2e_resource_memory`
- `e2e_scalability_resource`（四个子图合成的一行四列总图，顶部居中显示共享 legend，(a)–(d) 标注放在各子图下方，供论文插图使用）

## 五、常用参数说明

- --sample-size
  控制抽样 trace 数量。默认 100。

- --seed
  控制抽样和随机过程，保证可复现。默认 20260621。

- --resume
  开启断点续跑。已经完成的 trace 会跳过，适合长任务中断后继续。

## 六、跑 E2E QPS sweep（模拟）

按论文补充实验默认设置（seed=0，sample-size=20，QPS=1..20）：

python run_e2e_latency_experiment.py --sample-size 20 --seed 0 --qps-min 1 --qps-max 20

输出文件：
- e2e_qps_results.jsonl
- e2e_qps_metrics.csv
- e2e_scalability_metrics.csv
- e2e_resource_metrics.csv
- e2e_qps_summary.json

说明：
- `e2e_scalability_metrics.csv` 对应可扩展性章节，包含 E2E p99、goodput、工具 cumulative。
- `e2e_resource_metrics.csv` 对应资源章节，包含 CPU/内存均值与峰值。
- 默认是本地可跑配置；若机器性能更强，可提高 `--qps-max` 和 `--requests-per-qps`。

## 七、推荐执行顺序

1) 先跑 cumulative（模拟）
2) 跑 E2E QPS sweep（模拟）
3) 画 cumulative CDF 图和 QPS sweep 图
4) 最后汇总

## 八、跑 real E2E QPS sweep（真实）

按论文补充实验默认设置（seed=0，sample-size=20，QPS=1..20，每个 QPS 重复 10 次）：

python run_real_e2e_latency_experiment.py --sample-size 20 --seed 0 --qps-min 1 --qps-max 20 --repeats 10

输出文件：
- real_e2e_request_results.jsonl
- real_e2e_wave_results.jsonl
- real_e2e_qps_metrics.csv
- real_e2e_scalability_metrics.csv
- real_e2e_resource_metrics.csv
- real_e2e_summary.json

说明：
- 该脚本是实时压测，不走模拟，耗时和成本都明显更高。
- 需要先配置环境变量：`DASHSCOPE_API_KEY`。
- 默认开启断点续传（resume），中断后重启会跳过已完成的 mode/qps/repeat 波次。
- 若希望全新开始，增加参数：`--no-resume`。
- 若本地资源有限，建议先用 `--qps-max 3 --repeats 1` 做冒烟验证。

### TTL-20m 历史数据回放估算

`real_e2e_scalability_metrics.csv` 中 `ttl_20m` 行的 `e2e_p99_ms` 和 `tool_cumulative_p95_ms` 是基于已有历史数据进行 20 分钟 TTL 回放的估算，并非新的真实 TTL 实验：

- 使用 `formal_qps1to20_r2_strict_replay` 的 on-demand 请求/波次时间和 trace 中实际访问的 MCP server。每个 QPS 独立从冷缓存开始；同一波次按并发访问处理，波次完成时将访问过的 server 记为 warm，下一波仅在上次使用距当前不超过 20 分钟时命中。
- 每个 QPS 的冷 server 访问比例约为 47%–83%：QPS 1–3 约 82%，QPS 4–20 约 47%–55%。该比例用于在已有 `always_on`（reserved）和 `on_demand` 延迟指标间插值。
- E2E P99 插值结果再做单调回归，以降低只有两次历史重复实验带来的局部噪声；tool cumulative P95 保留按历史冷访问比例得到的插值结果。历史 always_on tool cumulative P95 在 QPS 11 起出现约 50 秒的高值，因此对应 TTL 估算也会明显升高，反映输入基线的这一现象。
- CPU 和内存 TTL 行仍是 Reserved/On-demand 间的 35% 插值，不是由 TTL 命中回放估算。为避免高 QPS 下 Reserved 原始测量波动传递到 TTL memory 曲线，QPS 16–20 的 TTL average/peak memory 从 QPS 15 的估值开始按每档 0.5% 平滑递增。所有 TTL 值均为离线估算，不代表新的实测结果；请求仅在波次粒度上排序，缺少波次内每次 server 激活的精确时间戳。

直接运行 `python plot_e2e_qps.py` 时，脚本默认读取 `formal_qps1to20_r2_strict_replay/real_e2e_resource_metrics.csv`，并生成 CPU 和 memory 图。需要替换资源数据时可用 `--resource-csv` 指定其他文件。

### LRU-5 离线模拟

`real_e2e_scalability_metrics.csv` 中的 `lru_5` 行模拟固定 warm capacity 为 5 的 LRU baseline，并非真实运行结果：

- 每个 QPS sweep 从空 cache 开始，按历史请求 trace 的 server 使用顺序更新 LRU，最多保留 5 个最近使用的 server；同一并发 wave 的所有请求先检查 wave 开始时的 cache，wave 结束时再按稳定的 request/trace 顺序更新 recency。
- 按各 QPS 历史请求的 cold server-access 比例，在已有 `always_on` 与 `on_demand` scalability 指标间插值，估算完整 CSV 指标行。LRU-5 只覆盖 32 个候选 server 的一部分，也不依赖未来频率。
- 资源 CSV 中的 LRU CPU avg/peak 按同一冷访问比例在 `always_on` 和 `on_demand` 资源指标间插值；memory avg/peak 则估算为 `on_demand + (5/32) * (always_on - on_demand)`，即假设各 sandbox 的内存开销相近，并按 5 个常驻 sandbox 估算额外内存。
- 该结果受每个 QPS 只有两个历史 repeat、波次内缺少精确 server 事件时间及等 sandbox 内存假设影响，属于离线 baseline 估算。`plot_e2e_qps.py` 的图例显示为 `LRU`；资源图会绘制这些估算值。
