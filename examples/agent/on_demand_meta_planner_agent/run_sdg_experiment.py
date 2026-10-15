# -*- coding: utf-8 -*-
"""Run one-click SDG A/B experiment for on-demand meta planner.

This script is designed for A/B comparison of SDG optimization in a realistic
multi-turn planning scenario:

- A: C1 only (prompt prewarm on, predictive prewarm off)
- B: C1 + C2 (prompt prewarm on, predictive prewarm on)

This script runs the following pipeline automatically:

1. Run baseline mode: c1_only
2. Run SDG mode: c1_c2
3. Build one-page comparison report

CLI output is intentionally minimal: only the final report path.
"""

from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
import importlib
import json
import os
import statistics
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from agentscope.agent import ReActAgent
from agentscope.mcp import (
    MCPLaplaceController,
    MCPLaplaceControllerConfig,
    MCPPrewarmHybridRouter,
    load_laplace_registration_configs,
    build_mcp_speculative_executor,
)
from agentscope.message import Msg
from agentscope.plan import PlanNotebook
from agentscope.tool import Toolkit


_MODE_C1_ONLY = "c1_only"
_MODE_C1_C2 = "c1_c2"
_MODE_C2_ONLY = "c2_only"
_MODE_ON_DEMAND = "on_demand"
_MODE_CHOICES = (
    _MODE_C1_ONLY,
    _MODE_C1_C2,
    _MODE_C2_ONLY,
    _MODE_ON_DEMAND,
)
_DEFAULT_TURN_SCRIPT_FILE = (
    Path(__file__).resolve().parent / "multiturn_plan_dialogue_script.json"
)
_DEFAULT_TURN_SCRIPTS_DIR = Path(__file__).resolve().parent / "dialogue_scripts"
_TEMP_FILE_DIR = Path(__file__).resolve().parent / "temp_file"

_FIXED_TURNS = [
    (
        "Please decompose the task into 4 subtasks, and for each subtask "
        "explain which tool group is likely needed. Do not execute yet."
    ),
    (
        "Now execute subtask 1 and 2: find today's weather in Beijing and "
        "provide one concise citation-style source note."
    ),
    (
        "Continue with subtask 3: inspect the agentscope GitHub repository, "
        "find one recently closed issue, and report title plus closed time "
        "with link."
    ),
    (
        "Finish subtask 4: produce a final concise summary with risks and "
        "next-step suggestions."
    ),
]


