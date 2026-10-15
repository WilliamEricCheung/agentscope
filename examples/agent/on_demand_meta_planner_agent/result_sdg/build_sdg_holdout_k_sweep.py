"""Build a grouped held-out SDG transition suite and training-only matrix."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any


_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_TRACE_FILE = (
    _REPOSITORY_ROOT / "laplace" / "mcp_dataset" / "laplace_sdg_traces.json"
)
_DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "sdg_holdout_k_sweep_20261010"


def _is_test_sequence(sequence: tuple[str, ...]) -> bool:
    """Match the grouped holdout split used by the Markov evaluation.

    Args:
        sequence (`tuple[str, ...]`):
            Ordered server labels for a trace path.

    Returns:
        `bool`:
            Whether the entire path is assigned to the held-out split.
    """
    key = "\x1f".join(sequence).encode("utf-8")
    return int(hashlib.sha256(key).hexdigest()[:8], 16) % 5 == 0


def _group_name(server_name: str) -> str:
    """Map a trace server label to its runtime MCP group name.

    Args:
        server_name (`str`):
            Server label from the SDG trace.

    Returns:
        `str`:
            Runtime MCP group name.
    """
    aliases = {
        "Playwright": "browser_tools",
        "Hugging Face": "laplace_huggingface",
    }
    if server_name in aliases:
        return aliases[server_name]
    slug = re.sub(r"[^a-z0-9]+", "_", server_name.lower()).strip("_")
    return f"laplace_{slug}"


def _prompt(
    trace: dict[str, Any],
    source_step: dict[str, Any],
    target_step: dict[str, Any],
) -> str:
    """Build a two-tool replay prompt for one held-out transition.

    Args:
        trace (`dict[str, Any]`):
            Trace record containing the user request.
        source_step (`dict[str, Any]`):
            First tool step in the selected transition.
        target_step (`dict[str, Any]`):
            Second tool step in the selected transition.

    Returns:
        `str`:
            Prompt that requests the two selected tools in order.
    """
    return (
        f"Complete this request: {trace['user_request']}\n\n"
        "For this controlled trace-replay experiment, make exactly the "
        "following two MCP calls in order. Actually call both tools and use "
        "the first result when carrying out the second step. Do not call any "
        "other tools. If a call returns an error or times out, state that it "
        "was skipped and continue to the next step without retrying or "
        "inventing results. If a listed tool is unavailable, say so explicitly.\n\n"
        "1. Activate MCP group "
        f"\"{_group_name(source_step['server_name'])}\" "
        f"(server: {source_step['server_name']}) and call tool "
        f"\"{source_step['tool_name']}\". Goal: {source_step['intent']}\n"
        "2. Activate MCP group "
        f"\"{_group_name(target_step['server_name'])}\" "
        f"(server: {target_step['server_name']}) and call tool "
        f"\"{target_step['tool_name']}\". Goal: {target_step['intent']}\n\n"
        "Return a concise result based on the tool outputs."
    )


def _build_artifacts(trace_file: Path, output_dir: Path) -> Path:
    """Write replay scripts, a grouped holdout manifest, and train-only matrix.

    Args:
        trace_file (`Path`):
            Source SDG trace collection.
        output_dir (`Path`):
            Destination for replay and matrix artifacts.

    Returns:
        `Path`:
            Path to the generated suite manifest.
    """
    payload = json.loads(trace_file.read_text(encoding="utf-8"))
    traces = payload.get("traces")
    if not isinstance(traces, list) or not traces:
        raise ValueError(f"No trace records found in {trace_file}.")

    train_paths: dict[tuple[str, ...], dict[str, Any]] = {}
    test_paths: dict[tuple[str, ...], dict[str, Any]] = {}
    for trace in traces:
        summary = trace.get("sdg_summary", {})
        sequence = tuple(
            str(item).strip()
            for item in summary.get("server_path", [])
            if str(item).strip()
        )
        path_group = test_paths if _is_test_sequence(sequence) else train_paths
        path_group.setdefault(sequence, trace)

    if not train_paths or not test_paths:
        raise ValueError("Grouped split must contain both training and test traces.")

    transition_counts: Counter[tuple[str, str]] = Counter()
    representatives: dict[
        tuple[str, str],
        tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
    ] = {}
    for trace in test_paths.values():
        steps = trace.get("execution_trace", [])
        for source_step, target_step in zip(steps, steps[1:]):
            edge = (
                str(source_step.get("server_name", "")),
                str(target_step.get("server_name", "")),
            )
            if not edge[0] or not edge[1] or edge[0] == edge[1]:
                continue
            transition_counts[edge] += 1
            representatives.setdefault(
                edge,
                (trace, source_step, target_step),
            )
    if not representatives:
        raise ValueError("The held-out traces contain no cross-server transitions.")

    train_counts: dict[str, dict[str, int]] = {}
    for path in train_paths:
        for source, target in zip(path, path[1:]):
            bucket = train_counts.setdefault(str(source), {})
            bucket[str(target)] = bucket.get(str(target), 0) + 1
    train_matrix = {
        source: {
            target: count / sum(targets.values())
            for target, count in targets.items()
        }
        for source, targets in train_counts.items()
        if sum(targets.values()) > 0
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = output_dir / "training_transition_matrix.json"
    matrix_path.write_text(
        json.dumps(
            {
                "trace_schema_version": payload.get("schema_version"),
                "trace_count": len(train_paths),
                "training_source": str(trace_file.resolve()),
                "split": "deterministic grouped 80/20 by unique server path",
                "server_transition_counts": train_counts,
                "server_transition_matrix": train_matrix,
                "state_transition_counts": {},
                "state_transition_matrix": {},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    cases = []
    for index, edge in enumerate(
        sorted(
            representatives,
            key=lambda item: (-transition_counts[item], item[0], item[1]),
        ),
        start=1,
    ):
        trace, source_step, target_step = representatives[edge]
        trace_id = f"holdout_transition_{index:02d}_{trace['trace_id']}"
        script_name = f"{trace_id}.json"
        (output_dir / script_name).write_text(
            json.dumps(
                [_prompt(trace, source_step, target_step)],
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        cases.append(
            {
                "case_index": index,
                "trace_id": trace_id,
                "source_trace_id": trace["trace_id"],
                "server_path": list(edge),
                "group_path": [
                    _group_name(edge[0]),
                    _group_name(edge[1]),
                ],
                "tool_path": [
                    source_step["tool_name"],
                    target_step["tool_name"],
                ],
                "heldout_edge_frequency": transition_counts[edge],
                "turn_script": script_name,
            },
        )

    manifest_path = output_dir / "sdg_holdout_transition_suite_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "suite_name": "Grouped held-out SDG cross-server transitions",
                "source_trace_file": str(trace_file.resolve()),
                "train_trace_count": sum(
                    not _is_test_sequence(
                        tuple(
                            str(item).strip()
                            for item in trace.get("sdg_summary", {}).get(
                                "server_path",
                                [],
                            )
                            if str(item).strip()
                        ),
                    )
                    for trace in traces
                ),
                "test_trace_count": sum(
                    _is_test_sequence(
                        tuple(
                            str(item).strip()
                            for item in trace.get("sdg_summary", {}).get(
                                "server_path",
                                [],
                            )
                            if str(item).strip()
                        ),
                    )
                    for trace in traces
                ),
                "train_unique_paths": len(train_paths),
                "test_unique_paths": len(test_paths),
                "unique_heldout_edges": len(cases),
                "heldout_cross_server_transition_count": sum(
                    transition_counts.values()
                ),
                "training_matrix": str(matrix_path.resolve()),
                "selection": (
                    "One representative from each distinct cross-server edge "
                    "in grouped held-out traces; self-transitions excluded."
                ),
                "cases": cases,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest_path


def main() -> None:
    """Build held-out transition evaluation inputs from command-line options.

    Returns:
        `None`:
            Artifacts are written to the selected output directory.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-file", type=Path, default=_DEFAULT_TRACE_FILE)
    parser.add_argument("--output-dir", type=Path, default=_DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    print(_build_artifacts(args.trace_file, args.output_dir))


if __name__ == "__main__":
    main()
