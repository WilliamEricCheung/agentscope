# -*- coding: utf-8 -*-
"""Tests for MCPPrewarm routers and build_mcp_speculative_executor."""
import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np

from agentscope.agent import ReActAgent
from agentscope.mcp import (
    MCPLaplaceController,
    MCPLaplaceControllerConfig,
    MCPPrewarmHybridRouter,
    MCPPrewarmRouter,
    MCPPrewarmKeywordRouter,
    MCPPrewarmSemanticRouter,
    build_mcp_speculative_executor,
)
from agentscope.message import Msg
from agentscope.tool import ToolResponse


class MCPPrewarmKeywordRouterTest(TestCase):
    """Tests for :class:`MCPPrewarmKeywordRouter`."""

    def _make_msg(self, text: str) -> Msg:
        return Msg(name="user", content=text, role="user")

    # ------------------------------------------------------------------
    # Mapping loading
    # ------------------------------------------------------------------

    def test_default_mapping_loaded_when_none(self) -> None:
        """Router initialised with None should use the built-in mapping."""
        router = MCPPrewarmKeywordRouter()
        self.assertIn("playwright-mcp", router._mapping)
        self.assertIn("github-mcp", router._mapping)

    def test_dict_mapping_accepted(self) -> None:
        """Router can be initialised with an explicit dict."""
        router = MCPPrewarmKeywordRouter(
            mapping={"my-svc": ["foo", "bar"]}
        )
        self.assertEqual(router._mapping, {"my-svc": ["foo", "bar"]})

    def test_json_file_mapping_loaded(self) -> None:
        """Router can load mapping from a JSON file path."""
        mapping = {"json-svc": ["alpha", "beta"]}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            json.dump(mapping, fh)
            path = fh.name
        try:
            router = MCPPrewarmKeywordRouter(mapping=path)
            self.assertEqual(router._mapping, {"json-svc": ["alpha", "beta"]})
        finally:
            os.unlink(path)

    def test_missing_json_file_raises(self) -> None:
        """A non-existent JSON path should raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            MCPPrewarmKeywordRouter(mapping="/no/such/file.json")

    def test_from_json_classmethod(self) -> None:
        """from_json() should create a router equivalent to passing path."""
        mapping = {"svc": ["kw1"]}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            json.dump(mapping, fh)
            path = fh.name
        try:
            router = MCPPrewarmKeywordRouter.from_json(path)
            self.assertEqual(router._mapping, {"svc": ["kw1"]})
        finally:
            os.unlink(path)

    def test_base_router_dispatches_to_keyword_by_default(self) -> None:
        """Base router should dispatch to keyword router by default."""
        router = MCPPrewarmRouter()
        self.assertIsInstance(router, MCPPrewarmKeywordRouter)

    def test_base_router_dispatches_to_semantic_when_specified(self) -> None:
        """Base router should dispatch to semantic router for method semantic."""
        router = MCPPrewarmRouter(method="semantic")
        self.assertIsInstance(router, MCPPrewarmSemanticRouter)

    def test_base_router_dispatches_to_hybrid_when_specified(self) -> None:
        """Base router should dispatch to hybrid router for method hybrid."""
        router = MCPPrewarmRouter(method="hybrid")
        self.assertIsInstance(router, MCPPrewarmHybridRouter)

    def test_semantic_router_uses_retrieval_artifact(self) -> None:
        """Semantic router should return retrieval-based prewarm candidates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_dir = Path(tmpdir)
            (artifact_dir / "semantic_router_retrieval.json").write_text(
                json.dumps(
                    {
                        "vocabulary": {"w:wikipedia": 0},
                        "char_ngram_range": [3, 5],
                        "use_word_bigrams": False,
                        "top_neighbors": 1,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            np.savez_compressed(
                artifact_dir / "semantic_router_retrieval.npz",
                idf=np.array([1.0], dtype=np.float32),
                train_matrix=np.array([[1.0]], dtype=np.float32),
                train_labels=np.array(["Wikipedia"], dtype=object),
                train_task_ids=np.array(["wiki_000"], dtype=object),
            )
            (artifact_dir / "grid_search_results.json").write_text(
                json.dumps(
                    {
                        "best": {
                            "threshold": 0.05,
                            "top_k": 1,
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            router = MCPPrewarmSemanticRouter(mapping=str(artifact_dir))
            self.assertEqual(router(self._make_msg("Please search Wikipedia")), ["Wikipedia"])

    def test_unknown_method_raises(self) -> None:
        """Unknown method string should raise ValueError."""
        with self.assertRaises(ValueError):
            MCPPrewarmKeywordRouter(method="fuzzy")  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Keyword matching
    # ------------------------------------------------------------------

    def test_keyword_match_returns_client(self) -> None:
        """A message containing a keyword should return the matching client."""
        router = MCPPrewarmKeywordRouter(
            mapping={"playwright-mcp": ["browser", "web"]}
        )
        result = router(self._make_msg("Open the browser and search"))
        self.assertEqual(result, ["playwright-mcp"])

    def test_keyword_case_insensitive(self) -> None:
        """Keyword matching is case-insensitive."""
        router = MCPPrewarmKeywordRouter(
            mapping={"svc": ["Browser"]}
        )
        result = router(self._make_msg("Use BROWSER to load the page"))
        self.assertEqual(result, ["svc"])

    def test_no_keyword_match_returns_empty(self) -> None:
        """A message with no matching keyword should return an empty list."""
        router = MCPPrewarmKeywordRouter(
            mapping={"svc": ["browser"]}
        )
        result = router(self._make_msg("Just a plain text message"))
        self.assertEqual(result, [])

    def test_multiple_clients_matched(self) -> None:
        """Multiple clients can match from a single message."""
        router = MCPPrewarmKeywordRouter(
            mapping={
                "playwright-mcp": ["browser"],
                "github-mcp": ["repository"],
            }
        )
        result = router(self._make_msg("Search the browser and check the repository"))
        self.assertIn("playwright-mcp", result)
        self.assertIn("github-mcp", result)
        self.assertEqual(len(result), 2)

    def test_each_client_matched_once(self) -> None:
        """Even if multiple keywords match, a client appears only once."""
        router = MCPPrewarmKeywordRouter(
            mapping={"svc": ["foo", "bar"]}
        )
        result = router(self._make_msg("foo and bar are both here"))
        self.assertEqual(result, ["svc"])

    def test_none_message_returns_empty(self) -> None:
        """None message should return an empty list without error."""
        router = MCPPrewarmKeywordRouter(mapping={"svc": ["kw"]})
        self.assertEqual(router(None), [])

    def test_list_of_messages(self) -> None:
        """List of Msg objects should all have their text concatenated."""
        router = MCPPrewarmKeywordRouter(mapping={"svc": ["kw"]})
        msgs = [
            self._make_msg("hello"),
            self._make_msg("contains kw here"),
        ]
        self.assertEqual(router(msgs), ["svc"])

    def test_string_fragment_can_drive_stream_level_match(self) -> None:
        """Raw streamed tool-name fragments should also be routable."""
        router = MCPPrewarmKeywordRouter(
            mapping={"playwright-mcp": ["browser"]}
        )
        self.assertEqual(router("browser_navigate"), ["playwright-mcp"])

    def test_hybrid_router_prefers_keyword_before_semantic(self) -> None:
        """Hybrid router should short-circuit on L1 keyword matches."""
        router = MCPPrewarmHybridRouter(
            mapping={"keyword_mapping": {"playwright-mcp": ["browser"]}},
        )

        with patch.object(
            router._semantic_router,
            "__call__",
            side_effect=AssertionError("semantic router should not be called"),
        ):
            result = router(self._make_msg("Open the browser please"))

        self.assertEqual(result, ["playwright-mcp"])
        self.assertEqual(router.last_route_method, "keyword")

    def test_hybrid_router_falls_back_to_semantic_on_keyword_miss(self) -> None:
        """Hybrid router should use L2 semantic routing after L1 miss."""
        router = MCPPrewarmHybridRouter(
            mapping={"keyword_mapping": {"playwright-mcp": ["browser"]}},
        )

        semantic_mock = MagicMock(return_value=["Wikipedia"])
        router._semantic_router = semantic_mock
        result = router(self._make_msg("Explain climate policy background"))

        semantic_mock.assert_called_once()
        self.assertEqual(result, ["Wikipedia"])
        self.assertEqual(router.last_route_method, "semantic")


class ReActAgentStreamPrewarmHookTest(IsolatedAsyncioTestCase):
    """Tests for stream-level prewarm hook installation on ReActAgent."""

    async def test_stream_tool_name_can_trigger_keyword_prewarm(self) -> None:
        """Explicit streamed tool names should schedule dynamic prewarm."""

        class DummyModel:
            stream_tool_speculation_hook = None
            stream_text_speculation_interval_tokens = None
            stream = True

        router = MCPPrewarmKeywordRouter(
            mapping={"playwright-mcp": ["browser"]}
        )
        controller = MCPLaplaceController(
            prompt_prewarm_router=router,
            prompt_prewarm_executor=AsyncMock(),
        )
        agent = ReActAgent(
            name="worker",
            sys_prompt="test",
            model=DummyModel(),
            formatter=MagicMock(),
            mcp_laplace_controller=controller,
        )
        agent._schedule_prompt_prewarm_task = MagicMock()

        self.assertIsNone(agent.model.stream_text_speculation_interval_tokens)

        hook = agent.model.stream_tool_speculation_hook
        self.assertIsNotNone(hook)
        result = hook("browser_navigate", 0, "resp-1")
        if hasattr(result, "__await__"):
            await result

        agent._schedule_prompt_prewarm_task.assert_called_once_with(
            "playwright-mcp",
            stage="stream",
        )

    async def test_stream_reasoning_text_can_trigger_keyword_prewarm(
        self,
    ) -> None:
        """Periodic reasoning-text snapshots should also schedule prewarm."""

        class DummyModel:
            stream_tool_speculation_hook = None
            stream_text_speculation_interval_tokens = None
            stream = True

        router = MCPPrewarmKeywordRouter(
            mapping={"playwright-mcp": ["搜索", "网页", "weather"]}
        )
        controller = MCPLaplaceController(
            prompt_prewarm_router=router,
            prompt_prewarm_executor=AsyncMock(),
        )
        agent = ReActAgent(
            name="worker",
            sys_prompt="test",
            model=DummyModel(),
            formatter=MagicMock(),
            mcp_laplace_controller=controller,
        )
        agent._schedule_prompt_prewarm_task = MagicMock()

        hook = agent.model.stream_tool_speculation_hook
        self.assertIsNotNone(hook)
        result = hook("我需要搜索网页查询 weather", -1, "resp-2")
        if hasattr(result, "__await__"):
            await result

        agent._schedule_prompt_prewarm_task.assert_called_once_with(
            "playwright-mcp",
            stage="stream",
        )


class BuildMCPSpeculativeExecutorTest(IsolatedAsyncioTestCase):
    """Tests for :func:`build_mcp_speculative_executor`."""

    def _make_registration(
        self,
        container_name: str,
        client_name: str,
        server_name: str | None = None,
    ) -> MagicMock:
        reg = MagicMock()
        reg.server_config.container_name = container_name
        reg.server_config.client_name = client_name
        reg.server_name = server_name
        reg.docker_run_command = ["docker", "run", container_name]
        reg.headers = None
        return reg

    async def test_executor_routes_by_container_name(self) -> None:
        """Executor should find a registration keyed by container_name."""
        reg = self._make_registration("playwright-mcp", "playwright-mcp")
        executor = build_mcp_speculative_executor([reg])

        speculative_mock = AsyncMock()
        with patch(
            "agentscope.mcp._mcp_server_helper"
            "._speculative_ensure_local_docker_mcp_server",
            speculative_mock,
        ):
            await executor("playwright-mcp")

        speculative_mock.assert_awaited_once_with(
            config=reg.server_config,
            docker_run_command=reg.docker_run_command,
            headers=reg.headers,
        )

    async def test_executor_routes_by_client_name(self) -> None:
        """Executor should also match when keyed by client_name."""
        # GitHub: container_name="github-mcp", client_name="github"
        reg = self._make_registration("github-mcp", "github")
        executor = build_mcp_speculative_executor([reg])

        speculative_mock = AsyncMock()
        with patch(
            "agentscope.mcp._mcp_server_helper"
            "._speculative_ensure_local_docker_mcp_server",
            speculative_mock,
        ):
            await executor("github")  # routed via client_name

        speculative_mock.assert_awaited_once()

    async def test_unknown_candidate_silently_skipped(self) -> None:
        """An unrecognised candidate key should not raise an error."""
        reg = self._make_registration("playwright-mcp", "playwright-mcp")
        executor = build_mcp_speculative_executor([reg])

        speculative_mock = AsyncMock()
        with patch(
            "agentscope.mcp._mcp_server_helper"
            "._speculative_ensure_local_docker_mcp_server",
            speculative_mock,
        ):
            await executor("unknown-svc")

        speculative_mock.assert_not_awaited()

    async def test_executor_routes_by_server_name(self) -> None:
        """Executor should also match when keyed by server_name."""
        reg = self._make_registration(
            "laplace-wikipedia",
            "laplace-wikipedia",
            server_name="Wikipedia",
        )
        executor = build_mcp_speculative_executor([reg])

        speculative_mock = AsyncMock()
        with patch(
            "agentscope.mcp._mcp_server_helper"
            "._speculative_ensure_local_docker_mcp_server",
            speculative_mock,
        ):
            await executor("Wikipedia")

        speculative_mock.assert_awaited_once()

    async def test_empty_registrations_returns_callable(self) -> None:
        """Even with an empty list, calling the executor should not crash."""
        executor = build_mcp_speculative_executor([])
        # Should complete without raising
        await executor("anything")


class ReActAgentPredictivePrewarmHookTest(IsolatedAsyncioTestCase):
    """Integration tests for predictive warmer hook in ReActAgent."""

    async def _single_chunk_tool_result(self):
        """Build a minimal async tool-result generator."""
        yield ToolResponse(
            content=[{"type": "text", "text": "ok"}],
            is_last=True,
        )

    async def test_predictive_warmer_triggers_after_tool_completion(self) -> None:
        """Successful MCP tool completion should trigger predictive prewarm."""

        class DummyModel:
            stream_tool_speculation_hook = None
            stream_text_speculation_interval_tokens = None
            stream = False

        predictive_warmer = MagicMock()
        predictive_warmer.predict_next_servers.return_value = ["Weather Data"]
        controller = MCPLaplaceController(
            prompt_prewarm_executor=AsyncMock(),
            predictive_warmer=predictive_warmer,
        )

        agent = ReActAgent(
            name="worker",
            sys_prompt="test",
            model=DummyModel(),
            formatter=MagicMock(),
            mcp_laplace_controller=controller,
        )

        agent._schedule_prompt_prewarm_task = MagicMock()
        agent.toolkit.call_tool_function = AsyncMock(
            return_value=self._single_chunk_tool_result(),
        )
        agent.toolkit.tools["maps_geocode"] = MagicMock(mcp_name="Google Maps")

        await agent._acting(
            {
                "id": "tool-1",
                "type": "tool_use",
                "name": "maps_geocode",
                "input": {},
            },
        )

        predictive_warmer.predict_next_servers.assert_called_once_with(
            current_server="Google Maps",
        )
        agent._schedule_prompt_prewarm_task.assert_called_once_with(
            "Weather Data",
            stage="predictive",
        )

    async def test_predictive_warmer_respects_disable_switch(self) -> None:
        """Predictive prewarm should be skipped when switch is disabled."""

        class DummyModel:
            stream_tool_speculation_hook = None
            stream_text_speculation_interval_tokens = None
            stream = False

        predictive_warmer = MagicMock()
        predictive_warmer.predict_next_servers.return_value = ["Weather Data"]
        controller = MCPLaplaceController(
            prompt_prewarm_executor=AsyncMock(),
            predictive_warmer=predictive_warmer,
            config=MCPLaplaceControllerConfig(predictive_warmer_enabled=False),
        )

        agent = ReActAgent(
            name="worker",
            sys_prompt="test",
            model=DummyModel(),
            formatter=MagicMock(),
            mcp_laplace_controller=controller,
        )

        agent._schedule_prompt_prewarm_task = MagicMock()
        agent.toolkit.call_tool_function = AsyncMock(
            return_value=self._single_chunk_tool_result(),
        )
        agent.toolkit.tools["maps_geocode"] = MagicMock(mcp_name="Google Maps")

        await agent._acting(
            {
                "id": "tool-2",
                "type": "tool_use",
                "name": "maps_geocode",
                "input": {},
            },
        )

        predictive_warmer.predict_next_servers.assert_not_called()
        agent._schedule_prompt_prewarm_task.assert_not_called()

    async def test_single_controller_injection_triggers_c1_and_c2(self) -> None:
        """One controller should drive both prompt and predictive prewarm."""

        class DummyModel:
            stream_tool_speculation_hook = None
            stream_text_speculation_interval_tokens = None
            stream = False

        router = MagicMock(return_value=["playwright-mcp"])
        executor = AsyncMock()
        predictive_warmer = MagicMock()
        predictive_warmer.predict_next_servers.return_value = ["Weather Data"]

        controller = MCPLaplaceController(
            prompt_prewarm_router=router,
            prompt_prewarm_executor=executor,
            predictive_warmer=predictive_warmer,
            config=MCPLaplaceControllerConfig(predictive_warmer_enabled=True),
        )

        agent = ReActAgent(
            name="worker",
            sys_prompt="test",
            model=DummyModel(),
            formatter=MagicMock(),
            mcp_laplace_controller=controller,
        )

        await agent._trigger_prompt_prewarm(Msg("user", "hello", "user"))
        router.assert_called_once()

        agent._schedule_prompt_prewarm_task = MagicMock()
        agent.toolkit.call_tool_function = AsyncMock(
            return_value=self._single_chunk_tool_result(),
        )
        agent.toolkit.tools["maps_geocode"] = MagicMock(mcp_name="Google Maps")

        await agent._acting(
            {
                "id": "tool-3",
                "type": "tool_use",
                "name": "maps_geocode",
                "input": {},
            },
        )

        predictive_warmer.predict_next_servers.assert_called_once_with(
            current_server="Google Maps",
        )
        agent._schedule_prompt_prewarm_task.assert_any_call(
            "Weather Data",
            stage="predictive",
        )

    async def test_controller_telemetry_collects_stage_events(self) -> None:
        """Controller telemetry should include route/schedule/execute events."""

        class DummyModel:
            stream_tool_speculation_hook = None
            stream_text_speculation_interval_tokens = None
            stream = False

        router = MagicMock(return_value=["playwright-mcp", "playwright-mcp"])
        executor = AsyncMock(return_value=None)
        controller = MCPLaplaceController(
            prompt_prewarm_router=router,
            prompt_prewarm_executor=executor,
            config=MCPLaplaceControllerConfig(
                telemetry_enabled=True,
                telemetry_max_events=64,
            ),
        )

        agent = ReActAgent(
            name="worker",
            sys_prompt="test",
            model=DummyModel(),
            formatter=MagicMock(),
            mcp_laplace_controller=controller,
        )

        await agent._trigger_prompt_prewarm(Msg("user", "hello", "user"))
        router.assert_called_once()
        await asyncio.sleep(0)

        telemetry = controller.get_telemetry_snapshot()
        self.assertGreaterEqual(telemetry["stats"]["prompt_route_calls"], 1)
        self.assertGreaterEqual(telemetry["stats"]["schedule_attempts"], 1)
        self.assertGreaterEqual(telemetry["stats"]["executor_runs"], 1)
        event_names = {
            str(event.get("event", ""))
            for event in telemetry["events"]
        }
        self.assertIn("route_prompt_candidates", event_names)
        self.assertIn("prewarm_schedule", event_names)
        self.assertIn("prewarm_executor", event_names)
