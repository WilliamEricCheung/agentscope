"""Augment and rebalance the laplace single-runner router dataset."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .benchmark_generator import BenchmarkTaskGenerator
from .merge_single_runner_format import merge_single_runner_files


def _load_counts(dataset_path: Path) -> dict[str, int]:
    """Load per-server task counts from one runner-format dataset."""
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    return {
        str(block.get("server_name", "")).strip(): len(block.get("tasks", []))
        for block in payload.get("server_tasks", [])
        if str(block.get("server_name", "")).strip()
    }


def _load_sources(dataset_path: Path) -> list[str]:
    """Load merge metadata source names from one runner-format dataset."""
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    sources = [
        str(item)
        for item in payload.get("generation_info", {}).get("merged_from_files", [])
        if str(item).strip()
    ]
    return sources or [str(dataset_path)]


def _build_gap_groups(
    counts: dict[str, int],
    target_count: int,
) -> dict[int, list[str]]:
    """Group servers by remaining task gap."""
    grouped: dict[int, list[str]] = defaultdict(list)
    for server_name, count in counts.items():
        gap = max(0, int(target_count) - int(count))
        if gap <= 0:
            continue
        grouped[gap].append(server_name)
    for gap in grouped:
        grouped[gap].sort()
    return dict(sorted(grouped.items()))


async def _augment_dataset(args: argparse.Namespace) -> dict[str, Any]:
    """Run balanced synthesis batches and merge results back into one dataset."""
    dataset_path = Path(args.dataset).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    counts = _load_counts(dataset_path)
    gap_groups = _build_gap_groups(counts, args.target_count)
    generated_runner_files: list[str] = []
    batch_records: list[dict[str, Any]] = []

    if not gap_groups:
        return {
            "dataset": str(dataset_path),
            "target_count": args.target_count,
            "generated_batches": [],
            "generated_runner_files": [],
            "status": "no_op",
        }

    generator = BenchmarkTaskGenerator(
        model_name=args.dashscope_model,
        tasks_per_server=1,
        max_retries=args.max_retries,
        manifest_path=args.manifest_path,
    )

    run_stamp = datetime.now().strftime("%m%d%H%M")
    print(
        json.dumps(
            {
                "dataset": str(dataset_path),
                "target_count": args.target_count,
                "gap_groups": gap_groups,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    for gap, servers in gap_groups.items():
        generator.tasks_per_server = gap
        batch_name = f"laplace_balance_gap{gap}_{run_stamp}"
        raw_file = output_dir / f"{batch_name}.json"
        print(
            json.dumps(
                {
                    "stage": "start_batch",
                    "gap": gap,
                    "server_count": len(servers),
                    "servers": servers,
                    "raw_file": str(raw_file),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        results = await generator.generate_single_server_tasks(
            servers=servers,
            output_file=str(raw_file),
        )
        runner_file = raw_file.with_name(f"{raw_file.stem}_runner_format.json")
        generator.convert_single_to_runner_format(results, str(runner_file))
        generated_runner_files.append(str(runner_file))
        print(
            json.dumps(
                {
                    "stage": "finish_batch",
                    "gap": gap,
                    "runner_file": str(runner_file),
                    "generation_info": results.get("generation_info", {}),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        batch_records.append(
            {
                "gap": gap,
                "servers": servers,
                "raw_file": str(raw_file),
                "runner_file": str(runner_file),
                "generation_info": results.get("generation_info", {}),
            },
        )

    tmp_output = dataset_path.with_suffix(".tmp.json")
    source_names = _load_sources(dataset_path) + generated_runner_files
    merge_single_runner_files(
        input_files=[str(dataset_path), *generated_runner_files],
        output_file=str(tmp_output),
        source_names=source_names,
    )
    tmp_output.replace(dataset_path)

    summary = {
        "dataset": str(dataset_path),
        "target_count": args.target_count,
        "generated_batches": batch_records,
        "generated_runner_files": generated_runner_files,
        "status": "completed",
    }
    summary_path = output_dir / f"laplace_balance_summary_{run_stamp}.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    summary["summary_file"] = str(summary_path)
    return summary


def _parse_args() -> argparse.Namespace:
    """Parse CLI args for balanced laplace augmentation."""
    parser = argparse.ArgumentParser(
        description="Augment laplace_tasks_single_runner_format.json to a balanced target count.",
    )
    parser.add_argument(
        "--dataset",
        default="laplace/mcp_dataset/laplace_tasks_single_runner_format.json",
        help="Target laplace single-runner dataset to augment.",
    )
    parser.add_argument(
        "--output-dir",
        default="laplace/mcp_dataset/synthesis/prompt2task/generated_20260604/balanced_laplace",
        help="Directory for intermediate synthesis outputs.",
    )
    parser.add_argument(
        "--target-count",
        type=int,
        default=8,
        help="Desired minimum task count per server after augmentation.",
    )
    parser.add_argument(
        "--dashscope-model",
        default="qwen3-max",
        help="DashScope model used for synthesis.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum generation retries per server batch.",
    )
    parser.add_argument(
        "--manifest-path",
        help="Optional laplace_mcp_manifest.json path.",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""
    args = _parse_args()
    summary = asyncio.run(_augment_dataset(args))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())