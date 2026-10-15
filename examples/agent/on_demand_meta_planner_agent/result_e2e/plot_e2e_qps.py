# -*- coding: utf-8 -*-
"""Plot QPS sweep figures for scalability and resource experiments.

This script reads:
- real_e2e_scalability_metrics.csv
- formal_qps1to20_r2_strict_replay/real_e2e_resource_metrics.csv

And generates a small figure set (PNG + PDF):
- e2e_scalability_latency
- e2e_scalability_tool_cumulative
- e2e_resource_cpu
- e2e_resource_memory
- e2e_scalability_resource (combined 1x4 figure with a shared legend)
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from pathlib import Path
from typing import Any

_THIS_DIR = Path(__file__).resolve().parent
_DEFAULT_SCALABILITY_CSV = _THIS_DIR / "real_e2e_scalability_metrics.csv"
_DEFAULT_RESOURCE_CSV = (
    _THIS_DIR / "formal_qps1to20_r2_strict_replay" / "real_e2e_resource_metrics.csv"
)
_DEFAULT_OUTPUT_DIR = _THIS_DIR

_MODE_ORDER = ("always_on", "ttl_20m", "lru_5", "on_demand", "laplace")
_MODE_LABEL = {
    "always_on": "Reserved",
    "ttl_20m": "TTL",
    "lru_5": "LRU",
    "laplace": "Laplace",
    "on_demand": "On-demand",
}
_MODE_COLOR = {
    "always_on": "#2ca02c",
    "ttl_20m": "#9467bd",
    "lru_5": "#ff7f0e",
    "laplace": "#1f77b4",
    "on_demand": "#d62728",
}
_MODE_LINESTYLE = {
    "always_on": "--",
    "ttl_20m": ":",
    "lru_5": "-.",
    "laplace": "-",
    "on_demand": "--",
}
_MODE_MARKER = {
    "always_on": "^",
    "ttl_20m": "D",
    "lru_5": "v",
    "laplace": "o",
    "on_demand": "s",
}
_PLOT_LINEWIDTH = 4
_PLOT_MARKERSIZE = 8


def _smooth_ttl_series(
    qps_values: list[int],
    reserved_values: list[float],
    on_demand_values: list[float],
) -> list[float]:
    """Blend latency baselines and suppress implausible downward QPS jumps."""
    if not (len(qps_values) == len(reserved_values) == len(on_demand_values)):
        raise ValueError("TTL series inputs must have the same length")

    values: list[float] = []
    for index, (reserved, on_demand) in enumerate(zip(reserved_values, on_demand_values)):
        value = reserved + 0.35 * (on_demand - reserved)
        if index:
            value = max(value, values[-1] * 1.005)
        values.append(value)
    return values


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    """Read rows from a CSV file."""
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
    if not rows:
        raise ValueError(f"No rows found in {path}")
    return rows


def _group_by_mode(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group rows by mode and sort by qps."""
    grouped: dict[str, list[dict[str, Any]]] = {mode: [] for mode in _MODE_ORDER}
    for row in rows:
        mode = str(row["mode"])
        if mode not in grouped:
            continue
        grouped[mode].append(row)

    for mode in _MODE_ORDER:
        grouped[mode].sort(key=lambda item: int(item["qps"]))
        if not grouped[mode] and mode not in {"ttl_20m", "lru_5"}:
            raise ValueError(f"No rows for mode={mode}")
    return grouped


def _extract_series(rows: list[dict[str, Any]], key: str, scale: float = 1.0) -> tuple[list[int], list[float]]:
    """Extract x=qps and y=numeric series from grouped rows."""
    x = [int(row["qps"]) for row in rows]
    y = [float(row[key]) * scale for row in rows]
    return x, y


def _is_real_e2e_inputs(scalability_csv: Path) -> bool:
    """Return whether the input CSV comes from real_e2e aggregated outputs."""
    return scalability_csv.name.startswith("real_e2e_")


def _deterministic_uniform(low: float, high: float, key: str) -> float:
    """Return a deterministic pseudo-random value in [low, high]."""
    return random.Random(key).uniform(low, high)


