"""CLI for generating SDG-oriented structured execution traces."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .._dashscope_provider import DashScopeCompletionProvider
from .sdg_trace_synthesis import (
    SDGTraceSynthesizer,
    TRACE_SCHEMA_VERSION,
    build_batch_trace_prompt,
    build_standalone_trace_prompt,
    build_server_transition_counts,
    build_server_transition_matrix,
    build_state_transition_counts,
    build_state_transition_matrix,
    load_laplace_server_catalog,
)


_TRACE_INDEX_WIDTH = 5
_CHECKPOINT_SHARD_SIZE = 50


def _build_prompt_shard_filename(
    shard_start_index: int,
    shard_end_index: int,
    requested_trace_count: int,
) -> str:
    """Build an archive-friendly checkpoint prompt shard file name.

    Args:
        shard_start_index (`int`):
            Inclusive shard start index.
        shard_end_index (`int`):
            Inclusive shard end index.
        requested_trace_count (`int`):
            Total requested trace count for the run.

    Returns:
        `str`:
            Prompt shard file name containing shard range and run size.
    """
    return (
        f"sdg_prompt_shard_{shard_start_index:0{_TRACE_INDEX_WIDTH}d}"
        f"_to_{shard_end_index:0{_TRACE_INDEX_WIDTH}d}"
        f"_of_{requested_trace_count:0{_TRACE_INDEX_WIDTH}d}.json"
    )


def _build_trace_shard_filename(
    shard_start_index: int,
    shard_end_index: int,
    requested_trace_count: int,
) -> str:
    """Build an archive-friendly checkpoint trace shard file name.

    Args:
        shard_start_index (`int`):
            Inclusive shard start index.
        shard_end_index (`int`):
            Inclusive shard end index.
        requested_trace_count (`int`):
            Total requested trace count for the run.

    Returns:
        `str`:
            Trace shard file name containing shard range and run size.
    """
    return (
        f"sdg_trace_shard_{shard_start_index:0{_TRACE_INDEX_WIDTH}d}"
        f"_to_{shard_end_index:0{_TRACE_INDEX_WIDTH}d}"
        f"_of_{requested_trace_count:0{_TRACE_INDEX_WIDTH}d}.json"
    )


def _build_trace_id(trace_index: int) -> str:
    """Build the canonical trace id for one generated trace.

    Args:
        trace_index (`int`):
            Zero-based trace index.

    Returns:
        `str`:
            Canonical trace id.
    """
    return f"sdg_trace_{trace_index:0{_TRACE_INDEX_WIDTH}d}"


def _resolve_shard_bounds(
    trace_index: int,
    requested_trace_count: int,
) -> tuple[int, int]:
    """Resolve the inclusive shard range for one trace index.

    Args:
        trace_index (`int`):
            Zero-based trace index.
        requested_trace_count (`int`):
            Total requested trace count for the run.

    Returns:
        `tuple[int, int]`:
            Inclusive shard start/end indices.
    """
    del requested_trace_count
    shard_start = (trace_index // _CHECKPOINT_SHARD_SIZE) * _CHECKPOINT_SHARD_SIZE
    shard_end = shard_start + _CHECKPOINT_SHARD_SIZE - 1
    return shard_start, shard_end


def _utc_timestamp() -> str:
    """Build a compact UTC timestamp for artifact metadata.

    Returns:
        `str`:
            ISO 8601 UTC timestamp.
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_existing_manifest(run_paths: dict[str, Path]) -> dict[str, Any]:
    """Load existing manifest data when resuming a checkpointed run.

    Args:
        run_paths (`dict[str, Path]`):
            Resolved path mapping.

    Returns:
        `dict[str, Any]`:
            Existing manifest payload, or an empty mapping.
    """
    manifest_path = run_paths["manifest"]
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _resolve_prompt_shard_path(
    prompt_dir: Path,
    trace_index: int,
    requested_trace_count: int,
) -> Path:
    """Resolve the prompt shard path for the current archive convention.

    Args:
        prompt_dir (`Path`):
            Checkpoint prompt directory.
        trace_index (`int`):
            Zero-based trace index.
        requested_trace_count (`int`):
            Total requested trace count for the run.

    Returns:
        `Path`:
            Archive-friendly prompt shard path.
    """
    shard_start, shard_end = _resolve_shard_bounds(
        trace_index=trace_index,
        requested_trace_count=requested_trace_count,
    )
    shard_end = min(shard_end, requested_trace_count - 1)
    return prompt_dir / _build_prompt_shard_filename(
        shard_start_index=shard_start,
        shard_end_index=shard_end,
        requested_trace_count=requested_trace_count,
    )


