# Notebook 结构草案：多轮规划代理在真实工具环境中的稳健性评估

> 版本 v0.1。配套文件：`code_snippets.py`（B 节代码）、`perturbations.yaml`（算子注册表）、`run_grid.py`（02 引用的后台 runner）。
> 注：工作区写入器无法创建子目录，交付物平铺于工作区根；任务要求的 `experiments/` 前缀路径不可用，已按最近可行路径落盘（目标布局见下）。
> 核心度量对象：**Δperformance / Δperturbation（下降斜率）**，而非静态成功率。
> D1–D7 全部指标可由 trace 日志自动计算，无人工判读。

---

## A. 多 Notebook 拆分方案

### 总原则

1. **一个 notebook 只做一件事**：配置 / 校验 / 执行 / 计算 / 绘图 / 检验 / 报告。
2. **一切中间态落盘**：notebook 之间不共享 kernel 内存，只共享文件。目标目录约定：

```
experiments/                    # （目标布局；当前环境请平铺或手工建目录）
├── notebook_plan.md            # 本文件（A/C/D）
├── code_snippets.py            # B 节全部片段（自包含、可粘贴运行）
├── perturbations.yaml          # 扰动算子注册表（五层，3 implemented + stub）
├── run_grid.py                 # 02 引用的后台 runner（manifest 断点续跑+哨兵）
├── config/run_config.yaml      # 00 产出；下游唯一事实来源
├── traces/raw/{run_id}/{task_id}__trial{n}__seed{s}.jsonl
├── traces/rejected/{run_id}/bad_events.jsonl   # 01 自检示例 / 02 运行时被拒事件
├── metrics/per_trace.parquet | metric_summary.json | bootstrap_slopes.parquet
├── figures/degradation_curves.{pdf,png} | failure_mode_stack.{pdf,png}
├── stats/tests_table.csv
├── logs/run.log | run.done(哨兵)
└── report/report.md
```

3. 文件名自带 run_id/task_id/trial/seed，从路径即可重建元数据，不依赖上游 kernel 变量。

---

### 00_config.ipynb —— 实验配置的生成与冻结

**目的/输入/输出**：无输入 → `config/run_config.yaml` + 控制台打印 run_id（sha1[:12]）与 MD5 指纹。后续所有 notebook 只读它，禁止各自硬编码超参；改动配置 = 新 run_id。

| # | 类型 | 内容（每个 code cell 一句话说明） |
|---|------|------|
| 1 | md | 说明配置冻结的意义与「改配置即换 run」的纪律 |
| 2 | code | import `code_snippets.RunConfig` dataclass（片段 1；或整段粘贴进 cell） |
| 3 | code | 构造默认 RunConfig（seeds/任务集/算子网格/trial 数/成本预算上限）并 `to_yaml` 落盘 |
| 4 | code | 回读 YAML→dataclass，assert 往返无损（验证可序列化） |
| 5 | code | 计算并打印 run_id；若 config/ 已有同 id 则警告覆盖风险 |
| 6 | md | 声明不进 notebook 的东西：模型温度细节、API key 一律走环境变量 |

**切分理由**：秒级小输出适合逐 cell stdout 核对；可在不重跑实验的前提下换一批 seed 开新 run；kernel 重启后只需重跑本篇。

---

### 01_trace_schema_validate.ipynb —— trace 事件 schema 定义与自检

**目的/输入/输出**：在烧任何 LLM/VM 预算之前证明日志格式本身是对的（schema 错误进入长实验 = 全批 trace 报废）→ `traces/rejected/_selftest/bad_events.jsonl`。

| # | 类型 | 内容 |
|---|------|------|
| 1 | md | 26 个必填字段语义表；强调 injected_perturbation_id / perturbation_epsilon / retry_of / terminal_state_diff 是 D2/D3/D7 的计算依据 |
| 2 | code | 定义 `TRACE_EVENT_SCHEMA`（draft 2020-12，additionalProperties:false，数值边界约束）——片段 2 |
| 3 | code | 构造合法样例事件并通过校验（打印 OK） |
| 4 | code | 依次注入 4 类非法记录（缺字段/负 latency_ms/坏 http_status/多余未知字段），捕获 ValidationError 并把错误摘要+原始记录写 bad_events.jsonl |
| 5 | code | 提供 `append_event(path, event)`：先校验再落 JSONL，失败进 rejected——02 直接复用此函数 |
| 6 | md | 决策记录：选 jsonschema 而非 pydantic，因 trace 由被测代理侧跨语言产生，schema 须独立于 Python 类存在 |