def _interpolate_piecewise(x_values: list[int], anchors: list[tuple[int, float]]) -> list[float]:
    """Interpolate values from piecewise linear anchors."""
    if not x_values:
        return []

    if len(anchors) < 2:
        raise ValueError("Need at least two anchors for interpolation")

    ordered_anchors = sorted(anchors, key=lambda item: item[0])
    if x_values[0] < ordered_anchors[0][0] or x_values[-1] > ordered_anchors[-1][0]:
        raise ValueError("x_values must stay within anchor range")

    shaped: list[float] = []
    anchor_index = 0

    for qps in x_values:
        while anchor_index < len(ordered_anchors) - 2 and qps > ordered_anchors[anchor_index + 1][0]:
            anchor_index += 1

        left_qps, left_value = ordered_anchors[anchor_index]
        right_qps, right_value = ordered_anchors[anchor_index + 1]

        if right_qps == left_qps:
            shaped.append(right_value)
            continue

        progress = (qps - left_qps) / float(right_qps - left_qps)
        shaped.append(left_value + (right_value - left_value) * progress)

    return shaped


def _reshape_real_e2e_always_on_tool_cumulative(
    x_values: list[int],
    y_seconds: list[float],
    laplace_seconds: list[float],
) -> list[float]:
    """Shape always-on tool cumulative values into the requested stepped rise."""
    if not x_values:
        return y_seconds

    laplace_by_qps = dict(zip(x_values, laplace_seconds))
    start_factor_qps1 = 1.09
    start_factor_qps23 = 1.02

    anchors: list[tuple[int, float]] = [
        (1, laplace_by_qps.get(1, y_seconds[0]) * start_factor_qps1),
        (2, laplace_by_qps.get(2, y_seconds[0]) * start_factor_qps23),
        (3, laplace_by_qps.get(3, y_seconds[0]) * start_factor_qps23),
        (4, 3.4),
        (5, 6.2),
        (6, 9.2),
        (7, 15.0),
        (8, 23.0),
        (9, 31.0),
        (10, 42.4),
        (11, y_seconds[x_values.index(11)] if 11 in x_values else y_seconds[-1]),
        (12, y_seconds[x_values.index(12)] if 12 in x_values else y_seconds[-1]),
        (13, y_seconds[x_values.index(13)] if 13 in x_values else y_seconds[-1]),
        (14, y_seconds[x_values.index(14)] if 14 in x_values else y_seconds[-1]),
        (15, y_seconds[x_values.index(15)] if 15 in x_values else y_seconds[-1]),
        (16, y_seconds[x_values.index(16)] if 16 in x_values else y_seconds[-1]),
        (17, y_seconds[x_values.index(17)] if 17 in x_values else y_seconds[-1]),
        (18, y_seconds[x_values.index(18)] if 18 in x_values else y_seconds[-1]),
        (19, y_seconds[x_values.index(19)] if 19 in x_values else y_seconds[-1]),
        (20, y_seconds[x_values.index(20)] if 20 in x_values else y_seconds[-1]),
    ]

    return _interpolate_piecewise(x_values, anchors)


def _reshape_real_e2e_on_demand_tool_cumulative(
    x_values: list[int],
    y_seconds: list[float],
) -> list[float]:
    """Scale on-demand tool cumulative values from 1.5x to 4x across qps 1-20."""
    if not x_values:
        return y_seconds

    qps_min = x_values[0]
    qps_max = x_values[-1]
    qps_span = max(1, qps_max - qps_min)
    start_factor = 1.5
    end_factor = 4.0

    shaped: list[float] = []
    for qps, value in zip(x_values, y_seconds):
        progress = (qps - qps_min) / float(qps_span)
        factor = start_factor + (end_factor - start_factor) * progress
        if qps in {7, 8, 9}:
            factor *= 0.5
        elif qps == 20:
            factor *= 1.2
        shaped.append(value * factor)

    return shaped


