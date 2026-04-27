# -*- coding: utf-8 -*-
"""Train a small semantic encoder router on single-skill MCP-Bench data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _encoder_router import EncoderSemanticRouter, evaluate, predict_topk_with_threshold
from _router_data import (
    load_samples_from_datasets,
    parse_dataset_paths,
    save_eval_samples,
    split_samples,
)


def main() -> None:
    """CLI entrypoint.

    Args:
        None:
            Command line arguments are parsed from the active process.

    Returns:
        `None`:
            This function writes artifacts to disk and prints metrics.
    """
    parser = argparse.ArgumentParser(description="Train encoder semantic router")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("mcpbench_tasks_single_runner_format.json"),
        help="Single-skill dataset path (used when --datasets is not provided)",
    )
    parser.add_argument(
        "--datasets",
        type=str,
        default=(
            "mcpbench_tasks_single_runner_format.json,"
            "laplace_tasks_single_runner_format.json"
        ),
        help="Comma-separated single-skill dataset paths",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts_encoder_router_deploy"),
        help="Directory for trained model and metadata",
    )
    parser.add_argument(
        "--text-mode",
        choices=["fuzzy", "task", "both"],
        default="both",
        help="Which text field to use as training text",
    )
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--threshold", type=float, default=0.35)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--ensure-non-empty", action="store_true")

    parser.add_argument(
        "--model-name",
        type=str,
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Sentence-transformers checkpoint used for initialization",
    )
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--max-positive-pairs-per-label", type=int, default=24)
    parser.add_argument("--negative-ratio", type=int, default=2)

    parser.add_argument(
        "--query",
        type=str,
        default="",
        help="Optional single query text for interactive prediction",
    )

    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    dataset_paths = parse_dataset_paths(args.dataset, args.datasets)
    all_samples = load_samples_from_datasets(
        dataset_paths=dataset_paths,
        text_mode=args.text_mode,
    )
    train_samples, eval_samples = split_samples(
        all_samples,
        train_ratio=args.train_ratio,
        seed=args.seed,
    )

    model, pair_stats = EncoderSemanticRouter.fit(
        train_samples=train_samples,
        model_name=args.model_name,
        output_dir=args.output_dir,
        seed=args.seed,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        max_positive_pairs_per_label=args.max_positive_pairs_per_label,
        negative_ratio=args.negative_ratio,
    )

    metadata = {
        "router_family": "encoder_sentence_transformer",
        "datasets": [str(path) for path in dataset_paths],
        "joint_training": len(dataset_paths) > 1,
        "training_mode": "single_only",
        "text_mode": args.text_mode,
        "train_ratio": args.train_ratio,
        "seed": args.seed,
        "hyperparameters": {
            "model_name": args.model_name,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "max_positive_pairs_per_label": args.max_positive_pairs_per_label,
            "negative_ratio": args.negative_ratio,
        },
        "pair_stats": pair_stats,
        "label_map": {
            server: server
            for server in sorted({sample.positive_servers[0] for sample in all_samples})
        },
        "train_samples": len(train_samples),
        "eval_samples": len(eval_samples),
    }
    metadata_path = args.output_dir / "metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    eval_dump = args.output_dir / "eval_samples.jsonl"
    save_eval_samples(eval_samples, eval_dump)

    metrics = evaluate(
        model=model,
        samples=eval_samples,
        threshold=args.threshold,
        top_k=args.top_k,
        ensure_non_empty=args.ensure_non_empty,
    )
    metrics_path = args.output_dir / "eval_metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("[train] model dir:", args.output_dir / "semantic_router_encoder_model")
    print(
        "[train] prototype file:",
        args.output_dir / "semantic_router_encoder_prototypes.npz",
    )
    print("[train] metadata:", metadata_path)
    print("[train] eval samples:", eval_dump)
    print("[eval]", json.dumps(metrics, ensure_ascii=False))

    if args.query.strip():
        pred = predict_topk_with_threshold(
            model=model,
            text=args.query,
            threshold=args.threshold,
            top_k=args.top_k,
            ensure_non_empty=args.ensure_non_empty,
        )
        print("[predict]", json.dumps(pred, ensure_ascii=False))


if __name__ == "__main__":
    main()