# -*- coding: utf-8 -*-
"""Build comparison reports from prewarm experiment JSONL outputs."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


def _load_completed_records(
    path: Path,
    expected_mode: str | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if str(payload.get("trial_status", "")).strip() != "completed":
                continue
            if expected_mode is not None and str(payload.get("experiment_mode")) != expected_mode:
                continue
            records.append(payload)
    return records


def _format_number(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.3f}"


def _build_rows(named_records: list[tuple[str, list[dict[str, Any]]]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for label, records in named_records:
        waits = [
            float(record.get("summary", {}).get("wait_for_mcp_ready_after_activation_ms"))
            for record in records
            if record.get("summary", {}).get("wait_for_mcp_ready_after_activation_ms") is not None
        ]
        matched_runs = sum(
            1
            for record in records
            if bool(record.get("summary", {}).get("target_router_matched"))
        )
        effective_runs = sum(
            1
            for record in records
            if bool(record.get("summary", {}).get("target_effective_prewarm"))
        )
        startup_modes: dict[str, int] = defaultdict(int)
        for record in records:
            startup_modes[str(record.get("summary", {}).get("startup_mode") or "unknown")] += 1

        rows.append(
            [
                label,
                str(len(records)),
                f"{(matched_runs / len(records)) * 100:.1f}%" if records else "-",
                (
                    f"{(effective_runs / matched_runs) * 100:.1f}%"
                    if matched_runs
                    else "-"
                ),
                _format_number(sum(waits) / len(waits) if waits else None),
                _format_number(min(waits) if waits else None),
                _format_number(max(waits) if waits else None),
                ", ".join(
                    f"{name}:{startup_modes[name]}"
                    for name in sorted(startup_modes)
                ),
            ],
        )
    return rows


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _write_report(path: Path, title: str, subtitle: str, rows: list[list[str]]) -> None:
    headers = [
        "Mode",
        "Runs",
        "Target Match Rate",
        "Effectiveness Rate",
        "Avg Wait (ms)",
        "Min Wait (ms)",
        "Max Wait (ms)",
        "Activation Startup Modes",
    ]
    body = [
        f"# {title}",
        "",
        subtitle,
        "",
        _markdown_table(headers, rows),
        "",
    ]
    path.write_text("\n".join(body), encoding="utf-8")


def _with_timestamp(path: Path) -> Path:
    # Remove embedded date fragments like _0611 or _20260611 and append current timestamp.
    stem = re.sub(r"_(?:\d{4}|\d{8})", "", path.stem)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return path.with_name(f"{stem}_{timestamp}{path.suffix}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build hybrid comparison reports.")
    parser.add_argument("--keyword-jsonl", required=True)
    parser.add_argument("--keyword-mode", default="keyword")
    parser.add_argument("--semantic-jsonl", required=True)
    parser.add_argument("--semantic-mode", default="semantic")
    parser.add_argument("--hybrid-union-jsonl", required=True)
    parser.add_argument("--hybrid-union-mode", default="hybrid")
    parser.add_argument("--hybrid-intersection-jsonl", required=True)
    parser.add_argument("--hybrid-intersection-mode", default="hybrid")
    parser.add_argument("--hybrid-weighted-jsonl", required=True)
    parser.add_argument("--hybrid-weighted-mode", default="hybrid")
    parser.add_argument("--fusion-report", required=True)
    parser.add_argument("--all-report", required=True)
    args = parser.parse_args()

    keyword_records = _load_completed_records(
        Path(args.keyword_jsonl),
        expected_mode=args.keyword_mode,
    )
    semantic_records = _load_completed_records(
        Path(args.semantic_jsonl),
        expected_mode=args.semantic_mode,
    )
    hybrid_union_records = _load_completed_records(
        Path(args.hybrid_union_jsonl),
        expected_mode=args.hybrid_union_mode,
    )
    hybrid_intersection_records = _load_completed_records(
        Path(args.hybrid_intersection_jsonl),
        expected_mode=args.hybrid_intersection_mode,
    )
    hybrid_weighted_records = _load_completed_records(
        Path(args.hybrid_weighted_jsonl),
        expected_mode=args.hybrid_weighted_mode,
    )

    fusion_rows = _build_rows(
        [
            ("Hybrid (union)", hybrid_union_records),
            ("Hybrid (intersection)", hybrid_intersection_records),
            ("Hybrid (weighted)", hybrid_weighted_records),
        ],
    )
    _write_report(
        path=_with_timestamp(Path(args.fusion_report)),
        title="Hybrid Fusion Mode Comparison",
        subtitle="Using the same 0605 sampled-task plan for all runs.",
        rows=fusion_rows,
    )

    all_rows = _build_rows(
        [
            ("Keyword Only", keyword_records),
            ("Semantic Only", semantic_records),
            ("Hybrid (union)", hybrid_union_records),
            ("Hybrid (intersection)", hybrid_intersection_records),
            ("Hybrid (weighted)", hybrid_weighted_records),
        ],
    )
    _write_report(
        path=_with_timestamp(Path(args.all_report)),
        title="All Mode Comparison",
        subtitle="Keyword/Semantic versus three Hybrid fusion modes on the same sampled-task set.",
        rows=all_rows,
    )


if __name__ == "__main__":
    main()
