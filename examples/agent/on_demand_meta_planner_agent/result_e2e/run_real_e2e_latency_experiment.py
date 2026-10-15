# -*- coding: utf-8 -*-
"""Run real (non-simulated) E2E QPS stress tests for paper experiments.

This script executes real planner/worker calls with model inference and tool
activation under concurrent QPS waves. It supports three runtimes:
- on_demand
- laplace
- always_on

Default setup follows the requested local paper protocol:
- sample-size = 20 (from SDG traces)
- seed = 0
- qps range = 1..20
- repeats per qps = 10

Outputs include:
- per-request real E2E and cumulative tool provisioning latency
- per-wave host CPU/memory usage
- aggregated scalability/resource metrics by mode and QPS
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import importlib
import importlib.util
import json
import math
import re
import os
import random
import socket
import statistics
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.mcp import (
    MCPLaplaceController,
    MCPLaplaceControllerConfig,
    MCPPrewarmHybridRouter,
    _ensure_local_docker_mcp_server,
    build_mcp_speculative_executor,
    load_laplace_registration_configs,
)
from agentscope.message import Msg
from agentscope.model import DashScopeChatModel
from agentscope.plan import PlanNotebook
from agentscope.tool import Toolkit

_THIS_DIR = Path(__file__).resolve().parent
_AGENT_DIR = _THIS_DIR.parent
if str(_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENT_DIR))


def _load_request_scope_helper() -> Any:
    """Load the local request-scope helper by file path."""
    helper_path = _AGENT_DIR / "_mcp_request_scope.py"
    spec = importlib.util.spec_from_file_location(
        "agentscope_request_scope_helper",
        helper_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load request-scope helper: {helper_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_REQUEST_SCOPE_HELPER = _load_request_scope_helper()
build_request_namespace = _REQUEST_SCOPE_HELPER.build_request_namespace
build_request_port = _REQUEST_SCOPE_HELPER.build_request_port
cleanup_scoped_containers = _REQUEST_SCOPE_HELPER.cleanup_scoped_containers
get_request_namespace = _REQUEST_SCOPE_HELPER.get_request_namespace
get_request_port = _REQUEST_SCOPE_HELPER.get_request_port
scope_registration_configs = _REQUEST_SCOPE_HELPER.scope_registration_configs

_DEFAULT_TRACES_JSON = (
    _THIS_DIR.parent.parent.parent.parent / "laplace" / "mcp_dataset" / "laplace_sdg_traces.json"
)
_DEFAULT_OUTPUT_DIR = _THIS_DIR

_MODE_ON_DEMAND = "on_demand"
_MODE_LAPLACE = "laplace"
_MODE_ALWAYS_ON = "always_on"
_MODE_CHOICES = (_MODE_ON_DEMAND, _MODE_LAPLACE, _MODE_ALWAYS_ON)
_ALWAYS_ON_IDLE_STOP_SECONDS = 60.0 * 60.0 * 24.0
_ALWAYS_ON_IDLE_REMOVE_SECONDS = 60.0 * 60.0 * 48.0


@dataclass(frozen=True)
class TraceRequest:
    """One sampled trace request."""

    trace_id: str
    user_request: str
    source_server_scope: tuple[str, ...] = ()
    execution_steps: tuple[tuple[str, str, str], ...] = ()


class _ResourceMonitor:
    """Sample host CPU/memory usage during a wave."""

    def __init__(self, interval_seconds: float = 0.2) -> None:
        self.interval_seconds = max(0.05, float(interval_seconds))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._cpu_percent_samples: list[float] = []
        self._mem_used_gib_samples: list[float] = []
        self._mem_percent_samples: list[float] = []
        self._cpu_count = float(os.cpu_count() or 1)

        try:
            import psutil  # type: ignore

            self._psutil = psutil
        except Exception:
            self._psutil = None

    def start(self) -> None:
        """Start background sampling."""
        if self._psutil is None:
            return

        # Prime cpu_percent to avoid the first-call 0.0 artifact.
        self._psutil.cpu_percent(interval=None)

        def _run() -> None:
            while not self._stop.is_set():
                cpu_percent = float(self._psutil.cpu_percent(interval=None))
                vm = self._psutil.virtual_memory()
                mem_used_gib = float(vm.used) / (1024.0**3)
                mem_percent = float(vm.percent)

                self._cpu_percent_samples.append(cpu_percent)
                self._mem_used_gib_samples.append(mem_used_gib)
                self._mem_percent_samples.append(mem_percent)

                self._stop.wait(self.interval_seconds)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self) -> dict[str, float | None]:
        """Stop sampling and return wave resource metrics."""
        if self._thread is not None:
            self._stop.set()
            self._thread.join(timeout=2.0)

        if not self._cpu_percent_samples:
            return {
                "cpu_avg_cores": None,
                "cpu_peak_cores": None,
                "cpu_avg_percent": None,
                "cpu_peak_percent": None,
                "memory_avg_gib": None,
                "memory_peak_gib": None,
                "memory_avg_percent": None,
                "memory_peak_percent": None,
            }

        cpu_avg_percent = statistics.mean(self._cpu_percent_samples)
        cpu_peak_percent = max(self._cpu_percent_samples)
        cpu_avg_cores = self._cpu_count * cpu_avg_percent / 100.0
        cpu_peak_cores = self._cpu_count * cpu_peak_percent / 100.0

        return {
            "cpu_avg_cores": round(cpu_avg_cores, 6),
            "cpu_peak_cores": round(cpu_peak_cores, 6),
            "cpu_avg_percent": round(cpu_avg_percent, 6),
            "cpu_peak_percent": round(cpu_peak_percent, 6),
            "memory_avg_gib": round(statistics.mean(self._mem_used_gib_samples), 6),
            "memory_peak_gib": round(max(self._mem_used_gib_samples), 6),
            "memory_avg_percent": round(statistics.mean(self._mem_percent_samples), 6),
            "memory_peak_percent": round(max(self._mem_percent_samples), 6),
        }


def _stable_seed(seed: int, key: str) -> int:
    """Generate deterministic per-key seed."""
    digest = hashlib.sha256(f"{seed}:{key}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _normalize_api_seed(seed: int) -> int:
    """Normalize seed into a stable positive integer for model APIs."""
    return int(seed % (2**31 - 1)) + 1


def _quantile(sorted_values: list[float], q: float) -> float:
    """Compute nearest-rank quantile."""
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, max(0, int(math.ceil(q * len(sorted_values))) - 1))
    return float(sorted_values[index])


def _load_trace_requests(traces_json: Path, sample_size: int, seed: int) -> list[TraceRequest]:
    """Sample fixed trace requests from SDG traces."""
    payload = json.loads(traces_json.read_text(encoding="utf-8"))
    traces = list(payload.get("traces", []))
    if sample_size > len(traces):
        raise ValueError(
            f"sample_size={sample_size} is larger than available traces={len(traces)}",
        )

    rng = random.Random(seed)
    sampled = rng.sample(traces, sample_size)

    requests: list[TraceRequest] = []
    for trace in sampled:
        user_request = str(trace.get("user_request", "")).strip()
        if not user_request:
            continue

        execution_trace = list(trace.get("execution_trace", []))
        execution_steps: list[tuple[str, str, str]] = []
        for step in execution_trace:
            server_name = str(step.get("server_name", "")).strip()
            tool_name = str(step.get("tool_name", "")).strip()
            intent = str(step.get("intent", "")).strip()
            if server_name or tool_name or intent:
                execution_steps.append((server_name, tool_name, intent))

        source_server_scope = tuple(
            str(name)
            for name in trace.get("source_server_scope", [])
            if str(name).strip()
        )
        if not source_server_scope:
            source_server_scope = tuple(
                sorted(
                    {
                        server_name
                        for server_name, _, _ in execution_steps
                        if server_name
                    },
                ),
            )

        requests.append(
            TraceRequest(
                trace_id=str(trace.get("trace_id", "unknown")),
                user_request=user_request,
                source_server_scope=source_server_scope,
                execution_steps=tuple(execution_steps),
            ),
        )

    if not requests:
        raise ValueError("No non-empty user_request found in sampled traces")
    return requests


def _trace_required_server_names(trace: TraceRequest) -> set[str] | None:
    """Resolve server-name allowlist for one trace request."""
    names = {name for name in trace.source_server_scope if str(name).strip()}
    for server_name, _, _ in trace.execution_steps:
        if server_name:
            names.add(server_name)
    return names or None


def _build_trace_replay_instruction(trace: TraceRequest) -> str:
    """Build strict replay instruction from SDG execution_trace."""
    if not trace.execution_steps:
        return ""

    lines = [
        f"Trace ID: {trace.trace_id}",
        "Strict replay constraints:",
        "1. You must execute tool calls aligned with the trace steps below.",
        "2. Do not switch to clarification-only replies; execute the listed tool flow.",
        "3. Use available servers/tools from the trace scope only.",
        "Trace steps:",
    ]
    for index, (server_name, tool_name, intent) in enumerate(trace.execution_steps, start=1):
        lines.append(
            f"- step {index}: server={server_name or 'unknown'}, "
            f"tool={tool_name or 'unknown'}, intent={intent or 'unknown'}"
        )
    return "\n".join(lines)


def _resolve_required_server_names_from_env() -> set[str] | None:
    """Resolve optional server-name allowlist from environment."""
    raw = os.getenv("AGENTSCOPE_EXPERIMENT_SERVER_NAMES", "").strip()
    if not raw:
        return None

    try:
        payload = json.loads(raw)
        if isinstance(payload, list):
            values = {
                str(item).strip()
                for item in payload
                if str(item).strip()
            }
            return values or None
    except Exception:
        pass

    values = {part.strip() for part in raw.split(",") if part.strip()}
    return values or None


def _load_experiment_registrations(
    required_server_names: set[str] | None = None,
) -> list[Any]:
    """Load experiment MCP registrations used by workers."""
    all_registrations = load_laplace_registration_configs()
    if required_server_names is None:
        required_server_names = _resolve_required_server_names_from_env()

    registrations = [
        reg
        for reg in all_registrations.values()
        if (
            required_server_names is None
            or str(getattr(reg, "server_name", "") or "")
            in required_server_names
        )
    ]
    if "GITHUB_PERSONAL_ACCESS_TOKEN" not in os.environ:
        registrations = [reg for reg in registrations if reg.group_name != "github_tools"]
    if not registrations:
        raise ValueError("No MCP registrations matched the selected trace server scope.")
    return registrations


def _resolve_repo_root() -> Path:
    """Resolve repository root."""
    return _AGENT_DIR.parents[2]


def _resolve_mcp_lifecycle_dir() -> Path:
    """Resolve lifecycle state directory used by MCP helper daemon."""
    configured = os.getenv("AGENTSCOPE_MCP_LIFECYCLE_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _resolve_repo_root() / "laplace" / "mcp_lifecycle"


def _cleanup_experiment_mcp_runtime(registrations: list[Any]) -> None:
    """Force-remove experiment MCP containers and lifecycle states."""
    container_names = sorted(
        {
            str(reg.server_config.container_name)
            for reg in registrations
            if getattr(reg, "server_config", None) is not None
        },
    )

    for container_name in container_names:
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
            )
        except subprocess.TimeoutExpired:
            pass

    lifecycle_dir = _resolve_mcp_lifecycle_dir()
    if lifecycle_dir.exists():
        for container_name in container_names:
            safe_name = container_name.replace(os.sep, "_").replace(":", "_")
            state_file = lifecycle_dir / f"{safe_name}.json"
            if state_file.exists():
                state_file.unlink()


def _cleanup_request_scoped_mcp_runtime(
    registrations: list[Any],
    request_rows: list[dict[str, Any]],
) -> None:
    """Force-remove request-scoped containers for one completed wave."""
    for row in request_rows:
        namespace = str(row.get("mcp_container_namespace", "")).strip()
        if not namespace:
            continue
        port_value = row.get("mcp_container_port")
        port = int(port_value) if isinstance(port_value, (int, float)) else None
        scoped_registrations = scope_registration_configs(registrations, namespace, port)
        cleanup_scoped_containers(scoped_registrations)


def _cleanup_request_scoped_temp_root(
    temp_root: Path,
    registrations: list[Any],
) -> None:
    """Remove leftover request-scoped containers discovered from temp dirs."""
    if not temp_root.exists():
        return

    pattern = re.compile(
        r"^(?P<mode>[^_]+)_qps(?P<qps>\d+)_r(?P<repeat>\d+)_req(?P<request>\d+)_",
    )
    for child in temp_root.iterdir():
        if not child.is_dir():
            continue
        match = pattern.match(child.name)
        if match is None:
            continue

        mode = match.group("mode")
        qps = int(match.group("qps"))
        repeat_id = int(match.group("repeat"))
        request_id = int(match.group("request"))
        namespace = child.name
        port = build_request_port(mode, qps, repeat_id, request_id)
        scoped_registrations = scope_registration_configs(registrations, namespace, port)
        cleanup_scoped_containers(scoped_registrations)


async def _ensure_experiment_mcp_runtime(registrations: list[Any]) -> None:
    """Ensure experiment MCP containers are running (always_on warmup)."""
    for index, reg in enumerate(registrations):
        try:
            await _ensure_local_docker_mcp_server(
                config=reg.server_config,
                docker_run_command=reg.docker_run_command,
                headers=reg.headers,
            )
        except RuntimeError as exc:
            # Docker occasionally leaves stale port allocation state for a scoped
            # container between waves; clean the target container and retry once.
            if "port is already allocated" not in str(exc).lower():
                raise

            cleanup_scoped_containers([reg])
            rebound_reg = reg
            last_exc: RuntimeError | None = None
            for _ in range(6):
                rebound_port = _pick_free_host_port()
                rebound_reg = _rebind_registration_host_port(reg, rebound_port)
                try:
                    await _ensure_local_docker_mcp_server(
                        config=rebound_reg.server_config,
                        docker_run_command=rebound_reg.docker_run_command,
                        headers=rebound_reg.headers,
                    )
                    registrations[index] = rebound_reg
                    last_exc = None
                    break
                except RuntimeError as retry_exc:
                    last_exc = retry_exc
                    if "port is already allocated" not in str(retry_exc).lower():
                        raise
                    cleanup_scoped_containers([rebound_reg])

            if last_exc is not None:
                raise last_exc


def _pick_free_host_port(start_port: int = 40000, end_port: int = 62000) -> int:
    """Pick a currently bindable host TCP port in a safe high range."""
    for _ in range(200):
        port = random.randint(int(start_port), int(end_port))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    raise RuntimeError("Unable to find a free host port for MCP container retry")


def _rebind_registration_host_port(registration: Any, port: int) -> Any:
    """Clone one registration with the same names but a different host port."""
    scoped_server_config = replace(
        registration.server_config,
        url=_rewrite_url_port(registration.server_config.url, port),
    )
    scoped_docker_run_command = _rewrite_docker_run_command_host_port(
        list(registration.docker_run_command),
        port,
    )
    return replace(
        registration,
        server_config=scoped_server_config,
        docker_run_command=scoped_docker_run_command,
    )


def _rewrite_url_port(url: str, port: int) -> str:
    """Rewrite URL host port while preserving scheme/path/query."""
    parts = urlsplit(url)
    host = parts.hostname or "localhost"
    netloc = f"{host}:{int(port)}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _rewrite_docker_run_command_host_port(
    docker_run_command: list[str],
    port: int,
) -> list[str]:
    """Rewrite host side of docker '-p host:container' mapping."""
    updated = list(docker_run_command)
    for index, item in enumerate(updated):
        if item != "-p" or index + 1 >= len(updated):
            continue
        mapping = str(updated[index + 1])
        if ":" not in mapping:
            continue
        _, container_port = mapping.split(":", maxsplit=1)
        updated[index + 1] = f"{int(port)}:{container_port}"
        return updated
    raise ValueError("docker_run_command does not contain a '-p host:container' mapping")


def _build_wave_scoped_registrations(
    mode: str,
    qps: int,
    repeat_id: int,
    registrations: list[Any],
    request_traces: list[TraceRequest],
) -> list[Any]:
    """Build per-request scoped registration set for one wave."""
    scoped_registrations: list[Any] = []
    seen_container_names: set[str] = set()
    for request_id, trace in enumerate(request_traces):
        trace_required_server_names = _trace_required_server_names(trace)
        trace_registrations = [
            reg
            for reg in registrations
            if (
                trace_required_server_names is None
                or str(getattr(reg, "server_name", "") or "")
                in trace_required_server_names
            )
        ]
        namespace = build_request_namespace(mode, qps, repeat_id, request_id)
        port = build_request_port(mode, qps, repeat_id, request_id)
        for reg in scope_registration_configs(trace_registrations, namespace, port):
            container_name = str(reg.server_config.container_name)
            if container_name in seen_container_names:
                continue
            seen_container_names.add(container_name)
            scoped_registrations.append(reg)
    return scoped_registrations


def _resolve_request_scope(args: argparse.Namespace) -> tuple[str, int]:
    """Resolve the request namespace and host port for one subprocess."""
    namespace = get_request_namespace()
    if not namespace:
        namespace = build_request_namespace(
            args.mode,
            args.qps,
            args.repeat_id,
            args.request_id,
        )

    port = get_request_port()
    if port is None:
        port = build_request_port(
            args.mode,
            args.qps,
            args.repeat_id,
            args.request_id,
        )

    return namespace, port


def _set_runtime_config(mode: str, stream_interval_tokens: int | None) -> None:
    """Set on-demand runtime config values before loading tool module."""
    import config

    if mode == _MODE_ON_DEMAND:
        prewarm_enabled = False
        predictive_enabled = False
    elif mode == _MODE_LAPLACE:
        prewarm_enabled = True
        predictive_enabled = True
    elif mode == _MODE_ALWAYS_ON:
        prewarm_enabled = False
        predictive_enabled = False
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    config.ON_DEMAND_PREWARM_ENABLED = prewarm_enabled
    config.ON_DEMAND_PREDICTIVE_PREWARM_ENABLED = predictive_enabled
    config.ON_DEMAND_PREWARM_TELEMETRY_ENABLED = True
    config.ON_DEMAND_PREWARM_TELEMETRY_MAX_EVENTS = 2048
    config.ON_DEMAND_STREAM_TEXT_SPECULATION_INTERVAL_TOKENS = (
        config.normalize_stream_text_speculation_interval_tokens(stream_interval_tokens)
    )


def _configure_mcp_idle_retention(mode: str) -> None:
    """Configure MCP idle cleanup thresholds for the current execution mode."""
    if mode == _MODE_ALWAYS_ON:
        os.environ["MCP_CONTAINER_IDLE_STOP_SECONDS"] = str(_ALWAYS_ON_IDLE_STOP_SECONDS)
        os.environ["MCP_CONTAINER_IDLE_REMOVE_SECONDS"] = str(_ALWAYS_ON_IDLE_REMOVE_SECONDS)
        return

    os.environ.pop("MCP_CONTAINER_IDLE_STOP_SECONDS", None)
    os.environ.pop("MCP_CONTAINER_IDLE_REMOVE_SECONDS", None)


def _patch_tool_model_determinism(
    tool_module: Any,
    llm_seed: int,
    llm_temperature: float,
    llm_top_p: float,
) -> None:
    """Patch worker model constructor to enforce deterministic generation kwargs."""
    original_cls = tool_module.DashScopeChatModel

    class _DeterministicDashScopeChatModel(original_cls):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            generate_kwargs = dict(kwargs.pop("generate_kwargs", {}) or {})
            generate_kwargs.setdefault("seed", llm_seed)
            generate_kwargs.setdefault("temperature", llm_temperature)
            generate_kwargs.setdefault("top_p", llm_top_p)
            super().__init__(*args, generate_kwargs=generate_kwargs, **kwargs)

    tool_module.DashScopeChatModel = _DeterministicDashScopeChatModel


def _build_planner(
    mode: str,
    model_name: str,
    planner_max_iters: int,
    stream_interval_tokens: int | None,
    llm_seed: int,
    llm_temperature: float,
    llm_top_p: float,
    registrations: list[Any],
) -> tuple[ReActAgent, Path]:
    """Construct planner for one real request."""
    _set_runtime_config(mode, stream_interval_tokens)

    tool_module = importlib.import_module("tool")
    tool_module = importlib.reload(tool_module)
    _patch_tool_model_determinism(
        tool_module=tool_module,
        llm_seed=llm_seed,
        llm_temperature=llm_temperature,
        llm_top_p=llm_top_p,
    )

    timing_log_path = Path(getattr(tool_module, "_TIMING_LOG_PATH")).resolve()

    toolkit = Toolkit()

    async def create_worker(task_description: str) -> Any:
        """Create worker with mode-fixed prewarm policy for fair experiments."""
        fixed_prewarm = mode == _MODE_LAPLACE
        fixed_stream_interval = (
            stream_interval_tokens if (fixed_prewarm and stream_interval_tokens is not None) else None
        )
        async for item in tool_module.create_worker(
            task_description=task_description,
            prewarm=fixed_prewarm,
            stream_text_speculation_interval_tokens=fixed_stream_interval,
        ):
            yield item

    toolkit.register_tool_function(create_worker)

    prewarm_enabled = mode == _MODE_LAPLACE
    planner_prewarm_registrations = registrations

    planner_controller = MCPLaplaceController(
        prompt_prewarm_router=(MCPPrewarmHybridRouter() if prewarm_enabled else None),
        prompt_prewarm_executor=(
            build_mcp_speculative_executor(planner_prewarm_registrations) if prewarm_enabled else None
        ),
        config=MCPLaplaceControllerConfig(
            prompt_prewarm_enabled=prewarm_enabled,
            predictive_warmer_enabled=prewarm_enabled,
            telemetry_enabled=True,
            telemetry_max_events=2048,
            telemetry_name=f"real_e2e_planner_{mode}",
        ),
    )

    planner = ReActAgent(
        name="Friday",
        sys_prompt=(
            "You are Friday, a meta planner agent. "
            "Always create a plan first, then execute subtasks in order. "
            "You MUST call create_worker at least once for each user request "
            "before producing the final answer. "
            "If user message includes strict trace replay constraints, follow them exactly."
        ),
        model=DashScopeChatModel(
            model_name=model_name,
            api_key=os.environ["DASHSCOPE_API_KEY"],
            generate_kwargs={
                "seed": llm_seed,
                "temperature": llm_temperature,
                "top_p": llm_top_p,
            },
            stream_text_speculation_interval_tokens=(
                stream_interval_tokens if prewarm_enabled else None
            ),
        ),
        formatter=DashScopeChatFormatter(),
        plan_notebook=PlanNotebook(),
        toolkit=toolkit,
        max_iters=planner_max_iters,
        mcp_laplace_controller=planner_controller,
    )
    planner.set_console_output_enabled(False)

    return planner, timing_log_path


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load JSONL rows."""
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def _compute_tool_cumulative_ms(records: list[dict[str, Any]]) -> float:
    """Compute cumulative tool provisioning latency from worker timing records."""
    total = 0.0
    for record in records:
        summary = record.get("summary") or {}
        value = summary.get("wait_for_mcp_ready_after_activation_ms")
        if isinstance(value, (int, float)):
            total += float(value)
    return total


