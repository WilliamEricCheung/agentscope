# -*- coding: utf-8 -*-
"""Shared data utilities for single-skill router experiments."""

from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class Sample:
    """One training/evaluation sample."""

    task_id: str
    text: str
    positive_servers: list[str]
    distraction_servers: list[str]
    source_dataset: str


@dataclass
class SplitAudit:
    """Summary of one train/eval split operation."""

    split_method: str
    dedupe_method: str
    similarity_threshold: float
    original_samples: int
    deduped_samples: int
    duplicates_removed: int
    grouped_cluster_count: int
    grouped_multi_sample_clusters: int
    skipped_eval_servers: list[str]
    train_samples: int
    eval_samples: int

    def to_dict(self) -> dict[str, Any]:
        """Convert the audit payload into a JSON-friendly dictionary."""
        return asdict(self)


def normalize_text(text: str) -> str:
    """Normalize text for router input."""
    return re.sub(r"\s+", " ", text).strip()


def _tokenize_for_similarity(text: str) -> set[str]:
    """Tokenize text for coarse lexical similarity grouping."""
    return set(re.findall(r"[a-z0-9]+", normalize_text(text).lower()))


def _jaccard_similarity(left: set[str], right: set[str]) -> float:
    """Compute Jaccard similarity between two token sets."""
    if not left or not right:
        return 0.0
    return float(len(left & right)) / float(len(left | right))


def _dedupe_samples(
    samples: list[Sample],
    dedupe_method: str,
) -> tuple[list[Sample], int]:
    """Deduplicate samples before splitting."""
    if dedupe_method == "none":
        return list(samples), 0
    if dedupe_method != "exact_text_per_server":
        raise ValueError(f"Unsupported dedupe_method: {dedupe_method}")

    deduped: list[Sample] = []
    seen: set[tuple[str, str]] = set()
    removed = 0
    for sample in samples:
        key = (sample.positive_servers[0], normalize_text(sample.text).lower())
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        deduped.append(sample)
    return deduped, removed


def _cluster_by_server_similarity(
    samples: list[Sample],
    similarity_threshold: float,
) -> list[list[Sample]]:
    """Cluster one server's samples by lexical similarity."""
    if not samples:
        return []

    ordered = sorted(samples, key=lambda sample: sample.task_id)
    token_sets = [_tokenize_for_similarity(sample.text) for sample in ordered]
    visited = [False] * len(ordered)
    clusters: list[list[Sample]] = []

    for start_index in range(len(ordered)):
        if visited[start_index]:
            continue
        stack = [start_index]
        visited[start_index] = True
        component_indices: list[int] = []

        while stack:
            current = stack.pop()
            component_indices.append(current)
            for neighbor in range(len(ordered)):
                if visited[neighbor]:
                    continue
                if _jaccard_similarity(token_sets[current], token_sets[neighbor]) < similarity_threshold:
                    continue
                visited[neighbor] = True
                stack.append(neighbor)

        clusters.append([ordered[index] for index in sorted(component_indices)])

    clusters.sort(
        key=lambda cluster: (
            cluster[0].task_id,
            len(cluster),
            normalize_text(cluster[0].text).lower(),
        ),
    )
    return clusters


def split_samples_with_audit(
    samples: list[Sample],
    train_ratio: float,
    eval_seed: int,
    split_method: str = "grouped_by_server_similarity",
    dedupe_method: str = "exact_text_per_server",
    similarity_threshold: float = 0.8,
) -> tuple[list[Sample], list[Sample], SplitAudit]:
    """Split samples into train/eval subsets with optional dedupe and grouping."""
    if not 0.1 <= train_ratio <= 0.95:
        raise ValueError("train_ratio must be between 0.1 and 0.95")

    deduped_samples, duplicates_removed = _dedupe_samples(
        samples=samples,
        dedupe_method=dedupe_method,
    )

    grouped: dict[str, list[Sample]] = defaultdict(list)
    for sample in deduped_samples:
        grouped[sample.positive_servers[0]].append(sample)

    train: list[Sample] = []
    eval_set: list[Sample] = []
    eval_ratio = 1.0 - train_ratio
    grouped_cluster_count = 0
    grouped_multi_sample_clusters = 0
    skipped_eval_servers: list[str] = []

    for server_name in sorted(grouped):
        server_samples = list(grouped[server_name])
        if split_method == "stratified_by_server":
            random.Random(f"{eval_seed}:{server_name}").shuffle(server_samples)

            if len(server_samples) == 1:
                train.extend(server_samples)
                continue

            eval_count = max(1, int(round(len(server_samples) * eval_ratio)))
            eval_count = min(eval_count, len(server_samples) - 1)
            split_idx = len(server_samples) - eval_count
            train.extend(server_samples[:split_idx])
            eval_set.extend(server_samples[split_idx:])
            continue

        if split_method != "grouped_by_server_similarity":
            raise ValueError(f"Unsupported split_method: {split_method}")

        clusters = _cluster_by_server_similarity(
            samples=server_samples,
            similarity_threshold=similarity_threshold,
        )
        grouped_cluster_count += len(clusters)
        grouped_multi_sample_clusters += sum(1 for cluster in clusters if len(cluster) > 1)

        if len(server_samples) == 1 or len(clusters) <= 1:
            train.extend(server_samples)
            if len(server_samples) > 1:
                skipped_eval_servers.append(server_name)
            continue

        eval_target = max(1, int(round(len(server_samples) * eval_ratio)))
        eval_target = min(eval_target, len(server_samples) - 1)
        shuffled_clusters = list(clusters)
        random.Random(f"{eval_seed}:{server_name}:cluster").shuffle(shuffled_clusters)

        eval_count = 0
        for index, cluster in enumerate(shuffled_clusters):
            remaining_samples = sum(len(item) for item in shuffled_clusters[index + 1 :])
            should_assign_eval = eval_count < eval_target and remaining_samples >= 1
            if should_assign_eval:
                eval_set.extend(cluster)
                eval_count += len(cluster)
                continue
            train.extend(cluster)

        if eval_count == 0:
            skipped_eval_servers.append(server_name)

    if not train or not eval_set:
        raise ValueError("Split produced empty train or eval subset; adjust train_ratio or split settings")

    audit = SplitAudit(
        split_method=split_method,
        dedupe_method=dedupe_method,
        similarity_threshold=similarity_threshold,
        original_samples=len(samples),
        deduped_samples=len(deduped_samples),
        duplicates_removed=duplicates_removed,
        grouped_cluster_count=grouped_cluster_count,
        grouped_multi_sample_clusters=grouped_multi_sample_clusters,
        skipped_eval_servers=skipped_eval_servers,
        train_samples=len(train),
        eval_samples=len(eval_set),
    )
    return train, eval_set, audit


