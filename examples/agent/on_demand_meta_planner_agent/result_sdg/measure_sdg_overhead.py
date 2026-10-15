"""Run repeated SDG prefetch overhead experiments and retain raw telemetry.

The default workload matches the historical ``case_blended_heavy_late``
experiments. Each repetition runs C1+C2 with the existing SDG experiment
runner, retains its worker timing JSONL, and samples Docker resource usage.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import threading
import time
from typing import Any

_AGENT_DIR = Path(__file__).resolve().parents[1]
_DEFAULT_TURN_SCRIPT = _AGENT_DIR / "dialogue_scripts" / "case_blended_heavy_late.json"
_THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_AGENT_DIR))

import run_sdg_experiment as _runner  # noqa: E402


def _parse_cpu_cores(value: str) -> float:
    """Convert Docker's CPU percentage to the equivalent number of cores.

    Args:
        value (`str`):
            CPU percentage reported by Docker.

    Returns:
        `float`:
            CPU usage in core equivalents.
    """
    match = re.fullmatch(r"\s*([\d.]+)\s*%\s*", value)
    if match is None:
        raise ValueError(f"Unrecognized Docker CPU percentage: {value!r}")
    return float(match.group(1)) / 100.0


def _parse_memory_gib(value: str) -> float:
    """Parse the used-memory part of Docker's ``used / limit`` value.

    Args:
        value (`str`):
            Memory usage string reported by Docker.

    Returns:
        `float`:
            Used memory in GiB.
    """
    used = value.split("/", maxsplit=1)[0].strip()
    match = re.fullmatch(r"([\d.]+)\s*([A-Za-z]+)", used)
    if match is None:
        raise ValueError(f"Unrecognized Docker memory usage: {value!r}")
    amount = float(match.group(1))
    unit = match.group(2).lower()
    byte_factors = {
        "b": 1,
        "kb": 1000,
        "kib": 1024,
        "mb": 1000**2,
        "mib": 1024**2,
        "gb": 1000**3,
        "gib": 1024**3,
        "tb": 1000**4,
        "tib": 1024**4,
    }
    if unit not in byte_factors:
        raise ValueError(f"Unsupported Docker memory unit: {unit!r}")
    return amount * byte_factors[unit] / (1024**3)


class _DockerStatsSampler:
    """Sample Docker CPU and memory usage for the experiment's MCP containers."""

    def __init__(
        self,
        group_to_container_prefix: dict[str, str],
        interval_seconds: float,
    ) -> None:
        """Initialize the sampler.

        Args:
            group_to_container_prefix (`dict[str, str]`):
                MCP group names mapped to base Docker container names. Scoped
                worker containers may append a unique suffix to the base name.
            interval_seconds (`float`):
                Time between resource samples.
        """
        self.group_to_container_prefix = {
            group: name.lstrip("/")
            for group, name in group_to_container_prefix.items()
        }
        self.interval_seconds = interval_seconds
        self.samples: list[dict[str, Any]] = []
        self.error: BaseException | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def start(self) -> None:
        """Start background sampling.

        Returns:
            `None`:
                The sampling thread is started.
        """
        self._thread.start()

    def stop(self) -> None:
        """Stop sampling and surface any sampler failure.

        Returns:
            `None`:
                The sampling thread has stopped.
        """
        self._stop.set()
        self._thread.join()
        if self.error is not None:
            raise RuntimeError("Docker resource sampling failed") from self.error

    def _sample(self) -> None:
        """Poll Docker stats until stopped.

        Returns:
            `None`:
                Samples are appended to the instance.
        """
        try:
            while not self._stop.is_set():
                result = subprocess.run(
                    [
                        "docker",
                        "stats",
                        "--no-stream",
                        "--format",
                        "{{json .}}",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=max(15.0, self.interval_seconds * 5),
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        "docker stats failed: "
                        f"{result.stderr.strip() or result.stdout.strip()}",
                    )
                resources: dict[str, dict[str, float]] = {}
                for line in result.stdout.splitlines():
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    name = str(item.get("Name", "")).lstrip("/")
                    matched_groups = [
                        group
                        for group, prefix in self.group_to_container_prefix.items()
                        if name == prefix or name.startswith(f"{prefix}-")
                    ]
                    if not matched_groups:
                        continue
                    group = max(
                        matched_groups,
                        key=lambda candidate: len(
                            self.group_to_container_prefix[candidate],
                        ),
                    )
                    group_resources = resources.setdefault(
                        group,
                        {"cpu_cores": 0.0, "memory_gib": 0.0},
                    )
                    group_resources["cpu_cores"] += _parse_cpu_cores(
                        str(item["CPUPerc"]),
                    )
                    group_resources["memory_gib"] += _parse_memory_gib(
                        str(item["MemUsage"]),
                    )
                self.samples.append(
                    {
                        "timestamp_unix_s": time.time(),
                        "containers": resources,
                    },
                )
                self._stop.wait(self.interval_seconds)
        except BaseException as exc:  # Preserve background thread failures.
            self.error = exc
            self._stop.set()


def _load_timing_records(path: Path) -> list[dict[str, Any]]:
    """Load worker timing records from one JSONL file.

    Args:
        path (`Path`):
            Timing log path.

    Returns:
        `list[dict[str, Any]]`:
            Parsed worker timing records.
    """
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _event_epoch(
    record_started_at: str,
    elapsed_ms: Any,
    record_started_at_unix_s: float | None = None,
) -> float:
    """Convert worker-relative elapsed time to approximate Unix seconds.

    Args:
        record_started_at (`str`):
            Local timestamp at the start of a worker timing record.
        elapsed_ms (`Any`):
            Event elapsed time in milliseconds.
        record_started_at_unix_s (`float | None`, optional):
            Precise Unix start time when available.

    Returns:
        `float`:
            Approximate Unix timestamp in seconds.
    """
    if record_started_at_unix_s is None:
        started = datetime.strptime(record_started_at, "%Y-%m-%d %H:%M:%S")
        record_started_at_unix_s = time.mktime(started.timetuple())
    return record_started_at_unix_s + float(elapsed_ms or 0) / 1000.0


def _read_predictive_events(
    records: list[dict[str, Any]],
    repeat_id: int,
    started_at: str,
    finished_at: str,
    candidate_to_group: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    """Extract started predictive warmups and eligible demand requests.

    Args:
        records (`list[dict[str, Any]]`):
            Timing records from one session.
        repeat_id (`int`):
            One-based repetition index.
        started_at (`str`):
            Session start timestamp.
        finished_at (`str`):
            Session end timestamp.
        candidate_to_group (`dict[str, str] | None`, optional):
            Predictive candidate names mapped to runtime MCP group names.

    Returns:
        `tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]`:
            Warmups, eligible requests, and emitted prediction telemetry.
    """
    warmups: list[dict[str, Any]] = []
    demand_requests: list[dict[str, Any]] = []
    all_demand_requests: list[dict[str, Any]] = []
    prediction_events: list[dict[str, Any]] = []
    predictive_opportunities: list[float] = []
    candidate_to_group = candidate_to_group or {}

    def _resolve_group(candidate: str) -> str:
        """Map a predictor's server label to the runtime tool-group name."""
        return candidate_to_group.get(candidate, candidate)

    for record_index, record in enumerate(records):
        record_started_at = str(record.get("started_at", started_at))
        precise_started_at = record.get("started_at_unix_s")
        if not isinstance(precise_started_at, (int, float)):
            precise_started_at = None
        telemetry = record.get("prewarm_controller_telemetry") or {}
        controller_events = telemetry.get("events") or []
        predictive_opportunities.extend(
            float(event["ts"]) / 1000.0
            for event in controller_events
            if event.get("event") == "predict_candidates"
            and event.get("stage") == "predictive"
            and event.get("status") == "completed"
            and int(event.get("candidate_count") or 0) > 0
            and event.get("ts") is not None
        )
        schedule_by_candidate: dict[str, list[dict[str, Any]]] = {}
        executor_results: dict[str, list[dict[str, Any]]] = defaultdict(list)
        executor_result_offsets: dict[str, int] = defaultdict(int)
        for event in record.get("events") or []:
            if event.get("step") == "prewarm_candidate_finished":
                executor_results[str(event.get("candidate") or "")].append(
                    {
                        "effective": event.get("effective"),
                        "startup_mode": event.get("startup_mode"),
                    },
                )
        completion_results: dict[int, dict[str, Any]] = {}
        for event in controller_events:
            if (
                event.get("event") != "prewarm_executor"
                or event.get("status") != "completed"
            ):
                continue
            target = str(event.get("candidate") or "")
            offset = executor_result_offsets[target]
            if offset < len(executor_results[target]):
                completion_results[id(event)] = executor_results[target][offset]
                executor_result_offsets[target] += 1

        for event_index, event in enumerate(controller_events):
            if event.get("stage") != "predictive":
                continue
            target = str(event.get("candidate") or "").strip()
            if event.get("event") == "predict_candidates":
                prediction_events.append(
                    {
                        "repeat_id": repeat_id,
                        "record_index": record_index,
                        "event_index": event_index,
                        "timestamp_unix_ms": event.get("ts"),
                        "current_server": event.get("current_server"),
                        "status": event.get("status"),
                        "candidate_count": event.get("candidate_count", 0),
                    },
                )
            if event.get("event") == "prewarm_schedule" and target:
                schedule_by_candidate.setdefault(target, []).append(event)

        predictive_starts: dict[str, list[dict[str, Any]]] = {}
        for event_index, event in enumerate(controller_events):
            if (
                event.get("event") != "prewarm_executor"
                or event.get("stage") != "predictive"
                or event.get("status") != "started"
            ):
                continue
            target = str(event.get("candidate") or "").strip()
            if not target:
                continue
            timestamp = float(event.get("ts") or 0) / 1000.0
            schedules = schedule_by_candidate.get(target, [])
            preceding_schedule = next(
                (
                    item
                    for item in reversed(schedules)
                    if float(item.get("ts") or 0) <= float(event.get("ts") or 0)
                    and item.get("status") == "accepted"
                ),
                {},
            )
            warmup = {
                "repeat_id": repeat_id,
                "record_index": record_index,
                "target": _resolve_group(target),
                "candidate": target,
                "schedule_timestamp_unix_s": (
                    float(preceding_schedule["ts"]) / 1000.0
                    if preceding_schedule.get("ts") is not None
                    else None
                ),
                "schedule_timestamp": (
                    datetime.fromtimestamp(
                        float(preceding_schedule["ts"]) / 1000.0,
                    ).isoformat(timespec="milliseconds")
                    if preceding_schedule.get("ts") is not None
                    else ""
                ),
                "start_timestamp_unix_s": timestamp,
                "start_timestamp": datetime.fromtimestamp(timestamp).isoformat(
                    timespec="milliseconds",
                ),
                "ready_timestamp_unix_s": None,
                "ready_timestamp": "",
                "later_demand_use": False,
                "prefetch_hit": False,
                "prefetch_eligible_demand_use": False,
                "demand_timestamp_unix_s": None,
                "demand_timestamp": "",
                "discard_timestamp_unix_s": None,
                "discard_timestamp": "",
                "discard_timestamp_basis": "",
                "cpu_seconds": None,
                "memory_gib_seconds": None,
                "resource_measurement": "pending",
                "effective": None,
                "_executor_start_event_index": event_index,
            }
            warmups.append(warmup)
            predictive_starts.setdefault(target, []).append(warmup)

        for event in controller_events:
            if (
                event.get("event") != "prewarm_executor"
                or event.get("stage") != "predictive"
                or event.get("status") != "completed"
            ):
                continue
            target = str(event.get("candidate") or "").strip()
            pending = predictive_starts.get(target, [])
            ready = float(event.get("ts") or 0) / 1000.0
            match = next(
                (
                    item
                    for item in pending
                    if item["ready_timestamp_unix_s"] is None
                    and item["start_timestamp_unix_s"] <= ready
                ),
                None,
            )
            if match is not None:
                match["ready_timestamp_unix_s"] = ready
                match["ready_timestamp"] = datetime.fromtimestamp(ready).isoformat(
                    timespec="milliseconds",
                )
                result = completion_results.get(id(event), {})
                match["effective"] = result.get(
                    "effective",
                    event.get("effective"),
                )
                match["startup_mode"] = result.get(
                    "startup_mode",
                    event.get("startup_mode"),
                )
                if match["effective"] is None:
                    match["effective"] = match["startup_mode"] in {
                        "cold",
                        "resume",
                    }

        warmups = [
            warmup
            for warmup in warmups
            if warmup["effective"] is True
        ]

        activation_requests: dict[str, list[dict[str, Any]]] = {}
        for event_index, event in enumerate(record.get("events") or []):
            target = str(event.get("group_name") or "").strip()
            if event.get("step") == "tool_group_activation_requested":
                request_timestamp = _event_epoch(
                    record_started_at,
                    event.get("elapsed_ms"),
                    precise_started_at,
                )
                request = {
                    "repeat_id": repeat_id,
                    "record_index": record_index,
                    "event_index": event_index,
                    "target": target,
                    "request_timestamp_unix_s": request_timestamp,
                    "ready_timestamp_unix_s": None,
                    "startup_mode": "unknown",
                    "prefetch_hit": False,
                    "prefetch_eligible": False,
                }
                all_demand_requests.append(request)
                activation_requests.setdefault(target, []).append(request)
            elif event.get("step") == "mcp_server_ready":
                pending = activation_requests.get(target, [])
                if pending:
                    request = pending.pop(0)
                    request["ready_timestamp_unix_s"] = _event_epoch(
                        record_started_at,
                        event.get("elapsed_ms"),
                        precise_started_at,
                    )
                    request["startup_mode"] = str(
                        event.get("startup_mode") or "unknown",
                    )

    last_activation_timestamp = float("-inf")
    for demand in sorted(
        all_demand_requests,
        key=lambda item: item["request_timestamp_unix_s"],
    ):
        request_timestamp = demand["request_timestamp_unix_s"]
        demand["prefetch_eligible"] = any(
            last_activation_timestamp < prediction_timestamp <= request_timestamp
            for prediction_timestamp in predictive_opportunities
        )
        if demand["prefetch_eligible"]:
            demand_requests.append(demand)
        last_activation_timestamp = request_timestamp

    for demand in sorted(
        all_demand_requests,
        key=lambda item: item["request_timestamp_unix_s"],
    ):
        started_matches = [
            warmup
            for warmup in warmups
            if warmup["target"] == demand["target"]
            and warmup["start_timestamp_unix_s"]
            <= demand["request_timestamp_unix_s"]
            and (
                warmup["discard_timestamp_unix_s"] is None
                or warmup["discard_timestamp_unix_s"]
                >= demand["request_timestamp_unix_s"]
            )
        ]
        completed_matches = [
            warmup
            for warmup in started_matches
            if demand["request_timestamp_unix_s"] is not None
            and demand["startup_mode"] in {"running", "resume"}
            if warmup["ready_timestamp_unix_s"] is not None
            and warmup["ready_timestamp_unix_s"]
            <= demand["request_timestamp_unix_s"]
        ]
        eventual_matches = [
            warmup
            for warmup in started_matches
            if demand["ready_timestamp_unix_s"] is not None
            and demand["startup_mode"] in {"running", "resume"}
        ]
        selected = None
        if completed_matches:
            selected = max(
                completed_matches,
                key=lambda item: item["ready_timestamp_unix_s"],
            )
            demand["prefetch_hit"] = bool(demand["prefetch_eligible"])
        elif eventual_matches:
            selected = max(
                eventual_matches,
                key=lambda item: item["start_timestamp_unix_s"],
            )
            demand["prefetch_hit"] = False
        else:
            demand["prefetch_hit"] = False

        if selected is not None:
            selected["later_demand_use"] = True
            selected["prefetch_hit"] = bool(demand["prefetch_hit"])
            selected["prefetch_eligible_demand_use"] = bool(
                demand["prefetch_eligible"],
            )
            selected["demand_timestamp_unix_s"] = demand[
                "request_timestamp_unix_s"
            ]
            selected["demand_timestamp"] = datetime.fromtimestamp(
                demand["request_timestamp_unix_s"],
            ).isoformat(timespec="milliseconds")

        if demand["startup_mode"] == "cold":
            to_close = started_matches
        elif selected is not None:
            to_close = [
                warmup for warmup in started_matches if warmup is not selected
            ]
        else:
            to_close = []
        for warmup in to_close:
            if warmup["later_demand_use"]:
                continue
            warmup["discard_timestamp_unix_s"] = demand[
                "request_timestamp_unix_s"
            ]
            warmup["discard_timestamp"] = datetime.fromtimestamp(
                demand["request_timestamp_unix_s"],
            ).isoformat(timespec="milliseconds")
            warmup["discard_timestamp_basis"] = (
                "cold_demand_detected"
                if demand["startup_mode"] == "cold"
                else "superseded_by_used_warmup"
            )

    for warmup in warmups:
        if not warmup["later_demand_use"] and warmup["discard_timestamp_unix_s"] is None:
            warmup["discard_timestamp_unix_s"] = time.mktime(
                datetime.strptime(finished_at, "%Y-%m-%d %H:%M:%S").timetuple(),
            )
            warmup["discard_timestamp"] = finished_at
            warmup["discard_timestamp_basis"] = "forced_run_cleanup"
        if warmup["later_demand_use"]:
            warmup["resource_measurement"] = "not_applicable_warmup_was_used"
    return warmups, demand_requests, prediction_events


def _integrate_discarded_resources(
    warmups: list[dict[str, Any]],
    samples: list[dict[str, Any]],
    group_to_container: dict[str, str],
) -> None:
    """Estimate per-warmup CPU and memory integrals from sampled Docker stats.

    Args:
        warmups (`list[dict[str, Any]]`):
            Warmup lifecycle records to enrich.
        samples (`list[dict[str, Any]]`):
            Time-ordered per-group Docker resource samples.
        group_to_container (`dict[str, str]`):
            MCP group to base container-name mapping.

    Returns:
        `None`:
            Resource integrals are written into the warmup records.
    """
    discarded = [item for item in warmups if not item["later_demand_use"]]
    for item in discarded:
        item["cpu_seconds"] = 0.0
        item["memory_gib_seconds"] = 0.0
        item["resource_measurement"] = "docker_stats_sampled_estimate"

    for target in {item["target"] for item in discarded}:
        container = group_to_container.get(target)
        target_warmups = [item for item in discarded if item["target"] == target]
        if not container:
            for item in target_warmups:
                item["cpu_seconds"] = None
                item["memory_gib_seconds"] = None
                item["resource_measurement"] = "container_name_unavailable"
            continue

        relevant_samples = [
            (
                float(sample["timestamp_unix_s"]),
                sample["containers"].get(target),
            )
            for sample in samples
        ]
        available_pairs = [
            (left, right)
            for left, right in zip(relevant_samples, relevant_samples[1:])
            if left[1] is not None and right[1] is not None and right[0] > left[0]
        ]
        if not available_pairs:
            for item in target_warmups:
                item["cpu_seconds"] = None
                item["memory_gib_seconds"] = None
                item["resource_measurement"] = "insufficient_docker_samples"
            continue

        for left, right in available_pairs:
            interval_start, interval_end = left[0], right[0]
            duration = interval_end - interval_start
            midpoint = (interval_start + interval_end) / 2.0
            active = [
                item
                for item in target_warmups
                if item["start_timestamp_unix_s"] <= midpoint
                < float(item["discard_timestamp_unix_s"])
            ]
            if not active:
                continue
            share = 1.0 / len(active)
            for resource in ("cpu_cores", "memory_gib"):
                left_value = float(left[1][resource])
                right_value = float(right[1][resource])
                for item in active:
                    overlap_start = max(
                        interval_start,
                        item["start_timestamp_unix_s"],
                    )
                    overlap_end = min(
                        interval_end,
                        float(item["discard_timestamp_unix_s"]),
                    )
                    if overlap_end <= overlap_start:
                        continue
                    start_fraction = (overlap_start - interval_start) / duration
                    end_fraction = (overlap_end - interval_start) / duration
                    value_start = left_value + (right_value - left_value) * start_fraction
                    value_end = left_value + (right_value - left_value) * end_fraction
                    integral = (value_start + value_end) * 0.5 * (
                        overlap_end - overlap_start
                    ) * share
                    metric = (
                        "cpu_seconds"
                        if resource == "cpu_cores"
                        else "memory_gib_seconds"
                    )
                    item[metric] += integral


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    """Write a CSV with a stable schema.

    Args:
        path (`Path`):
            Output CSV path.
        fieldnames (`list[str]`):
            Ordered output columns.
        rows (`list[dict[str, Any]]`):
            Rows to serialize.

    Returns:
        `None`:
            The CSV file is written.
    """
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _persist_repeat_outputs(
    repeat_dir: Path,
    warmups: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> None:
    """Persist per-repeat data immediately for interruption recovery.

    Args:
        repeat_dir (`Path`):
            Output directory for one repetition.
        warmups (`list[dict[str, Any]]`):
            Extracted warmup records.
        predictions (`list[dict[str, Any]]`):
            Extracted predictive telemetry events.
        metrics (`dict[str, Any]`):
            Per-repeat summary fields.

    Returns:
        `None`:
            Per-repeat CSV, JSON, and JSONL files are written.
    """
    columns = [
        "repeat_id",
        "trace_id",
        "record_index",
        "target",
        "candidate",
        "schedule_timestamp",
        "start_timestamp",
        "ready_timestamp",
        "later_demand_use",
        "prefetch_hit",
        "demand_timestamp",
        "discard_timestamp",
        "discard_timestamp_basis",
        "cpu_seconds",
        "memory_gib_seconds",
        "resource_measurement",
    ]
    _write_csv(
        repeat_dir / "sdg_warmup_records.csv",
        columns,
        [{key: row.get(key, "") for key in columns} for row in warmups],
    )
    (repeat_dir / "sdg_repeat_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (repeat_dir / "sdg_predictive_events.jsonl").open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as stream:
        for event in predictions:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")


def _container_mapping(registrations: list[Any]) -> dict[str, str]:
    """Map configured MCP group names to Docker container names.

    Args:
        registrations (`list[Any]`):
            MCP registration configurations.

    Returns:
        `dict[str, str]`:
            Group names mapped to base container names.
    """
    mapping: dict[str, str] = {}
    for registration in registrations:
        config = getattr(registration, "server_config", None)
        container_name = getattr(config, "container_name", None)
        if container_name:
            mapping[str(registration.group_name)] = str(container_name).lstrip("/")
    return mapping


def _candidate_group_mapping(
    registrations: list[Any],
) -> dict[str, str]:
    """Map predictor aliases and Docker names back to runtime MCP groups."""
    mapping: dict[str, str] = {}
    for registration in registrations:
        group_name = str(registration.group_name)
        aliases = {
            str(getattr(registration, "server_name", "")).strip(),
            str(getattr(registration, "group_name", "")).strip(),
        }
        server_config = getattr(registration, "server_config", None)
        aliases.update(
            {
                str(getattr(server_config, "client_name", "")).strip(),
                str(getattr(server_config, "container_name", "")).strip(),
            },
        )
        for alias in aliases:
            if alias:
                mapping[alias] = group_name
    return mapping


def _run_experiments(args: argparse.Namespace) -> Path:
    """Run repetitions and write raw records and aggregate overhead results."""
    if args.repeats < 1:
        raise ValueError("--repeats must be >= 1")
    if args.sample_interval <= 0:
        raise ValueError("--sample-interval must be > 0")
    if args.top_k < 1:
        raise ValueError("--top-k must be >= 1")
    if args.transition_matrix and not Path(args.transition_matrix).is_file():
        raise FileNotFoundError(args.transition_matrix)
    if not os.environ.get("DASHSCOPE_API_KEY"):
        raise RuntimeError("DASHSCOPE_API_KEY must be set before running the experiment.")
    trace_suite: list[dict[str, Any]] | None = None
    if args.trace_suite_manifest:
        suite_path = Path(args.trace_suite_manifest).expanduser().resolve()
        suite_payload = json.loads(suite_path.read_text(encoding="utf-8"))
        trace_suite = suite_payload.get("cases")
        if not isinstance(trace_suite, list) or not trace_suite:
            raise ValueError(f"Trace suite manifest has no cases: {suite_path}")
        if len(trace_suite) != args.repeats:
            raise ValueError(
                f"--repeats ({args.repeats}) must match trace suite case count "
                f"({len(trace_suite)}).",
            )
        seen_trace_ids: set[str] = set()
        for case in trace_suite:
            if not isinstance(case, dict):
                raise ValueError("Each trace suite case must be a JSON object.")
            trace_id = str(case.get("trace_id", "")).strip()
            script = Path(str(case.get("turn_script", ""))).expanduser()
            if not trace_id or trace_id in seen_trace_ids:
                raise ValueError(f"Invalid or duplicate trace_id: {trace_id!r}")
            if not script.is_absolute():
                script = suite_path.parent / script
            if not script.is_file():
                raise FileNotFoundError(script)
            case["turn_script"] = str(script.resolve())
            seen_trace_ids.add(trace_id)
        suite_groups = sorted(
            {
                str(group).strip()
                for case in trace_suite
                for group in case.get("group_path", [])
                if str(group).strip()
            },
        )
        if suite_groups:
            os.environ["AGENTSCOPE_EXPERIMENT_SERVER_NAMES"] = json.dumps(
                suite_groups,
                ensure_ascii=False,
            )
    else:
        turn_script = Path(args.turn_script).expanduser().resolve()
        if not turn_script.is_file():
            raise FileNotFoundError(turn_script)
    subprocess.run(["docker", "info"], check=True, capture_output=True, text=True)

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise FileExistsError(
            f"Output directory is not empty; choose a new --output-dir: {output_dir}",
        )

    registrations = _runner._load_experiment_registrations()
    group_to_container = _container_mapping(registrations)
    candidate_to_group = _candidate_group_mapping(registrations)
    if not group_to_container:
        raise ValueError("No Docker container names found in MCP registrations.")
    temp_dir = _runner._ensure_temp_file_dir()
    timing_basename = (
        f"sdg_overhead_timing_{datetime.now().strftime('%Y%m%d_%H%M%S')}_"
        f"{os.getpid()}.jsonl"
    )
    os.environ["AGENTSCOPE_TIMING_LOG_BASENAME"] = timing_basename

    all_warmups: list[dict[str, Any]] = []
    all_prediction_events: list[dict[str, Any]] = []
    repeat_rows: list[dict[str, Any]] = []
    summary_path = output_dir / "sdg_accuracy_overhead_summary.json"

    for repeat_id in range(1, args.repeats + 1):
        repeat_dir = output_dir / f"repeat_{repeat_id:02d}"
        repeat_dir.mkdir()
        timing_path = temp_dir / timing_basename
        trace_case = trace_suite[repeat_id - 1] if trace_suite else None
        repeat_script = (
            Path(trace_case["turn_script"])
            if trace_case
            else turn_script
        )
        trace_id = str(trace_case["trace_id"]) if trace_case else ""
        sampler = _DockerStatsSampler(group_to_container, args.sample_interval)
        sampler.start()
        print(
            f"Starting {args.mode} overhead repeat {repeat_id}/{args.repeats}"
            + (f" ({trace_id})" if trace_id else ""),
            flush=True,
        )
        try:
            with _runner._temporary_cwd(_AGENT_DIR):
                payload = _runner.run_once(
                    mode=args.mode,
                    output_dir=repeat_dir,
                    model_name=args.model_name,
                    planner_max_iters=args.planner_max_iters,
                    stream_interval_tokens=args.stream_interval_tokens,
                    turn_script_file=str(repeat_script),
                    predictive_top_k=args.top_k,
                    predictive_transition_matrix_path=args.transition_matrix,
                )
        except BaseException as exc:
            sampler.stop()
            if timing_path.is_file():
                (repeat_dir / "worker_timing_partial.jsonl").write_bytes(
                    timing_path.read_bytes(),
                )
            partial_samples = []
            for sample in sampler.samples:
                for group, resources in sample["containers"].items():
                    partial_samples.append(
                        {
                            "timestamp_unix_s": sample["timestamp_unix_s"],
                            "target_group": group,
                            **resources,
                        },
                    )
            _write_csv(
                repeat_dir / "docker_stats_samples_partial.csv",
                [
                    "timestamp_unix_s",
                    "target_group",
                    "cpu_cores",
                    "memory_gib",
                ],
                partial_samples,
            )
            (repeat_dir / "repeat_failure.json").write_text(
                json.dumps(
                    {
                        "repeat_id": repeat_id,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            raise
        else:
            sampler.stop()

        retained_timing = repeat_dir / "worker_timing.jsonl"
        if timing_path.is_file():
            retained_timing.write_bytes(timing_path.read_bytes())
        else:
            raise FileNotFoundError(
                f"Expected worker timing log was not produced: {timing_path}",
            )

        records = _load_timing_records(retained_timing)
        finished_at = str(payload["finished_at"])
        warmups, demands, predictions = _read_predictive_events(
            records,
            repeat_id,
            str(payload["started_at"]),
            finished_at,
            candidate_to_group=candidate_to_group,
        )
        for row in warmups:
            row["trace_id"] = trace_id
        _integrate_discarded_resources(warmups, sampler.samples, group_to_container)

        samples_path = repeat_dir / "docker_stats_samples.csv"
        sample_rows = []
        for sample in sampler.samples:
            for container, resources in sample["containers"].items():
                sample_rows.append(
                    {
                        "timestamp_unix_s": sample["timestamp_unix_s"],
                        "target_group": container,
                        **resources,
                    },
                )
        _write_csv(
            samples_path,
            ["timestamp_unix_s", "target_group", "cpu_cores", "memory_gib"],
            sample_rows,
        )

        all_warmups.extend(warmups)
        all_prediction_events.extend(predictions)
        accepted_targets = {
            str(event.get("candidate"))
            for record in records
            for event in (record.get("prewarm_controller_telemetry") or {}).get(
                "events",
                [],
            )
            if event.get("event") == "prewarm_schedule"
            and event.get("stage") == "predictive"
            and event.get("status") == "accepted"
            and event.get("candidate")
        }
        discarded = [item for item in warmups if not item["later_demand_use"]]
        cpu_values = [item["cpu_seconds"] for item in discarded if item["cpu_seconds"] is not None]
        memory_values = [
            item["memory_gib_seconds"]
            for item in discarded
            if item["memory_gib_seconds"] is not None
        ]
        cpu_complete = len(cpu_values) == len(discarded)
        memory_complete = len(memory_values) == len(discarded)
        eligible_demand_count = len(demands)
        hit_count = sum(
            1
            for demand in demands
            if demand.get("prefetch_hit")
        )
        run_metrics = payload.get("metrics") or {}
        if trace_case:
            run_metrics["trace_id"] = trace_id
            run_metrics["trace_server_path"] = trace_case.get("server_path", [])
        repeat_rows.append(
            {
                "repeat_id": repeat_id,
                "top_k": args.top_k,
                "trace_id": trace_id,
                "trace_server_path": json.dumps(
                    trace_case.get("server_path", []) if trace_case else [],
                    ensure_ascii=False,
                ),
                "workload_script": str(repeat_script),
                "status": "completed",
                "started_at": payload["started_at"],
                "finished_at": finished_at,
                "worker_calls": run_metrics.get("worker_calls"),
                "e2e_elapsed_ms": run_metrics.get("e2e_elapsed_ms"),
                "avg_wait_ms": run_metrics.get("avg_wait_ms"),
                "p50_wait_ms": run_metrics.get("p50_wait_ms"),
                "p95_wait_ms": run_metrics.get("p95_wait_ms"),
                "cold_starts": run_metrics.get("cold_starts"),
                "worker_records": len(records),
                "prediction_calls": sum(
                    1 for event in predictions
                ),
                "predictive_schedule_targets": len(accepted_targets),
                "started_predictive_warmups": len(warmups),
                "eligible_sandbox_requests": eligible_demand_count,
                "prefetch_hits": hit_count,
                "late_warmups_used": sum(
                    1
                    for item in warmups
                    if item["prefetch_eligible_demand_use"]
                    and not item["prefetch_hit"]
                ),
                "prefetch_hit_rate": (
                    hit_count / eligible_demand_count
                    if eligible_demand_count
                    else ""
                ),
                "discarded_warmups": len(discarded),
                "discarded_cpu_seconds": sum(cpu_values) if cpu_complete else "",
                "discarded_cpu_resource_complete": cpu_complete,
                "discarded_cpu_resource_records": len(cpu_values),
                "discarded_memory_gib_seconds": (
                    sum(memory_values) if memory_complete else ""
                ),
                "discarded_memory_resource_complete": memory_complete,
                "discarded_memory_resource_records": len(memory_values),
                "false_positives": len(discarded),
                "false_positive_rate": (
                    len(discarded) / len(warmups) if warmups else ""
                ),
                "run_json": str(Path(payload["artifact_path"]).relative_to(output_dir)),
                "worker_timing_jsonl": str(retained_timing.relative_to(output_dir)),
                "docker_stats_csv": str(samples_path.relative_to(output_dir)),
            },
        )
        _persist_repeat_outputs(
            repeat_dir,
            warmups,
            predictions,
            repeat_rows[-1],
        )
        print(
            f"Finished repeat {repeat_id}/{args.repeats}: "
            f"{len(warmups)} started SDG warmups, {len(discarded)} discarded",
            flush=True,
        )

    warmup_columns = [
        "repeat_id",
        "trace_id",
        "record_index",
        "target",
        "candidate",
        "schedule_timestamp",
        "start_timestamp",
        "ready_timestamp",
        "later_demand_use",
        "prefetch_hit",
        "demand_timestamp",
        "discard_timestamp",
        "discard_timestamp_basis",
        "cpu_seconds",
        "memory_gib_seconds",
        "resource_measurement",
    ]
    _write_csv(
        output_dir / "sdg_warmup_records.csv",
        warmup_columns,
        [
            {key: row.get(key, "") for key in warmup_columns}
            for row in all_warmups
        ],
    )
    _write_csv(
        output_dir / "sdg_accuracy_overhead_by_repeat.csv",
        list(repeat_rows[0].keys()) if repeat_rows else [],
        repeat_rows,
    )
    with (output_dir / "sdg_predictive_events.jsonl").open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as stream:
        for event in all_prediction_events:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")

    started_total = sum(int(row["started_predictive_warmups"]) for row in repeat_rows)
    discarded_total = sum(int(row["discarded_warmups"]) for row in repeat_rows)
    late_warmups_total = sum(
        int(row["late_warmups_used"])
        for row in repeat_rows
    )
    eligible_total = sum(int(row["eligible_sandbox_requests"]) for row in repeat_rows)
    hit_total = sum(int(row["prefetch_hits"]) for row in repeat_rows)
    cpu_resource_count = sum(int(row["discarded_cpu_resource_records"]) for row in repeat_rows)
    memory_resource_count = sum(
        int(row["discarded_memory_resource_records"]) for row in repeat_rows
    )
    cpu_complete_sessions = sum(
        bool(row["discarded_cpu_resource_complete"]) for row in repeat_rows
    )
    memory_complete_sessions = sum(
        bool(row["discarded_memory_resource_complete"]) for row in repeat_rows
    )
    cpu_total_complete = sum(
        float(row["discarded_cpu_seconds"])
        for row in repeat_rows
        if row["discarded_cpu_resource_complete"]
    )
    memory_total_complete = sum(
        float(row["discarded_memory_gib_seconds"])
        for row in repeat_rows
        if row["discarded_memory_resource_complete"]
    )
    total_sessions = len(repeat_rows)
    performance_fields = (
        "worker_calls",
        "e2e_elapsed_ms",
        "avg_wait_ms",
        "p50_wait_ms",
        "p95_wait_ms",
        "cold_starts",
    )
    performance_means = {}
    for field in performance_fields:
        values = [
            float(row[field])
            for row in repeat_rows
            if isinstance(row.get(field), (int, float))
        ]
        performance_means[field] = {
            "mean_per_session": (
                statistics.mean(values)
                if values
                else None
            ),
            "sessions_with_value": len(values),
        }
    summary = {
        "status": "complete" if total_sessions == args.repeats else "incomplete",
        "predictive_top_k": args.top_k,
        "transition_matrix": args.transition_matrix,
        "repeats_requested": args.repeats,
        "sessions_completed": total_sessions,
        "workload_script": (
            str(Path(args.trace_suite_manifest).expanduser().resolve())
            if trace_suite
            else str(turn_script)
        ),
        "trace_suite_case_count": len(trace_suite) if trace_suite else None,
        "mode": args.mode,
        "model_name": args.model_name,
        "planner_max_iters": args.planner_max_iters,
        "stream_interval_tokens": args.stream_interval_tokens,
        "performance_means": performance_means,
        "prefetch_hit_rate": hit_total / eligible_total if eligible_total else None,
        "prefetch_hit_rate_numerator": hit_total,
        "prefetch_hit_rate_denominator_eligible_sandbox_requests": eligible_total,
        "false_positive_rate": (
            discarded_total / started_total if started_total else None
        ),
        "false_positive_rate_numerator_discarded_started_warmups": discarded_total,
        "false_positive_rate_denominator_started_warmups": started_total,
        "late_warmups_used_total": late_warmups_total,
        "late_warmups_used_per_session": (
            late_warmups_total / total_sessions
            if total_sessions
            else None
        ),
        "discarded_warmups_per_session": discarded_total / total_sessions
        if total_sessions
        else None,
        "discarded_warmup_cpu_seconds_per_session": (
            cpu_total_complete / total_sessions
            if total_sessions and cpu_complete_sessions == total_sessions
            else None
        ),
        "discarded_warmup_memory_gib_seconds_per_session": (
            memory_total_complete / total_sessions
            if total_sessions and memory_complete_sessions == total_sessions
            else None
        ),
        "cpu_resource_sessions_complete": cpu_complete_sessions,
        "memory_resource_sessions_complete": memory_complete_sessions,
        "cpu_observed_mean_per_complete_session": (
            cpu_total_complete / cpu_complete_sessions
            if cpu_complete_sessions
            else None
        ),
        "memory_observed_mean_per_complete_session": (
            memory_total_complete / memory_complete_sessions
            if memory_complete_sessions
            else None
        ),
        "cpu_resource_records_available": cpu_resource_count,
        "memory_resource_records_available": memory_resource_count,
        "resource_measurement": (
            "CPU and memory are estimated by trapezoidal integration of Docker "
            "stats samples for all base and request-scoped containers matching "
            "the MCP target group. Integration starts at warmup start and ends "
            "at the detected cold-demand/supersession boundary or forced run "
            "cleanup. Overlapping discarded warmups for one group split that "
            "group's sampled integral equally. Samples are taken at the "
            "configured interval; attribution is estimated at group/container "
            "level, not directly measured per warmup process."
        ),
        "lifecycle_accounting": (
            "A started predictive executor counts as a warmup only if its executor "
            "created or resumed a container (effective=true). It is marked used "
            "when a later demand for the same MCP group reaches a running/resume "
            "ready state after that warmup started. A hit additionally requires "
            "the warmup to be ready before the demand activation began. Thus a "
            "late-but-used warmup is not counted as a false positive. Discard "
            "timestamps are detected boundaries, not directly observed Docker "
            "removal timestamps."
        ),
        "attribution_limitations": (
            "C1 prompt/stream prewarming is disabled in c2_only mode. In c1_c2 "
            "mode, if both mechanisms target the same MCP group, timing and "
            "group-level Docker stats cannot causally separate their contribution."
        ),
        "hit_rate_accounting": (
            "The denominator is every tool_group_activation_requested event "
            "preceded, since the prior sandbox activation in the same worker "
            "record, by a completed predictive-stage predict_candidates event "
            "with candidate_count > 0. The requested group need not match a "
            "predicted candidate, so wrong-target predictions count as misses. "
            "A hit requires an effective predictive executor for the requested "
            "group and a running/resume ready event after warmup completion and "
            "before the activation."
        ),
        "aggregation": (
            "Hit and false-positive rates pool numerators and denominators across "
            "completed sessions. Per-session discarded counts and resource "
            "integrals are pooled totals divided by completed sessions. Resource "
            "means include zero-cost sessions with no discarded warmups; records "
            "missing sufficient Docker samples are counted separately."
        ),
        "resource_session_completeness": {
            "cpu": cpu_complete_sessions,
            "memory": memory_complete_sessions,
            "total_sessions": total_sessions,
            "paper_table_values_are_null_unless_all_sessions_are_measured": True,
        },
        "files": {
            "warmup_records": "sdg_warmup_records.csv",
            "repeat_summary": "sdg_accuracy_overhead_by_repeat.csv",
            "prediction_events": "sdg_predictive_events.jsonl",
        },
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    timing_path.unlink(missing_ok=True)
    print(f"Summary: {summary_path}")
    return output_dir


def _build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser.

    Returns:
        `argparse.ArgumentParser`:
            Parser for experiment options.
    """
    parser = argparse.ArgumentParser(
        description="Run repeated SDG prefetch overhead measurements.",
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument(
        "--output-dir",
        default=str(_THIS_DIR / f"sdg_overhead_{timestamp}"),
    )
    parser.add_argument("--turn-script", default=str(_DEFAULT_TURN_SCRIPT))
    parser.add_argument(
        "--trace-suite-manifest",
        help=(
            "JSON manifest containing one turn-script path per repeat; the "
            "case count must equal --repeats."
        ),
    )
    parser.add_argument("--model-name", default="qwen3.8-flash")
    parser.add_argument("--planner-max-iters", type=int, default=20)
    parser.add_argument("--stream-interval-tokens", type=int, default=20)
    parser.add_argument("--sample-interval", type=float, default=1.0)
    parser.add_argument("--top-k", type=int, default=1)
    parser.add_argument(
        "--transition-matrix",
        help="Optional SDG transition matrix JSON path.",
    )
    parser.add_argument(
        "--mode",
        choices=_runner._MODE_CHOICES,
        default=_runner._MODE_C2_ONLY,
    )
    return parser


def _main() -> None:
    """Run the command-line experiment.

    Returns:
        `None`:
            Experiment outputs are written to the selected directory.
    """
    args = _build_parser().parse_args()
    _run_experiments(args)


if __name__ == "__main__":
    _main()
