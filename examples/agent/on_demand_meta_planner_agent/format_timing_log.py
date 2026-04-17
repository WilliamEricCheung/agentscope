# -*- coding: utf-8 -*-
"""Format on-demand MCP timing logs into human-readable Markdown tables."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

_DEFAULT_LOG_PATH = Path(__file__).with_name("on_demand_timing.log.jsonl")
_DEFAULT_OUTPUT_PATH = Path(__file__).with_name("on_demand_timing_report.md")


def _format_number(value: Any) -> str:
    """Format one numeric value for Markdown display.

    Args:
        value (`Any`):
            The raw value from the timing log summary.

    Returns:
        `str`:
            A short human-readable string.
    """
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        return f"{float(value):.3f}"
    return str(value)


def _format_bool(value: Any) -> str:
    """Format a boolean value for display.

    Args:
        value (`Any`):
            The raw boolean-like value.

    Returns:
        `str`:
            ``yes`` / ``no`` / ``-``.
    """
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "-"


def _truncate_text(text: Any, limit: int = 48) -> str:
    """Truncate long text so table cells stay readable.

    Args:
        text (`Any`):
            Input text.
        limit (`int`, defaults to `48`):
            Maximum output length.

    Returns:
        `str`:
            The truncated text.
    """
    text = str(text or "")
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _normalize_startup_mode(value: Any) -> str:
    """Normalize raw startup mode values for human-readable comparison.

    Args:
        value (`Any`):
            Raw startup mode from the timing summary.

    Returns:
        `str`:
            Normalized mode name.
    """
    text = str(value or "").strip().lower()
    if text in {"", "none", "null", "-"}:
        return "unknown"
    return text


def _normalize_router_method(value: Any, prewarm: bool) -> str:
    """Normalize router method values for report display.

    Args:
        value (`Any`):
            Raw router method from the timing summary.
        prewarm (`bool`):
            Whether prewarm mode was enabled for the run.

    Returns:
        `str`:
            Normalized router method name.
    """
    if not prewarm:
        return "disabled"
    text = str(value or "").strip().lower()
    if text in {"", "none", "null", "-"}:
        return "unknown"
    return text


def _load_records(log_path: Path) -> list[dict[str, Any]]:
    """Load JSONL records from disk.

    Args:
        log_path (`Path`):
            The input JSONL timing log path.

    Returns:
        `list[dict[str, Any]]`:
            Parsed timing log records.
    """
    if not log_path.exists():
        return []

    records: list[dict[str, Any]] = []
    with log_path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))

    return records


def _build_markdown_table(
    headers: list[str],
    rows: list[list[str]],
) -> str:
    """Build a Markdown table string.

    Args:
        headers (`list[str]`):
            Column headers.
        rows (`list[list[str]]`):
            Table rows.

    Returns:
        `str`:
            The Markdown table.
    """
    if not rows:
        rows = [["-" for _ in headers]]

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _build_detail_rows(records: list[dict[str, Any]]) -> list[list[str]]:
    """Build detailed per-run rows.

    Args:
        records (`list[dict[str, Any]]`):
            Timing log records.

    Returns:
        `list[list[str]]`:
            Table rows for detailed comparison.
    """
    rows: list[list[str]] = []
    for record in records:
        summary = record.get("summary", {}) or {}
        rows.append(
            [
                str(record.get("run_id", "-")),
                str(record.get("started_at", "-")),
                _format_bool(record.get("prewarm")),
                _normalize_router_method(
                    summary.get("prewarm_router_method"),
                    bool(record.get("prewarm", False)),
                ),
                _format_bool(summary.get("prewarm_router_matched")),
                _format_bool(summary.get("prewarm_effective")),
                _normalize_startup_mode(summary.get("startup_mode")),
                _format_number(summary.get("wait_for_mcp_ready_after_activation_ms")),
                _truncate_text(record.get("task_description", "-")),
            ],
        )
    return rows


def _build_aggregate_rows(records: list[dict[str, Any]]) -> list[list[str]]:
    """Build aggregated comparison rows grouped by prewarm mode.

    Args:
        records (`list[dict[str, Any]]`):
            Timing log records.

    Returns:
        `list[list[str]]`:
            Aggregated summary rows.
    """
    grouped: dict[bool, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[bool(record.get("prewarm", False))].append(record)

    rows: list[list[str]] = []
    for prewarm in (False, True):
        group = grouped.get(prewarm, [])
        if not group:
            continue

        waits = [
            float(record.get("summary", {}).get("wait_for_mcp_ready_after_activation_ms"))
            for record in group
            if record.get("summary", {}).get("wait_for_mcp_ready_after_activation_ms")
            is not None
        ]
        avg_wait = sum(waits) / len(waits) if waits else None
        min_wait = min(waits) if waits else None
        max_wait = max(waits) if waits else None

        rows.append(
            [
                f"prewarm={str(prewarm).lower()}",
                str(len(group)),
                _format_number(avg_wait),
                _format_number(min_wait),
                _format_number(max_wait),
            ],
        )

    return rows


def _build_startup_mode_rows(records: list[dict[str, Any]]) -> list[list[str]]:
    """Build subgroup rows grouped by prewarm mode and startup mode.

    Args:
        records (`list[dict[str, Any]]`):
            Timing log records.

    Returns:
        `list[list[str]]`:
            Subgroup comparison rows.
    """
    grouped: dict[tuple[bool, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        summary = record.get("summary", {}) or {}
        key = (
            bool(record.get("prewarm", False)),
            _normalize_startup_mode(summary.get("startup_mode")),
        )
        grouped[key].append(record)

    mode_order = {"cold": 0, "resume": 1, "running": 2, "unknown": 3}
    rows: list[list[str]] = []
    for key in sorted(
        grouped,
        key=lambda item: (item[0], mode_order.get(item[1], 99), item[1]),
    ):
        prewarm, startup_mode = key
        group = grouped[key]
        waits = [
            float(record.get("summary", {}).get("wait_for_mcp_ready_after_activation_ms"))
            for record in group
            if record.get("summary", {}).get("wait_for_mcp_ready_after_activation_ms")
            is not None
        ]
        avg_wait = sum(waits) / len(waits) if waits else None
        min_wait = min(waits) if waits else None
        max_wait = max(waits) if waits else None

        rows.append(
            [
                f"prewarm={str(prewarm).lower()}",
                startup_mode,
                str(len(group)),
                _format_number(avg_wait),
                _format_number(min_wait),
                _format_number(max_wait),
            ],
        )

    return rows


def _build_router_effectiveness_rows(
    records: list[dict[str, Any]],
) -> list[list[str]]:
    """Build aggregated rows for prewarm router effectiveness.

    Args:
        records (`list[dict[str, Any]]`):
            Timing log records.

    Returns:
        `list[list[str]]`:
            Router-effectiveness summary rows.
    """
    grouped: dict[tuple[bool, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        summary = record.get("summary", {}) or {}
        key = (
            bool(record.get("prewarm", False)),
            _normalize_router_method(
                summary.get("prewarm_router_method"),
                bool(record.get("prewarm", False)),
            ),
        )
        grouped[key].append(record)

    rows: list[list[str]] = []
    for key in sorted(grouped, key=lambda item: (item[0], item[1])):
        prewarm, router_method = key
        group = grouped[key]
        matched_runs = sum(
            1 for record in group if record.get("summary", {}).get("prewarm_router_matched")
        )
        effective_runs = sum(
            1 for record in group if record.get("summary", {}).get("prewarm_effective")
        )
        rate = (
            f"{(effective_runs / matched_runs) * 100:.1f}%"
            if matched_runs
            else "-"
        )
        rows.append(
            [
                f"prewarm={str(prewarm).lower()}",
                router_method,
                str(len(group)),
                str(matched_runs),
                str(effective_runs),
                rate,
            ],
        )

    return rows


def generate_report(
    log_path: Path | str = _DEFAULT_LOG_PATH,
    output_path: Path | str = _DEFAULT_OUTPUT_PATH,
) -> str:
    """Generate a Markdown comparison report from the JSONL timing log.

    Args:
        log_path (`Path | str`, optional):
            The input JSONL path.
        output_path (`Path | str`, optional):
            The Markdown output path.

    Returns:
        `str`:
            The generated Markdown report text.
    """
    log_path = Path(log_path)
    output_path = Path(output_path)
    records = _load_records(log_path)

    if not records:
        report = (
            "# On-demand MCP Timing Report\n\n"
            f"> No timing log records found at `{log_path}`.\n"
        )
        output_path.write_text(report, encoding="utf-8")
        return report

    records = sorted(records, key=lambda item: str(item.get("started_at", "")))

    detail_headers = [
        "Run ID",
        "Started At",
        "Prewarm",
        "Router Method",
        "Router Matched",
        "Prewarm Effective",
        "Startup Mode",
        "Wait After Activation (ms)",
        "Task",
    ]
    aggregate_headers = [
        "Mode",
        "Runs",
        "Avg Wait After Activation (ms)",
        "Min Wait (ms)",
        "Max Wait (ms)",
    ]
    subgroup_headers = [
        "Mode",
        "Startup Mode",
        "Runs",
        "Avg Wait After Activation (ms)",
        "Min Wait (ms)",
        "Max Wait (ms)",
    ]
    router_headers = [
        "Mode",
        "Router Method",
        "Runs",
        "Router Matched Runs",
        "Effective Prewarm Runs",
        "Effectiveness Rate",
    ]

    report = "\n\n".join(
        [
            "# On-demand MCP Timing Report",
            f"> Source log: `{log_path}`",
            "> Primary KPI: `Wait After Activation (ms)`. The prewarm-start / prewarm-duration / ready-before-activation fields are useful only for low-level debugging and are often absent, so the main comparison now focuses on the actual post-activation container-ready wait time.",
            "> `Prewarm Effective` means the speculative prewarm itself changed the container from `cold` or `resume` into a running state before formal activation.",
            "## Aggregated Comparison by Prewarm Mode",
            _build_markdown_table(aggregate_headers, _build_aggregate_rows(records)),
            "## Prewarm Router Effectiveness",
            _build_markdown_table(router_headers, _build_router_effectiveness_rows(records)),
            "## Aggregated Comparison by Prewarm + Startup Mode",
            _build_markdown_table(
                subgroup_headers,
                _build_startup_mode_rows(records),
            ),
            "## Per-run Details",
            _build_markdown_table(detail_headers, _build_detail_rows(records)),
        ],
    ) + "\n"

    output_path.write_text(report, encoding="utf-8")
    return report


def main() -> None:
    """CLI entrypoint for formatting the timing log into Markdown."""
    parser = argparse.ArgumentParser(
        description="Convert on-demand MCP timing JSONL logs into a Markdown comparison table.",
    )
    parser.add_argument(
        "--log-path",
        default=str(_DEFAULT_LOG_PATH),
        help="Path to the input on_demand_timing.log.jsonl file.",
    )
    parser.add_argument(
        "--output-path",
        default=str(_DEFAULT_OUTPUT_PATH),
        help="Path to the output Markdown report file.",
    )
    args = parser.parse_args()

    report = generate_report(args.log_path, args.output_path)
    print(report)
    print(f"\nSaved Markdown table to: {args.output_path}")


if __name__ == "__main__":
    main()
