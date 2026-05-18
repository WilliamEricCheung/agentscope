"""Shared helpers for merging runner-format benchmark datasets."""

from __future__ import annotations

import json
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
import re
from typing import Any


def normalize_task_prefix(server_name: str) -> str:
    """Normalize a server label into a stable task id prefix.

    Args:
        server_name (`str`):
            Server display name or server-group label.

    Returns:
        `str`:
            Normalized identifier prefix.
    """
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", server_name.strip().lower())
    normalized = normalized.strip("_")
    if normalized:
        return normalized
    return "generated"


def load_runner_format(input_file: str) -> dict[str, Any]:
    """Load one runner-format JSON payload.

    Args:
        input_file (`str`):
            Path to a runner-format JSON file.

    Returns:
        `dict[str, Any]`:
            Parsed JSON object.

    Raises:
        `ValueError`:
            Raised when the payload is missing required top-level keys.
    """
    path = Path(input_file)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Runner-format file must contain a JSON object: {path}")
    if "server_tasks" not in payload:
        raise ValueError(f"Runner-format file missing 'server_tasks': {path}")
    return payload


def _normalize_path_string(path_like: str) -> str:
    """Normalize one path string for set comparisons.

    Args:
        path_like (`str`):
            Raw path string.

    Returns:
        `str`:
            Normalized absolute path string.
    """
    return str(Path(path_like).resolve())


def resolve_merge_plan(
    inputs: list[str] | None = None,
    glob_pattern: str | None = None,
    search_root: str | None = None,
    output_file: str | None = None,
    include_existing_output: bool = True,
) -> tuple[list[str], list[str]]:
    """Resolve the actual payload inputs and raw source-file metadata.

    Args:
        inputs (`list[str] | None`, optional):
            Explicit input file paths.
        glob_pattern (`str | None`, optional):
            Optional glob pattern used under ``search_root``.
        search_root (`str | None`, optional):
            Root directory for glob expansion.
        output_file (`str | None`, optional):
            Output file path.
        include_existing_output (`bool`, optional):
            Whether to use the existing output file as the merge baseline.

    Returns:
        `tuple[list[str], list[str]]`:
            Input payload paths and raw source-file paths for metadata.

    Raises:
        `ValueError`:
            Raised when no input payload can be resolved.
    """
    resolved_inputs: list[str] = []
    resolved_sources: list[str] = []
    seen_inputs: set[str] = set()
    seen_sources: set[str] = set()
    already_merged_sources: set[str] = set()
    output_path = Path(output_file).resolve() if output_file else None

    if (
        include_existing_output
        and output_path is not None
        and output_path.exists()
        and output_path.is_file()
    ):
        baseline_payload = load_runner_format(str(output_path))
        baseline_sources = [
            _normalize_path_string(str(path))
            for path in baseline_payload.get("generation_info", {}).get(
                "merged_from_files",
                [],
            )
            if str(path).strip()
        ]
        resolved_inputs.append(str(output_path))
        seen_inputs.add(str(output_path))
        for source in baseline_sources:
            if source in seen_sources:
                continue
            seen_sources.add(source)
            already_merged_sources.add(source)
            resolved_sources.append(source)

    for item in inputs or []:
        path = Path(item).resolve()
        path_str = str(path)
        if output_path is not None and path == output_path:
            continue
        if path_str in seen_inputs:
            continue
        if path_str in already_merged_sources:
            continue
        seen_inputs.add(path_str)
        resolved_inputs.append(path_str)
        if path_str not in seen_sources:
            seen_sources.add(path_str)
            resolved_sources.append(path_str)

    if glob_pattern:
        root = Path(search_root or ".").resolve()
        for path in sorted(root.glob(glob_pattern)):
            if not path.is_file():
                continue
            path = path.resolve()
            path_str = str(path)
            if output_path is not None and path == output_path:
                continue
            if path_str in seen_inputs:
                continue
            if path_str in already_merged_sources:
                continue
            seen_inputs.add(path_str)
            resolved_inputs.append(path_str)
            if path_str not in seen_sources:
                seen_sources.add(path_str)
                resolved_sources.append(path_str)

    if not resolved_inputs:
        raise ValueError("No input files resolved for merging")
    return resolved_inputs, resolved_sources


