"""Rebuild and evaluate SDG Markov transition matrices from retained traces."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .sdg_trace_synthesis import (
    build_server_transition_counts,
    build_server_transition_matrix,
    build_state_transition_counts,
    build_state_transition_matrix,
)


_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_TRACES = _REPOSITORY_ROOT / "laplace/mcp_dataset/laplace_sdg_traces.json"
_DEFAULT_MATRIX = (
    _REPOSITORY_ROOT
    / "laplace/mcp_dataset/laplace_sdg_transition_matrices_retrained.json"
)
_DEFAULT_EVALUATION = (
    _REPOSITORY_ROOT
    / "laplace/mcp_dataset/laplace_sdg_markov_retraining_evaluation.json"
)
_DEFAULT_MANIFEST = (
    _REPOSITORY_ROOT / "src/agentscope/mcp/server_config/laplace_mcp_manifest.json"
)


def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object from disk.

    Args:
        path (`Path`):
            Input JSON file.

    Returns:
        `dict[str, Any]`:
            Parsed JSON object.

    Raises:
        `ValueError`:
            If the input JSON root is not an object.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}.")
    return payload


def _sequence(trace: dict[str, Any]) -> tuple[str, ...]:
    """Extract the ordered server sequence from one trace.

    Args:
        trace (`dict[str, Any]`):
            SDG trace record.

    Returns:
        `tuple[str, ...]`:
            Clean server sequence.
    """
    summary = trace.get("sdg_summary", {})
    if not isinstance(summary, dict):
        return ()
    return tuple(
        str(item).strip()
        for item in summary.get("server_path", [])
        if str(item).strip()
    )


def _is_test_sequence(sequence: tuple[str, ...]) -> bool:
    """Place an entire unique trace sequence in the deterministic test split.

    Args:
        sequence (`tuple[str, ...]`):
            Server sequence used as a group key.

    Returns:
        `bool`:
            Whether this sequence belongs to the 20% held-out split.
    """
    sequence_key = "\x1f".join(sequence).encode("utf-8")
    bucket = int(hashlib.sha256(sequence_key).hexdigest()[:8], 16) % 5
    return bucket == 0


def _fit_counts(
    sequences: list[tuple[str, ...]],
) -> dict[str, dict[str, int]]:
    """Count adjacent transitions for a sequence collection.

    Args:
        sequences (`list[tuple[str, ...]]`):
            Server paths used for fitting.

    Returns:
        `dict[str, dict[str, int]]`:
            Nested transition count table.
    """
    counts: dict[str, dict[str, int]] = {}
    for sequence in sequences:
        for source, target in zip(sequence, sequence[1:]):
            bucket = counts.setdefault(source, {})
            bucket[target] = bucket.get(target, 0) + 1
    return counts


def _ranked_candidates(
    counts: dict[str, dict[str, int]],
    source: str,
    top_k: int,
    exclude_self: bool,
) -> list[str]:
    """Rank candidates by fitted transition probability.

    Args:
        counts (`dict[str, dict[str, int]]`):
            Fitted transition counts.
        source (`str`):
            Source server.
        top_k (`int`):
            Maximum candidate count.
        exclude_self (`bool`):
            Whether to remove the active source server.

    Returns:
        `list[str]`:
            Ranked candidate servers.
    """
    bucket = counts.get(source, {})
    ranked = sorted(bucket, key=lambda target: (-bucket[target], target))
    if exclude_self:
        ranked = [target for target in ranked if target != source]
    return ranked[:top_k]


def _evaluate_holdout(
    train_sequences: list[tuple[str, ...]],
    test_sequences: list[tuple[str, ...]],
) -> dict[str, Any]:
    """Measure next-server prediction on held-out whole trace paths.

    Args:
        train_sequences (`list[tuple[str, ...]]`):
            Unique trace paths used to estimate transition probabilities.
        test_sequences (`list[tuple[str, ...]]`):
            Unique, disjoint trace paths used for evaluation.

    Returns:
        `dict[str, Any]`:
            Top-k prediction results under both self-transition policies.
    """
    counts = _fit_counts(train_sequences)
    policies: dict[str, Any] = {}
    for exclude_self in (False, True):
        policy_name = "self_transitions_excluded" if exclude_self else "self_transitions_included"
        policies[policy_name] = {}
        for top_k in (1, 2, 3, 5):
            results: dict[str, Any] = {}
            for transition_type, include_self_target in (
                ("all_transitions", True),
                ("cross_server_transitions", False),
            ):
                hits = 0
                emitted = 0
                predictable = 0
                denominator = 0
                for sequence in test_sequences:
                    for source, target in zip(sequence, sequence[1:]):
                        if not include_self_target and source == target:
                            continue
                        candidates = _ranked_candidates(
                            counts,
                            source,
                            top_k=top_k,
                            exclude_self=exclude_self,
                        )
                        denominator += 1
                        hits += int(target in candidates)
                        emitted += len(candidates)
                        predictable += int(bool(candidates))
                results[transition_type] = {
                    "correct_transitions": hits,
                    "test_transitions": denominator,
                    "recall_at_k": hits / denominator if denominator else None,
                    "mean_candidates_per_transition": (
                        emitted / denominator if denominator else None
                    ),
                    "predictable_transition_fraction": (
                        predictable / denominator if denominator else None
                    ),
                }
            policies[policy_name][f"top_{top_k}"] = results
    return policies


def _runtime_coverage(
    counts: dict[str, dict[str, int]],
    manifest_path: Path,
) -> dict[str, Any]:
    """Measure how much of the training target mass is runnable by default.

    Args:
        counts (`dict[str, dict[str, int]]`):
            Full-data server transition counts.
        manifest_path (`Path`):
            Runtime MCP manifest.

    Returns:
        `dict[str, Any]`:
            Default allowlist coverage statistics.
    """
    manifest = _load_json(manifest_path)
    servers = manifest.get("servers", {})
    if not isinstance(servers, dict):
        raise ValueError(f"Expected a servers mapping in {manifest_path}.")
    default_server_labels = {
        str(name)
        for name, entry in servers.items()
        if isinstance(entry, dict)
        and entry.get("group_name") in {"browser_tools", "github_tools"}
    }
    total = sum(sum(targets.values()) for targets in counts.values())
    available = sum(
        count
        for targets in counts.values()
        for target, count in targets.items()
        if target in default_server_labels
    )
    return {
        "default_runtime_server_labels": sorted(default_server_labels),
        "transition_count_total": total,
        "transitions_to_default_available_servers": available,
        "transition_target_coverage": available / total if total else None,
        "note": (
            "The experiment helper further removes github_tools when no GitHub "
            "token is configured."
        ),
    }


def rebuild_and_evaluate(
    traces_path: Path,
    matrix_path: Path,
    evaluation_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    """Rebuild the Markov matrices and evaluate generalization from traces.

    Args:
        traces_path (`Path`):
            Retained SDG trace JSON.
        matrix_path (`Path`):
            Destination for rebuilt transition matrices.
        evaluation_path (`Path`):
            Destination for evaluation metrics.
        manifest_path (`Path`):
            MCP runtime manifest for candidate-availability checks.

    Returns:
        `dict[str, Any]`:
            Evaluation report payload.
    """
    trace_payload = _load_json(traces_path)
    traces = trace_payload.get("traces", [])
    if not isinstance(traces, list) or not traces:
        raise ValueError(f"No trace records found in {traces_path}.")

    unique_sequences = sorted(
        {_sequence(trace) for trace in traces if isinstance(trace, dict)},
    )
    unique_sequences = [sequence for sequence in unique_sequences if sequence]
    test_sequences = [
        sequence for sequence in unique_sequences if _is_test_sequence(sequence)
    ]
    train_sequences = [
        sequence for sequence in unique_sequences if not _is_test_sequence(sequence)
    ]
    if not train_sequences or not test_sequences:
        raise ValueError(
            "The grouped 80/20 split must contain both train and test sequences.",
        )

    server_counts = build_server_transition_counts(traces)
    server_matrix = build_server_transition_matrix(traces)
    state_counts = build_state_transition_counts(traces)
    state_matrix = build_state_transition_matrix(traces)
    matrix_payload = {
        "trace_schema_version": trace_payload.get("schema_version"),
        "trace_count": len(traces),
        "training_source": str(traces_path.resolve()),
        "server_transition_counts": server_counts,
        "server_transition_matrix": server_matrix,
        "state_transition_counts": state_counts,
        "state_transition_matrix": state_matrix,
    }
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    matrix_path.write_text(
        json.dumps(matrix_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    old_matrix_path = traces_path.with_name("laplace_sdg_transition_matrices.json")
    existing_matrix = _load_json(old_matrix_path) if old_matrix_path.exists() else {}
    count_match = existing_matrix.get("server_transition_counts") == server_counts
    probability_match = (
        existing_matrix.get("server_transition_matrix") == server_matrix
    )
    all_transitions = sum(sum(targets.values()) for targets in server_counts.values())
    self_transitions = sum(
        targets.get(source, 0) for source, targets in server_counts.items()
    )
    report = {
        "status": "complete",
        "method": "First-order maximum-likelihood Markov estimation from adjacent server labels in SDG traces.",
        "input": {
            "traces_path": str(traces_path.resolve()),
            "trace_count": len(traces),
            "unique_server_paths": len(unique_sequences),
            "trace_sha256": hashlib.sha256(traces_path.read_bytes()).hexdigest(),
        },
        "outputs": {
            "rebuilt_matrix": str(matrix_path.resolve()),
        },
        "existing_matrix_match": {
            "server_transition_counts_identical": count_match,
            "server_transition_probabilities_identical": probability_match,
            "interpretation": (
                "Retraining reproduces the checked-in matrix exactly."
                if count_match and probability_match
                else "Retraining differs from the checked-in matrix."
            ),
        },
        "dataset_diagnostics": {
            "server_transition_count": all_transitions,
            "self_transition_count": self_transitions,
            "self_transition_fraction": (
                self_transitions / all_transitions if all_transitions else None
            ),
        },
        "held_out_evaluation": {
            "split": (
                "Unique server paths are grouped before a deterministic 80/20 "
                "split; duplicate paths cannot leak across train and test."
            ),
            "train_unique_paths": len(train_sequences),
            "test_unique_paths": len(test_sequences),
            "test_transitions": sum(
                max(0, len(sequence) - 1) for sequence in test_sequences
            ),
            "policies": _evaluate_holdout(train_sequences, test_sequences),
        },
        "runtime_candidate_coverage": _runtime_coverage(
            server_counts,
            manifest_path,
        ),
    }
    evaluation_path.parent.mkdir(parents=True, exist_ok=True)
    evaluation_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    """Run the trace-based matrix rebuild and holdout evaluation."""
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild Context2SDG Markov matrices from retained traces and "
            "evaluate top-k prediction on grouped held-out paths."
        ),
    )
    parser.add_argument("--traces", type=Path, default=_DEFAULT_TRACES)
    parser.add_argument("--output-matrix", type=Path, default=_DEFAULT_MATRIX)
    parser.add_argument("--evaluation-output", type=Path, default=_DEFAULT_EVALUATION)
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    args = parser.parse_args()

    report = rebuild_and_evaluate(
        traces_path=args.traces,
        matrix_path=args.output_matrix,
        evaluation_path=args.evaluation_output,
        manifest_path=args.manifest,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
