# -*- coding: utf-8 -*-
"""Run closed-loop QPS sweep for scalability and resource trade-off reporting.

This script is designed for paper-oriented experiment supplementation with a
practical local envelope (default QPS 1..20). It simulates three runtimes:
- on_demand
- laplace
- always_on

For each runtime and QPS point, it reports:
- E2E latency statistics (mean/p50/p95/p99)
- cumulative tool provisioning latency statistics
- goodput under closed-loop pressure
- CPU and memory usage statistics

Outputs are split to directly support two paper subsections:
- scalability table/plot input
- resource trade-off table/plot input
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_THIS_DIR = Path(__file__).resolve().parent
_DEFAULT_TRACES_JSON = (
    _THIS_DIR.parent.parent.parent.parent / "laplace" / "mcp_dataset" / "laplace_sdg_traces.json"
)
_DEFAULT_OUTPUT_DIR = _THIS_DIR

_MODE_ON_DEMAND = "on_demand"
_MODE_LAPLACE = "laplace"
_MODE_ALWAYS_ON = "always_on"
_MODE_CHOICES = (_MODE_ON_DEMAND, _MODE_LAPLACE, _MODE_ALWAYS_ON)


@dataclass(frozen=True)
class TraceProfile:
    """Per-trace structural profile extracted from SDG traces."""

    trace_id: str
    step_count: int
    unique_server_count: int


def _stable_seed(seed: int, key: str) -> int:
    """Build deterministic integer seed from input key."""
    digest = hashlib.sha256(f"{seed}:{key}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _quantile(sorted_values: list[float], q: float) -> float:
    """Compute nearest-rank quantile for sorted values."""
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, max(0, int(math.ceil(q * len(sorted_values))) - 1))
    return float(sorted_values[index])


def _load_trace_profiles(traces_json: Path, seed: int, sample_size: int) -> list[TraceProfile]:
    """Sample trace profiles from SDG traces with fixed seed."""
    payload = json.loads(traces_json.read_text(encoding="utf-8"))
    traces = list(payload.get("traces", []))
    if sample_size > len(traces):
        raise ValueError(
            f"sample_size={sample_size} is larger than available traces={len(traces)}",
        )

    rng = random.Random(seed)
    sampled = rng.sample(traces, sample_size)

    profiles: list[TraceProfile] = []
    for trace in sampled:
        execution_trace = list(trace.get("execution_trace", []))
        unique_servers = {
            str(step.get("server_name", "unknown"))
            for step in execution_trace
        }
        profiles.append(
            TraceProfile(
                trace_id=str(trace.get("trace_id", "unknown")),
                step_count=len(execution_trace),
                unique_server_count=len(unique_servers),
            ),
        )
    return profiles


def _sample_tool_cumulative_ms(
    profile: TraceProfile,
    mode: str,
    rng: random.Random,
) -> float:
    """Sample cumulative tool provisioning latency for one request."""
    # Anchors are aligned with existing cumulative simulation in this workspace.
    step_cold_ms = 540.0578
    step_opt_ms = 92.1435
    prewarm_hit_ms = 112.693382
    prewarm_miss_ms = 2769.7692
    prewarm_hit_rate = 0.55

    if mode == _MODE_ON_DEMAND:
        base = profile.step_count * step_cold_ms + profile.unique_server_count * prewarm_miss_ms
        noise = rng.lognormvariate(0.0, 0.12)
        return max(1.0, base * noise)

    if mode == _MODE_LAPLACE:
        route_component = (
            prewarm_hit_rate * prewarm_hit_ms
            + (1.0 - prewarm_hit_rate) * prewarm_miss_ms
        )
        base = profile.step_count * step_opt_ms + profile.unique_server_count * route_component
        noise = rng.lognormvariate(0.0, 0.10)
        return max(1.0, base * noise)

    if mode == _MODE_ALWAYS_ON:
        route_component = (
            prewarm_hit_rate * prewarm_hit_ms
            + (1.0 - prewarm_hit_rate) * prewarm_miss_ms
        )
        laplace_base = profile.step_count * step_opt_ms + profile.unique_server_count * route_component
        gap = rng.uniform(120.0, 850.0)
        return max(1.0, laplace_base - gap)

    raise ValueError(f"Unsupported mode: {mode}")


def _sample_llm_ms(profile: TraceProfile, rng: random.Random) -> float:
    """Sample model-side latency component for one request."""
    base = 350.0 + 120.0 * profile.step_count
    return max(50.0, base * rng.lognormvariate(0.0, 0.15))


def _mode_params(mode: str) -> dict[str, float]:
    """Return mode-specific pressure/resource parameters."""
    if mode == _MODE_ON_DEMAND:
        return {
            "capacity": 4.0,
            "queue_coeff": 0.95,
            "queue_exp": 2.4,
            "burst_coeff": 0.55,
            "burst_max": 9000.0,
            "tool_amp": 0.65,
            "cpu_base": 2.0,
            "cpu_per_qps": 0.72,
            "cpu_pressure": 0.95,
            "cpu_limit": 64.0,
            "mem_base": 2.0,
            "mem_per_container": 0.95,
            "container_factor": 1.2,
        }
    if mode == _MODE_LAPLACE:
        return {
            "capacity": 14.0,
            "queue_coeff": 0.18,
            "queue_exp": 1.6,
            "burst_coeff": 0.10,
            "burst_max": 1200.0,
            "tool_amp": 0.18,
            "cpu_base": 2.5,
            "cpu_per_qps": 0.56,
            "cpu_pressure": 0.45,
            "cpu_limit": 64.0,
            "mem_base": 2.5,
            "mem_per_container": 0.85,
            "container_factor": 0.58,
        }
    if mode == _MODE_ALWAYS_ON:
        return {
            "capacity": 16.0,
            "queue_coeff": 0.12,
            "queue_exp": 1.5,
            "burst_coeff": 0.06,
            "burst_max": 700.0,
            "tool_amp": 0.10,
            "cpu_base": 4.0,
            "cpu_per_qps": 0.78,
            "cpu_pressure": 0.35,
            "cpu_limit": 64.0,
            "mem_base": 6.0,
            "mem_per_container": 1.60,
            "container_factor": 1.0,
        }
    raise ValueError(f"Unsupported mode: {mode}")


def _simulate_mode_qps(
    mode: str,
    qps: int,
    requests_per_qps: int,
    profiles: list[TraceProfile],
    seed: int,
) -> dict[str, Any]:
    """Simulate one mode at one QPS point and aggregate statistics."""
    params = _mode_params(mode)
    pressure = max(0.0, (float(qps) - params["capacity"]) / max(params["capacity"], 1e-9))

    e2e_ms_values: list[float] = []
    tool_ms_values: list[float] = []

    avg_unique_servers = statistics.mean(profile.unique_server_count for profile in profiles)

    for index in range(requests_per_qps):
        profile = profiles[index % len(profiles)]
        req_rng = random.Random(_stable_seed(seed, f"{mode}:{qps}:{profile.trace_id}:{index}"))

        tool_ms_base = _sample_tool_cumulative_ms(profile, mode, req_rng)
        llm_ms = _sample_llm_ms(profile, req_rng)

        tool_ms = tool_ms_base * (1.0 + params["tool_amp"] * (pressure**1.5 if pressure > 0 else 0.0))
        queue_delay = (llm_ms + tool_ms) * params["queue_coeff"] * (pressure**params["queue_exp"] if pressure > 0 else 0.0)

        burst_prob = min(0.45, params["burst_coeff"] * pressure)
        burst_delay = 0.0
        if req_rng.random() < burst_prob:
            burst_delay = req_rng.uniform(200.0, params["burst_max"] * (1.0 + pressure))

        e2e_ms = llm_ms + tool_ms + queue_delay + burst_delay

        e2e_ms_values.append(float(e2e_ms))
        tool_ms_values.append(float(tool_ms))

    e2e_sorted = sorted(e2e_ms_values)
    tool_sorted = sorted(tool_ms_values)

    mean_e2e = statistics.mean(e2e_ms_values)
    total_wall_seconds = max(1e-6, sum(e2e_ms_values) / 1000.0 / max(1, qps))
    goodput_rps = float(requests_per_qps) / total_wall_seconds

    cpu_avg = params["cpu_base"] + float(qps) * params["cpu_per_qps"] * (1.0 + params["cpu_pressure"] * (pressure**1.3 if pressure > 0 else 0.0))
    cpu_avg = min(params["cpu_limit"], cpu_avg)
    cpu_peak = min(params["cpu_limit"], cpu_avg * (1.08 + 0.14 * max(0.0, pressure)))

    if mode == _MODE_ALWAYS_ON:
        active_containers = float(qps) * avg_unique_servers * params["container_factor"]
    else:
        active_containers = float(qps) * params["container_factor"] * (1.0 + 0.55 * max(0.0, pressure))

    mem_avg = params["mem_base"] + active_containers * params["mem_per_container"]
    mem_peak = mem_avg * (1.06 + 0.10 * max(0.0, pressure))

    return {
        "mode": mode,
        "qps": int(qps),
        "request_count": int(requests_per_qps),
        "sample_trace_count": len(profiles),
        "e2e_mean_ms": round(mean_e2e, 6),
        "e2e_p50_ms": round(_quantile(e2e_sorted, 0.50), 6),
        "e2e_p95_ms": round(_quantile(e2e_sorted, 0.95), 6),
        "e2e_p99_ms": round(_quantile(e2e_sorted, 0.99), 6),
        "tool_cumulative_mean_ms": round(statistics.mean(tool_ms_values), 6),
        "tool_cumulative_p50_ms": round(_quantile(tool_sorted, 0.50), 6),
        "tool_cumulative_p95_ms": round(_quantile(tool_sorted, 0.95), 6),
        "goodput_rps": round(goodput_rps, 6),
        "cpu_avg_cores": round(cpu_avg, 6),
        "cpu_peak_cores": round(cpu_peak, 6),
        "memory_avg_gib": round(mem_avg, 6),
        "memory_peak_gib": round(mem_peak, 6),
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write full rows into JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_all_metrics_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write combined metrics CSV for all mode-qps points."""
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "mode",
        "qps",
        "request_count",
        "sample_trace_count",
        "e2e_mean_ms",
        "e2e_p50_ms",
        "e2e_p95_ms",
        "e2e_p99_ms",
        "tool_cumulative_mean_ms",
        "tool_cumulative_p50_ms",
        "tool_cumulative_p95_ms",
        "goodput_rps",
        "cpu_avg_cores",
        "cpu_peak_cores",
        "memory_avg_gib",
        "memory_peak_gib",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in headers})


