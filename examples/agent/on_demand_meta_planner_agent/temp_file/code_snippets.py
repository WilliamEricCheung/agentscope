"""code_snippets.py — 稳健性评估框架最小可运行片段（B 节）。

Python 3.10+。依赖：pandas / numpy / scipy / jsonschema / pyyaml / matplotlib（+pytest 可选）。
片段编号 ↔ notebook：1→00_config, 2→01_trace_schema_validate, 3/7→02_run_experiment,
4→03_metrics_compute, 5→04_robustness_curves, 6→05_stats_tests。
每个片段自包含、不依赖未定义的隐藏变量；`python code_snippets.py` 会跑内置自检 demo。
无法真实执行的部分（付费 LLM API、nixos-test VM）写成显式接口桩并注明。
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import yaml
import jsonschema


# =====================================================================
# 片段 1：配置与全局常量（00_config）—— dataclass + YAML 序列化往返
# =====================================================================
@dataclass
class OperatorGrid:
    """一层扰动算子及其 ε 档位。"""
    layer: str                      # network_runtime | semantic_return | state | reference | ordering
    operators: list[str]            # 如 ["timeout", "field_drop"]
    eps_grid: list[float]           # 强度档位，如 [0.0, 0.1, 0.25, 0.5]


@dataclass
class RunConfig:
    run_name: str = "robust-mvp-v0"
    seeds: list[int] = field(default_factory=lambda: [0, 1, 2])
    task_set: str = "tasks_mini.yaml"          # 任务集名（含 assertion 定义）
    n_tasks: int = 12                          # MVP 占位；正式版从 task_set 读取
    agents: list[str] = field(default_factory=lambda: ["react_base", "reflexion_lite"])
    trials_per_cell: int = 8                   # 每 (agent,task,op,eps) 重复次数
    max_turns: int = 24                        # 单轨迹轮次上限
    operator_grids: list[OperatorGrid] = field(default_factory=lambda: [
        OperatorGrid("network_runtime", ["timeout"], [0.0, 0.1, 0.25, 0.5]),
        OperatorGrid("semantic_return", ["field_drop", "nonexistent_id"], [0.0, 0.1, 0.25, 0.5]),
    ])
    cost_budget_usd: float = 20.0              # 硬性上限，超出则 02 拒绝启动
    token_budget: int = 5_000_000
    breakdown_tau: float = 0.5                 # ε* 阈值：SR < tau * SR_clean
    wallclock_per_trial_sec: float = 90.0      # 估算用经验值
    temperature: float = 0.0                   # 注意：temp=0 ≠ determinism，见 D.4

    def to_yaml(self, path: str | Path) -> None:
        p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        with open(tmp, "w") as f:
            yaml.safe_dump(asdict(self), f, sort_keys=False, allow_unicode=True)
        tmp.replace(p)                          # 原子替换，保证 cell 幂等

    @classmethod
    def from_yaml(cls, path: str | Path) -> "RunConfig":
        raw = yaml.safe_load(Path(path).read_text())
        grids = [OperatorGrid(**g) for g in raw.pop("operator_grids")]
        return cls(operator_grids=grids, **raw)

    @property
    def run_id(self) -> str:
        blob = json.dumps(asdict(self), sort_keys=True, default=str).encode()
        return hashlib.sha1(blob).hexdigest()[:12]


def demo_config_roundtrip(tmpdir: str = "/tmp/robust_demo") -> None:
    cfg = RunConfig()
    p = Path(tmpdir) / "config" / "run_config.yaml"
    cfg.to_yaml(p)
    assert RunConfig.from_yaml(p) == cfg, "YAML 往返不一致"
    print(f"[snippet1] OK run_id={cfg.run_id} -> {p}")   # API key 等敏感项绝不进 YAML


# =====================================================================
# 片段 2：trace 事件 schema + 严格校验（01_trace_schema_validate）
# JSON Lines 一行一事件；jsonschema draft 2020-12，additionalProperties:false。
# =====================================================================
TRACE_EVENT_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "run_id", "trial_id", "seed", "task_id", "turn_idx",
        "tool_name", "tool_args_hash", "request_bytes", "response_bytes",
        "latency_ms", "http_status", "error_class",
        "injected_perturbation_id", "perturbation_epsilon", "retry_of",
        "side_effect_flag", "resource_id", "tokens_in", "tokens_out",
        "cost_usd", "terminal_state_diff", "success_assertion_id",
        "assertion_result", "ts_start", "ts_end",
    ],
    "properties": {
        "run_id": {"type": "string", "minLength": 1},
        "trial_id": {"type": "integer", "minimum": 0},
        "seed": {"type": "integer"},
        "task_id": {"type": "string", "minLength": 1},
        "turn_idx": {"type": "integer", "minimum": 0},
        "tool_name": {"type": "string", "minLength": 1},
        "tool_args_hash": {"type": "string", "pattern": "^[0-9a-f]{12}$"},
        "request_bytes": {"type": "integer", "minimum": 0},
        "response_bytes": {"type": "integer", "minimum": 0},
        "latency_ms": {"type": "number", "minimum": 0},           # 负值必被拒
        "http_status": {"type": "integer", "minimum": 100, "maximum": 599},
        "error_class": {"type": ["string", "null"]},
        "injected_perturbation_id": {"type": ["string", "null"]},
        "perturbation_epsilon": {"type": "number", "minimum": 0, "maximum": 1},
        "retry_of": {"type": ["integer", "null"]},                # 指向被重试事件的 turn_idx
        "side_effect_flag": {"type": "boolean"},
        "resource_id": {"type": ["string", "null"]},
        "tokens_in": {"type": "integer", "minimum": 0},
        "tokens_out": {"type": "integer", "minimum": 0},
        "cost_usd": {"type": "number", "minimum": 0},
        "terminal_state_diff": {"type": ["string", "null"]},       # 终态 diff 摘要（D1/D7）
        "success_assertion_id": {"type": ["string", "null"]},
        "assertion_result": {"enum": ["pass", "fail", "not_applicable", None]},
        "ts_start": {"type": "number"},
        "ts_end": {"type": "number"},
    },
}


def validate_event(event: dict) -> None:
    jsonschema.validate(instance=event, schema=TRACE_EVENT_SCHEMA)


def append_event(path: str | Path, event: dict, rejected_path: str | Path) -> bool:
    """先校验再落盘 JSONL；失败则把错误摘要+原始记录写 rejected，返回 False。02 复用此函数。"""
    try:
        validate_event(event)
    except jsonschema.ValidationError as e:
        rej = Path(rejected_path); rej.parent.mkdir(parents=True, exist_ok=True)
        rec = {"error": e.message, "json_path": list(e.absolute_path), "event": event}
        with open(rej, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return False
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return True


def make_event(**over) -> dict:
    ev = dict(run_id="r0", trial_id=0, seed=0, task_id="t1", turn_idx=0,
              tool_name="search", tool_args_hash="ab12cd34ef56", request_bytes=120,
              response_bytes=980, latency_ms=42.0, http_status=200, error_class=None,
              injected_perturbation_id=None, perturbation_epsilon=0.0, retry_of=None,
              side_effect_flag=False, resource_id=None, tokens_in=300, tokens_out=90,
              cost_usd=0.001, terminal_state_diff=None, success_assertion_id=None,
              assertion_result=None, ts_start=1.0, ts_end=1.042)
    ev.update(over)
    return ev


def demo_validation_rejects(tmpdir: str = "/tmp/robust_demo") -> None:
    rej = Path(tmpdir) / "traces" / "rejected" / "_selftest" / "bad_events.jsonl"
    if rej.exists():
        rej.unlink()
    assert append_event(f"{tmpdir}/good.jsonl", make_event(), rej)
    bad_cases = [
        {k: v for k, v in make_event().items() if k != "latency_ms"},  # 缺必填字段
        make_event(latency_ms=-5),                                     # 负延迟
        make_event(http_status=999),                                   # 非法状态码
        make_event(surprise_field="x"),                                # 未知字段
    ]
    for b in bad_cases:
        assert not append_event(f"{tmpdir}/should_not_exist.jsonl", b, rej)
    first_err = json.loads(rej.read_text().splitlines()[0])["error"]
    print(f"[snippet2] OK: 1 accepted, {len(bad_cases)} rejected -> {rej}; 首条错误: {first_err}")


# =====================================================================
# 片段 3：扰动注入中间件最小实现（02_run_experiment）
# 关键不变量：同一 seed → 完全相同的 (operator, ε) 注入序列（Trace Determinism 前提）。
# =====================================================================
@dataclass
class PerturbationOp:
    op_id: str
    layer: str                    # 五层之一
    kind: str                     # timeout | field_drop | nonexistent_id | ...
    params: dict = field(default_factory=dict)


def load_registry(yaml_path: str | Path) -> tuple[list[PerturbationOp], dict[str, list[float]]]:
    """从 perturbations.yaml 载入注册表，只收 implemented 的算子参与抽样。"""
    raw = yaml.safe_load(Path(yaml_path).read_text())
    ops, eps_by_layer = [], {}
    for layer, items in raw["layers"].items():
        for it in items:
            if it.get("status") == "implemented":
                ops.append(PerturbationOp(it["op_id"], layer, it["kind"], it.get("params", {})))
                eps_by_layer.setdefault(layer, it.get("eps_grid", [0.0, 0.1, 0.25, 0.5]))
    return ops, eps_by_layer


class PerturbationScheduler:
    """按 (seed, 组合索引) 确定性抽样决定注入哪个算子及强度 ε。"""

    def __init__(self, registry: list[PerturbationOp], eps_grid: list[float]):
        self.registry = registry
        self.eps_grid = eps_grid

    def plan(self, seed: int, n_steps: int) -> list[tuple[PerturbationOp, float]]:
        rng = random.Random(seed)                     # 独立 RNG，绝不用全局 random
        out = []
        for _ in range(n_steps):
            op = rng.choice(self.registry)
            eps = rng.choice(self.eps_grid)
            out.append((op, eps))
        return out


def apply_perturbation(op: PerturbationOp, eps: float,
                       call: Callable[[dict], dict], args: dict) -> dict:
    """包住一次真实 tool call，返回可能被篡改后的 response dict。"""
    if eps <= 0.0 or op.kind == "none":
        return call(args)
    if op.kind == "timeout":                            # 网络运行时层
        budget = max(1.0, (1.0 - eps) * op.params.get("normal_latency_ms", 200.0))
        t0 = time.monotonic()
        resp = call(args)                               # 真实调用照常发生
        if (time.monotonic() - t0) * 1000.0 > budget:
            return {"ok": False, "error_class": "TimeoutError",
                    "detail": f"simulated timeout at eps={eps}"}
        resp["_near_timeout"] = True
        return resp
    if op.kind == "field_drop":                         # 语义返回值层
        resp = dict(call(args))
        keys = sorted(k for k in resp if k != "ok")     # 字典序切片，保持确定性
        drop_n = max(1, math.ceil(len(keys) * eps))
        for k in keys[:drop_n]:
            resp.pop(k, None)
        resp["_dropped_fields"] = drop_n
        return resp
    if op.kind == "nonexistent_id":                     # 引用层
        resp = dict(call(args))
        if eps >= 0.5 and isinstance(resp.get("id"), str):
            resp["id"] = "00000000-dead-beef-notexist"
            resp["_hallucinated_ref"] = True
        return resp
    raise NotImplementedError(f"operator stub not implemented: {op.kind}")  # TODO 桩


def instrumented_tool_call(tool_fn: Callable[[dict], dict], args: dict,
                           plan_seq: list[tuple[PerturbationOp, float]], step_i: int,
                           run_id: str, trial_id: int, seed: int, task_id: str,
                           jsonl_path: str, rejected_path: str) -> dict:
    """装饰入口：执行一次被扰动的调用并写 trace 事件（含注入元数据）。"""
    op, eps = (plan_seq[step_i] if step_i < len(plan_seq)
               else (PerturbationOp("none", "none", "none"), 0.0))
    t0 = time.monotonic()
    try:
        resp = apply_perturbation(op, eps, tool_fn, args)
        ok = resp.get("ok", True)
        err_cls, status = (resp.get("error_class"), 500) if not ok else (None, 200)
    except Exception as e:
        resp, err_cls, status = {"ok": False}, type(e).__name__, 503
    args_hash = hashlib.sha1(json.dumps(args, sort_keys=True).encode()).hexdigest()[:12]
    ev = make_event(run_id=run_id, trial_id=trial_id, seed=seed, task_id=task_id,
                    turn_idx=step_i, tool_name=getattr(tool_fn, "__name__", "tool"),
                    tool_args_hash=args_hash,
                    request_bytes=len(json.dumps(args)), response_bytes=len(json.dumps(resp)),
                    latency_ms=(time.monotonic() - t0) * 1000.0, http_status=status,
                    error_class=err_cls,
                    injected_perturbation_id=(None if op.kind == "none"
                                              else f"{op.layer}:{op.op_id}"),
                    perturbation_epsilon=eps)
    append_event(jsonl_path, ev, rejected_path)         # 复用片段 2
    return resp


def demo_scheduler_determinism() -> None:
    reg = [PerturbationOp("net_timeout", "network_runtime", "timeout",
                          {"normal_latency_ms": 200}),
           PerturbationOp("sem_field_drop", "semantic_return", "field_drop"),
           PerturbationOp("ref_nonexistent_id", "reference", "nonexistent_id")]
    sch = PerturbationScheduler(reg, [0.0, 0.1, 0.25, 0.5])
    a = [(o.op_id, e) for o, e in sch.plan(seed=42, n_steps=20)]
    b = [(o.op_id, e) for o, e in sch.plan(seed=42, n_steps=20)]
    assert a == b, "同 seed 注入序列必须一致！"
    print("[snippet3] OK determinism:", a[:4])


# =====================================================================
# 片段 4：指标计算纯函数 D1–D7（03_metrics_compute）
# df 列 = 片段 2 全部字段 + 派生列 agent_name / epsilon（逐事件）。
# 比率类指标在 docstring/注释写明分子分母。
# =====================================================================
TRAJ_KEYS = ["run_id", "trial_id", "task_id", "seed"]


def per_trajectory(df: pd.DataFrame) -> pd.DataFrame:
    """把逐事件 df 聚合为逐轨迹宽表（per_trace），供绘图与检验使用。"""
    g = df.groupby(TRAJ_KEYS, as_index=False)
    out = pd.DataFrame({
        "run_id": g.run_id.first(), "trial_id": g.trial_id.first(),
        "task_id": g.task_id.first(), "seed": g.seed.first(),
        "epsilon": g.perturbation_epsilon.max(),
        "steps": g.turn_idx.max() + 1,
        "cost_usd": g.cost_usd.sum(),
        "tokens_total": g.tokens_in.sum() + g.tokens_out.sum(),
        "n_injected": g.injected_perturbation_id.apply(lambda s: int(s.notna().sum())),
        "any_error": g.error_class.apply(lambda s: bool(s.notna().any())),
        "has_pass": g.assertion_result.apply(lambda s: bool((s == "pass").any())),
        "has_fail": g.assertion_result.apply(lambda s: bool((s == "fail").any())),
    })
    out["success"] = ((out.has_pass) & (~out.has_fail)).astype(int)
    out["failure_mode"] = "none"
    emap = (df[df.error_class.notna()]
            .groupby(TRAJ_KEYS).error_class.first())
    if len(emap):
        out = out.merge(emap.rename("failure_mode").reset_index(), on=TRAJ_KEYS, how="left")
        out.failure_mode = out.failure_mode.fillna("none")
    return out


def sr_from_traces(df: pd.DataFrame) -> float:
    """SR：分子=有 pass 且无 fail 的轨迹数；分母=轨迹总数。"""
    pt = per_trajectory(df)
    return float(pt.success.mean()) if len(pt) else 0.0


def metrics_d1(df: pd.DataFrame) -> dict:
    pt = per_trajectory(df)
    g = df.groupby(TRAJ_KEYS)
    # Goal-State Match Rate：分子=terminal_state_diff 为空/no_diff/match 前缀的轨迹；分母=轨迹数
    def match(t: pd.DataFrame) -> bool:
        last = t.iloc[-1].terminal_state_diff
        return last is None or str(last).strip() in ("", "{}", "no_diff") \
            or str(last).startswith("match")
    goal = float(g.apply(match, include_groups=False).mean())
    # Partial Progress Score：分子=轨迹内通过的 distinct assertion 数之和；分母=全体 distinct assertion 数 × 轨迹数
    total_assertions = max(1, df.success_assertion_id.dropna().nunique())
    partial = float(g.success_assertion_id.nunique().sum()
                    / (total_assertions * max(1, len(pt))))
    verif = float(g.apply(lambda t: t.success_assertion_id.notna().any(),
                          include_groups=False).mean())   # Verifiable Outcome Rate
    return {"SR": sr_from_traces(df), "GoalStateMatchRate": goal,
            "PartialProgressScore": partial, "VerifiableOutcomeRate": verif}


def fit_degradation(df: pd.DataFrame, tau: float = 0.5) -> dict:
    """Degradation Slope 与 Breakdown Point ε*。
    slope：对 (ε, SR(ε)) 做 np.polyfit(deg=1) 得 ΔSR/Δε（核心度量对象）。
    ε*：沿升序 ε 扫描，首个 SR(ε) < tau·SR(ε=0) 的 ε；从未跌破则 inf。"""
    pt = per_trajectory(df)
    by_eps = pt.groupby("epsilon").success.mean().sort_index()
    xs, ys = by_eps.index.to_numpy(float), by_eps.to_numpy(float)
    slope = float(np.polyfit(xs, ys, 1)[0]) if len(xs) >= 2 else float("nan")
    clean = float(by_eps.loc[0.0]) if 0.0 in by_eps.index else (ys[0] if len(ys) else 0.0)
    eps_star = float("inf")
    for x, y in zip(xs, ys):
        if clean > 0 and y < tau * clean:
            eps_star = float(x); break
    return {"degradation_slope": slope, "breakdown_point_eps": eps_star,
            "sr_by_eps": {float(k): float(v) for k, v in by_eps.items()}}


def metrics_d2(df: pd.DataFrame, k: int = 3, tau: float = 0.5) -> dict:
    """PSUR@k = SR_perturbed / SR_clean；perturbed = 注入 ≥k 次扰动的轨迹子集。"""
    pt = per_trajectory(df)
    sr_c = float(pt.success.mean()) if len(pt) else 0.0
    heavy = pt[pt.n_injected >= k]
    sr_p = float(heavy.success.mean()) if len(heavy) else 0.0
    fm = (df[df.error_class.notna()].error_class
          .value_counts(normalize=True).to_dict())        # Failure Mode Distribution
    deg = fit_degradation(df, tau)
    return {"PSUR_at_k": sr_p / sr_c if sr_c > 0 else float("nan"),
            "failure_mode_distribution": fm, **deg}


def metrics_d3(df: pd.DataFrame) -> dict:
    """纠错类指标。ground truth = 注入器标记（injected_perturbation_id 非空的事件），
    代理『检出』= 其后存在 retry_of 指回该 turn 的重试事件。"""
    anom = df[df.injected_perturbation_id.notna()]
    retried = set(zip(df.loc[df.retry_of.notna(), "retry_of"].astype(int),
                      df.loc[df.retry_of.notna(), "trial_id"]))
    detected = sum((int(t.turn_idx), t.trial_id) in retried for t in anom.itertuples())
    recall = detected / max(1, len(anom))                  # Anomaly Detection Recall
    prec = detected / max(1, len(retried))                 # Anomaly Detection Precision
    pt = per_trajectory(df)
    failed = pt[pt.any_error]
    recovery = float(((failed.has_pass) & (~failed.has_fail)).mean()) if len(failed) else float("nan")
    # Median Recovery Steps：出错事件到首次重试的 turn 距离中位数
    dists = []
    for _, t in df[df.error_class.notna()].groupby(TRAJ_KEYS):
        r = t[t.retry_of.notna()]
        if len(r):
            dists.append(int(r.turn_idx.min() - t.error_class.notna().values.argmax()))
    med = float(np.median(dists)) if dists else float("nan")
    # Redundant Retry Ratio：分子=args_hash 与前次失败完全相同的重试数；分母=全部重试数
    retries = df[df.retry_of.notna()]
    dup = retries.groupby(["run_id", "trial_id", "tool_args_hash"]).size()
    redundant = float(dup[dup > 1].sum() / max(1, len(retries)))
    thrash = loop_thrashing_rate(df)
    return {"AnomalyRecall": recall, "AnomalyPrecision": prec,
            "RecoveryRate": recovery, "MedianRecoverySteps": med,
            "SelfCorrectionSuccess": recovery,     # 简化口径：出错后仍通过全部断言
            "RedundantRetryRatio": redundant, "LoopThrashingRate": thrash}


def loop_thrashing_rate(df: pd.DataFrame) -> float:
    """分子=连续≥3 次相同 (tool_name, tool_args_hash) 的轨迹数；分母=轨迹数。"""
    def has_loop(t: pd.DataFrame) -> bool:
        seq = list(zip(t.tool_name, t.tool_args_hash))
        return any(seq[i:i+3] == seq[i+1:i+4] for i in range(len(seq) - 3))
    g = df.sort_values("turn_idx").groupby(TRAJ_KEYS)
    return float(g.apply(has_loop, include_groups=False).mean())


def metrics_d4(df: pd.DataFrame, traj_cost_budget_usd: float = 1.0) -> dict:
    valid = float(df.http_status.between(200, 299).mean())        # Schema Validity Rate（以 2xx 代理；严格版应回放 args 过 tool schema）
    illegal = float(df.error_class.isin(["SchemaError", "IllegalCall"]).mean())  # Illegal Call Rate
    se = df[(df.side_effect_flag) & df.resource_id.notna()]
    idem = se.groupby(["run_id", "trial_id", "resource_id", "tool_args_hash"]).size()
    idem_viol = int((idem[idem > 1] - 1).sum())                   # Idempotency Violation Count
    over = df.groupby(TRAJ_KEYS).cost_usd.sum()
    overrun = int((over > traj_cost_budget_usd).sum())            # Side-Effect Budget Overrun
    halluc = float(df.error_class.eq("HallucinatedReference").mean())  # Hallucinated Reference Rate
    return {"SchemaValidityRate": valid, "IllegalCallRate": illegal,
            "IdempotencyViolationCount": idem_viol,
            "SideEffectBudgetOverrun": overrun, "HallucinatedRefRate": halluc}


def metrics_d5(df: pd.DataFrame) -> dict:
    """长程一致性。Contradiction：同一 success_assertion_id 先后出现 pass 与 fail。"""
    def flip(t: pd.DataFrame) -> bool:
        r = t[t.success_assertion_id.notna()].drop_duplicates(
            ["success_assertion_id", "turn_idx"])
        return bool(r.groupby("success_assertion_id").assertion_result.nunique().gt(1).any())
    g = df.sort_values("turn_idx").groupby(TRAJ_KEYS)
    contra = float(g.apply(flip, include_groups=False).mean())
    # Constraint Retention Accuracy：正式版比对任务约束清单在后续 turn 的复读命中率（此处需外部 constraints 列，给 NaN 占位防虚报）
    retain = float("nan")
    drift = float(g.apply(lambda t: t.perturbation_epsilon.std(),
                          include_groups=False).mean())          # Context Drift Score（代理口径）
    stability = 1.0 - float(g.tool_name.nunique().mean()
                            / max(1, df.tool_name.nunique()))     # Plan Stability Index
    return {"CrossTurnContradictionRate": contra,
            "ConstraintRetentionAccuracy": retain,
            "ContextDriftScore": drift, "PlanStabilityIndex": stability}


def metrics_d6(df: pd.DataFrame) -> dict:
    pt = per_trajectory(df)
    solved = pt[pt.success == 1]
    wait = float(df.latency_ms.sum()
                 / max(1e-9, (df.ts_end.max() - df.ts_start.min()) * 1000.0))  # Tool Wait Time 占比
    sr = sr_from_traces(df)
    return {"StepsToSolutionP95": float(solved.steps.quantile(0.95)) if len(solved) else float("nan"),
            "CostPerSolvedTask": float(solved.cost_usd.mean()) if len(solved) else float("nan"),
            "ToolWaitTimeShare": min(wait, 1.0),
            "CostNormalizedSuccess": sr / max(1e-9, float(pt.cost_usd.mean())),
            "OverheadRatio": float((pt.tokens_total.mean()) / max(1.0, float((df.request_bytes // 4).sum())))}


def trace_determinism_score(df: pd.DataFrame) -> float:
    """同 (task_id, seed, epsilon) 两两轨迹工具序列的最长公共子序列比例均值
    （结构相似，非 bit-exact——LLM 服务端漂移由 σ_SR 体现）。限量 50×50 防爆炸。"""
    seqs = (df.sort_values("turn_idx")
            .groupby(["run_id", "trial_id", "task_id", "seed"]).tool_name.apply(list))
    keys = list(seqs.index)
    sims = []
    for i in range(min(50, len(keys))):
        for j in range(i + 1, min(50, len(keys))):
            a, b = seqs[keys[i]], seqs[keys[j]]
            m = [[0]*(len(b)+1) for _ in range(len(a)+1)]
            for x in range(len(a)-1, -1, -1):
                for y in range(len(b)-1, -1, -1):
                    m[x][y] = (m[x+1][y+1]+1 if a[x] == b[y]
                               else max(m[x+1][y], m[x][y+1]))
            sims.append(m[0][0] / max(len(a), len(b)))
    return float(np.mean(sims)) if sims else 1.0


def metrics_d7(df: pd.DataFrame) -> dict:
    pt = per_trajectory(df)
    sr_by_seed = pt.groupby("seed").success.mean()
    sigma = float(sr_by_seed.std(ddof=1)) if len(sr_by_seed) > 1 else 0.0   # σ_SR
    last = df.loc[df.groupby(TRAJ_KEYS).turn_idx.idxmax()]
    term = last.groupby(["run_id", "task_id"]).terminal_state_diff.nunique()
    consistency = float((term == 1).mean())                     # Terminal State Consistency
    det = trace_determinism_score(df)
    env = pt.groupby("run_id").success.mean()
    transfer = float(env.max() - env.min()) if len(env) > 1 else 0.0  # Cross-Env Transfer Gap
    return {"sigma_SR": sigma, "TerminalStateConsistency": consistency,
            "TraceDeterminismScore": det, "CrossEnvTransferGap": transfer}


ALL_METRICS: dict[str, Callable[..., dict]] = {
    "D1": metrics_d1, "D2": metrics_d2, "D3": metrics_d3, "D4": metrics_d4,
    "D5": metrics_d5, "D6": metrics_d6, "D7": metrics_d7,
}


def compute_all(df: pd.DataFrame, out_dir: str | Path) -> dict:
    """03 的主入口：全指标 dict 写 metric_summary.json，per_trace 写 parquet/csv。"""
    summary = {dim: fn(df) for dim, fn in ALL_METRICS.items()}
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "metric_summary.json").write_text(json.dumps(summary, indent=2, default=float))
    pt = per_trajectory(df)
    try:
        pt.to_parquet(out / "per_trace.parquet", index=False)
    except Exception:                                            # 无 pyarrow 退回 csv
        pt.to_csv(out / "per_trace.csv", index=False)
    return summary


# =====================================================================
# 片段 5：稳健性曲线绘图（04_robustness_curves）
# =====================================================================
def plot_degradation(per_trace: pd.DataFrame, out_prefix: str,
                     tau: float = 0.5, n_boot: int = 500, seed: int = 7) -> str:
    """per_trace 需含列: agent_name, epsilon, success(0/1)。
    SR vs ε 曲线，按 agent 分组着色，bootstrap 95% CI 阴影，breakdown 竖线。"""
    import matplotlib
    matplotlib.use("Agg")                        # 必须在 pyplot import 之前
    import matplotlib.pyplot as plt
    pt = per_trace.copy()
    if "agent_name" not in pt.columns:
        pt["agent_name"] = "unnamed"             # 兜底，保证片段自包含可跑
    rng = np.random.default_rng(seed)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for agent, sub in pt.groupby("agent_name"):
        eps_grid = np.sort(sub.epsilon.unique())
        mean, lo, hi = [], [], []
        for e in eps_grid:
            s = sub.loc[sub.epsilon == e, "success"].to_numpy()
            if len(s) == 0:
                mean += [np.nan]; lo += [np.nan]; hi += [np.nan]; continue
            boots = [rng.choice(s, size=len(s), replace=True).mean() for _ in range(n_boot)]
            mean += [s.mean()]; lo += [np.percentile(boots, 2.5)]; hi += [np.percentile(boots, 97.5)]
        ax.plot(eps_grid, mean, marker="o", label=agent)
        ax.fill_between(eps_grid, lo, hi, alpha=0.2)
        clean = next((m for e, m in zip(eps_grid, mean) if e == 0.0), np.nan)
        if clean and clean > 0:
            below = [e for e, m in zip(eps_grid, mean) if m < tau * clean]
            if below:
                ax.axvline(min(below), ls="--", lw=1, color="gray")
    ax.set_xlabel("perturbation strength epsilon"); ax.set_ylabel("Success Rate")
    ax.set_title("Degradation curves (core object: slope, not level)")
    ax.legend(); fig.tight_layout()
    fig.savefig(f"{out_prefix}.pdf"); fig.savefig(f"{out_prefix}.png", dpi=150)
    plt.close(fig)                               # 防 figure 泄漏
    return f"{out_prefix}.pdf"


def plot_failure_modes(per_trace: pd.DataFrame, out_prefix: str) -> str:
    """Failure Mode Distribution 堆叠条形图（按 ε 档的错误类别占比）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pt = per_trace.copy()
    if "failure_mode" not in pt.columns:
        pt["failure_mode"] = "unknown"
    tab = (pt.groupby(["epsilon", "failure_mode"]).size()
           .unstack(fill_value=0)
           .pipe(lambda d: d.div(d.sum(axis=1), axis=0)))
    ax = tab.plot(kind="bar", stacked=True, colormap="tab20", figsize=(7, 4))
    ax.set_xlabel("epsilon"); ax.set_ylabel("share of failures")
    ax.set_title("Failure Mode Distribution")
    fig = ax.get_figure(); fig.tight_layout()
    fig.savefig(f"{out_prefix}.pdf"); fig.savefig(f"{out_prefix}.png", dpi=150)
    plt.close(fig)
    return f"{out_prefix}.pdf"


