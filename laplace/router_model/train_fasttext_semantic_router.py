# -*- coding: utf-8 -*-
"""Train a single-skill FastText semantic router on MCP-Bench task data.

This script supports:
1) training from single-skill MCP-Bench runner-format JSON
2) confidence-threshold + Top-K prediction
3) optional quick evaluation on a held-out split
4) exporting eval samples for threshold grid search
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from pathlib import Path
from typing import Any

from _router_data import (
    Sample,
    load_samples_from_datasets,
    normalize_text,
    parse_dataset_paths,
    save_eval_samples,
    split_samples_with_audit,
)


_LABEL_PREFIX = "__label__"
_SCRIPT_DIR = Path(__file__).resolve().parent
_DATASET_DIR = _SCRIPT_DIR.parent / "mcp_dataset"

def _normalize_label(server_name: str) -> str:
    """Normalize server name into fastText-compatible label suffix."""
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", server_name.strip().lower())
    normalized = normalized.strip("_")
    return normalized or "unknown"


def _resolve_local_path(path: Path) -> Path:
    """Resolve relative paths against the router_model directory."""
    return path if path.is_absolute() else (_SCRIPT_DIR / path)


def _build_label_maps(samples: list[Sample]) -> tuple[dict[str, str], dict[str, str]]:
    """Build fastText label mappings.

    Returns:
        tuple[dict[str, str], dict[str, str]]:
            server_to_label and label_to_server
    """
    server_names = sorted({srv for s in samples for srv in s.positive_servers})
    server_to_label: dict[str, str] = {}
    used: set[str] = set()

    for server in server_names:
        candidate = _normalize_label(server)
        if candidate not in used:
            server_to_label[server] = candidate
            used.add(candidate)
            continue

        suffix = 2
        while f"{candidate}_{suffix}" in used:
            suffix += 1
        deduped = f"{candidate}_{suffix}"
        server_to_label[server] = deduped
        used.add(deduped)

    label_to_server = {label: server for server, label in server_to_label.items()}
    return server_to_label, label_to_server


def _write_fasttext_train_file(
    train_samples: list[Sample],
    server_to_label: dict[str, str],
    output_path: Path,
) -> None:
    """Write fastText supervised training lines for single-skill routing."""
    with output_path.open("w", encoding="utf-8") as f:
        for sample in train_samples:
            server = sample.positive_servers[0]
            label = server_to_label[server]
            f.write(f"{_LABEL_PREFIX}{label} {sample.text}\n")


def train_fasttext_model(
    train_file: Path,
    output_model_prefix: Path,
    epoch: int,
    lr: float,
    word_ngrams: int,
    dim: int,
    minn: int,
    maxn: int,
) -> None:
    """Train and save a fastText supervised model."""
    import fasttext  # lazy import to avoid hard dependency at module import

    model = fasttext.train_supervised(
        input=str(train_file),
        epoch=epoch,
        lr=lr,
        wordNgrams=word_ngrams,
        dim=dim,
        minn=minn,
        maxn=maxn,
        loss="ova",
    )
    model.save_model(str(output_model_prefix.with_suffix(".bin")))


def _safe_predict_labels_probs(
    model: Any,
    text: str,
    k: int,
) -> tuple[list[str], list[float]]:
    """Predict labels/probabilities with NumPy 2.x compatible fallback.

    Some fasttext wheels call ``np.array(..., copy=False)`` internally, which
    raises on NumPy 2.x in specific paths. This helper first tries the standard
    wrapper API and falls back to ``model.f.predict`` when needed.
    """
    try:
        labels, probs = model.predict(text, k=k)
        return list(labels), [float(p) for p in probs]
    except ValueError as exc:
        if "Unable to avoid copy" not in str(exc):
            raise

        backend = getattr(model, "f", None)
        if backend is None:
            raise

        k_resolved = k
        if k_resolved < 0:
            labels_all = model.get_labels()
            k_resolved = len(labels_all)

        predictions = backend.predict(text, k_resolved, 0.0, "strict")
        if not predictions:
            return [], []

        probs, labels = zip(*predictions)
        return list(labels), [float(p) for p in probs]


def _predict_all_scores(model: Any, text: str, label_to_server: dict[str, str]) -> list[tuple[str, float]]:
    """Predict all label scores and map back to server names."""
    labels, probs = _safe_predict_labels_probs(model, text, k=-1)
    pairs: list[tuple[str, float]] = []
    for raw_label, prob in zip(labels, probs):
        suffix = raw_label[len(_LABEL_PREFIX) :] if raw_label.startswith(_LABEL_PREFIX) else raw_label
        server = label_to_server.get(suffix)
        if server is None:
            continue
        pairs.append((server, float(prob)))

    pairs.sort(key=lambda x: x[1], reverse=True)
    return pairs


def predict_topk_with_threshold(
    model: Any,
    text: str,
    label_to_server: dict[str, str],
    threshold: float,
    top_k: int,
    ensure_non_empty: bool,
) -> list[tuple[str, float]]:
    """Return threshold-filtered Top-K server predictions."""
    scored = _predict_all_scores(model, text, label_to_server)
    selected = [(s, p) for s, p in scored if p >= threshold][:top_k]

    if not selected and ensure_non_empty and scored:
        selected = scored[:1]

    return selected


def evaluate(
    model: Any,
    samples: list[Sample],
    label_to_server: dict[str, str],
    threshold: float,
    top_k: int,
    ensure_non_empty: bool,
) -> dict[str, float | int]:
    """Evaluate multi-label routing metrics."""
    tp = fp = fn = 0
    total = 0
    hit = 0
    distraction_fp = 0

    for sample in samples:
        total += 1
        pred = predict_topk_with_threshold(
            model=model,
            text=sample.text,
            label_to_server=label_to_server,
            threshold=threshold,
            top_k=top_k,
            ensure_non_empty=ensure_non_empty,
        )
        pred_set = {s for s, _ in pred}
        true_set = set(sample.positive_servers)

        tp += len(pred_set & true_set)
        fp += len(pred_set - true_set)
        fn += len(true_set - pred_set)

        if pred_set & true_set:
            hit += 1

        if sample.distraction_servers:
            distraction_fp += len(pred_set & set(sample.distraction_servers))

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return {
        "samples": total,
        "threshold": threshold,
        "top_k": top_k,
        "micro_precision": round(precision, 6),
        "micro_recall": round(recall, 6),
        "micro_f1": round(f1, 6),
        "hit_rate": round(hit / total if total else 0.0, 6),
        "distraction_false_positive_count": distraction_fp,
    }


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Train FastText semantic router")
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
        help=(
            "Comma-separated single-skill dataset paths for joint training into "
            "one model"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts_fasttext_router_deploy"),
        help="Directory for trained model and metadata",
    )
    parser.add_argument(
        "--text-mode",
        choices=["fuzzy", "task", "both", "split_both"],
        default="split_both",
        help="Which text field to use as training text",
    )
    parser.add_argument(
        "--query-only",
        action="store_true",
        help="Alias for query-side-only input; currently equivalent to --text-mode fuzzy",
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

    parser.add_argument("--epoch", type=int, default=30)
    parser.add_argument("--lr", type=float, default=0.6)
    parser.add_argument("--word-ngrams", type=int, default=2)
    parser.add_argument("--dim", type=int, default=100)
    parser.add_argument("--minn", type=int, default=2)
    parser.add_argument("--maxn", type=int, default=5)

    parser.add_argument("--threshold", type=float, default=0.35)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--ensure-non-empty", action="store_true")

    parser.add_argument(
        "--query",
        type=str,
        default="",
        help="Optional single query text for interactive prediction",
    )

    args = parser.parse_args()
    if args.query_only:
        args.text_mode = "fuzzy"
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

    server_to_label, label_to_server = _build_label_maps(all_samples)

    with tempfile.TemporaryDirectory() as tmpdir:
        train_file = Path(tmpdir) / "fasttext_train.txt"
        _write_fasttext_train_file(train_samples, server_to_label, train_file)

        model_prefix = args.output_dir / "semantic_router_fasttext"
        train_fasttext_model(
            train_file=train_file,
            output_model_prefix=model_prefix,
            epoch=args.epoch,
            lr=args.lr,
            word_ngrams=args.word_ngrams,
            dim=args.dim,
            minn=args.minn,
            maxn=args.maxn,
        )

    metadata = {
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
        "query_only": bool(args.query_only),
        "hyperparameters": {
            "epoch": args.epoch,
            "lr": args.lr,
            "word_ngrams": args.word_ngrams,
            "dim": args.dim,
            "minn": args.minn,
            "maxn": args.maxn,
        },
        "label_map": server_to_label,
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

    import fasttext  # lazy import

    model = fasttext.load_model(str((args.output_dir / "semantic_router_fasttext.bin")))
    metrics = evaluate(
        model=model,
        samples=eval_samples,
        label_to_server=label_to_server,
        threshold=args.threshold,
        top_k=args.top_k,
        ensure_non_empty=args.ensure_non_empty,
    )

    metrics_path = args.output_dir / "eval_metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("[train] model saved:", args.output_dir / "semantic_router_fasttext.bin")
    print("[train] metadata:", metadata_path)
    print("[train] eval samples:", eval_dump)
    print("[eval]", json.dumps(metrics, ensure_ascii=False))

    if args.query.strip():
        query = normalize_text(args.query)
        pred = predict_topk_with_threshold(
            model=model,
            text=query,
            label_to_server=label_to_server,
            threshold=args.threshold,
            top_k=args.top_k,
            ensure_non_empty=args.ensure_non_empty,
        )
        print("[predict]", json.dumps(pred, ensure_ascii=False))


if __name__ == "__main__":
    main()