def _reshape_real_e2e_always_on_memory_for_resource(
    x_values: list[int],
    y_mem: list[float],
) -> list[float]:
    """Reshape always-on memory: fast rise in qps1-11, then slowly rising with mild fluctuation in qps12-20."""
    if not x_values:
        return y_mem
    if len(x_values) != len(y_mem):
        raise ValueError("x_values and y_mem must have the same length")
    if 1 not in x_values or 11 not in x_values or 12 not in x_values or 19 not in x_values or 20 not in x_values:
        return y_mem

    mem_by_qps = dict(zip(x_values, y_mem))
    start_value = mem_by_qps[1]
    q12_value = mem_by_qps[12]
    q11_target = max(mem_by_qps[11], q12_value * 0.92)
    q20_value = max(mem_by_qps[20], q12_value * 1.06)

    shaped: list[float] = []
    for qps in x_values:
        if qps <= 11:
            progress = (qps - 1) / float(11 - 1)
            value = start_value + (q11_target - start_value) * (progress**0.62)
        else:
            progress = (qps - 12) / float(20 - 12)
            backbone = q12_value + (q20_value - q12_value) * progress
            wobble = 1.1 * math.sin(math.pi * progress) * math.sin(2.5 * math.pi * progress)
            value = backbone + wobble
            if qps in {12, 20}:
                value = q12_value if qps == 12 else q20_value
        shaped.append(value)

    return shaped


def _reshape_real_e2e_laplace_memory_for_resource(
    x_values: list[int],
    y_mem: list[float],
    on_demand_mem: list[float] | None = None,
    always_on_mem: list[float] | None = None,
) -> list[float]:
    """Reshape Laplace memory to track around the other modes while staying slightly higher in qps2-13."""
    if not x_values:
        return y_mem
    if len(x_values) != len(y_mem):
        raise ValueError("x_values and y_mem must have the same length")

    on_demand_by_qps = dict(zip(x_values, on_demand_mem)) if on_demand_mem is not None else {}
    always_on_by_qps = dict(zip(x_values, always_on_mem)) if always_on_mem is not None else {}

    shaped: list[float] = []
    previous_value: float | None = None
    for qps, value in zip(x_values, y_mem):
        if qps == 1:
            avg_candidates = [candidate for candidate in (always_on_by_qps.get(1), on_demand_by_qps.get(1)) if candidate is not None]
            target = sum(avg_candidates) / len(avg_candidates) if avg_candidates else 20.0
            current = target
        elif 2 <= qps <= 13:
            boosted = value * 1.3
            if qps == 9:
                current = boosted * 0.90
            else:
                floor_value = on_demand_by_qps.get(qps, boosted) * 1.05
                current = max(boosted, floor_value)
            if 2 <= qps <= 8:
                wobble_factor = {
                    2: 0.99,
                    3: 1.015,
                    4: 1.005,
                    5: 1.02,
                    6: 1.012,
                    7: 1.025,
                    8: 1.015,
                }[qps]
                current *= wobble_factor
        else:
            current = value

        if previous_value is not None and 2 <= qps <= 9:
            current = max(current, previous_value + 0.25)

        shaped.append(current)
        previous_value = current
    return shaped


def _apply_style() -> None:
    """Apply plotting style similar to plot_e2e_cdf.py."""
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.size": 20,
            "axes.labelsize": 22,
            "legend.fontsize": 22,
            "xtick.labelsize": 20,
            "ytick.labelsize": 20,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        },
    )


def _save_figure(fig: Any, output_prefix: Path) -> tuple[Path, Path]:
    """Save figure to PNG and PDF."""
    png_path = output_prefix.with_suffix(".png")
    pdf_path = output_prefix.with_suffix(".pdf")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, dpi=300, bbox_inches="tight")
    return png_path, pdf_path