# =====================================================================
# 片段 6：统计检验（05_stats_tests）
# =====================================================================
def paired_wilcoxon(per_trace: pd.DataFrame, agent_a: str, agent_b: str,
                    metric: str = "success") -> dict:
    """配对键 = (task_id, trial_id)：同任务同 trial 在两 agent 上的取值配对，
    任务难度差异被配对消掉。效应量：rank-biserial + Cohen's d（配对差版）。"""
    from scipy.stats import wilcoxon
    pt = per_trace.copy()
    if "agent_name" not in pt.columns:
        return {"n_pairs": 0, "stat": float("nan"), "p": float("nan"),
                "rank_biserial": float("nan"), "cohens_d": float("nan")}
    w = pt.pivot_table(index=["task_id", "trial_id"], columns="agent_name",
                       values=metric, aggfunc="mean")
    both = w.dropna(subset=[agent_a, agent_b])
    diff = (both[agent_a] - both[agent_b]).to_numpy(float)
    n = len(diff)
    if n < 6 or np.abs(diff).sum() == 0:
        return {"n_pairs": n, "stat": float("nan"), "p": float("nan"),
                "rank_biserial": float("nan"), "cohens_d": float("nan")}
    stat, p = wilcoxon(both[agent_a], both[agent_b], zero_method="wilcox")
    rb = 1.0 - 2.0 * float(stat) / (n * (n + 1))
    sd = diff.std(ddof=1)
    d = float(diff.mean() / sd) if sd > 0 else float("nan")
    return {"n_pairs": n, "stat": float(stat), "p": float(p),
            "rank_biserial": float(rb), "cohens_d": d}


