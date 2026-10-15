# -*- coding: utf-8 -*-
"""Plot final QPS sweep figures directly from CSV data."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

_THIS_DIR = Path(__file__).resolve().parent
_DEFAULT_SCALABILITY_CSV = _THIS_DIR / "real_e2e_scalability_metrics_final.csv"
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


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    """Read rows from a CSV file."""
    with path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError(f"No rows found in {path}")
    return rows


def _group_by_mode(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group rows by mode and sort them by QPS."""
    grouped: dict[str, list[dict[str, Any]]] = {mode: [] for mode in _MODE_ORDER}
    for row in rows:
        mode = str(row["mode"])
        if mode in grouped:
            grouped[mode].append(row)

    for mode in _MODE_ORDER:
        grouped[mode].sort(key=lambda row: int(row["qps"]))
        if not grouped[mode] and mode not in {"ttl_20m", "lru_5"}:
            raise ValueError(f"No rows for mode={mode}")
    return grouped


def _extract_series(
    rows: list[dict[str, Any]],
    key: str,
) -> tuple[list[int], list[float]]:
    """Extract QPS and values from a CSV column."""
    x_values = [int(row["qps"]) for row in rows]
    y_values = [float(row[key]) for row in rows]
    return x_values, y_values


def _apply_style() -> None:
    """Apply the plotting style."""
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
    """Save a figure in PNG and PDF formats."""
    png_path = output_prefix.with_suffix(".png")
    pdf_path = output_prefix.with_suffix(".pdf")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, dpi=300, bbox_inches="tight")
    return png_path, pdf_path


def _plot_series(
    ax: Any,
    grouped: dict[str, list[dict[str, Any]]],
    column: str,
    scale: float = 1.0,
) -> None:
    """Plot one CSV column for every available mode."""
    for mode in _MODE_ORDER:
        rows = grouped[mode]
        if not rows:
            continue
        x_values, y_values = _extract_series(rows, column)
        ax.plot(
            x_values,
            [value * scale for value in y_values],
            color=_MODE_COLOR[mode],
            linewidth=_PLOT_LINEWIDTH,
            linestyle=_MODE_LINESTYLE[mode],
            marker=_MODE_MARKER[mode],
            markersize=_PLOT_MARKERSIZE,
            label=_MODE_LABEL[mode],
        )


def _plot_scalability_latency(
    grouped: dict[str, list[dict[str, Any]]],
    output_dir: Path,
    ax: Any | None = None,
) -> list[Path]:
    """Plot CSV E2E p99 latency against QPS."""
    import matplotlib.pyplot as plt

    fig = None
    if ax is None:
        fig, ax = plt.subplots(figsize=(8.0, 5.0), constrained_layout=True)

    _plot_series(ax, grouped, "e2e_p99_ms", scale=1.0 / 1000.0)
    ax.set_xlabel("QPS")
    ax.set_ylabel("Latency (s)")
    ax.grid(axis="both", linestyle=":", alpha=0.35)

    if fig is None:
        return []
    paths = _save_figure(fig, output_dir / "e2e_scalability_latency_final")
    plt.close(fig)
    return list(paths)


def _plot_scalability_tool_cumulative(
    grouped: dict[str, list[dict[str, Any]]],
    output_dir: Path,
    ax: Any | None = None,
) -> list[Path]:
    """Plot the final CSV cumulative provisioning p95 values against QPS."""
    import matplotlib.pyplot as plt

    fig = None
    if ax is None:
        fig, ax = plt.subplots(figsize=(8.0, 5.0), constrained_layout=True)

    _plot_series(ax, grouped, "tool_cumulative_p95_ms", scale=1.0 / 1000.0)
    ax.set_xlabel("QPS")
    ax.set_ylabel("Latency (s)")
    ax.grid(axis="both", linestyle=":", alpha=0.35)

    if fig is None:
        return []
    paths = _save_figure(fig, output_dir / "e2e_scalability_tool_cumulative_final")
    plt.close(fig)
    return list(paths)


def _plot_resource_cpu_memory(
    grouped: dict[str, list[dict[str, Any]]],
    output_dir: Path,
    axes: tuple[Any, Any] | None = None,
) -> list[Path]:
    """Plot preprocessed CPU and memory columns from the final CSV."""
    import matplotlib.pyplot as plt

    fig_cpu = fig_mem = None
    if axes is None:
        fig_cpu, ax_cpu = plt.subplots(figsize=(8.0, 5.0), constrained_layout=True)
        fig_mem, ax_mem = plt.subplots(figsize=(8.0, 5.0), constrained_layout=True)
    else:
        ax_cpu, ax_mem = axes

    _plot_series(ax_cpu, grouped, "final_cpu_peak_cores")
    _plot_series(ax_mem, grouped, "final_memory_peak_gib")
    ax_cpu.set_xlabel("QPS")
    ax_cpu.set_ylabel("CPU Usage (cores)")
    ax_cpu.grid(axis="both", linestyle=":", alpha=0.35)
    ax_mem.set_xlabel("QPS")
    ax_mem.set_ylabel("Memory Usage (GiB)")
    ax_mem.grid(axis="both", linestyle=":", alpha=0.35)

    if fig_cpu is None or fig_mem is None:
        return []
    cpu_paths = _save_figure(fig_cpu, output_dir / "e2e_resource_cpu_final")
    mem_paths = _save_figure(fig_mem, output_dir / "e2e_resource_memory_final")
    plt.close(fig_cpu)
    plt.close(fig_mem)
    return [*cpu_paths, *mem_paths]


def _plot_combined_scalability_resource(
    grouped: dict[str, list[dict[str, Any]]],
    output_dir: Path,
) -> list[Path]:
    """Plot all four panels from preprocessed final CSV columns."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 4, figsize=(32.0, 6.8))
    _plot_scalability_latency(grouped, output_dir, ax=axes[0])
    _plot_scalability_tool_cumulative(grouped, output_dir, ax=axes[1])
    _plot_resource_cpu_memory(grouped, output_dir, axes=(axes[2], axes[3]))

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
    legend_bottom = legend.get_window_extent(fig.canvas.get_renderer()).transformed(
        fig.transFigure.inverted(),
    ).y0
    label_y = (legend_bottom + axes[0].get_position().y1) / 2
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

    paths = _save_figure(fig, output_dir / "e2e_scalability_resource_final")
    plt.close(fig)
    return list(paths)


def main() -> None:
    """Run the final CSV plotting command."""
    parser = argparse.ArgumentParser(description="Plot final QPS sweep figures.")
    parser.add_argument(
        "--scalability-csv",
        type=Path,
        default=_DEFAULT_SCALABILITY_CSV,
        help="Path to real_e2e_scalability_metrics_final.csv.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUTPUT_DIR,
        help="Directory for output figures.",
    )
    args = parser.parse_args()

    _apply_style()
    scalability_grouped = _group_by_mode(_read_csv_rows(args.scalability_csv))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    outputs = _plot_scalability_latency(scalability_grouped, args.output_dir)
    outputs.extend(_plot_scalability_tool_cumulative(scalability_grouped, args.output_dir))
    outputs.extend(_plot_resource_cpu_memory(scalability_grouped, args.output_dir))
    outputs.extend(
        _plot_combined_scalability_resource(
            scalability_grouped,
            args.output_dir,
        ),
    )

    for output in outputs:
        print(str(output))


if __name__ == "__main__":
    main()
