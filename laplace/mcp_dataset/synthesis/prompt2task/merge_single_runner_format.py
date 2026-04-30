"""Merge single-server runner-format synthesis outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .._merge_runner_format import merge_runner_files, merge_runner_payloads, resolve_merge_plan


DEFAULT_SINGLE_RUNNER_GLOB = "benchmark_tasks_single_*_runner_format.json"


def resolve_input_files(
    inputs: list[str] | None = None,
    glob_pattern: str | None = None,
    search_root: str | None = None,
    output_file: str | None = None,
) -> list[str]:
    """Resolve merge input files from explicit paths and optional glob.

    Args:
        inputs (`list[str] | None`, optional):
            Explicit input file paths.
        glob_pattern (`str | None`, optional):
            Optional glob pattern used under ``search_root``.
        search_root (`str | None`, optional):
            Root directory for glob expansion.
        output_file (`str | None`, optional):
            Output file path to exclude from discovered inputs.

    Returns:
        `list[str]`:
            Ordered unique input file paths.

    Raises:
        `ValueError`:
            Raised when no input files are resolved.
    """
    resolved, _ = resolve_merge_plan(
        inputs=inputs,
        glob_pattern=glob_pattern,
        search_root=search_root,
        output_file=output_file,
        include_existing_output=False,
    )
    return resolved


def resolve_merge_sources(
    inputs: list[str] | None = None,
    glob_pattern: str | None = None,
    search_root: str | None = None,
    output_file: str | None = None,
) -> tuple[list[str], list[str]]:
    """Resolve payload inputs and source-file metadata for single merges.

    Args:
        inputs (`list[str] | None`, optional):
            Explicit input file paths.
        glob_pattern (`str | None`, optional):
            Optional glob pattern used under ``search_root``.
        search_root (`str | None`, optional):
            Root directory for glob expansion.
        output_file (`str | None`, optional):
            Output file path.

    Returns:
        `tuple[list[str], list[str]]`:
            Input payload files and raw source files.
    """
    return resolve_merge_plan(
        inputs=inputs,
        glob_pattern=glob_pattern,
        search_root=search_root,
        output_file=output_file,
        include_existing_output=True,
    )


def merge_single_runner_payloads(
    payloads: list[dict[str, Any]],
    source_names: list[str] | None = None,
) -> dict[str, Any]:
    """Merge multiple single-server runner-format payloads.

    Args:
        payloads (`list[dict[str, Any]]`):
            Runner-format payloads to merge.
        source_names (`list[str] | None`, optional):
            Optional source file names for metadata.

    Returns:
        `dict[str, Any]`:
            Merged runner-format payload with reindexed task ids.

    Raises:
        `ValueError`:
            Raised when no payloads are provided.
    """
    return merge_runner_payloads(payloads, source_names=source_names)


def merge_single_runner_files(
    input_files: list[str],
    output_file: str,
    source_names: list[str] | None = None,
) -> dict[str, Any]:
    """Merge multiple single-server runner-format files and write output.

    Args:
        input_files (`list[str]`):
            Source runner-format file paths.
        output_file (`str`):
            Destination JSON file path.

    Returns:
        `dict[str, Any]`:
            Merged runner-format payload.
    """
    return merge_runner_files(
        input_files=input_files,
        output_file=output_file,
        source_names=source_names or input_files,
    )


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments.

    Returns:
        `argparse.Namespace`:
            Parsed CLI args.
    """
    parser = argparse.ArgumentParser(
        description="Merge benchmark_tasks_single_*_runner_format.json files.",
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Optional explicit input single runner-format JSON files.",
    )
    parser.add_argument(
        "--glob",
        dest="glob_pattern",
        default=DEFAULT_SINGLE_RUNNER_GLOB,
        help=(
            "Glob pattern under --search-root for auto-discovery "
            f"(default: {DEFAULT_SINGLE_RUNNER_GLOB})."
        ),
    )
    parser.add_argument(
        "--search-root",
        default=".",
        help="Root directory used when expanding --glob.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON file path.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the merge CLI.

    Returns:
        `int`:
            Process exit code.
    """
    args = _parse_args()
    input_files, source_names = resolve_merge_sources(
        inputs=[str(Path(path)) for path in args.inputs],
        glob_pattern=args.glob_pattern,
        search_root=args.search_root,
        output_file=args.output,
    )
    merged = merge_single_runner_files(
        input_files=input_files,
        output_file=args.output,
        source_names=source_names,
    )
    print(
        json.dumps(
            {
                "output": args.output,
                "input_files": input_files,
                "source_files": source_names,
                "source_file_count": merged["generation_info"]["source_file_count"],
                "successful_servers": merged["generation_info"]["successful_servers"],
                "total_tasks": merged["total_tasks"],
            },
            indent=2,
            ensure_ascii=False,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())