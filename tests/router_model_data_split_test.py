"""Tests for router-model stratified dataset splitting."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import TestCase


ROUTER_MODEL_DIR = Path(__file__).resolve().parents[1] / "laplace" / "router_model"
if str(ROUTER_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(ROUTER_MODEL_DIR))

from _router_data import load_samples, Sample, split_samples, split_samples_with_audit  # noqa: E402


class RouterModelDataSplitTest(TestCase):
    """Tests for stratified router train/eval splitting."""

    @staticmethod
    def _make_samples(server_name: str, count: int) -> list[Sample]:
        return [
            Sample(
                task_id=f"{server_name}_{index}",
                text=f"sample text {server_name} {index}",
                positive_servers=[server_name],
                distraction_servers=[],
                source_dataset="laplace_tasks_single_runner_format.json",
            )
            for index in range(count)
        ]

    def test_split_samples_is_stratified_and_keeps_singletons_in_train(self) -> None:
        """Servers with multiple samples should appear in eval, singletons stay in train."""
        samples = []
        samples.extend(self._make_samples("alpha", 1))
        samples.extend(self._make_samples("beta", 2))
        samples.extend(self._make_samples("gamma", 5))

        train_samples, eval_samples = split_samples(
            samples=samples,
            train_ratio=0.8,
            eval_seed=42,
        )

        train_ids = {sample.task_id for sample in train_samples}
        eval_ids = {sample.task_id for sample in eval_samples}
        self.assertIn("alpha_0", train_ids)
        self.assertNotIn("alpha_0", eval_ids)
        self.assertEqual(sum(sample.positive_servers[0] == "beta" for sample in eval_samples), 1)
        self.assertEqual(sum(sample.positive_servers[0] == "gamma" for sample in eval_samples), 1)

    def test_split_samples_keeps_existing_server_eval_membership_stable(self) -> None:
        """Adding another server should not reshuffle held-out samples for existing servers."""
        base_samples = []
        base_samples.extend(self._make_samples("alpha", 4))
        base_samples.extend(self._make_samples("beta", 4))

        _, base_eval = split_samples(
            samples=base_samples,
            train_ratio=0.8,
            eval_seed=42,
        )
        base_eval_ids = {sample.task_id for sample in base_eval}

        expanded_samples = list(base_samples)
        expanded_samples.extend(self._make_samples("gamma", 4))
        _, expanded_eval = split_samples(
            samples=expanded_samples,
            train_ratio=0.8,
            eval_seed=42,
        )
        expanded_eval_ids = {
            sample.task_id
            for sample in expanded_eval
            if sample.positive_servers[0] in {"alpha", "beta"}
        }

        self.assertEqual(base_eval_ids, expanded_eval_ids)

    def test_grouped_split_dedupes_exact_duplicates(self) -> None:
        """Harder split should remove exact duplicates before train/eval partitioning."""
        samples = [
            Sample(
                task_id="alpha_0",
                text="search papers on transformers and attention",
                positive_servers=["alpha"],
                distraction_servers=[],
                source_dataset="laplace_tasks_single_runner_format.json",
            ),
            Sample(
                task_id="alpha_1",
                text="search papers on transformers and attention",
                positive_servers=["alpha"],
                distraction_servers=[],
                source_dataset="laplace_tasks_single_runner_format.json",
            ),
            Sample(
                task_id="alpha_2",
                text="search papers on graph neural networks",
                positive_servers=["alpha"],
                distraction_servers=[],
                source_dataset="laplace_tasks_single_runner_format.json",
            ),
            Sample(
                task_id="beta_0",
                text="look up weather forecasts for shanghai",
                positive_servers=["beta"],
                distraction_servers=[],
                source_dataset="laplace_tasks_single_runner_format.json",
            ),
            Sample(
                task_id="beta_1",
                text="check tomorrow weather forecast for shanghai",
                positive_servers=["beta"],
                distraction_servers=[],
                source_dataset="laplace_tasks_single_runner_format.json",
            ),
        ]

        train_samples, eval_samples, diagnostics = split_samples_with_audit(
            samples=samples,
            train_ratio=0.5,
            eval_seed=42,
            split_method="grouped_by_server_similarity",
            dedupe_method="exact_text_per_server",
            similarity_threshold=0.8,
        )

        all_texts = [sample.text for sample in train_samples + eval_samples]
        self.assertEqual(len(all_texts), len(set(all_texts)))
        self.assertEqual(diagnostics.duplicates_removed, 1)
        self.assertEqual(diagnostics.original_samples, 5)
        self.assertEqual(diagnostics.deduped_samples, 4)

    def test_grouped_split_keeps_lexical_family_together(self) -> None:
        """Harder split should avoid splitting one lexical family across train and eval when possible."""
        samples = [
            Sample(
                task_id="alpha_0",
                text="search papers on transformers and attention",
                positive_servers=["alpha"],
                distraction_servers=[],
                source_dataset="laplace_tasks_single_runner_format.json",
            ),
            Sample(
                task_id="alpha_1",
                text="search papers on transformers attention models",
                positive_servers=["alpha"],
                distraction_servers=[],
                source_dataset="laplace_tasks_single_runner_format.json",
            ),
            Sample(
                task_id="alpha_2",
                text="find benchmark datasets for graph neural networks",
                positive_servers=["alpha"],
                distraction_servers=[],
                source_dataset="laplace_tasks_single_runner_format.json",
            ),
            Sample(
                task_id="alpha_3",
                text="list benchmark datasets for graph neural networks",
                positive_servers=["alpha"],
                distraction_servers=[],
                source_dataset="laplace_tasks_single_runner_format.json",
            ),
            Sample(
                task_id="beta_0",
                text="check the weather for beijing",
                positive_servers=["beta"],
                distraction_servers=[],
                source_dataset="laplace_tasks_single_runner_format.json",
            ),
            Sample(
                task_id="beta_1",
                text="weather forecast for beijing tomorrow",
                positive_servers=["beta"],
                distraction_servers=[],
                source_dataset="laplace_tasks_single_runner_format.json",
            ),
        ]

        train_samples, eval_samples, _ = split_samples_with_audit(
            samples=samples,
            train_ratio=0.5,
            eval_seed=42,
            split_method="grouped_by_server_similarity",
            dedupe_method="none",
            similarity_threshold=0.45,
        )

        train_ids = {sample.task_id for sample in train_samples}
        eval_ids = {sample.task_id for sample in eval_samples}
        self.assertFalse({"alpha_0", "alpha_1"} & train_ids and {"alpha_0", "alpha_1"} & eval_ids)
        self.assertFalse({"alpha_2", "alpha_3"} & train_ids and {"alpha_2", "alpha_3"} & eval_ids)

    def test_load_samples_split_both_expands_each_task_into_two_rows(self) -> None:
        """split_both should emit separate fuzzy and task rows for one dataset task."""
        dataset_path = ROUTER_MODEL_DIR.parent / "mcp_dataset" / "laplace_tasks_single_runner_format.json"

        fuzzy_samples = load_samples(dataset_path=dataset_path, text_mode="fuzzy")
        task_samples = load_samples(dataset_path=dataset_path, text_mode="task")
        split_samples_payload = load_samples(dataset_path=dataset_path, text_mode="split_both")

        self.assertEqual(len(split_samples_payload), len(fuzzy_samples) + len(task_samples))
        sample_ids = {sample.task_id for sample in split_samples_payload}
        self.assertTrue(any(task_id.endswith("__fuzzy") for task_id in sample_ids))
        self.assertTrue(any(task_id.endswith("__task") for task_id in sample_ids))