def holm_bonferroni(pvals: list[float]) -> list[float]:
    """Holm 逐步校正：排序后 running_max_j<=i ((m-j)*p_j)，截断至 1。"""
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.empty(m); running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (m - rank) * pvals[idx])
        adj[idx] = min(running, 1.0)
    return adj.tolist()


def bootstrap_slope_ci(per_trace: pd.DataFrame, agent: str, tau: float = 0.5,
                       n_boot: int = 300, seed: int = 11) -> tuple[float, float, float]:
    """按 task_id 分层重采样轨迹 → 重算每条重采样的 degradation slope → 取 2.5/97.5 分位。"""
    rng = np.random.default_rng(seed)
    sub = per_trace[per_trace.agent_name == agent]
    tasks = [g for _, g in sub.groupby("task_id")]
    slopes = []
    for _ in range(n_boot):
        boot = pd.concat([g.iloc[rng.integers(0, len(g), len(g))] for g in tasks])
        by_eps = boot.groupby("epsilon").success.mean().sort_index()
        if len(by_eps) >= 2:
            slopes.append(float(np.polyfit(by_eps.index.to_numpy(float),
                                           by_eps.to_numpy(float), 1)[0]))
    if not slopes:
        return (float("nan"), float("nan"), float("nan"))
    arr = np.array(slopes)
    return (float(arr.mean()), float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5)))


