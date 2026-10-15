# -*- coding: utf-8 -*-
"""Rerun one Paper Search dialogue at QPS=1 and QPS=20, then plot breakdown.

This script selects a paper_search task from
laplace/mcp_dataset/laplace_tasks_single_runner_format.json, executes two
single-run on-demand requests via run_real_e2e_latency_experiment.py, and
creates a breakdown figure by calling plot_time_breakdown.py.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parents[4]
_DEFAULT_TASK_FILE = _REPO_ROOT / "laplace" / "mcp_dataset" / "laplace_tasks_single_runner_format.json"
_REAL_RUNNER = _THIS_DIR / "run_real_e2e_latency_experiment.py"
_BREAKDOWN_PLOTTER = _THIS_DIR / "plot_time_breakdown.py"
_DEFAULT_OUT_ROOT = _THIS_DIR / "paper_search_remeasure"


@dataclass
class PaperTask:
    """Paper Search task payload extracted from task dataset.

    Args:
        task_id (`str`):
            The selected task id.
        server_name (`str`):
            The MCP server name.
        user_request (`str`):
            The user prompt used for single-run replay.
        trace_replay_instruction (`str`):
            Additional instruction carried into replay field.

    Returns:
        `None`:
            This is a data container.
    """

    task_id: str
    server_name: str
    user_request: str
    trace_replay_instruction: str


def _load_task_json(task_file: Path) -> dict[str, Any]:
    """Load task file JSON.

    Args:
        task_file (`Path`):
            Path to laplace task dataset.

    Returns:
        `dict[str, Any]`:
            Parsed JSON object.
    """

    with task_file.open("r", encoding="utf-8") as file:
        return json.load(file)


def _pick_paper_task(task_file: Path, task_id: str) -> PaperTask:
    """Pick one Paper Search dialogue from dataset.

    Args:
        task_file (`Path`):
            Path to laplace task dataset.
        task_id (`str`):
            Preferred task id, usually paper_search_001.

    Returns:
        `PaperTask`:
            Selected task payload used for rerun.
    """

    payload = _load_task_json(task_file)
    server_tasks = payload.get("server_tasks")
    if not isinstance(server_tasks, list):
        raise ValueError(f"Invalid task file schema: missing list field server_tasks in {task_file}")

    paper_entries: list[dict[str, Any]] = []
    for server_row in server_tasks:
        if str(server_row.get("server_name")) != "Paper Search":
            continue
        tasks = server_row.get("tasks") or []
        for task in tasks:
            if isinstance(task, dict):
                paper_entries.append(task)

    if not paper_entries:
        raise ValueError(f"No Paper Search tasks found in {task_file}")

    selected: dict[str, Any] | None = None
    for task in paper_entries:
        if str(task.get("task_id")) == task_id:
            selected = task
            break
    if selected is None:
        selected = paper_entries[0]

    replay_text = str(selected.get("task_description") or "")
    user_text = str(selected.get("fuzzy_description") or replay_text)

    if not user_text.strip():
        raise ValueError(f"Selected task has empty user request: {selected.get('task_id')}")

    return PaperTask(
        task_id=str(selected.get("task_id") or task_id),
        server_name="Paper Search",
        user_request=user_text,
        trace_replay_instruction=replay_text,
    )


def _run_single_request(
    python_exe: str,
    qps: int,
    repeat_id: int,
    request_id: int,
    attempt_id: int,
    task: PaperTask,
    output_dir: Path,
    model_name: str,
    planner_max_iters: int,
    stream_interval_tokens: int,
) -> None:
    """Run one on-demand single request for specified qps.

    Args:
        python_exe (`str`):
            Python executable path.
        qps (`int`):
            QPS value for this request.
        repeat_id (`int`):
            Repeat index.
        request_id (`int`):
            Request index.
        attempt_id (`int`):
            Attempt index.
        task (`PaperTask`):
            Selected task payload.
        output_dir (`Path`):
            Request output directory.
        model_name (`str`):
            Model passed to runner.
        planner_max_iters (`int`):
            Planner max iterations.
        stream_interval_tokens (`int`):
            Stream interval tokens.

    Returns:
        `None`:
            Writes result and timing files to output_dir.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    output_json = output_dir / "result.json"

    cmd = [
        python_exe,
        str(_REAL_RUNNER),
        "--single-run",
        "--mode",
        "on_demand",
        "--qps",
        str(qps),
        "--repeat-id",
        str(repeat_id),
        "--request-id",
        str(request_id),
        "--attempt-id",
        str(attempt_id),
        "--trace-id",
        task.task_id,
        "--user-request",
        task.user_request,
        "--trace-replay-instruction",
        task.trace_replay_instruction,
        "--temp-dir",
        str(output_dir),
        "--output-json",
        str(output_json),
        "--model-name",
        model_name,
        "--planner-max-iters",
        str(planner_max_iters),
        "--stream-interval-tokens",
        str(stream_interval_tokens),
    ]

    print("[run]", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=str(_REPO_ROOT))

    # Strict guard: this remeasure pipeline must stay on on-demand mode only.
    result_payload = json.loads(output_json.read_text(encoding="utf-8"))
    if str(result_payload.get("mode")) != "on_demand":
        raise RuntimeError(f"Unexpected mode in {output_json}: {result_payload.get('mode')}")


