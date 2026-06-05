# -*- coding: utf-8 -*-
"""Run the router benchmark suite for one or more text modes."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


_SCRIPT_DIR = Path(__file__).resolve().parent
_DATASET_DIR = _SCRIPT_DIR.parent / "mcp_dataset"


def _resolve_local_path(path: Path) -> Path:
    """Resolve relative paths against the router_model directory."""
    return path if path.is_absolute() else (_SCRIPT_DIR / path)


def _run(command: list[str]) -> None:
    """Run one child command inside the router_model directory."""
    print("[suite]", " ".join(command))
    subprocess.run(command, cwd=_SCRIPT_DIR, check=True)


def _build_mode_args(args: argparse.Namespace, text_mode: str) -> list[str]:
    """Build shared CLI arguments for one text mode."""
    return [
        "--datasets",
        args.datasets,
        "--text-mode",
        text_mode,
        "--train-ratio",
        str(args.train_ratio),
        "--seed",
        str(args.seed),
        "--eval-seed",
        str(args.eval_seed),
        "--split-method",
        args.split_method,
        "--dedupe-method",
        args.dedupe_method,
        "--similarity-threshold",
        str(args.similarity_threshold),
    ]


def _resolve_mode_output_paths(
    args: argparse.Namespace,
    text_mode: str,
) -> tuple[Path, Path, Path, Path, Path]:
    """Resolve artifact and report paths for one benchmark mode."""
    single_mode = len(args.text_modes_list) == 1
    if single_mode:
        mode_dir = args.output_root
        report_name = "router_model_report.md"
    else:
        mode_dir = args.output_root / text_mode
        report_name = f"router_model_report_{text_mode}.md"

    mode_dir.mkdir(parents=True, exist_ok=True)
    retrieval_dir = mode_dir / "artifacts_retrieval_router_deploy"
    encoder_dir = mode_dir / "artifacts_encoder_router_deploy"
    fasttext_dir = mode_dir / "artifacts_fasttext_router_deploy"
    latency_summary = mode_dir / "router_latency_summary.json"
    report_path = mode_dir / report_name
    return retrieval_dir, encoder_dir, fasttext_dir, latency_summary, report_path


def _run_one_mode(args: argparse.Namespace, text_mode: str) -> None:
    """Train, tune, benchmark, and report one text mode."""
    retrieval_dir, encoder_dir, fasttext_dir, latency_summary, report_path = (
        _resolve_mode_output_paths(args, text_mode)
    )

    shared_args = _build_mode_args(args, text_mode)

    _run(
        [
            sys.executable,
            "train_retrieval_semantic_router.py",
            "--output-dir",
            str(retrieval_dir),
            *shared_args,
        ],
    )
    _run(
        [
            sys.executable,
            "grid_search_retrieval_topk.py",
            "--artifact-dir",
            str(retrieval_dir),
        ],
    )

    _run(
        [
            sys.executable,
            "train_encoder_semantic_router.py",
            "--output-dir",
            str(encoder_dir),
            *shared_args,
        ],
    )
    _run(
        [
            sys.executable,
            "grid_search_encoder_topk.py",
            "--artifact-dir",
            str(encoder_dir),
        ],
    )

    fasttext_command = [
        sys.executable,
        "train_fasttext_semantic_router.py",
        "--output-dir",
        str(fasttext_dir),
        *shared_args,
    ]
    if text_mode == "fuzzy":
        fasttext_command.append("--query-only")
    _run(fasttext_command)
    _run(
        [
            sys.executable,
            "grid_search_threshold_topk.py",
            "--artifact-dir",
            str(fasttext_dir),
        ],
    )

    _run(
        [
            sys.executable,
            "benchmark_router_latency.py",
            "--fasttext-artifact-dir",
            str(fasttext_dir),
            "--retrieval-artifact-dir",
            str(retrieval_dir),
            "--encoder-artifact-dir",
            str(encoder_dir),
            "--repeats",
            str(args.latency_repeats),
            "--summary-output",
            str(latency_summary),
        ],
    )
    _run(
        [
            sys.executable,
            "generate_router_model_report.py",
            "--fasttext-artifact-dir",
            str(fasttext_dir),
            "--retrieval-artifact-dir",
            str(retrieval_dir),
            "--encoder-artifact-dir",
            str(encoder_dir),
            "--output",
            str(report_path),
        ],
    )


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run router benchmark suite across text modes")
    parser.add_argument(
        "--datasets",
        type=str,
        default=str(_DATASET_DIR / "laplace_tasks_single_runner_format.json"),
        help="Comma-separated dataset paths",
    )
    parser.add_argument(
        "--text-modes",
        type=str,
        default="split_both",
        help="Comma-separated text modes to benchmark",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("."),
        help=(
            "Base directory for artifacts and reports. Single-mode runs write "
            "directly under this directory; multi-mode runs create per-mode subdirectories."
        ),
    )
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--eval-seed", type=int, default=42)
    parser.add_argument(
        "--split-method",
        choices=["stratified_by_server", "grouped_by_server_similarity"],
        default="grouped_by_server_similarity",
    )
    parser.add_argument(
        "--dedupe-method",
        choices=["none", "exact_text_per_server"],
        default="exact_text_per_server",
    )
    parser.add_argument("--similarity-threshold", type=float, default=0.8)
    parser.add_argument("--latency-repeats", type=int, default=20)
    args = parser.parse_args()

    args.output_root = _resolve_local_path(args.output_root)
    args.text_modes_list = [item.strip() for item in args.text_modes.split(",") if item.strip()]
    if not args.text_modes_list:
        raise ValueError("At least one text mode is required")

    for text_mode in args.text_modes_list:
        if text_mode not in {"fuzzy", "task", "both", "split_both"}:
            raise ValueError(f"Unsupported text mode: {text_mode}")
        _run_one_mode(args, text_mode)


if __name__ == "__main__":
    main()