# -*- coding: utf-8 -*-
"""Shared data utilities for single-skill router experiments."""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
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


def normalize_text(text: str) -> str:
    """Normalize text for router input."""
    return re.sub(r"\s+", " ", text).strip()


def extract_text(task: dict[str, Any], text_mode: str) -> str:
    """Extract one text field from a task record."""
    fuzzy = str(task.get("fuzzy_description") or "").strip()
    exact = str(task.get("task_description") or "").strip()

    if text_mode == "fuzzy":
        return fuzzy or exact
    if text_mode == "task":
        return exact or fuzzy

    return "\n".join(part for part in [fuzzy, exact] if part)


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
            text = normalize_text(extract_text(task, text_mode))
            if not text:
                continue
            samples.append(
                Sample(
                    task_id=str(task.get("task_id") or f"sample_{len(samples)}"),
                    text=text,
                    positive_servers=block_servers,
                    distraction_servers=[
                        str(s)
                        for s in task.get("distraction_servers", [])
                        if str(s).strip()
                    ],
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
    seed: int,
) -> tuple[list[Sample], list[Sample]]:
    """Split samples into train/eval subsets."""
    if not 0.1 <= train_ratio <= 0.95:
        raise ValueError("train_ratio must be between 0.1 and 0.95")

    rng = random.Random(seed)
    shuffled = list(samples)
    rng.shuffle(shuffled)
    split_idx = int(len(shuffled) * train_ratio)

    train = shuffled[:split_idx]
    eval_set = shuffled[split_idx:]
    if not train or not eval_set:
        raise ValueError("Split produced empty train or eval subset; adjust train_ratio")

    return train, eval_set


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
