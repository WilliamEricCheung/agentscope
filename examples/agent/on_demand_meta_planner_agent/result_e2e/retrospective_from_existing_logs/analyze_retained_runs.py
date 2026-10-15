"""Recompute retrospective E2E and prefetch summaries from retained raw logs.

This script does not run new experiments. It uses the two-repeat real E2E
records retained under formal_qps1to20_r2_strict_replay and writes
machine-readable, explicitly scoped retrospective outputs next to itself.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

_THIS_DIR = Path(__file__).resolve().parent
_DEFAULT_SOURCE_DIR = _THIS_DIR.parent / "formal_qps1to20_r2_strict_replay"
_DEFAULT_OUTPUT_DIR = _THIS_DIR
_MODES = ("on_demand", "laplace", "always_on")
_QPS_VALUES = tuple(range(1, 21))
_REPEATS = (0, 1)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read JSON objects from a JSON Lines file."""
    if not path.is_file():
        raise FileNotFoundError(path)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise ValueError(f"No rows found in {path}")
    return rows


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    """Write rows to a CSV file with a stable column order."""
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write rows to a JSON Lines file."""
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            stream.write("\n")


def _nearest_rank(values: list[float], quantile: float) -> float:
    """Calculate the nearest-rank quantile of a non-empty sequence."""
    if not values:
        raise ValueError("Cannot calculate a quantile without observations")
    ordered = sorted(values)
    index = max(0, math.ceil(quantile * len(ordered)) - 1)
    return ordered[index]


def _aggregate_per_repeat(
    source_dir: Path,
) -> tuple[list[dict[str, Any]], dict[tuple[str, int, int], list[dict[str, Any]]]]:
    """Aggregate successful request and wave records into repeat-level metrics."""
    requests = _read_jsonl(source_dir / "real_e2e_request_results.jsonl")
    waves = _read_jsonl(source_dir / "real_e2e_wave_results.jsonl")
    requests_by_wave: dict[tuple[str, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in requests:
        key = (str(row["mode"]), int(row["qps"]), int(row["repeat_id"]))
        requests_by_wave[key].append(row)

    waves_by_key = {
        (str(row["mode"]), int(row["qps"]), int(row["repeat_id"])): row
        for row in waves
    }
    expected = {
        (mode, qps, repeat_id)
        for mode in _MODES
        for qps in _QPS_VALUES
        for repeat_id in _REPEATS
    }
    if set(requests_by_wave) != expected or set(waves_by_key) != expected:
        raise ValueError("Retained runs do not cover all expected mode/QPS/repeat groups")

    result: list[dict[str, Any]] = []
    for mode, qps, repeat_id in sorted(
        expected,
        key=lambda key: (_MODES.index(key[0]), key[1], key[2]),
    ):
        request_rows = requests_by_wave[(mode, qps, repeat_id)]
        wave = waves_by_key[(mode, qps, repeat_id)]
        if len(request_rows) != qps:
            raise ValueError(
                f"Expected {qps} requests in {mode}/QPS={qps}/repeat={repeat_id}; "
                f"found {len(request_rows)}",
            )
        if any(row.get("status") != "ok" for row in request_rows):
            raise ValueError(f"Non-success request found in {mode}/QPS={qps}/repeat={repeat_id}")

        e2e_values = [float(row["e2e_ms"]) for row in request_rows]
        tool_values = [
            float(row["tool_cumulative_ms"])
            for row in request_rows
            if row.get("tool_cumulative_ms") is not None
        ]
        if len(tool_values) != qps:
            raise ValueError(f"Missing cumulative provisioning value in {mode}/QPS={qps}")

        result.append(
            {
                "observed_mode": mode,
                "qps": qps,
                "repeat_id": repeat_id,
                "request_count": len(request_rows),
                "successful_requests": len(e2e_values),
                "p99_e2e_ms": _nearest_rank(e2e_values, 0.99),
                "mean_cumulative_provisioning_ms": mean(tool_values),
                "peak_cpu_cores": float(wave["cpu_peak_cores"]),
                "peak_memory_gib": float(wave["memory_peak_gib"]),
                "wave_elapsed_seconds": float(wave["wave_elapsed_seconds"]),
                "source_request_jsonl": "real_e2e_request_results.jsonl",
                "source_wave_jsonl": "real_e2e_wave_results.jsonl",
            },
        )
    return result, requests_by_wave


def _write_performance_outputs(
    output_dir: Path,
    per_repeat: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Write per-repeat results and QPS-wise means for requested configurations."""
    raw_columns = [
        "observed_mode",
        "qps",
        "repeat_id",
        "request_count",
        "successful_requests",
        "p99_e2e_ms",
        "mean_cumulative_provisioning_ms",
        "peak_cpu_cores",
        "peak_memory_gib",
        "wave_elapsed_seconds",
        "source_request_jsonl",
        "source_wave_jsonl",
    ]
    _write_csv(
        output_dir / "performance_breakdown_per_repeat.csv",
        raw_columns,
        per_repeat,
    )

    mapping: dict[str, tuple[str | None, str, str]] = {
        "On-demand": (
            "on_demand",
            "measured",
            "Direct match to the retained on_demand runtime mode.",
        ),
        "+ Prewarm": (
            None,
            "not_measured",
            "No prewarm-only run exists; retained Laplace enables prewarm and predictive warming together.",
        ),
        "+ Prefetch": (
            "laplace",
            "measured_c1_c2_enabled",
            "Retained Laplace run has prompt prewarm and predictive warmer enabled; no predictive candidates were emitted.",
        ),
        "+ Data Optimization": (
            None,
            "not_measured",
            "No run with semantic cache and out-of-band transmission exists in retained logs.",
        ),
        "Historical Reserved reference": (
            "always_on",
            "measured_reference",
            "Additional retained mode; not one of the four requested incremental configurations.",
        ),
    }
    by_mode_qps: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in per_repeat:
        by_mode_qps[(str(row["observed_mode"]), int(row["qps"]))].append(row)

    means: list[dict[str, Any]] = []
    for config, (source_mode, status, note) in mapping.items():
        for qps in _QPS_VALUES:
            repeat_rows = by_mode_qps.get((source_mode, qps), []) if source_mode else []
            metric_means: dict[str, float | str] = {
                "p99_e2e_mean_s": "",
                "mean_cumulative_provisioning_mean_s": "",
                "peak_cpu_mean_cores": "",
                "peak_memory_mean_gib": "",
            }
            if repeat_rows:
                metric_means = {
                    "p99_e2e_mean_s": mean(float(row["p99_e2e_ms"]) for row in repeat_rows) / 1000.0,
                    "mean_cumulative_provisioning_mean_s": mean(
                        float(row["mean_cumulative_provisioning_ms"])
                        for row in repeat_rows
                    )
                    / 1000.0,
                    "peak_cpu_mean_cores": mean(
                        float(row["peak_cpu_cores"]) for row in repeat_rows
                    ),
                    "peak_memory_mean_gib": mean(
                        float(row["peak_memory_gib"]) for row in repeat_rows
                    ),
                }
            means.append(
                {
                    "requested_configuration": config,
                    "observed_mode": source_mode or "",
                    "measurement_status": status,
                    "qps": qps,
                    "repeats_observed": len(repeat_rows),
                    **metric_means,
                    "aggregation": (
                        "Arithmetic mean across repeat-level metrics; per-repeat p99 is nearest-rank "
                        "over successful requests in that wave; cumulative latency is the per-request "
                        "sum averaged across requests within a wave; CPU/memory are per-wave peaks."
                    ),
                    "note": note,
                },
            )

    mean_columns = [
        "requested_configuration",
        "observed_mode",
        "measurement_status",
        "qps",
        "repeats_observed",
        "p99_e2e_mean_s",
        "mean_cumulative_provisioning_mean_s",
        "peak_cpu_mean_cores",
        "peak_memory_mean_gib",
        "aggregation",
        "note",
    ]
    _write_csv(output_dir / "performance_breakdown_means_by_qps.csv", mean_columns, means)
    return means


