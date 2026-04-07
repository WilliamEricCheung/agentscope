# -*- coding: utf-8 -*-
"""Built-in prompt-level speculative pre-warming routers for MCP containers.

Class hierarchy:

- :class:`MCPPrewarmRouter`: base class and factory entrypoint
- :class:`MCPPrewarmKeywordRouter`: keyword matching implementation
- :class:`MCPPrewarmSemanticRouter`: semantic matching placeholder

.. note::
    The keyword mapping JSON has the following schema::

        {
            "playwright-mcp": ["search", "web", "browser", "screenshot"],
            "github-mcp": ["github", "pull request", "repository", "code"]
        }

    Each key is the MCP client/container name that will be passed to the
    ``prompt_prewarm_executor``. Values are lists of lowercase keywords
    (or phrases) that, when found in the user prompt, trigger pre-warming
    for that container.
"""
import json
import os
from typing import TYPE_CHECKING, Awaitable, Callable, Literal

from ..message import Msg
from .._logging import logger

if TYPE_CHECKING:
    from ._mcp_server_config import _DockerMCPRegistrationConfig


_DEFAULT_KEYWORD_MAPPING_FILE = os.path.join(
    os.path.dirname(__file__),
    "prewarm_keyword_mapping.json",
)

# Default mapping shipped with AgentScope — enough to cover the most common
# public MCP images.  Users can override via a custom JSON file.
_DEFAULT_KEYWORD_MAPPING: dict[str, list[str]] = {
    "playwright-mcp": [
        "search",
        "web",
        "browser",
        "url",
        "html",
        "screenshot",
        "click",
        "navigate",
        "page",
    ],
    "github-mcp": [
        "github",
        "pull request",
        "repository",
        "repo",
        "issue",
        "commit",
        "code review",
        "branch",
    ],
}


class MCPPrewarmRouter:
    """Base class and factory for prompt-level pre-warming routers.

    When instantiated directly, this class dispatches to the concrete router
    implementation based on ``method``:

    - ``method='keyword'`` -> :class:`MCPPrewarmKeywordRouter`
    - ``method='semantic'`` -> :class:`MCPPrewarmSemanticRouter`
    """

    def __new__(
        cls,
        mapping: dict[str, list[str]] | str | None = None,
        method: Literal["keyword", "semantic"] = "keyword",
    ) -> "MCPPrewarmRouter":
        if cls is MCPPrewarmRouter:
            if method == "keyword":
                return super().__new__(MCPPrewarmKeywordRouter)
            if method == "semantic":
                return super().__new__(MCPPrewarmSemanticRouter)
            raise ValueError(
                f"Unknown prewarm routing method '{method}'. "
                "Supported: 'keyword', 'semantic'.",
            )
        return super().__new__(cls)

    @classmethod
    def from_json(
        cls,
        path: str,
        method: Literal["keyword", "semantic"] = "keyword",
    ) -> "MCPPrewarmRouter":
        """Create a prewarm router from a JSON mapping file."""
        return cls(mapping=path, method=method)

    def __call__(
        self,
        msg: "Msg | list[Msg] | None",
    ) -> list[str]:
        """Return candidates to prewarm for the given message(s)."""
        raise NotImplementedError


