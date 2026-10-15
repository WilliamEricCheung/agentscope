#!/usr/bin/env python3
"""Plot sorted On-Demand cold-start ready time by MCP server.

Default behavior follows the current analysis requirement:
- Metric: Total Avg (from trial total_ms)
- Aggregation: success-only trials (status == "pass")
- Plot: bar chart sorted by time ascending
"""

from __future__ import annotations

import argparse
import math
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent

plt.rcParams.update(
    {
        "font.size": 20,
        "axes.labelsize": 20,
        "legend.fontsize": 20,
        "xtick.labelsize": 20,
        "ytick.labelsize": 20,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    },
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments for bar-chart generation."""
    parser = argparse.ArgumentParser(description="Generate sorted MCP cold-start bar chart (success-only).")
    parser.add_argument(
        "--input-json",
        type=Path,
        default=SCRIPT_DIR / "profile_results.json",
        help="Path to profile_results.json",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=SCRIPT_DIR / "cold_start_ready_time_total_avg_success_only_sorted.csv",
        help="Path to output sorted CSV",
    )
    parser.add_argument(
        "--output-png",
        type=Path,
        default=SCRIPT_DIR / "on_demand_cold_start_32_mcp.png",
        help="Path to output PNG chart",
    )
    parser.add_argument(
        "--output-pdf",
        type=Path,
        default=SCRIPT_DIR / "on_demand_cold_start_32_mcp.pdf",
        help="Path to output PDF chart",
    )
    parser.add_argument(
        "--expected-count",
        type=int,
        default=32,
        help="Expected number of MCP servers after aggregation.",
    )
    parser.add_argument(
        "--bar-width",
        type=float,
        default=0.56,
        help="Bar width for the chart.",
    )
    parser.add_argument(
        "--fig-width",
        type=float,
        default=8.6,
        help="Figure width in inches.",
    )
    parser.add_argument(
        "--fig-height",
        type=float,
        default=5.4,
        help="Figure height in inches.",
    )
    parser.add_argument(
        "--max-xticks",
        type=int,
        default=10,
        help="Maximum number of x-axis tick labels to display.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Figure DPI.",
    )
    return parser.parse_args()


def build_dataframe(results: dict) -> pd.DataFrame:
    """Build sorted data frame with sandbox mapping and time in seconds."""
    rows: list[dict] = []
    for server in results.get("servers", []):
        server_name = server.get("server_name")
        if not server_name:
            continue

        trials = server.get("trials") or []
        success_total_ms = [
            t.get("total_ms")
            for t in trials
            if t.get("status") == "pass" and isinstance(t.get("total_ms"), (int, float))
        ]
        if not success_total_ms:
            continue
        rows.append(
            {
                "server_name": server_name,
                "success_count": len(success_total_ms),
                "time_s": sum(success_total_ms) / len(success_total_ms) / 1000.0,
            },
        )

    df = pd.DataFrame(rows)
    df = df.sort_values("time_s", ascending=True).reset_index(drop=True)
    df.insert(0, "sandbox_id", df.index)
    return df


def main() -> None:
    """Generate sorted CSV and bar chart from profiling results."""
    args = parse_args()

    with args.input_json.open("r", encoding="utf-8") as f:
        results = json.load(f)

    df = build_dataframe(results=results)
    if len(df) != args.expected_count:
        raise ValueError(f"Expected {args.expected_count} servers, got {len(df)}")

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_png.parent.mkdir(parents=True, exist_ok=True)
    args.output_pdf.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(args.output_csv, index=False)

    plt.figure(figsize=(args.fig_width, args.fig_height), dpi=args.dpi)
    cmap = plt.get_cmap("Reds")
    n = len(df)
    colors = [cmap(0.30 + 0.65 * i / max(1, n - 1)) for i in range(n)]
    x = df["sandbox_id"].to_numpy()
    y = df["time_s"].to_numpy()
    plt.bar(x, y, width=args.bar_width, color=colors, edgecolor="none")

    plt.xlabel("Sandbox ID", fontsize=24, labelpad=8)
    plt.ylabel("Time (s)", fontsize=24)
    plt.grid(axis="y", linestyle="--", alpha=0.30)
    max_x = int(df["sandbox_id"].max()) if not df.empty else 0
    plt.xlim(-0.6, max_x + 0.6)
    if args.max_xticks <= 1:
        tick_positions = [0, max_x] if max_x > 0 else [0]
    else:
        step = max(1, math.ceil((max_x + 1) / args.max_xticks))
        tick_positions = list(range(0, max_x + 1, step))
        if tick_positions[-1] != max_x:
            tick_positions.append(max_x)
    plt.xticks(tick_positions)
    plt.tight_layout()
    plt.savefig(args.output_png)
    plt.savefig(args.output_pdf)
    plt.close()

    print(f"saved csv: {args.output_csv}")
    print(f"saved png: {args.output_png}")
    print(f"saved pdf: {args.output_pdf}")


if __name__ == "__main__":
    main()