def _resolve_trace_shard_path(
    trace_dir: Path,
    trace_index: int,
    requested_trace_count: int,
) -> Path:
    """Resolve the trace shard path for the current archive convention.

    Args:
        trace_dir (`Path`):
            Checkpoint trace directory.
        trace_index (`int`):
            Zero-based trace index.
        requested_trace_count (`int`):
            Total requested trace count for the run.

    Returns:
        `Path`:
            Archive-friendly trace shard path.
    """
    shard_start, shard_end = _resolve_shard_bounds(
        trace_index=trace_index,
        requested_trace_count=requested_trace_count,
    )
    shard_end = min(shard_end, requested_trace_count - 1)
    return trace_dir / _build_trace_shard_filename(
        shard_start_index=shard_start,
        shard_end_index=shard_end,
        requested_trace_count=requested_trace_count,
    )


def _load_json_payload(payload_path: Path) -> dict[str, Any]:
    """Load one JSON payload file if it exists.

    Args:
        payload_path (`Path`):
            JSON file path.

    Returns:
        `dict[str, Any]`:
            Parsed JSON payload, or an empty payload when absent.
    """
    if not payload_path.exists():
        return {}
    return json.loads(payload_path.read_text(encoding="utf-8"))


def _read_prompt_from_shard(
    prompt_dir: Path,
    trace_index: int,
    requested_trace_count: int,
) -> str | None:
    """Read one prompt from the corresponding prompt shard.

    Args:
        prompt_dir (`Path`):
            Checkpoint prompt directory.
        trace_index (`int`):
            Zero-based trace index.
        requested_trace_count (`int`):
            Total requested trace count for the run.

    Returns:
        `str | None`:
            Stored prompt text when present.
    """
    shard_path = _resolve_prompt_shard_path(
        prompt_dir=prompt_dir,
        trace_index=trace_index,
        requested_trace_count=requested_trace_count,
    )
    shard_payload = _load_json_payload(shard_path)
    for record in shard_payload.get("records", []):
        if int(record.get("trace_index", -1)) == trace_index:
            return str(record.get("prompt", ""))
    return None


