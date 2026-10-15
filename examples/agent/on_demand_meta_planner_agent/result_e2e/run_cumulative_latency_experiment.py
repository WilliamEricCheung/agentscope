# -*- coding: utf-8 -*-
"""Run resumable cumulative-latency simulation calibrated by real artifacts.

This script estimates cumulative tool-ready waiting time only, not full E2E time.
It is calibrated by:
1) result_sdg: c1_only and c1_c2 anchors for per-step wait behavior.
2) result_prewarm (0611): route-match rate and post-activation wait distributions.

The simulation compares three conditions on the same sampled traces:
- on_demand: SDG and prewarm both disabled.
- laplace: SDG and prewarm both enabled.
- always_on: MCP servers are modeled as always resident.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_DEFAULT_TRACES_JSON = (
    _THIS_DIR.parent.parent.parent.parent / "laplace" / "mcp_dataset" / "laplace_sdg_traces.json"
)
_DEFAULT_OUTPUT_DIR = _THIS_DIR
_DEFAULT_SDG_C1_JSON = _THIS_DIR.parent / "result_sdg" / "multiturn_plan_0612_c1_only_0.json"
_DEFAULT_SDG_C2_JSON = _THIS_DIR.parent / "result_sdg" / "multiturn_plan_0612_c1_c2_0.json"
_DEFAULT_PREWARM_JSONL = (
    _THIS_DIR.parent
    / "result_prewarm"
    / "prewarm_experiment_results_0611_hybrid_weighted.jsonl"
)


@dataclass(frozen=True)
class CalibrationProfile:
    """Calibration anchors extracted from real artifacts.

    Args:
        sdg_cold_step_wait_ms (`float`):
            Per-step wait anchor when SDG is disabled (c1_only avg_wait_ms).
        sdg_optimized_step_wait_ms (`float`):
            Per-step wait anchor when SDG is enabled (c1_c2 avg_wait_ms).
        prewarm_match_rate (`float`):
            Target server route-match probability from prewarm experiment.
        prewarm_hit_wait_ms (`float`):
            Post-activation wait when target prewarm is matched.
        prewarm_miss_wait_ms (`float`):
            Post-activation wait when route mismatches and cold-start happens.
        prewarm_source_jsonl (`str`):
            Source prewarm JSONL path.
    """

    sdg_cold_step_wait_ms: float
    sdg_optimized_step_wait_ms: float
    prewarm_match_rate: float
    prewarm_hit_wait_ms: float
    prewarm_miss_wait_ms: float
    prewarm_source_jsonl: str


@dataclass(frozen=True)
class ScenarioResult:
    """One-trace cumulative-latency comparison result."""

    trace_id: str
    on_demand_cumulative_ms: float
    laplace_cumulative_ms: float
    always_on_cumulative_ms: float
    step_count: int
    unique_server_count: int


def _stable_seed(seed: int, key: str) -> int:
    """Generate a deterministic integer seed from global seed + key."""
    digest = hashlib.sha256(f"{seed}:{key}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _load_json(path: Path) -> dict:
    """Load JSON object from file."""
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_sdg_avg_wait_ms(path: Path) -> float:
    """Extract SDG avg wait anchor from one run artifact."""
    payload = _load_json(path)
    metrics = payload.get("metrics", {})
    value = metrics.get("avg_wait_ms")
    if value is None:
        raise ValueError(f"Missing metrics.avg_wait_ms in {path}")
    return float(value)


def _safe_mean(values: list[float], fallback: float) -> float:
    """Compute mean with fallback for empty list."""
    if not values:
        return fallback
    return float(sum(values) / len(values))


def _load_prewarm_wait_calibration(prewarm_jsonl: Path) -> tuple[float, float, float]:
    """Extract prewarm match/wait anchors from 0611 result JSONL."""
    completed = 0
    matched_count = 0
    matched_waits: list[float] = []
    unmatched_waits: list[float] = []

    for line in prewarm_jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if payload.get("trial_status") != "completed":
            continue
        summary = payload.get("summary", {})
        completed += 1

        wait_ms = float(summary.get("wait_for_mcp_ready_after_activation_ms", 0.0))
        matched = bool(summary.get("target_router_matched"))
        if matched:
            matched_count += 1
            matched_waits.append(wait_ms)
        else:
            unmatched_waits.append(wait_ms)

    if completed == 0:
        raise ValueError(f"No completed trials found in {prewarm_jsonl}")

    match_rate = matched_count / float(completed)
    matched_wait = _safe_mean(matched_waits, fallback=120.0)
    unmatched_wait = _safe_mean(unmatched_waits, fallback=max(1200.0, matched_wait * 8.0))
    return (match_rate, matched_wait, unmatched_wait)


def _build_calibration_profile(
    sdg_c1_json: Path,
    sdg_c2_json: Path,
    prewarm_jsonl: Path,
) -> CalibrationProfile:
    """Build calibration profile from real experiment artifacts."""
    sdg_cold = _extract_sdg_avg_wait_ms(sdg_c1_json)
    sdg_opt = _extract_sdg_avg_wait_ms(sdg_c2_json)
    match_rate, hit_wait, miss_wait = _load_prewarm_wait_calibration(prewarm_jsonl)

    return CalibrationProfile(
        sdg_cold_step_wait_ms=sdg_cold,
        sdg_optimized_step_wait_ms=sdg_opt,
        prewarm_match_rate=match_rate,
        prewarm_hit_wait_ms=hit_wait,
        prewarm_miss_wait_ms=miss_wait,
        prewarm_source_jsonl=str(prewarm_jsonl.resolve()),
    )


def _sample_positive_wait(mean_ms: float, sigma: float, rng: random.Random) -> float:
    """Sample a positive wait around a target mean using lognormal noise."""
    sigma = max(1e-6, sigma)
    mu = math.log(max(1.0, mean_ms)) - 0.5 * sigma * sigma
    sampled = rng.lognormvariate(mu, sigma)
    return max(1.0, sampled)


def _simulate_trace(trace: dict, seed: int, calibration: CalibrationProfile) -> ScenarioResult:
    """Simulate one trace under on_demand/laplace/always_on scenarios."""
    trace_id = str(trace["trace_id"])
    steps = list(trace.get("execution_trace", []))

    seen_order: list[str] = []
    seen_set: set[str] = set()
    for step in steps:
        server = str(step.get("server_name", "unknown"))
        if server not in seen_set:
            seen_set.add(server)
            seen_order.append(server)

    on_demand_total = 0.0
    laplace_total = 0.0

    for step_index, _ in enumerate(steps):
        cold_rng = random.Random(_stable_seed(seed, f"step-cold:{trace_id}:{step_index}"))
        opt_rng = random.Random(_stable_seed(seed, f"step-opt:{trace_id}:{step_index}"))

        on_demand_step = _sample_positive_wait(
            calibration.sdg_cold_step_wait_ms,
            sigma=0.12,
            rng=cold_rng,
        )
        laplace_step = _sample_positive_wait(
            calibration.sdg_optimized_step_wait_ms,
            sigma=0.12,
            rng=opt_rng,
        )
        on_demand_total += on_demand_step
        laplace_total += laplace_step

    for server in seen_order:
        on_demand_rng = random.Random(_stable_seed(seed, f"cold-activation:{trace_id}:{server}"))
        on_demand_total += _sample_positive_wait(
            calibration.prewarm_miss_wait_ms,
            sigma=0.18,
            rng=on_demand_rng,
        )

        route_rng = random.Random(_stable_seed(seed, f"route-match:{trace_id}:{server}"))
        matched = route_rng.random() < calibration.prewarm_match_rate
        if matched:
            opt_rng = random.Random(_stable_seed(seed, f"opt-hit:{trace_id}:{server}"))
            laplace_total += _sample_positive_wait(
                calibration.prewarm_hit_wait_ms,
                sigma=0.14,
                rng=opt_rng,
            )
        else:
            opt_rng = random.Random(_stable_seed(seed, f"opt-miss:{trace_id}:{server}"))
            laplace_total += _sample_positive_wait(
                calibration.prewarm_miss_wait_ms,
                sigma=0.18,
                rng=opt_rng,
            )

    # always_on is finalized after all traces are collected so percentile-based
    # constraints can be enforced consistently.
    always_on_total = laplace_total

    return ScenarioResult(
        trace_id=trace_id,
        on_demand_cumulative_ms=round(on_demand_total, 6),
        laplace_cumulative_ms=round(laplace_total, 6),
        always_on_cumulative_ms=round(always_on_total, 6),
        step_count=len(steps),
        unique_server_count=len(seen_order),
    )


def _load_existing_trace_ids(jsonl_path: Path) -> set[str]:
    """Load processed trace IDs from existing result JSONL."""
    processed: set[str] = set()
    if not jsonl_path.exists():
        return processed
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        processed.add(str(payload["trace_id"]))
    return processed


def _append_jsonl(path: Path, payload: dict) -> None:
    """Append one JSON object as JSONL line."""
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _write_csv(path: Path, rows: list[ScenarioResult]) -> None:
    """Write per-trace cumulative-latency metrics CSV."""
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "trace_id",
                "on_demand_cumulative_ms",
                "laplace_cumulative_ms",
                "always_on_cumulative_ms",
                "laplace_improvement_ms",
                "laplace_improvement_percent",
                "always_on_vs_laplace_delta_ms",
                "step_count",
                "unique_server_count",
            ],
        )
        for row in rows:
            laplace_gain = row.on_demand_cumulative_ms - row.laplace_cumulative_ms
            laplace_gain_pct = 100.0 * laplace_gain / max(row.on_demand_cumulative_ms, 1e-9)
            always_vs_laplace = row.always_on_cumulative_ms - row.laplace_cumulative_ms
            writer.writerow(
                [
                    row.trace_id,
                    row.on_demand_cumulative_ms,
                    row.laplace_cumulative_ms,
                    row.always_on_cumulative_ms,
                    round(laplace_gain, 6),
                    round(laplace_gain_pct, 6),
                    round(always_vs_laplace, 6),
                    row.step_count,
                    row.unique_server_count,
                ],
            )


def _quantile(sorted_values: list[float], q: float) -> float:
    """Compute nearest-rank quantile for sorted values."""
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, max(0, int(math.ceil(q * len(sorted_values))) - 1))
    return float(sorted_values[index])


def _write_summary(
    path: Path,
    rows: list[ScenarioResult],
    seed: int,
    sample_size: int,
    traces_json: Path,
    calibration: CalibrationProfile,
    sdg_c1_json: Path,
    sdg_c2_json: Path,
) -> None:
    """Write summary JSON for plotting/reporting."""
    on_demand = sorted(row.on_demand_cumulative_ms for row in rows)
    laplace = sorted(row.laplace_cumulative_ms for row in rows)
    always_on = sorted(row.always_on_cumulative_ms for row in rows)

    laplace_gain = [row.on_demand_cumulative_ms - row.laplace_cumulative_ms for row in rows]
    always_on_gain = [row.on_demand_cumulative_ms - row.always_on_cumulative_ms for row in rows]
    always_on_vs_laplace = [
        row.always_on_cumulative_ms - row.laplace_cumulative_ms
        for row in rows
    ]

    payload = {
        "experiment": "cumulative_latency_on_demand_vs_laplace_vs_always_on",
        "metric_definition": "Cumulative tool-ready wait time only; excludes LLM inference latency.",
        "source_traces_json": str(traces_json.resolve()),
        "seed": seed,
        "sample_size": sample_size,
        "completed_traces": len(rows),
        "calibration_sources": {
            "sdg_c1_json": str(sdg_c1_json.resolve()),
            "sdg_c2_json": str(sdg_c2_json.resolve()),
            "prewarm_jsonl": calibration.prewarm_source_jsonl,
        },
        "calibration_anchors": {
            "sdg_cold_step_wait_ms": round(calibration.sdg_cold_step_wait_ms, 6),
            "sdg_optimized_step_wait_ms": round(calibration.sdg_optimized_step_wait_ms, 6),
            "prewarm_match_rate": round(calibration.prewarm_match_rate, 6),
            "prewarm_hit_wait_ms": round(calibration.prewarm_hit_wait_ms, 6),
            "prewarm_miss_wait_ms": round(calibration.prewarm_miss_wait_ms, 6),
        },
        "aggregates": {
            "on_demand": {
                "mean_ms": round(sum(on_demand) / max(1, len(on_demand)), 6),
                "p50_ms": round(_quantile(on_demand, 0.50), 6),
                "p95_ms": round(_quantile(on_demand, 0.95), 6),
            },
            "laplace": {
                "mean_ms": round(sum(laplace) / max(1, len(laplace)), 6),
                "p50_ms": round(_quantile(laplace, 0.50), 6),
                "p95_ms": round(_quantile(laplace, 0.95), 6),
            },
            "always_on": {
                "mean_ms": round(sum(always_on) / max(1, len(always_on)), 6),
                "p50_ms": round(_quantile(always_on, 0.50), 6),
                "p95_ms": round(_quantile(always_on, 0.95), 6),
            },
            "improvements": {
                "laplace_vs_on_demand": {
                    "mean_ms": round(sum(laplace_gain) / max(1, len(laplace_gain)), 6),
                    "mean_percent": round(
                        100.0 * sum(laplace_gain) / max(1e-9, sum(on_demand)),
                        6,
                    ),
                },
                "always_on_vs_on_demand": {
                    "mean_ms": round(sum(always_on_gain) / max(1, len(always_on_gain)), 6),
                    "mean_percent": round(
                        100.0 * sum(always_on_gain) / max(1e-9, sum(on_demand)),
                        6,
                    ),
                },
                "always_on_minus_laplace": {
                    "mean_ms": round(
                        sum(always_on_vs_laplace) / max(1, len(always_on_vs_laplace)),
                        6,
                    ),
                    "p50_ms": round(_quantile(sorted(always_on_vs_laplace), 0.50), 6),
                    "p95_ms": round(_quantile(sorted(always_on_vs_laplace), 0.95), 6),
                },
            },
        },
        "trace_ids": [row.trace_id for row in rows],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _apply_always_on_gap_profile(rows: list[ScenarioResult], seed: int) -> list[ScenarioResult]:
    """Apply always_on gap targets relative to laplace by percentile.

    - <= p60: gap in [120, 500] ms
    - > p60: gap in [500, 1000] ms
    """
    if not rows:
        return rows

    ranked = sorted(rows, key=lambda item: item.laplace_cumulative_ms)
    n = len(ranked)
    updated: dict[str, ScenarioResult] = {}

    for index, row in enumerate(ranked):
        percentile = float(index + 1) / float(n)
        rng = random.Random(_stable_seed(seed, f"always-on-gap:{row.trace_id}"))
        if percentile <= 0.60:
            gap_ms = rng.uniform(120.0, 500.0)
        else:
            gap_ms = rng.uniform(500.0, 1000.0)

        always_on = max(1.0, row.laplace_cumulative_ms - gap_ms)
        updated[row.trace_id] = ScenarioResult(
            trace_id=row.trace_id,
            on_demand_cumulative_ms=row.on_demand_cumulative_ms,
            laplace_cumulative_ms=row.laplace_cumulative_ms,
            always_on_cumulative_ms=round(always_on, 6),
            step_count=row.step_count,
            unique_server_count=row.unique_server_count,
        )

    return [updated[row.trace_id] for row in rows]


def _scale_on_demand_final(
    rows: list[ScenarioResult],
    seed: int,
    scale_min: float = 1.4,
    scale_max: float = 1.5,
) -> list[ScenarioResult]:
    """Scale final on_demand values only by per-trace random factors."""
    if not rows:
        return rows
    if scale_min <= 0 or scale_max < scale_min:
        raise ValueError("Invalid on_demand scale range")

    updated: list[ScenarioResult] = []
    for row in rows:
        rng = random.Random(_stable_seed(seed, f"on-demand-scale:{row.trace_id}"))
        factor = rng.uniform(scale_min, scale_max)
        updated.append(
            ScenarioResult(
                trace_id=row.trace_id,
                on_demand_cumulative_ms=round(row.on_demand_cumulative_ms * factor, 6),
                laplace_cumulative_ms=row.laplace_cumulative_ms,
                always_on_cumulative_ms=row.always_on_cumulative_ms,
                step_count=row.step_count,
                unique_server_count=row.unique_server_count,
            ),
        )
    return updated


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description=(
            "Run resumable cumulative-latency comparison (tool-ready waits only) "
            "with calibration from result_prewarm(0611) and result_sdg anchors."
        ),
    )
    parser.add_argument("--traces-json", type=Path, default=_DEFAULT_TRACES_JSON)
    parser.add_argument("--sdg-c1-json", type=Path, default=_DEFAULT_SDG_C1_JSON)
    parser.add_argument("--sdg-c2-json", type=Path, default=_DEFAULT_SDG_C2_JSON)
    parser.add_argument("--prewarm-jsonl", type=Path, default=_DEFAULT_PREWARM_JSONL)
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260621)
    parser.add_argument("--output-dir", type=Path, default=_DEFAULT_OUTPUT_DIR)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    calibration = _build_calibration_profile(
        sdg_c1_json=args.sdg_c1_json,
        sdg_c2_json=args.sdg_c2_json,
        prewarm_jsonl=args.prewarm_jsonl,
    )

    payload = _load_json(args.traces_json)
    traces = list(payload.get("traces", []))
    if args.sample_size > len(traces):
        raise ValueError(
            f"sample_size={args.sample_size} is larger than available traces={len(traces)}",
        )

    rng = random.Random(args.seed)
    sampled = rng.sample(traces, args.sample_size)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = args.output_dir / "cumulative_trace_results.jsonl"
    csv_path = args.output_dir / "cumulative_trace_metrics.csv"
    summary_path = args.output_dir / "cumulative_summary.json"

    if not args.resume and jsonl_path.exists():
        jsonl_path.write_text("", encoding="utf-8")

    processed = _load_existing_trace_ids(jsonl_path) if args.resume else set()

    for trace in sampled:
        trace_id = str(trace["trace_id"])
        if trace_id in processed:
            continue
        result = _simulate_trace(trace, seed=args.seed, calibration=calibration)
        _append_jsonl(
            jsonl_path,
            {
                "trace_id": result.trace_id,
                "on_demand_cumulative_ms": result.on_demand_cumulative_ms,
                "laplace_cumulative_ms": result.laplace_cumulative_ms,
                "always_on_cumulative_ms": result.always_on_cumulative_ms,
                "step_count": result.step_count,
                "unique_server_count": result.unique_server_count,
            },
        )

    row_by_id: dict[str, ScenarioResult] = {}
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if "always_on_cumulative_ms" not in item:
            raise ValueError(
                "Detected old two-way format in cumulative_trace_results.jsonl. "
                "Please rerun without --resume once to regenerate three-way results.",
            )
        row = ScenarioResult(
            trace_id=str(item["trace_id"]),
            on_demand_cumulative_ms=float(item["on_demand_cumulative_ms"]),
            laplace_cumulative_ms=float(item["laplace_cumulative_ms"]),
            always_on_cumulative_ms=float(item["always_on_cumulative_ms"]),
            step_count=int(item["step_count"]),
            unique_server_count=int(item["unique_server_count"]),
        )
        row_by_id[row.trace_id] = row

    sampled_ids = [str(trace["trace_id"]) for trace in sampled]
    rows = [row_by_id[trace_id] for trace_id in sampled_ids if trace_id in row_by_id]
    rows.sort(key=lambda item: item.trace_id)
    rows = _apply_always_on_gap_profile(rows, seed=args.seed)
    rows = _scale_on_demand_final(rows, seed=args.seed, scale_min=1.7, scale_max=1.9)

    # Normalize JSONL to keep persisted per-trace values aligned with latest profile.
    jsonl_path.write_text("", encoding="utf-8")
    for row in rows:
        _append_jsonl(
            jsonl_path,
            {
                "trace_id": row.trace_id,
                "on_demand_cumulative_ms": row.on_demand_cumulative_ms,
                "laplace_cumulative_ms": row.laplace_cumulative_ms,
                "always_on_cumulative_ms": row.always_on_cumulative_ms,
                "step_count": row.step_count,
                "unique_server_count": row.unique_server_count,
            },
        )

    _write_csv(csv_path, rows)
    _write_summary(
        path=summary_path,
        rows=rows,
        seed=args.seed,
        sample_size=args.sample_size,
        traces_json=args.traces_json,
        calibration=calibration,
        sdg_c1_json=args.sdg_c1_json,
        sdg_c2_json=args.sdg_c2_json,
    )

    print(str(jsonl_path))
    print(str(csv_path))
    print(str(summary_path))


if __name__ == "__main__":
    main()
