#!/usr/bin/env python3
"""Render a reference figure for Section 3.2 (Stochastic Sandbox Prefetching).

The output contains two panels:
- Left: Markov Transition Graph over sandbox states with example probabilities.
- Right: A concise multi-turn prefetch decision process.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import patches


OUT_DIR = Path(__file__).resolve().parent
PNG_PATH = OUT_DIR / "s32_markov_transition_prefetch_example.png"
PDF_PATH = OUT_DIR / "s32_markov_transition_prefetch_example.pdf"


def set_style() -> None:
    """Set publication-friendly plotting style."""
    plt.rcParams.update(
        {
            "font.size": 12,
            "axes.titlesize": 13,
            "axes.labelsize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        },
    )


def draw_left_markov_graph(ax: plt.Axes) -> None:
    """Draw Markov transition graph panel."""
    ax.set_title("Markov State Transition Graph", pad=10)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # Example SDG states in Section 3.2 style: sandbox-level states.
    pos = {
        "Search": (2.2, 7.5),
        "Reader": (5.0, 8.4),
        "Python": (7.8, 7.0),
        "Report": (8.0, 3.6),
        "Web": (3.0, 2.8),
        "Maps": (1.4, 5.0),
    }

    node_color = "#ffe5e5"
    node_edge = "#a63434"

    for name, (x, y) in pos.items():
        circle = patches.Circle((x, y), radius=0.78, facecolor=node_color, edgecolor=node_edge, linewidth=1.6)
        ax.add_patch(circle)
        ax.text(x, y, name, ha="center", va="center", fontsize=10, color="#7a1111")

    # Edge format: (u, v, probability, count)
    edges = [
        ("Search", "Reader", 0.62, 124),
        ("Search", "Web", 0.21, 42),
        ("Search", "Maps", 0.17, 34),
        ("Reader", "Python", 0.58, 77),
        ("Reader", "Report", 0.32, 43),
        ("Reader", "Web", 0.10, 13),
        ("Python", "Report", 0.71, 61),
        ("Python", "Search", 0.29, 25),
        ("Web", "Search", 0.64, 39),
        ("Maps", "Search", 0.73, 27),
    ]

    for u, v, p, c in edges:
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        arrow = patches.FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="->",
            mutation_scale=12,
            linewidth=1.1 + 2.2 * p,
            color="#b33a3a",
            alpha=0.68,
            connectionstyle="arc3,rad=0.11",
            shrinkA=15,
            shrinkB=15,
        )
        ax.add_patch(arrow)

        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        ax.text(
            mx,
            my,
            f"p={p:.2f}\ncount={c}",
            fontsize=8,
            color="#6f1010",
            ha="center",
            va="center",
            bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "#e6b0b0", "alpha": 0.9},
        )

    formula = (
        r"$P_{i,j}=P(S_{N+1}=v_j\mid S_N=v_i)$" "\n"
        r"$\;\;\;\;=\dfrac{\mathrm{Count}(v_i\rightarrow v_j)+\alpha}{\sum_k (\mathrm{Count}(v_i\rightarrow v_k)+\alpha)}$"
    )
    ax.text(
        4.95,
        2.05,
        formula,
        fontsize=10,
        color="#5f0f0f",
        bbox={"boxstyle": "round,pad=0.25", "fc": "#fff7f7", "ec": "#d48787"},
    )


def draw_right_prefetch_panel(ax: plt.Axes) -> None:
    """Draw concise session timeline and prefetch decision panel."""
    ax.set_title("Prefetch Decision (Session Example)", pad=10)
    ax.set_xlim(0, 9.0)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # Timeline backbone.
    ax.plot([0.6, 0.6], [1.1, 9.0], color="#6b7280", linewidth=1.8)

    turns = [
        (8.3, "Turn N", "Current: Search", "Top successors: Reader(0.62), Web(0.21)", "Prefetch: Reader"),
        (6.5, "Turn N+1", "Observed: Reader", "Update SDG edge count Search->Reader", "Prefetch: Python"),
        (4.7, "Turn N+2", "Observed: Python", "Top successors: Report(0.71), Search(0.29)", "Prefetch: Report"),
        (2.9, "Turn N+3", "Observed: Report", "No heavy successor above threshold", "No prefetch"),
    ]

    for y, tname, line1, line2, line3 in turns:
        ax.scatter([0.6], [y], s=36, color="#b91c1c", zorder=3)
        ax.text(1.58, y + 0.22, tname, fontsize=10.2, color="#7f1d1d", weight="bold", ha="right")

        card = patches.FancyBboxPatch(
            (1.75, y - 0.55),
            6.95,
            1.35,
            boxstyle="round,pad=0.18,rounding_size=0.08",
            linewidth=1.0,
            edgecolor="#fca5a5",
            facecolor="#fff5f5",
        )
        ax.add_patch(card)
        ax.text(1.98, y + 0.48, line1, fontsize=9.2, color="#111827")
        ax.text(1.98, y + 0.12, line2, fontsize=8.8, color="#374151")
        ax.text(1.98, y - 0.24, line3, fontsize=9.2, color="#991b1b")

    policy = (
        "Decision policy:\n"
        "1) Rank successors by transition probability P(i,j)\n"
        "2) Score by expected gain G(i,j)=P(i,j)*L(j)\n"
        "3) Keep only P(i,j) >= tau; select top-B"
    )
    ax.text(
        1.75,
        1.2,
        policy,
        fontsize=9,
        color="#4b5563",
        bbox={"boxstyle": "round,pad=0.24", "fc": "#f9fafb", "ec": "#d1d5db"},
    )


def main() -> None:
    """Render and save the reference figure."""
    set_style()
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8), dpi=240)

    draw_left_markov_graph(axes[0])
    draw_right_prefetch_panel(axes[1])

    fig.subplots_adjust(left=0.03, right=0.99, bottom=0.06, top=0.93, wspace=0.02)

    fig.savefig(PNG_PATH)
    fig.savefig(PDF_PATH)
    plt.close(fig)

    print(f"saved png: {PNG_PATH}")
    print(f"saved pdf: {PDF_PATH}")


if __name__ == "__main__":
    main()
