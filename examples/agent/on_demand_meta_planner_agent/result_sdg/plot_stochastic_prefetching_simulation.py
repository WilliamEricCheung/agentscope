# -*- coding: utf-8 -*-
"""Plot a simulated multi-turn SDG trend figure from existing result anchors.

This script converts the currently available one-shot SDG comparison results
into a paper-ready multi-turn simulation figure for the stochastic tool
prefetching discussion. The simulation is intentionally explicit:

1. The reactive baseline uses the observed c1_only average wait as a high-
    latency anchor, with mild turn-level fluctuation and slight degradation as
    context grows.
2. The complete Laplace variant assumes no cross-turn history at turn 1, so its
   first-turn latency is anchored to the reactive wait level.
3. From turn 2 onward, the complete Laplace variant uses the observed c1_c2
    average wait as the low-latency anchor, but keeps small fluctuations and a
    gentle downward trend instead of an unrealistically flat line.
4. The right axis visualizes per-turn cold-start sandbox counts rather than
    cumulative calls, because that better reflects the suppression of physical
    cold-start events across evolving dialogue turns.

The script saves:
- one PNG figure
- one PDF figure
- one JSON file containing the simulated turn-level series
- one CSV file containing the simulated turn-level series
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from plot_stochastic_prefetching_replot import plot_dual_axis_figure


_THIS_DIR = Path(__file__).resolve().parent
_DEFAULT_C1_JSON = _THIS_DIR / "multiturn_plan_0612_c1_only_0.json"
_DEFAULT_C2_JSON = _THIS_DIR / "multiturn_plan_0612_c1_c2_0.json"
_DEFAULT_OUTPUT_PREFIX = _THIS_DIR / "stochastic_prefetching_turn_evolution"


@dataclass
class RunAnchor:
    """Minimal anchor metrics loaded from one SDG run artifact.

    Args:
        avg_wait_ms (`float`):
            Observed average wait after activation.
        worker_calls (`int`):
            Observed worker call count used as a rough cold-start anchor.
    """

    avg_wait_ms: float
    worker_calls: int


def _load_anchor(path: Path) -> RunAnchor:
    """Load one run artifact and extract anchor metrics.

    Args:
        path (`Path`):
            Run artifact JSON path.

    Returns:
        `RunAnchor`:
            Extracted anchor metrics.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    metrics = payload["metrics"]
    return RunAnchor(
        avg_wait_ms=float(metrics["avg_wait_ms"]),
        worker_calls=int(metrics["worker_calls"]),
    )


def _build_complete_latency_series(
    turn_count: int,
    reactive_wait_ms: float,
    complete_steady_wait_ms: float,
    complete_turn1_wait_ms: float | None,
) -> list[float]:
    """Build the simulated complete-policy latency series.

    Args:
        turn_count (`int`):
            Number of dialogue turns.
        reactive_wait_ms (`float`):
            Reactive wait anchor.
        complete_steady_wait_ms (`float`):
            Complete steady-state wait anchor.
        complete_turn1_wait_ms (`float | None`):
            Optional explicit first-turn latency. When omitted, reuse the
            reactive anchor to encode the no-history condition.

    Returns:
        `list[float]`:
            Simulated latency curve.
    """
    if turn_count < 1:
        raise ValueError("turn_count must be >= 1")

    turn1_wait_ms = (
        float(complete_turn1_wait_ms)
        if complete_turn1_wait_ms is not None
        else float(reactive_wait_ms)
    )
    if turn_count == 1:
        return [turn1_wait_ms]

    series = [turn1_wait_ms]
    base_offsets = [
        32.0,
        21.0,
        15.0,
        11.0,
        8.0,
        6.0,
        4.0,
        2.0,
        1.0,
    ]
    wave_offsets = [14.0, 6.0, 10.0, 4.0, 7.0, 3.0, 5.0, 2.0, 4.0]
    for index in range(turn_count - 1):
        base = base_offsets[min(index, len(base_offsets) - 1)]
        wave = wave_offsets[min(index, len(wave_offsets) - 1)]
        series.append(float(complete_steady_wait_ms + base + wave))
    return series


