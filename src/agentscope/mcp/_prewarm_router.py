# -*- coding: utf-8 -*-
"""Built-in prompt-level speculative pre-warming routers for MCP containers.

Class hierarchy:

- :class:`MCPPrewarmRouter`: base class and factory entrypoint
- :class:`MCPPrewarmKeywordRouter`: keyword matching implementation
- :class:`MCPPrewarmSemanticRouter`: semantic matching implementation
- :class:`MCPPrewarmHybridRouter`: L1 keyword then L2 semantic cascade

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
import math
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Awaitable, Callable, Literal

from ..message import Msg
from .._logging import logger

if TYPE_CHECKING:
    from ._mcp_server_config import _DockerMCPRegistrationConfig


_DEFAULT_KEYWORD_MAPPING_FILE = os.path.join(
    os.path.dirname(__file__),
    "prewarm_keyword_mapping.json",
)
_SEMANTIC_ROUTER_ARTIFACT_ENV_VAR = (
    "AGENTSCOPE_MCP_PREWARM_RETRIEVAL_ARTIFACT_DIR"
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


def _default_semantic_artifact_dir() -> Path:
    """Resolve the default retrieval artifact directory.

    Returns:
        `Path`:
            The configured artifact directory path.
    """
    configured = os.getenv(_SEMANTIC_ROUTER_ARTIFACT_ENV_VAR, "").strip()
    if configured:
        return Path(os.path.expanduser(configured)).resolve()

    return (
        Path(__file__).resolve().parents[3]
        / "laplace"
        / "router_model"
        / "artifacts_retrieval_router_deploy"
    )


def _normalize_retrieval_text(text: str) -> str:
    """Normalize text before sparse feature extraction.

    Args:
        text (`str`):
            Raw prompt text.

    Returns:
        `str`:
            Whitespace-normalized text.
    """
    return re.sub(r"\s+", " ", text).strip()


def _word_tokens(text: str) -> list[str]:
    """Tokenize text into lowercase word tokens.

    Args:
        text (`str`):
            Raw input text.

    Returns:
        `list[str]`:
            Extracted word tokens.
    """
    return re.findall(r"[a-z0-9]+", text.lower())


def _char_ngrams(text: str, min_n: int, max_n: int) -> list[str]:
    """Extract character n-grams from normalized text.

    Args:
        text (`str`):
            Raw input text.
        min_n (`int`):
            Minimum n-gram size.
        max_n (`int`):
            Maximum n-gram size.

    Returns:
        `list[str]`:
            Extracted n-grams.
    """
    normalized = f" {_normalize_retrieval_text(text).lower()} "
    grams: list[str] = []
    for n_size in range(min_n, max_n + 1):
        for idx in range(0, max(len(normalized) - n_size + 1, 0)):
            gram = normalized[idx : idx + n_size]
            if gram.strip():
                grams.append(gram)
    return grams


def _extract_retrieval_features(
    text: str,
    char_ngram_range: tuple[int, int],
    use_word_bigrams: bool,
) -> Counter[str]:
    """Extract sparse lexical retrieval features.

    Args:
        text (`str`):
            Raw query text.
        char_ngram_range (`tuple[int, int]`):
            Character n-gram range.
        use_word_bigrams (`bool`):
            Whether to include word bigrams.

    Returns:
        `Counter[str]`:
            Sparse feature counter.
    """
    tokens = _word_tokens(text)
    counts: Counter[str] = Counter()

    for token in tokens:
        counts[f"w:{token}"] += 1

    if use_word_bigrams:
        for left, right in zip(tokens, tokens[1:]):
            counts[f"wb:{left}_{right}"] += 1

    char_min, char_max = char_ngram_range
    for gram in _char_ngrams(text, char_min, char_max):
        counts[f"c:{gram}"] += 1

    return counts


class _RetrievalPrewarmModel:
    """Minimal retrieval router loader used by semantic pre-warming.

    Args:
        vocabulary (`dict[str, int]`):
            Sparse feature vocabulary.
        idf (`object`):
            IDF vector.
        train_matrix (`object`):
            Normalized train matrix.
        train_labels (`list[str]`):
            Label for each train sample.
        char_ngram_range (`tuple[int, int]`):
            Character n-gram range.
        use_word_bigrams (`bool`):
            Whether word bigrams are enabled.
        top_neighbors (`int`):
            Maximum number of neighbors to aggregate.
    """

    def __init__(
        self,
        vocabulary: dict[str, int],
        idf: object,
        train_matrix: object,
        train_labels: list[str],
        char_ngram_range: tuple[int, int],
        use_word_bigrams: bool,
        top_neighbors: int,
    ) -> None:
        self.vocabulary = vocabulary
        self.idf = idf
        self.train_matrix = train_matrix
        self.train_labels = train_labels
        self.char_ngram_range = char_ngram_range
        self.use_word_bigrams = use_word_bigrams
        self.top_neighbors = top_neighbors

    @classmethod
    def load(cls, artifact_prefix: Path) -> "_RetrievalPrewarmModel":
        """Load a retrieval model from artifact files.

        Args:
            artifact_prefix (`Path`):
                Retrieval model prefix without suffix.

        Returns:
            `_RetrievalPrewarmModel`:
                Loaded retrieval model.
        """
        import numpy as np

        payload = json.loads(
            artifact_prefix.with_suffix(".json").read_text(encoding="utf-8")
        )
        matrix_payload = np.load(
            artifact_prefix.with_suffix(".npz"),
            allow_pickle=True,
        )
        return cls(
            vocabulary={str(k): int(v) for k, v in payload["vocabulary"].items()},
            idf=matrix_payload["idf"].astype(np.float32, copy=False),
            train_matrix=matrix_payload["train_matrix"].astype(np.float32, copy=False),
            train_labels=[str(item) for item in matrix_payload["train_labels"].tolist()],
            char_ngram_range=(
                int(payload["char_ngram_range"][0]),
                int(payload["char_ngram_range"][1]),
            ),
            use_word_bigrams=bool(payload["use_word_bigrams"]),
            top_neighbors=int(payload["top_neighbors"]),
        )

    def _vectorize_counts(self, counts: Counter[str]) -> object:
        """Vectorize one sparse feature counter into normalized TF-IDF.

        Args:
            counts (`Counter[str]`):
                Sparse query feature counts.

        Returns:
            `object`:
                Dense normalized query vector.
        """
        import numpy as np

        vector = np.zeros(len(self.vocabulary), dtype=np.float32)
        if not counts:
            return vector

        total = float(sum(counts.values()))
        for feature, count in counts.items():
            idx = self.vocabulary.get(feature)
            if idx is None:
                continue
            vector[idx] = (float(count) / total) * self.idf[idx]

        norm = float(np.linalg.norm(vector))
        if norm > 0.0:
            vector /= norm
        return vector

    def score(self, text: str) -> list[tuple[str, float]]:
        """Score all servers by nearest-neighbor retrieval.

        Args:
            text (`str`):
                Query text.

        Returns:
            `list[tuple[str, float]]`:
                Sorted `(server_name, score)` pairs.
        """
        import numpy as np

        counts = _extract_retrieval_features(
            text=text,
            char_ngram_range=self.char_ngram_range,
            use_word_bigrams=self.use_word_bigrams,
        )
        query = self._vectorize_counts(counts)
        if not float(np.linalg.norm(query)):
            return []

        similarities = self.train_matrix @ query
        if similarities.size == 0:
            return []

        neighbor_count = min(self.top_neighbors, similarities.shape[0])
        top_indices = np.argpartition(similarities, -neighbor_count)[-neighbor_count:]
        top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]

        server_scores: dict[str, float] = defaultdict(float)
        for idx in top_indices:
            similarity = float(similarities[idx])
            if similarity <= 0.0:
                continue
            server_name = self.train_labels[int(idx)]
            if similarity > server_scores[server_name]:
                server_scores[server_name] = similarity

        return sorted(
            server_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )


class MCPPrewarmRouter:
    """Base class and factory for prompt-level pre-warming routers.

    When instantiated directly, this class dispatches to the concrete router
    implementation based on ``method``:

    - ``method='keyword'`` -> :class:`MCPPrewarmKeywordRouter`
    - ``method='semantic'`` -> :class:`MCPPrewarmSemanticRouter`
    - ``method='hybrid'`` -> :class:`MCPPrewarmHybridRouter`
    """

    def __new__(
        cls,
        mapping: dict[str, list[str]] | str | None = None,
        method: Literal["keyword", "semantic", "hybrid"] = "keyword",
    ) -> "MCPPrewarmRouter":
        if cls is MCPPrewarmRouter:
            if method == "keyword":
                return super().__new__(MCPPrewarmKeywordRouter)
            if method == "semantic":
                return super().__new__(MCPPrewarmSemanticRouter)
            if method == "hybrid":
                return super().__new__(MCPPrewarmHybridRouter)
            raise ValueError(
                f"Unknown prewarm routing method '{method}'. "
                "Supported: 'keyword', 'semantic', 'hybrid'.",
            )
        return super().__new__(cls)

    @classmethod
    def from_json(
        cls,
        path: str,
        method: Literal["keyword", "semantic", "hybrid"] = "keyword",
    ) -> "MCPPrewarmRouter":
        """Create a prewarm router from a JSON mapping file."""
        return cls(mapping=path, method=method)

    def __call__(
        self,
        msg: "Msg | list[Msg] | str | None",
    ) -> list[str]:
        """Return candidates to prewarm for the given message(s).

        .. note:: The same router can be used for both prompt-level inputs
            and stream-level speculative fragments such as partial tool names.
        """
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

    _CONFIG_KEYS = {
        "keyword_mapping",
        "min_matches_per_client",
        "max_candidates",
    }

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
        self._min_matches_per_client = 1
        self._max_candidates: int | None = None

        mapping_payload: dict[str, list[str]] | str | None = mapping
        if isinstance(mapping, dict) and any(
            key in mapping for key in self._CONFIG_KEYS
        ):
            mapping_payload = mapping.get("keyword_mapping")
            self._min_matches_per_client = max(
                1,
                int(mapping.get("min_matches_per_client", 1)),
            )
            max_candidates = mapping.get("max_candidates")
            self._max_candidates = (
                max(1, int(max_candidates))
                if max_candidates is not None
                else None
            )

        self._mapping = self._load_mapping(mapping_payload)

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
    def _extract_text(msg: "Msg | list[Msg] | str | None") -> str:
        """Extract all text content from prompt or stream fragments.

        Args:
            msg (`Msg | list[Msg] | str | None`):
                Input message(s) or raw text fragments.

        Returns:
            `str`:
                Concatenated lower-cased text.
        """
        if msg is None:
            return ""

        if isinstance(msg, str):
            return msg.lower()

        msgs = [msg] if isinstance(msg, Msg) else list(msg)
        parts: list[str] = []
        for m in msgs:
            if isinstance(m, Msg):
                text = m.get_text_content()
            else:
                text = str(m)
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
            matched_keyword_count = 0
            for kw in keywords:
                if kw in text:
                    matched_keyword_count += 1
                    logger.debug(
                        "[PrewarmRouter] keyword '%s' matched -> '%s'",
                        kw,
                        client_name,
                    )
            if matched_keyword_count >= self._min_matches_per_client:
                candidates.append(client_name)

        if self._max_candidates is not None:
            candidates = candidates[: self._max_candidates]

        return candidates


class MCPPrewarmSemanticRouter(MCPPrewarmRouter):
    """Semantic pre-warming router backed by the retrieval baseline.

    Args:
        mapping (`dict[str, list[str]] | str | None`, optional):
            Semantic router configuration. Accepted forms:

            * `None`: use the default retrieval artifact directory.
            * `str`: use the given retrieval artifact directory.
            * `dict`: optional config with keys like `artifact_dir`,
              `threshold`, `top_k`, and `ensure_non_empty`.
        method (`Literal['keyword', 'semantic']`, optional):
            Routing method. Only `semantic` is valid for this class.
    """

    def __init__(
        self,
        mapping: dict[str, list[str]] | str | None = None,
        method: Literal["keyword", "semantic"] = "semantic",
    ) -> None:
        """Initialize semantic router state.

        Args:
            mapping (`dict[str, list[str]] | str | None`, optional):
                Semantic retrieval config.
            method (`Literal['keyword', 'semantic']`, optional):
                Routing method selector.
        """
        if method != "semantic":
            raise ValueError(
                f"Unknown prewarm routing method '{method}'. "
                "Supported: 'semantic'.",
            )
        self.method = method
        self._artifact_dir = _default_semantic_artifact_dir()
        self._threshold = 0.0
        self._top_k = 1
        self._ensure_non_empty = False
        self._model: _RetrievalPrewarmModel | None = None
        self._load_failed = False

        if isinstance(mapping, str):
            self._artifact_dir = Path(os.path.expanduser(mapping)).resolve()
        elif isinstance(mapping, dict):
            artifact_dir = mapping.get("artifact_dir")
            if artifact_dir:
                self._artifact_dir = Path(str(artifact_dir)).expanduser().resolve()
            self._threshold = float(mapping.get("threshold", self._threshold))
            self._top_k = int(mapping.get("top_k", self._top_k))
            self._ensure_non_empty = bool(
                mapping.get("ensure_non_empty", self._ensure_non_empty),
            )

    def _ensure_model_loaded(self) -> bool:
        """Load retrieval artifacts on first use.

        Returns:
            `bool`:
                Whether the model is available.
        """
        if self._model is not None:
            return True
        if self._load_failed:
            return False

        try:
            self._model = _RetrievalPrewarmModel.load(
                self._artifact_dir / "semantic_router_retrieval",
            )
            grid_path = self._artifact_dir / "grid_search_results.json"
            if grid_path.exists():
                payload = json.loads(grid_path.read_text(encoding="utf-8"))
                best = payload.get("best") or payload.get("best_by_objective")
                if best is not None:
                    self._threshold = float(best.get("threshold", self._threshold))
                    self._top_k = max(1, int(best.get("top_k", self._top_k)))
            logger.info(
                "[PrewarmSemanticRouter] loaded retrieval artifact from '%s'.",
                self._artifact_dir,
            )
            return True
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._load_failed = True
            logger.warning(
                "[PrewarmSemanticRouter] failed to load retrieval artifact from '%s': %s",
                self._artifact_dir,
                exc,
            )
            return False

    def __call__(
        self,
        msg: "Msg | list[Msg] | str | None",
    ) -> list[str]:
        """Return semantic pre-warm candidates from the retrieval model.

        Args:
            msg (`Msg | list[Msg] | str | None`):
                Incoming prompt text or message list.

        Returns:
            `list[str]`:
                Server-name candidates chosen by semantic retrieval.
        """
        text = MCPPrewarmKeywordRouter._extract_text(msg)
        if not text:
            return []
        if not self._ensure_model_loaded() or self._model is None:
            return []

        scored = self._model.score(text)
        selected = [
            server_name
            for server_name, score in scored
            if score >= self._threshold
        ][: self._top_k]
        if not selected and self._ensure_non_empty and scored:
            selected = [scored[0][0]]

        for server_name in selected:
            logger.debug(
                "[PrewarmSemanticRouter] semantic match -> '%s'",
                server_name,
            )
        return selected


class MCPPrewarmHybridRouter(MCPPrewarmRouter):
    """Hybrid pre-warming router with L1 keyword and L2 semantic fallback.

    The router first applies the low-cost keyword matcher. When L1 produces no
    candidates, it falls back to the semantic retrieval router.

    Args:
        mapping (`dict[str, list[str]] | str | None`, optional):
            Hybrid configuration. Accepted forms:

            * `None`: use default keyword mapping and default semantic artifact.
            * `str`: use the path as keyword-mapping JSON and keep the default
              semantic artifact.
            * `dict`: either a plain keyword mapping, or a config object with
              optional keys `keyword_mapping`, `semantic_mapping`,
              `artifact_dir`, `threshold`, `top_k`, and `ensure_non_empty`.
        method (`Literal['keyword', 'semantic', 'hybrid']`, optional):
            Routing method. Only `hybrid` is valid for this class.
    """

    _SEMANTIC_CONFIG_KEYS = {
        "keyword_mapping",
        "keyword_min_matches_per_client",
        "keyword_max_candidates",
        "semantic_mapping",
        "artifact_dir",
        "threshold",
        "top_k",
        "ensure_non_empty",
    }

    def __init__(
        self,
        mapping: dict[str, list[str]] | str | None = None,
        method: Literal["keyword", "semantic", "hybrid"] = "hybrid",
    ) -> None:
        """Initialize hybrid router state."""
        if method != "hybrid":
            raise ValueError(
                f"Unknown prewarm routing method '{method}'. "
                "Supported: 'hybrid'.",
            )

        self.method = method
        self.last_route_method = "keyword"

        keyword_mapping: dict[str, list[str]] | str | None = mapping
        semantic_mapping: dict[str, object] | str | None = None

        if isinstance(mapping, dict):
            if any(key in mapping for key in self._SEMANTIC_CONFIG_KEYS):
                keyword_mapping = mapping.get("keyword_mapping")
                semantic_mapping = mapping.get("semantic_mapping")

                keyword_payload: dict[str, object] = {}
                if keyword_mapping is not None:
                    keyword_payload["keyword_mapping"] = keyword_mapping
                if "keyword_min_matches_per_client" in mapping:
                    keyword_payload["min_matches_per_client"] = mapping[
                        "keyword_min_matches_per_client"
                    ]
                if "keyword_max_candidates" in mapping:
                    keyword_payload["max_candidates"] = mapping[
                        "keyword_max_candidates"
                    ]
                if keyword_payload:
                    keyword_mapping = keyword_payload

                if semantic_mapping is None:
                    semantic_payload = {
                        key: mapping[key]
                        for key in (
                            "artifact_dir",
                            "threshold",
                            "top_k",
                            "ensure_non_empty",
                        )
                        if key in mapping
                    }
                    semantic_mapping = semantic_payload or None

                if keyword_mapping is None:
                    keyword_payload = {
                        key: value
                        for key, value in mapping.items()
                        if key not in self._SEMANTIC_CONFIG_KEYS
                    }
                    keyword_mapping = keyword_payload or None

        self._keyword_router = MCPPrewarmKeywordRouter(mapping=keyword_mapping)
        self._semantic_router = MCPPrewarmSemanticRouter(mapping=semantic_mapping)

    def __call__(
        self,
        msg: "Msg | list[Msg] | str | None",
    ) -> list[str]:
        """Return candidates from L1 keyword, then L2 semantic fallback."""
        keyword_candidates = self._keyword_router(msg)
        if keyword_candidates:
            self.last_route_method = "keyword"
            return keyword_candidates

        semantic_candidates = self._semantic_router(msg)
        self.last_route_method = "semantic"
        return semantic_candidates

def build_mcp_speculative_executor(
    registrations: "list[_DockerMCPRegistrationConfig]",
) -> Callable[[str], Awaitable[object | None]]:
    """Build a speculative pre-warming executor from registration configs.

    The returned callable accepts a candidate key (``container_name``,
    ``client_name``, or ``server_name`` when available) and calls
    :func:`~agentscope.mcp._mcp_server_helper._speculative_ensure_local_docker_mcp_server`
    asynchronously without polluting formal usage metrics.

    Args:
        registrations (`list[_DockerMCPRegistrationConfig]`):
            List of Docker MCP registration configurations.  Both
            ``server_config.container_name`` and ``server_config.client_name``
            are indexed so either can be used as a routing key.  When
            available, the human-readable ``server_name`` is also indexed.

    Returns:
        `Callable[[str], Awaitable[object | None]]`:
            An async executor that accepts one candidate key per call and
            returns the ensured MCP client when a registration is found.

    Example:
        .. code-block:: python

            from agentscope.mcp import (
                MCPLaplaceController,
                MCPPrewarmKeywordRouter,
                build_mcp_speculative_executor,
            )

            executor = build_mcp_speculative_executor([
                playwright_registration,
                github_registration,
            ])
            router = MCPPrewarmKeywordRouter.from_json("prewarm_mapping.json")
            controller = MCPLaplaceController(
                prompt_prewarm_router=router,
                prompt_prewarm_executor=executor,
            )

            agent = ReActAgent(
                ...
                mcp_laplace_controller=controller,
            )
    """
    # Build a lookup keyed by container_name, client_name, and optional
    # human-readable server_name so semantic routing can return dataset labels.
    lookup: dict[str, "_DockerMCPRegistrationConfig"] = {}
    for reg in registrations:
        lookup[reg.server_config.container_name] = reg
        lookup[reg.server_config.client_name] = reg
        if getattr(reg, "server_name", None):
            lookup[str(reg.server_name)] = reg

    async def _executor(candidate: str) -> object | None:
        reg = lookup.get(candidate)
        if reg is None:
            logger.debug(
                "[PrewarmExecutor] no registration found for '%s', skipping.",
                candidate,
            )
            return None

        # Lazy import to satisfy the lazy-loading convention.
        from ._mcp_server_helper import (
            _speculative_ensure_local_docker_mcp_server,
        )

        logger.debug(
            "[PrewarmExecutor] speculatively warming '%s' ...",
            candidate,
        )
        return await _speculative_ensure_local_docker_mcp_server(
            config=reg.server_config,
            docker_run_command=reg.docker_run_command,
            headers=reg.headers,
        )

    return _executor
