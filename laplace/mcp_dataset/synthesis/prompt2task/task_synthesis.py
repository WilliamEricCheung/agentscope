"""Task synthesis pipeline for DashScope-based MCP-Bench generation."""

from __future__ import annotations

import json
import logging
import random
import re
from typing import Any

from laplace.util.dashscope_provider import DashScopeCompletionProvider


_logger = logging.getLogger(__name__)


class TaskQualityEvaluator:
    """Evaluate synthesized tasks on solvability and utility.

    Args:
        llm_provider (`DashScopeCompletionProvider`):
            DashScope-backed completion provider.
        solvability_threshold (`float`, optional):
            Minimum acceptable solvability score.
        utility_threshold (`float`, optional):
            Minimum acceptable utility score.
    """

    def __init__(
        self,
        llm_provider: DashScopeCompletionProvider,
        solvability_threshold: float = 8.0,
        utility_threshold: float = 5.0,
    ) -> None:
        """Initialize the evaluator.

        Args:
            llm_provider (`DashScopeCompletionProvider`):
                DashScope-backed completion provider.
            solvability_threshold (`float`, optional):
                Minimum acceptable solvability score.
            utility_threshold (`float`, optional):
                Minimum acceptable utility score.
        """
        self.llm = llm_provider
        self.solvability_threshold = solvability_threshold
        self.utility_threshold = utility_threshold

    async def evaluate_task_quality(
        self,
        task: dict[str, Any],
        tools: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Evaluate one task candidate.

        Args:
            task (`dict[str, Any]`):
                Candidate task dictionary.
            tools (`dict[str, dict[str, Any]]`):
                Available MCP tool metadata.

        Returns:
            `dict[str, Any]`:
                Parsed evaluation result.
        """
        prompt = f"""Evaluate this MCP benchmark task and return JSON only.

Task description:
{task.get("task_description", "")}

Fuzzy description:
{task.get("fuzzy_description", "")}

Dependency analysis:
{task.get("dependency_analysis", "")}

Available tools:
{_format_tools(tools, limit=24)}

Score the task on two dimensions from 1 to 10:
1. solvability: Can the task be completed with these tools alone?
2. utility: Does the task provide meaningful research or business value?

Return exactly this JSON shape:
{{
  "solvability_score": 0,
  "utility_score": 0,
  "solvability_feedback": "",
  "utility_feedback": ""
}}"""

        response = await self.llm.get_completion(
            system_prompt=(
                "You are an expert evaluator for MCP benchmark task quality. "
                "Return JSON only."
            ),
            user_prompt=prompt,
            max_tokens=1200,
        )
        evaluation = self.llm.clean_and_parse_json(response)
        evaluation["solvability_score"] = float(evaluation.get("solvability_score", 0.0))
        evaluation["utility_score"] = float(evaluation.get("utility_score", 0.0))
        return evaluation

    def _resolve_thresholds(self, tool_count: int) -> tuple[float, float]:
        """Resolve effective quality thresholds for current tool availability.

        Args:
            tool_count (`int`):
                Number of available tools for the active server scope.

        Returns:
            `tuple[float, float]`:
                Effective ``(solvability_threshold, utility_threshold)``.
        """
        if tool_count <= 1:
            # Single-tool servers cannot form multi-step dependency chains.
            return (min(self.solvability_threshold, 6.0), self.utility_threshold)
        return (self.solvability_threshold, self.utility_threshold)

    @staticmethod
    def _is_search_only_toolset(tools: dict[str, dict[str, Any]]) -> bool:
        """Check whether the active toolset only supports search-style queries.

        Args:
            tools (`dict[str, dict[str, Any]]`):
                Available MCP tool metadata.

        Returns:
            `bool`:
                Whether every tool name indicates a search-only capability.
        """
        if not tools:
            return False

        return all(
            tool_name.rsplit(":", maxsplit=1)[-1].startswith("search_")
            for tool_name in tools
        )

    @staticmethod
    def _is_retrieval_only_toolset(tools: dict[str, dict[str, Any]]) -> bool:
        """Check whether the active tools are limited to retrieval operations.

        Args:
            tools (`dict[str, dict[str, Any]]`):
                Available MCP tool metadata.

        Returns:
            `bool`:
                Whether every tool is a search, download, or read capability.
        """
        if not tools:
            return False

        return all(
            tool_name.rsplit(":", maxsplit=1)[-1].startswith(
                ("search_", "download_", "read_"),
            )
            for tool_name in tools
        )

    def resolve_thresholds(
        self,
        tools: dict[str, dict[str, Any]],
    ) -> tuple[float, float]:
        """Resolve quality thresholds for the active toolset.

        Args:
            tools (`dict[str, dict[str, Any]]`):
                Available MCP tool metadata.

        Returns:
            `tuple[float, float]`:
                Effective ``(solvability_threshold, utility_threshold)``.
        """
        tool_count = len(tools)
        solvability_threshold, utility_threshold = self._resolve_thresholds(
            tool_count=tool_count,
        )
        if self._is_retrieval_only_toolset(tools):
            # Retrieval-only paper servers often require orchestration across
            # search, download, and read steps but still score around 6 on the
            # evaluator's solvability rubric.
            solvability_threshold = min(solvability_threshold, 6.0)
        if self._is_search_only_toolset(tools):
            # Search-only servers can still support useful benchmark tasks,
            # but they rarely satisfy the same dependency depth as richer
            # read/download toolchains.
            solvability_threshold = min(solvability_threshold, 7.0)
        return (solvability_threshold, utility_threshold)

    def meets_quality_threshold(
        self,
        evaluation: dict[str, Any],
        tools: dict[str, dict[str, Any]],
    ) -> bool:
        """Check whether one evaluation passes quality thresholds.

        Args:
            evaluation (`dict[str, Any]`):
                Parsed evaluation result.
            tools (`dict[str, dict[str, Any]]`):
                Available MCP tool metadata.

        Returns:
            `bool`:
                Whether the task should be kept.
        """
        solvability_threshold, utility_threshold = self.resolve_thresholds(
            tools=tools,
        )
        return (
            float(evaluation.get("solvability_score", 0.0)) >= solvability_threshold
            and float(evaluation.get("utility_score", 0.0)) >= utility_threshold
        )


class TaskSynthesizer:
    """Synthesize detailed and fuzzy benchmark tasks with DashScope.

    Args:
        llm_provider (`DashScopeCompletionProvider`):
            DashScope-backed completion provider.
        max_retries_per_task (`int`, optional):
            Maximum attempts for one accepted task.
    """

    def __init__(
        self,
        llm_provider: DashScopeCompletionProvider,
        max_retries_per_task: int = 5,
    ) -> None:
        """Initialize the synthesizer.

        Args:
            llm_provider (`DashScopeCompletionProvider`):
                DashScope-backed completion provider.
            max_retries_per_task (`int`, optional):
                Maximum attempts for one accepted task.
        """
        self.llm = llm_provider
        self.quality_evaluator = TaskQualityEvaluator(llm_provider=llm_provider)
        self.max_retries_per_task = max_retries_per_task

    async def generate_tasks(
        self,
        tools: dict[str, dict[str, Any]],
        server_name: str,
        num_tasks: int = 5,
        distraction_candidates: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate multiple accepted tasks for one server group.

        Args:
            tools (`dict[str, dict[str, Any]]`):
                Available MCP tool metadata.
            server_name (`str`):
                Active server name or combined multi-server name.
            num_tasks (`int`, optional):
                Number of accepted tasks to generate.
            distraction_candidates (`list[str] | None`, optional):
                Candidate server names that should be treated as plausible hard
                negatives for routing confusion.

        Returns:
            `list[dict[str, Any]]`:
                Accepted task records.
        """
        generated: list[dict[str, Any]] = []
        task_index = 0

        while len(generated) < num_tasks:
            attempt = 0
            accepted = False
            _logger.info(
                "[synthesis] %s — targeting accepted task %d/%d",
                server_name,
                len(generated) + 1,
                num_tasks,
            )

            while attempt < self.max_retries_per_task and not accepted:
                _logger.info(
                    "[synthesis] %s — task slot %d attempt %d/%d",
                    server_name,
                    task_index + 1,
                    attempt + 1,
                    self.max_retries_per_task,
                )
                try:
                    detail = await self._generate_single_detailed_task(
                        tools=tools,
                        server_name=server_name,
                        task_index=task_index,
                        distraction_candidates=distraction_candidates,
                    )
                    fuzzy = await self._generate_fuzzy_version(
                        detailed_task=detail["task_description"],
                        tools=tools,
                        server_name=server_name,
                    )
                    candidate = {
                        **detail,
                        "fuzzy_description": fuzzy,
                    }
                    evaluation = await self.quality_evaluator.evaluate_task_quality(
                        task=candidate,
                        tools=tools,
                    )
                except Exception as exc:
                    _logger.warning(
                        "[synthesis] %s — task slot %d attempt %d failed: %s",
                        server_name,
                        task_index + 1,
                        attempt + 1,
                        exc,
                    )
                    attempt += 1
                    continue

                if self.quality_evaluator.meets_quality_threshold(
                    evaluation=evaluation,
                    tools=tools,
                ):
                    generated.append(candidate)
                    accepted = True
                    _logger.info(
                        "[synthesis] %s — accepted task %d/%d on attempt %d (solvability=%.1f, utility=%.1f)",
                        server_name,
                        len(generated),
                        num_tasks,
                        attempt + 1,
                        float(evaluation.get("solvability_score", 0.0)),
                        float(evaluation.get("utility_score", 0.0)),
                    )
                else:
                    _logger.info(
                        "[synthesis] %s — rejected task slot %d attempt %d (solvability=%.1f, utility=%.1f)",
                        server_name,
                        task_index + 1,
                        attempt + 1,
                        float(evaluation.get("solvability_score", 0.0)),
                        float(evaluation.get("utility_score", 0.0)),
                    )
                attempt += 1

            task_index += 1
            if task_index > num_tasks * self.max_retries_per_task * 2:
                _logger.warning(
                    "[synthesis] %s — reached task index cap without enough accepted tasks (%d/%d)",
                    server_name,
                    len(generated),
                    num_tasks,
                )
                break

        return generated

    async def _generate_single_detailed_task(
        self,
        tools: dict[str, dict[str, Any]],
        server_name: str,
        task_index: int,
        distraction_candidates: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate one detailed task draft.

        Args:
            tools (`dict[str, dict[str, Any]]`):
                Available MCP tool metadata.
            server_name (`str`):
                Active server name or combined multi-server name.
            task_index (`int`):
                Zero-based task index.

        Returns:
            `dict[str, Any]`:
                Parsed detailed task object.
        """
        special_notice = ""
        if "openapi" in server_name.lower():
            special_notice = (
                "For OpenAPI-related tasks, only synthesize tasks about "
                "analyzing API specifications rather than calling external APIs."
            )
        dependency_requirement = (
            "- has clear dependency chains between tools;"
            if len(tools) > 1
            else "- can be solved coherently with the single available tool;"
        )
        candidate_text = ""
        if distraction_candidates:
            formatted = ", ".join(distraction_candidates[:20])
            candidate_text = (
                "Potentially confusable alternative servers for routing hard negatives: "
                f"{formatted}\n"
            )

        prompt = f"""You are designing an MCP benchmark task.

Active servers: {server_name}
{special_notice}
{candidate_text}

Available tools:
{_format_tools(tools, limit=30)}

Create one complex, self-contained task that:
- must use tools from all active servers when multiple servers are present;
{dependency_requirement}
- does not rely on local files, external URLs, hidden databases, or user follow-up;
- uses relative dates such as "past 7 days" or "next 3 months" when dates matter;
- includes all concrete values needed for execution;
- reads like a realistic end-user scenario rather than a benchmark checklist;
- contains mild natural ambiguity or surface wording that could superficially fit a few other servers, but still has one correct routing target;
- is not just a templated imperative command sequence;
- ends with a structured deliverable requirement.

When possible, choose 3 to 6 hard-negative servers from the candidate list above.
They should be servers a naive router might confuse with this task based on surface wording, domain overlap, or user phrasing.

Return JSON only with this shape:
{{
  "task_id": "task_{task_index:03d}",
  "task_description": "",
    "dependency_analysis": "",
    "distraction_servers": []
}}"""

        response = await self.llm.get_completion(
            system_prompt=(
                "You are an expert at writing realistic benchmark tasks for "
                "LLM agents using MCP tools. Return JSON only."
            ),
            user_prompt=prompt,
            max_tokens=3200,
        )
        task = self.llm.clean_and_parse_json(response)
        task["task_id"] = f"{_normalize_server_id(server_name)}_{task_index:03d}"
        task["distraction_servers"] = self._sanitize_distraction_servers(
            task.get("distraction_servers", []),
            distraction_candidates or [],
        )
        return task

    async def _generate_fuzzy_version(
        self,
        detailed_task: str,
        tools: dict[str, dict[str, Any]],
        server_name: str,
    ) -> str:
        """Generate a natural-language fuzzy user request.

        Args:
            detailed_task (`str`):
                Detailed task description.
            tools (`dict[str, dict[str, Any]]`):
                Available MCP tool metadata.
            server_name (`str`):
                Active server name or combined multi-server name.

        Returns:
            `str`:
                Conversational fuzzy task description.
        """
        prompt = f"""Rewrite the benchmark task below as a natural user request.

Detailed task:
{detailed_task}

Rules:
- keep all critical factual constraints and numeric values;
- do not mention tool names, server names, MCP, or implementation steps;
- sound like a real person asking for help;
- avoid robotic checklist phrasing or benchmark-style wording;
- keep a little natural ambiguity or contextual noise that could mislead a shallow router, while preserving one correct routing target;
- keep the task answerable without further clarification;
- naturally ask for concrete evidence, numbers, or verifiable support.

Return plain text only."""

        response = await self.llm.get_completion(
            system_prompt=(
                "You rewrite formal benchmark tasks into realistic user "
                "requests while preserving execution-critical details."
            ),
            user_prompt=prompt,
            max_tokens=1800,
        )
        fuzzy = response.strip()
        if not re.search(r"evidence|number|data|source|specific|concrete", fuzzy, re.IGNORECASE):
            fuzzy = (
                f"{fuzzy}\n\nPlease make sure the final answer is backed by "
                "specific data, concrete numbers, or verifiable sources."
            )
        return fuzzy

    @staticmethod
    def _sanitize_distraction_servers(
        suggested_servers: Any,
        candidates: list[str],
    ) -> list[str]:
        """Filter LLM-suggested hard negatives against allowed candidates.

        Args:
            suggested_servers (`Any`):
                Raw server suggestions returned by the model.
            candidates (`list[str]`):
                Allowed confusion candidates.

        Returns:
            `list[str]`:
                Unique validated server names.
        """
        allowed = {name for name in candidates if str(name).strip()}
        output: list[str] = []
        if not isinstance(suggested_servers, list):
            return output
        for item in suggested_servers:
            server_name = str(item).strip()
            if not server_name or server_name not in allowed or server_name in output:
                continue
            output.append(server_name)
        return output


def _format_tools(
    tools: dict[str, dict[str, Any]],
    limit: int = 30,
) -> str:
    """Format tool metadata into prompt-friendly text.

    Args:
        tools (`dict[str, dict[str, Any]]`):
            Available MCP tool metadata.
        limit (`int`, optional):
            Maximum number of tools included in the prompt.

    Returns:
        `str`:
            Prompt-friendly tool summary text.
    """
    lines: list[str] = []
    selected_items = list(tools.items())[:limit]
    for tool_name, tool_info in selected_items:
        lines.append(f"Tool: {tool_name}")
        lines.append(f"Description: {tool_info.get('description', '')}")
        schema = tool_info.get("input_schema") or {}
        if schema:
            lines.append(f"Input schema: {json.dumps(schema, ensure_ascii=False)}")
        lines.append("")

    if len(tools) > limit:
        lines.append(f"... and {len(tools) - limit} more tools")
    return "\n".join(lines)


def _normalize_server_id(server_name: str) -> str:
    """Normalize one server group name into a stable task id prefix.

    Args:
        server_name (`str`):
            Active server name or combined multi-server name.

    Returns:
        `str`:
            Stable identifier prefix.
    """
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", server_name.strip().lower())
    normalized = normalized.strip("_")
    if normalized:
        return normalized
    return f"generated_{random.randint(1000, 9999)}"