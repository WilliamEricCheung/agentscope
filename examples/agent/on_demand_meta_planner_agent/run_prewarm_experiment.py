# -*- coding: utf-8 -*-
"""Run controlled prompt-prewarm experiments for Laplace MCP servers.

This script samples one fuzzy-description task from a configurable number of
distinct Laplace servers, then evaluates four prompt-prewarm modes:

1. No Prewarm
2. Keyword Prewarm
3. Semantic Prewarm
4. Hybrid Prewarm

Each trial starts from a clean Docker/container-lifecycle state so the
measured activation wait reflects true speculative prewarming behavior.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import random
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Literal

from agentscope.mcp import (
    MCPPrewarmHybridRouter,
    MCPPrewarmKeywordRouter,
    MCPPrewarmSemanticRouter,
    _build_mcp_timing_summary,
    _create_mcp_timing_run,
    _ensure_local_docker_mcp_server,
    _record_mcp_timing_event,
    load_laplace_registration_bundle,
)
from agentscope.mcp._mcp_server_helper import (
    _CONTAINER_LIFECYCLE_STATES,
    _remove_persisted_container_state,
)
from agentscope.mcp.server_config.base import _DockerMCPRegistrationConfig

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_TASK_FILE = (
    _REPO_ROOT / "laplace" / "mcp_dataset" / "laplace_tasks_single_runner_format.json"
)
_PLAN_SUFFIX = ".plan.json"
_MODE_ORDER = ("none", "keyword", "semantic", "hybrid")
_MODE_LABELS = {
    "none": "No Prewarm",
    "keyword": "Keyword Prewarm",
    "semantic": "Semantic Prewarm",
    "hybrid": "Hybrid Prewarm",
}


def _default_output_paths(base_dir: Path | None = None) -> tuple[Path, Path, Path]:
    """Build dated default output paths with an incrementing daily index.

    When the same day already has completed output files, the next available
    suffix is chosen, for example ``0428_0`` -> ``0428_1``.

    Args:
        base_dir (`Path | None`, optional):
            Output directory. Defaults to the current example folder.

    Returns:
        `tuple[Path, Path, Path]`:
            Default JSONL, Markdown report, and plan file paths.
    """
    output_dir = base_dir or Path(__file__).resolve().parent
    date_prefix = time.strftime("%m%d", time.localtime())
    index = 0

    while True:
        run_suffix = f"{date_prefix}_{index}"
        log_path = output_dir / f"prewarm_experiment_results_{run_suffix}.jsonl"
        report_path = output_dir / f"prewarm_experiment_report_{run_suffix}.md"
        plan_path = output_dir / f"prewarm_experiment_results_{run_suffix}.plan.json"
        if not any(path.exists() for path in (log_path, report_path, plan_path)):
            return log_path, report_path, plan_path
        index += 1


def _default_plan_path(output_log_path: Path) -> Path:
    """Build the companion plan path for one JSONL output file.

    Args:
        output_log_path (`Path`):
            Experiment JSONL output path.

    Returns:
        `Path`:
            The plan-file path.
    """
    return output_log_path.with_name(output_log_path.stem + _PLAN_SUFFIX)


def _format_number(value: Any) -> str:
    """Format one numeric value for Markdown display.

    Args:
        value (`Any`):
            The raw numeric value.

    Returns:
        `str`:
            A human-readable number string.
    """
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        return f"{float(value):.3f}"
    return str(value)


def _build_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    """Build a Markdown table string.

    Args:
        headers (`list[str]`):
            Table headers.
        rows (`list[list[str]]`):
            Table rows.

    Returns:
        `str`:
            The Markdown table.
    """
    if not rows:
        rows = [["-" for _ in headers]]

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _load_task_pool(task_file: Path) -> dict[str, list[dict[str, str]]]:
    """Load fuzzy-description tasks grouped by source server.

    Args:
        task_file (`Path`):
            Runner-format dataset file.

    Returns:
        `dict[str, list[dict[str, str]]]`:
            Tasks grouped by human-readable server name.
    """
    payload = json.loads(task_file.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)

    for server_block in payload.get("server_tasks", []):
        server_name = str(server_block.get("server_name", "")).strip()
        if not server_name:
            continue
        for task in server_block.get("tasks", []):
            fuzzy_description = str(task.get("fuzzy_description", "")).strip()
            if not fuzzy_description:
                continue
            grouped[server_name].append(
                {
                    "server_name": server_name,
                    "task_id": str(task.get("task_id", "")).strip(),
                    "task_description": str(
                        task.get("task_description", ""),
                    ).strip(),
                    "fuzzy_description": fuzzy_description,
                },
            )

    return dict(grouped)


def _sample_unique_server_tasks(
    grouped_tasks: dict[str, list[dict[str, str]]],
    sample_size: int,
    seed: int,
) -> list[dict[str, str]]:
    """Sample one task per distinct server.

    Args:
        grouped_tasks (`dict[str, list[dict[str, str]]]`):
            Tasks grouped by server name.
        sample_size (`int`):
            Number of distinct servers to sample.
        seed (`int`):
            Random seed for reproducibility.

    Returns:
        `list[dict[str, str]]`:
            Sampled tasks with unique server names.

    Raises:
        `ValueError`:
            Raised when the requested sample size exceeds available servers.
    """
    server_names = sorted(grouped_tasks.keys())
    if sample_size > len(server_names):
        raise ValueError(
            f"Requested {sample_size} servers but only {len(server_names)} are available.",
        )

    random_source = random.Random(seed)
    selected_servers = random_source.sample(server_names, sample_size)

    sampled_tasks: list[dict[str, str]] = []
    for server_name in selected_servers:
        sampled_tasks.append(random_source.choice(grouped_tasks[server_name]))

    return sampled_tasks


def _build_router(
    mode: Literal["none", "keyword", "semantic", "hybrid"],
) -> object | None:
    """Create one router for the given experiment mode.

    Args:
        mode (`Literal["none", "keyword", "semantic", "hybrid"]`):
            Experiment mode.

    Returns:
        `object | None`:
            The router instance or `None` for no-prewarm mode.

    Raises:
        `ValueError`:
            Raised when the mode is unsupported.
    """
    if mode == "none":
        return None
    if mode == "keyword":
        return MCPPrewarmKeywordRouter()
    if mode == "semantic":
        return MCPPrewarmSemanticRouter()
    if mode == "hybrid":
        return MCPPrewarmHybridRouter()
    raise ValueError(f"Unsupported experiment mode: {mode}")


def _trial_key(
    task_id: str,
    mode: str,
    repeat_index: int,
) -> str:
    """Build one stable identifier for a single trial.

    Args:
        task_id (`str`):
            The sampled task ID.
        mode (`str`):
            Experiment mode.
        repeat_index (`int`):
            One-based repetition index.

    Returns:
        `str`:
            Stable trial key.
    """
    return f"{task_id}::{mode}::{repeat_index}"


def _trial_metadata(
    task: dict[str, str],
    mode: str,
    repeat_index: int,
) -> dict[str, Any]:
    """Build the stable metadata shared by all records for one trial.

    Args:
        task (`dict[str, str]`):
            Sampled task payload.
        mode (`str`):
            Experiment mode.
        repeat_index (`int`):
            One-based repetition index.

    Returns:
        `dict[str, Any]`:
            Shared trial metadata.
    """
    return {
        "trial_key": _trial_key(task["task_id"], mode, repeat_index),
        "experiment_mode": mode,
        "repeat_index": repeat_index,
        "server_name": task["server_name"],
        "task_id": task["task_id"],
        "prompt_description": task["fuzzy_description"],
    }


def _append_jsonl_record(
    output_log_path: Path,
    record: dict[str, Any],
) -> None:
    """Append one serialized record to the experiment JSONL.

    Args:
        output_log_path (`Path`):
            JSONL path.
        record (`dict[str, Any]`):
            Serializable record payload.

    Returns:
        `None`:
            The record is appended to disk.
    """
    with output_log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def _build_experiment_plan(
    task_file: Path,
    sample_size: int,
    repeats: int,
    seed: int,
    modes: list[Literal["none", "keyword", "semantic", "hybrid"]],
    sampled_tasks: list[dict[str, str]],
    manifest_path: str | None,
) -> dict[str, Any]:
    """Build a persisted experiment plan for resumable execution.

    Args:
        task_file (`Path`):
            Source task dataset path.
        sample_size (`int`):
            Number of sampled servers.
        repeats (`int`):
            Repetitions per task and mode.
        seed (`int`):
            Sampling seed.
        modes (`list[Literal["none", "keyword", "semantic", "hybrid"]]`):
            Enabled experiment modes.
        sampled_tasks (`list[dict[str, str]]`):
            Persisted sampled tasks.
        manifest_path (`str | None`):
            Explicit manifest path, if any.

    Returns:
        `dict[str, Any]`:
            Serializable experiment plan.
    """
    return {
        "task_file": str(task_file.resolve()),
        "manifest_path": str(Path(manifest_path).resolve()) if manifest_path else None,
        "sample_size": sample_size,
        "repeats": repeats,
        "seed": seed,
        "modes": list(modes),
        "sampled_tasks": sampled_tasks,
    }


def _load_existing_records(output_log_path: Path) -> list[dict[str, Any]]:
    """Load existing JSONL records for resume or report rebuild.

    Args:
        output_log_path (`Path`):
            JSONL result path.

    Returns:
        `list[dict[str, Any]]`:
            Parsed records in file order.
    """
    if not output_log_path.exists():
        return []

    records: list[dict[str, Any]] = []
    with output_log_path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _latest_trial_records(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Collapse raw JSONL history to the latest record for each trial.

    Args:
        records (`list[dict[str, Any]]`):
            Raw JSONL records.

    Returns:
        `dict[str, dict[str, Any]]`:
            Latest record indexed by trial key.
    """
    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        trial_key = str(record.get("trial_key", "")).strip()
        if not trial_key:
            task_id = str(record.get("task_id", "")).strip()
            mode = str(record.get("experiment_mode", "")).strip()
            repeat_index = int(record.get("repeat_index", 0) or 0)
            if task_id and mode and repeat_index > 0:
                trial_key = _trial_key(task_id, mode, repeat_index)
            else:
                continue
        latest[trial_key] = record
    return latest