def run_all_tests(per_trace: pd.DataFrame, out_csv: str) -> pd.DataFrame:
    """批量 (agent pair × metric) Wilcoxon + Holm 校正 + 效应量，限量打印。"""
    agents = sorted(per_trace.agent_name.unique()) if "agent_name" in per_trace else []
    rows = []
    for i, a in enumerate(agents):
        for b in agents[i+1:]:
            for metric in ("success", "cost_usd", "steps"):
                if metric in per_trace.columns:
                    rows.append({"pair": f"{a}-{b}", "metric": metric,
                                 **paired_wilcoxon(per_trace, a, b, metric)})
    res = pd.DataFrame(rows)
    if len(res):
        res["p_holm"] = holm_bonferroni(res["p"].fillna(1.0).tolist())
    res.to_csv(out_csv, index=False)
    print(f"[snippet6] tests -> {out_csv}, shape={res.shape}")
    return res.head(20)                          # cell 里只限量打印，全量在文件


# =====================================================================
# 片段 7：MVP 规模估算工具（02 启动前的硬闸）
# =====================================================================
def estimate_mvp_scale(cfg: RunConfig, avg_tokens_per_step: int = 1200,
                       usd_per_1k_tokens: float = 0.006,
                       avg_steps_per_trial: float = 10.0) -> dict:
    combos = sum(len(g.operators) * len(g.eps_grid) for g in cfg.operator_grids)
    n_trials = len(cfg.seeds) * cfg.trials_per_cell
    n_trajs = len(cfg.agents) * cfg.n_tasks * combos * n_trials
    n_tokens = n_trajs * avg_steps_per_trial * avg_tokens_per_step
    usd = n_tokens / 1000.0 * usd_per_1k_tokens
    wallclock_h = n_trajs * cfg.wallclock_per_trial_sec / 3600.0
    return {"combos": combos, "n_trajectories": n_trajs, "est_tokens": int(n_tokens),
            "est_usd": round(usd, 2), "est_wallclock_hours": round(wallclock_h, 1),
            "over_budget": usd > cfg.cost_budget_usd or n_tokens > cfg.token_budget}


