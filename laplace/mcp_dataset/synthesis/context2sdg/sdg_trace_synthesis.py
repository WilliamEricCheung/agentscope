"""SDG-oriented trace synthesis helpers for MCP prewarm research.

This module converts the existing task-centric synthesis artifacts into
structured execution traces that are easier to consume by cross-step
predictive prewarming models such as a Skill Dependency Graph or a
first-order Markov router.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from laplace.util.dashscope_provider import DashScopeCompletionProvider
from laplace.util.server_config import LaplaceMCPManifestSource


TRACE_SCHEMA_VERSION = 2


def load_laplace_server_catalog(
    manifest_path: str | None = None,
    ready_only: bool = True,
) -> dict[str, dict[str, Any]]:
    """Load the Laplace MCP server catalog from the manifest.

    Args:
        manifest_path (`str | None`, optional):
            Explicit path to ``laplace_mcp_manifest.json``.
        ready_only (`bool`, optional):
            Whether to keep only entries marked as prewarm-ready.

    Returns:
        `dict[str, dict[str, Any]]`:
            Mapping from server name to prompt-friendly metadata.
    """
    resolved_path = (
        Path(manifest_path)
        if manifest_path is not None
        else _resolve_default_manifest_path()
    )
    manifest = json.loads(resolved_path.read_text(encoding="utf-8"))

    catalog: dict[str, dict[str, Any]] = {}
    for server_name, payload in manifest.get("servers", {}).items():
        if ready_only and not bool(payload.get("ready_for_prewarm", False)):
            continue

        server_config = payload.get("server_config", {})
        catalog[server_name] = {
            "group_name": str(payload.get("group_name", "")).strip(),
            "group_description": str(
                payload.get("group_description", ""),
            ).strip(),
            "tool_names": [
                str(tool_name).strip()
                for tool_name in payload.get("tool_names", [])
                if str(tool_name).strip()
            ],
            "transport": str(server_config.get("transport", "")).strip(),
            "url": str(server_config.get("url", "")).strip(),
            "container_name": str(
                server_config.get("container_name", ""),
            ).strip(),
            "server_type": _infer_server_type(
                server_name=server_name,
                group_name=str(payload.get("group_name", "")).strip(),
                group_description=str(
                    payload.get("group_description", ""),
                ).strip(),
            ),
            "ready_for_prewarm": bool(payload.get("ready_for_prewarm", False)),
        }
    return catalog


def build_batch_trace_prompt(
    server_catalog: dict[str, dict[str, Any]],
    trace_count: int = 100,
    min_steps: int = 5,
    max_steps: int = 8,
    common_pattern_ratio: float = 0.7,
) -> str:
    """Build a generic batch prompt for synthetic SDG trace generation.

    Args:
        server_catalog (`dict[str, dict[str, Any]]`):
            Prompt-friendly server metadata.
        trace_count (`int`, optional):
            Number of traces requested from the model.
        min_steps (`int`, optional):
            Minimum number of tool calls per trace.
        max_steps (`int`, optional):
            Maximum number of tool calls per trace.
        common_pattern_ratio (`float`, optional):
            Fraction of traces that should follow common patterns.

    Returns:
        `str`:
            Full prompt text for batch trace generation.
    """
    common_percent = int(max(0.0, min(common_pattern_ratio, 1.0)) * 100)
    edge_percent = 100 - common_percent
    return f"""Role: You are a senior system architect generating synthetic LLM-agent traces for cross-step MCP prewarming research.

Objective:
Generate {trace_count} diverse execution traces for an LLM agent that solves user requests by calling the available MCP servers and tools.

Research constraints:
- Every trace must contain {min_steps}-{max_steps} tool calls.
- Approximately {common_percent}% of traces should represent common execution motifs.
- Approximately {edge_percent}% of traces should represent edge cases, long-tail branches, retries, or server handoff patterns.
- Tool calls must respect the server-to-tool mapping exactly.
- The trace should be realistic for an agent: each step must expose why the next server or tool becomes likely.
- The output should be optimized for downstream SDG training, so make state carry-over and next-step predictability explicit.
- Every step must expose a contextual state using `(server_type, tool_category)`.
- If a workflow contains parallelizable branches, surface them in `sdg_summary.parallel_server_groups`.

