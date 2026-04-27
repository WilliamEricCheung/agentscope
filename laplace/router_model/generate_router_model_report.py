# -*- coding: utf-8 -*-
"""Generate a Markdown comparison report for router model artifacts."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_SCRIPT_DIR = Path(__file__).resolve().parent


def _resolve_local_path(path: Path) -> Path:
    """Resolve relative paths against the router_model directory."""
    return path if path.is_absolute() else (_SCRIPT_DIR / path)


@dataclass
class RouterArtifactSummary:
    """One router artifact summary row.

    Args:
        model_name (`str`):
            Human-readable model name.
        artifact_dir (`Path`):
            Artifact directory path.
        router_family (`str`):
            Router family identifier.
        objective (`str`):
            Objective used in grid search.
        best (`dict[str, Any]`):
            Best grid-search row.
        metadata (`dict[str, Any]`):
            Training metadata.
        eval_metrics (`dict[str, Any]`):
            Default evaluation metrics written by the training script.
    """

    model_name: str
    artifact_dir: Path
    router_family: str
    objective: str
    best: dict[str, Any]
    metadata: dict[str, Any]
    eval_metrics: dict[str, Any]
    latency_metrics: dict[str, Any] | None


def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON file.

    Args:
        path (`Path`):
            JSON file path.

    Returns:
        `dict[str, Any]`:
            Parsed JSON payload.
    """
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _infer_router_family(model_name: str, metadata: dict[str, Any], artifact_dir: Path) -> str:
    """Infer router family when grid-search payload omits it.

    Args:
        model_name (`str`):
            Human-readable model name.
        metadata (`dict[str, Any]`):
            Training metadata.
        artifact_dir (`Path`):
            Artifact directory path.

        Returns:
            `str`:
                Router family string.
    """
    if metadata.get("router_family"):
        return str(metadata["router_family"])
    lowered = artifact_dir.name.lower()
    if "fasttext" in lowered or model_name.lower() == "fasttext":
        return "fasttext"
    if "retrieval" in lowered or model_name.lower() == "retrieval":
        return "retrieval_tfidf"
    if "encoder" in lowered or model_name.lower() == "encoder":
        return "encoder_sentence_transformer"
    return model_name.lower()


def _load_summary(model_name: str, artifact_dir: Path) -> RouterArtifactSummary:
    """Load one model artifact summary.

    Args:
        model_name (`str`):
            Human-readable model name.
        artifact_dir (`Path`):
            Artifact directory path.

        Returns:
            `RouterArtifactSummary`:
                Loaded report-ready summary.
    """
    grid_path = artifact_dir / "grid_search_results.json"
    metadata_path = artifact_dir / "metadata.json"
    eval_metrics_path = artifact_dir / "eval_metrics.json"
    latency_metrics_path = artifact_dir / "latency_benchmark.json"

    if not grid_path.exists():
        raise FileNotFoundError(f"Grid-search results not found: {grid_path}")
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata not found: {metadata_path}")
    if not eval_metrics_path.exists():
        raise FileNotFoundError(f"Eval metrics not found: {eval_metrics_path}")

    grid_results = _load_json(grid_path)
    metadata = _load_json(metadata_path)
    eval_metrics = _load_json(eval_metrics_path)
    latency_metrics = (
        _load_json(latency_metrics_path)
        if latency_metrics_path.exists()
        else None
    )

    best = grid_results.get("best") or grid_results.get("best_by_objective")
    if best is None:
        raise ValueError(f"Best grid-search row missing in: {grid_path}")

    objective = str(grid_results.get("objective") or "composite_score")
    router_family = str(
        grid_results.get("router_family")
        or _infer_router_family(model_name=model_name, metadata=metadata, artifact_dir=artifact_dir)
    )
    return RouterArtifactSummary(
        model_name=model_name,
        artifact_dir=artifact_dir,
        router_family=router_family,
        objective=objective,
        best=dict(best),
        metadata=metadata,
        eval_metrics=eval_metrics,
        latency_metrics=latency_metrics,
    )