def _resolve_mcp_lifecycle_dir() -> Path:
    """Resolve MCP lifecycle state directory used by helper daemon.

    Returns:
        `Path`:
            Lifecycle state directory path.
    """
    configured = os.getenv("AGENTSCOPE_MCP_LIFECYCLE_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()

    return Path(__file__).resolve().parents[4] / "laplace" / "mcp_lifecycle"


def _ensure_temp_file_dir() -> Path:
    """Ensure temp_file directory exists and return path.

    Returns:
        `Path`:
            temp_file directory path.
    """
    _TEMP_FILE_DIR.mkdir(parents=True, exist_ok=True)
    return _TEMP_FILE_DIR


@contextmanager
def _temporary_cwd(target_dir: Path):
    """Temporarily switch current working directory.

    Args:
        target_dir (`Path`):
            Target current working directory.
    """
    previous = Path.cwd()
    os.chdir(target_dir)
    try:
        yield
    finally:
        os.chdir(previous)


def _cleanup_experiment_mcp_runtime(registrations: list[Any]) -> None:
    """Force-remove experiment MCP containers and persisted lifecycle state.

    Args:
        registrations (`list[Any]`):
            Registration configs used by this experiment run.

    Returns:
        `None`:
            Runtime state is cleaned in-place.
    """
    container_names = sorted(
        {
            str(reg.server_config.container_name)
            for reg in registrations
            if getattr(reg, "server_config", None) is not None
        },
    )

    for container_name in container_names:
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    lifecycle_dir = _resolve_mcp_lifecycle_dir()
    if lifecycle_dir.exists():
        for container_name in container_names:
            safe_name = container_name.replace(os.sep, "_").replace(":", "_")
            state_file = lifecycle_dir / f"{safe_name}.json"
            if state_file.exists():
                state_file.unlink()


def _load_experiment_registrations() -> list[Any]:
    """Load MCP registrations used by SDG planner experiments.

    Returns:
        `list[Any]`:
            Filtered registration list for browser/github groups.
    """
    all_registrations = load_laplace_registration_configs()
    requested_names_raw = os.getenv(
        "AGENTSCOPE_EXPERIMENT_SERVER_NAMES",
        "",
    ).strip()
    requested_names: set[str] | None = None
    if requested_names_raw:
        try:
            payload = json.loads(requested_names_raw)
            if isinstance(payload, list):
                requested_names = {
                    str(item).strip()
                    for item in payload
                    if str(item).strip()
                }
        except json.JSONDecodeError:
            requested_names = None
        if requested_names is None:
            requested_names = {
                item.strip()
                for item in requested_names_raw.split(",")
                if item.strip()
            }

    registrations = []
    for registry_name, registration in all_registrations.items():
        if requested_names is None:
            enabled = registration.group_name in {
                "browser_tools",
                "github_tools",
            }
        else:
            enabled = bool(
                requested_names
                & {
                    str(registry_name).strip(),
                    str(registration.group_name).strip(),
                    str(getattr(registration, "server_name", "")).strip(),
                },
            )
        if enabled:
            registrations.append(registration)
    if "GITHUB_PERSONAL_ACCESS_TOKEN" not in os.environ:
        registrations = [
            reg
            for reg in registrations
            if reg.group_name != "github_tools"
        ]
    if requested_names is None and not any(
        reg.group_name == "browser_tools"
        for reg in registrations
    ):
        raise ValueError(
            "`browser_tools` registration is missing in laplace_mcp_manifest.json.",
        )
    if not registrations:
        raise ValueError(
            "No MCP registrations match AGENTSCOPE_EXPERIMENT_SERVER_NAMES.",
        )
    return registrations


def _cleanup_non_result_artifacts(
    output_dir: Path,
    keep_paths: set[Path],
) -> None:
    """Remove non-result files in output directory.

    Args:
        output_dir (`Path`):
            Result directory.
        keep_paths (`set[Path]`):
            Absolute file paths that should be preserved.

    Returns:
        `None`:
            Files outside the keep set are removed.
    """
    if not output_dir.exists():
        return

    resolved_keep = {path.resolve() for path in keep_paths}
    for file_path in output_dir.iterdir():
        if not file_path.is_file():
            continue
        if file_path.resolve() in resolved_keep:
            continue
        file_path.unlink()


@dataclass
class RunMetrics:
    """Aggregated metrics extracted from on-demand worker timing logs.

    Args:
        run_mode (`str`):
            Experiment mode identifier.
        worker_calls (`int`):
            Number of worker invocations recorded.
        avg_wait_ms (`float | None`):
            Mean wait after activation.
        p50_wait_ms (`float | None`):
            Median wait after activation.
        p95_wait_ms (`float | None`):
            95th percentile wait after activation.
        cold_starts (`int`):
            Count of cold starts.
        non_cold_starts (`int`):
            Count of non-cold starts.
        telemetry_prompt_route_calls (`int`):
            Sum of prompt route calls in controller telemetry.
        telemetry_predict_calls (`int`):
            Sum of predictive calls in controller telemetry.
        telemetry_schedule_attempts (`int`):
            Sum of candidate scheduling attempts.
        telemetry_schedule_accepted (`int`):
            Sum of accepted schedules.
        telemetry_executor_runs (`int`):
            Sum of executor runs.
        telemetry_executor_errors (`int`):
            Sum of executor errors.
        e2e_elapsed_ms (`float | None`):
            End-to-end elapsed time for one run.
    """

    run_mode: str
    worker_calls: int
    avg_wait_ms: float | None
    p50_wait_ms: float | None
    p95_wait_ms: float | None
    cold_starts: int
    non_cold_starts: int
    telemetry_prompt_route_calls: int
    telemetry_predict_calls: int
    telemetry_schedule_attempts: int
    telemetry_schedule_accepted: int
    telemetry_executor_runs: int
    telemetry_executor_errors: int
    e2e_elapsed_ms: float | None = None


def _default_output_dir() -> Path:
    """Return default output directory for this experiment.

    Returns:
        `Path`:
            Experiment output directory.
    """
    output_dir = Path(__file__).resolve().parent / "result_sdg"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _next_run_path(output_dir: Path, mode: str, ext: str) -> Path:
    """Build next available artifact path.

    Args:
        output_dir (`Path`):
            Base output directory.
        mode (`str`):
            Run mode label.
        ext (`str`):
            File extension including dot.

    Returns:
        `Path`:
            Next available artifact path.
    """
    prefix = time.strftime("%m%d", time.localtime())
    index = 0
    while True:
        path = output_dir / f"multiturn_plan_{prefix}_{mode}_{index}{ext}"
        if not path.exists():
            return path
        index += 1


def _latest_run_path(output_dir: Path, mode: str, ext: str) -> Path | None:
    """Find latest existing run artifact path for one mode.

    Args:
        output_dir (`Path`):
            Base output directory.
        mode (`str`):
            Run mode label.
        ext (`str`):
            File extension including dot.

    Returns:
        `Path | None`:
            Latest existing path, or `None` when no artifact exists.
    """
    prefix = time.strftime("%m%d", time.localtime())
    latest: Path | None = None
    latest_index = -1
    pattern = f"multiturn_plan_{prefix}_{mode}_*{ext}"
    for path in output_dir.glob(pattern):
        stem = path.stem
        index_text = stem.rsplit("_", maxsplit=1)[-1]
        if not index_text.isdigit():
            continue
        index = int(index_text)
        if index > latest_index:
            latest_index = index
            latest = path
    return latest


def _sanitize_case_name(name: str) -> str:
    """Normalize one case name for directory usage.

    Args:
        name (`str`):
            Raw case name.

    Returns:
        `str`:
            Normalized case name.
    """

    cleaned = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in name)
    return cleaned.strip("_") or "case"


def _resolve_batch_turn_script_files(
    turn_script_files: list[str] | None,
    turn_script_dir: str | None,
    turn_script_glob: str | None,
) -> list[Path]:
    """Resolve multi-case turn script files.

    Args:
        turn_script_files (`list[str] | None`):
            Explicit script file paths.
        turn_script_dir (`str | None`):
            Script directory for glob search.
        turn_script_glob (`str | None`):
            Glob pattern under directory.

    Returns:
        `list[Path]`:
            Sorted unique script paths.
    """

    resolved: list[Path] = []
    seen: set[Path] = set()

    if turn_script_files:
        for item in turn_script_files:
            path = Path(item).expanduser().resolve()
            if path in seen:
                continue
            seen.add(path)
            resolved.append(path)

    if turn_script_dir or turn_script_glob:
        script_dir = (
            Path(turn_script_dir).expanduser().resolve()
            if turn_script_dir is not None
            else _DEFAULT_TURN_SCRIPTS_DIR
        )
        pattern = turn_script_glob or "*.json"
        for path in sorted(script_dir.glob(pattern)):
            if not path.is_file():
                continue
            full = path.resolve()
            if full in seen:
                continue
            seen.add(full)
            resolved.append(full)

    return resolved


def _format_number(value: float | int | None) -> str:
    """Format one numeric value for markdown.

    Args:
        value (`float | int | None`):
            Value to format.

    Returns:
        `str`:
            Human-readable number.
    """
    if value is None:
        return "-"
    return f"{float(value):.3f}"