class MCPPrewarmKeywordRouter(MCPPrewarmRouter):
    """Keyword-based prompt-level pre-warming router.

    It scans the text content of the incoming message against a mapping of
    ``{mcp_client_name: [keyword, ...]}``.  On match it returns the matching
    client names so they can be passed to the ``prompt_prewarm_executor``.

    Args:
        mapping (`dict[str, list[str]] | str | None`, optional):
            Keyword mapping definition.  Three accepted forms:

            * ``dict`` — provided directly as a Python dict.
            * ``str`` — path to a JSON file containing the mapping.
            * ``None`` (default) — use the built-in default mapping.
        method (`Literal['keyword', 'semantic']`, optional):
            Routing strategy.  Currently ``'keyword'`` is implemented.
            ``'semantic'`` is reserved for future lightweight embedding-based
            routing and will raise ``NotImplementedError`` when selected.

    Example:
        .. code-block:: python

            from agentscope.mcp import MCPPrewarmKeywordRouter

            router = MCPPrewarmKeywordRouter()
            candidates = router(msg)
            # Returns e.g. ['playwright-mcp'] when prompt contains 'browser'
    """

    def __init__(
        self,
        mapping: dict[str, list[str]] | str | None = None,
        method: Literal["keyword", "semantic"] = "keyword",
    ) -> None:
        """Initialize the keyword pre-warming router.

        Args:
            mapping (`dict[str, list[str]] | str | None`, optional):
                Keyword mapping as a dict, a path to a JSON file, or None to
                use the built-in default mapping.
            method (`Literal['keyword', 'semantic']`, optional):
                Routing method.  Only ``'keyword'`` is currently available.
        """
        if method != "keyword":
            raise ValueError(
                f"Unknown prewarm routing method '{method}'. "
                "Supported: 'keyword'.",
            )
        self.method = method
        self._mapping = self._load_mapping(mapping)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_mapping(
        mapping: dict[str, list[str]] | str | None,
    ) -> dict[str, list[str]]:
        """Load and normalise the keyword mapping.

        Args:
            mapping (`dict[str, list[str]] | str | None`):
                Mapping definition.

        Returns:
            `dict[str, list[str]]`:
                Loaded mapping with lowercase keywords.
        """
        if mapping is None:
            if os.path.exists(_DEFAULT_KEYWORD_MAPPING_FILE):
                with open(_DEFAULT_KEYWORD_MAPPING_FILE, encoding="utf-8") as fh:
                    raw = json.load(fh)
            else:
                raw = _DEFAULT_KEYWORD_MAPPING
        elif isinstance(mapping, str):
            path = os.path.expanduser(mapping)
            if not os.path.exists(path):
                raise FileNotFoundError(
                    f"Keyword mapping file not found: {path}",
                )
            with open(path, encoding="utf-8") as fh:
                raw = json.load(fh)
        else:
            raw = mapping

        # Normalise to lowercase for case-insensitive matching
        return {
            client_name: [kw.lower() for kw in keywords]
            for client_name, keywords in raw.items()
            if not client_name.startswith("_")
        }

    @staticmethod
    def _extract_text(msg: "Msg | list[Msg] | None") -> str:
        """Extract all text content from a message or list of messages.

        Args:
            msg (`Msg | list[Msg] | None`):
                Input message(s).

        Returns:
            `str`:
                Concatenated lower-cased text.
        """
        if msg is None:
            return ""

        msgs = [msg] if isinstance(msg, Msg) else list(msg)
        parts: list[str] = []
        for m in msgs:
            text = m.get_text_content()
            if text:
                parts.append(text)
        return " ".join(parts).lower()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def __call__(
        self,
        msg: "Msg | list[Msg] | None",
    ) -> list[str]:
        """Return MCP client names whose keywords appear in the message.

        Args:
            msg (`Msg | list[Msg] | None`):
                The incoming user message(s).

        Returns:
            `list[str]`:
                Deduplicated list of candidate client names to pre-warm.
        """
        text = self._extract_text(msg)
        if not text:
            return []

        candidates: list[str] = []
        for client_name, keywords in self._mapping.items():
            for kw in keywords:
                if kw in text:
                    candidates.append(client_name)
                    logger.debug(
                        "[PrewarmRouter] keyword '%s' matched -> '%s'",
                        kw,
                        client_name,
                    )
                    break  # one match per client is enough

        return candidates


class MCPPrewarmSemanticRouter(MCPPrewarmRouter):
    """Semantic pre-warming router placeholder.

    This implementation is intentionally left as TODO + pass for now.
    """

    def __init__(
        self,
        mapping: dict[str, list[str]] | str | None = None,
        method: Literal["keyword", "semantic"] = "semantic",
    ) -> None:
        """Initialize semantic router placeholder."""
        if method != "semantic":
            raise ValueError(
                f"Unknown prewarm routing method '{method}'. "
                "Supported: 'semantic'.",
            )
        self.method = method
        self.mapping = mapping
        # TODO: initialize semantic index and embedding model.
        pass

    def __call__(
        self,
        msg: "Msg | list[Msg] | None",
    ) -> list[str]:
        """Return candidates for semantic pre-warming.

        TODO: implement semantic retrieval and ranking.
        """
        pass

def build_mcp_speculative_executor(
    registrations: "list[_DockerMCPRegistrationConfig]",
) -> Callable[[str], Awaitable[None]]:
    """Build a speculative pre-warming executor from registration configs.

    The returned callable accepts a candidate key (either ``container_name``
    or ``client_name``) and calls
    :func:`~agentscope.mcp._mcp_server_helper._speculative_ensure_local_docker_mcp_server`
    asynchronously without polluting formal usage metrics.

    Args:
        registrations (`list[_DockerMCPRegistrationConfig]`):
            List of Docker MCP registration configurations.  Both
            ``server_config.container_name`` and ``server_config.client_name``
            are indexed so either can be used as a routing key.

    Returns:
        `Callable[[str], Awaitable[None]]`:
            An async executor that accepts one candidate key per call.

    Example:
        .. code-block:: python

            from agentscope.mcp import (
                MCPPrewarmKeywordRouter,
                build_mcp_speculative_executor,
            )

            executor = build_mcp_speculative_executor([
                playwright_registration,
                github_registration,
            ])
            router = MCPPrewarmKeywordRouter.from_json("prewarm_mapping.json")

            agent = ReActAgent(
                ...
                prompt_prewarm_router=router,
                prompt_prewarm_executor=executor,
            )
    """
    # Build a lookup keyed by both container_name and client_name so the
    # JSON mapping can use either form.
    lookup: dict[str, "_DockerMCPRegistrationConfig"] = {}
    for reg in registrations:
        lookup[reg.server_config.container_name] = reg
        lookup[reg.server_config.client_name] = reg

    async def _executor(candidate: str) -> None:
        reg = lookup.get(candidate)
        if reg is None:
            logger.debug(
                "[PrewarmExecutor] no registration found for '%s', skipping.",
                candidate,
            )
            return

        # Lazy import to satisfy the lazy-loading convention.
        from ._mcp_server_helper import (
            _speculative_ensure_local_docker_mcp_server,
        )

        logger.debug(
            "[PrewarmExecutor] speculatively warming '%s' ...",
            candidate,
        )
        await _speculative_ensure_local_docker_mcp_server(
            config=reg.server_config,
            docker_run_command=reg.docker_run_command,
            headers=reg.headers,
        )

    return _executor