def extract_text(task: dict[str, Any], text_mode: str) -> str:
    """Extract one text field from a task record."""
    fuzzy = str(task.get("fuzzy_description") or "").strip()
    exact = str(task.get("task_description") or "").strip()

    if text_mode == "fuzzy":
        return fuzzy or exact
    if text_mode == "task":
        return exact or fuzzy
    if text_mode == "split_both":
        raise ValueError("split_both must be expanded via load_samples")

    return "\n".join(part for part in [fuzzy, exact] if part)


def _expand_task_texts(task: dict[str, Any], text_mode: str) -> list[tuple[str, str]]:
    """Expand one task record into one or more training texts."""
    fuzzy = normalize_text(str(task.get("fuzzy_description") or "").strip())
    exact = normalize_text(str(task.get("task_description") or "").strip())

    if text_mode == "split_both":
        expanded: list[tuple[str, str]] = []
        if fuzzy:
            expanded.append(("fuzzy", fuzzy))
        if exact:
            expanded.append(("task", exact))
        return expanded

    text = normalize_text(extract_text(task, text_mode))
    return [(text_mode, text)] if text else []


def load_samples(dataset_path: Path, text_mode: str) -> list[Sample]:
    """Load single-skill samples from one runner-format json file."""
    with dataset_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    samples: list[Sample] = []
    for block in data.get("server_tasks", []):
        block_servers = [str(s) for s in block.get("servers", []) if str(s).strip()]
        if len(block_servers) != 1:
            raise ValueError(
                "Single-skill training requires exactly one server per block: "
                f"{dataset_path.name} -> {block.get('server_name', '<unknown>')} "
                f"has {len(block_servers)} servers"
            )

        for task in block.get("tasks", []):
            base_task_id = str(task.get("task_id") or f"sample_{len(samples)}")
            distraction_servers = [
                str(s)
                for s in task.get("distraction_servers", [])
                if str(s).strip()
            ]
            for variant_name, text in _expand_task_texts(task, text_mode):
                if not text:
                    continue
                task_id = base_task_id
                if text_mode == "split_both":
                    task_id = f"{base_task_id}__{variant_name}"
                samples.append(
                    Sample(
                        task_id=task_id,
                        text=text,
                        positive_servers=block_servers,
                        distraction_servers=distraction_servers,
                        source_dataset=dataset_path.name,
                    ),
                )

    if not samples:
        raise ValueError(f"No valid samples found in dataset: {dataset_path}")

    return samples


def load_samples_from_datasets(
    dataset_paths: list[Path],
    text_mode: str,
) -> list[Sample]:
    """Load and concatenate samples from multiple datasets."""
    merged: list[Sample] = []
    for dataset_path in dataset_paths:
        merged.extend(load_samples(dataset_path=dataset_path, text_mode=text_mode))

    if not merged:
        raise ValueError("No valid samples found across all datasets")

    return merged


def parse_dataset_paths(dataset: Path, datasets: str | None) -> list[Path]:
    """Resolve dataset inputs from either --dataset or --datasets."""
    if datasets:
        paths = [Path(p.strip()) for p in datasets.split(",") if p.strip()]
        if not paths:
            raise ValueError("--datasets was provided but no valid paths found")
        return paths
    return [dataset]


def split_samples(
    samples: list[Sample],
    train_ratio: float,
    eval_seed: int,
) -> tuple[list[Sample], list[Sample]]:
    """Split samples into train/eval subsets.

    The split is stratified by server label so that adding unrelated server
    classes does not reshuffle the held-out subset for existing classes.
    """
    train_samples, eval_samples, _ = split_samples_with_audit(
        samples=samples,
        train_ratio=train_ratio,
        eval_seed=eval_seed,
        split_method="stratified_by_server",
        dedupe_method="none",
        similarity_threshold=0.0,
    )
    return train_samples, eval_samples


def save_eval_samples(eval_samples: list[Sample], output_path: Path) -> None:
    """Save eval subset for reusable threshold grid search."""
    with output_path.open("w", encoding="utf-8") as f:
        for sample in eval_samples:
            row = {
                "task_id": sample.task_id,
                "text": sample.text,
                "positive_servers": sample.positive_servers,
                "distraction_servers": sample.distraction_servers,
                "source_dataset": sample.source_dataset,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