def _p95(values: list[float]) -> float | None:
    """Compute p95 for a value list.

    Args:
        values (`list[float]`):
            Numeric list.

    Returns:
        `float | None`:
            P95 value when list is not empty.
    """
    if not values:
        return None
    sorted_values = sorted(values)
    idx = max(0, min(len(sorted_values) - 1, int(len(sorted_values) * 0.95) - 1))
    return sorted_values[idx]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load JSONL records.

    Args:
        path (`Path`):
            Input JSONL path.

    Returns:
        `list[dict[str, Any]]`:
            Parsed records.
    """
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _aggregate_metrics(
    mode: str,
    records: list[dict[str, Any]],
    e2e_elapsed_ms: float | None = None,
) -> RunMetrics:
    """Aggregate worker timing + controller telemetry metrics.

    Args:
        mode (`str`):
            Run mode label.
        records (`list[dict[str, Any]]`):
            Raw worker timing records.
        e2e_elapsed_ms (`float | None`):
            End-to-end elapsed time for one run.

    Returns:
        `RunMetrics`:
            Aggregated metrics.
    """
    waits: list[float] = []
    cold_starts = 0
    non_cold_starts = 0

    telemetry_prompt_route_calls = 0
    telemetry_predict_calls = 0
    telemetry_schedule_attempts = 0
    telemetry_schedule_accepted = 0
    telemetry_executor_runs = 0
    telemetry_executor_errors = 0

    for record in records:
        summary = record.get("summary") or {}
        wait_value = summary.get("wait_for_mcp_ready_after_activation_ms")
        if isinstance(wait_value, (int, float)):
            waits.append(float(wait_value))

        startup_mode = str(summary.get("startup_mode") or "unknown")
        if startup_mode == "cold":
            cold_starts += 1
        elif startup_mode != "unknown":
            non_cold_starts += 1

        telemetry = record.get("prewarm_controller_telemetry") or {}
        stats = telemetry.get("stats") or {}

        telemetry_prompt_route_calls += int(stats.get("prompt_route_calls", 0) or 0)
        telemetry_predict_calls += int(stats.get("predict_calls", 0) or 0)
        telemetry_schedule_attempts += int(stats.get("schedule_attempts", 0) or 0)
        telemetry_schedule_accepted += int(stats.get("schedule_accepted", 0) or 0)
        telemetry_executor_runs += int(stats.get("executor_runs", 0) or 0)
        telemetry_executor_errors += int(stats.get("executor_errors", 0) or 0)

    return RunMetrics(
        run_mode=mode,
        worker_calls=len(records),
        avg_wait_ms=(statistics.mean(waits) if waits else None),
        p50_wait_ms=(statistics.median(waits) if waits else None),
        p95_wait_ms=_p95(waits),
        cold_starts=cold_starts,
        non_cold_starts=non_cold_starts,
        telemetry_prompt_route_calls=telemetry_prompt_route_calls,
        telemetry_predict_calls=telemetry_predict_calls,
        telemetry_schedule_attempts=telemetry_schedule_attempts,
        telemetry_schedule_accepted=telemetry_schedule_accepted,
        telemetry_executor_runs=telemetry_executor_runs,
        telemetry_executor_errors=telemetry_executor_errors,
        e2e_elapsed_ms=e2e_elapsed_ms,
    )


def _build_run_markdown(
    run_json_path: Path,
    mode: str,
    turns: list[str],
    metrics: RunMetrics,
) -> str:
    """Build one run-level markdown summary.

    Args:
        run_json_path (`Path`):
            Run artifact path.
        mode (`str`):
            Run mode.
        turns (`list[str]`):
            Fixed turns used in this run.
        metrics (`RunMetrics`):
            Aggregated metrics.

    Returns:
        `str`:
            Markdown summary.
    """
    rows = [
        ["Mode", mode],
        ["E2E Elapsed (ms)", _format_number(metrics.e2e_elapsed_ms)],
        ["Worker Calls", str(metrics.worker_calls)],
        ["Avg Wait (ms)", _format_number(metrics.avg_wait_ms)],
        ["P50 Wait (ms)", _format_number(metrics.p50_wait_ms)],
        ["P95 Wait (ms)", _format_number(metrics.p95_wait_ms)],
        ["Cold Starts", str(metrics.cold_starts)],
        ["Non-cold Starts", str(metrics.non_cold_starts)],
        ["Telemetry Prompt Route Calls", str(metrics.telemetry_prompt_route_calls)],
        ["Telemetry Predict Calls", str(metrics.telemetry_predict_calls)],
        ["Telemetry Schedule Attempts", str(metrics.telemetry_schedule_attempts)],
        ["Telemetry Schedule Accepted", str(metrics.telemetry_schedule_accepted)],
        ["Telemetry Executor Runs", str(metrics.telemetry_executor_runs)],
        ["Telemetry Executor Errors", str(metrics.telemetry_executor_errors)],
    ]

    lines = [
        "# Multi-turn Plan Experiment (Single Run)",
        "",
        f"> Run artifact: `{run_json_path}`",
        "",
        "## Fixed Dialogue Script",
    ]
    for idx, turn in enumerate(turns, start=1):
        lines.append(f"{idx}. {turn}")

    lines.extend(
        [
            "",
            "## Metrics",
            "| Metric | Value |",
            "| --- | --- |",
        ],
    )
    for metric, value in rows:
        lines.append(f"| {metric} | {value} |")

    return "\n".join(lines) + "\n"


def _build_compare_markdown(
    run_a: dict[str, Any],
    run_b: dict[str, Any],
) -> str:
    """Build one-page A/B comparison markdown.

    Args:
        run_a (`dict[str, Any]`):
            First run artifact payload.
        run_b (`dict[str, Any]`):
            Second run artifact payload.

    Returns:
        `str`:
            Markdown report.
    """
    metrics_a = RunMetrics(**run_a["metrics"])
    metrics_b = RunMetrics(**run_b["metrics"])

    # Prefer A as C1 only and B as C1+C2 for readability.
    left = metrics_a
    right = metrics_b
    left_artifact = run_a["artifact_path"]
    right_artifact = run_b["artifact_path"]
    if metrics_a.run_mode == _MODE_C1_C2 and metrics_b.run_mode == _MODE_C1_ONLY:
        left, right = right, left
        left_artifact, right_artifact = right_artifact, left_artifact

    avg_wait_delta = None
    if left.avg_wait_ms is not None and right.avg_wait_ms is not None:
        avg_wait_delta = right.avg_wait_ms - left.avg_wait_ms

    p50_wait_delta = None
    if left.p50_wait_ms is not None and right.p50_wait_ms is not None:
        p50_wait_delta = right.p50_wait_ms - left.p50_wait_ms

    conclusion = "No clear conclusion yet (missing wait metrics)."
    if avg_wait_delta is not None:
        if avg_wait_delta < 0:
            conclusion = (
                "C1+C2 reduced average activation wait compared with C1 only."
            )
        elif avg_wait_delta > 0:
            conclusion = (
                "C1+C2 increased average activation wait compared with C1 only."
            )
        else:
            conclusion = "C1+C2 and C1 only are equivalent on average wait."

    rows = [
        (
            "E2E Elapsed (ms)",
            _format_number(left.e2e_elapsed_ms),
            _format_number(right.e2e_elapsed_ms),
            _format_number(
                (
                    right.e2e_elapsed_ms - left.e2e_elapsed_ms
                    if left.e2e_elapsed_ms is not None and right.e2e_elapsed_ms is not None
                    else None
                ),
            ),
        ),
        (
            "Worker Calls",
            str(left.worker_calls),
            str(right.worker_calls),
            str(right.worker_calls - left.worker_calls),
        ),
        (
            "Avg Wait (ms)",
            _format_number(left.avg_wait_ms),
            _format_number(right.avg_wait_ms),
            _format_number(avg_wait_delta),
        ),
        (
            "P50 Wait (ms)",
            _format_number(left.p50_wait_ms),
            _format_number(right.p50_wait_ms),
            _format_number(p50_wait_delta),
        ),
        (
            "P95 Wait (ms)",
            _format_number(left.p95_wait_ms),
            _format_number(right.p95_wait_ms),
            (
                _format_number(
                    (
                        right.p95_wait_ms - left.p95_wait_ms
                        if left.p95_wait_ms is not None and right.p95_wait_ms is not None
                        else None
                    ),
                )
            ),
        ),
        (
            "Cold Starts",
            str(left.cold_starts),
            str(right.cold_starts),
            str(right.cold_starts - left.cold_starts),
        ),
        (
            "Non-cold Starts",
            str(left.non_cold_starts),
            str(right.non_cold_starts),
            str(right.non_cold_starts - left.non_cold_starts),
        ),
        (
            "Telemetry Predict Calls",
            str(left.telemetry_predict_calls),
            str(right.telemetry_predict_calls),
            str(right.telemetry_predict_calls - left.telemetry_predict_calls),
        ),
        (
            "Telemetry Schedule Accepted",
            str(left.telemetry_schedule_accepted),
            str(right.telemetry_schedule_accepted),
            str(right.telemetry_schedule_accepted - left.telemetry_schedule_accepted),
        ),
        (
            "Telemetry Executor Errors",
            str(left.telemetry_executor_errors),
            str(right.telemetry_executor_errors),
            str(right.telemetry_executor_errors - left.telemetry_executor_errors),
        ),
    ]

    lines = [
        "# Multi-turn Plan SDG Comparison (One Page)",
        "",
        f"> Baseline artifact: `{left_artifact}`",
        f"> SDG artifact: `{right_artifact}`",
        "",
        "## Conclusion",
        conclusion,
        "",
        "## A/B Metrics",
        "| Metric | C1 Only | C1 + C2 | Delta (C1+C2 - C1) |",
        "| --- | --- | --- | --- |",
    ]
    for metric, left_value, right_value, delta_value in rows:
        lines.append(f"| {metric} | {left_value} | {right_value} | {delta_value} |")

    lines.extend(
        [
            "",
            "## Notes",
            "- This comparison uses the same fixed multi-turn dialogue script.",
            "- Keep model/provider settings and environment stable across two runs.",
            "- Use multiple repeated A/B pairs for stronger statistical confidence.",
        ],
    )

    return "\n".join(lines) + "\n"


def _build_batch_summary_markdown(cases: list[dict[str, Any]]) -> str:
    """Build one markdown summary across multiple dialogue-script cases.

    Args:
        cases (`list[dict[str, Any]]`):
            Case-level summary records.

    Returns:
        `str`:
            Markdown report.
    """

    lines = [
        "# Multi-case SDG Comparison Summary",
        "",
        "This summary compares C1-only vs C1+C2 across multiple dialogue scripts.",
        "",
        "| Case | Repeats | Script | C1 E2E p50 (ms) | C1 E2E p95 (ms) | C1+C2 E2E p50 (ms) | C1+C2 E2E p95 (ms) | Delta E2E p50 (ms) | Delta E2E p95 (ms) | C1 Avg Wait (ms) | C1+C2 Avg Wait (ms) | Delta Wait (C1+C2-C1) | C1 Cold Starts | C1+C2 Cold Starts | Compare Reports |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    all_c1_e2e: list[float] = []
    all_c2_e2e: list[float] = []
    all_delta_e2e: list[float] = []

    for case in cases:
        c1 = RunMetrics(**case["c1_metrics"])
        c2 = RunMetrics(**case["c2_metrics"])
        delta = (
            c2.avg_wait_ms - c1.avg_wait_ms
            if c1.avg_wait_ms is not None and c2.avg_wait_ms is not None
            else None
        )

        repeats = int(case.get("repeats", 1) or 1)
        compare_reports = case.get("compare_reports") or []
        c1_e2e_values = [
            float(value)
            for value in (case.get("c1_e2e_values") or [])
            if isinstance(value, (int, float))
        ]
        c2_e2e_values = [
            float(value)
            for value in (case.get("c2_e2e_values") or [])
            if isinstance(value, (int, float))
        ]
        delta_e2e_values = [
            float(value)
            for value in (case.get("delta_e2e_values") or [])
            if isinstance(value, (int, float))
        ]

        all_c1_e2e.extend(c1_e2e_values)
        all_c2_e2e.extend(c2_e2e_values)
        all_delta_e2e.extend(delta_e2e_values)

        c1_e2e_p50 = statistics.median(c1_e2e_values) if c1_e2e_values else None
        c2_e2e_p50 = statistics.median(c2_e2e_values) if c2_e2e_values else None
        delta_e2e_p50 = statistics.median(delta_e2e_values) if delta_e2e_values else None
        c1_e2e_p95 = _p95(c1_e2e_values)
        c2_e2e_p95 = _p95(c2_e2e_values)
        delta_e2e_p95 = _p95(delta_e2e_values)

        lines.append(
            "| {case_name} | {repeats} | {script_name} | {c1_e2e_p50} | {c1_e2e_p95} | {c2_e2e_p50} | {c2_e2e_p95} | {delta_e2e_p50} | {delta_e2e_p95} | {c1_avg} | {c2_avg} | {delta_wait} | {c1_cold} | {c2_cold} | {report_paths} |".format(
                case_name=case["case_name"],
                repeats=repeats,
                script_name=case["script_name"],
                c1_e2e_p50=_format_number(c1_e2e_p50),
                c1_e2e_p95=_format_number(c1_e2e_p95),
                c2_e2e_p50=_format_number(c2_e2e_p50),
                c2_e2e_p95=_format_number(c2_e2e_p95),
                delta_e2e_p50=_format_number(delta_e2e_p50),
                delta_e2e_p95=_format_number(delta_e2e_p95),
                c1_avg=_format_number(c1.avg_wait_ms),
                c2_avg=_format_number(c2.avg_wait_ms),
                delta_wait=_format_number(delta),
                c1_cold=c1.cold_starts,
                c2_cold=c2.cold_starts,
                report_paths=", ".join(compare_reports) if compare_reports else str(case.get("compare_report_path", "-")),
            ),
        )

    overall_c1_e2e_p50 = statistics.median(all_c1_e2e) if all_c1_e2e else None
    overall_c2_e2e_p50 = statistics.median(all_c2_e2e) if all_c2_e2e else None
    overall_delta_e2e_p50 = statistics.median(all_delta_e2e) if all_delta_e2e else None
    overall_c1_e2e_p95 = _p95(all_c1_e2e)
    overall_c2_e2e_p95 = _p95(all_c2_e2e)
    overall_delta_e2e_p95 = _p95(all_delta_e2e)

    lines.extend(
        [
            "",
            "## Overall E2E (All Repeats Across Cases)",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| C1 E2E p50 (ms) | {_format_number(overall_c1_e2e_p50)} |",
            f"| C1 E2E p95 (ms) | {_format_number(overall_c1_e2e_p95)} |",
            f"| C1+C2 E2E p50 (ms) | {_format_number(overall_c2_e2e_p50)} |",
            f"| C1+C2 E2E p95 (ms) | {_format_number(overall_c2_e2e_p95)} |",
            f"| Delta E2E p50 (ms) | {_format_number(overall_delta_e2e_p50)} |",
            f"| Delta E2E p95 (ms) | {_format_number(overall_delta_e2e_p95)} |",
            "",
            "## Notes",
            "- E2E p50/p95 are computed over repeated runs per case.",
            "- Heavy MCP servers should appear in later turns (not first tool call) by script design.",
            "- Use enough cases to avoid single-case bias in paper claims.",
        ],
    )
    return "\n".join(lines) + "\n"


def _set_runtime_config(
    mode: str,
    stream_interval_tokens: int | None,
    predictive_top_k: int = 1,
    predictive_transition_matrix_path: str | None = None,
) -> None:
    """Set runtime config values before loading worker tool module.

    Args:
        mode (`str`):
            Experiment mode.
        stream_interval_tokens (`int | None`):
            Stream speculation interval.
        predictive_top_k (`int`):
            Number of SDG candidates to prewarm.
        predictive_transition_matrix_path (`str | None`):
            Optional SDG transition matrix override.
    """
    import config

    if predictive_top_k < 1:
        raise ValueError("predictive_top_k must be >= 1.")
    config.ON_DEMAND_PREWARM_ENABLED = mode in {
        _MODE_C1_ONLY,
        _MODE_C1_C2,
    }
    config.ON_DEMAND_PREDICTIVE_PREWARM_ENABLED = mode in {
        _MODE_C2_ONLY,
        _MODE_C1_C2,
    }
    config.ON_DEMAND_PREDICTIVE_TOP_K = predictive_top_k
    config.ON_DEMAND_PREDICTIVE_TRANSITION_MATRIX_PATH = (
        predictive_transition_matrix_path
    )
    config.ON_DEMAND_PREWARM_TELEMETRY_ENABLED = True
    config.ON_DEMAND_PREWARM_TELEMETRY_MAX_EVENTS = 2048
    config.ON_DEMAND_STREAM_TEXT_SPECULATION_INTERVAL_TOKENS = (
        config.normalize_stream_text_speculation_interval_tokens(
            stream_interval_tokens,
        )
    )


def _build_planner(
    mode: str,
    model_name: str,
    planner_max_iters: int,
    stream_interval_tokens: int | None,
    predictive_top_k: int = 1,
    predictive_transition_matrix_path: str | None = None,
) -> ReActAgent:
    """Construct planner for one experiment run.

    Args:
        mode (`str`):
            Experiment mode.
        model_name (`str`):
            Planner model name.
        planner_max_iters (`int`):
            Max reasoning iterations.
        stream_interval_tokens (`int | None`):
            Stream speculation interval tokens.
        predictive_top_k (`int`):
            Number of SDG candidates to prewarm.
        predictive_transition_matrix_path (`str | None`):
            Optional SDG transition matrix override.

    Returns:
        `ReActAgent`:
            Configured planner agent.
    """
    import config

    _set_runtime_config(
        mode,
        stream_interval_tokens,
        predictive_top_k,
        predictive_transition_matrix_path,
    )

    tool_module = importlib.import_module("tool")
    tool_module = importlib.reload(tool_module)

    toolkit = Toolkit()
    toolkit.register_tool_function(tool_module.create_worker)

    planner_prewarm_registrations = _load_experiment_registrations()

    prompt_prewarm_enabled = mode in {
        _MODE_C1_ONLY,
        _MODE_C1_C2,
    }
    predictive_enabled = mode in {
        _MODE_C2_ONLY,
        _MODE_C1_C2,
    }
    planner_controller = MCPLaplaceController(
        prompt_prewarm_router=(
            MCPPrewarmHybridRouter()
            if prompt_prewarm_enabled
            else None
        ),
        prompt_prewarm_executor=build_mcp_speculative_executor(
            planner_prewarm_registrations,
        ),
        config=MCPLaplaceControllerConfig(
            prompt_prewarm_enabled=prompt_prewarm_enabled,
            predictive_warmer_enabled=predictive_enabled,
            predictive_top_k=predictive_top_k,
            predictive_transition_matrix_path=(
                predictive_transition_matrix_path
            ),
            telemetry_enabled=True,
            telemetry_max_events=2048,
            telemetry_name=f"multiturn_planner_{mode}",
        ),
    )

    planner = ReActAgent(
        name="Friday",
        sys_prompt=(
            "You are Friday, a meta planner agent. "
            "Always create a plan first, then execute subtasks in order by "
            "creating worker agents via create_worker when needed."
        ),
        model=config.build_experiment_chat_model(
            model_name=model_name,
            stream_interval_tokens=stream_interval_tokens,
        ),
        formatter=config.get_experiment_chat_formatter(),
        plan_notebook=PlanNotebook(),
        toolkit=toolkit,
        max_iters=planner_max_iters,
        mcp_laplace_controller=planner_controller,
    )
    planner.set_console_output_enabled(False)
    return planner


async def _run_dialogue(
    planner: ReActAgent,
    turns: list[str],
) -> list[dict[str, str]]:
    """Run fixed multi-turn dialogue against planner.

    Args:
        planner (`ReActAgent`):
            Planner instance.
        turns (`list[str]`):
            User turns.

    Returns:
        `list[dict[str, str]]`:
            Turn-level transcript snippets.
    """
    transcript: list[dict[str, str]] = []
    for turn in turns:
        reply = await planner(Msg("user", turn, "user"))
        transcript.append(
            {
                "user": turn,
                "assistant": reply.get_text_content()[:2000],
            },
        )
    return transcript


def _load_turn_script(turn_script_file: str | None) -> list[str]:
    """Load fixed turn script from optional JSON file.

    Args:
        turn_script_file (`str | None`):
            Optional JSON file path.

    Returns:
        `list[str]`:
            Turn list.
    """
    if turn_script_file is None:
        if _DEFAULT_TURN_SCRIPT_FILE.exists():
            payload = json.loads(
                _DEFAULT_TURN_SCRIPT_FILE.read_text(encoding="utf-8"),
            )
            if isinstance(payload, list) and all(
                isinstance(item, str)
                for item in payload
            ):
                return payload
        return list(_FIXED_TURNS)

    path = Path(turn_script_file)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(item, str) for item in payload):
        raise ValueError("Turn script JSON must be a list[str].")
    return payload


def run_once(
    mode: str,
    output_dir: Path,
    model_name: str,
    planner_max_iters: int,
    stream_interval_tokens: int | None,
    turn_script_file: str | None,
    predictive_top_k: int = 1,
    predictive_transition_matrix_path: str | None = None,
) -> dict[str, Any]:
    """Run one experiment and persist artifacts.

    Args:
        mode (`str`):
            Experiment mode.
        output_dir (`Path`):
            Artifact directory.
        model_name (`str`):
            Planner model.
        planner_max_iters (`int`):
            Planner max iterations.
        stream_interval_tokens (`int | None`):
            Stream speculation interval.
        turn_script_file (`str | None`):
            Optional custom turn script file.
        predictive_top_k (`int`):
            Number of SDG candidates to prewarm.
        predictive_transition_matrix_path (`str | None`):
            Optional SDG transition matrix override.

    Returns:
        `dict[str, Any]`:
            Run artifact payload.
    """
    if mode not in _MODE_CHOICES:
        raise ValueError(f"Unsupported mode: {mode}")

    run_started_perf = time.perf_counter()
    os.environ["AGENTSCOPE_EXPERIMENT_MODEL_NAME"] = model_name
    temp_file_dir = _ensure_temp_file_dir()
    os.environ["AGENTSCOPE_ON_DEMAND_TEMP_DIR"] = str(temp_file_dir)
    turns = _load_turn_script(turn_script_file)
    planner_prewarm_registrations = _load_experiment_registrations()

    # Always start each run from a clean MCP runtime.
    _cleanup_experiment_mcp_runtime(planner_prewarm_registrations)

    # Reset worker timing log for isolated run accounting.
    tool_module = importlib.import_module("tool")
    timing_log_path = Path(getattr(tool_module, "_TIMING_LOG_PATH")).resolve()
    timing_log_path.parent.mkdir(parents=True, exist_ok=True)
    timing_log_path.write_text("", encoding="utf-8")

    planner = _build_planner(
        mode=mode,
        model_name=model_name,
        planner_max_iters=planner_max_iters,
        stream_interval_tokens=stream_interval_tokens,
        predictive_top_k=predictive_top_k,
        predictive_transition_matrix_path=predictive_transition_matrix_path,
    )

    started_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    try:
        with _temporary_cwd(temp_file_dir):
            transcript = asyncio.run(_run_dialogue(planner, turns))
    finally:
        # Clean again so the next mode/run also starts from a clean state.
        _cleanup_experiment_mcp_runtime(planner_prewarm_registrations)

    run_elapsed_ms = (time.perf_counter() - run_started_perf) * 1000.0
    timing_records = _load_jsonl(timing_log_path)
    metrics = _aggregate_metrics(
        mode,
        timing_records,
        e2e_elapsed_ms=run_elapsed_ms,
    )

    run_json_path = _next_run_path(output_dir, mode, ".json")
    run_md_path = run_json_path.with_suffix(".md")

    payload = {
        "artifact_path": str(run_json_path),
        "started_at": started_at,
        "finished_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "run_mode": mode,
        "model_name": model_name,
        "planner_max_iters": planner_max_iters,
        "stream_interval_tokens": stream_interval_tokens,
        "turns": turns,
        "transcript": transcript,
        "timing_log_path": str(timing_log_path),
        "worker_records": len(timing_records),
        "metrics": asdict(metrics),
    }

    run_json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    run_md_path.write_text(
        _build_run_markdown(
            run_json_path=run_json_path,
            mode=mode,
            turns=turns,
            metrics=metrics,
        ),
        encoding="utf-8",
    )

    return payload


def run_batch_cases(
    output_dir: Path,
    script_files: list[Path],
    model_name: str,
    planner_max_iters: int,
    stream_interval_tokens: int | None,
    resume: bool,
    batch_output_path: Path | None,
    batch_repeats: int,
) -> Path:
    """Run one-click A/B for each script and build one aggregate summary.

    Args:
        output_dir (`Path`):
            Base output directory.
        script_files (`list[Path]`):
            Dialogue script files.
        model_name (`str`):
            Planner model.
        planner_max_iters (`int`):
            Planner max iterations.
        stream_interval_tokens (`int | None`):
            Stream speculation interval.
        resume (`bool`):
            Reuse per-case existing artifacts when possible.
        batch_output_path (`Path | None`):
            Optional aggregate summary path.
        batch_repeats (`int`):
            Number of repeats per case.

    Returns:
        `Path`:
            Aggregate summary markdown path.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    if batch_repeats < 1:
        raise ValueError("--batch-repeats must be >= 1.")

    cases: list[dict[str, Any]] = []

    for script_file in script_files:
        case_name = _sanitize_case_name(script_file.stem)
        case_output_dir = output_dir / case_name
        case_output_dir.mkdir(parents=True, exist_ok=True)

        compare_reports: list[str] = []
        c1_e2e_values: list[float] = []
        c2_e2e_values: list[float] = []
        delta_e2e_values: list[float] = []
        c1_payload: dict[str, Any] | None = None
        c2_payload: dict[str, Any] | None = None

        for repeat_idx in range(batch_repeats):
            repeat_output_dir = case_output_dir / f"repeat_{repeat_idx}"
            compare_report_path = run_one_click(
                output_dir=repeat_output_dir,
                model_name=model_name,
                planner_max_iters=planner_max_iters,
                stream_interval_tokens=stream_interval_tokens,
                turn_script_file=str(script_file),
                output_path=None,
                resume=resume,
            )
            compare_reports.append(str(compare_report_path))

            c1_json_path = _latest_run_path(repeat_output_dir, _MODE_C1_ONLY, ".json")
            c2_json_path = _latest_run_path(repeat_output_dir, _MODE_C1_C2, ".json")
            if c1_json_path is None or c2_json_path is None:
                raise RuntimeError(
                    f"Missing c1/c2 JSON artifacts for case '{case_name}' in {repeat_output_dir}",
                )

            c1_payload = json.loads(c1_json_path.read_text(encoding="utf-8"))
            c2_payload = json.loads(c2_json_path.read_text(encoding="utf-8"))

            c1_e2e = c1_payload.get("metrics", {}).get("e2e_elapsed_ms")
            c2_e2e = c2_payload.get("metrics", {}).get("e2e_elapsed_ms")
            if isinstance(c1_e2e, (int, float)):
                c1_e2e_values.append(float(c1_e2e))
            if isinstance(c2_e2e, (int, float)):
                c2_e2e_values.append(float(c2_e2e))
            if isinstance(c1_e2e, (int, float)) and isinstance(c2_e2e, (int, float)):
                delta_e2e_values.append(float(c2_e2e) - float(c1_e2e))

        if c1_payload is None or c2_payload is None:
            raise RuntimeError(f"Batch repeats produced no payloads for case '{case_name}'.")

        cases.append(
            {
                "case_name": case_name,
                "script_name": script_file.name,
                "script_path": str(script_file),
                "compare_report_path": compare_reports[-1] if compare_reports else "",
                "compare_reports": compare_reports,
                "repeats": batch_repeats,
                "c1_e2e_values": c1_e2e_values,
                "c2_e2e_values": c2_e2e_values,
                "delta_e2e_values": delta_e2e_values,
                "c1_metrics": c1_payload["metrics"],
                "c2_metrics": c2_payload["metrics"],
            },
        )

    summary_path = batch_output_path or _next_run_path(output_dir, "sdg_batch_summary", ".md")
    summary_path.write_text(
        _build_batch_summary_markdown(cases),
        encoding="utf-8",
    )
    return summary_path


