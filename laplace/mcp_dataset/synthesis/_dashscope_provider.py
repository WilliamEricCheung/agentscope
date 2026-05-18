"""DashScope completion provider built on top of AgentScope models."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any


def _import_agentscope_model() -> tuple[Any, Any]:
    """Import AgentScope model classes with a local source fallback.

    Returns:
        `tuple[Any, Any]`:
            The `DashScopeChatModel` and `ChatResponse` classes.
    """
    try:
        from agentscope.model import ChatResponse, DashScopeChatModel

        return DashScopeChatModel, ChatResponse
    except ImportError:
        repo_root = Path(__file__).resolve().parents[3]
        src_path = repo_root / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

        from agentscope.model import ChatResponse, DashScopeChatModel

        return DashScopeChatModel, ChatResponse


DashScopeChatModel, ChatResponse = _import_agentscope_model()


class DashScopeCompletionProvider:
    """A lightweight completion wrapper around AgentScope's DashScope model.

    Args:
        model_name (`str`, optional):
            DashScope model name used for synthesis.
        api_key (`str | None`, optional):
            DashScope API key. If not provided, it will be read from the
            `DASHSCOPE_API_KEY` environment variable.
        temperature (`float`, optional):
            Sampling temperature for task generation.
    """

    def __init__(
        self,
        model_name: str = "qwen-plus",
        api_key: str | None = None,
        temperature: float = 0.7,
        request_timeout_seconds: float = 120.0,
    ) -> None:
        """Initialize the completion provider.

        Args:
            model_name (`str`, optional):
                DashScope model name used for synthesis.
            api_key (`str | None`, optional):
                DashScope API key. If not provided, the environment variable
                `DASHSCOPE_API_KEY` is used.
            temperature (`float`, optional):
                Sampling temperature for generation.
            request_timeout_seconds (`float`, optional):
                Maximum seconds allowed for one completion request.

        Raises:
            `ValueError`:
                Raised when the DashScope API key is unavailable.
        """
        resolved_api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        if not resolved_api_key:
            raise ValueError(
                "DashScope API key is required. Set DASHSCOPE_API_KEY or "
                "pass api_key explicitly.",
            )

        self.model_name = model_name
        self.request_timeout_seconds = request_timeout_seconds
        self.model = DashScopeChatModel(
            model_name=model_name,
            api_key=resolved_api_key,
            stream=False,
            generate_kwargs={"temperature": temperature},
        )

    async def get_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
    ) -> str:
        """Generate one non-streaming completion.

        Args:
            system_prompt (`str`):
                System instruction passed to the chat model.
            user_prompt (`str`):
                User prompt passed to the chat model.
            max_tokens (`int`):
                Maximum number of output tokens.

        Returns:
            `str`:
                The concatenated text content from the model response.

        Raises:
            `ValueError`:
                Raised when the model response does not contain text blocks.
        """
        try:
            response = await asyncio.wait_for(
                self.model(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=max_tokens,
                ),
                timeout=self.request_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise TimeoutError(
                "DashScope completion request timed out after "
                f"{self.request_timeout_seconds:.0f}s.",
            ) from exc
        text = self._extract_text(response)
        if not text:
            raise ValueError("DashScope returned an empty response.")
        return text.strip()

    def clean_and_parse_json(self, raw_json: str) -> Any:
        """Parse a JSON response with repair fallback.

        Args:
            raw_json (`str`):
                Raw model output that is expected to contain JSON.

        Returns:
            `Any`:
                Parsed Python object.

        Raises:
            `ValueError`:
                Raised when the output cannot be repaired into valid JSON.
        """
        cleaned = raw_json.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", maxsplit=1)[1]
            cleaned = cleaned.split("```", maxsplit=1)[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```", maxsplit=2)[1].strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            import json_repair

            try:
                return json_repair.loads(cleaned)
            except Exception as exc:
                raise ValueError(
                    f"Failed to parse JSON from model output: {exc}",
                ) from exc

    @staticmethod
    def _extract_text(response: ChatResponse) -> str:
        """Extract all text blocks from one AgentScope chat response.

        Args:
            response (`ChatResponse`):
                AgentScope chat response.

        Returns:
            `str`:
                Concatenated text content.
        """
        chunks: list[str] = []
        for block in response.content:
            if block.get("type") == "text" and block.get("text"):
                chunks.append(str(block["text"]))
        return "\n".join(chunks)