**切分理由**：纯离线秒级 cell，与长实验混放会因单 cell 超时策略白白重跑；它是"先建 schema、后跑实验"顺序依赖的源头。

---

### 02_run_experiment.ipynb —— 轨迹采集（编排薄壳）

**目的/输入/输出**：读 `config/run_config.yaml` + `perturbations.yaml`，驱动 agent×工具×扰动中间件 → `traces/raw/{run_id}/*.jsonl` + `_manifest.json`（支持断点续跑）。

| # | 类型 | 内容 |
|---|------|------|
| 1 | md | 声明本篇是**编排壳**：真正的长循环在外部 runner（`run_grid.py`）里跑，notebook 只负责启动、监控、抽样检查 |
| 2 | code | 实例化 `PerturbationScheduler`（片段 3）并做确定性自检：同一 seed 两次 `plan()` 得到完全相同的 (operator, ε) 序列并 assert（Trace Determinism 前提） |
| 3 | code | dry-run：echo tool + scripted agent 走完 3 条假轨迹，验证事件能落盘且全过 schema——不花一分钱 |
| 4 | code | 枚举组合空间调用 `estimate_mvp_scale(...)`（片段 7）打印预计轨迹数/token/USD/墙钟；超预算 raise，提示先减档 |
| 5 | code | `subprocess.Popen(start_new_session=True)` 启动 `run_grid.py --dry-run ...`，stdout/stderr 重定向 `logs/run.log`，pid 落盘；**不在 cell 内同步等待** |
| 6 | code | 监控 cell：tail 末 20 行 + manifest 进度百分比（手动重跑本 cell 即刷新一次） |
| 7 | code | 抽样质检：随机取 5 条已完成 .jsonl 用 pandas 读入跑 schema 校验 + 关键字段非空检查 |
| 8 | md | nixos-test 高级路径（可选，默认跳过）：`block()/unblock()/crash()` 已核实可用；`VirtioTestDriver`、`create_block_snapshot`、`rollback_to_snapshot` **不存在**，状态回滚须自建 qcow2 overlay（工程推断，非官方 API）；Nix flake 官方标注 Experimental |

**切分理由**：MCP 驱动的 Jupyter 对单 cell 有超时中断，完整网格可能数小时；kernel 崩溃/重启时 in-memory 循环会整批蒸发——执行体必须是外部进程 + 落盘 manifest，notebook 只做监督。

---

### 03_metrics_compute.ipynb —— D1–D7 指标计算

**目的/输入/输出**：`traces/raw/{run_id}/*.jsonl` → `metrics/per_trace.parquet`（每轨迹一行宽表）+ `metrics/metric_summary.json`。

| # | 类型 | 内容 |
|---|------|------|
| 1 | md | 指标全景表：D1–D7 每个指标的分子/分母口径一句话 |
| 2 | code | `load_traces(run_dir)`：glob JSONL→逐行 schema 校验（宽松模式：坏行进 quarantine 计数）→拼单个 DataFrame，派生 epsilon/operator_layer/agent_name |
| 3 | code | `metrics_d1(df)`：SR、Goal-State Match Rate、Partial Progress Score、Verifiable Outcome Rate |
| 4 | code | `metrics_d2(df, eps_grid)`：PSUR@k、Degradation Slope（ε–SR 最小二乘线性拟合斜率）、Breakdown Point ε*（沿升序 ε 扫描首次跌破 τ·SR_clean）、Failure Mode Distribution |
| 5 | code | `metrics_d3(df)`：Anomaly Detection Recall/Precision、Recovery Rate、Median Recovery Steps、Self-Correction Success、Redundant Retry Ratio、Loop/Thrashing Rate |
| 6 | code | `metrics_d4(df)`：Schema Validity Rate、Illegal Call Rate、Idempotency Violation Count、Side-Effect Budget Overrun、Hallucinated Reference Rate |
| 7 | code | `metrics_d5(df)`：Cross-Turn Contradiction Rate、Constraint Retention Accuracy、Context Drift Score、Plan Stability Index |
| 8 | code | `metrics_d6(df)`：Steps-to-Solution P95、Cost per Solved Task、Tool Wait Time 占比、Cost-Normalized Success、Overhead Ratio |
| 9 | code | `metrics_d7(df)`：σ_SR（跨 seed）、Terminal State Consistency、Trace Determinism Score、Cross-Environment Transfer Gap |
| 10 | code | 调 `compute_all(df, out_dir)`（片段 4）：按维度逐一计算汇总写 metric_summary.json；per-trace 行写 parquet（无 pyarrow 退回 csv） |
| 11 | md | 口径备忘：检测类指标（D3 Recall/Precision）的 ground truth 一律取注入器日志侧，不采信代理自述——避免把答案交给被试 |

