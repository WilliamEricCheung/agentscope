"""Tests for rebuilding and evaluating SDG Markov transition models."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from laplace.mcp_dataset.synthesis.context2sdg.rebuild_sdg_transition_matrices import (
    _evaluate_holdout,
    _fit_counts,
    _ranked_candidates,
)


def test_fit_counts_uses_adjacent_server_pairs() -> None:
    """Count repeated adjacent transitions from trace sequences."""
    counts = _fit_counts(
        [
            ("A", "A", "B"),
            ("A", "B", "C"),
        ],
    )

    assert counts == {
        "A": {"A": 1, "B": 2},
        "B": {"C": 1},
    }


def test_candidate_ranking_can_skip_current_server() -> None:
    """Exclude a dominant self-transition when selecting prewarm targets."""
    counts = {"A": {"A": 8, "B": 2, "C": 1}}

    assert _ranked_candidates(counts, "A", top_k=1, exclude_self=False) == ["A"]
    assert _ranked_candidates(counts, "A", top_k=1, exclude_self=True) == ["B"]


def test_holdout_reports_cross_server_accuracy_separately() -> None:
    """Evaluate cross-server transitions separately from same-server steps."""
    path = ("A", "A", "B", "C")
    result = _evaluate_holdout(
        train_sequences=[("A", "A", "B"), ("B", "C", "C")],
        test_sequences=[path],
    )

    assert result["self_transitions_included"]["top_1"][
        "all_transitions"
    ]["test_transitions"] == 3
    assert result["self_transitions_excluded"]["top_1"][
        "cross_server_transitions"
    ]["test_transitions"] == 2
    assert result["self_transitions_excluded"]["top_1"][
        "cross_server_transitions"
    ]["correct_transitions"] == 2