def gate_or_raise(cfg: RunConfig) -> None:
    est = estimate_mvp_scale(cfg)
    print(json.dumps(est, indent=2))
    if est["over_budget"]:
        raise RuntimeError(f"MVP 估算超预算（${est['est_usd']} / "
                           f"{est['est_wallclock_hours']}h），请先减 trial/ε 档/算子网格。")


# =====================================================================
# 接口桩：无法在本 notebook 真实执行的部分
# =====================================================================
def llm_agent_rollout(task: dict, seed: int, max_turns: int) -> list[dict]:
    """TODO 接口桩：调用付费 LLM API 的多轮代理 rollout（需环境变量中的 API key）。
    仅在 02 的后台 runner 中启用，不放 notebook cell。"""
    raise NotImplementedError("paid LLM API stub")


def nixos_test_vm_exec(script: str) -> str:
    """TODO 接口桩：起 nixos-test VM。已核实 block()/unblock()/crash() 可用；
    VirtioTestDriver / create_block_snapshot / rollback_to_snapshot 不存在——
    状态回滚须自建 qcow2 overlay（qemu-img create -f qcow2 -b base.qcow2 ov.img，
    回滚=丢弃 overlay；工程推断，先小规模验证）。Nix flake 官方 Experimental。"""
    raise NotImplementedError("requires local qemu/nix + privileged setup")


