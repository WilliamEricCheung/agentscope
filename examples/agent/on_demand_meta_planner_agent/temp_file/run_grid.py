"""run_grid.py — 02_run_experiment 引用的后台 runner 参考实现。

设计要点（对应 notebook_plan.md C.2）：
- 由 notebook 用 subprocess.Popen(start_new_session=True) 拉起，stdout/stderr 重定向 logs/run.log；
- 每完成一条轨迹原子重写 _manifest.json → 断点续跑；
- 全部结束后写 logs/run.done 哨兵，03 据此拒绝在"采集不完整"时出指标；
- 真实 LLM rollout / nixos VM 是接口桩（llm_agent_rollout），默认走合成 echo agent 干跑。

用法: python run_grid.py --config config/run_config.yaml \
      --registry perturbations.yaml --out traces/raw/<run_id> [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))          # 允许与 code_snippets.py 同目录运行
from code_snippets import (RunConfig, PerturbationScheduler, load_registry,
                           instrumented_tool_call, llm_agent_rollout, make_event,
                           append_event)


def atomic_write_json(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    tmp.replace(path)                                    # 幂等 + 防半截文件


def echo_tool(args: dict) -> dict:                      # dry-run 用的假工具
    time.sleep(args.get("_sim_latency_ms", 5) / 1000.0)
    return {"ok": True, "id": f"res-{args.get('q', 'x')}", "value": 42,
            "extra": "y", "note": "echo"}


def run_trial(cfg: RunConfig, sched: PerturbationScheduler, agent: str, task_id: str,
              trial_id: int, seed: int, op_name: str, eps: float,
              out_dir: Path, rejected: Path, dry_run: bool) -> Path:
    """单条轨迹：n_turns 次被扰动/未扰动的 tool call，逐事件落 JSONL。"""
    fname = out_dir / f"{task_id}__trial{trial_id}__seed{seed}.jsonl"
    if fname.exists() and fname.stat().st_size > 0:     # 断点续跑：已完成则跳过
        return fname
    n_steps = cfg.max_turns // 4 or 6
    plan = sched.plan(seed=seed * 7919 + hash((agent, task_id, op_name)) % 10_000,
                      n_steps=n_steps)
    # 强制本条轨迹的注入档为 (op_name, eps)，其余步不注入 —— 保证网格可解释
    ops_by_kind = {o.kind: o for o in sched.registry}
    forced = [(ops_by_kind.get(op_name, sched.registry[0]), eps)] + [
        (sched.registry[0], 0.0) for _ in range(n_steps - 1)]
    tool = echo_tool
    traj = out_dir / f"{task_id}__trial{trial_id}__seed{seed}.jsonl"
    for i in range(n_steps):
        if not dry_run:
            raise SystemExit("真实 rollout 需实现 llm_agent_rollout 接口桩后启用（付费 API）")
        resp = instrumented_tool_call(
            tool, {"q": f"{task_id}-{i}"}, forced, i, cfg.run_id, trial_id, seed,
            task_id, str(traj), str(rejected))
        _ = resp
    # 收尾：终态与断言结果（dry-run 简化：最后一步记 pass）
    last = make_event(run_id=cfg.run_id, trial_id=trial_id, seed=seed, task_id=task_id,
                      turn_idx=n_steps, tool_name="finalize",
                      tool_args_hash="f"*12, request_bytes=0, response_bytes=0,
                      latency_ms=0.0, http_status=200, error_class=None,
                      injected_perturbation_id=None, perturbation_epsilon=0.0,
                      retry_of=None, side_effect_flag=False, resource_id=None,
                      tokens_in=0, tokens_out=0, cost_usd=0.0,
                      terminal_state_diff="no_diff", success_assertion_id=f"{task_id}_a0",
                      assertion_result="pass", ts_start=time.time(), ts_end=time.time())
    append_event(traj, last, rejected)
    return traj


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--registry", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    cfg = RunConfig.from_yaml(a.config)
    ops, _ = load_registry(a.registry)
    sched = PerturbationScheduler(ops, [0.0, 0.1, 0.25, 0.5])
    out_dir = Path(a.out); out_dir.mkdir(parents=True, exist_ok=True)
    rejected = out_dir.parent / "rejected" / cfg.run_id / "bad_events.jsonl"
    manifest = out_dir / "_manifest.json"
    done = json.loads(manifest.read_text()).get("completed", []) if manifest.exists() else []

    combos = [(agent, task_id, trial, seed, op.kind, eps)
              for agent in cfg.agents
              for task_id in [f"task{i}" for i in range(cfg.n_tasks)]
              for seed in cfg.seeds
              for trial in range(cfg.trials_per_cell)
              for g in cfg.operator_grids for op in g.operators
              for eps in g.eps_grid]
    total = len(combos)
    print(f"[runner] run_id={cfg.run_id} combos={total} already_done={len(done)}", flush=True)

    for idx, (agent, task_id, trial, seed, kind, eps) in enumerate(combos):
        key = f"{agent}|{task_id}|{trial}|{seed}|{kind}|{eps}"
        if key in done:
            continue
        run_trial(cfg, sched, agent, task_id, trial, seed, kind, eps,
                  out_dir, rejected, dry_run=a.dry_run)
        done.append(key)
        atomic_write_json(manifest, {"run_id": cfg.run_id, "total": total,
                                     "completed": done})
        if idx % 25 == 0:
            print(f"[runner] {idx+1}/{total}", flush=True)

    (out_dir.parent.parent / "logs").mkdir(parents=True, exist_ok=True)
    (out_dir.parent.parent / "logs" / "run.done").write_text(cfg.run_id)
    print("[runner] DONE -> logs/run.done", flush=True)


if __name__ == "__main__":
    main()