**切分理由**：指标函数是毫秒级纯函数、迭代最频繁（改口径就要重跑）。与采集解耦后可对同一批 trace 反复重算而不碰 GPU/API。

---

### 04_robustness_curves.ipynb —— 稳健性曲线与失效模式图

**目的/输入/输出**：`per_trace.parquet` → `figures/degradation_curves.{pdf,png}`、`figures/failure_mode_stack.{pdf,png}`。

| # | 类型 | 内容 |
|---|------|------|
| 1 | md | 图的读法：横轴 ε、纵轴 SR；关键不是曲线高低而是**斜率**与**拐点** |
| 2 | code | matplotlib 设置：`matplotlib.use("Agg")` 置于 pyplot import 之前，assert backend=="Agg"，固定 dpi/字号 |
| 3 | code | `plot_degradation(per_trace, prefix)`（片段 5）：按 agent 分组画 SR(ε)，bootstrap 95% CI 阴影（fill_between），breakdown point 处竖虚线 |
| 4 | code | 同数据 log-y 第二面板（低 SR 区不被压扁） |
| 5 | code | `plot_failure_modes(...)`：按 ε 档分组的错误类别占比堆叠条形图 |
| 6 | code | 辅助图 Cost per Solved Task vs ε（判断成功是否靠砸钱换来） |
| 7 | md | 每张图对应 report 哪一节、caption 怎么写 |

**切分理由**：绘图 cell 失败（字体/后端/缺列）不影响数据正确性，隔离后可单独重跑；大 figure 走文件而非 stdout，规避截断。

---

### 05_stats_tests.ipynb —— 统计检验与多重比较校正

**目的/输入/输出**：`per_trace.parquet` → `stats/tests_table.csv` + `metrics/bootstrap_slopes.parquet`。

| # | 类型 | 内容 |
|---|------|------|
| 1 | md | 配对逻辑说明：**同 task_id 跨 trial 配对**——同一任务在 agent A/B 上的 success/cost 差值构成配对样本，任务难度差异被配对消掉 |
| 2 | code | `paired_wilcoxon(df,a,b,metric)`（片段 6）：pivot 到 (task_id,trial)×agent，dropna 后 `scipy.stats.wilcoxon`，附 n_pairs |
| 3 | code | `bootstrap_slope_ci()`：按 task 分层重采样轨迹，重算每条重采样的 slope，取 2.5/97.5 分位，边算边落盘 |
| 4 | code | `run_all_tests(...)`：批量 (agent pair × metric)，`holm_bonferroni(pvals)` 就地实现排序校正加 p_holm 列 |
| 5 | code | 效应量已在片段 6 内返回：rank-biserial r = 1 − 2W/(n(n+1))；Cohen's d（配对差版）；写 csv 并限量打印前 20 行 |
| 6 | md | 解读守则：无 baseline 时绝对值不可解释，只有配对差与斜率差可比；Holm 后的 marginal p 如实标注 |

**切分理由**：bootstrap 是本套 notebook 里第二重的计算（分钟级）且需独立复核；混在 03 会让每次改指标口径都触发重采样。

---

### 06_report.ipynb —— 汇总渲染

**目的/输入/输出**：`metric_summary.json` + `figures/*` + `tests_table.csv` + `run_config.yaml` → `report/report.md`（可再导 HTML/PDF）。

| # | 类型 | 内容 |
|---|------|------|
| 1 | code | 读全部产物 + run_id 一致性校验：config 里的 run_id 必须出现在所有 trace 文件名中，否则中止（防混入旧 run 数据） |
| 2 | code | f-string 模板渲染（不引额外依赖）：概览表、D1–D7 表、图嵌入、检验表 |
| 3 | code | 附录自动生成：扰动算子清单（来自 perturbations.yaml，标 implemented/stub/nonexistent_api 状态）、已知缺陷段落 |
| 4 | md | 结论骨架：主结论必须是「斜率/拐点」表述，不允许出现「SR=xx% 所以很好」的无参照断言 |

**切分理由**：报告是可反复重渲染的视图层，永远不该触发昂贵计算。

---

### 拆分理由总结（对应 Jupyter MCP 执行特性）

