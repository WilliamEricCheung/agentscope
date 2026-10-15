"""Build a reproducible suite of short, trace-derived SDG transitions."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from typing import Any


_DEFAULT_TRACE_FILE = (
    Path(__file__).resolve().parents[4]
    / "laplace"
    / "mcp_dataset"
    / "laplace_sdg_traces.json"
)
_DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "sdg_short_transitions_20"


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
    """Create a two-tool replay prompt from adjacent trace steps.

    Args:
        trace (`dict[str, Any]`):
            Source trace record.
        source_step (`dict[str, Any]`):
            Earlier step in the cross-server transition.
        target_step (`dict[str, Any]`):
            Later step in the cross-server transition.

    Returns:
        `str`:
            Explicit two-tool replay request.
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


def _build_suite(trace_file: Path, output_dir: Path, case_count: int) -> Path:
    """Write deterministic scripts for the most frequent cross-server edges.

    Args:
        trace_file (`Path`):
            JSON file containing the generated SDG traces.
        output_dir (`Path`):
            Directory for the scripts and suite manifest.
        case_count (`int`):
            Number of distinct cross-server transitions to include.

    Returns:
        `Path`:
            Written suite manifest path.
    """
    payload = json.loads(trace_file.read_text(encoding="utf-8"))
    traces = payload["traces"]
    transition_counts: Counter[tuple[str, str]] = Counter()
    representatives: dict[
        tuple[str, str],
        tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
    ] = {}

    for trace in traces:
        steps = trace["execution_trace"]
        for source_step, target_step in zip(steps, steps[1:]):
            edge = (source_step["server_name"], target_step["server_name"])
            if edge[0] == edge[1]:
                continue
            transition_counts[edge] += 1
            representatives.setdefault(edge, (trace, source_step, target_step))

    selected = sorted(
        transition_counts,
        key=lambda edge: (-transition_counts[edge], edge[0], edge[1]),
    )[:case_count]
    if len(selected) != case_count:
        raise ValueError(
            f"Requested {case_count} transitions, found only {len(selected)}.",
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    cases = []
    for index, edge in enumerate(selected, start=1):
        trace, source_step, target_step = representatives[edge]
        trace_id = f"transition_{index:02d}_{trace['trace_id']}"
        script_path = output_dir / f"{trace_id}.json"
        script_path.write_text(
            json.dumps([_prompt(trace, source_step, target_step)], indent=2)
            + "\n",
            encoding="utf-8",
        )
        cases.append(
            {
                "case_index": index,
                "trace_id": trace_id,
                "source_trace_id": trace["trace_id"],
                "source_step_index": source_step["step_index"],
                "target_step_index": target_step["step_index"],
                "server_path": list(edge),
                "tool_path": [
                    source_step["tool_name"],
                    target_step["tool_name"],
                ],
                "source_edge_frequency": transition_counts[edge],
                "turn_script": script_path.name,
            },
        )

    manifest = {
        "suite_name": f"SDG {case_count} frequent cross-server transitions",
        "source_trace_file": str(trace_file.resolve()),
        "selection": (
            "One representative from each of the most frequent distinct "
            "directed cross-server edges in the trace file; self-transitions "
            "excluded; ties broken lexicographically. Each script replays "
            "the two adjacent source trace steps only."
        ),
        "case_count": case_count,
        "transition_population": sum(transition_counts.values()),
        "unique_cross_server_edges": len(transition_counts),
        "cases": cases,
    }
    manifest_path = output_dir / "sdg_short_transition_suite_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def _main() -> None:
    """Parse options and build the replay suite."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-file", type=Path, default=_DEFAULT_TRACE_FILE)
    parser.add_argument("--output-dir", type=Path, default=_DEFAULT_OUTPUT_DIR)
    parser.add_argument("--cases", type=int, default=20)
    args = parser.parse_args()
    if args.cases < 1:
        raise ValueError("--cases must be positive.")
    print(_build_suite(args.trace_file, args.output_dir, args.cases))


if __name__ == "__main__":
    _main()