def merge_runner_payloads(
    payloads: list[dict[str, Any]],
    source_names: list[str] | None = None,
) -> dict[str, Any]:
    """Merge multiple runner-format payloads.

    Args:
        payloads (`list[dict[str, Any]]`):
            Runner-format payloads to merge.
        source_names (`list[str] | None`, optional):
            Raw source files represented by the merge result.

    Returns:
        `dict[str, Any]`:
            Merged runner-format payload with reindexed task ids.

    Raises:
        `ValueError`:
            Raised when no payloads are provided.
    """
    if not payloads:
        raise ValueError("At least one runner-format payload is required")

    grouped: OrderedDict[str, dict[str, Any]] = OrderedDict()
    runtime_unhealthy_servers: set[str] = set()
    generation_models: list[str] = []

    for payload in payloads:
        generation_info = payload.get("generation_info", {})
        runtime_unhealthy_servers.update(
            str(name)
            for name in generation_info.get("runtime_unhealthy_servers", [])
            if str(name).strip()
        )
        model_name = generation_info.get("generation_model")
        if isinstance(model_name, list):
            for item in model_name:
                normalized = str(item).strip()
                if normalized and normalized not in generation_models:
                    generation_models.append(normalized)
        else:
            normalized = str(model_name or "").strip()
            if normalized and normalized not in generation_models:
                generation_models.append(normalized)

        for block in payload.get("server_tasks", []):
            server_name = str(block.get("server_name", "")).strip()
            if not server_name:
                continue

            merged_block = grouped.setdefault(
                server_name,
                {
                    "server_name": server_name,
                    "servers": list(block.get("servers", [])) or [server_name],
                    "combination_name": block.get("combination_name", server_name),
                    "combination_type": block.get("combination_type", "merged"),
                    "tasks": [],
                },
            )
            merged_block["tasks"].extend(block.get("tasks", []))

    merged_server_tasks: list[dict[str, Any]] = []
    total_tasks = 0
    for server_name, block in grouped.items():
        prefix = normalize_task_prefix(server_name)
        reindexed_tasks: list[dict[str, Any]] = []
        for index, task in enumerate(block.get("tasks", [])):
            reindexed_task = dict(task)
            reindexed_task["task_id"] = f"{prefix}_{index:03d}"
            reindexed_tasks.append(reindexed_task)

        merged_block = dict(block)
        merged_block["tasks"] = reindexed_tasks
        total_tasks += len(reindexed_tasks)
        merged_server_tasks.append(merged_block)

    generation_model: str | list[str] | None
    if not generation_models:
        generation_model = None
    elif len(generation_models) == 1:
        generation_model = generation_models[0]
    else:
        generation_model = generation_models

    merged_generation_info = {
        "timestamp": datetime.now().isoformat(),
        "successful_servers": len(merged_server_tasks),
        "failed_servers": 0,
        "runtime_unhealthy_servers": sorted(runtime_unhealthy_servers),
        "generation_model": generation_model,
        "status": "completed",
        "merged_from_files": source_names or [],
        "source_file_count": len(source_names or []),
    }

    return {
        "generation_info": merged_generation_info,
        "server_tasks": merged_server_tasks,
        "total_tasks": total_tasks,
    }


def merge_runner_files(
    input_files: list[str],
    output_file: str,
    source_names: list[str] | None = None,
) -> dict[str, Any]:
    """Merge multiple runner-format files and write the output.

    Args:
        input_files (`list[str]`):
            Source runner-format payload paths.
        output_file (`str`):
            Destination JSON path.
        source_names (`list[str] | None`, optional):
            Raw source-file list stored in output metadata.

    Returns:
        `dict[str, Any]`:
            Merged runner-format payload.
    """
    payloads = [load_runner_format(path) for path in input_files]
    merged = merge_runner_payloads(payloads, source_names=source_names)
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return merged