Available MCP servers and tools:
{_format_server_catalog(server_catalog)}

Common motif examples to include across the batch:
- search -> inspect -> summarize
- locate -> filter -> inspect -> enrich
- health_check -> fetch -> cross_validate
- resolve_id -> fetch_docs -> extract_fields
- search -> lookup -> compare -> report

Edge-case motif examples to include across the batch:
- alternate branch after empty search result
- retry with narrower filter
- cross-server handoff after intermediate artifact extraction
- repeated same-server tool loops that evolve state
- optional enrichment step skipped because a prior result is sufficient

Return JSON only with this exact top-level shape:
{json.dumps(_batch_trace_schema(), indent=2, ensure_ascii=False)}
"""


def build_standalone_trace_prompt(
    server_catalog: dict[str, dict[str, Any]],
    trace_index: int,
    total_traces: int,
    min_steps: int = 5,
    max_steps: int = 8,
    common_pattern_ratio: float = 0.7,
) -> str:
    """Build one standalone prompt for a single SDG trace.

    Args:
        server_catalog (`dict[str, dict[str, Any]]`):
            Prompt-friendly server metadata.
        trace_index (`int`):
            Zero-based trace index in the requested run.
        total_traces (`int`):
            Total number of traces requested for the run.
        min_steps (`int`, optional):
            Minimum number of tool calls per trace.
        max_steps (`int`, optional):
            Maximum number of tool calls per trace.
        common_pattern_ratio (`float`, optional):
            Fraction of traces that should follow common patterns.

    Returns:
        `str`:
            Full prompt text for one standalone trace.
    """
    total = max(1, int(total_traces))
    common_cutoff = int(max(0.0, min(common_pattern_ratio, 1.0)) * total)
    trace_profile = (
        "common execution motif"
        if trace_index < common_cutoff
        else "edge-case or long-tail branch"
    )
    return f"""Role: You are a senior system architect generating one synthetic LLM-agent trace for cross-step MCP prewarming research.

Objective:
Generate exactly 1 standalone execution trace for an LLM agent that solves a realistic user request by calling the available MCP servers and tools.

Run context:
- This is trace {trace_index + 1} of {total}.
- Prioritize a {trace_profile}.

Research constraints:
- The trace must contain {min_steps}-{max_steps} tool calls.
- Tool calls must respect the server-to-tool mapping exactly.
- The trace should be realistic for an agent: each step must expose why the next server or tool becomes likely.
- The output should be optimized for downstream SDG training, so make state carry-over and next-step predictability explicit.
- Every step must expose a contextual state using `(server_type, tool_category)`.
- If a workflow contains parallelizable branches, surface them in `sdg_summary.parallel_server_groups`.

Available MCP servers and tools:
{_format_server_catalog(server_catalog)}

Common motif examples:
- search -> inspect -> summarize
- locate -> filter -> inspect -> enrich
- health_check -> fetch -> cross_validate
- resolve_id -> fetch_docs -> extract_fields
- search -> lookup -> compare -> report

Edge-case motif examples:
- alternate branch after empty search result
- retry with narrower filter
- cross-server handoff after intermediate artifact extraction
- repeated same-server tool loops that evolve state
- optional enrichment step skipped because a prior result is sufficient