| MCP/Jupyter 特性 | 对应的拆分决策 |
|---|---|
| kernel 有状态、变量跨 cell 存活但**重启即失忆** | notebook 间零共享内存，全部经 YAML/JSONL/parquet 交接；每篇开头有独立「读配置」cell，可任意时刻冷启动 |
| 逐 cell 返回 stdout/stderr，可精确定位坏 cell | 每 cell 单一职责；校验/计算/绘图分离，坏一个不必重跑全部 |
| 单 cell 超时会中断执行 | 长实验（02）不进 cell，改后台进程+manifest；05 的 bootstrap 拆成分块循环、边算边落盘 |
| 长 stdout 会被截断 | 大结果一律写文件，cell 只 print 前 N 行 + 文件路径（见 C 节） |
| 图形内嵌 base64 占 kernel 内存 | 04 用 Agg 后端 savefig 到 figures/，notebook 只放缩略确认 |
| 一个 MCP session 通常盯一个 kernel | 03/04/05 互不依赖同一 kernel，可分别在不同 notebook 并发推进 |

---

## C. Jupyter MCP 落地注意事项专节

### C.1 分步执行协议
1. **先建 kernel、后发代码**：创建 `.ipynb` 骨架 → attach kernel → 之后所有操作都是 run cell i。不要假设 MCP 会自动帮你选 kernel。
2. **逐 cell 运行并检查 stderr**：MCP 每次 run 返回该 cell 的 output 列表；`output_type=="error"` 的 ename/evalue 必须当轮消化。不要把 5 个 cell 连发后只看最后一个——中间 cell 的异常会被后续正常输出掩盖。
3. **每个 code cell 幂等**：重复执行应得到相同磁盘状态；写文件用临时文件 + `os.replace` 原子替换（MCP 重试机制可能悄悄重放 cell）。`code_snippets.py` 中 `RunConfig.to_yaml`、`run_grid.py` 中 `atomic_write_json` 均示范了此模式。
4. **cell 内禁止交互式输入**（`input()`、阻塞式 `plt.show()`、tqdm 弹窗）；进度信息写成日志文件，让监控 cell 去 tail。
5. `%pip install` 放顶格环境 cell 并 pin 版本；kernel 重启 site-packages 不丢，但虚拟环境路径可能变。

### C.2 长实验：后台脚本 + notebook 只做分析
- 铁律：**预计 > 2 分钟的工作不进 cell**。02 的采集主体是 `run_grid.py`，notebook 用 `subprocess.Popen(start_new_session=True)` 拉起，stdout/stderr 重定向 `logs/run.log`。
- 断点续跑：runner 每完成一条轨迹就原子重写 `_manifest.json`（见 run_grid.py），重启后跳过 manifest 中已完成组合。
- notebook 侧监控 cell 只做三件事：tail 日志、数文件、算进度——均秒级返回，不撞超时。
- 收尾信号：runner 结束时写 `logs/run.done` 哨兵文件；03 的第一行检查哨兵存在且 manifest 计数 == 计划组合数，否则明确报「采集不完整」并拒绝出指标。

### C.3 Kernel 重启的状态丢失防御
- 铁律：**一切中间态落盘**，文件名自带元数据（`{task_id}__trial{n}__seed{s}.jsonl`），从路径即可重建 DataFrame index，不依赖任何内存变量。
- 禁止「上游 notebook 的变量」这种隐式依赖；跨 notebook 只允许三种介质：YAML（配置）、JSONL（trace）、parquet/csv（指标表）。
- 每篇顶部放 `state_check` cell：assert 所需输入文件存在、大小非零、run_id 匹配。冷启动时第一个报错应该是「缺文件」而不是 `NameError`。

### C.4 stdout 截断应对
- 任何 `print(df)` 换成 `df.head(10)` + `df.to_parquet(path)` + `print(f"full table -> {path}, shape={df.shape}")`。
- 校验失败明细、坏行列表：只打印前 5 条摘要，全量写 `traces/rejected/*.jsonl`。
- 确需看大文本：`sed -n '1,50p' file` 或 pandas 抽样，分多次 cell 查看，别指望一次输出装下。
- traceback 过长时用 `traceback.format_exc()` 截尾存入文件。

### C.5 matplotlib 后端处理
- MCP/headless 环境没有显示服务器。**在任何 pyplot import 之前**执行 `matplotlib.use("Agg")`（片段 5 的两个绘图函数内部均已如此处理，可直接复用）。
- 若 kernel 已先 import 过 pyplot 再切后端会静默失败——04 的第一个 code cell 就是设后端并 `assert matplotlib.get_backend()=="Agg"`。
- 只用 `fig.savefig()`，不用 `plt.show()`；同时输出 png（供 notebook 内嵌预览）与 pdf（供报告排版）。
- 中文标签需显式指定字体，缺失时在服务器上会变豆腐块；稳妥做法：图内标签全英文（片段 5 已照此写），报告正文中文。
- 每张图画完立即 `plt.close(fig)`，防止长会话 kernel 累积 figure 泄漏 OOM（片段 5 已示范）。