def _extract_prefetch_events(
    source_dir: Path,
    requests_by_wave: dict[tuple[str, int, int], list[dict[str, Any]]],
    output_dir: Path,
) -> dict[str, Any]:
    """Extract predictive call records and summarize SDG warmup observability."""
    prediction_rows: list[dict[str, Any]] = []
    warmup_rows: list[dict[str, Any]] = []
    qps_stats: dict[int, dict[str, int]] = {
        qps: {
            "predictive_calls": 0,
            "candidate_targets_emitted": 0,
            "predictive_warmups_scheduled": 0,
            "predictive_warmups_completed": 0,
            "c1_effective_starts_context": 0,
        }
        for qps in _QPS_VALUES
    }
    laplace_requests = [
        row
        for (mode, _, _), wave_requests in requests_by_wave.items()
        if mode == "laplace"
        for row in wave_requests
        if row.get("status") == "ok"
    ]
    missing_logs = 0

    for request in laplace_requests:
        namespace = str(request.get("mcp_container_namespace", "")).strip()
        timing_path = source_dir / "real_e2e_tmp" / namespace / "laplace_timing.log.jsonl"
        if not namespace or not timing_path.is_file():
            missing_logs += 1
            continue
        raw_lines = [line for line in timing_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not raw_lines:
            missing_logs += 1
            continue
        qps = int(request["qps"])
        for timing_record_index, raw_line in enumerate(raw_lines):
            timing = json.loads(raw_line)
            telemetry = timing.get("prewarm_controller_telemetry") or {}
            controller_events = telemetry.get("events") or []
            for event_index, event in enumerate(controller_events):
                if event.get("event") == "predict_candidates" and event.get("stage") == "predictive":
                    candidate_count = int(event.get("candidate_count") or 0)
                    if candidate_count < 0:
                        raise ValueError(f"Invalid candidate count in {timing_path}")
                    qps_stats[qps]["predictive_calls"] += 1
                    qps_stats[qps]["candidate_targets_emitted"] += candidate_count
                    prediction_rows.append(
                        {
                            "mode": "laplace",
                            "qps": qps,
                            "repeat_id": int(request["repeat_id"]),
                            "request_id": int(request["request_id"]),
                            "attempt_id": int(request["attempt_id"]),
                            "trace_id": str(request["trace_id"]),
                            "timing_record_index": timing_record_index,
                            "timing_event_index": event_index,
                            "event_timestamp_ms": event.get("ts"),
                            "current_server": event.get("current_server"),
                            "status": event.get("status"),
                            "candidate_count": candidate_count,
                            "duration_ms": event.get("duration_ms"),
                            "candidate_names_recorded": False,
                            "source_timing_log": str(timing_path.relative_to(source_dir)),
                        },
                    )
                if event.get("event") == "prewarm_schedule" and event.get("stage") == "predictive":
                    if event.get("status") == "accepted":
                        qps_stats[qps]["predictive_warmups_scheduled"] += 1
                        warmup_rows.append(
                            {
                                "mode": "laplace",
                                "qps": qps,
                                "repeat_id": int(request["repeat_id"]),
                                "request_id": int(request["request_id"]),
                                "trace_id": str(request["trace_id"]),
                                "target": event.get("candidate", ""),
                                "schedule_timestamp_ms": event.get("ts"),
                                "ready_timestamp_ms": "",
                                "later_demand_use": "",
                                "discard_timestamp_ms": "",
                                "cpu_seconds": "",
                                "memory_gib_seconds": "",
                                "resource_measurement": "not_recorded",
                                "source_timing_log": str(timing_path.relative_to(source_dir)),
                            },
                        )
                if event.get("event") == "prewarm_executor" and event.get("stage") == "predictive":
                    if event.get("status") == "completed":
                        qps_stats[qps]["predictive_warmups_completed"] += 1
            for event in timing.get("events") or []:
                if (
                    event.get("step") == "prewarm_candidate_finished"
                    and event.get("effective") is True
                    and event.get("startup_mode") in {"cold", "resume"}
                ):
                    qps_stats[qps]["c1_effective_starts_context"] += 1

    _write_jsonl(output_dir / "prefetch_prediction_events.jsonl", prediction_rows)
    _write_csv(
        output_dir / "sdg_prefetch_warmup_records.csv",
        [
            "mode",
            "qps",
            "repeat_id",
            "request_id",
            "trace_id",
            "target",
            "schedule_timestamp_ms",
            "ready_timestamp_ms",
            "later_demand_use",
            "discard_timestamp_ms",
            "cpu_seconds",
            "memory_gib_seconds",
            "resource_measurement",
            "source_timing_log",
        ],
        warmup_rows,
    )

    sweep_predictive_calls = sum(row["predictive_calls"] for row in qps_stats.values())
    sweep_candidate_targets = sum(row["candidate_targets_emitted"] for row in qps_stats.values())
    sweep_scheduled = sum(row["predictive_warmups_scheduled"] for row in qps_stats.values())
    sweep_completed = sum(row["predictive_warmups_completed"] for row in qps_stats.values())
    sessions = len(laplace_requests)
    no_candidate = sweep_candidate_targets == 0
    accuracy_denominator = sweep_candidate_targets if no_candidate else None
    false_positive_denominator = sweep_scheduled
    summary = {
        "source": str(source_dir),
        "mode": "laplace",
        "scope": "Retained successful Laplace-mode sessions only; prompt/stream C1 warmups excluded from SDG metrics.",
        "sessions": sessions,
        "predictive_calls": sweep_predictive_calls,
        "candidate_targets_emitted": sweep_candidate_targets,
        "predictive_warmups_scheduled": sweep_scheduled,
        "predictive_warmups_completed": sweep_completed,
        "predictive_warmup_records": len(warmup_rows),
        "c1_effective_starts_context_only": sum(
            row["c1_effective_starts_context"] for row in qps_stats.values()
        ),
        "missing_timing_logs": missing_logs,
        "prefetch_hit_rate": None if no_candidate else None,
        "prefetch_hit_rate_status": (
            "undefined_zero_eligible_candidate_targets"
            if no_candidate
            else "not_computable_target_names_and_uses_not_recorded"
        ),
        "prefetch_hit_rate_numerator": None,
        "prefetch_hit_rate_denominator_candidate_targets": accuracy_denominator,
        "false_positive_rate": None if false_positive_denominator == 0 else None,
        "false_positive_rate_status": (
            "undefined_zero_started_predictive_warmups"
            if false_positive_denominator == 0
            else "not_computable_discard_events_not_recorded"
        ),
        "false_positive_rate_numerator": None,
        "false_positive_rate_denominator_started_warmups": false_positive_denominator,
        "discarded_warmups_per_session": (
            0.0 if sweep_scheduled == 0 and sessions > 0 else None
        ),
        "discarded_warmup_cpu_seconds_per_session": (
            0.0 if sweep_scheduled == 0 and sessions > 0 else None
        ),
        "discarded_warmup_memory_gib_seconds_per_session": (
            0.0 if sweep_scheduled == 0 and sessions > 0 else None
        ),
        "resource_accounting": (
            "No SDG predictive warmups were scheduled in retained successful runs, so SDG-attributable "
            "discard count and resource integrals are zero for these logs. Per-warmup CPU and memory "
            "were not recorded; host wave samples cannot attribute resources to an individual warmup. "
            "Intent-aware prompt/stream C1 warmups are a separate mechanism and are excluded."
        ),
        "denominator_definition": (
            "Candidate-target denominator is the sum of candidate_count over predictive calls. "
            "The retained logs emit zero candidates, so hit rate has a zero denominator. False-positive "
            "denominator is accepted predictive-stage prewarm_schedule events; zero were recorded."
        ),
    }
    (output_dir / "prefetch_accuracy_overhead_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    qps_rows = []
    for qps in _QPS_VALUES:
        item = qps_stats[qps]
        qps_rows.append(
            {
                "qps": qps,
                **item,
                "prefetch_hit_rate": "",
                "prefetch_hit_rate_status": (
                    "undefined_zero_eligible_candidate_targets"
                    if item["candidate_targets_emitted"] == 0
                    else "not_computable"
                ),
                "false_positive_rate": "",
                "false_positive_rate_status": (
                    "undefined_zero_started_predictive_warmups"
                    if item["predictive_warmups_scheduled"] == 0
                    else "not_computable_discard_events_not_recorded"
                ),
                "sessions": sum(
                    1
                    for row in laplace_requests
                    if int(row["qps"]) == qps
                ),
            },
        )
    _write_csv(
        output_dir / "prefetch_metrics_by_qps.csv",
        [
            "qps",
            "sessions",
            "predictive_calls",
            "candidate_targets_emitted",
            "predictive_warmups_scheduled",
            "predictive_warmups_completed",
            "c1_effective_starts_context",
            "prefetch_hit_rate",
            "prefetch_hit_rate_status",
            "false_positive_rate",
            "false_positive_rate_status",
        ],
        qps_rows,
    )
    return summary


def _write_paper_tables(
    output_dir: Path,
    performance_means: list[dict[str, Any]],
    prefetch_summary: dict[str, Any],
) -> None:
    """Write paper-ready QPS=20 performance and sweep-level prefetch tables."""
    _write_csv(
        output_dir / "paper_table_performance_qps20.csv",
        [
            "requested_configuration",
            "observed_mode",
            "measurement_status",
            "qps",
            "repeats_observed",
            "p99_e2e_mean_s",
            "mean_cumulative_provisioning_mean_s",
            "peak_cpu_mean_cores",
            "peak_memory_mean_gib",
            "aggregation",
            "note",
        ],
        [row for row in performance_means if row["qps"] == 20],
    )

    no_predictive_warmups = prefetch_summary["predictive_warmups_scheduled"] == 0
    _write_csv(
        output_dir / "paper_table_prefetch_accuracy_overhead.csv",
        ["metric", "value", "unit", "numerator", "denominator", "status", "accounting"],
        [
            {
                "metric": "Prefetch hit rate",
                "value": "",
                "unit": "fraction",
                "numerator": "",
                "denominator": prefetch_summary[
                    "prefetch_hit_rate_denominator_candidate_targets"
                ],
                "status": prefetch_summary["prefetch_hit_rate_status"],
                "accounting": (
                    "No candidate targets were emitted; target names and later demand use "
                    "are not recorded."
                ),
            },
            {
                "metric": "False-positive rate",
                "value": "",
                "unit": "fraction",
                "numerator": 0 if no_predictive_warmups else "",
                "denominator": prefetch_summary[
                    "false_positive_rate_denominator_started_warmups"
                ],
                "status": prefetch_summary["false_positive_rate_status"],
                "accounting": "Denominator is accepted predictive-stage schedules; none were recorded.",
            },
            {
                "metric": "Discarded warmups per session",
                "value": prefetch_summary["discarded_warmups_per_session"],
                "unit": "warmups/session",
                "numerator": 0 if no_predictive_warmups else "",
                "denominator": prefetch_summary["sessions"],
                "status": "measured_no_predictive_warmups_started",
                "accounting": (
                    "SDG predictive-stage schedules were zero; prompt/stream C1 warmups excluded."
                ),
            },
            {
                "metric": "Discarded-warmup CPU time per session",
                "value": prefetch_summary["discarded_warmup_cpu_seconds_per_session"],
                "unit": "CPU-seconds/session",
                "numerator": 0 if no_predictive_warmups else "",
                "denominator": prefetch_summary["sessions"],
                "status": "measured_no_predictive_warmups_started",
                "accounting": (
                    "Zero SDG warmups, therefore zero SDG-attributable CPU integral; "
                    "not a per-warmup resource measurement."
                ),
            },
            {
                "metric": "Discarded-warmup memory per session",
                "value": prefetch_summary[
                    "discarded_warmup_memory_gib_seconds_per_session"
                ],
                "unit": "GiB-seconds/session",
                "numerator": 0 if no_predictive_warmups else "",
                "denominator": prefetch_summary["sessions"],
                "status": "measured_no_predictive_warmups_started",
                "accounting": (
                    "Zero SDG warmups, therefore zero SDG-attributable memory integral; "
                    "not a per-warmup resource measurement."
                ),
            },
        ],
    )


def main() -> None:
    """Recompute retrospective performance and prefetch outputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=_DEFAULT_SOURCE_DIR)
    parser.add_argument("--output-dir", type=Path, default=_DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    per_repeat, requests_by_wave = _aggregate_per_repeat(args.source_dir)
    means = _write_performance_outputs(args.output_dir, per_repeat)
    prefetch = _extract_prefetch_events(
        args.source_dir,
        requests_by_wave,
        args.output_dir,
    )
    _write_paper_tables(args.output_dir, means, prefetch)
    (args.output_dir / "retrospective_methodology.json").write_text(
        json.dumps(
            {
                "source_dir": str(args.source_dir),
                "source_files": [
                    "real_e2e_request_results.jsonl",
                    "real_e2e_wave_results.jsonl",
                    "real_e2e_tmp/<request_namespace>/*_timing.log.jsonl",
                ],
                "qps_range": [1, 20],
                "retained_repeats": [0, 1],
                "successful_request_rows": sum(
                    int(row["successful_requests"]) for row in per_repeat
                ),
                "repeat_level_rows": len(per_repeat),
                "qps_mean_rows": len(means),
                "p99_aggregation": (
                    "Nearest-rank P99 over successful requests within each QPS/repeat wave, "
                    "then arithmetic mean of the two repeat-level P99 values."
                ),
                "cumulative_latency_aggregation": (
                    "Per-request cumulative provisioning latency is the sum of worker wait-for-ready "
                    "times. Average across requests within each repeat wave, then arithmetic mean "
                    "across repeats."
                ),
                "resource_aggregation": (
                    "Use peak CPU cores and peak memory GiB recorded for each wave, then arithmetic "
                    "mean across repeats."
                ),
                "configuration_notes": [
                    "Retained runs contain only on_demand, laplace, and always_on modes.",
                    "Laplace has prompt prewarm and predictive warmer enabled together; it maps to the requested +Prefetch stage, but cannot isolate +Prewarm.",
                    "No semantic cache or out-of-band data transmission E2E mode is present in retained runs.",
                    "The two measured modes use the same sampled trace IDs per QPS/repeat and default model parameters; the runner derives a different deterministic API seed per mode.",
                    "The retained run contains two repeats per QPS, not the requested ten.",
                ],
                "prefetch_observation": prefetch,
                "status": "retrospective_partial",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    for filename in (
        "performance_breakdown_per_repeat.csv",
        "performance_breakdown_means_by_qps.csv",
        "prefetch_prediction_events.jsonl",
        "sdg_prefetch_warmup_records.csv",
        "prefetch_metrics_by_qps.csv",
        "prefetch_accuracy_overhead_summary.json",
        "paper_table_performance_qps20.csv",
        "paper_table_prefetch_accuracy_overhead.csv",
        "retrospective_methodology.json",
    ):
        print(args.output_dir / filename)


if __name__ == "__main__":
    main()