def _plot_breakdown(real_e2e_tmp_dir: Path, output_prefix: Path, llm_context_ratio: float) -> None:
    """Generate time breakdown chart based on newly generated samples.

    Args:
        real_e2e_tmp_dir (`Path`):
            Directory containing per-request results.
        output_prefix (`Path`):
            Output path prefix for png/pdf.
        llm_context_ratio (`float`):
            Prefill ratio in LLM pre-tool phase.

    Returns:
        `None`:
            Saves breakdown figures.
    """

    cmd = [
        sys.executable,
        str(_BREAKDOWN_PLOTTER),
        "--real-e2e-tmp-dir",
        str(real_e2e_tmp_dir),
        "--target-group-name",
        "laplace_paper_search",
        "--llm-context-ratio",
        str(llm_context_ratio),
        "--output-prefix",
        str(output_prefix),
    ]
    print("[plot]", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=str(_REPO_ROOT))


def main() -> None:
    """CLI entrypoint.

    Args:
        None:
            No positional args.

    Returns:
        `None`:
            Executes rerun and plotting pipeline.
    """

    parser = argparse.ArgumentParser(
        description="Remeasure Paper Search with real single-run requests (QPS=1/20).",
    )
    parser.add_argument("--task-file", type=Path, default=_DEFAULT_TASK_FILE)
    parser.add_argument("--task-id", type=str, default="paper_search_001")
    parser.add_argument("--output-root", type=Path, default=_DEFAULT_OUT_ROOT)
    parser.add_argument("--run-tag", type=str, default="")
    parser.add_argument("--repeat-id", type=int, default=0)
    parser.add_argument("--request-id", type=int, default=0)
    parser.add_argument("--attempt-id", type=int, default=0)
    parser.add_argument("--model-name", type=str, default="qwen3-max")
    parser.add_argument("--planner-max-iters", type=int, default=10)
    parser.add_argument("--stream-interval-tokens", type=int, default=20)
    parser.add_argument("--llm-context-ratio", type=float, default=0.45)
    parser.add_argument(
        "--skip-plot",
        action="store_true",
        help="Only run requests and skip breakdown plotting.",
    )

    args = parser.parse_args()

    if not _REAL_RUNNER.exists():
        raise FileNotFoundError(f"Runner not found: {_REAL_RUNNER}")
    if not _BREAKDOWN_PLOTTER.exists() and not args.skip_plot:
        raise FileNotFoundError(f"Plotter not found: {_BREAKDOWN_PLOTTER}")
    if not args.task_file.exists():
        raise FileNotFoundError(f"Task file not found: {args.task_file}")
    if not (0.0 < args.llm_context_ratio < 1.0):
        raise ValueError("--llm-context-ratio must be in (0, 1)")

    task = _pick_paper_task(args.task_file, args.task_id)

    run_tag = args.run_tag.strip() or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = args.output_root / run_tag
    run_dir.mkdir(parents=True, exist_ok=True)

    qps1_dir = run_dir / f"on_demand_qps1_r{args.repeat_id}_req{args.request_id}"
    qps20_dir = run_dir / f"on_demand_qps20_r{args.repeat_id}_req{args.request_id}"

    manifest = {
        "task_file": str(args.task_file),
        "task_id": task.task_id,
        "server_name": task.server_name,
        "output_run_dir": str(run_dir),
        "qps_values": [1, 20],
        "repeat_id": args.repeat_id,
        "request_id": args.request_id,
        "attempt_id": args.attempt_id,
        "model_name": args.model_name,
        "planner_max_iters": args.planner_max_iters,
        "stream_interval_tokens": args.stream_interval_tokens,
        "mode": "on_demand",
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    _run_single_request(
        python_exe=sys.executable,
        qps=1,
        repeat_id=args.repeat_id,
        request_id=args.request_id,
        attempt_id=args.attempt_id,
        task=task,
        output_dir=qps1_dir,
        model_name=args.model_name,
        planner_max_iters=args.planner_max_iters,
        stream_interval_tokens=args.stream_interval_tokens,
    )
    _run_single_request(
        python_exe=sys.executable,
        qps=20,
        repeat_id=args.repeat_id,
        request_id=args.request_id,
        attempt_id=args.attempt_id,
        task=task,
        output_dir=qps20_dir,
        model_name=args.model_name,
        planner_max_iters=args.planner_max_iters,
        stream_interval_tokens=args.stream_interval_tokens,
    )

    if not args.skip_plot:
        output_prefix = run_dir / "time_breakdown_paper_search"
        _plot_breakdown(
            real_e2e_tmp_dir=run_dir,
            output_prefix=output_prefix,
            llm_context_ratio=args.llm_context_ratio,
        )

    print(f"[done] run dir: {run_dir}")
    print(f"[done] task id: {task.task_id}")


if __name__ == "__main__":
    main()
