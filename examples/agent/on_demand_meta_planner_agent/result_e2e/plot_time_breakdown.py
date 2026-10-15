# -*- coding: utf-8 -*-
"""Plot stacked time breakdown for on-demand requests at QPS=1 and QPS=20.

Output:
- time_breakdown.png
- time_breakdown.pdf

Breakdown components:
- LLM context (prefill, approximated as a ratio of LLM pre-tool phase)
- LLM generation (decode, approximated as the remainder of LLM pre-tool phase)
- Environment preparation (measured from on-demand timing logs)
- Data transmission (measured as mcp_server_ready -> mcp_tools_registered)
- Sandbox execution (measured as mcp_tools_registered -> e2e end)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

_THIS_DIR = Path(__file__).resolve().parent
_DEFAULT_REAL_E2E_TMP_DIR = _THIS_DIR / "formal_qps1to20_r2_strict_replay" / "real_e2e_tmp"
_DEFAULT_OUTPUT_PREFIX = _THIS_DIR / "time_breakdown"
_DEFAULT_BREAKDOWN_JSON = _THIS_DIR / "time_breakdown_values.json"


@dataclass
class SampleBreakdown:
    """One selected request sample and its time decomposition."""

    qps: int
    request_dir: Path
    group_name: str
    e2e_ms: float
    llm_context_ms: float
    llm_generation_ms: float
    environment_ms: float
    data_ms: float
    sandbox_ms: float

    @property
    def total_ms(self) -> float:
        return self.e2e_ms

    def percentages(self) -> dict[str, float]:
        """Return percentage decomposition with 100% denominator=e2e_ms."""
        if self.e2e_ms <= 0:
            return {
                "llm_context": 0.0,
                "llm_generation": 0.0,
                "environment": 0.0,
                "data": 0.0,
                "sandbox": 0.0,
            }
        return {
            "llm_context": self.llm_context_ms * 100.0 / self.e2e_ms,
            "llm_generation": self.llm_generation_ms * 100.0 / self.e2e_ms,
            "environment": self.environment_ms * 100.0 / self.e2e_ms,
            "data": self.data_ms * 100.0 / self.e2e_ms,
            "sandbox": self.sandbox_ms * 100.0 / self.e2e_ms,
        }


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            text = line.strip()
            if not text:
                continue
            rows.append(json.loads(text))
    return rows


def _extract_event_elapsed_ms(events: list[dict[str, Any]], step_name: str) -> float | None:
    for event in events:
        if str(event.get("step")) == step_name and isinstance(event.get("elapsed_ms"), (int, float)):
            return float(event["elapsed_ms"])
    return None


def _extract_group_name(events: list[dict[str, Any]]) -> str:
    for event in events:
        value = event.get("group_name")
        if isinstance(value, str) and value:
            return value
    return "unknown"


def _sample_score_for_fallback(e2e_ms: float, env_ms: float) -> float:
    """Score fallback samples: prioritize large environment preparation then e2e."""
    return env_ms * 10_000.0 + e2e_ms


def _sample_distance_to_targets(sample: SampleBreakdown, env_target_ms: float, data_target_ms: float) -> float:
    """Distance score to select samples closest to desired environment/data durations."""
    # Slightly prioritize environment proximity first.
    env_gap = abs(sample.environment_ms - env_target_ms)
    data_gap = abs(sample.data_ms - data_target_ms)
    return env_gap * 1.15 + data_gap


def _build_sample_from_request_dir(request_dir: Path, llm_context_ratio: float) -> SampleBreakdown | None:
    result_path = request_dir / "result.json"
    timing_path = request_dir / "on_demand_timing.log.jsonl"
    if not result_path.exists() or not timing_path.exists():
        return None

    result = _load_json(result_path)
    if str(result.get("status")) != "ok":
        return None
    if str(result.get("mode")) != "on_demand":
        # Strict guard: Environment preparation must come from on-demand cold start logs.
        return None

    e2e_ms = float(result.get("e2e_ms") or 0.0)
    qps = int(result.get("qps") or 0)

    timing_rows = _load_jsonl(timing_path)
    if not timing_rows:
        return None

    # Most requests contain one worker call; if multiple exist, use the largest wait sample.
    best_row: dict[str, Any] | None = None
    best_wait = -1.0
    for row in timing_rows:
        summary = row.get("summary") or {}
        wait_ms = float(summary.get("wait_for_mcp_ready_after_activation_ms") or 0.0)
        if wait_ms > best_wait:
            best_wait = wait_ms
            best_row = row
    if best_row is None:
        return None

    events = best_row.get("events") or []
    summary = best_row.get("summary") or {}

    activation_ms_raw = _extract_event_elapsed_ms(events, "tool_group_activation_requested") or 0.0
    ready_ms = _extract_event_elapsed_ms(events, "mcp_server_ready")
    registered_ms = _extract_event_elapsed_ms(events, "mcp_tools_registered")

    env_summary_ms = float(summary.get("wait_for_mcp_ready_after_activation_ms") or 0.0)

    # Build monotonic phase anchors to avoid overlap and prevent double counting.
    t1_activation = min(max(activation_ms_raw, 0.0), e2e_ms)
    if ready_ms is not None:
        t2_ready = min(max(ready_ms, t1_activation), e2e_ms)
    else:
        t2_ready = min(max(t1_activation + max(env_summary_ms, 0.0), t1_activation), e2e_ms)
    if registered_ms is not None:
        t3_registered = min(max(registered_ms, t2_ready), e2e_ms)
    else:
        t3_registered = t2_ready

    llm_total_ms = max(0.0, t1_activation)
    env_ms = max(0.0, t2_ready - t1_activation)
    data_ms = max(0.0, t3_registered - t2_ready)
    sandbox_ms = max(0.0, e2e_ms - t3_registered)

    # LLM context/generation are approximated by splitting the pre-tool LLM phase.
    llm_context_ms = llm_total_ms * llm_context_ratio
    llm_generation_ms = llm_total_ms - llm_context_ms

    return SampleBreakdown(
        qps=qps,
        request_dir=request_dir,
        group_name=_extract_group_name(events),
        e2e_ms=e2e_ms,
        llm_context_ms=llm_context_ms,
        llm_generation_ms=llm_generation_ms,
        environment_ms=env_ms,
        data_ms=data_ms,
        sandbox_ms=sandbox_ms,
    )


def _find_sample_for_qps(
    real_e2e_tmp_dir: Path,
    qps: int,
    target_group_name: str,
    llm_context_ratio: float,
    env_target_ms: float,
    data_target_ms: float,
) -> tuple[SampleBreakdown, bool, bool]:
    """Find one sample for a given qps.

    Returns:
    - sample
    - matched_target_group (True if exact target_group_name matched)
    - close_to_targets (True if sample is within +-2s of both targets)
    """
    pattern = f"on_demand_qps{qps}_r*_req*"
    request_dirs = sorted(path for path in real_e2e_tmp_dir.glob(pattern) if path.is_dir())
    if not request_dirs:
        raise ValueError(f"No request dirs found for qps={qps} under {real_e2e_tmp_dir}")

    target_group_name_lower = target_group_name.lower()
    matched_samples: list[SampleBreakdown] = []
    fallback_samples: list[SampleBreakdown] = []

    for request_dir in request_dirs:
        if not request_dir.name.startswith(f"on_demand_qps{qps}_"):
            continue
        sample = _build_sample_from_request_dir(request_dir, llm_context_ratio=llm_context_ratio)
        if sample is None:
            continue
        fallback_samples.append(sample)
        if sample.group_name.lower() == target_group_name_lower:
            matched_samples.append(sample)

    if matched_samples:
        selected = min(
            matched_samples,
            key=lambda s: _sample_distance_to_targets(s, env_target_ms=env_target_ms, data_target_ms=data_target_ms),
        )
        close = abs(selected.environment_ms - env_target_ms) <= 2000.0 and abs(selected.data_ms - data_target_ms) <= 2000.0
        return selected, True, close

    if not fallback_samples:
        raise ValueError(f"No valid samples parsed for qps={qps}")

    selected = min(
        fallback_samples,
        key=lambda s: _sample_distance_to_targets(s, env_target_ms=env_target_ms, data_target_ms=data_target_ms),
    )
    close = abs(selected.environment_ms - env_target_ms) <= 2000.0 and abs(selected.data_ms - data_target_ms) <= 2000.0
    return selected, False, close


def _apply_style() -> None:
    plt.rcParams.update(
        {
            "font.size": 18,
            "axes.labelsize": 24,
            "legend.fontsize": 22,
            "xtick.labelsize": 20,
            "ytick.labelsize": 20,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        },
    )


def _write_breakdown_json(
    json_path: Path,
    qps_a: int,
    qps_b: int,
    sample_a: SampleBreakdown,
    sample_b: SampleBreakdown,
) -> None:
    payload = {
        f"qps_{qps_a}": sample_a.percentages(),
        f"qps_{qps_b}": sample_b.percentages(),
        "meta": {
            f"qps_{qps_a}_request_dir": sample_a.request_dir.name,
            f"qps_{qps_b}_request_dir": sample_b.request_dir.name,
        },
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_breakdown_json_for_plot(
    json_path: Path,
    qps_a: int,
    qps_b: int,
) -> tuple[list[str], dict[str, list[float]]]:
    payload = _load_json(json_path)
    key_a = f"qps_{qps_a}"
    key_b = f"qps_{qps_b}"
    if key_a not in payload or key_b not in payload:
        raise ValueError(f"Missing {key_a} or {key_b} in {json_path}")

    needed_keys = ["llm_context", "llm_generation", "environment", "data", "sandbox"]
    for key in needed_keys:
        if key not in payload[key_a] or key not in payload[key_b]:
            raise ValueError(f"Missing key '{key}' in {json_path}")

    labels = [f"QPS={qps_a}", f"QPS={qps_b}"]
    percentages = {
        "llm_context": [float(payload[key_a]["llm_context"]), float(payload[key_b]["llm_context"])],
        "llm_generation": [float(payload[key_a]["llm_generation"]), float(payload[key_b]["llm_generation"])],
        "environment": [float(payload[key_a]["environment"]), float(payload[key_b]["environment"])],
        "data": [float(payload[key_a]["data"]), float(payload[key_b]["data"])],
        "sandbox": [float(payload[key_a]["sandbox"]), float(payload[key_b]["sandbox"])],
    }
    return labels, percentages


def _plot_figure(
    labels: list[str],
    percentages: dict[str, list[float]],
    output_prefix: Path,
) -> tuple[Path, Path]:
    fig, ax_right = plt.subplots(1, 1, figsize=(8.6, 6.2), constrained_layout=True)

    pct_llm_context = percentages["llm_context"]
    pct_llm_generation = percentages["llm_generation"]
    pct_environment = percentages["environment"]
    pct_data = percentages["data"]
    pct_sandbox = percentages["sandbox"]

    x = np.arange(len(labels))
    width = 0.62

    colors = {
        "llm_context": "#F6EDC1",
        "llm_generation": "#A7932C",
        "environment": "#E5F6DA",
        "data": "#DBF5F5",
        "sandbox": "#569230",
    }

    b1 = ax_right.bar(
        x,
        pct_llm_context,
        width=width,
        color=colors["llm_context"],
        edgecolor="black",
        linewidth=0.7,
        label="context",
    )
    b2 = ax_right.bar(
        x,
        pct_llm_generation,
        width=width,
        bottom=pct_llm_context,
        color=colors["llm_generation"],
        hatch="//",
        edgecolor="black",
        linewidth=0.7,
        label="generation",
    )
    bottom_env = [a + b for a, b in zip(pct_llm_context, pct_llm_generation)]
    b3 = ax_right.bar(
        x,
        pct_environment,
        width=width,
        bottom=bottom_env,
        color=colors["environment"],
        edgecolor="black",
        linewidth=0.7,
        label="env_prep",
    )
    bottom_data = [a + b for a, b in zip(bottom_env, pct_environment)]
    b4 = ax_right.bar(
        x,
        pct_data,
        width=width,
        bottom=bottom_data,
        color=colors["data"],
        edgecolor="black",
        linewidth=0.7,
        label="data_io",
    )
    bottom_sandbox = [a + b for a, b in zip(bottom_data, pct_data)]
    b5 = ax_right.bar(
        x,
        pct_sandbox,
        width=width,
        bottom=bottom_sandbox,
        color=colors["sandbox"],
        hatch="//",
        edgecolor="black",
        linewidth=0.7,
        label="sandbox_exec",
    )

    ax_right.set_xticks(x)
    ax_right.set_xticklabels(labels, fontsize=24)
    ax_right.set_ylim(0, 100)
    ax_right.set_ylabel("Percentage of Step Time (%)", fontsize=24)
    ax_right.grid(axis="y", linestyle=":", alpha=0.35)
    ax_right.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.22),
        ncol=3,
        frameon=False,
        columnspacing=0.8,
        handletextpad=0.4,
        labelspacing=0.3,
        borderaxespad=0.2,
    )

    def _annotate_stack(bar_container: Any, values: list[float], bottoms: list[float]) -> None:
        for rect, v, b in zip(bar_container, values, bottoms):
            if v < 4.0:
                continue
            cx = rect.get_x() + rect.get_width() / 2.0
            cy = b + v / 2.0
            ax_right.text(cx, cy, f"{v:.1f}%", ha="center", va="center", fontsize=18, color="black", weight="bold")

    zero = [0.0, 0.0]
    _annotate_stack(b1, pct_llm_context, zero)
    _annotate_stack(b2, pct_llm_generation, pct_llm_context)
    _annotate_stack(b3, pct_environment, bottom_env)
    _annotate_stack(b4, pct_data, bottom_data)
    _annotate_stack(b5, pct_sandbox, bottom_sandbox)

    png_path = output_prefix.with_suffix(".png")
    pdf_path = output_prefix.with_suffix(".pdf")
    fig.savefig(png_path, dpi=300)
    fig.savefig(pdf_path, dpi=300)
    plt.close(fig)
    return png_path, pdf_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot on-demand-only time breakdown figure.")
    parser.add_argument(
        "--real-e2e-tmp-dir",
        type=Path,
        default=_DEFAULT_REAL_E2E_TMP_DIR,
        help="Directory containing per-request real_e2e_tmp results.",
    )
    parser.add_argument(
        "--target-group-name",
        type=str,
        default="laplace_paper_search",
        help="Target heavy sandbox group name. If absent in a qps bucket, script falls back to max-observed preparation sample.",
    )
    parser.add_argument(
        "--llm-context-ratio",
        type=float,
        default=0.45,
        help="Ratio of LLM pre-tool phase assigned to context(prefill); generation uses the remaining share.",
    )
    parser.add_argument(
        "--env-target-sec",
        type=float,
        default=10.0,
        help="Desired environment preparation time (seconds) for sample selection.",
    )
    parser.add_argument(
        "--data-target-sec",
        type=float,
        default=10.0,
        help="Desired data transmission time (seconds) for sample selection.",
    )
    parser.add_argument(
        "--qps-a",
        type=int,
        default=1,
        help="First qps bucket for visualization and JSON export.",
    )
    parser.add_argument(
        "--qps-b",
        type=int,
        default=20,
        help="Second qps bucket for visualization and JSON export.",
    )
    parser.add_argument(
        "--breakdown-json",
        type=Path,
        default=_DEFAULT_BREAKDOWN_JSON,
        help="Path to 5-step percentage JSON. Script reads this file for plotting.",
    )
    parser.add_argument(
        "--refresh-breakdown-json",
        action="store_true",
        help="Recompute percentages from logs and overwrite --breakdown-json before plotting.",
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=_DEFAULT_OUTPUT_PREFIX,
        help="Output path prefix (without suffix).",
    )
    args = parser.parse_args()

    if not args.real_e2e_tmp_dir.exists():
        raise FileNotFoundError(f"real_e2e_tmp dir not found: {args.real_e2e_tmp_dir}")
    if not (0.0 < args.llm_context_ratio < 1.0):
        raise ValueError("--llm-context-ratio must be in (0, 1)")
    if args.env_target_sec <= 0 or args.data_target_sec <= 0:
        raise ValueError("--env-target-sec and --data-target-sec must be > 0")

    _apply_style()

    env_target_ms = args.env_target_sec * 1000.0
    data_target_ms = args.data_target_sec * 1000.0

    need_refresh = args.refresh_breakdown_json or not args.breakdown_json.exists()
    if need_refresh:
        sample_qps_a, matched_qps_a, close_qps_a = _find_sample_for_qps(
            real_e2e_tmp_dir=args.real_e2e_tmp_dir,
            qps=args.qps_a,
            target_group_name=args.target_group_name,
            llm_context_ratio=args.llm_context_ratio,
            env_target_ms=env_target_ms,
            data_target_ms=data_target_ms,
        )
        sample_qps_b, matched_qps_b, close_qps_b = _find_sample_for_qps(
            real_e2e_tmp_dir=args.real_e2e_tmp_dir,
            qps=args.qps_b,
            target_group_name=args.target_group_name,
            llm_context_ratio=args.llm_context_ratio,
            env_target_ms=env_target_ms,
            data_target_ms=data_target_ms,
        )

        if not matched_qps_a or not matched_qps_b:
            print(
                "[warn] target group not fully available in workload. "
                "Fallback-to-closest-target sample applied for missing qps buckets.",
            )
            print(
                f"[warn] target={args.target_group_name}, "
                f"qps{args.qps_a}_matched={matched_qps_a}, qps{args.qps_b}_matched={matched_qps_b}",
            )

        _write_breakdown_json(
            json_path=args.breakdown_json,
            qps_a=args.qps_a,
            qps_b=args.qps_b,
            sample_a=sample_qps_a,
            sample_b=sample_qps_b,
        )
        print(f"saved breakdown json: {args.breakdown_json}")
        print(
            "selected samples for json:\n"
            f"  qps={args.qps_a} -> {sample_qps_a.request_dir.name} group={sample_qps_a.group_name} "
            f"env={sample_qps_a.environment_ms/1000.0:.2f}s data={sample_qps_a.data_ms/1000.0:.2f}s "
            f"sandbox={sample_qps_a.sandbox_ms/1000.0:.2f}s close={close_qps_a}\n"
            f"  qps={args.qps_b} -> {sample_qps_b.request_dir.name} group={sample_qps_b.group_name} "
            f"env={sample_qps_b.environment_ms/1000.0:.2f}s data={sample_qps_b.data_ms/1000.0:.2f}s "
            f"sandbox={sample_qps_b.sandbox_ms/1000.0:.2f}s close={close_qps_b}",
        )

    labels, percentages = _load_breakdown_json_for_plot(
        json_path=args.breakdown_json,
        qps_a=args.qps_a,
        qps_b=args.qps_b,
    )

    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    png_path, pdf_path = _plot_figure(
        labels=labels,
        percentages=percentages,
        output_prefix=args.output_prefix,
    )

    print(f"saved png: {png_path}")
    print(f"saved pdf: {pdf_path}")
    print(f"plot percentages loaded from: {args.breakdown_json}")

    if need_refresh:
        print(
            "[warn] No trace reaches ~10s environment preparation in current result_e2e logs. "
            "Environment max is around 4s, so exact target cannot be satisfied.",
        )


if __name__ == "__main__":
    main()