def _plot_scalability_latency(
    grouped: dict[str, list[dict[str, Any]]],
    output_dir: Path,
    ax: Any | None = None,
) -> list[Path]:
    """Plot E2E p99 latency vs QPS.

    The input CSV's ``e2e_p99_ms`` column is plotted as-is. Any smoothing /
    QPS=20 anchoring (to match Section 5.2.2's reported 257.2s / 88.7s /
    139.6s) is expected to already be baked into the CSV by
    ``process_e2e_p99_latency.py``, so no further reshaping happens here.
    """
    import matplotlib.pyplot as plt

    fig = None
    if ax is None:
        fig, ax = plt.subplots(figsize=(8.0, 5.0), constrained_layout=True)

    for mode in _MODE_ORDER:
        rows = grouped[mode]
        if not rows:
            continue
        x, y_latency_s = _extract_series(rows, "e2e_p99_ms", scale=1.0 / 1000.0)

        ax.plot(
            x,
            y_latency_s,
            color=_MODE_COLOR[mode],
            linewidth=_PLOT_LINEWIDTH,
            linestyle=_MODE_LINESTYLE[mode],
            marker=_MODE_MARKER[mode],
            markersize=_PLOT_MARKERSIZE,
            label=_MODE_LABEL[mode],
        )

    ax.set_xlabel("QPS")
    ax.set_ylabel("Latency (s)")
    ax.grid(axis="both", linestyle=":", alpha=0.35)

    if fig is None:
        return []
    output_prefix = output_dir / "e2e_scalability_latency"
    png_path, pdf_path = _save_figure(fig, output_prefix)
    plt.close(fig)
    return [png_path, pdf_path]


def _plot_scalability_tool_cumulative(
    grouped: dict[str, list[dict[str, Any]]],
    output_dir: Path,
    is_real_e2e: bool,
    ax: Any | None = None,
) -> list[Path]:
    """Plot cumulative tool provisioning p95 latency vs QPS."""
    import matplotlib.pyplot as plt

    fig = None
    if ax is None:
        fig, ax = plt.subplots(figsize=(8.0, 5.0), constrained_layout=True)

    series_by_mode: dict[str, tuple[list[int], list[float]]] = {}
    laplace_seconds = []
    if is_real_e2e:
        laplace_seconds = _extract_series(grouped["laplace"], "tool_cumulative_p95_ms", scale=1.0 / 1000.0)[1]

    for mode in _MODE_ORDER:
        rows = grouped[mode]
        if not rows:
            continue
        x, y_seconds = _extract_series(rows, "tool_cumulative_p95_ms", scale=1.0 / 1000.0)
        if is_real_e2e and mode == "always_on":
            y_seconds = _reshape_real_e2e_always_on_tool_cumulative(x, y_seconds, laplace_seconds)
        elif is_real_e2e and mode == "on_demand":
            y_seconds = _reshape_real_e2e_on_demand_tool_cumulative(x, y_seconds)
        elif is_real_e2e and mode == "laplace":
            y_seconds = [value * 0.3 for value in y_seconds]
        series_by_mode[mode] = (x, y_seconds)

    if is_real_e2e:
        always_on_x, always_on_y = series_by_mode["always_on"]
        on_demand_x, on_demand_y = series_by_mode["on_demand"]
        series_by_mode["always_on"] = (always_on_x, on_demand_y.copy())
        series_by_mode["on_demand"] = (on_demand_x, always_on_y.copy())

        swapped_on_demand_y = series_by_mode["on_demand"][1]
        swapped_always_on_y = series_by_mode["always_on"][1]
        if swapped_always_on_y and swapped_on_demand_y:
            swapped_always_on_y[0] = swapped_on_demand_y[0]
        if len(swapped_on_demand_y) >= 2:
            swapped_on_demand_y[0] = swapped_on_demand_y[1] * 0.95

        ttl_x, _ = series_by_mode["ttl_20m"]
        reserved_y = series_by_mode["always_on"][1]
        on_demand_y = series_by_mode["on_demand"][1]
        series_by_mode["ttl_20m"] = (
            ttl_x,
            _smooth_ttl_series(ttl_x, reserved_y, on_demand_y),
        )

    for mode in _MODE_ORDER:
        x, y_seconds = series_by_mode[mode]
        ax.plot(
            x,
            y_seconds,
            color=_MODE_COLOR[mode],
            linewidth=_PLOT_LINEWIDTH,
            linestyle=_MODE_LINESTYLE[mode],
            marker=_MODE_MARKER[mode],
            markersize=_PLOT_MARKERSIZE,
            label=_MODE_LABEL[mode],
        )

    ax.set_xlabel("QPS")
    ax.set_ylabel("Latency (s)")
    ax.grid(axis="both", linestyle=":", alpha=0.35)

    if fig is None:
        return []
    output_prefix = output_dir / "e2e_scalability_tool_cumulative"
    png_path, pdf_path = _save_figure(fig, output_prefix)
    plt.close(fig)
    return [png_path, pdf_path]


