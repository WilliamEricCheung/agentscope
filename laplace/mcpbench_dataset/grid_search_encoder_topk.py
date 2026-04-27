# -*- coding: utf-8 -*-
"""Grid-search threshold and Top-K for the semantic encoder router."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _encoder_router import EncoderSemanticRouter, evaluate


@dataclass
class EvalSample:
    """One evaluation sample for threshold tuning.

    Args:
        task_id (`str`):
            Unique sample id.
        text (`str`):
            Query text.
        positive_servers (`list[str]`):
            Ground-truth positive servers.
        distraction_servers (`list[str]`):
            Distractor servers.
    """

    task_id: str
    text: str
    positive_servers: list[str]
    distraction_servers: list[str]


def _load_metadata(metadata_path: Path) -> dict[str, Any]:
    """Load artifact metadata.

    Args:
        metadata_path (`Path`):
            Metadata file path.

    Returns:
        `dict[str, Any]`:
            Parsed metadata.
    """
    with metadata_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _load_eval_samples(path: Path) -> list[EvalSample]:
    """Load eval samples dumped by the training script.

    Args:
        path (`Path`):
            Eval sample jsonl path.

    Returns:
        `list[EvalSample]`:
            Loaded eval samples.
    """
    samples: list[EvalSample] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            row = json.loads(line)
            samples.append(
                EvalSample(
                    task_id=str(row["task_id"]),
                    text=str(row["text"]),
                    positive_servers=list(row["positive_servers"]),
                    distraction_servers=list(row.get("distraction_servers", [])),
                ),
            )
    if not samples:
        raise ValueError("No eval samples loaded")
    return samples


def _parse_float_list(raw: str) -> list[float]:
    """Parse a comma-separated float list.

    Args:
        raw (`str`):
            Raw comma-separated values.

    Returns:
        `list[float]`:
            Parsed floats.
    """
    return [float(item.strip()) for item in raw.split(",") if item.strip()]


def _parse_int_list(raw: str) -> list[int]:
    """Parse a comma-separated int list.

    Args:
        raw (`str`):
            Raw comma-separated values.

    Returns:
        `list[int]`:
            Parsed integers.
    """
    return [int(item.strip()) for item in raw.split(",") if item.strip()]


def _add_composite_score(
    results: list[dict[str, float | int]],
    weight_f1: float,
    weight_distraction: float,
) -> None:
    """Add distraction-aware composite scores to trial rows.

    Args:
        results (`list[dict[str, float | int]]`):
            Trial metrics.
        weight_f1 (`float`):
            Weight on micro-f1.
        weight_distraction (`float`):
            Weight on distraction false positive rate.

    Returns:
        `None`:
            The list is updated in place.
    """
    for row in results:
        samples = int(row.get("samples", 0) or 0)
        distraction_fp = int(row.get("distraction_false_positive_count", 0) or 0)
        distraction_fp_rate = float(distraction_fp) / float(samples) if samples > 0 else 0.0
        row["distraction_fp_rate"] = round(distraction_fp_rate, 6)
        composite = weight_f1 * float(row.get("micro_f1", 0.0)) - weight_distraction * distraction_fp_rate
        row["composite_score"] = round(composite, 6)


def main() -> None:
    """CLI entrypoint.

    Args:
        None:
            Command line arguments are parsed from the active process.

    Returns:
        `None`:
            This function writes the search result file to disk.
    """
    parser = argparse.ArgumentParser(description="Grid search threshold + top-k for encoder router")
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("artifacts_encoder_router_deploy"),
        help="Directory produced by train_encoder_semantic_router.py",
    )
    parser.add_argument(
        "--thresholds",
        type=str,
        default="0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40,0.45,0.50",
    )
    parser.add_argument("--topk-list", type=str, default="1,2,3")
    parser.add_argument(
        "--objective",
        choices=["composite_score", "micro_f1", "hit_rate", "micro_precision", "micro_recall"],
        default="composite_score",
    )
    parser.add_argument("--composite-weight-f1", type=float, default=1.0)
    parser.add_argument("--composite-weight-distraction", type=float, default=0.3)
    parser.add_argument("--ensure-non-empty", action="store_true")
    args = parser.parse_args()

    metadata_path = args.artifact_dir / "metadata.json"
    eval_path = args.artifact_dir / "eval_samples.jsonl"
    model_dir = args.artifact_dir / "semantic_router_encoder_model"
    prototype_path = args.artifact_dir / "semantic_router_encoder_prototypes.npz"

    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
    if not eval_path.exists():
        raise FileNotFoundError(f"Eval samples not found: {eval_path}")
    if not model_dir.exists():
        raise FileNotFoundError(f"Encoder model dir not found: {model_dir}")
    if not prototype_path.exists():
        raise FileNotFoundError(f"Prototype file not found: {prototype_path}")

    metadata = _load_metadata(metadata_path)
    eval_samples = _load_eval_samples(eval_path)
    model = EncoderSemanticRouter.load(args.artifact_dir)

    thresholds = _parse_float_list(args.thresholds)
    topk_list = _parse_int_list(args.topk_list)

    results: list[dict[str, float | int]] = []
    for threshold in thresholds:
        for top_k in topk_list:
            metrics = evaluate(
                model=model,
                samples=eval_samples,
                threshold=threshold,
                top_k=top_k,
                ensure_non_empty=args.ensure_non_empty,
            )
            results.append(metrics)

    _add_composite_score(
        results=results,
        weight_f1=args.composite_weight_f1,
        weight_distraction=args.composite_weight_distraction,
    )
    if not results:
        raise ValueError("No grid-search trials executed")

    best = max(results, key=lambda row: float(row[args.objective]))
    payload = {
        "router_family": metadata.get("router_family", "encoder_sentence_transformer"),
        "objective": args.objective,
        "composite": {
            "weight_f1": args.composite_weight_f1,
            "weight_distraction": args.composite_weight_distraction,
            "formula": "weight_f1 * micro_f1 - weight_distraction * distraction_fp_rate",
        },
        "best": best,
        "trials": results,
    }
    output_path = args.artifact_dir / "grid_search_results.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("[grid-search] best:", json.dumps(best, ensure_ascii=False))
    print("[grid-search] full results:", output_path)


if __name__ == "__main__":
    main()