# -*- coding: utf-8 -*-
"""Tests for MCPPrewarm routers and build_mcp_speculative_executor."""
import json
import os
import tempfile
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock, patch

from agentscope.agent import ReActAgent
from agentscope.mcp import (
    MCPPrewarmRouter,
    MCPPrewarmKeywordRouter,
    MCPPrewarmSemanticRouter,
    build_mcp_speculative_executor,
)
from agentscope.message import Msg


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

    def test_semantic_router_placeholder_returns_none(self) -> None:
        """Semantic router placeholder currently returns None due TODO/pass."""
        router = MCPPrewarmRouter(method="semantic")
        self.assertIsNone(router(self._make_msg("hello")))

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
        agent = ReActAgent(
            name="worker",
            sys_prompt="test",
            model=DummyModel(),
            formatter=MagicMock(),
            prompt_prewarm_router=router,
            prompt_prewarm_executor=AsyncMock(),
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
        agent = ReActAgent(
            name="worker",
            sys_prompt="test",
            model=DummyModel(),
            formatter=MagicMock(),
            prompt_prewarm_router=router,
            prompt_prewarm_executor=AsyncMock(),
        )
        agent._schedule_prompt_prewarm_task = MagicMock()

        hook = agent.model.stream_tool_speculation_hook
        self.assertIsNotNone(hook)
        result = hook("我需要搜索网页查询 weather", -1, "resp-2")
        if hasattr(result, "__await__"):
            await result

        agent._schedule_prompt_prewarm_task.assert_called_once_with(
            "playwright-mcp",
        )


class BuildMCPSpeculativeExecutorTest(IsolatedAsyncioTestCase):
    """Tests for :func:`build_mcp_speculative_executor`."""

    def _make_registration(
        self, container_name: str, client_name: str
    ) -> MagicMock:
        reg = MagicMock()
        reg.server_config.container_name = container_name
        reg.server_config.client_name = client_name
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

    async def test_empty_registrations_returns_callable(self) -> None:
        """Even with an empty list, calling the executor should not crash."""
        executor = build_mcp_speculative_executor([])
        # Should complete without raising
        await executor("anything")