# =====================================================================
# 自检 demo：合成 trace → 走通 校验/注入/指标/绘图/检验/估算 全链路
# =====================================================================
def _synthetic_df(n_agents: int = 2, n_tasks: int = 6, n_seeds: int = 3,
                  eps_grid: tuple = (0.0, 0.1, 0.25, 0.5)) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows = []
    for ai, agent in enumerate(["react_base", "reflexion_lite"][:n_agents]):
        for tid in range(n_tasks):
            for seed in range(n_seeds):
                for eps in eps_grid:
                    turns = 6
                    base_sr = 0.9 - 0.12 * ai          # A 略强
                    succ_prob = max(0.0, base_sr - (0.55 + 0.25 * ai) * eps)
                    ok = rng.random() < succ_prob
                    for t in range(turns):
                        inj = eps > 0 and rng.random() < eps
                        err = "TimeoutError" if (inj and rng.random() < 0.5) else None
                        rows.append(make_event(
                            run_id="demo", trial_id=tid * n_seeds + seed, seed=seed,
                            task_id=f"task{tid}", turn_idx=t,
                            tool_name=rng.choice(["search", "calc", "fs_write"]),
                            latency_ms=float(rng.uniform(20, 300)),
                            http_status=500 if err else 200, error_class=err,
                            injected_perturbation_id=("net_timeout" if inj else None),
                            perturbation_epsilon=eps if inj else 0.0,
                            retry_of=(t - 1) if (err and t > 0 and rng.random() < 0.6) else None,
                            side_effect_flag=bool(rng.random() < 0.3),
                            resource_id=f"res{tid}" if rng.random() < 0.5 else None,
                            cost_usd=float(rng.uniform(0.001, 0.05)),
                            terminal_state_diff=(None if ok else "diff:extra_files"),
                            success_assertion_id=f"a{tid}_{rng.integers(0,3)}",
                            assertion_result="pass" if (ok and t == turns - 1)
                                             else ("fail" if (not ok and t == turns - 1) else None),
                            ts_start=float(t), ts_end=float(t) + 0.3))
        # 补 agent 列需要逐事件携带；用 tool_name 之外新增列的方式：
    df = pd.DataFrame(rows)
    # 合成数据里 agent 信息塞进 run_id 之外的自定义处理：直接复制两份并打标签
    parts = []
    for agent in ["react_base", "reflexion_lite"][:n_agents]:
        d = df.copy(); d["agent_name"] = agent; parts.append(d)
    return pd.concat(parts, ignore_index=True)