def _wave_succeeded(rows: list[dict[str, Any]]) -> bool:
    """Return whether all request rows in one wave succeeded."""
    return bool(rows) and all(row.get("status") == "ok" for row in rows)


def _is_container_runtime_error(error_value: Any) -> bool:
    """Return whether an error string indicates MCP container runtime failure."""
    if not isinstance(error_value, str):
        return False

    text = error_value.lower()
    keywords = (
        "failed to start mcp container",
        "failed to recreate mcp container",
        "port is already allocated",
        "failed to set up container networking",
        "mcp container",
        "docker: error response from daemon",
    )
    return any(keyword in text for keyword in keywords)


def _is_port_already_allocated_error(error_value: Any) -> bool:
    """Return whether an error indicates docker host-port allocation conflict."""
    if not isinstance(error_value, str):
        return False

    text = error_value.lower()
    return (
        "port is already allocated" in text
        or "bind for 0.0.0.0" in text
        or "failed to set up container networking" in text
    )


async def _run_single_dialogue(planner: ReActAgent, user_request: str) -> None:
    """Run one-turn dialogue."""
    await planner(Msg("user", user_request, "user"))


def _build_worker_enforcement_prompt(original_user_request: str, attempt_index: int) -> str:
    """Build an explicit follow-up prompt that forces at least one worker call."""
    return (
        "Protocol correction: your previous response did not invoke create_worker. "
        "You must call create_worker now before any final answer. "
        "Do not skip tool usage. After create_worker returns, provide the final answer. "
        f"Enforcement attempt: {attempt_index}. "
        f"Original user request: {original_user_request}"
    )