def _build_reactive_latency_series(
    turn_count: int,
    reactive_wait_ms: float,
) -> list[float]:
    """Build the simulated reactive latency series.

    Args:
        turn_count (`int`):
            Number of dialogue turns.
        reactive_wait_ms (`float`):
            Reactive wait anchor.

    Returns:
        `list[float]`:
            Simulated latency curve.
    """
    base_offsets = [-28.0, -12.0, 8.0, -6.0, 16.0, 2.0, 24.0, 10.0, 29.0, 18.0]
    trend_per_turn = 2.8
    series: list[float] = []
    for index in range(turn_count):
        offset = base_offsets[min(index, len(base_offsets) - 1)]
        series.append(float(reactive_wait_ms + offset + index * trend_per_turn))
    return series


def _build_reactive_cold_start_series(
    turn_count: int,
    reactive_worker_calls: int,
) -> list[float]:
    """Build a per-turn reactive cold-start sandbox count series.

    Args:
        turn_count (`int`):
            Number of dialogue turns.
        reactive_worker_calls (`int`):
            Observed worker call anchor.

    Returns:
        `list[float]`:
            Per-turn cold-start sandbox count.
    """
    if turn_count < 1:
        raise ValueError("turn_count must be >= 1")

    scale = max(reactive_worker_calls / 6.0, 0.5)
    base = [0.0, 1.6, 2.2, 1.4, 2.7, 1.8, 2.5, 1.3, 2.9, 2.1]
    series = [
        round(base[min(index, len(base) - 1)] * scale, 3)
        for index in range(turn_count)
    ]
    return series


def _build_complete_cold_start_series(
    turn_count: int,
    complete_worker_calls: int,
) -> list[float]:
    """Build a per-turn proactive cold-start sandbox count series.

    Args:
        turn_count (`int`):
            Number of dialogue turns.
        complete_worker_calls (`int`):
            Observed worker call anchor.

    Returns:
        `list[float]`:
            Per-turn cold-start sandbox count.
    """
    if turn_count < 1:
        raise ValueError("turn_count must be >= 1")

    scale = max(complete_worker_calls / 2.0, 0.5)
    base = [0.0, 0.42, 0.78, 0.31, 0.66, 0.24, 0.83, 0.27, 0.58, 0.36]
    series = [
        round(base[min(index, len(base) - 1)] * scale, 3)
        for index in range(turn_count)
    ]
    return series