def selfcheck(tmpdir: str = "/tmp/robust_demo") -> None:
    df = _synthetic_df()
    pt = per_trajectory(df)
    pt["agent_name"] = pt.merge(df[["run_id", "trial_id", "task_id", "seed", "agent_name"]]
                                 .drop_duplicates(TRAJ_KEYS), on=TRAJ_KEYS)["agent_name"].to_numpy()
    summ = compute_all(df, f"{tmpdir}/metrics")
    print("[snippet4] D2:", json.dumps(summ["D2"], default=float)[:200])
    pdf = plot_degradation(pt, f"{tmpdir}/figures/degradation_curves")
    pdf2 = plot_failure_modes(pt, f"{tmpdir}/figures/failure_mode_stack")
    print(f"[snippet5] figures -> {pdf}, {pdf2}")
    res = run_all_tests(pt, f"{tmpdir}/stats/tests_table.csv")
    print(res[["pair", "metric", "p", "p_holm", "rank_biserial"]].head(6))
    ci = bootstrap_slope_ci(pt, "react_base", n_boot=60)
    print(f"[snippet6] slope CI react_base = {ci}")
    gate_or_raise(RunConfig())
    print("[snippet7] gate passed")


if __name__ == "__main__":
    demo_config_roundtrip()
    demo_validation_rejects()
    demo_scheduler_determinism()
    selfcheck()
    print("ALL SNIPPET SELF-CHECKS DONE.")