def _completed_trial_keys(records: list[dict[str, Any]]) -> set[str]:
    """Extract the completed-trial key set from persisted records.

    Args:
        records (`list[dict[str, Any]]`):
            Existing experiment records.

    Returns:
        `set[str]`:
            Completed stable trial keys.
    """
    return {
        trial_key
        for trial_key, record in _latest_trial_records(records).items()
        if str(record.get("trial_status", "")).strip() == "completed"
    }


def _completed_trial_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the latest completed record for each successful trial.

    Args:
        records (`list[dict[str, Any]]`):
            Raw JSONL records.

    Returns:
        `list[dict[str, Any]]`:
            Latest completed trial records only.
    """
    return [
        record
        for record in _latest_trial_records(records).values()
        if str(record.get("trial_status", "")).strip() == "completed"
    ]


def _load_or_initialize_plan(
    plan_path: Path,
    task_file: Path,
    sample_size: int,
    repeats: int,
    seed: int,
    modes: list[Literal["none", "keyword", "semantic", "hybrid"]],
    manifest_path: str | None,
    resume: bool,
) -> dict[str, Any]:
    """Load an existing resumable plan or initialize a new one.

    Args:
        plan_path (`Path`):
            Persisted plan path.
        task_file (`Path`):
            Source task file.
        sample_size (`int`):
            Number of sampled servers.
        repeats (`int`):
            Repetitions per task and mode.
        seed (`int`):
            Sampling seed.
        modes (`list[Literal["none", "keyword", "semantic", "hybrid"]]`):
            Enabled experiment modes.
        manifest_path (`str | None`):
            Explicit manifest path, if any.
        resume (`bool`):
            Whether the caller expects resume behavior.

    Returns:
        `dict[str, Any]`:
            The active experiment plan.

    Raises:
        `ValueError`:
            Raised when resume is requested but the persisted plan is
            incompatible with the current CLI arguments.
    """
    expected_manifest_path = (
        str(Path(manifest_path).resolve()) if manifest_path else None
    )
    expected = {
        "task_file": str(task_file.resolve()),
        "manifest_path": expected_manifest_path,
        "sample_size": sample_size,
        "repeats": repeats,
        "seed": seed,
        "modes": list(modes),
    }

    if plan_path.exists():
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        mismatches = [
            key
            for key, expected_value in expected.items()
            if plan.get(key) != expected_value
        ]
        if mismatches:
            raise ValueError(
                "Existing experiment plan is incompatible with the current "
                f"arguments: {', '.join(mismatches)}. Use --reset-output to "
                "start a fresh experiment.",
            )
        return plan

    grouped_tasks = _load_task_pool(task_file)
    sampled_tasks = _sample_unique_server_tasks(grouped_tasks, sample_size, seed)
    plan = _build_experiment_plan(
        task_file=task_file,
        sample_size=sample_size,
        repeats=repeats,
        seed=seed,
        modes=modes,
        sampled_tasks=sampled_tasks,
        manifest_path=manifest_path,
    )
    plan_path.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return plan


def _candidate_aliases(
    registration: _DockerMCPRegistrationConfig,
) -> set[str]:
    """Build all valid candidate identifiers for one registration.

    Args:
        registration (`_DockerMCPRegistrationConfig`):
            Target registration.

    Returns:
        `set[str]`:
            Candidate aliases accepted by the executor.
    """
    aliases = {
        registration.server_config.client_name,
        registration.server_config.container_name,
    }
    if registration.server_name is not None:
        aliases.add(str(registration.server_name))
    return {alias for alias in aliases if alias}


def _collect_target_metrics(
    events: list[dict[str, Any]],
    registration: _DockerMCPRegistrationConfig,
) -> dict[str, Any]:
    """Summarize target-server prewarm metrics from raw timing events.

    Args:
        events (`list[dict[str, Any]]`):
            Recorded timing events.
        registration (`_DockerMCPRegistrationConfig`):
            The actual server activated for the task.

    Returns:
        `dict[str, Any]`:
            Target-specific router and prewarm metrics.
    """
    aliases = _candidate_aliases(registration)
    matched = False
    effective = False
    route_method = None
    prewarm_duration_ms = None

    for event in events:
        candidate = str(event.get("candidate", "")).strip()
        if event.get("step") == "prewarm_router_matched":
            candidates = [
                item.strip()
                for item in str(event.get("candidates", "")).split(",")
                if item.strip()
            ]
            if any(candidate_name in aliases for candidate_name in candidates):
                matched = True
                route_method = event.get("effective_route_method")

        if event.get("step") == "prewarm_candidate_finished" and candidate in aliases:
            matched = True
            route_method = event.get("effective_route_method", route_method)
            prewarm_duration_ms = event.get("duration_ms")
            if event.get("effective") is True:
                effective = True

    return {
        "target_router_matched": matched,
        "target_effective_prewarm": effective,
        "target_effective_route_method": route_method,
        "target_prewarm_duration_ms": prewarm_duration_ms,
    }


async def _cleanup_experiment_containers(
    registrations: list[_DockerMCPRegistrationConfig],
) -> None:
    """Remove all managed Laplace MCP containers and lifecycle state.

    Args:
        registrations (`list[_DockerMCPRegistrationConfig]`):
            Registrations whose containers must be removed.

    Returns:
        `None`:
            The experiment starts from a clean lifecycle state.
    """
    for registration in registrations:
        container_name = registration.server_config.container_name
        try:
            completed = await asyncio.to_thread(
                subprocess.run,
                ["docker", "rm", "-f", container_name],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Docker CLI is required to run the prewarm experiment.",
            ) from exc

        stderr = (completed.stderr or "").strip().lower()
        if completed.returncode != 0 and "no such container" not in stderr:
            raise RuntimeError(
                f"Failed to remove MCP container '{container_name}': {completed.stderr.strip()}",
            )

        _CONTAINER_LIFECYCLE_STATES.pop(container_name, None)
        _remove_persisted_container_state(container_name)


async def _maybe_call_router(router: object, prompt: str) -> list[str]:
    """Call one router and normalize the result to a list.

    Args:
        router (`object`):
            Prewarm router instance.
        prompt (`str`):
            Prompt text used for routing.

    Returns:
        `list[str]`:
            Candidate identifiers.
    """
    result = router(prompt)
    if inspect.isawaitable(result):
        result = await result
    return [str(candidate).strip() for candidate in result or [] if candidate]


async def _run_single_trial(
    task: dict[str, str],
    mode: Literal["none", "keyword", "semantic", "hybrid"],
    repeat_index: int,
    registration: _DockerMCPRegistrationConfig,
    registrations: list[_DockerMCPRegistrationConfig],
    speculative_executor: object,
) -> dict[str, Any]:
    """Run one prompt-prewarm trial.

    Args:
        task (`dict[str, str]`):
            The sampled task payload.
        mode (`Literal["none", "keyword", "semantic", "hybrid"]`):
            Experiment mode.
        repeat_index (`int`):
            One-based repetition index.
        registration (`_DockerMCPRegistrationConfig`):
            The target server registration.
        registrations (`list[_DockerMCPRegistrationConfig]`):
            All prewarm-ready registrations used for cleanup.
        speculative_executor (`object`):
            Speculative executor compatible with prewarm candidates.

    Returns:
        `dict[str, Any]`:
            Serialized trial record with summary.
    """
    await _cleanup_experiment_containers(registrations)

    prompt = task["fuzzy_description"]
    router = _build_router(mode)
    timing_run = _create_mcp_timing_run(
        task_description=prompt,
        prewarm=mode != "none",
    )
    timing_run["experiment_mode"] = mode
    timing_run["repeat_index"] = repeat_index
    timing_run["server_name"] = task["server_name"]
    timing_run["task_id"] = task["task_id"]
    timing_run["prompt_description"] = prompt

    target_aliases = _candidate_aliases(registration)
    target_effective_route_method = None

    if router is not None:
        configured_router_method = str(getattr(router, "method", mode))
        _record_mcp_timing_event(
            timing_run,
            "prewarm_router_enabled",
            configured_router_method=configured_router_method,
        )
        candidates = sorted(set(await _maybe_call_router(router, prompt)))
        effective_route_method = str(
            getattr(router, "last_route_method", configured_router_method),
        )
        if candidates:
            _record_mcp_timing_event(
                timing_run,
                "prewarm_router_matched",
                configured_router_method=configured_router_method,
                effective_route_method=effective_route_method,
                candidate_count=len(candidates),
                candidates=",".join(candidates),
            )
        else:
            _record_mcp_timing_event(
                timing_run,
                "prewarm_router_no_match",
                configured_router_method=configured_router_method,
                effective_route_method=effective_route_method,
                candidate_count=0,
            )

        for candidate in candidates:
            candidate_route_method = effective_route_method
            candidate_started_at = asyncio.get_running_loop().time()
            _record_mcp_timing_event(
                timing_run,
                "prewarm_candidate_started",
                candidate=candidate,
                configured_router_method=configured_router_method,
                effective_route_method=candidate_route_method,
            )
            try:
                client = await speculative_executor(candidate)
                startup_mode = getattr(client, "startup_mode", None)
                effective = startup_mode in {"cold", "resume"}
                _record_mcp_timing_event(
                    timing_run,
                    "prewarm_candidate_finished",
                    candidate=candidate,
                    configured_router_method=configured_router_method,
                    effective_route_method=candidate_route_method,
                    startup_mode=startup_mode,
                    effective=effective,
                    duration_ms=round(
                        (asyncio.get_running_loop().time() - candidate_started_at)
                        * 1000,
                        3,
                    ),
                )
            except Exception as exc:
                _record_mcp_timing_event(
                    timing_run,
                    "prewarm_candidate_failed",
                    candidate=candidate,
                    configured_router_method=configured_router_method,
                    effective_route_method=candidate_route_method,
                    duration_ms=round(
                        (asyncio.get_running_loop().time() - candidate_started_at)
                        * 1000,
                        3,
                    ),
                    error=str(exc),
                )
                continue

            if candidate in target_aliases:
                target_effective_route_method = candidate_route_method

    _record_mcp_timing_event(
        timing_run,
        "tool_group_activation_requested",
        group_name=registration.group_name,
    )
    client = await _ensure_local_docker_mcp_server(
        config=registration.server_config,
        docker_run_command=registration.docker_run_command,
        headers=registration.headers,
    )
    _record_mcp_timing_event(
        timing_run,
        "mcp_server_ready",
        group_name=registration.group_name,
        startup_mode=getattr(client, "startup_mode", None),
    )

    summary = _build_mcp_timing_summary(timing_run)
    summary.update(
        _collect_target_metrics(
            timing_run.get("events", []),
            registration,
        ),
    )
    if target_effective_route_method is not None:
        summary["target_effective_route_method"] = target_effective_route_method

    record = {
        key: value
        for key, value in timing_run.items()
        if not key.startswith("_")
    }
    record["trial_key"] = _trial_key(task["task_id"], mode, repeat_index)
    record["trial_status"] = "completed"
    record["summary"] = summary
    return record


def _build_mode_rows(records: list[dict[str, Any]]) -> list[list[str]]:
    """Build aggregate comparison rows grouped by experiment mode.

    Args:
        records (`list[dict[str, Any]]`):
            Trial records.

    Returns:
        `list[list[str]]`:
            Markdown-ready rows.
    """
    route_method_labels = {
        "keyword": "L1",
        "semantic": "L2",
    }
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("experiment_mode", "none"))].append(record)

    rows: list[list[str]] = []
    for mode in _MODE_ORDER:
        group = grouped.get(mode, [])
        if not group:
            continue

        waits = [
            float(record["summary"]["wait_for_mcp_ready_after_activation_ms"])
            for record in group
            if record.get("summary", {}).get("wait_for_mcp_ready_after_activation_ms")
            is not None
        ]
        matched_runs = sum(
            1
            for record in group
            if record.get("summary", {}).get("target_router_matched")
        )
        effective_runs = sum(
            1
            for record in group
            if record.get("summary", {}).get("target_effective_prewarm")
        )
        effective_route_counts: dict[str, int] = defaultdict(int)
        for record in group:
            summary = record.get("summary", {})
            if not summary.get("target_effective_prewarm"):
                continue
            route_method = str(
                summary.get("target_effective_route_method") or "unknown",
            )
            effective_route_counts[route_method] += 1
        activation_modes: dict[str, int] = defaultdict(int)
        for record in group:
            activation_mode = str(
                record.get("summary", {}).get("startup_mode") or "unknown",
            )
            activation_modes[activation_mode] += 1

        effective_route_breakdown = "-"
        if effective_route_counts:
            effective_route_breakdown = ", ".join(
                f"{route_method_labels.get(name, name)}:{effective_route_counts[name]}"
                for name in sorted(effective_route_counts)
            )

        rows.append(
            [
                _MODE_LABELS[mode],
                str(len(group)),
                str(matched_runs),
                f"{(matched_runs / len(group)) * 100:.1f}%",
                str(effective_runs),
                (
                    f"{(effective_runs / matched_runs) * 100:.1f}%"
                    if matched_runs
                    else "-"
                ),
                effective_route_breakdown,
                _format_number(sum(waits) / len(waits) if waits else None),
                _format_number(min(waits) if waits else None),
                _format_number(max(waits) if waits else None),
                ", ".join(
                    f"{name}:{activation_modes[name]}"
                    for name in sorted(activation_modes)
                ),
            ],
        )

    return rows


def _build_task_mode_rows(records: list[dict[str, Any]]) -> list[list[str]]:
    """Build per-task comparison rows grouped by task and mode.

    Args:
        records (`list[dict[str, Any]]`):
            Trial records.

    Returns:
        `list[list[str]]`:
            Markdown-ready rows.
    """
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        key = (str(record.get("task_id", "")), str(record.get("experiment_mode", "none")))
        grouped[key].append(record)

    task_lookup = {
        str(record.get("task_id", "")): record
        for record in records
    }
    rows: list[list[str]] = []
    for task_id, mode in sorted(
        grouped,
        key=lambda item: (
            str(task_lookup[item[0]].get("server_name", "")),
            item[0],
            _MODE_ORDER.index(item[1]),
        ),
    ):
        group = grouped[(task_id, mode)]
        waits = [
            float(record["summary"]["wait_for_mcp_ready_after_activation_ms"])
            for record in group
            if record.get("summary", {}).get("wait_for_mcp_ready_after_activation_ms")
            is not None
        ]
        matched_runs = sum(
            1
            for record in group
            if record.get("summary", {}).get("target_router_matched")
        )
        effective_runs = sum(
            1
            for record in group
            if record.get("summary", {}).get("target_effective_prewarm")
        )
        exemplar = task_lookup[task_id]
        rows.append(
            [
                str(exemplar.get("server_name", "-")),
                task_id,
                _MODE_LABELS[mode],
                str(len(group)),
                f"{(matched_runs / len(group)) * 100:.1f}%",
                (
                    f"{(effective_runs / matched_runs) * 100:.1f}%"
                    if matched_runs
                    else "-"
                ),
                _format_number(sum(waits) / len(waits) if waits else None),
            ],
        )

    return rows


def _build_sample_rows(sampled_tasks: list[dict[str, str]]) -> list[list[str]]:
    """Build sampled-task rows for the report header section.

    Args:
        sampled_tasks (`list[dict[str, str]]`):
            Sampled tasks.

    Returns:
        `list[list[str]]`:
            Markdown-ready rows.
    """
    rows: list[list[str]] = []
    for task in sampled_tasks:
        rows.append(
            [
                task["server_name"],
                task["task_id"],
                task["fuzzy_description"][:80] + ("..." if len(task["fuzzy_description"]) > 80 else ""),
            ],
        )
    return rows


def _build_report(
    records: list[dict[str, Any]],
    sampled_tasks: list[dict[str, str]],
    task_file: Path,
    repeats: int,
    seed: int,
    completed_trial_count: int | None = None,
    total_trial_count: int | None = None,
    skipped_resumed_trial_count: int | None = None,
) -> str:
    """Generate a Markdown report for one experiment run.

    Args:
        records (`list[dict[str, Any]]`):
            Trial records.
        sampled_tasks (`list[dict[str, str]]`):
            The sampled task list.
        task_file (`Path`):
            Dataset source path.
        repeats (`int`):
            Number of repetitions per mode and task.
        seed (`int`):
            Sampling seed.
        completed_trial_count (`int | None`, optional):
            Number of completed trials in the current result set.
        total_trial_count (`int | None`, optional):
            Expected total number of planned trials.
        skipped_resumed_trial_count (`int | None`, optional):
            Number of completed trials skipped at startup because resume was
            enabled.

    Returns:
        `str`:
            Markdown report text.
    """
    mode_headers = [
        "Mode",
        "Runs",
        "Target Match Runs",
        "Target Match Rate",
        "Effective Prewarm Runs",
        "Effectiveness Rate",
        "Effective Route Breakdown",
        "Avg Wait After Activation (ms)",
        "Min Wait (ms)",
        "Max Wait (ms)",
        "Activation Startup Modes",
    ]
    task_headers = [
        "Server",
        "Task ID",
        "Mode",
        "Runs",
        "Target Match Rate",
        "Effectiveness Rate",
        "Avg Wait After Activation (ms)",
    ]
    sample_headers = ["Server", "Task ID", "Fuzzy Description"]
    progress_headers = ["Completed Trials", "Remaining Trials", "Skipped Resumed Trials"]
    progress_rows: list[list[str]] = []
    if completed_trial_count is not None and total_trial_count is not None:
        remaining_trial_count = max(total_trial_count - completed_trial_count, 0)
        progress_rows.append(
            [
                str(completed_trial_count),
                str(remaining_trial_count),
                str(skipped_resumed_trial_count or 0),
            ],
        )

    completed_records = _completed_trial_records(records)

    sections = [
        "# MCP Prewarm Experiment Report",
        f"> Source dataset: `{task_file}`",
        f"> Sample size: `{len(sampled_tasks)}` distinct servers, repeats per mode: `{repeats}`, random seed: `{seed}`.",
        "> Each trial begins by forcibly removing all prewarm-ready Laplace MCP containers and their lifecycle state so speculative prewarm always starts from a clean container state.",
        "> `Target Match Rate` measures whether the router selected the actual server required by the sampled task. `Effectiveness Rate` is computed as `effective target prewarm runs / target matched runs`, aligned with the earlier timing-report definition but made target-specific for this experiment.",
    ]
    if progress_rows:
        sections.extend(
            [
                "## Resume Progress",
                _build_markdown_table(progress_headers, progress_rows),
            ],
        )
    sections.extend(
        [
            "## Sampled Tasks",
            _build_markdown_table(sample_headers, _build_sample_rows(sampled_tasks)),
            "## Overall Comparison by Mode",
            _build_markdown_table(mode_headers, _build_mode_rows(completed_records)),
            "## Per-task Comparison by Mode",
            _build_markdown_table(task_headers, _build_task_mode_rows(completed_records)),
        ],
    )

    return "\n\n".join(sections) + "\n"


async def run_experiment(
    task_file: Path,
    output_log_path: Path,
    output_report_path: Path,
    sample_size: int,
    repeats: int,
    seed: int,
    modes: list[Literal["none", "keyword", "semantic", "hybrid"]],
    manifest_path: str | None = None,
    resume: bool = True,
    reset_output: bool = False,
    plan_path: Path | None = None,
) -> str:
    """Run the full prewarm experiment and save artifacts.

    Args:
        task_file (`Path`):
            Runner-format dataset path.
        output_log_path (`Path`):
            JSONL output path.
        output_report_path (`Path`):
            Markdown report output path.
        sample_size (`int`):
            Number of distinct servers to sample.
        repeats (`int`):
            Number of repetitions per task and mode.
        seed (`int`):
            Random seed for task sampling.
        modes (`list[Literal["none", "keyword", "semantic", "hybrid"]]`):
            Experiment modes to execute.
        manifest_path (`str | None`, optional):
            Explicit Laplace manifest path.
        resume (`bool`, optional):
            Whether to resume from existing JSONL and plan artifacts.
        reset_output (`bool`, optional):
            Whether to discard previous JSONL and plan artifacts first.
        plan_path (`Path | None`, optional):
            Explicit plan path. When omitted, derive from the output log path.

    Returns:
        `str`:
            The generated Markdown report.
    """
    plan_path = plan_path or _default_plan_path(output_log_path)
    if reset_output:
        if output_log_path.exists():
            output_log_path.unlink()
        if plan_path.exists():
            plan_path.unlink()

    plan = _load_or_initialize_plan(
        plan_path=plan_path,
        task_file=task_file,
        sample_size=sample_size,
        repeats=repeats,
        seed=seed,
        modes=modes,
        manifest_path=manifest_path,
        resume=resume,
    )
    sampled_tasks = [
        {
            "server_name": str(task["server_name"]),
            "task_id": str(task["task_id"]),
            "task_description": str(task.get("task_description", "")),
            "fuzzy_description": str(task["fuzzy_description"]),
        }
        for task in plan.get("sampled_tasks", [])
    ]
    registrations_by_server, speculative_executor = load_laplace_registration_bundle(
        manifest_path=manifest_path,
        ready_only=True,
    )
    all_registrations = list(registrations_by_server.values())

    existing_records = _load_existing_records(output_log_path) if resume else []
    completed_keys = _completed_trial_keys(existing_records)
    records: list[dict[str, Any]] = list(existing_records)
    total_trial_count = len(sampled_tasks) * len(modes) * repeats
    skipped_resumed_trial_count = len(completed_keys)

    if not resume:
        output_log_path.write_text("", encoding="utf-8")

    for task in sampled_tasks:
        registration = registrations_by_server[task["server_name"]]
        for mode in modes:
            for repeat_index in range(1, repeats + 1):
                trial_metadata = _trial_metadata(task, mode, repeat_index)
                current_trial_key = _trial_key(task["task_id"], mode, repeat_index)
                if current_trial_key in completed_keys:
                    continue
                started_record = {
                    **trial_metadata,
                    "trial_status": "started",
                    "recorded_at": time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.localtime(),
                    ),
                }
                records.append(started_record)
                _append_jsonl_record(output_log_path, started_record)
                try:
                    record = await _run_single_trial(
                        task=task,
                        mode=mode,
                        repeat_index=repeat_index,
                        registration=registration,
                        registrations=all_registrations,
                        speculative_executor=speculative_executor,
                    )
                    record["recorded_at"] = time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.localtime(),
                    )
                    records.append(record)
                    completed_keys.add(current_trial_key)
                    _append_jsonl_record(output_log_path, record)
                except BaseException as exc:
                    failed_record = {
                        **trial_metadata,
                        "trial_status": (
                            "interrupted"
                            if isinstance(exc, (KeyboardInterrupt, asyncio.CancelledError))
                            else "failed"
                        ),
                        "recorded_at": time.strftime(
                            "%Y-%m-%d %H:%M:%S",
                            time.localtime(),
                        ),
                        "error": str(exc),
                    }
                    records.append(failed_record)
                    _append_jsonl_record(output_log_path, failed_record)

                    report = _build_report(
                        records,
                        sampled_tasks,
                        task_file,
                        repeats,
                        seed,
                        completed_trial_count=len(completed_keys),
                        total_trial_count=total_trial_count,
                        skipped_resumed_trial_count=skipped_resumed_trial_count,
                    )
                    output_report_path.write_text(report, encoding="utf-8")
                    raise

                report = _build_report(
                    records,
                    sampled_tasks,
                    task_file,
                    repeats,
                    seed,
                    completed_trial_count=len(completed_keys),
                    total_trial_count=total_trial_count,
                    skipped_resumed_trial_count=skipped_resumed_trial_count,
                )
                output_report_path.write_text(report, encoding="utf-8")

    report = _build_report(
        records,
        sampled_tasks,
        task_file,
        repeats,
        seed,
        completed_trial_count=len(completed_keys),
        total_trial_count=total_trial_count,
        skipped_resumed_trial_count=skipped_resumed_trial_count,
    )
    output_report_path.write_text(report, encoding="utf-8")
    return report


def main() -> None:
    """CLI entry point for the prompt-prewarm experiment runner."""
    parser = argparse.ArgumentParser(
        description="Run controlled MCP prompt-prewarm experiments across four routing modes.",
    )
    parser.add_argument(
        "--task-file",
        default=str(_DEFAULT_TASK_FILE),
        help="Path to laplace_tasks_single_runner_format.json.",
    )
    parser.add_argument(
        "--manifest-path",
        default=None,
        help="Optional path to laplace_mcp_manifest.json.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=20,
        help="Number of distinct servers to sample.",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=5,
        help="Number of repetitions per mode and sampled task.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible task sampling.",
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        default=list(_MODE_ORDER),
        choices=list(_MODE_ORDER),
        help="Experiment modes to execute.",
    )
    parser.add_argument(
        "--output-log-path",
        default=None,
        help="Path to the JSONL output file.",
    )
    parser.add_argument(
        "--output-report-path",
        default=None,
        help="Path to the Markdown report file.",
    )
    parser.add_argument(
        "--plan-path",
        default=None,
        help="Optional path to the resumable experiment plan JSON file.",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable resume and start from a fresh JSONL file unless --reset-output is omitted.",
    )
    parser.add_argument(
        "--reset-output",
        action="store_true",
        help="Delete any existing JSONL and plan artifacts before starting.",
    )
    args = parser.parse_args()

    default_log_path, default_report_path, default_plan_path = _default_output_paths()
    output_log_path = Path(args.output_log_path) if args.output_log_path else default_log_path
    output_report_path = (
        Path(args.output_report_path)
        if args.output_report_path
        else default_report_path
    )
    plan_path = Path(args.plan_path) if args.plan_path else default_plan_path

    report = asyncio.run(
        run_experiment(
            task_file=Path(args.task_file),
            output_log_path=output_log_path,
            output_report_path=output_report_path,
            sample_size=args.sample_size,
            repeats=args.repeats,
            seed=args.seed,
            modes=list(args.modes),
            manifest_path=args.manifest_path,
            resume=not args.no_resume,
            reset_output=args.reset_output,
            plan_path=plan_path,
        ),
    )
    print(report)
    print(f"\nSaved JSONL results to: {output_log_path}")
    print(f"Saved Markdown report to: {output_report_path}")


if __name__ == "__main__":
    main()