def compare_runs(
    run_a_path: Path,
    run_b_path: Path,
    output_path: Path,
) -> None:
    """Compare two run artifacts and write one-page markdown report.

    Args:
        run_a_path (`Path`):
            Run artifact A path.
        run_b_path (`Path`):
            Run artifact B path.
        output_path (`Path`):
            Output markdown report path.

    Returns:
        `None`:
            The report is written to disk.
    """
    run_a = json.loads(run_a_path.read_text(encoding="utf-8"))
    run_b = json.loads(run_b_path.read_text(encoding="utf-8"))

    report = _build_compare_markdown(run_a, run_b)
    output_path.write_text(report, encoding="utf-8")


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI parser for one-click SDG experiment.

    Returns:
        `argparse.ArgumentParser`:
            CLI parser.
    """
    parser = argparse.ArgumentParser(
        description="Run c1_only + c1_c2 sequentially and auto-generate a compare report.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(_default_output_dir()),
        help="Output artifact directory.",
    )
    parser.add_argument(
        "--model-name",
        default="qwen3.8-flash",
        help="Planner model name used in both runs.",
    )
    parser.add_argument(
        "--planner-max-iters",
        type=int,
        default=20,
        help="Max planner iterations in both runs.",
    )
    parser.add_argument(
        "--stream-interval-tokens",
        type=int,
        default=20,
        help="Stream speculation interval tokens. Use 0 to disable.",
    )
    parser.add_argument(
        "--turn-script-file",
        default=None,
        help="Optional JSON file for custom turn script (list[str]).",
    )
    parser.add_argument(
        "--turn-script-files",
        nargs="*",
        default=None,
        help="Optional multiple JSON files for batch experiments.",
    )
    parser.add_argument(
        "--turn-script-dir",
        default=None,
        help=(
            "Optional script directory for batch mode. "
            "If used with --turn-script-glob, all matched files are included."
        ),
    )
    parser.add_argument(
        "--turn-script-glob",
        default=None,
        help="Optional glob pattern for batch script discovery (e.g. 'case_*.json').",
    )
    parser.add_argument(
        "--output-path",
        default=None,
        help="Optional final compare report path.",
    )
    parser.add_argument(
        "--batch-output-path",
        default=None,
        help="Optional final aggregate markdown path for batch mode.",
    )
    parser.add_argument(
        "--batch-repeats",
        type=int,
        default=1,
        help="Repeat count per script case in batch mode (>=1).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Reuse latest existing c1_only/c1_c2 run artifacts in output-dir "
            "and only run missing phases before building compare report."
        ),
    )
    return parser


def run_one_click(
    output_dir: Path,
    model_name: str,
    planner_max_iters: int,
    stream_interval_tokens: int | None,
    turn_script_file: str | None,
    output_path: Path | None,
    resume: bool,
) -> Path:
    """Run c1_only + c1_c2 sequentially and compare automatically.

    Args:
        output_dir (`Path`):
            Artifact directory.
        model_name (`str`):
            Planner model.
        planner_max_iters (`int`):
            Planner max iterations.
        stream_interval_tokens (`int | None`):
            Stream speculation interval.
        turn_script_file (`str | None`):
            Optional custom turn script file.
        output_path (`Path | None`):
            Optional final compare report path.
        resume (`bool`):
            Reuse existing per-mode artifacts when available.

    Returns:
        `Path`:
            Final comparison report path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    expected_turns = _load_turn_script(turn_script_file)

    run_c1: dict[str, Any] | None = None
    run_c2: dict[str, Any] | None = None

    if resume:
        existing_c1 = _latest_run_path(output_dir, _MODE_C1_ONLY, ".json")
        if existing_c1 is not None:
            payload = json.loads(existing_c1.read_text(encoding="utf-8"))
            if payload.get("turns") == expected_turns:
                run_c1 = payload

        existing_c2 = _latest_run_path(output_dir, _MODE_C1_C2, ".json")
        if existing_c2 is not None:
            payload = json.loads(existing_c2.read_text(encoding="utf-8"))
            if payload.get("turns") == expected_turns:
                run_c2 = payload

    if run_c1 is None:
        run_c1 = run_once(
            mode=_MODE_C1_ONLY,
            output_dir=output_dir,
            model_name=model_name,
            planner_max_iters=planner_max_iters,
            stream_interval_tokens=stream_interval_tokens,
            turn_script_file=turn_script_file,
        )

    if run_c2 is None:
        run_c2 = run_once(
            mode=_MODE_C1_C2,
            output_dir=output_dir,
            model_name=model_name,
            planner_max_iters=planner_max_iters,
            stream_interval_tokens=stream_interval_tokens,
            turn_script_file=turn_script_file,
        )

    report_path = output_path or _next_run_path(output_dir, "sdg_compare", ".md")
    compare_runs(
        run_a_path=Path(str(run_c1["artifact_path"])),
        run_b_path=Path(str(run_c2["artifact_path"])),
        output_path=report_path,
    )

    # Keep only result JSON/Markdown artifacts generated by this run.
    keep_paths = {
        Path(str(run_c1["artifact_path"])),
        Path(str(run_c2["artifact_path"])),
        Path(str(run_c1["artifact_path"])).with_suffix(".md"),
        Path(str(run_c2["artifact_path"])).with_suffix(".md"),
        report_path,
    }
    _cleanup_non_result_artifacts(output_dir=output_dir, keep_paths=keep_paths)

    # Timing log is an intermediate artifact and should not be retained.
    for run_payload in (run_c1, run_c2):
        timing_log_path = Path(str(run_payload.get("timing_log_path", ""))).resolve()
        if timing_log_path.exists() and timing_log_path.is_file():
            timing_log_path.unlink()

    return report_path


