"""CLI for DashScope-based MCP-Bench dataset synthesis in AgentScope."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .benchmark_generator import BenchmarkTaskGenerator
from .validate_mcp_servers import MCPServerValidator

_logger = logging.getLogger(__name__)


def _build_run_stamp(now: datetime | None = None) -> str:
    """Build the default timestamp suffix for generated artifacts.

    Args:
        now (`datetime | None`, optional):
            Datetime value to format. Uses current local time when omitted.

    Returns:
        `str`:
            Timestamp string formatted as ``MMDDHHMM``.
    """
    moment = now or datetime.now()
    return moment.strftime("%m%d%H%M")


async def _generate_single(
    generator: BenchmarkTaskGenerator,
    output_file: str,
    server_names: list[str] | None = None,
) -> dict[str, Any]:
    """Generate single-server tasks and runner-format export.

    Args:
        generator (`BenchmarkTaskGenerator`):
            Initialized generator.
        output_file (`str`):
            Raw JSON output path.
        server_names (`list[str] | None`, optional):
            Optional target server names.

    Returns:
        `dict[str, Any]`:
            Raw generation result.
    """
    results = await generator.generate_single_server_tasks(
        servers=server_names,
        output_file=output_file,
    )
    generator.convert_single_to_runner_format(
        results,
        output_file.replace(".json", "_runner_format.json"),
    )
    return results


async def _generate_multi(
    generator: BenchmarkTaskGenerator,
    output_file: str,
    combinations_file: str,
    allowed_servers: list[str] | None = None,
) -> dict[str, Any]:
    """Generate multi-server tasks and runner-format export.

    Args:
        generator (`BenchmarkTaskGenerator`):
            Initialized generator.
        output_file (`str`):
            Raw JSON output path.
        combinations_file (`str`):
            Combination JSON path.
        allowed_servers (`list[str] | None`, optional):
            Optional server whitelist. When provided, combinations that include
            unavailable servers are dropped before generation.

    Returns:
        `dict[str, Any]`:
            Raw generation result.
    """
    filtered_file = combinations_file
    if allowed_servers is not None:
        combo_path = Path(combinations_file)
        if not combo_path.is_absolute():
            combo_path = Path(__file__).resolve().parent / combo_path
        filtered_data, kept, dropped = _filter_combinations_payload(
            payload=json.loads(combo_path.read_text(encoding="utf-8")),
            allowed_servers=set(allowed_servers),
        )
        if kept == 0:
            raise RuntimeError(
                "No combinations left after applying server whitelist.",
            )
        filtered_path = combo_path.parent / (
            f"{combo_path.stem}_whitelist_filtered{combo_path.suffix}"
        )
        filtered_path.write_text(
            json.dumps(filtered_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        filtered_file = str(filtered_path)
        _logger.info(
            "[whitelist] filtered combinations: kept=%d, dropped=%d, file=%s",
            kept,
            dropped,
            filtered_path,
        )

    results = await generator.generate_multi_server_tasks(
        combinations_file=filtered_file,
        output_file=output_file,
    )
    generator.convert_multi_to_runner_format(
        results,
        output_file.replace(".json", "_runner_format.json"),
    )
    return results


def _filter_combinations_payload(
    payload: dict[str, Any],
    allowed_servers: set[str],
) -> tuple[dict[str, Any], int, int]:
    """Filter multi-server combinations by whitelist.

    Args:
        payload (`dict[str, Any]`):
            Raw combinations JSON payload.
        allowed_servers (`set[str]`):
            Whitelisted server names.

    Returns:
        `tuple[dict[str, Any], int, int]`:
            Filtered payload, kept-count, dropped-count.
    """
    output = {"mcp_server_combinations": {}}
    kept = 0
    dropped = 0
    combo_groups = payload.get("mcp_server_combinations", {})
    for group_name, items in combo_groups.items():
        if not isinstance(items, list):
            continue
        selected: list[dict[str, Any]] = []
        for item in items:
            servers = [str(name) for name in item.get("servers", [])]
            if servers and all(name in allowed_servers for name in servers):
                selected.append(item)
                kept += 1
            else:
                dropped += 1
        output["mcp_server_combinations"][group_name] = selected
    return output, kept, dropped


def _load_server_whitelist(whitelist_file: str) -> list[str]:
    """Load server whitelist from JSON or newline text file.

    Args:
        whitelist_file (`str`):
            Path to whitelist file.

    Returns:
        `list[str]`:
            Unique server names preserving input order.
    """
    path = Path(whitelist_file)
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []

    server_names: list[str] = []
    if path.suffix.lower() == ".json":
        payload = json.loads(raw)
        if isinstance(payload, dict):
            source = payload.get("servers", [])
        elif isinstance(payload, list):
            source = payload
        else:
            source = []
        server_names = [str(name).strip() for name in source if str(name).strip()]
    else:
        server_names = [line.strip() for line in raw.splitlines() if line.strip()]

    deduped: list[str] = []
    seen: set[str] = set()
    for name in server_names:
        if name in seen:
            continue
        deduped.append(name)
        seen.add(name)
    return deduped


def _save_server_whitelist(
    server_names: list[str],
    output_path: str,
) -> None:
    """Save server whitelist to JSON.

    Args:
        server_names (`list[str]`):
            Whitelisted server names.
        output_path (`str`):
            Output JSON path.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "timestamp": datetime.now().isoformat(),
                "total_servers": len(server_names),
                "servers": server_names,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