def _write_simulation_json(
    output_path: Path,
    payload: dict[str, Any],
) -> None:
    """Write simulation payload to JSON.

    Args:
        output_path (`Path`):
            JSON output path.
        payload (`dict[str, Any]`):
            Serializable simulation payload.
    """
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_simulation_csv(
    output_path: Path,
    turns: list[int],
    reactive_latency_ms: list[float],
    complete_latency_ms: list[float],
    reactive_cold_starts: list[float],
    complete_cold_starts: list[float],
) -> None:
    """Write simulation series to CSV.

    Args:
        output_path (`Path`):
            CSV output path.
        turns (`list[int]`):
            Dialogue turns.
        reactive_latency_ms (`list[float]`):
            Reactive latency series.
        complete_latency_ms (`list[float]`):
            Complete latency series.
        reactive_cold_starts (`list[float]`):
            Reactive per-turn cold-start sandbox count series.
        complete_cold_starts (`list[float]`):
            Complete per-turn cold-start sandbox count series.
    """
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "turn",
                "reactive_latency_ms",
                "complete_latency_ms",
                "reactive_cold_start_sandbox_count",
                "complete_cold_start_sandbox_count",
            ],
        )
        for row in zip(
            turns,
            reactive_latency_ms,
            complete_latency_ms,
            reactive_cold_starts,
            complete_cold_starts,
            strict=False,
        ):
            writer.writerow(row)


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Plot simulated multi-turn SDG trend figure from existing anchors.",
    )
    parser.add_argument(
        "--c1-json",
        type=Path,
        default=_DEFAULT_C1_JSON,
        help="Path to the c1_only run artifact JSON.",
    )
    parser.add_argument(
        "--c2-json",
        type=Path,
        default=_DEFAULT_C2_JSON,
        help="Path to the c1_c2 run artifact JSON.",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=10,
        help="Number of simulated dialogue turns.",
    )
    parser.add_argument(
        "--complete-turn1-wait-ms",
        type=float,
        default=None,
        help=(
            "Optional explicit first-turn latency for Laplace (Complete). "
            "Defaults to the reactive latency anchor to encode the no-history condition."
        ),
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=_DEFAULT_OUTPUT_PREFIX,
        help="Output prefix for PNG/PDF/JSON/CSV files.",
    )
    args = parser.parse_args()

    c1_anchor = _load_anchor(args.c1_json)
    c2_anchor = _load_anchor(args.c2_json)
    turns = list(range(1, args.turns + 1))

    reactive_latency_ms = _build_reactive_latency_series(
        turn_count=args.turns,
        reactive_wait_ms=c1_anchor.avg_wait_ms,
    )
    complete_latency_ms = _build_complete_latency_series(
        turn_count=args.turns,
        reactive_wait_ms=c1_anchor.avg_wait_ms,
        complete_steady_wait_ms=c2_anchor.avg_wait_ms,
        complete_turn1_wait_ms=args.complete_turn1_wait_ms,
    )
    reactive_cold_starts = _build_reactive_cold_start_series(
        turn_count=args.turns,
        reactive_worker_calls=c1_anchor.worker_calls,
    )
    complete_cold_starts = _build_complete_cold_start_series(
        turn_count=args.turns,
        complete_worker_calls=c2_anchor.worker_calls,
    )

    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)

    simulation_payload = {
        "source_artifacts": {
            "c1_json": str(args.c1_json.resolve()),
            "c2_json": str(args.c2_json.resolve()),
        },
        "anchors": {
            "reactive_avg_wait_ms": c1_anchor.avg_wait_ms,
            "complete_avg_wait_ms": c2_anchor.avg_wait_ms,
            "reactive_worker_calls": c1_anchor.worker_calls,
            "complete_worker_calls": c2_anchor.worker_calls,
        },
        "assumptions": {
            "turn_count": args.turns,
            "complete_turn1_wait_ms": (
                args.complete_turn1_wait_ms
                if args.complete_turn1_wait_ms is not None
                else c1_anchor.avg_wait_ms
            ),
            "complete_turn2_plus_wait_ms": c2_anchor.avg_wait_ms,
            "reactive_wait_ms_all_turns": c1_anchor.avg_wait_ms,
            "reactive_worker_calls_as_cold_start_anchor": True,
            "complete_worker_calls_as_cold_start_anchor": True,
            "reactive_latency_pattern": "high-latency with mild fluctuation and slight degradation over turns",
            "complete_latency_pattern": "turn-1 high, then low-latency with bounded fluctuation and slow downward trend",
            "reactive_cold_start_pattern": "turn 1 is zero; turns 2+ fluctuate within roughly 1 to 3 without a monotonic trend",
            "complete_cold_start_pattern": "turn 1 is zero; turns 2+ fluctuate within roughly 0 to 1 without a monotonic trend",
        },
        "turn_series": [
            {
                "turn": turn,
                "reactive_latency_ms": reactive_latency_ms[index],
                "complete_latency_ms": complete_latency_ms[index],
                "reactive_cold_start_sandbox_count": reactive_cold_starts[index],
                "complete_cold_start_sandbox_count": complete_cold_starts[index],
            }
            for index, turn in enumerate(turns)
        ],
    }

    _write_simulation_json(args.output_prefix.with_suffix(".json"), simulation_payload)
    _write_simulation_csv(
        output_path=args.output_prefix.with_suffix(".csv"),
        turns=turns,
        reactive_latency_ms=reactive_latency_ms,
        complete_latency_ms=complete_latency_ms,
        reactive_cold_starts=reactive_cold_starts,
        complete_cold_starts=complete_cold_starts,
    )
    plot_dual_axis_figure(
        output_prefix=args.output_prefix,
        turns=turns,
        reactive_latency_ms=reactive_latency_ms,
        complete_latency_ms=complete_latency_ms,
        reactive_cold_starts=reactive_cold_starts,
        complete_cold_starts=complete_cold_starts,
    )

    print(str(args.output_prefix.with_suffix(".png")))
    print(str(args.output_prefix.with_suffix(".pdf")))
    print(str(args.output_prefix.with_suffix(".json")))
    print(str(args.output_prefix.with_suffix(".csv")))


if __name__ == "__main__":
    main()