def main() -> None:
    """CLI entry point."""
    parser = _build_arg_parser()
    args = parser.parse_args()

    interval = args.stream_interval_tokens
    stream_interval_tokens = interval if interval > 0 else None
    output_path = Path(args.output_path) if args.output_path else None
    batch_script_files = _resolve_batch_turn_script_files(
        turn_script_files=args.turn_script_files,
        turn_script_dir=args.turn_script_dir,
        turn_script_glob=args.turn_script_glob,
    )

    if batch_script_files:
        report_path = run_batch_cases(
            output_dir=Path(args.output_dir),
            script_files=batch_script_files,
            model_name=args.model_name,
            planner_max_iters=args.planner_max_iters,
            stream_interval_tokens=stream_interval_tokens,
            resume=args.resume,
            batch_output_path=(
                Path(args.batch_output_path)
                if args.batch_output_path
                else None
            ),
            batch_repeats=args.batch_repeats,
        )
    else:
        report_path = run_one_click(
            output_dir=Path(args.output_dir),
            model_name=args.model_name,
            planner_max_iters=args.planner_max_iters,
            stream_interval_tokens=stream_interval_tokens,
            turn_script_file=args.turn_script_file,
            output_path=output_path,
            resume=args.resume,
        )
    # Keep stdout minimal for automation consumption.
    print(str(report_path))
    return


if __name__ == "__main__":
    main()