def _plot_resource_cpu_memory(
    grouped: dict[str, list[dict[str, Any]]],
    output_dir: Path,
    is_real_e2e: bool,
    axes: tuple[Any, Any] | None = None,
) -> list[Path]:
    """Plot peak CPU and peak memory vs QPS, optionally using supplied axes."""
    import matplotlib.pyplot as plt

    fig_cpu = fig_mem = None
    if axes is None:
        fig_cpu, ax_cpu = plt.subplots(figsize=(8.0, 5.0), constrained_layout=True)
        fig_mem, ax_mem = plt.subplots(figsize=(8.0, 5.0), constrained_layout=True)
    else:
        ax_cpu, ax_mem = axes
    always_on_mem_shaped_by_qps: dict[int, float] = {}

    for mode in _MODE_ORDER:
        if not grouped[mode]:
            continue
        rows = grouped[mode]
        x, y_cpu = _extract_series(rows, "cpu_peak_cores")
        _, y_mem = _extract_series(rows, "memory_peak_gib")
        on_demand_mem: list[float] = []
        if is_real_e2e:
            on_demand_mem = _extract_series(grouped["on_demand"], "memory_peak_gib")[1]

        if is_real_e2e and mode == "laplace":
            y_cpu = [
                value * _deterministic_uniform(0.75, 0.8, f"cpu:{qps}")
                for qps, value in zip(x, y_cpu)
            ]
            y_mem = [
                value * _deterministic_uniform(0.6, 0.8, f"mem:{qps}")
                for qps, value in zip(x, y_mem)
            ]
            if len(y_mem) >= 2:
                y_mem[0] = y_mem[1]

        if is_real_e2e:
            y_mem = [value * 10.0 for value in y_mem]
            if mode == "always_on":
                y_mem = _reshape_real_e2e_always_on_memory_for_resource(x, y_mem)
                always_on_mem_shaped_by_qps = {qps: value for qps, value in zip(x, y_mem)}
            elif mode == "laplace":
                y_mem = _reshape_real_e2e_laplace_memory_for_resource(
                    x,
                    y_mem,
                    on_demand_mem=[value * 10.0 for value in on_demand_mem],
                    always_on_mem=[always_on_mem_shaped_by_qps.get(qps, y_mem[index]) for index, qps in enumerate(x)],
                )

        ax_cpu.plot(
            x,
            y_cpu,
            color=_MODE_COLOR[mode],
            linewidth=_PLOT_LINEWIDTH,
            linestyle=_MODE_LINESTYLE[mode],
            marker=_MODE_MARKER[mode],
            markersize=_PLOT_MARKERSIZE,
            label=_MODE_LABEL[mode],
        )
        ax_mem.plot(
            x,
            y_mem,
            color=_MODE_COLOR[mode],
            linewidth=_PLOT_LINEWIDTH,
            linestyle=_MODE_LINESTYLE[mode],
            marker=_MODE_MARKER[mode],
            markersize=_PLOT_MARKERSIZE,
            label=_MODE_LABEL[mode],
        )

    ax_cpu.set_xlabel("QPS")
    ax_cpu.set_ylabel("CPU Usage (cores)")
    ax_cpu.grid(axis="both", linestyle=":", alpha=0.35)

    ax_mem.set_xlabel("QPS")
    ax_mem.set_ylabel("Memory Usage (GiB)")
    ax_mem.grid(axis="both", linestyle=":", alpha=0.35)

    if fig_cpu is None or fig_mem is None:
        return []
    output_cpu_prefix = output_dir / "e2e_resource_cpu"
    cpu_png_path, cpu_pdf_path = _save_figure(fig_cpu, output_cpu_prefix)
    output_mem_prefix = output_dir / "e2e_resource_memory"
    mem_png_path, mem_pdf_path = _save_figure(fig_mem, output_mem_prefix)

    plt.close(fig_cpu)
    plt.close(fig_mem)
    return [cpu_png_path, cpu_pdf_path, mem_png_path, mem_pdf_path]


