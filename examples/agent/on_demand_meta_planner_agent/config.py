# -*- coding: utf-8 -*-
"""Unified runtime configuration for the on-demand meta planner example."""

import os
from typing import Any


def build_experiment_chat_model(
    model_name: str,
    api_key: str | None = None,
    stream_interval_tokens: int | None = None,
) -> Any:
    """Build a chat model using native DashScope or a configured OpenAI endpoint.

    Args:
        model_name (`str`):
            Model identifier to send to the provider.
        api_key (`str`):
            Provider API key.
        stream_interval_tokens (`int | None`, optional):
            DashScope token interval for stream-level speculation.

    Returns:
        `ChatModelBase`:
            Configured model client.
    """
    compatible_base_url = os.getenv(
        "AGENTSCOPE_OPENAI_COMPAT_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    ).strip()
    resolved_api_key = (
        api_key
        or os.getenv("DASHSCOPE_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    if not resolved_api_key:
        raise RuntimeError(
            "Set DASHSCOPE_API_KEY or OPENAI_API_KEY before running the "
            "experiment.",
        )
    if compatible_base_url:
        from agentscope.model import OpenAIChatModel

        return OpenAIChatModel(
            model_name=model_name,
            api_key=resolved_api_key,
            client_kwargs={"base_url": compatible_base_url},
            generate_kwargs={
                "extra_body": {
                    "enable_thinking": False,
                },
            },
        )

    from agentscope.model import DashScopeChatModel

    return DashScopeChatModel(
        model_name=model_name,
        api_key=resolved_api_key,
        stream_text_speculation_interval_tokens=stream_interval_tokens,
    )


def get_experiment_chat_formatter() -> Any:
    """Get the formatter matching the configured experiment model API.

    Returns:
        `Any`:
            OpenAI-compatible or DashScope chat formatter.
    """
    if os.getenv(
        "AGENTSCOPE_OPENAI_COMPAT_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    ).strip():
        from agentscope.formatter import OpenAIChatFormatter

        return OpenAIChatFormatter()

    from agentscope.formatter import DashScopeChatFormatter

    return DashScopeChatFormatter()


def normalize_stream_text_speculation_interval_tokens(
    interval_tokens: int | str | None,
) -> int | None:
    """Normalize stream-level periodic speculation interval.

    Args:
        interval_tokens (`int | str | None`):
            Desired interval in approximate tokens.

    Returns:
        `int | None`:
            Positive interval value or `None` when disabled.
    """
    if interval_tokens is None:
        return None

    if isinstance(interval_tokens, str):
        try:
            interval_tokens = int(interval_tokens)
        except ValueError as exc:
            raise ValueError(
                "Stream speculation interval must be an integer.",
            ) from exc

    return interval_tokens if interval_tokens > 0 else None


# Unified switch for both parent planner and sub-worker prewarm behavior.
ON_DEMAND_PREWARM_ENABLED = False

# Unified C2 predictive prewarm switch.
ON_DEMAND_PREDICTIVE_PREWARM_ENABLED = True

# Number of top-ranked SDG transition candidates to prewarm.
ON_DEMAND_PREDICTIVE_TOP_K = 1

# Optional transition matrix override used by controlled evaluations.
ON_DEMAND_PREDICTIVE_TRANSITION_MATRIX_PATH: str | None = None

# Unified controller telemetry switch.
ON_DEMAND_PREWARM_TELEMETRY_ENABLED = True

# Maximum retained telemetry events inside one controller instance.
ON_DEMAND_PREWARM_TELEMETRY_MAX_EVENTS = 512

# Unified stream-level periodic speculation threshold.
# Use a positive integer to enable periodic text-based speculation.
# Use `None` or `0` to disable periodic text-based speculation.
ON_DEMAND_STREAM_TEXT_SPECULATION_INTERVAL_TOKENS = (
    normalize_stream_text_speculation_interval_tokens(20)
)
