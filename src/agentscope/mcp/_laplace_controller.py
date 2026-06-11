# -*- coding: utf-8 -*-
"""Minimal Laplace controller for MCP prewarm orchestration.

This controller centralizes C1 (prompt router) and C2 (predictive warmer)
switches/configurations so the agent can receive one controller object
instead of multiple independent prewarm parameters.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import inspect
import time
from typing import Any, Awaitable, Callable

from .._logging import logger


@dataclass
class MCPLaplaceControllerConfig:
    """Configuration for :class:`MCPLaplaceController`.

    Args:
        prompt_prewarm_enabled (`bool`, defaults to `True`):
            Whether prompt prewarm (C1) is enabled.
        predictive_warmer_enabled (`bool`, defaults to `True`):
            Whether predictive prewarm (C2) is enabled.
        auto_create_predictive_warmer (`bool`, defaults to `True`):
            Whether to create a default predictive warmer when C2 is enabled
            and the warmer is not provided.
        telemetry_enabled (`bool`, defaults to `True`):
            Whether to record unified controller telemetry.
        telemetry_max_events (`int`, defaults to `2000`):
            Max number of telemetry events retained in memory.
        telemetry_name (`str`, defaults to `"mcp_laplace_controller"`):
            Logical telemetry source name.
    """

    prompt_prewarm_enabled: bool = True
    predictive_warmer_enabled: bool = True
    auto_create_predictive_warmer: bool = True
    telemetry_enabled: bool = True
    telemetry_max_events: int = 2000
    telemetry_name: str = "mcp_laplace_controller"


class MCPLaplaceController:
    """A minimal controller that coordinates MCP prewarm stages.

    Args:
        prompt_prewarm_router (`Callable | None`, optional):
            C1 router that maps prompt/stream text to prewarm candidates.
        prompt_prewarm_executor (`Callable | None`, optional):
            Executor used to prewarm one candidate.
        predictive_warmer (`Any | None`, optional):
            C2 predictive warmer instance.
        prompt_prewarm_enabled (`bool`, defaults to `True`):
            Whether prompt prewarm (C1) is enabled.
        predictive_warmer_enabled (`bool`, defaults to `True`):
            Whether predictive prewarm (C2) is enabled.
        auto_create_predictive_warmer (`bool`, defaults to `True`):
            When true and C2 is enabled, create a default predictive warmer
            if none is provided.
    """

    def __init__(
        self,
        prompt_prewarm_router: Callable[..., Any] | None = None,
        prompt_prewarm_executor: Callable[[str], Any | Awaitable[Any]] | None = None,
        predictive_warmer: Any | None = None,
        config: MCPLaplaceControllerConfig | dict[str, Any] | None = None,
    ) -> None:
        """Initialize controller state."""
        if config is None:
            config_obj = MCPLaplaceControllerConfig()
        elif isinstance(config, dict):
            config_obj = MCPLaplaceControllerConfig(**config)
        else:
            config_obj = config

        self.config = config_obj
        self.prompt_prewarm_router = prompt_prewarm_router
        self.prompt_prewarm_executor = prompt_prewarm_executor
        self.prompt_prewarm_enabled = bool(config_obj.prompt_prewarm_enabled)

        self.predictive_warmer_enabled = bool(config_obj.predictive_warmer_enabled)
        self.predictive_warmer = predictive_warmer

        self._telemetry_enabled = bool(config_obj.telemetry_enabled)
        self._telemetry_max_events = max(1, int(config_obj.telemetry_max_events))
        self._telemetry_name = str(config_obj.telemetry_name)
        self._telemetry_events: list[dict[str, Any]] = []
        self._telemetry_stats: dict[str, int] = {
            "prompt_route_calls": 0,
            "prompt_route_errors": 0,
            "predict_calls": 0,
            "predict_errors": 0,
            "schedule_attempts": 0,
            "schedule_accepted": 0,
            "executor_runs": 0,
            "executor_errors": 0,
        }

        if (
            self.predictive_warmer_enabled
            and self.predictive_warmer is None
            and self.prompt_prewarm_executor is not None
            and config_obj.auto_create_predictive_warmer
        ):
            try:
                from ._predictive_warmer import MCPPredictiveWarmer

                self.predictive_warmer = MCPPredictiveWarmer()
                self._record_telemetry(
                    event="predictive_warmer_auto_created",
                    stage="controller",
                    status="success",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to initialize default MCPPredictiveWarmer in "
                    "MCPLaplaceController: %s",
                    exc,
                )
                self._record_telemetry(
                    event="predictive_warmer_auto_created",
                    stage="controller",
                    status="failed",
                    error=str(exc),
                )

    def _record_telemetry(self, **event: Any) -> None:
        """Record one telemetry event when telemetry is enabled."""
        if not self._telemetry_enabled:
            return

        payload = {
            "ts": round(time.time() * 1000, 3),
            "source": self._telemetry_name,
            **event,
        }
        self._telemetry_events.append(payload)
        if len(self._telemetry_events) > self._telemetry_max_events:
            self._telemetry_events = self._telemetry_events[
                -self._telemetry_max_events :
            ]

    def clear_telemetry(self) -> None:
        """Clear in-memory telemetry events and counters."""
        self._telemetry_events.clear()
        for key in list(self._telemetry_stats):
            self._telemetry_stats[key] = 0

    def get_telemetry_snapshot(self, reset: bool = False) -> dict[str, Any]:
        """Return telemetry snapshot across C1/C2 routing and execution.

        Args:
            reset (`bool`, defaults to `False`):
                Whether to clear telemetry after snapshotting.

        Returns:
            `dict[str, Any]`:
                Snapshot with config, counters, and event list.
        """
        snapshot = {
            "config": asdict(self.config),
            "stats": dict(self._telemetry_stats),
            "events": list(self._telemetry_events),
        }
        if reset:
            self.clear_telemetry()
        return snapshot

    def note_schedule_attempt(
        self,
        candidate: str,
        stage: str,
        accepted: bool,
        reason: str | None = None,
    ) -> None:
        """Record one scheduling attempt for a prewarm candidate."""
        self._telemetry_stats["schedule_attempts"] += 1
        if accepted:
            self._telemetry_stats["schedule_accepted"] += 1

        self._record_telemetry(
            event="prewarm_schedule",
            stage=stage,
            candidate=candidate,
            status="accepted" if accepted else "skipped",
            reason=reason,
        )

    async def execute_prompt_candidate(
        self,
        candidate: str,
        stage: str = "prompt",
    ) -> None:
        """Run the prompt prewarm executor with unified telemetry."""
        executor = self.prompt_prewarm_executor
        if executor is None:
            self._record_telemetry(
                event="prewarm_executor",
                stage=stage,
                candidate=candidate,
                status="skipped",
                reason="no_executor",
            )
            return

        started = time.perf_counter()
        self._telemetry_stats["executor_runs"] += 1
        self._record_telemetry(
            event="prewarm_executor",
            stage=stage,
            candidate=candidate,
            status="started",
        )

        try:
            result = executor(candidate)
            if inspect.isawaitable(result):
                await result
            self._record_telemetry(
                event="prewarm_executor",
                stage=stage,
                candidate=candidate,
                status="completed",
                duration_ms=round((time.perf_counter() - started) * 1000, 3),
            )
        except Exception as exc:  # noqa: BLE001
            self._telemetry_stats["executor_errors"] += 1
            self._record_telemetry(
                event="prewarm_executor",
                stage=stage,
                candidate=candidate,
                status="failed",
                duration_ms=round((time.perf_counter() - started) * 1000, 3),
                error=str(exc),
            )
            raise

    @property
    def has_prompt_prewarm(self) -> bool:
        """Whether C1 prompt prewarm path is runnable."""
        return (
            self.prompt_prewarm_enabled
            and self.prompt_prewarm_router is not None
            and self.prompt_prewarm_executor is not None
        )

    @property
    def has_predictive_prewarm(self) -> bool:
        """Whether C2 predictive prewarm path is runnable."""
        return (
            self.predictive_warmer_enabled
            and self.predictive_warmer is not None
            and self.prompt_prewarm_executor is not None
        )

    async def route_prompt_candidates(
        self,
        msg: Any,
    ) -> list[str]:
        """Route prompt/stream text into C1 candidates.

        Args:
            msg (`Any`):
                Message payload accepted by the configured router.

        Returns:
            `list[str]`:
                Routed candidate keys.
        """
        self._telemetry_stats["prompt_route_calls"] += 1
        started = time.perf_counter()

        if not self.has_prompt_prewarm:
            self._record_telemetry(
                event="route_prompt_candidates",
                stage="prompt",
                status="skipped",
                reason="prompt_prewarm_unavailable",
            )
            return []

        router = self.prompt_prewarm_router
        if router is None:
            self._record_telemetry(
                event="route_prompt_candidates",
                stage="prompt",
                status="skipped",
                reason="missing_router",
            )
            return []

        try:
            result = router(msg)
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:  # noqa: BLE001
            self._telemetry_stats["prompt_route_errors"] += 1
            self._record_telemetry(
                event="route_prompt_candidates",
                stage="prompt",
                status="failed",
                duration_ms=round((time.perf_counter() - started) * 1000, 3),
                error=str(exc),
            )
            raise

        if not result:
            self._record_telemetry(
                event="route_prompt_candidates",
                stage="prompt",
                status="completed",
                candidate_count=0,
                duration_ms=round((time.perf_counter() - started) * 1000, 3),
            )
            return []

        candidates = [str(candidate) for candidate in set(result)]
        self._record_telemetry(
            event="route_prompt_candidates",
            stage="prompt",
            status="completed",
            candidate_count=len(candidates),
            duration_ms=round((time.perf_counter() - started) * 1000, 3),
        )
        return candidates

    async def predict_candidates(
        self,
        current_server: str | None,
    ) -> list[str]:
        """Predict C2 candidates from current server.

        Args:
            current_server (`str | None`):
                The current server label.

        Returns:
            `list[str]`:
                Predicted candidate keys.
        """
        self._telemetry_stats["predict_calls"] += 1
        started = time.perf_counter()

        if not self.has_predictive_prewarm or not current_server:
            self._record_telemetry(
                event="predict_candidates",
                stage="predictive",
                status="skipped",
                reason="predictive_prewarm_unavailable",
                current_server=current_server,
            )
            return []

        warmer = self.predictive_warmer
        if warmer is None:
            self._record_telemetry(
                event="predict_candidates",
                stage="predictive",
                status="skipped",
                reason="missing_predictive_warmer",
                current_server=current_server,
            )
            return []

        try:
            if hasattr(warmer, "predict_next_servers"):
                result = warmer.predict_next_servers(current_server=current_server)
            else:
                result = warmer(current_server)

            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:  # noqa: BLE001
            self._telemetry_stats["predict_errors"] += 1
            self._record_telemetry(
                event="predict_candidates",
                stage="predictive",
                status="failed",
                current_server=current_server,
                duration_ms=round((time.perf_counter() - started) * 1000, 3),
                error=str(exc),
            )
            raise

        if not result:
            self._record_telemetry(
                event="predict_candidates",
                stage="predictive",
                status="completed",
                current_server=current_server,
                candidate_count=0,
                duration_ms=round((time.perf_counter() - started) * 1000, 3),
            )
            return []

        candidates = [str(candidate) for candidate in set(result)]
        self._record_telemetry(
            event="predict_candidates",
            stage="predictive",
            status="completed",
            current_server=current_server,
            candidate_count=len(candidates),
            duration_ms=round((time.perf_counter() - started) * 1000, 3),
        )
        return candidates