def _write_prompt_to_shard(
    prompt_dir: Path,
    trace_index: int,
    requested_trace_count: int,
    prompt: str,
) -> None:
    """Write one prompt into the corresponding prompt shard.

    Args:
        prompt_dir (`Path`):
            Checkpoint prompt directory.
        trace_index (`int`):
            Zero-based trace index.
        requested_trace_count (`int`):
            Total requested trace count for the run.
        prompt (`str`):
            Prompt text to persist.
    """
    shard_path = _resolve_prompt_shard_path(
        prompt_dir=prompt_dir,
        trace_index=trace_index,
        requested_trace_count=requested_trace_count,
    )
    shard_start, shard_end = _resolve_shard_bounds(
        trace_index=trace_index,
        requested_trace_count=requested_trace_count,
    )
    shard_payload = _load_json_payload(shard_path) or {
        "artifact_type": "sdg_prompt_shard",
        "trace_index_start": shard_start,
        "trace_index_end": min(shard_end, requested_trace_count - 1),
        "requested_trace_count": requested_trace_count,
        "records": [],
    }
    records = [
        record
        for record in shard_payload.get("records", [])
        if int(record.get("trace_index", -1)) != trace_index
    ]
    records.append(
        {
            "trace_index": trace_index,
            "trace_id": _build_trace_id(trace_index),
            "prompt": prompt,
        },
    )
    shard_payload["records"] = sorted(records, key=lambda item: int(item["trace_index"]))
    shard_path.write_text(
        json.dumps(shard_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _read_trace_from_shard(
    trace_dir: Path,
    trace_index: int,
    requested_trace_count: int,
) -> dict[str, Any] | None:
    """Read one trace from the corresponding trace shard.

    Args:
        trace_dir (`Path`):
            Checkpoint trace directory.
        trace_index (`int`):
            Zero-based trace index.
        requested_trace_count (`int`):
            Total requested trace count for the run.

    Returns:
        `dict[str, Any] | None`:
            Stored trace when present.
    """
    shard_path = _resolve_trace_shard_path(
        trace_dir=trace_dir,
        trace_index=trace_index,
        requested_trace_count=requested_trace_count,
    )
    shard_payload = _load_json_payload(shard_path)
    for record in shard_payload.get("records", []):
        if int(record.get("trace_index", -1)) == trace_index:
            return dict(record.get("trace", {}))
    return None


def _write_trace_to_shard(
    trace_dir: Path,
    trace_index: int,
    requested_trace_count: int,
    trace: dict[str, Any],
) -> None:
    """Write one trace into the corresponding trace shard.

    Args:
        trace_dir (`Path`):
            Checkpoint trace directory.
        trace_index (`int`):
            Zero-based trace index.
        requested_trace_count (`int`):
            Total requested trace count for the run.
        trace (`dict[str, Any]`):
            Trace payload to persist.
    """
    shard_path = _resolve_trace_shard_path(
        trace_dir=trace_dir,
        trace_index=trace_index,
        requested_trace_count=requested_trace_count,
    )
    shard_start, shard_end = _resolve_shard_bounds(
        trace_index=trace_index,
        requested_trace_count=requested_trace_count,
    )
    shard_payload = _load_json_payload(shard_path) or {
        "artifact_type": "sdg_trace_shard",
        "trace_index_start": shard_start,
        "trace_index_end": min(shard_end, requested_trace_count - 1),
        "requested_trace_count": requested_trace_count,
        "records": [],
    }
    records = [
        record
        for record in shard_payload.get("records", [])
        if int(record.get("trace_index", -1)) != trace_index
    ]
    records.append(
        {
            "trace_index": trace_index,
            "trace_id": trace.get("trace_id", _build_trace_id(trace_index)),
            "trace": trace,
        },
    )
    shard_payload["records"] = sorted(records, key=lambda item: int(item["trace_index"]))
    shard_path.write_text(
        json.dumps(shard_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        `argparse.ArgumentParser`:
            Configured parser instance.
    """
    parser = argparse.ArgumentParser(
        description="Generate SDG-oriented MCP execution traces.",
    )
    parser.add_argument(
        "--trace-count",
        type=int,
        default=100,
        help="Number of standalone SDG traces to generate.",
    )
    parser.add_argument(
        "--output",
        help="Path to the output JSON file.",
    )
    parser.add_argument(
        "--transition-matrix-output",
        help=(
            "Optional JSON path for server/state transition counts and "
            "Markov matrices derived from the generated traces."
        ),
    )
    parser.add_argument(
        "--checkpoint-dir",
        help=(
            "Optional directory for resumable prompt/trace checkpoints. "
            "Defaults to <output_stem>_checkpoint next to --output."
        ),
    )
    parser.add_argument(
        "--manifest-path",
        help="Optional path to laplace_mcp_manifest.json.",
    )
    parser.add_argument(
        "--dashscope-model",
        default="qwen3-max",
        help="DashScope model name.",
    )
    parser.add_argument(
        "--emit-prompt-only",
        action="store_true",
        help="Print the generic batch prompt instead of calling the model.",
    )
    parser.add_argument(
        "--batch-trace-count",
        type=int,
        default=100,
        help="Trace count used by --emit-prompt-only.",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    """Run the CLI workflow.

    Args:
        args (`argparse.Namespace`):
            Parsed CLI arguments.

    Returns:
        `int`:
            Process exit code.
    """
    catalog = load_laplace_server_catalog(manifest_path=args.manifest_path)
    if args.emit_prompt_only:
        print(
            build_batch_trace_prompt(
                server_catalog=catalog,
                trace_count=max(1, int(args.batch_trace_count)),
            ),
        )
        return 0

    if not args.output:
        raise ValueError(
            "--output is required unless --emit-prompt-only is used.",
        )

    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise ValueError("DASHSCOPE_API_KEY is required for trace generation.")

    synthesizer = SDGTraceSynthesizer(
        llm_provider=DashScopeCompletionProvider(
            model_name=args.dashscope_model,
            api_key=api_key,
        ),
    )
    output_path = Path(args.output)
    run_paths = _resolve_run_paths(
        output_path=output_path,
        checkpoint_dir=args.checkpoint_dir,
    )
    _ensure_run_dirs(run_paths)

    requested_trace_count = max(1, int(args.trace_count))
    traces = _load_checkpointed_traces(
        trace_dir=run_paths["trace_dir"],
        requested_trace_count=requested_trace_count,
    )
    _persist_outputs(
        traces=traces,
        requested_trace_count=requested_trace_count,
        output_path=output_path,
        transition_matrix_output=args.transition_matrix_output,
        run_paths=run_paths,
    )

    for trace_index in range(len(traces), requested_trace_count):
        prompt = _read_prompt_from_shard(
            prompt_dir=run_paths["prompt_dir"],
            trace_index=trace_index,
            requested_trace_count=requested_trace_count,
        )
        if prompt is None:
            prompt = build_standalone_trace_prompt(
                server_catalog=catalog,
                trace_index=trace_index,
                total_traces=requested_trace_count,
            )
            _write_prompt_to_shard(
                prompt_dir=run_paths["prompt_dir"],
                trace_index=trace_index,
                requested_trace_count=requested_trace_count,
                prompt=prompt,
            )

        trace = _read_trace_from_shard(
            trace_dir=run_paths["trace_dir"],
            trace_index=trace_index,
            requested_trace_count=requested_trace_count,
        )
        if trace is None:
            trace = await synthesizer.generate_trace_from_prompt(
                prompt=prompt,
                server_catalog=catalog,
                trace_index=trace_index,
            )
            _write_trace_to_shard(
                trace_dir=run_paths["trace_dir"],
                trace_index=trace_index,
                requested_trace_count=requested_trace_count,
                trace=trace,
            )

        traces.append(trace)
        _persist_outputs(
            traces=traces,
            requested_trace_count=requested_trace_count,
            output_path=output_path,
            transition_matrix_output=args.transition_matrix_output,
            run_paths=run_paths,
        )
    return 0


def _build_transition_matrix_payload(
    traces: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a JSON-serializable payload for transition statistics.

    Args:
        traces (`list[dict[str, Any]]`):
            Generated SDG traces.

    Returns:
        `dict[str, Any]`:
            Combined server/state transition counts and Markov matrices.
    """
    return {
        "trace_schema_version": TRACE_SCHEMA_VERSION,
        "trace_count": len(traces),
        "server_transition_counts": build_server_transition_counts(traces),
        "server_transition_matrix": build_server_transition_matrix(traces),
        "state_transition_counts": build_state_transition_counts(traces),
        "state_transition_matrix": build_state_transition_matrix(traces),
    }


def _resolve_run_paths(
    output_path: Path,
    checkpoint_dir: str | None,
) -> dict[str, Path]:
    """Resolve resumable generation paths for prompts, traces, and metadata.

    Args:
        output_path (`Path`):
            Consolidated trace output path.
        checkpoint_dir (`str | None`):
            Optional checkpoint directory override.

    Returns:
        `dict[str, Path]`:
            Resolved path mapping.
    """
    root = (
        Path(checkpoint_dir)
        if checkpoint_dir is not None
        else Path(__file__).resolve().parent / f"{output_path.stem}_checkpoint"
    )
    return {
        "root": root,
        "prompt_dir": root / "prompts",
        "trace_dir": root / "traces",
        "manifest": root / "generation_manifest.json",
    }


def _ensure_run_dirs(run_paths: dict[str, Path]) -> None:
    """Create directories required by the resumable generation run.

    Args:
        run_paths (`dict[str, Path]`):
            Resolved path mapping.
    """
    run_paths["root"].mkdir(parents=True, exist_ok=True)
    run_paths["prompt_dir"].mkdir(parents=True, exist_ok=True)
    run_paths["trace_dir"].mkdir(parents=True, exist_ok=True)


def _load_checkpointed_traces(
    trace_dir: Path,
    requested_trace_count: int,
) -> list[dict[str, Any]]:
    """Load already-generated traces from checkpoint files in index order.

    Args:
        trace_dir (`Path`):
            Checkpoint trace directory.
        requested_trace_count (`int`):
            Number of traces requested for the current run.

    Returns:
        `list[dict[str, Any]]`:
            Loaded traces in contiguous index order.
    """
    traces: list[dict[str, Any]] = []
    for trace_index in range(max(1, int(requested_trace_count))):
        trace = _read_trace_from_shard(
            trace_dir=trace_dir,
            trace_index=trace_index,
            requested_trace_count=requested_trace_count,
        )
        if trace is None:
            break
        traces.append(trace)
    return traces


def _persist_outputs(
    traces: list[dict[str, Any]],
    requested_trace_count: int,
    output_path: Path,
    transition_matrix_output: str | None,
    run_paths: dict[str, Path],
) -> None:
    """Persist consolidated traces, optional matrices, and run manifest.

    Args:
        traces (`list[dict[str, Any]]`):
            Generated traces collected so far.
        requested_trace_count (`int`):
            Number of traces requested for the run.
        output_path (`Path`):
            Consolidated trace output path.
        transition_matrix_output (`str | None`):
            Optional transition-matrix JSON path.
        run_paths (`dict[str, Path]`):
            Resolved path mapping.
    """
    existing_manifest = _load_existing_manifest(run_paths)
    archive_collection_id = existing_manifest.get("collection_id", output_path.stem)
    started_at_utc = existing_manifest.get("started_at_utc", _utc_timestamp())
    status = (
        "completed"
        if len(traces) >= requested_trace_count
        else "in_progress"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "schema_version": TRACE_SCHEMA_VERSION,
                "trace_count": len(traces),
                "requested_trace_count": requested_trace_count,
                "generation_mode": "standalone_resumable",
                "checkpoint_dir": str(run_paths["root"]),
                "traces": traces,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    if transition_matrix_output:
        matrix_output_path = Path(transition_matrix_output)
        matrix_output_path.parent.mkdir(parents=True, exist_ok=True)
        matrix_output_path.write_text(
            json.dumps(
                _build_transition_matrix_payload(traces=traces),
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    run_paths["manifest"].write_text(
        json.dumps(
            {
                "manifest_schema": "laplace.context2sdg.checkpoint_manifest.v1",
                "trace_schema_version": TRACE_SCHEMA_VERSION,
                "collection_id": archive_collection_id,
                "artifact_type": "sdg_trace_checkpoint_run",
                "artifact_description": (
                    "Checkpointed standalone SDG trace generation artifacts "
                    "for the Laplace MCP server catalog."
                ),
                "requested_trace_count": requested_trace_count,
                "completed_trace_count": len(traces),
                "status": status,
                "generation_mode": "standalone_resumable",
                "started_at_utc": started_at_utc,
                "last_updated_at_utc": _utc_timestamp(),
                "artifact_paths": {
                    "checkpoint_root": str(run_paths["root"]),
                    "prompt_dir": str(run_paths["prompt_dir"]),
                    "trace_dir": str(run_paths["trace_dir"]),
                    "consolidated_trace_output": str(output_path),
                    "transition_matrix_output": transition_matrix_output,
                },
                "file_naming": {
                    "prompt_file_pattern": (
                        "sdg_prompt_shard_{trace_index_start:05d}_to_"
                        "{trace_index_end:05d}_of_"
                        "{requested_trace_count:05d}.json"
                    ),
                    "trace_file_pattern": (
                        "sdg_trace_shard_{trace_index_start:05d}_to_"
                        "{trace_index_end:05d}_of_"
                        "{requested_trace_count:05d}.json"
                    ),
                },
                "checkpoint_shard_size": _CHECKPOINT_SHARD_SIZE,
                "completed_trace_ids": [
                    trace.get("trace_id", _build_trace_id(index))
                    for index, trace in enumerate(traces)
                ],
                "is_complete": status == "completed",
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main() -> None:
    """Run the SDG trace synthesis CLI entry point.

    Returns:
        `None`:
            This function exits the process explicitly.
    """
    parser = _build_argument_parser()
    args = parser.parse_args()
    try:
        raise SystemExit(asyncio.run(_run(args)))
    except Exception as exc:  # noqa: BLE001
        print(f"[generate_sdg_traces] {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()