Return JSON only with this exact shape:
{json.dumps(_single_trace_schema(), indent=2, ensure_ascii=False)}
"""


class SDGTraceSynthesizer:
    """Generate structured SDG traces from the Laplace server catalog.

    Args:
        llm_provider (`DashScopeCompletionProvider`):
            DashScope-backed completion provider.
        max_retries_per_trace (`int`, optional):
            Maximum attempts for one accepted trace.
    """

    def __init__(
        self,
        llm_provider: DashScopeCompletionProvider,
        max_retries_per_trace: int = 3,
    ) -> None:
        """Initialize the trace synthesizer.

        Args:
            llm_provider (`DashScopeCompletionProvider`):
                DashScope-backed completion provider.
            max_retries_per_trace (`int`, optional):
                Maximum attempts for one accepted trace.
        """
        self.llm = llm_provider
        self.max_retries_per_trace = max(1, int(max_retries_per_trace))

    async def generate_trace_from_prompt(
        self,
        prompt: str,
        server_catalog: dict[str, dict[str, Any]] | None = None,
        trace_index: int = 0,
    ) -> dict[str, Any]:
        """Generate one structured SDG trace from a prepared prompt.

        Args:
            prompt (`str`):
                Fully prepared prompt text.
            server_catalog (`dict[str, dict[str, Any]] | None`, optional):
                Prompt-friendly server metadata.
            trace_index (`int`, optional):
                Zero-based trace index.

        Returns:
            `dict[str, Any]`:
                Normalized structured trace.

        Raises:
            `RuntimeError`:
                Raised when all trace-generation attempts fail.
        """
        catalog = server_catalog or load_laplace_server_catalog()

        last_error = "Unknown error"
        for _attempt in range(1, self.max_retries_per_trace + 1):
            try:
                response = await self.llm.get_completion(
                    system_prompt=(
                        "You generate structured MCP execution traces for "
                        "Skill Dependency Graph research. Return JSON only."
                    ),
                    user_prompt=prompt,
                    max_tokens=3200,
                )
                raw_trace = self.llm.clean_and_parse_json(response)
                if not isinstance(raw_trace, dict):
                    raise ValueError("Standalone SDG trace response must be a JSON object.")
                return _normalize_trace(
                    trace=raw_trace,
                    server_catalog=catalog,
                    trace_index=trace_index,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = f"{type(exc).__name__}: {exc}"

        raise RuntimeError(f"Failed to generate SDG trace: {last_error}")

    async def generate_batch_traces(
        self,
        trace_count: int,
        server_catalog: dict[str, dict[str, Any]] | None = None,
        min_steps: int = 5,
        max_steps: int = 8,
        common_pattern_ratio: float = 0.7,
    ) -> list[dict[str, Any]]:
        """Generate a standalone batch of structured SDG traces.

        Args:
            trace_count (`int`):
                Number of traces to synthesize.
            server_catalog (`dict[str, dict[str, Any]] | None`, optional):
                Prompt-friendly server metadata.
            min_steps (`int`, optional):
                Minimum tool-call count per trace.
            max_steps (`int`, optional):
                Maximum tool-call count per trace.
            common_pattern_ratio (`float`, optional):
                Fraction of traces that should follow common patterns.

        Returns:
            `list[dict[str, Any]]`:
                Generated structured traces.
        """
        catalog = server_catalog or load_laplace_server_catalog()
        prompt = build_batch_trace_prompt(
            server_catalog=catalog,
            trace_count=max(1, int(trace_count)),
            min_steps=min_steps,
            max_steps=max_steps,
            common_pattern_ratio=common_pattern_ratio,
        )

        last_error = "Unknown error"
        for _attempt in range(1, self.max_retries_per_trace + 1):
            try:
                response = await self.llm.get_completion(
                    system_prompt=(
                        "You generate structured MCP execution traces for "
                        "Skill Dependency Graph research. Return JSON only."
                    ),
                    user_prompt=prompt,
                    max_tokens=6400,
                )
                payload = self.llm.clean_and_parse_json(response)
                raw_traces = payload.get("traces", [])
                if not isinstance(raw_traces, list):
                    raise ValueError("Batch SDG trace response must contain a traces list.")
                return [
                    _normalize_trace(
                        trace=raw_trace,
                        server_catalog=catalog,
                        trace_index=trace_index,
                    )
                    for trace_index, raw_trace in enumerate(raw_traces)
                    if isinstance(raw_trace, dict)
                ]
            except Exception as exc:  # noqa: BLE001
                last_error = f"{type(exc).__name__}: {exc}"

        raise RuntimeError(f"Failed to generate SDG traces: {last_error}")


def _resolve_default_manifest_path() -> Path:
    """Resolve the default Laplace manifest path.

    Returns:
        `Path`:
            Resolved manifest file path.
    """
    return LaplaceMCPManifestSource._resolve_default_manifest_path()


def _format_server_catalog(server_catalog: dict[str, dict[str, Any]]) -> str:
    """Format the server catalog into prompt-friendly text.

    Args:
        server_catalog (`dict[str, dict[str, Any]]`):
            Prompt-friendly server metadata.

    Returns:
        `str`:
            Prompt-friendly catalog text.
    """
    lines: list[str] = []
    for server_name in sorted(server_catalog):
        payload = server_catalog[server_name]
        tool_names = ", ".join(payload.get("tool_names", []))
        lines.append(f"Server: {server_name}")
        lines.append(
            f"Description: {payload.get('group_description', '')}",
        )
        lines.append(f"Type: {payload.get('server_type', '')}")
        lines.append(f"Tools: {tool_names}")
        lines.append("")
    return "\n".join(lines).strip()


def _batch_trace_schema() -> dict[str, Any]:
    """Build the JSON schema example used in the batch prompt.

    Returns:
        `dict[str, Any]`:
            Example output structure.
    """
    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "traces": [
            _single_trace_schema(),
        ],
    }


def _single_trace_schema() -> dict[str, Any]:
    """Build the JSON schema example used in the single-trace prompt.

    Returns:
        `dict[str, Any]`:
            Example output structure.
    """
    return {
        "trace_id": "sdg_trace_00000",
        "source_server_scope": ["Google Maps"],
        "user_request": "Find a cafe near the museum and compare the best nearby options.",
        "execution_trace": [
            {
                "step_index": 1,
                "server_name": "Google Maps",
                "server_type": "Maps",
                "tool_name": "maps_geocode",
                "tool_category": "Resolve",
                "intent": "Resolve the origin place into coordinates.",
                "source_nodes": ["user_request"],
                "target_node": "origin_coordinates",
                "depends_on": [],
            },
            {
                "step_index": 2,
                "server_name": "Google Maps",
                "server_type": "Maps",
                "tool_name": "search_nearby",
                "tool_category": "Search",
                "intent": "Search nearby places using the resolved origin.",
                "source_nodes": ["origin_coordinates"],
                "target_node": "candidate_places",
                "depends_on": [1],
            },
        ],
        "sdg_summary": {
            "server_path": ["Google Maps", "Google Maps"],
            "tool_path": ["maps_geocode", "search_nearby"],
            "state_artifacts": ["origin_coordinates", "candidate_places"],
            "state_path": ["Maps::Resolve", "Maps::Search"],
            "successor_candidates": ["Google Maps"],
            "next_server_labels": ["Google Maps", "END"],
            "next_state_labels": ["Maps::Search", "END"],
            "parallel_server_groups": [],
            "inferred_edges": [
                {
                    "source_node": "user_request",
                    "target_node": "origin_coordinates",
                    "source_step_index": None,
                    "target_step_index": 1,
                    "edge_type": "data_dependency",
                },
                {
                    "source_node": "origin_coordinates",
                    "target_node": "candidate_places",
                    "source_step_index": 1,
                    "target_step_index": 2,
                    "edge_type": "data_dependency",
                },
            ],
        },
    }


def _normalize_trace(
    trace: dict[str, Any],
    server_catalog: dict[str, dict[str, Any]],
    trace_index: int,
) -> dict[str, Any]:
    """Normalize a raw model trace into a stable training record.

    Args:
        trace (`dict[str, Any]`):
            Raw model output.
        server_catalog (`dict[str, dict[str, Any]]`):
            Prompt-friendly server metadata.
        trace_index (`int`):
            Zero-based trace variant index.

    Returns:
        `dict[str, Any]`:
            Normalized trace record.
    """
    output = dict(trace)
    output["trace_id"] = str(
        output.get("trace_id") or f"sdg_trace_{trace_index:05d}",
    ).strip()
    output["source_server_scope"] = [
        str(server_name).strip()
        for server_name in output.get("source_server_scope", [])
        if str(server_name).strip()
    ]
    output["user_request"] = str(output.get("user_request", "")).strip()

    execution_trace = output.get("execution_trace", [])
    normalized_steps: list[dict[str, Any]] = []
    for index, raw_step in enumerate(execution_trace, start=1):
        if not isinstance(raw_step, dict):
            continue
        step = dict(raw_step)
        step["step_index"] = int(step.get("step_index", index))
        step["server_name"] = str(step.get("server_name", "")).strip()
        step["tool_name"] = str(step.get("tool_name", "")).strip()
        step["intent"] = str(step.get("intent", "")).strip()
        step["server_type"] = str(
            step.get("server_type")
            or server_catalog.get(step["server_name"], {}).get("server_type", "")
            or _infer_server_type(
                server_name=step["server_name"],
                group_name="",
                group_description=server_catalog.get(step["server_name"], {}).get(
                    "group_description",
                    "",
                ),
            )
        ).strip()
        step["tool_category"] = str(
            step.get("tool_category") or _infer_tool_category(step["tool_name"]),
        ).strip()
        step["target_node"] = str(step.get("target_node", "")).strip()
        step["source_nodes"] = [
            str(item).strip()
            for item in step.get("source_nodes", [])
            if str(item).strip()
        ]
        step["depends_on"] = [
            int(item)
            for item in step.get("depends_on", [])
            if str(item).strip()
        ]

        if step["server_name"] in server_catalog:
            step["tool_known_to_server"] = (
                step["tool_name"]
                in server_catalog[step["server_name"]].get("tool_names", [])
            )
        else:
            step["tool_known_to_server"] = False

        normalized_steps.append(step)

    output["execution_trace"] = normalized_steps

    sdg_summary = dict(output.get("sdg_summary", {}))
    server_sequence = [step["server_name"] for step in normalized_steps if step["server_name"]]
    tool_sequence = [step["tool_name"] for step in normalized_steps if step["tool_name"]]
    cross_step_state = [step["target_node"] for step in normalized_steps if step["target_node"]]
    state_path = [_build_state_signature(step) for step in normalized_steps]
    next_server_labels = _build_next_server_labels(server_sequence)
    next_state_labels = _build_next_server_labels(state_path)
    inferred_edges = _infer_sdg_edges(normalized_steps)
    parallel_server_groups = _normalize_parallel_server_groups(
        raw_groups=sdg_summary.get("parallel_server_groups", []),
    )

    sdg_summary["server_path"] = server_sequence
    sdg_summary["tool_path"] = tool_sequence
    sdg_summary["state_artifacts"] = cross_step_state
    sdg_summary["state_path"] = state_path
    sdg_summary["successor_candidates"] = [
        str(server_name).strip()
        for server_name in sdg_summary.get(
            "successor_candidates",
            _default_successor_candidates(server_sequence),
        )
        if str(server_name).strip()
    ]
    sdg_summary["next_server_labels"] = next_server_labels
    sdg_summary["next_state_labels"] = next_state_labels
    sdg_summary["parallel_server_groups"] = parallel_server_groups
    sdg_summary["inferred_edges"] = inferred_edges
    output["sdg_summary"] = sdg_summary
    output["schema_version"] = TRACE_SCHEMA_VERSION
    return output


def _normalize_parallel_server_groups(raw_groups: Any) -> list[list[str]]:
    """Normalize explicit parallel server groups from raw model output.

    Args:
        raw_groups (`Any`):
            Raw parallel-group payload.

    Returns:
        `list[list[str]]`:
            Clean parallel server groups.
    """
    normalized: list[list[str]] = []
    if not isinstance(raw_groups, list):
        return normalized

    for raw_group in raw_groups:
        if not isinstance(raw_group, list):
            continue
        group = [str(server_name).strip() for server_name in raw_group if str(server_name).strip()]
        if len(group) >= 2:
            normalized.append(group)
    return normalized


def _build_next_server_labels(server_sequence: list[str]) -> list[str]:
    """Build next-server labels for first-order transition learning.

    Args:
        server_sequence (`list[str]`):
            Ordered server sequence.

    Returns:
        `list[str]`:
            Next-server labels aligned with each step.
    """
    if not server_sequence:
        return []

    labels: list[str] = []
    for index in range(len(server_sequence) - 1):
        labels.append(server_sequence[index + 1])
    labels.append("END")
    return labels


def build_server_transition_counts(
    traces: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    """Count server-to-server transitions across traces.

    Args:
        traces (`list[dict[str, Any]]`):
            SDG traces.

    Returns:
        `dict[str, dict[str, int]]`:
            Nested mapping of source server to target server counts.
    """
    return _build_transition_counts(
        sequences=[
            trace.get("sdg_summary", {}).get("server_path", [])
            for trace in traces
        ],
    )


def build_server_transition_matrix(
    traces: list[dict[str, Any]],
) -> dict[str, dict[str, float]]:
    """Build a first-order server transition matrix.

    Args:
        traces (`list[dict[str, Any]]`):
            SDG traces.

    Returns:
        `dict[str, dict[str, float]]`:
            Transition probability matrix following `P(S_j | S_i)`.
    """
    return _normalize_transition_counts(build_server_transition_counts(traces))


def build_state_transition_counts(
    traces: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    """Count contextual state transitions across traces.

    Args:
        traces (`list[dict[str, Any]]`):
            SDG traces.

    Returns:
        `dict[str, dict[str, int]]`:
            Nested mapping of source state to target state counts.
    """
    return _build_transition_counts(
        sequences=[
            trace.get("sdg_summary", {}).get("state_path", [])
            for trace in traces
        ],
    )


def build_state_transition_matrix(
    traces: list[dict[str, Any]],
) -> dict[str, dict[str, float]]:
    """Build a first-order contextual state transition matrix.

    Args:
        traces (`list[dict[str, Any]]`):
            SDG traces.

    Returns:
        `dict[str, dict[str, float]]`:
            Transition probability matrix over `(Server_Type, Tool_Category)` states.
    """
    return _normalize_transition_counts(build_state_transition_counts(traces))


def _default_successor_candidates(server_sequence: list[str]) -> list[str]:
    """Infer default successor candidates from a server sequence.

    Args:
        server_sequence (`list[str]`):
            Ordered server sequence.

    Returns:
        `list[str]`:
            Deduplicated server names that appear after the first step.
    """
    seen: set[str] = set()
    candidates: list[str] = []
    for server_name in server_sequence[1:]:
        if server_name and server_name not in seen:
            candidates.append(server_name)
            seen.add(server_name)
    return candidates


def _build_state_signature(step: dict[str, Any]) -> str:
    """Build a stable contextual state key for one execution step.

    Args:
        step (`dict[str, Any]`):
            One normalized execution step.

    Returns:
        `str`:
            Contextual state key.
    """
    server_type = str(step.get("server_type", "")).strip() or "Unknown"
    tool_category = str(step.get("tool_category", "")).strip() or "Unknown"
    return f"{server_type}::{tool_category}"


def _build_transition_counts(
    sequences: list[list[str]],
) -> dict[str, dict[str, int]]:
    """Count adjacent transitions for ordered sequences.

    Args:
        sequences (`list[list[str]]`):
            Ordered symbol sequences.

    Returns:
        `dict[str, dict[str, int]]`:
            Nested transition counts.
    """
    counts: dict[str, dict[str, int]] = {}
    for sequence in sequences:
        cleaned = [str(item).strip() for item in sequence if str(item).strip()]
        for index in range(len(cleaned) - 1):
            source = cleaned[index]
            target = cleaned[index + 1]
            counts.setdefault(source, {})
            counts[source][target] = counts[source].get(target, 0) + 1
    return counts


def _normalize_transition_counts(
    counts: dict[str, dict[str, int]],
) -> dict[str, dict[str, float]]:
    """Normalize transition counts into probabilities.

    Args:
        counts (`dict[str, dict[str, int]]`):
            Nested transition counts.

    Returns:
        `dict[str, dict[str, float]]`:
            Nested transition probabilities.
    """
    matrix: dict[str, dict[str, float]] = {}
    for source, target_counts in counts.items():
        total = sum(target_counts.values())
        if total <= 0:
            matrix[source] = {}
            continue
        matrix[source] = {
            target: count / total
            for target, count in target_counts.items()
        }
    return matrix


def _infer_parallel_server_groups(
    dependency_analysis: str,
    source_servers: list[str],
    available_servers: list[str],
    normalized_steps: list[dict[str, Any]],
) -> list[list[str]]:
    """Infer parallelizable server groups from dependency analysis.

    Args:
        dependency_analysis (`str`):
            Task dependency analysis text.
        source_servers (`list[str]`):
            Source task server scope.
        available_servers (`list[str]`):
            Available servers for the current synthesis run.
        normalized_steps (`list[dict[str, Any]]`):
            Normalized execution steps.

    Returns:
        `list[list[str]]`:
            Parallelizable server groups.
    """
    analysis = dependency_analysis.lower()
    if not any(
        keyword in analysis
        for keyword in ["parallel", "concurrent", "simultaneous", "同时", "并行"]
    ):
        return []

    ordered_candidates: list[str] = []
    for server_name in source_servers + available_servers + [
        step.get("server_name", "") for step in normalized_steps
    ]:
        normalized_name = str(server_name).strip()
        if normalized_name and normalized_name not in ordered_candidates:
            ordered_candidates.append(normalized_name)

    mentioned_servers = [
        server_name
        for server_name in ordered_candidates
        if server_name.lower() in analysis
    ]
    if len(mentioned_servers) >= 2:
        return [mentioned_servers]

    if len(ordered_candidates) >= 2:
        return [ordered_candidates[:2]]
    return []


def _infer_server_type(
    server_name: str,
    group_name: str,
    group_description: str,
) -> str:
    """Infer a coarse server type for contextual state modeling.

    Args:
        server_name (`str`):
            Human-readable server name.
        group_name (`str`):
            Manifest group name.
        group_description (`str`):
            Manifest group description.

    Returns:
        `str`:
            Coarse server type.
    """
    text = " ".join([server_name, group_name, group_description]).lower()
    keyword_map = [
        ("Academic", ["paper", "bio", "wikipedia", "museum", "academic", "nasa"]),
        ("Maps", ["map", "route", "park", "travel", "place"]),
        ("Finance", ["finance", "price", "calculator", "exchange", "crypto", "okx"]),
        ("Developer", ["nixos", "huggingface", "context7", "openapi", "icon"]),
        ("Social", ["reddit", "osint", "intelligence"]),
        ("Entertainment", ["movie", "game"]),
        ("Utility", ["time", "convert", "unit", "math", "scientific"]),
    ]
    for server_type, keywords in keyword_map:
        if any(keyword in text for keyword in keywords):
            return server_type
    return "General"


def _infer_tool_category(tool_name: str) -> str:
    """Infer a coarse tool category from the tool name.

    Args:
        tool_name (`str`):
            Tool name.

    Returns:
        `str`:
            Coarse tool category.
    """
    normalized_name = str(tool_name).lower().strip()
    keyword_map = [
        ("Search", ["search", "find", "list", "lookup", "discover"]),
        ("Fetch", ["get", "fetch", "read", "load", "detail"]),
        ("Resolve", ["resolve", "geocode", "parse", "identify"]),
        ("Filter", ["filter", "rank", "sort", "select", "nearby"]),
        ("Calculate", ["calculate", "compute", "convert", "estimate"]),
        ("Summarize", ["summarize", "extract", "report", "compare"]),
    ]
    for category, keywords in keyword_map:
        if any(keyword in normalized_name for keyword in keywords):
            return category
    return "Operate"


def _infer_sdg_edges(normalized_steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Infer explicit node-level edges from normalized steps.

    Args:
        normalized_steps (`list[dict[str, Any]]`):
            Normalized execution steps.

    Returns:
        `list[dict[str, Any]]`:
            Explicit node-level edges for direct SDG construction.
    """
    node_producers: dict[str, int] = {}
    inferred_edges: list[dict[str, Any]] = []

    for step in normalized_steps:
        target_node = str(step.get("target_node", "")).strip()
        target_step_index = int(step.get("step_index", 0))
        for source_node in step.get("source_nodes", []):
            source_name = str(source_node).strip()
            if not source_name or not target_node:
                continue
            inferred_edges.append(
                {
                    "source_node": source_name,
                    "target_node": target_node,
                    "source_step_index": node_producers.get(source_name),
                    "target_step_index": target_step_index,
                    "edge_type": "data_dependency",
                },
            )
        if target_node:
            node_producers[target_node] = target_step_index

    return inferred_edges