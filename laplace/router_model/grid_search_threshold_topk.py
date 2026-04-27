# -*- coding: utf-8 -*-
"""Grid-search confidence threshold and Top-K for FastText semantic router."""

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
class EvalSample:
    """One evaluation sample for threshold tuning."""

    task_id: str
    text: str
    positive_servers: list[str]
    distraction_servers: list[str]


def _load_metadata(metadata_path: Path) -> dict[str, Any]:
    with metadata_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_eval_samples(path: Path) -> list[EvalSample]:
    samples: list[EvalSample] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
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


def _safe_predict_labels_probs(
    model: Any,
    text: str,
    k: int,
) -> tuple[list[str], list[float]]:
    """Predict labels/probabilities with NumPy 2.x compatible fallback."""
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
    labels, probs = _safe_predict_labels_probs(model, text, k=-1)
    scored: list[tuple[str, float]] = []
    for raw, prob in zip(labels, probs):
        label = raw.replace("__label__", "", 1)
        server = label_to_server.get(label)
        if server is None:
            continue
        scored.append((server, float(prob)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def _predict_with_threshold(
    model: Any,
    text: str,
    label_to_server: dict[str, str],
    threshold: float,
    top_k: int,
    ensure_non_empty: bool,
) -> set[str]:
    scored = _predict_all_scores(model, text, label_to_server)
    selected = [server for server, prob in scored if prob >= threshold][:top_k]
    if not selected and ensure_non_empty and scored:
        selected = [scored[0][0]]
    return set(selected)


def _evaluate(
    model: Any,
    samples: list[EvalSample],
    label_to_server: dict[str, str],
    threshold: float,
    top_k: int,
    ensure_non_empty: bool,
) -> dict[str, float | int]:
    tp = fp = fn = 0
    hit = 0
    distraction_fp = 0

    for sample in samples:
        pred = _predict_with_threshold(
            model=model,
            text=sample.text,
            label_to_server=label_to_server,
            threshold=threshold,
            top_k=top_k,
            ensure_non_empty=ensure_non_empty,
        )
        true_set = set(sample.positive_servers)
        tp += len(pred & true_set)
        fp += len(pred - true_set)
        fn += len(true_set - pred)

        if pred & true_set:
            hit += 1

        if sample.distraction_servers:
            distraction_fp += len(pred & set(sample.distraction_servers))

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    total = len(samples)
    return {
        "threshold": threshold,
        "top_k": top_k,
        "micro_precision": round(precision, 6),
        "micro_recall": round(recall, 6),
        "micro_f1": round(f1, 6),
        "hit_rate": round(hit / total if total else 0.0, 6),
        "distraction_false_positive_count": distraction_fp,
        "samples": total,
    }


def _parse_float_list(raw: str) -> list[float]:
    return [float(x.strip()) for x in raw.split(",") if x.strip()]


def _parse_int_list(raw: str) -> list[int]:
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def _add_composite_score(
    results: list[dict[str, float | int]],
    weight_f1: float,
    weight_distraction: float,
) -> None:
    """Attach a robust composite score to each trial in-place.

    Composite score definition:
        composite_score = weight_f1 * micro_f1
                          - weight_distraction * distraction_fp_rate
    """
    for row in results:
        samples = int(row.get("samples", 0) or 0)
        distraction_fp = int(row.get("distraction_false_positive_count", 0) or 0)
        distraction_fp_rate = (
            float(distraction_fp) / float(samples) if samples > 0 else 0.0
        )
        row["distraction_fp_rate"] = round(distraction_fp_rate, 6)
        composite = (
            weight_f1 * float(row.get("micro_f1", 0.0))
            - weight_distraction * distraction_fp_rate
        )
        row["composite_score"] = round(composite, 6)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Grid search threshold + top-k for fastText router",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("artifacts_fasttext_router_deploy"),
        help="Directory produced by train_fasttext_semantic_router.py",
    )
    parser.add_argument(
        "--thresholds",
        type=str,
        default="0.10,0.15,0.20,0.25,0.30,0.35,0.40,0.45,0.50,0.55,0.60",
    )
    parser.add_argument("--topk-list", type=str, default="1,2,3")
    parser.add_argument(
        "--objective",
        choices=[
            "composite_score",
            "micro_f1",
            "hit_rate",
            "micro_precision",
            "micro_recall",
        ],
        default="composite_score",
    )
    parser.add_argument(
        "--composite-weight-f1",
        type=float,
        default=1.0,
        help="Weight for micro_f1 in composite score",
    )
    parser.add_argument(
        "--composite-weight-distraction",
        type=float,
        default=0.3,
        help="Penalty weight for distraction_fp_rate in composite score",
    )
    parser.add_argument("--ensure-non-empty", action="store_true")
    args = parser.parse_args()
    args.artifact_dir = _resolve_local_path(args.artifact_dir)

    model_path = args.artifact_dir / "semantic_router_fasttext.bin"
    metadata_path = args.artifact_dir / "metadata.json"
    eval_path = args.artifact_dir / "eval_samples.jsonl"

    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
    if not eval_path.exists():
        raise FileNotFoundError(f"Eval samples not found: {eval_path}")

    metadata = _load_metadata(metadata_path)
    label_map = metadata.get("label_map", {})
    if not label_map:
        raise ValueError("label_map is missing in metadata")

    label_to_server = {label: server for server, label in label_map.items()}
    eval_samples = _load_eval_samples(eval_path)

    import fasttext  # lazy import

    model = fasttext.load_model(str(model_path))

    thresholds = _parse_float_list(args.thresholds)
    topk_list = _parse_int_list(args.topk_list)

    results: list[dict[str, float | int]] = []
    for threshold in thresholds:
        for top_k in topk_list:
            metrics = _evaluate(
                model=model,
                samples=eval_samples,
                label_to_server=label_to_server,
                threshold=threshold,
                top_k=top_k,
                ensure_non_empty=args.ensure_non_empty,
            )
            results.append(metrics)

    _add_composite_score(
        results,
        weight_f1=args.composite_weight_f1,
        weight_distraction=args.composite_weight_distraction,
    )

    results.sort(
        key=lambda x: (
            float(x[args.objective]),
            float(x["micro_recall"]),
            -float(x.get("distraction_fp_rate", 0.0)),
            -float(x["distraction_false_positive_count"]),
        ),
        reverse=True,
    )

    best = results[0]
    output = {
        "objective": args.objective,
        "composite": {
            "weight_f1": args.composite_weight_f1,
            "weight_distraction": args.composite_weight_distraction,
            "formula": "weight_f1 * micro_f1 - weight_distraction * distraction_fp_rate",
        },
        "best": best,
        "trials": results,
    }

    out_path = args.artifact_dir / "grid_search_results.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[grid-search] best:", json.dumps(best, ensure_ascii=False))
    print("[grid-search] full results:", out_path)


if __name__ == "__main__":
    main()