async def _wait_for_timing_records(
    timing_log_path: Path,
    timeout_seconds: float = 1.0,
    poll_interval_seconds: float = 0.05,
) -> list[dict[str, Any]]:
    """Wait briefly for timing records to be flushed to disk."""
    deadline = time.perf_counter() + max(0.0, float(timeout_seconds))
    while True:
        records = _load_jsonl(timing_log_path)
        if records:
            return records
        if time.perf_counter() >= deadline:
            return records
        await asyncio.sleep(max(0.01, float(poll_interval_seconds)))


async def _run_dialogue_with_worker_enforcement(
    planner: ReActAgent,
    user_request: str,
    timing_log_path: Path,
    max_enforcement_turns: int = 2,
) -> tuple[int, list[dict[str, Any]]]:
    """Run request and enforce at least one worker call when needed."""
    await _run_single_dialogue(planner, user_request)
    timing_records = await _wait_for_timing_records(timing_log_path)
    enforcement_turns = 0

    while not timing_records and enforcement_turns < max(0, int(max_enforcement_turns)):
        enforcement_turns += 1
        await _run_single_dialogue(
            planner,
            _build_worker_enforcement_prompt(user_request, enforcement_turns),
        )
        timing_records = await _wait_for_timing_records(timing_log_path)

    return enforcement_turns, timing_records


