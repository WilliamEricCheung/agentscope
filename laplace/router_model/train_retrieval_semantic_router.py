# -*- coding: utf-8 -*-
"""Train a single-skill retrieval semantic router on MCP-Bench task data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _retrieval_router import RetrievalSemanticRouter, evaluate, predict_topk_with_threshold
from _router_data import (
    load_samples_from_datasets,
    parse_dataset_paths,
    save_eval_samples,
    split_samples_with_audit,
)


_SCRIPT_DIR = Path(__file__).resolve().parent
_DATASET_DIR = _SCRIPT_DIR.parent / "mcp_dataset"


def _resolve_local_path(path: Path) -> Path:
    """Resolve relative paths against the router_model directory."""
    return path if path.is_absolute() else (_SCRIPT_DIR / path)


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Train retrieval semantic router",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=_DATASET_DIR / "laplace_tasks_single_runner_format.json",
        help="Single-skill dataset path (used when --datasets is not provided)",
    )
    parser.add_argument(
        "--datasets",
        type=str,
        default=f"{_DATASET_DIR / 'laplace_tasks_single_runner_format.json'}",
        help="Comma-separated single-skill dataset paths",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts_retrieval_router_deploy"),
        help="Directory for trained model and metadata",
    )
    parser.add_argument(
        "--text-mode",
        choices=["fuzzy", "task", "both", "split_both"],
        default="split_both",
        help="Which text field to use as training text",
    )
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--eval-seed", type=int, default=42)
    parser.add_argument(
        "--split-method",
        choices=["stratified_by_server", "grouped_by_server_similarity"],
        default="grouped_by_server_similarity",
        help="How to split train/eval examples",
    )
    parser.add_argument(
        "--dedupe-method",
        choices=["none", "exact_text_per_server"],
        default="exact_text_per_server",
        help="Whether to remove exact duplicate texts before splitting",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.8,
        help="Lexical Jaccard threshold used by grouped split",
    )
    parser.add_argument("--threshold", type=float, default=0.35)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--ensure-non-empty", action="store_true")

    parser.add_argument("--max-features", type=int, default=20000)
    parser.add_argument("--min-df", type=int, default=1)
    parser.add_argument("--char-ngram-min", type=int, default=3)
    parser.add_argument("--char-ngram-max", type=int, default=5)
    parser.add_argument("--disable-word-bigrams", action="store_true")
    parser.add_argument("--top-neighbors", type=int, default=16)

    parser.add_argument(
        "--query",
        type=str,
        default="",
        help="Optional single query text for interactive prediction",
    )

    args = parser.parse_args()
    args.output_dir = _resolve_local_path(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    dataset_paths = parse_dataset_paths(args.dataset, args.datasets)
    dataset_paths = [_resolve_local_path(path) for path in dataset_paths]
    all_samples = load_samples_from_datasets(
        dataset_paths=dataset_paths,
        text_mode=args.text_mode,
    )
    train_samples, eval_samples, split_audit = split_samples_with_audit(
        all_samples,
        train_ratio=args.train_ratio,
        eval_seed=args.eval_seed,
        split_method=args.split_method,
        dedupe_method=args.dedupe_method,
        similarity_threshold=args.similarity_threshold,
    )

    model = RetrievalSemanticRouter.fit(
        train_samples=train_samples,
        max_features=args.max_features,
        min_df=args.min_df,
        char_ngram_range=(args.char_ngram_min, args.char_ngram_max),
        use_word_bigrams=not args.disable_word_bigrams,
        top_neighbors=args.top_neighbors,
    )
    model_prefix = args.output_dir / "semantic_router_retrieval"
    model.save(model_prefix)

    metadata = {
        "router_family": "retrieval_tfidf",
        "datasets": [str(path) for path in dataset_paths],
        "joint_training": len(dataset_paths) > 1,
        "training_mode": "single_only",
        "text_mode": args.text_mode,
        "train_ratio": args.train_ratio,
        "seed": args.seed,
        "eval_seed": args.eval_seed,
        "split_method": args.split_method,
        "dedupe_method": args.dedupe_method,
        "similarity_threshold": args.similarity_threshold,
        "split_audit": split_audit.to_dict(),
        "hyperparameters": {
            "max_features": args.max_features,
            "min_df": args.min_df,
            "char_ngram_min": args.char_ngram_min,
            "char_ngram_max": args.char_ngram_max,
            "use_word_bigrams": not args.disable_word_bigrams,
            "top_neighbors": args.top_neighbors,
        },
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

    print("[train] model saved:", model_prefix.with_suffix(".npz"))
    print("[train] model config:", model_prefix.with_suffix(".json"))
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
