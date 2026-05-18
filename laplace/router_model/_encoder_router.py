# -*- coding: utf-8 -*-
"""Small encoder router based on sentence-transformers."""

from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from _router_data import Sample


@dataclass
class EncoderTrainingArtifacts:
    """Artifacts required to serve the encoder router.

    Args:
        model_dir (`Path`):
            Directory that stores the fine-tuned encoder model.
        prototype_path (`Path`):
            Path to the saved server prototype matrix.
        config_path (`Path`):
            Path to the saved encoder config.
    """

    model_dir: Path
    prototype_path: Path
    config_path: Path


class EncoderSemanticRouter:
    """Sentence-transformer encoder with server-level prototype retrieval.

    Args:
        model (`Any`):
            The loaded sentence-transformers model.
        servers (`list[str]`):
            Ordered list of server names corresponding to prototype rows.
        prototypes (`np.ndarray`):
            Normalized prototype embeddings with shape `(num_servers, dim)`.
        model_name (`str`):
            The encoder checkpoint name used for initialization.
    """

    def __init__(
        self,
        model: Any,
        servers: list[str],
        prototypes: np.ndarray,
        model_name: str,
    ) -> None:
        self.model = model
        self.servers = servers
        self.prototypes = prototypes.astype(np.float32, copy=False)
        self.model_name = model_name

    @classmethod
    def fit(
        cls,
        train_samples: list[Sample],
        model_name: str,
        output_dir: Path,
        seed: int,
        epochs: int,
        batch_size: int,
        learning_rate: float,
        max_positive_pairs_per_label: int,
        negative_ratio: int,
    ) -> tuple["EncoderSemanticRouter", dict[str, int]]:
        """Fine-tune a small encoder and build server prototypes.

        Args:
            train_samples (`list[Sample]`):
                Single-skill train samples.
            model_name (`str`):
                Pretrained sentence-transformers checkpoint name.
            output_dir (`Path`):
                Output directory for saved model artifacts.
            seed (`int`):
                Random seed for pair construction.
            epochs (`int`):
                Fine-tuning epochs.
            batch_size (`int`):
                Training batch size.
            learning_rate (`float`):
                Optimizer learning rate.
            max_positive_pairs_per_label (`int`):
                Max adjacent positive pairs sampled per label.
            negative_ratio (`int`):
                Number of negative pairs generated per positive pair.

        Returns:
            `tuple[EncoderSemanticRouter, dict[str, int]]`:
                The fitted router and training statistics.
        """
        grouped_texts: dict[str, list[str]] = defaultdict(list)
        for sample in train_samples:
            grouped_texts[sample.positive_servers[0]].append(sample.text)

        examples, stats = _build_training_examples(
            grouped_texts=grouped_texts,
            seed=seed,
            max_positive_pairs_per_label=max_positive_pairs_per_label,
            negative_ratio=negative_ratio,
        )
        if not examples:
            raise ValueError("No encoder training pairs were constructed")

        from sentence_transformers import SentenceTransformer, losses  # lazy import
        from torch.utils.data import DataLoader  # lazy import

        model = SentenceTransformer(model_name)
        train_loader = DataLoader(examples, shuffle=True, batch_size=batch_size)
        train_loss = losses.CosineSimilarityLoss(model=model)
        warmup_steps = max(1, math.ceil(len(train_loader) * epochs * 0.1))
        model.fit(
            train_objectives=[(train_loader, train_loss)],
            epochs=epochs,
            warmup_steps=warmup_steps,
            optimizer_params={"lr": learning_rate},
            show_progress_bar=True,
        )

        servers, prototypes = _build_server_prototypes(model=model, train_samples=train_samples)
        router = cls(
            model=model,
            servers=servers,
            prototypes=prototypes,
            model_name=model_name,
        )
        router.save(output_dir=output_dir)
        return router, stats

    def encode(self, texts: list[str]) -> np.ndarray:
        """Encode texts into normalized dense vectors.

        Args:
            texts (`list[str]`):
                Input texts to encode.

        Returns:
            `np.ndarray`:
                Normalized embeddings.
        """
        vectors = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)

    def score(self, text: str) -> list[tuple[str, float]]:
        """Score all servers with cosine similarity to server prototypes.

        Args:
            text (`str`):
                Query text.

        Returns:
            `list[tuple[str, float]]`:
                Sorted `(server, score)` pairs.
        """
        query = self.encode([text])
        if query.size == 0:
            return []

        similarity = self.prototypes @ query[0]
        pairs = list(zip(self.servers, similarity.tolist(), strict=False))
        pairs.sort(key=lambda item: item[1], reverse=True)
        return [(server, float(score)) for server, score in pairs]

    def save(self, output_dir: Path) -> EncoderTrainingArtifacts:
        """Persist the fine-tuned encoder and prototype matrix.

        Args:
            output_dir (`Path`):
                Directory to persist model files.

        Returns:
            `EncoderTrainingArtifacts`:
                Saved artifact paths.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        model_dir = output_dir / "semantic_router_encoder_model"
        prototype_path = output_dir / "semantic_router_encoder_prototypes.npz"
        config_path = output_dir / "semantic_router_encoder_config.json"

        self.model.save(str(model_dir))
        np.savez_compressed(
            prototype_path,
            servers=np.array(self.servers, dtype=object),
            prototypes=self.prototypes,
        )
        config_path.write_text(
            json.dumps({"model_name": self.model_name}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return EncoderTrainingArtifacts(
            model_dir=model_dir,
            prototype_path=prototype_path,
            config_path=config_path,
        )

    @classmethod
    def load(cls, output_dir: Path) -> "EncoderSemanticRouter":
        """Load a fine-tuned encoder router from disk.

        Args:
            output_dir (`Path`):
                Directory containing saved model files.

        Returns:
            `EncoderSemanticRouter`:
                Loaded router instance.
        """
        from sentence_transformers import SentenceTransformer  # lazy import

        model_dir = output_dir / "semantic_router_encoder_model"
        prototype_path = output_dir / "semantic_router_encoder_prototypes.npz"
        config_path = output_dir / "semantic_router_encoder_config.json"

        config = json.loads(config_path.read_text(encoding="utf-8"))
        payload = np.load(prototype_path, allow_pickle=True)
        model = SentenceTransformer(str(model_dir))
        return cls(
            model=model,
            servers=[str(item) for item in payload["servers"].tolist()],
            prototypes=np.asarray(payload["prototypes"], dtype=np.float32),
            model_name=str(config["model_name"]),
        )


def _build_training_examples(
    grouped_texts: dict[str, list[str]],
    seed: int,
    max_positive_pairs_per_label: int,
    negative_ratio: int,
) -> tuple[list[Any], dict[str, int]]:
    """Create a compact pairwise similarity dataset for encoder training.

    Args:
        grouped_texts (`dict[str, list[str]]`):
            Train texts grouped by server label.
        seed (`int`):
            Random seed.
        max_positive_pairs_per_label (`int`):
            Max positive pairs per label.
        negative_ratio (`int`):
            Negative pairs per positive pair.

        Returns:
            `tuple[list[Any], dict[str, int]]`:
                InputExample list and basic pair statistics.
    """
    from sentence_transformers import InputExample  # lazy import

    rng = random.Random(seed)
    labels = sorted(grouped_texts)
    examples: list[Any] = []
    positive_pairs = 0
    negative_pairs = 0

    for label in labels:
        texts = list(grouped_texts[label])
        rng.shuffle(texts)
        pair_count = min(max(len(texts) - 1, 0), max_positive_pairs_per_label)
        for index in range(pair_count):
            examples.append(InputExample(texts=[texts[index], texts[index + 1]], label=1.0))
            positive_pairs += 1

    available_negative_labels = [label for label in labels if grouped_texts[label]]
    for label in labels:
        texts = list(grouped_texts[label])
        if not texts:
            continue
        for text in texts[:max_positive_pairs_per_label]:
            for _ in range(max(1, negative_ratio)):
                negative_label = rng.choice(
                    [item for item in available_negative_labels if item != label],
                )
                negative_text = rng.choice(grouped_texts[negative_label])
                examples.append(InputExample(texts=[text, negative_text], label=0.0))
                negative_pairs += 1

    rng.shuffle(examples)
    return examples, {
        "positive_pairs": positive_pairs,
        "negative_pairs": negative_pairs,
        "total_pairs": len(examples),
    }


def _build_server_prototypes(
    model: Any,
    train_samples: list[Sample],
) -> tuple[list[str], np.ndarray]:
    """Average train embeddings into one prototype per server.

    Args:
        model (`Any`):
            Fine-tuned sentence-transformers model.
        train_samples (`list[Sample]`):
            Train samples.

        Returns:
            `tuple[list[str], np.ndarray]`:
                Ordered server names and normalized prototype matrix.
    """
    texts = [sample.text for sample in train_samples]
    servers = [sample.positive_servers[0] for sample in train_samples]
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    grouped_vectors: dict[str, list[np.ndarray]] = defaultdict(list)
    for server, vector in zip(servers, embeddings, strict=False):
        grouped_vectors[server].append(np.asarray(vector, dtype=np.float32))

    ordered_servers = sorted(grouped_vectors)
    prototype_rows: list[np.ndarray] = []
    for server in ordered_servers:
        prototype = np.mean(np.vstack(grouped_vectors[server]), axis=0)
        norm = float(np.linalg.norm(prototype))
        if norm > 0.0:
            prototype = prototype / norm
        prototype_rows.append(np.asarray(prototype, dtype=np.float32))

    return ordered_servers, np.vstack(prototype_rows)


def predict_topk_with_threshold(
    model: EncoderSemanticRouter,
    text: str,
    threshold: float,
    top_k: int,
    ensure_non_empty: bool,
) -> list[tuple[str, float]]:
    """Return threshold-filtered Top-K server predictions.

    Args:
        model (`EncoderSemanticRouter`):
            Loaded encoder router.
        text (`str`):
            Query text.
        threshold (`float`):
            Minimum cosine score to keep.
        top_k (`int`):
            Max candidates to return.
        ensure_non_empty (`bool`):
            Whether to force at least one candidate.

        Returns:
            `list[tuple[str, float]]`:
                Selected predictions.
    """
    scored = model.score(text)
    selected = [(server, score) for server, score in scored if score >= threshold][:top_k]
    if not selected and ensure_non_empty and scored:
        selected = scored[:1]
    return selected


def evaluate(
    model: EncoderSemanticRouter,
    samples: list[Sample],
    threshold: float,
    top_k: int,
    ensure_non_empty: bool,
) -> dict[str, float | int]:
    """Evaluate single-skill routing metrics for the encoder router.

    Args:
        model (`EncoderSemanticRouter`):
            Loaded encoder router.
        samples (`list[Sample]`):
            Eval samples.
        threshold (`float`):
            Score threshold.
        top_k (`int`):
            Max predictions per sample.
        ensure_non_empty (`bool`):
            Whether to force one fallback candidate.

        Returns:
            `dict[str, float | int]`:
                Routing metrics.
    """
    tp = fp = fn = 0
    hit = 0
    distraction_fp = 0

    for sample in samples:
        pred = predict_topk_with_threshold(
            model=model,
            text=sample.text,
            threshold=threshold,
            top_k=top_k,
            ensure_non_empty=ensure_non_empty,
        )
        pred_set = {server for server, _ in pred}
        true_set = set(sample.positive_servers)

        tp += len(pred_set & true_set)
        fp += len(pred_set - true_set)
        fn += len(true_set - pred_set)
        if pred_set & true_set:
            hit += 1
        if sample.distraction_servers:
            distraction_fp += len(pred_set & set(sample.distraction_servers))

    total = len(samples)
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