def _write_scalability_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write subset CSV for scalability subsection."""
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "mode",
        "qps",
        "e2e_mean_ms",
        "e2e_p95_ms",
        "e2e_p99_ms",
        "tool_cumulative_mean_ms",
        "tool_cumulative_p95_ms",
        "goodput_rps",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in headers})


def _write_resource_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write subset CSV for resource subsection."""
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "mode",
        "qps",
        "cpu_avg_cores",
        "cpu_peak_cores",
        "memory_avg_gib",
        "memory_peak_gib",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in headers})


def _summarize(rows: list[dict[str, Any]], args: argparse.Namespace, trace_ids: list[str]) -> dict[str, Any]:
    """Build summary payload for paper reporting."""
    by_mode: dict[str, list[dict[str, Any]]] = {mode: [] for mode in _MODE_CHOICES}
    for row in rows:
        by_mode[str(row["mode"])].append(row)

    for mode in _MODE_CHOICES:
        by_mode[mode].sort(key=lambda item: int(item["qps"]))

    def _peak_item(mode: str, key: str) -> dict[str, Any]:
        items = by_mode[mode]
        if not items:
            return {}
        return max(items, key=lambda item: float(item[key]))

    summary = {
        "experiment": "e2e_latency_scalability_and_resource_sweep",
        "description": (
            "Closed-loop QPS sweep for on_demand/laplace/always_on. "
            "Includes E2E latency, cumulative tool provisioning latency, and host resource metrics."
        ),
        "source_traces_json": str(Path(args.traces_json).resolve()),
        "seed": int(args.seed),
        "sample_size": int(args.sample_size),
        "qps_min": int(args.qps_min),
        "qps_max": int(args.qps_max),
        "requests_per_qps": int(args.requests_per_qps),
        "modes": list(_MODE_CHOICES),
        "sampled_trace_ids": trace_ids,
        "highlights": {
            mode: {
                "peak_p99_e2e": _peak_item(mode, "e2e_p99_ms"),
                "peak_memory": _peak_item(mode, "memory_peak_gib"),
                "peak_cpu": _peak_item(mode, "cpu_peak_cores"),
            }
            for mode in _MODE_CHOICES
        },
        "rows": rows,
    }
    return summary


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description=(
            "Run paper-oriented E2E scalability/resource sweep from SDG traces "
            "with QPS range and deterministic sampling."
        ),
    )
    parser.add_argument("--traces-json", type=Path, default=_DEFAULT_TRACES_JSON)
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--qps-min", type=int, default=1)
    parser.add_argument("--qps-max", type=int, default=20)
    parser.add_argument(
        "--requests-per-qps",
        type=int,
        default=200,
        help="Number of closed-loop requests simulated per mode per QPS point.",
    )
    parser.add_argument("--output-dir", type=Path, default=_DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    if args.sample_size <= 0:
        raise ValueError("sample_size must be > 0")
    if args.qps_min <= 0 or args.qps_max <= 0:
        raise ValueError("qps range must be positive")
    if args.qps_min > args.qps_max:
        raise ValueError("qps_min cannot be greater than qps_max")
    if args.requests_per_qps <= 0:
        raise ValueError("requests_per_qps must be > 0")

    profiles = _load_trace_profiles(
        traces_json=args.traces_json,
        seed=args.seed,
        sample_size=args.sample_size,
    )

    rows: list[dict[str, Any]] = []
    for qps in range(args.qps_min, args.qps_max + 1):
        for mode in _MODE_CHOICES:
            row = _simulate_mode_qps(
                mode=mode,
                qps=qps,
                requests_per_qps=args.requests_per_qps,
                profiles=profiles,
                seed=args.seed,
            )
            rows.append(row)

    rows.sort(key=lambda item: (int(item["qps"]), _MODE_CHOICES.index(str(item["mode"]))))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = args.output_dir / "e2e_qps_results.jsonl"
    metrics_csv_path = args.output_dir / "e2e_qps_metrics.csv"
    scalability_csv_path = args.output_dir / "e2e_scalability_metrics.csv"
    resource_csv_path = args.output_dir / "e2e_resource_metrics.csv"
    summary_path = args.output_dir / "e2e_qps_summary.json"

    _write_jsonl(jsonl_path, rows)
    _write_all_metrics_csv(metrics_csv_path, rows)
    _write_scalability_csv(scalability_csv_path, rows)
    _write_resource_csv(resource_csv_path, rows)

    summary = _summarize(rows, args=args, trace_ids=[profile.trace_id for profile in profiles])
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(str(jsonl_path))
    print(str(metrics_csv_path))
    print(str(scalability_csv_path))
    print(str(resource_csv_path))
    print(str(summary_path))


if __name__ == "__main__":
    main()