async def _resolve_allowed_servers(
    args: argparse.Namespace,
    output_dir: Path,
    run_stamp: str,
) -> list[str] | None:
    """Resolve effective allowed-server list from validation or file input.

    Args:
        args (`argparse.Namespace`):
            Parsed CLI arguments.
        output_dir (`Path`):
            Output directory.
        run_stamp (`str`):
            Timestamp suffix used in generated filenames.

    Returns:
        `list[str] | None`:
            Effective whitelist, or `None` when disabled.
    """
    file_whitelist: list[str] | None = None
    if args.server_whitelist_file:
        file_whitelist = _load_server_whitelist(args.server_whitelist_file)
        _logger.info(
            "[whitelist] loaded %d server(s) from %s",
            len(file_whitelist),
            args.server_whitelist_file,
        )

    validated_whitelist: list[str] | None = None
    if args.auto_validate_servers:
        validator = MCPServerValidator(
            manifest_path=args.manifest_path,
            request_timeout=args.validation_timeout,
            concurrency=args.validation_concurrency,
            enable_smoke_call=args.validation_enable_smoke_call,
        )
        report = await validator.validate()
        validation_output = (
            Path(args.validation_output)
            if args.validation_output
            else output_dir / f"server_validation_report_{run_stamp}.json"
        )
        validation_output.parent.mkdir(parents=True, exist_ok=True)
        validation_output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        _logger.info(
            "[validate] report written to %s",
            validation_output,
        )
        validated_whitelist = [
            str(item.get("server_name", ""))
            for item in report.get("servers", [])
            if item.get("status") == "pass"
        ]
        _logger.info(
            "[validate] pass=%d, fail/partial=%d",
            len(validated_whitelist),
            int(report.get("summary", {}).get("total_servers", 0)) - len(validated_whitelist),
        )

    effective: list[str] | None = None
    if file_whitelist is not None and validated_whitelist is not None:
        allow_set = set(validated_whitelist)
        effective = [name for name in file_whitelist if name in allow_set]
        _logger.info(
            "[whitelist] intersected file + validation -> %d server(s)",
            len(effective),
        )
    elif file_whitelist is not None:
        effective = file_whitelist
    elif validated_whitelist is not None:
        effective = validated_whitelist

    if effective is not None:
        if not effective:
            raise RuntimeError("Server whitelist is empty; aborting generation.")
        whitelist_output = (
            Path(args.whitelist_output)
            if args.whitelist_output
            else output_dir / f"server_whitelist_{run_stamp}.json"
        )
        _save_server_whitelist(effective, str(whitelist_output))
        _logger.info("[whitelist] saved to %s", whitelist_output)

    return effective