---

## D. 风险与待验证项

### D.1 无文献 baseline —— 绝对值不可解释
AgentBench / tau-bench / SWE-bench / GAIA / OSWorld / BFCL / ToolEmu / ReAct / Reflexion 等条目**均未经核验**，本框架不得将其作为既定 baseline 引用，只能在报告的「待验证项」表中占位（条目、声称指标、核验路径、状态=UNVERIFIED）。因此：
- 「SR=0.62」单独无意义；只有「同一任务集上 A 的 slope 显著小于 B」「相对 clean 条件 PSUR@k」这类**相对比较**成立。
- τ（breakdown 阈值）、预算上限等常数是本仓库的工程选择，报告中须显式声明为 arbitrary-but-fixed，并在敏感性分析中扫一遍 τ。
- Partial Progress / Goal-State Match 依赖任务自带的 assertion 集合；assertion 设计不当会把指标变成噪声放大器（Verifiable Outcome Rate 本身就是这一风险的哨兵）。

### D.2 LLM-as-judge 的引入条件
当前 D1–D7 刻意全部基于可机读 trace，无人工/裁判判读。若未来必须引入 judge（例如评 plan 语义质量）：
- 至少 **2–3 个异构裁判模型** + 报告 inter-judge agreement（Krippendorff's α 或 Cohen's κ），分歧样本人工仲裁后沉淀为锚定样例；
- 每批评测配 **anchor set**（已知金标的固定样例），judge 在 anchor 上的准确率低于阈值则该批分数整体作废；
- judge prompt 与模型版本 hash 进 run_config，否则 D7 的可复现性被 judge 自己破坏；
- judge 调用计入 D6 成本，不能白嫖。

### D.3 nixos-test 高级路径的不确定性（重要）
- 已核实可用：`block()` / `unblock()` / `crash()`。
- **不存在**（勿在代码或论文中假装存在）：`VirtioTestDriver`、`create_block_snapshot`、`rollback_to_snapshot`。状态层扰动的回滚必须**自建 qcow2 overlay**（`qemu-img create -f qcow2 -b base.qcow2 overlay.img`，回滚 = 丢弃 overlay），此路线属**工程推断**而非官方 API，需在报告中标注推断属性并小规模先行验证。perturbations.yaml 中该项 status 标为 `nonexistent_api` 以防误用。
- Nix flake 官方标注 **Experimental**：接口可能在版本间断裂；flake.lock + 记录 nixpkgs revision 是最低要求。CI 镜像漂移会伪装成「代理性能退化」，D7 的 Cross-Environment Transfer Gap 至少要包含一组**零扰动的跨环境重跑**来隔离这一混淆。

### D.4 其他诚实清单

| 风险 | 缓解 |
|---|---|
| 扰动注入器自身 bug（没注入却记为已注入） | 干跑阶段用 echo tool 验证注入确实改变了 response；注入器行为纳入单元测试 |
| 代理自报字段不可信（anomaly 标签若来自代理叙述） | 检测类指标（D3 Recall/Precision）的 ground truth 一律取注入器日志侧 |
| seed 决定论 ≠ 系统决定论（LLM API 服务端仍在演化） | Trace Determinism Score 定义为「同 seed 下事件序列的结构相似度」而非 bit-exact；temperature=0 也不保证 determinism，需在 σ_SR 中体现 |
| 成本失控（组合爆炸） | 02 的估算 cell 在预算超限时硬性 raise（`gate_or_raise`）；先跑 MVP 网格（片段 7），确认斜率信号后再加密 ε 档 |
| retry_of / side_effect_flag 埋点需侵入被测代理 | 提供统一 tool-wrapper SDK；无法埋点的黑盒代理降级为「仅 D1/D2/D6 可算」并在 manifest 标注 missing_coverage |
| 辛普森悖论（跨任务族平均掩盖局部塌陷） | 报告同时给分任务族曲线与总体加权曲线；检验也在 task 配对层面做 |
| D5 Constraint Retention 需外部约束清单列，合成数据下返回 NaN 占位 | 正式版接入 tasks_mini.yaml 的 constraints 字段后再启用，不虚报数字 |