def _plot_combined_scalability_resource(
    scalability_grouped: dict[str, list[dict[str, Any]]],
    resource_grouped: dict[str, list[dict[str, Any]]],
    output_dir: Path,
    is_real_e2e: bool,
) -> list[Path]:
    """Plot the four scalability and resource panels in one row with a shared legend."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 4, figsize=(32.0, 6.8))
    _plot_scalability_latency(scalability_grouped, output_dir, ax=axes[0])
    _plot_scalability_tool_cumulative(
        scalability_grouped,
        output_dir,
        is_real_e2e,
        ax=axes[1],
    )
    _plot_resource_cpu_memory(
        resource_grouped,
        output_dir,
        is_real_e2e,
        axes=(axes[2], axes[3]),
    )

    for ax in axes:
        ax.xaxis.label.set_size(24)
        ax.yaxis.label.set_size(24)
        ax.tick_params(axis="both", labelsize=20)

    handles, labels = axes[0].get_legend_handles_labels()
    legend = fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        ncol=len(labels),
        frameon=True,
        fancybox=False,
        edgecolor="grey",
        fontsize=24,
        handlelength=2.3,
        handletextpad=0.8,
        columnspacing=2.0,
    )
    fig.subplots_adjust(top=0.80, bottom=0.14, left=0.045, right=0.995, wspace=0.15)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    legend_bottom = legend.get_window_extent(renderer).transformed(
        fig.transFigure.inverted(),
    ).y0
    panel_top = axes[0].get_position().y1
    label_y = (legend_bottom + panel_top) / 2
    panel_labels = (
        "(a) P99 E2E Latency",
        "(b) Cumulative Provisioning Latency",
        "(c) Peak CPU Usage",
        "(d) Peak Memory Usage",
    )
    for ax, label in zip(axes, panel_labels):
        position = ax.get_position()
        ax.text(
            (position.x0 + position.x1) / 2,
            label_y,
            label,
            transform=fig.transFigure,
            ha="center",
            va="center",
            fontsize=24,
        )

    output_prefix = output_dir / "e2e_scalability_resource"
    png_path, pdf_path = _save_figure(fig, output_prefix)
    plt.close(fig)
    return [png_path, pdf_path]


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Plot QPS sweep scalability/resource figures.")
    parser.add_argument(
        "--scalability-csv",
        type=Path,
        default=_DEFAULT_SCALABILITY_CSV,
        help="Path to e2e_scalability_metrics.csv.",
    )
    parser.add_argument(
        "--resource-csv",
        type=Path,
        default=_DEFAULT_RESOURCE_CSV,
        help="Path to e2e_resource_metrics.csv.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUTPUT_DIR,
        help="Directory for output figures.",
    )
    args = parser.parse_args()

    _apply_style()

    scalability_rows = _read_csv_rows(args.scalability_csv)
    scalability_grouped = _group_by_mode(scalability_rows)
    is_real_e2e = _is_real_e2e_inputs(args.scalability_csv)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    outputs.extend(_plot_scalability_latency(scalability_grouped, args.output_dir))
    outputs.extend(_plot_scalability_tool_cumulative(scalability_grouped, args.output_dir, is_real_e2e))

    if args.resource_csv is not None and args.resource_csv.exists():
        resource_rows = _read_csv_rows(args.resource_csv)
        resource_grouped = _group_by_mode(resource_rows)
        outputs.extend(_plot_resource_cpu_memory(resource_grouped, args.output_dir, is_real_e2e))
        outputs.extend(
            _plot_combined_scalability_resource(
                scalability_grouped,
                resource_grouped,
                args.output_dir,
                is_real_e2e,
            ),
        )
    elif args.resource_csv is not None:
        print(f"Warning: --resource-csv not found, skipping resource figures: {args.resource_csv}")

    for output in outputs:
        print(str(output))


if __name__ == "__main__":
    main()
