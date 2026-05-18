# -*- coding: utf-8 -*-
"""Benchmark inference latency for router model artifacts."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from _encoder_router import EncoderSemanticRouter, predict_topk_with_threshold as predict_encoder
from _retrieval_router import RetrievalSemanticRouter, predict_topk_with_threshold as predict_retrieval
from grid_search_threshold_topk import _predict_with_threshold as predict_fasttext  # type: ignore
from grid_search_threshold_topk import _load_eval_samples as load_fasttext_eval_samples  # type: ignore
from grid_search_threshold_topk import _load_metadata as load_fasttext_metadata  # type: ignore


_SCRIPT_DIR = Path(__file__).resolve().parent


def _resolve_local_path(path: Path) -> Path:
    """Resolve relative paths against the router_model directory."""
    return path if path.is_absolute() else (_SCRIPT_DIR / path)


@dataclass
class LatencyBenchmarkResult:
    """Latency benchmark result for one model.

    Args:
        model_name (`str`):
            Human-readable model name.
        artifact_dir (`Path`):
            Artifact directory path.
        repeats (`int`):
            Number of measured repetitions.
        query_source (`str`):
            Description of where the query came from.
        min_latency_ms (`float`):
            Minimum single-query latency in milliseconds.
        avg_latency_ms (`float`):
            Average single-query latency in milliseconds.
        max_latency_ms (`float`):
            Maximum single-query latency in milliseconds.
        threshold (`float`):
            Threshold used for prediction.
        top_k (`int`):
            Top-K used for prediction.
    """

    model_name: str
    artifact_dir: Path
    repeats: int
    query_source: str
    min_latency_ms: float
    avg_latency_ms: float
    max_latency_ms: float
    threshold: float
    top_k: int


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _load_best_operating_point(artifact_dir: Path) -> tuple[float, int]:
    payload = _load_json(artifact_dir / "grid_search_results.json")
    best = payload.get("best") or payload.get("best_by_objective")
    if best is None:
        raise ValueError(f"Best grid-search row missing in: {artifact_dir / 'grid_search_results.json'}")
    return float(best["threshold"]), int(best["top_k"])


def _load_query_text(artifact_dir: Path, explicit_query: str) -> tuple[str, str]:
    if explicit_query.strip():
        return explicit_query, "--query"

    eval_samples = load_fasttext_eval_samples(artifact_dir / "eval_samples.jsonl")
    first = eval_samples[0]
    return first.text, f"{artifact_dir / 'eval_samples.jsonl'}:{first.task_id}"


def _benchmark_callable(
    predict_fn: Callable[[], Any],
    repeats: int,
) -> tuple[float, float, float]:
    predict_fn()
    measurements_ms: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        predict_fn()
        end = time.perf_counter()
        measurements_ms.append((end - start) * 1000.0)
    return min(measurements_ms), sum(measurements_ms) / len(measurements_ms), max(measurements_ms)


def _build_fasttext_predictor(artifact_dir: Path, text: str) -> tuple[Callable[[], Any], float, int]:
    threshold, top_k = _load_best_operating_point(artifact_dir)
    metadata = load_fasttext_metadata(artifact_dir / "metadata.json")
    label_map = metadata.get("label_map", {})
    if not label_map:
        raise ValueError(f"label_map is missing in metadata for {artifact_dir}")
    label_to_server = {label: server for server, label in label_map.items()}

    import fasttext  # lazy import

    model = fasttext.load_model(str(artifact_dir / "semantic_router_fasttext.bin"))

    def _predict() -> Any:
        return predict_fasttext(
            model=model,
            text=text,
            label_to_server=label_to_server,
            threshold=threshold,
            top_k=top_k,
            ensure_non_empty=False,
        )

    return _predict, threshold, top_k


def _build_retrieval_predictor(artifact_dir: Path, text: str) -> tuple[Callable[[], Any], float, int]:
    threshold, top_k = _load_best_operating_point(artifact_dir)
    model = RetrievalSemanticRouter.load(artifact_dir / "semantic_router_retrieval")

    def _predict() -> Any:
        return predict_retrieval(
            model=model,
            text=text,
            threshold=threshold,
            top_k=top_k,
            ensure_non_empty=False,
        )

    return _predict, threshold, top_k


def _build_encoder_predictor(artifact_dir: Path, text: str) -> tuple[Callable[[], Any], float, int]:
    threshold, top_k = _load_best_operating_point(artifact_dir)
    model = EncoderSemanticRouter.load(artifact_dir)

    def _predict() -> Any:
        return predict_encoder(
            model=model,
            text=text,
            threshold=threshold,
            top_k=top_k,
            ensure_non_empty=False,
        )

    return _predict, threshold, top_k


def _write_result(artifact_dir: Path, result: LatencyBenchmarkResult) -> None:
    payload = {
        "model_name": result.model_name,
        "artifact_dir": str(result.artifact_dir),
        "repeats": result.repeats,
        "query_source": result.query_source,
        "min_latency_ms": round(result.min_latency_ms, 6),
        "avg_latency_ms": round(result.avg_latency_ms, 6),
        "max_latency_ms": round(result.max_latency_ms, 6),
        "threshold": result.threshold,
        "top_k": result.top_k,
    }
    (artifact_dir / "latency_benchmark.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Benchmark router model inference latency")
    parser.add_argument("--fasttext-artifact-dir", type=Path, default=Path("artifacts_fasttext_router_deploy"))
    parser.add_argument("--retrieval-artifact-dir", type=Path, default=Path("artifacts_retrieval_router_deploy"))
    parser.add_argument("--encoder-artifact-dir", type=Path, default=Path("artifacts_encoder_router_deploy"))
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--query", type=str, default="", help="Optional shared query text for all models")
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("router_latency_summary.json"),
        help="Summary output path",
    )
    args = parser.parse_args()
    args.fasttext_artifact_dir = _resolve_local_path(args.fasttext_artifact_dir)
    args.retrieval_artifact_dir = _resolve_local_path(args.retrieval_artifact_dir)
    args.encoder_artifact_dir = _resolve_local_path(args.encoder_artifact_dir)
    args.summary_output = _resolve_local_path(args.summary_output)

    if args.repeats <= 0:
        raise ValueError("repeats must be positive")

    query_text, query_source = _load_query_text(args.retrieval_artifact_dir, args.query)

    model_builders: list[tuple[str, Path, Callable[[Path, str], tuple[Callable[[], Any], float, int]]]] = [
        ("fasttext", args.fasttext_artifact_dir, _build_fasttext_predictor),
        ("retrieval", args.retrieval_artifact_dir, _build_retrieval_predictor),
        ("encoder", args.encoder_artifact_dir, _build_encoder_predictor),
    ]

    summary_rows: list[dict[str, Any]] = []
    for model_name, artifact_dir, builder in model_builders:
        predict_fn, threshold, top_k = builder(artifact_dir, query_text)
        min_latency_ms, avg_latency_ms, max_latency_ms = _benchmark_callable(
            predict_fn=predict_fn,
            repeats=args.repeats,
        )
        result = LatencyBenchmarkResult(
            model_name=model_name,
            artifact_dir=artifact_dir,
            repeats=args.repeats,
            query_source=query_source,
            min_latency_ms=min_latency_ms,
            avg_latency_ms=avg_latency_ms,
            max_latency_ms=max_latency_ms,
            threshold=threshold,
            top_k=top_k,
        )
        _write_result(artifact_dir, result)
        summary_rows.append(
            {
                "model_name": model_name,
                "artifact_dir": str(artifact_dir),
                "repeats": args.repeats,
                "query_source": query_source,
                "min_latency_ms": round(min_latency_ms, 6),
                "avg_latency_ms": round(avg_latency_ms, 6),
                "max_latency_ms": round(max_latency_ms, 6),
                "threshold": threshold,
                "top_k": top_k,
            },
        )
        print(
            "[latency]",
            json.dumps(summary_rows[-1], ensure_ascii=False),
        )

    args.summary_output.write_text(
        json.dumps(
            {
                "repeats": args.repeats,
                "query_source": query_source,
                "results": summary_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("[latency] summary:", args.summary_output)


if __name__ == "__main__":
    main()