def _single_run_main(args: argparse.Namespace) -> None:
    """Execute one real request and write a JSON result file."""
    os.environ["AGENTSCOPE_ON_DEMAND_TEMP_DIR"] = str(Path(args.temp_dir).resolve())
    os.environ["AGENTSCOPE_TIMING_LOG_BASENAME"] = f"{args.mode}_timing.log.jsonl"
    Path(args.temp_dir).mkdir(parents=True, exist_ok=True)
    _configure_mcp_idle_retention(args.mode)

    request_namespace, request_port = _resolve_request_scope(args)
    os.environ["AGENTSCOPE_MCP_CONTAINER_NAMESPACE"] = request_namespace
    os.environ["AGENTSCOPE_MCP_CONTAINER_PORT"] = str(request_port)

    required_server_names = _resolve_required_server_names_from_env()
    registrations = scope_registration_configs(
        _load_experiment_registrations(required_server_names=required_server_names),
        request_namespace,
        request_port,
    )

    llm_seed = _normalize_api_seed(
        _stable_seed(
            args.seed,
            f"{args.trace_id}:{args.mode}:{args.repeat_id}:{args.request_id}:{args.attempt_id}",
        ),
    )
    try:
        planner, timing_log_path = _build_planner(
            mode=args.mode,
            model_name=args.model_name,
            planner_max_iters=args.planner_max_iters,
            stream_interval_tokens=(args.stream_interval_tokens if args.stream_interval_tokens > 0 else None),
            llm_seed=llm_seed,
            llm_temperature=args.llm_temperature,
            llm_top_p=args.llm_top_p,
            registrations=registrations,
        )

        timing_log_path.parent.mkdir(parents=True, exist_ok=True)
        timing_log_path.write_text("", encoding="utf-8")

        started = time.perf_counter()
        status = "ok"
        error_message = None
        enforcement_turns = 0
        timing_records: list[dict[str, Any]] = []
        try:
            previous_cwd = Path.cwd()
            os.chdir(Path(args.temp_dir).resolve())
            try:
                effective_user_request = str(args.user_request)
                if str(args.trace_replay_instruction or "").strip():
                    effective_user_request = (
                        f"{effective_user_request}\n\n"
                        "[TRACE_REPLAY]\n"
                        f"{args.trace_replay_instruction}\n"
                        "[/TRACE_REPLAY]"
                    )

                enforcement_turns, timing_records = asyncio.run(
                    _run_dialogue_with_worker_enforcement(
                        planner=planner,
                        user_request=effective_user_request,
                        timing_log_path=timing_log_path,
                    ),
                )
            finally:
                os.chdir(previous_cwd)
        except Exception as exc:  # pragma: no cover - runtime-dependent path
            status = "error"
            error_message = str(exc)
        elapsed_ms = (time.perf_counter() - started) * 1000.0

        if not timing_records:
            timing_records = _load_jsonl(timing_log_path)
        tool_cumulative_ms = _compute_tool_cumulative_ms(timing_records)
        worker_calls = len(timing_records)

        if status == "ok" and worker_calls == 0:
            status = "error"
            error_message = "no_worker_call"
            tool_cumulative_ms = None

        payload = {
            "status": status,
            "error": error_message,
            "mode": args.mode,
            "trace_id": args.trace_id,
            "attempt_id": args.attempt_id,
            "request_id": args.request_id,
            "repeat_id": args.repeat_id,
            "qps": args.qps,
            "e2e_ms": round(float(elapsed_ms), 6),
            "tool_cumulative_ms": (
                round(float(tool_cumulative_ms), 6)
                if isinstance(tool_cumulative_ms, (int, float))
                else None
            ),
            "worker_calls": worker_calls,
            "worker_enforcement_turns": int(enforcement_turns),
            "mcp_container_namespace": request_namespace,
            "mcp_container_port": request_port,
        }
        Path(args.output_json).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    finally:
        if args.mode != _MODE_ALWAYS_ON:
            cleanup_scoped_containers(registrations)