async def main() -> int:
    """Run the synthesis CLI.

    Returns:
        `int`:
            Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="DashScope-based MCP-Bench task synthesis for AgentScope.",
    )
    parser.add_argument(
        "--mode",
        choices=["single", "multi", "all"],
        default="all",
        help="Generation mode.",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file or directory path.",
    )
    parser.add_argument(
        "--server",
        type=str,
        help="Generate tasks for a specific single server only.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console log level (default: INFO).",
    )
    parser.add_argument(
        "--combinations-file",
        type=str,
        default="split_combinations/mcp_2server_combinations.json",
        help="Combination JSON for multi-server generation.",
    )
    parser.add_argument(
        "--tasks-per-combination",
        type=int,
        default=1,
        help="Accepted tasks per server or combination.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retries per server or combination.",
    )
    parser.add_argument(
        "--disable-filter-problematic",
        action="store_true",
        help="Disable filtering of MCP-Bench problematic tools.",
    )
    parser.add_argument(
        "--dashscope-model",
        type=str,
        default="qwen3-max",
        help="DashScope model name.",
    )
    parser.add_argument(
        "--manifest-path",
        type=str,
        help="Optional path to laplace_mcp_manifest.json.",
    )
    parser.add_argument(
        "--auto-validate-servers",
        action="store_true",
        help="Validate all servers first and synthesize only validated pass servers.",
    )
    parser.add_argument(
        "--validation-timeout",
        type=float,
        default=20.0,
        help="Timeout in seconds used by server validation.",
    )
    parser.add_argument(
        "--validation-concurrency",
        type=int,
        default=8,
        help="Concurrency used by server validation.",
    )
    parser.add_argument(
        "--validation-enable-smoke-call",
        action="store_true",
        help="Enable one-tool smoke call during pre-synthesis validation.",
    )
    parser.add_argument(
        "--validation-output",
        type=str,
        help="Optional path to save server validation report JSON.",
    )
    parser.add_argument(
        "--server-whitelist-file",
        type=str,
        help="Optional JSON/TXT whitelist file; synthesis is restricted to these servers.",
    )
    parser.add_argument(
        "--whitelist-output",
        type=str,
        help="Optional path to save effective whitelist JSON.",
    )
    parser.add_argument(
        "--disable-self-heal-on-discovery-failure",
        action="store_true",
        help="Disable dynamic exclusion of servers that fail during discovery.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )

    generator = BenchmarkTaskGenerator(
        model_name=args.dashscope_model,
        filter_problematic=not args.disable_filter_problematic,
        tasks_per_server=args.tasks_per_combination,
        max_retries=args.max_retries,
        manifest_path=args.manifest_path,
        self_heal_on_discovery_failure=(
            not args.disable_self_heal_on_discovery_failure
        ),
    )

    run_stamp = _build_run_stamp()
    output_arg = Path(args.output) if args.output else None
    if output_arg and output_arg.suffix:
        output_dir = output_arg.parent
    else:
        output_dir = output_arg or Path(__file__).resolve().parents[1]
    output_dir.mkdir(parents=True, exist_ok=True)

    allowed_servers = await _resolve_allowed_servers(
        args=args,
        output_dir=output_dir,
        run_stamp=run_stamp,
    )

    try:
        if args.server:
            if allowed_servers is not None and args.server not in set(allowed_servers):
                raise RuntimeError(
                    f"Requested server is not in effective whitelist: {args.server}",
                )
            output_file = str(
                output_dir
                / f"benchmark_tasks_{args.server.replace(' ', '_')}_{run_stamp}.json"
            )
            results = await _generate_single(
                generator,
                output_file,
                server_names=[args.server],
            )
            print(json.dumps(results.get("generation_info", {}), indent=2, ensure_ascii=False))
            return 0

        if args.mode == "single":
            output_file = str(output_dir / f"benchmark_tasks_single_{run_stamp}.json")
            results = await _generate_single(
                generator,
                output_file,
                server_names=allowed_servers,
            )
            print(json.dumps(results.get("generation_info", {}), indent=2, ensure_ascii=False))
            return 0

        if args.mode == "multi":
            output_file = str(output_dir / f"benchmark_tasks_multi_{run_stamp}.json")
            results = await _generate_multi(
                generator,
                output_file,
                args.combinations_file,
                allowed_servers=allowed_servers,
            )
            print(json.dumps(results.get("generation_info", {}), indent=2, ensure_ascii=False))
            return 0

        single_file = str(output_dir / f"benchmark_tasks_single_{run_stamp}.json")
        multi_file = str(output_dir / f"benchmark_tasks_multi_{run_stamp}.json")
        single_results = await _generate_single(
            generator,
            single_file,
            server_names=allowed_servers,
        )
        multi_results = await _generate_multi(
            generator,
            multi_file,
            args.combinations_file,
            allowed_servers=allowed_servers,
        )
        summary = {
            "generation_timestamp": datetime.now().isoformat(),
            "single_server": single_results.get("generation_info", {}),
            "multi_server": multi_results.get("generation_info", {}),
        }
        summary_file = output_dir / f"benchmark_generation_summary_{run_stamp}.json"
        summary_file.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"Generation failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))