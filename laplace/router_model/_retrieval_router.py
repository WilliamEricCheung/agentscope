# -*- coding: utf-8 -*-
"""Lightweight TF-IDF retrieval router for single-skill MCP routing."""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from _router_data import Sample, normalize_text


def _word_tokens(text: str) -> list[str]:
    """Tokenize text into normalized word tokens."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _char_ngrams(text: str, min_n: int, max_n: int) -> list[str]:
    """Extract character n-grams from normalized text."""
    normalized = f" {normalize_text(text).lower()} "
    grams: list[str] = []
    for n_size in range(min_n, max_n + 1):
        for idx in range(0, max(len(normalized) - n_size + 1, 0)):
            gram = normalized[idx : idx + n_size]
            if gram.strip():
                grams.append(gram)
    return grams


def extract_features(
    text: str,
    char_ngram_range: tuple[int, int],
    use_word_bigrams: bool,
) -> Counter[str]:
    """Extract sparse lexical features for retrieval."""
    tokens = _word_tokens(text)
    counts: Counter[str] = Counter()

    for token in tokens:
        counts[f"w:{token}"] += 1

    if use_word_bigrams:
        for left, right in zip(tokens, tokens[1:]):
            counts[f"wb:{left}_{right}"] += 1

    char_min, char_max = char_ngram_range
    for gram in _char_ngrams(text, char_min, char_max):
        counts[f"c:{gram}"] += 1

    return counts


class RetrievalSemanticRouter:
    """A tiny TF-IDF retrieval baseline for single-skill routing."""

    def __init__(
        self,
        vocabulary: dict[str, int],
        idf: np.ndarray,
        train_matrix: np.ndarray,
        train_labels: list[str],
        train_task_ids: list[str],
        char_ngram_range: tuple[int, int],
        use_word_bigrams: bool,
        top_neighbors: int,
    ) -> None:
        self.vocabulary = vocabulary
        self.idf = idf.astype(np.float32, copy=False)
        self.train_matrix = train_matrix.astype(np.float32, copy=False)
        self.train_labels = train_labels
        self.train_task_ids = train_task_ids
        self.char_ngram_range = char_ngram_range
        self.use_word_bigrams = use_word_bigrams
        self.top_neighbors = top_neighbors

    @classmethod
    def fit(
        cls,
        train_samples: list[Sample],
        max_features: int,
        min_df: int,
        char_ngram_range: tuple[int, int],
        use_word_bigrams: bool,
        top_neighbors: int,
    ) -> "RetrievalSemanticRouter":
        """Fit one retrieval router from train samples."""
        doc_features: list[Counter[str]] = []
        doc_freq: Counter[str] = Counter()
        for sample in train_samples:
            counts = extract_features(
                sample.text,
                char_ngram_range=char_ngram_range,
                use_word_bigrams=use_word_bigrams,
            )
            doc_features.append(counts)
            for feature in counts.keys():
                doc_freq[feature] += 1

        kept = [
            feature for feature, freq in doc_freq.items() if freq >= min_df
        ]
        kept.sort(key=lambda feature: (-doc_freq[feature], feature))
        if max_features > 0:
            kept = kept[:max_features]

        if not kept:
            raise ValueError("No features retained for retrieval router")

        vocabulary = {feature: idx for idx, feature in enumerate(kept)}
        num_docs = len(train_samples)
        idf = np.zeros(len(vocabulary), dtype=np.float32)
        for feature, idx in vocabulary.items():
            freq = doc_freq[feature]
            idf[idx] = math.log((1.0 + num_docs) / (1.0 + freq)) + 1.0

        train_matrix = np.vstack(
            [
                cls._vectorize_counts(counts, vocabulary, idf)
                for counts in doc_features
            ]
        ).astype(np.float32, copy=False)

        return cls(
            vocabulary=vocabulary,
            idf=idf,
            train_matrix=train_matrix,
            train_labels=[sample.positive_servers[0] for sample in train_samples],
            train_task_ids=[sample.task_id for sample in train_samples],
            char_ngram_range=char_ngram_range,
            use_word_bigrams=use_word_bigrams,
            top_neighbors=top_neighbors,
        )

    @staticmethod
    def _vectorize_counts(
        counts: Counter[str],
        vocabulary: dict[str, int],
        idf: np.ndarray,
    ) -> np.ndarray:
        """Vectorize one sparse feature counter into normalized TF-IDF."""
        vector = np.zeros(len(vocabulary), dtype=np.float32)
        if not counts:
            return vector

        total = float(sum(counts.values()))
        for feature, count in counts.items():
            idx = vocabulary.get(feature)
            if idx is None:
                continue
            vector[idx] = (float(count) / total) * idf[idx]

        norm = float(np.linalg.norm(vector))
        if norm > 0.0:
            vector /= norm
        return vector

    def encode(self, text: str) -> np.ndarray:
        """Encode one query text into TF-IDF space."""
        counts = extract_features(
            text,
            char_ngram_range=self.char_ngram_range,
            use_word_bigrams=self.use_word_bigrams,
        )
        return self._vectorize_counts(counts, self.vocabulary, self.idf)

    def score(self, text: str) -> list[tuple[str, float]]:
        """Score all servers by nearest-neighbor retrieval and aggregation."""
        query = self.encode(text)
        if not float(np.linalg.norm(query)):
            return []

        similarities = self.train_matrix @ query
        if similarities.size == 0:
            return []

        neighbor_count = min(self.top_neighbors, similarities.shape[0])
        top_indices = np.argpartition(similarities, -neighbor_count)[-neighbor_count:]
        top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]

        server_scores: dict[str, float] = defaultdict(float)
        for idx in top_indices:
            similarity = float(similarities[idx])
            if similarity <= 0.0:
                continue
            server = self.train_labels[int(idx)]
            if similarity > server_scores[server]:
                server_scores[server] = similarity

        scored = sorted(server_scores.items(), key=lambda item: item[1], reverse=True)
        return scored

    def save(self, artifact_prefix: Path) -> None:
        """Persist model arrays and metadata."""
        np.savez_compressed(
            artifact_prefix.with_suffix(".npz"),
            idf=self.idf,
            train_matrix=self.train_matrix,
            train_labels=np.array(self.train_labels, dtype=object),
            train_task_ids=np.array(self.train_task_ids, dtype=object),
        )
        payload = {
            "vocabulary": self.vocabulary,
            "char_ngram_range": list(self.char_ngram_range),
            "use_word_bigrams": self.use_word_bigrams,
            "top_neighbors": self.top_neighbors,
        }
        artifact_prefix.with_suffix(".json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, artifact_prefix: Path) -> "RetrievalSemanticRouter":
        """Load a persisted retrieval router."""
        payload = json.loads(
            artifact_prefix.with_suffix(".json").read_text(encoding="utf-8")
        )
        matrix_payload = np.load(artifact_prefix.with_suffix(".npz"), allow_pickle=True)
        return cls(
            vocabulary={str(k): int(v) for k, v in payload["vocabulary"].items()},
            idf=matrix_payload["idf"],
            train_matrix=matrix_payload["train_matrix"],
            train_labels=[str(item) for item in matrix_payload["train_labels"].tolist()],
            train_task_ids=[str(item) for item in matrix_payload["train_task_ids"].tolist()],
            char_ngram_range=(
                int(payload["char_ngram_range"][0]),
                int(payload["char_ngram_range"][1]),
            ),
            use_word_bigrams=bool(payload["use_word_bigrams"]),
            top_neighbors=int(payload["top_neighbors"]),
        )


def predict_topk_with_threshold(
    model: RetrievalSemanticRouter,
    text: str,
    threshold: float,
    top_k: int,
    ensure_non_empty: bool,
) -> list[tuple[str, float]]:
    """Return threshold-filtered Top-K server predictions."""
    scored = model.score(text)
    selected = [(server, score) for server, score in scored if score >= threshold][:top_k]
    if not selected and ensure_non_empty and scored:
        selected = scored[:1]
    return selected


def evaluate(
    model: RetrievalSemanticRouter,
    samples: list[Sample],
    threshold: float,
    top_k: int,
    ensure_non_empty: bool,
) -> dict[str, float | int]:
    """Evaluate single-skill routing metrics."""
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