def _spawn_single_request(
    python_exe: str,
    script_path: Path,
    mode: str,
    qps: int,
    repeat_id: int,
    request_id: int,
    trace: TraceRequest,
    seed: int,
    model_name: str,
    planner_max_iters: int,
    stream_interval_tokens: int,
    llm_temperature: float,
    llm_top_p: float,
    temp_root: Path,
    single_run_timeout_seconds: float | None,
    trace_required_server_names: set[str] | None,
    trace_replay_instruction: str,
    attempt_id: int,
) -> dict[str, Any]:
    """Run one request in an isolated subprocess and return parsed JSON result."""
    req_dir = temp_root / f"{mode}_qps{qps}_r{repeat_id}_req{request_id}_{uuid.uuid4().hex[:8]}"
    req_dir.mkdir(parents=True, exist_ok=True)
    output_json = req_dir / "result.json"
    request_namespace = req_dir.name
    request_port = build_request_port(mode, qps, repeat_id, request_id)

    cmd = [
        python_exe,
        str(script_path),
        "--single-run",
        "--mode",
        mode,
        "--qps",
        str(qps),
        "--repeat-id",
        str(repeat_id),
        "--request-id",
        str(request_id),
        "--attempt-id",
        str(attempt_id),
        "--trace-id",
        trace.trace_id,
        "--user-request",
        trace.user_request,
        "--trace-replay-instruction",
        str(trace_replay_instruction or ""),
        "--seed",
        str(seed),
        "--model-name",
        model_name,
        "--planner-max-iters",
        str(planner_max_iters),
        "--stream-interval-tokens",
        str(stream_interval_tokens),
        "--llm-temperature",
        str(llm_temperature),
        "--llm-top-p",
        str(llm_top_p),
        "--temp-dir",
        str(req_dir),
        "--output-json",
        str(output_json),
    ]

    max_local_port_retries = 2
    for _ in range(max_local_port_retries + 1):
        if output_json.exists():
            output_json.unlink()

        env = os.environ.copy()
        env["AGENTSCOPE_MCP_CONTAINER_NAMESPACE"] = request_namespace
        env["AGENTSCOPE_MCP_CONTAINER_PORT"] = str(request_port)
        if trace_required_server_names is not None:
            env["AGENTSCOPE_EXPERIMENT_SERVER_NAMES"] = json.dumps(
                sorted(trace_required_server_names),
                ensure_ascii=False,
            )

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            start_new_session=True,
        )
        try:
            stdout_text, stderr_text = process.communicate(timeout=single_run_timeout_seconds)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except Exception:
                pass
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                pass

            return {
                "status": "ok",
                "error": "subprocess_timeout",
                "mode": mode,
                "trace_id": trace.trace_id,
                "attempt_id": attempt_id,
                "request_id": request_id,
                "repeat_id": repeat_id,
                "qps": qps,
                "e2e_ms": (
                    round(float(single_run_timeout_seconds) * 1000.0, 6)
                    if isinstance(single_run_timeout_seconds, (int, float))
                    else None
                ),
                "tool_cumulative_ms": None,
                "worker_calls": 0,
                "timeout_reached": True,
                "mcp_container_namespace": request_namespace,
                "mcp_container_port": request_port,
            }

        completed = subprocess.CompletedProcess(
            args=cmd,
            returncode=int(process.returncode or 0),
            stdout=stdout_text,
            stderr=stderr_text,
        )

        if completed.returncode != 0:
            stderr_tail = str(completed.stderr or "")[-1000:]
            if _is_port_already_allocated_error(stderr_tail):
                request_port = _pick_free_host_port(start_port=40000, end_port=65000)
                continue
            return {
                "status": "error",
                "error": f"subprocess_exit_{completed.returncode}: {stderr_tail[-500:]}",
                "mode": mode,
                "trace_id": trace.trace_id,
                "attempt_id": attempt_id,
                "request_id": request_id,
                "repeat_id": repeat_id,
                "qps": qps,
                "e2e_ms": None,
                "tool_cumulative_ms": None,
                "worker_calls": 0,
                "mcp_container_namespace": request_namespace,
                "mcp_container_port": request_port,
            }

        if not output_json.exists():
            return {
                "status": "error",
                "error": "missing_output_json",
                "mode": mode,
                "trace_id": trace.trace_id,
                "attempt_id": attempt_id,
                "request_id": request_id,
                "repeat_id": repeat_id,
                "qps": qps,
                "e2e_ms": None,
                "tool_cumulative_ms": None,
                "worker_calls": 0,
                "mcp_container_namespace": request_namespace,
                "mcp_container_port": request_port,
            }

        result = json.loads(output_json.read_text(encoding="utf-8"))
        result.setdefault("attempt_id", attempt_id)
        result.setdefault("mcp_container_namespace", request_namespace)
        result.setdefault("mcp_container_port", request_port)
        if _is_port_already_allocated_error(result.get("error")):
            request_port = _pick_free_host_port(start_port=40000, end_port=65000)
            continue
        return result

    return {
        "status": "error",
        "error": "local_port_rebind_retries_exhausted",
        "mode": mode,
        "trace_id": trace.trace_id,
        "attempt_id": attempt_id,
        "request_id": request_id,
        "repeat_id": repeat_id,
        "qps": qps,
        "e2e_ms": None,
        "tool_cumulative_ms": None,
        "worker_calls": 0,
        "mcp_container_namespace": request_namespace,
        "mcp_container_port": request_port,
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write rows to JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    """Append one row to JSONL for crash-safe incremental persistence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False) + "\n")


def _wave_key(mode: str, qps: int, repeat_id: int) -> tuple[str, int, int]:
    """Build stable wave key used for resume deduplication."""
    return (str(mode), int(qps), int(repeat_id))


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    """Write CSV with selected headers."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header) for header in headers})


def _aggregate_metrics(
    request_rows: list[dict[str, Any]],
    wave_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Aggregate per-request and per-wave results into mode-qps metrics."""
    index: dict[tuple[str, int], dict[str, Any]] = {}

    for row in request_rows:
        mode = str(row["mode"])
        qps = int(row["qps"])
        key = (mode, qps)
        if key not in index:
            index[key] = {
                "mode": mode,
                "qps": qps,
                "e2e_ms_values": [],
                "tool_ms_values": [],
                "errors": 0,
                "total_requests": 0,
            }
        item = index[key]
        item["total_requests"] += 1
        if row.get("status") != "ok":
            item["errors"] += 1
            continue
        e2e = row.get("e2e_ms")
        tool_ms = row.get("tool_cumulative_ms")
        if isinstance(e2e, (int, float)):
            item["e2e_ms_values"].append(float(e2e))
        if isinstance(tool_ms, (int, float)):
            item["tool_ms_values"].append(float(tool_ms))

    wave_index: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in wave_rows:
        key = (str(row["mode"]), int(row["qps"]))
        wave_index.setdefault(key, []).append(row)

    aggregated: list[dict[str, Any]] = []
    for mode in _MODE_CHOICES:
        for qps in sorted({int(r["qps"]) for r in request_rows if str(r["mode"]) == mode}):
            key = (mode, qps)
            item = index.get(key)
            if item is None:
                continue

            e2e_values = sorted(item["e2e_ms_values"])
            tool_values = sorted(item["tool_ms_values"])
            waves = wave_index.get(key, [])

            cpu_avg_values = [
                float(w["cpu_avg_cores"])
                for w in waves
                if isinstance(w.get("cpu_avg_cores"), (int, float))
            ]
            cpu_peak_values = [
                float(w["cpu_peak_cores"])
                for w in waves
                if isinstance(w.get("cpu_peak_cores"), (int, float))
            ]
            mem_avg_values = [
                float(w["memory_avg_gib"])
                for w in waves
                if isinstance(w.get("memory_avg_gib"), (int, float))
            ]
            mem_peak_values = [
                float(w["memory_peak_gib"])
                for w in waves
                if isinstance(w.get("memory_peak_gib"), (int, float))
            ]
            goodput_values = [
                float(w["goodput_rps"])
                for w in waves
                if isinstance(w.get("goodput_rps"), (int, float))
            ]

            aggregated.append(
                {
                    "mode": mode,
                    "qps": qps,
                    "total_requests": int(item["total_requests"]),
                    "successful_requests": len(e2e_values),
                    "error_requests": int(item["errors"]),
                    "e2e_mean_ms": round(statistics.mean(e2e_values), 6) if e2e_values else None,
                    "e2e_p50_ms": round(_quantile(e2e_values, 0.50), 6) if e2e_values else None,
                    "e2e_p95_ms": round(_quantile(e2e_values, 0.95), 6) if e2e_values else None,
                    "e2e_p99_ms": round(_quantile(e2e_values, 0.99), 6) if e2e_values else None,
                    "tool_cumulative_mean_ms": round(statistics.mean(tool_values), 6) if tool_values else None,
                    "tool_cumulative_p50_ms": round(_quantile(tool_values, 0.50), 6) if tool_values else None,
                    "tool_cumulative_p95_ms": round(_quantile(tool_values, 0.95), 6) if tool_values else None,
                    "goodput_rps": round(statistics.mean(goodput_values), 6) if goodput_values else None,
                    "cpu_avg_cores": round(statistics.mean(cpu_avg_values), 6) if cpu_avg_values else None,
                    "cpu_peak_cores": round(max(cpu_peak_values), 6) if cpu_peak_values else None,
                    "memory_avg_gib": round(statistics.mean(mem_avg_values), 6) if mem_avg_values else None,
                    "memory_peak_gib": round(max(mem_peak_values), 6) if mem_peak_values else None,
                },
            )

    aggregated.sort(key=lambda row: (_MODE_CHOICES.index(str(row["mode"])), int(row["qps"])))
    return aggregated


def _sweep_main(args: argparse.Namespace) -> None:
    """Run full real QPS sweep and persist outputs."""
    if "DASHSCOPE_API_KEY" not in os.environ:
        raise ValueError("DASHSCOPE_API_KEY is required for real E2E runs")

    if args.sample_size <= 0:
        raise ValueError("sample_size must be > 0")
    if args.qps_min <= 0 or args.qps_max <= 0:
        raise ValueError("qps range must be positive")
    if args.qps_min > args.qps_max:
        raise ValueError("qps_min cannot be greater than qps_max")
    if args.repeats <= 0:
        raise ValueError("repeats must be > 0")

    requests = _load_trace_requests(
        traces_json=args.traces_json,
        sample_size=args.sample_size,
        seed=args.seed,
    )

    registrations = _load_experiment_registrations(required_server_names=None)

    script_path = Path(__file__).resolve()
    python_exe = sys.executable

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    request_jsonl = output_dir / "real_e2e_request_results.jsonl"
    wave_jsonl = output_dir / "real_e2e_wave_results.jsonl"
    metrics_csv = output_dir / "real_e2e_qps_metrics.csv"
    scalability_csv = output_dir / "real_e2e_scalability_metrics.csv"
    resource_csv = output_dir / "real_e2e_resource_metrics.csv"
    summary_json = output_dir / "real_e2e_summary.json"

    if args.resume:
        existing_wave_rows = _load_jsonl(wave_jsonl)
        completed_waves = {
            _wave_key(
                str(row.get("mode", "")),
                int(row.get("qps", -1)),
                int(row.get("repeat_id", -1)),
            )
            for row in existing_wave_rows
        }
        existing_request_rows = _load_jsonl(request_jsonl)
        request_rows = [
            row
            for row in existing_request_rows
            if _wave_key(
                str(row.get("mode", "")),
                int(row.get("qps", -1)),
                int(row.get("repeat_id", -1)),
            )
            in completed_waves
        ]
        wave_rows = existing_wave_rows
    else:
        completed_waves = set()
        request_rows = []
        wave_rows = []
        request_jsonl.write_text("", encoding="utf-8")
        wave_jsonl.write_text("", encoding="utf-8")

    temp_root = output_dir / "real_e2e_tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    single_run_timeout_seconds = (
        float(args.single_run_timeout_seconds)
        if args.single_run_timeout_seconds and args.single_run_timeout_seconds > 0
        else None
    )
    wave_max_attempts = max(1, int(args.wave_max_attempts))

    for mode in _MODE_CHOICES:
        _configure_mcp_idle_retention(mode)
        for qps in range(args.qps_min, args.qps_max + 1):
            always_on_qps_request_rows: list[dict[str, Any]] = []
            always_on_qps_all_repeats_succeeded = True
            for repeat_id in range(args.repeats):
                wave_key = _wave_key(mode, qps, repeat_id)
                if wave_key in completed_waves:
                    continue

                final_wave_request_rows: list[dict[str, Any]] = []
                final_wave_resource: dict[str, float | None] = {}
                final_elapsed_seconds = 0.0
                wave_traces = [
                    requests[(repeat_id * qps + request_id) % len(requests)]
                    for request_id in range(qps)
                ]
                for attempt_id in range(1, wave_max_attempts + 1):
                    if mode != _MODE_ALWAYS_ON:
                        _cleanup_request_scoped_temp_root(temp_root, registrations)
                        _cleanup_experiment_mcp_runtime(registrations)
                    if mode == _MODE_ALWAYS_ON:
                        always_on_registrations = _build_wave_scoped_registrations(
                            mode=mode,
                            qps=qps,
                            repeat_id=repeat_id,
                            registrations=registrations,
                            request_traces=wave_traces,
                        )
                        try:
                            asyncio.run(_ensure_experiment_mcp_runtime(always_on_registrations))
                        except RuntimeError:
                            cleanup_scoped_containers(always_on_registrations)
                            if attempt_id < wave_max_attempts:
                                continue
                            raise

                    monitor = _ResourceMonitor(interval_seconds=args.resource_sample_interval)
                    monitor.start()

                    started = time.perf_counter()
                    wave_request_rows: list[dict[str, Any]] = []

                    with ThreadPoolExecutor(max_workers=qps) as executor:
                        future_map = {}
                        for request_id in range(qps):
                            trace = wave_traces[request_id]
                            trace_required_server_names = _trace_required_server_names(trace)
                            trace_replay_instruction = _build_trace_replay_instruction(trace)
                            future = executor.submit(
                                _spawn_single_request,
                                python_exe,
                                script_path,
                                mode,
                                qps,
                                repeat_id,
                                request_id,
                                trace,
                                args.seed,
                                args.model_name,
                                args.planner_max_iters,
                                args.stream_interval_tokens,
                                args.llm_temperature,
                                args.llm_top_p,
                                temp_root,
                                single_run_timeout_seconds,
                                trace_required_server_names,
                                trace_replay_instruction,
                                attempt_id,
                            )
                            future_map[future] = request_id

                        for future in as_completed(future_map):
                            wave_request_rows.append(future.result())

                    elapsed_seconds = max(1e-6, time.perf_counter() - started)
                    wave_resource = monitor.stop()

                    if mode != _MODE_ALWAYS_ON:
                        _cleanup_request_scoped_mcp_runtime(registrations, wave_request_rows)
                        _cleanup_experiment_mcp_runtime(registrations)

                    success_count = sum(1 for row in wave_request_rows if row.get("status") == "ok")
                    error_count = len(wave_request_rows) - success_count
                    container_error_count = sum(
                        1
                        for row in wave_request_rows
                        if _is_container_runtime_error(row.get("error"))
                    )
                    final_wave_request_rows = wave_request_rows
                    final_wave_resource = wave_resource
                    final_elapsed_seconds = elapsed_seconds

                    if error_count == 0:
                        break

                    if container_error_count > 0 and attempt_id < wave_max_attempts:
                        # Batch-level retry policy for container errors:
                        # when any request in this batch hits container runtime
                        # failure, drop this whole attempt and rerun the batch.
                        continue

                request_rows.extend(final_wave_request_rows)
                for req_row in final_wave_request_rows:
                    _append_jsonl(request_jsonl, req_row)

                if mode == _MODE_ALWAYS_ON:
                    if _wave_succeeded(final_wave_request_rows):
                        always_on_qps_request_rows.extend(final_wave_request_rows)
                    else:
                        always_on_qps_all_repeats_succeeded = False

                success_count = sum(1 for row in final_wave_request_rows if row.get("status") == "ok")
                wave_row = {
                    "mode": mode,
                    "qps": qps,
                    "repeat_id": repeat_id,
                    "request_count": len(final_wave_request_rows),
                    "success_count": success_count,
                    "error_count": len(final_wave_request_rows) - success_count,
                    "wave_elapsed_seconds": round(final_elapsed_seconds, 6),
                    "goodput_rps": round(success_count / max(1e-6, final_elapsed_seconds), 6),
                    **final_wave_resource,
                }
                wave_rows.append(wave_row)
                _append_jsonl(wave_jsonl, wave_row)
                completed_waves.add(wave_key)

            if (
                mode == _MODE_ALWAYS_ON
                and always_on_qps_all_repeats_succeeded
                and always_on_qps_request_rows
            ):
                _cleanup_request_scoped_mcp_runtime(registrations, always_on_qps_request_rows)
                _cleanup_experiment_mcp_runtime(registrations)

    aggregated_rows = _aggregate_metrics(request_rows=request_rows, wave_rows=wave_rows)

    _write_jsonl(request_jsonl, request_rows)
    _write_jsonl(wave_jsonl, wave_rows)

    headers_all = [
        "mode",
        "qps",
        "total_requests",
        "successful_requests",
        "error_requests",
        "e2e_mean_ms",
        "e2e_p50_ms",
        "e2e_p95_ms",
        "e2e_p99_ms",
        "tool_cumulative_mean_ms",
        "tool_cumulative_p50_ms",
        "tool_cumulative_p95_ms",
        "goodput_rps",
        "cpu_avg_cores",
        "cpu_peak_cores",
        "memory_avg_gib",
        "memory_peak_gib",
    ]
    _write_csv(metrics_csv, headers_all, aggregated_rows)

    scalability_headers = [
        "mode",
        "qps",
        "e2e_mean_ms",
        "e2e_p95_ms",
        "e2e_p99_ms",
        "tool_cumulative_mean_ms",
        "tool_cumulative_p95_ms",
        "goodput_rps",
        "error_requests",
    ]
    _write_csv(scalability_csv, scalability_headers, aggregated_rows)

    resource_headers = [
        "mode",
        "qps",
        "cpu_avg_cores",
        "cpu_peak_cores",
        "memory_avg_gib",
        "memory_peak_gib",
    ]
    _write_csv(resource_csv, resource_headers, aggregated_rows)

    summary = {
        "experiment": "real_e2e_qps_sweep",
        "description": (
            "Real (non-simulated) QPS sweep with repeated waves. "
            "Includes E2E latency, cumulative tool provisioning latency, and host resources."
        ),
        "source_traces_json": str(Path(args.traces_json).resolve()),
        "seed": args.seed,
        "sample_size": args.sample_size,
        "qps_min": args.qps_min,
        "qps_max": args.qps_max,
        "repeats": args.repeats,
        "resume": bool(args.resume),
        "model_name": args.model_name,
        "planner_max_iters": args.planner_max_iters,
        "stream_interval_tokens": args.stream_interval_tokens,
        "llm_temperature": args.llm_temperature,
        "llm_top_p": args.llm_top_p,
        "wave_max_attempts": args.wave_max_attempts,
        "sampled_trace_ids": [req.trace_id for req in requests],
        "aggregated_rows": aggregated_rows,
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(str(request_jsonl))
    print(str(wave_jsonl))
    print(str(metrics_csv))
    print(str(scalability_csv))
    print(str(resource_csv))
    print(str(summary_json))


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run real E2E QPS stress tests.")

    parser.add_argument("--single-run", action="store_true", help=argparse.SUPPRESS)

    parser.add_argument("--mode", choices=_MODE_CHOICES, default=_MODE_ON_DEMAND)
    parser.add_argument("--qps", type=int, default=1)
    parser.add_argument("--repeat-id", type=int, default=0)
    parser.add_argument("--request-id", type=int, default=0)
    parser.add_argument("--attempt-id", type=int, default=0)
    parser.add_argument("--trace-id", default="")
    parser.add_argument("--user-request", default="")
    parser.add_argument("--trace-replay-instruction", default="")
    parser.add_argument("--temp-dir", default="")
    parser.add_argument("--output-json", default="")

    parser.add_argument("--traces-json", type=Path, default=_DEFAULT_TRACES_JSON)
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--qps-min", type=int, default=1)
    parser.add_argument("--qps-max", type=int, default=20)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--output-dir", type=Path, default=_DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable default resume behavior and start a fresh sweep.",
    )

    parser.add_argument("--model-name", default="qwen3.8-flash")
    parser.add_argument("--planner-max-iters", type=int, default=10)
    parser.add_argument("--stream-interval-tokens", type=int, default=20)
    parser.add_argument("--llm-temperature", type=float, default=0.0)
    parser.add_argument("--llm-top-p", type=float, default=1.0)
    parser.add_argument("--resource-sample-interval", type=float, default=0.2)
    parser.add_argument(
        "--single-run-timeout-seconds",
        type=float,
        default=300.0,
        help=(
            "Timeout for each single-run subprocess in sweep mode. "
            "Set <=0 to disable timeout."
        ),
    )
    parser.add_argument(
        "--wave-max-attempts",
        type=int,
        default=3,
        help=(
            "Maximum attempts for one (mode, qps, repeat_id) wave when errors occur. "
            "Wave is retried only when any request in that wave fails."
        ),
    )

    args = parser.parse_args()
    args.resume = not bool(args.no_resume)

    if args.single_run:
        if not args.user_request:
            raise ValueError("--user-request is required for --single-run")
        if not args.temp_dir:
            raise ValueError("--temp-dir is required for --single-run")
        if not args.output_json:
            raise ValueError("--output-json is required for --single-run")
        _single_run_main(args)
        return

    _sweep_main(args)


if __name__ == "__main__":
    main()