def _format_float(value: Any) -> str:
    """Format one float-like value for Markdown.

    Args:
        value (`Any`):
            Raw numeric value.

    Returns:
        `str`:
            Formatted string.
    """
    if value is None:
        return "-"
    try:
        return f"{float(value):.6f}"
    except (TypeError, ValueError):
        return str(value)


def _format_int(value: Any) -> str:
    """Format one int-like value for Markdown.

    Args:
        value (`Any`):
            Raw numeric value.

    Returns:
        `str`:
            Formatted string.
    """
    if value is None:
        return "-"
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return str(value)


def _build_report(summaries: list[RouterArtifactSummary]) -> str:
    """Render one Markdown report.

    Args:
        summaries (`list[RouterArtifactSummary]`):
            Loaded model summaries.

        Returns:
            `str`:
                Markdown report text.
    """
    ranked = sorted(
        summaries,
        key=lambda item: float(item.best.get(item.objective, float("-inf"))),
        reverse=True,
    )
    winner = ranked[0]

    datasets = sorted(
        {
            dataset
            for summary in summaries
            for dataset in summary.metadata.get("datasets", [])
        },
    )
    text_modes = {summary.model_name: summary.metadata.get("text_mode", "-") for summary in summaries}

    lines: list[str] = []
    lines.append("# Router Model Report")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(f"- Compared models: {', '.join(summary.model_name for summary in summaries)}")
    lines.append(f"- Datasets: {', '.join(datasets) if datasets else '-'}")
    lines.append(f"- Current winner by grid-search objective: {winner.model_name}")
    lines.append("")
    lines.append("## Best Grid-Search Results")
    lines.append("")
    lines.append("| Rank | Model | Router Family | Text Mode | Objective | Best Score | Micro F1 | Hit Rate | Precision | Recall | Threshold | Top-K | Avg Latency (ms) | Distraction FP | Artifact |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")

    for index, summary in enumerate(ranked, start=1):
        best = summary.best
        objective_value = best.get(summary.objective)
        lines.append(
            "| "
            + " | ".join(
                [
                    str(index),
                    summary.model_name,
                    summary.router_family,
                    str(text_modes.get(summary.model_name, "-")),
                    summary.objective,
                    _format_float(objective_value),
                    _format_float(best.get("micro_f1")),
                    _format_float(best.get("hit_rate")),
                    _format_float(best.get("micro_precision")),
                    _format_float(best.get("micro_recall")),
                    _format_float(best.get("threshold")),
                    _format_int(best.get("top_k")),
                    _format_float(
                        summary.latency_metrics.get("avg_latency_ms")
                        if summary.latency_metrics
                        else None,
                    ),
                    _format_int(best.get("distraction_false_positive_count")),
                    str(summary.artifact_dir),
                ],
            )
            + " |"
        )

    lines.append("")
    lines.append("## Inference Latency")
    lines.append("")
    lines.append("| Model | Repeats | Query Source | Min Latency (ms) | Avg Latency (ms) | Max Latency (ms) |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for summary in ranked:
        latency = summary.latency_metrics or {}
        lines.append(
            "| "
            + " | ".join(
                [
                    summary.model_name,
                    _format_int(latency.get("repeats")),
                    str(latency.get("query_source", "-")),
                    _format_float(latency.get("min_latency_ms")),
                    _format_float(latency.get("avg_latency_ms")),
                    _format_float(latency.get("max_latency_ms")),
                ],
            )
            + " |"
        )

    lines.append("")
    lines.append("## Training-Time Eval Snapshot")
    lines.append("")
    lines.append("| Model | Eval Micro F1 | Eval Hit Rate | Eval Precision | Eval Recall | Eval Threshold | Eval Top-K |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for summary in ranked:
        metrics = summary.eval_metrics
        lines.append(
            "| "
            + " | ".join(
                [
                    summary.model_name,
                    _format_float(metrics.get("micro_f1")),
                    _format_float(metrics.get("hit_rate")),
                    _format_float(metrics.get("micro_precision")),
                    _format_float(metrics.get("micro_recall")),
                    _format_float(metrics.get("threshold")),
                    _format_int(metrics.get("top_k")),
                ],
            )
            + " |"
        )

    lines.append("")
    lines.append("## Notes")
    lines.append("")
    if len(ranked) >= 2:
        runner_up = ranked[1]
        gap = float(winner.best.get(winner.objective, 0.0)) - float(
            runner_up.best.get(runner_up.objective, 0.0),
        )
        lines.append(
            f"- {winner.model_name} ranks first on `{winner.objective}` with a margin of {_format_float(gap)} over {runner_up.model_name}.",
        )
    lines.append(
        f"- FastText best `micro_f1` is {_format_float(next(summary.best.get('micro_f1') for summary in summaries if summary.model_name == 'fasttext'))}."
        if any(summary.model_name == "fasttext" for summary in summaries)
        else "- FastText artifact was not included.",
    )
    lines.append(
        f"- Retrieval best `micro_f1` is {_format_float(next(summary.best.get('micro_f1') for summary in summaries if summary.model_name == 'retrieval'))}."
        if any(summary.model_name == "retrieval" for summary in summaries)
        else "- Retrieval artifact was not included.",
    )
    lines.append(
        f"- Encoder best `micro_f1` is {_format_float(next(summary.best.get('micro_f1') for summary in summaries if summary.model_name == 'encoder'))}."
        if any(summary.model_name == "encoder" for summary in summaries)
        else "- Encoder artifact was not included.",
    )
    if all(summary.latency_metrics for summary in summaries):
        fastest = min(
            summaries,
            key=lambda summary: float(summary.latency_metrics["avg_latency_ms"]),
        )
        lines.append(
            f"- {fastest.model_name} has the lowest average single-query latency at {_format_float(fastest.latency_metrics['avg_latency_ms'])} ms.",
        )
    lines.append("- This report compares each model at its own best grid-search operating point, not at one shared threshold/top-k.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    """CLI entrypoint.

    Args:
        None:
            Command line arguments are parsed from the active process.

    Returns:
        `None`:
            This function writes a Markdown report to disk.
    """
    parser = argparse.ArgumentParser(description="Generate a comparison report for router model artifacts")
    parser.add_argument(
        "--fasttext-artifact-dir",
        type=Path,
        default=Path("artifacts_fasttext_router_deploy"),
        help="Artifact directory for the FastText router",
    )
    parser.add_argument(
        "--retrieval-artifact-dir",
        type=Path,
        default=Path("artifacts_retrieval_router_deploy"),
        help="Artifact directory for the retrieval router",
    )
    parser.add_argument(
        "--encoder-artifact-dir",
        type=Path,
        default=Path("artifacts_encoder_router_deploy"),
        help="Artifact directory for the encoder router",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("router_model_report.md"),
        help="Output Markdown report path",
    )
    args = parser.parse_args()
    args.fasttext_artifact_dir = _resolve_local_path(args.fasttext_artifact_dir)
    args.retrieval_artifact_dir = _resolve_local_path(args.retrieval_artifact_dir)
    args.encoder_artifact_dir = _resolve_local_path(args.encoder_artifact_dir)
    args.output = _resolve_local_path(args.output)

    summaries = [
        _load_summary(model_name="fasttext", artifact_dir=args.fasttext_artifact_dir),
        _load_summary(model_name="retrieval", artifact_dir=args.retrieval_artifact_dir),
        _load_summary(model_name="encoder", artifact_dir=args.encoder_artifact_dir),
    ]
    report = _build_report(summaries)
    args.output.write_text(report, encoding="utf-8")
    print("[report] written:", args.output)


if __name__ == "__main__":
    main()