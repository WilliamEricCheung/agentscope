# -*- coding: utf-8 -*-
"""Unified runtime configuration for the on-demand meta planner example."""


def normalize_stream_text_speculation_interval_tokens(
    interval_tokens: int | None,
) -> int | None:
    """Normalize stream-level periodic speculation interval.

    Args:
        interval_tokens (`int | None`):
            Desired interval in approximate tokens.

    Returns:
        `int | None`:
            Positive interval value or `None` when disabled.
    """
    if interval_tokens is None:
        return None

    return interval_tokens if interval_tokens > 0 else None


# Unified switch for both parent planner and sub-worker prewarm behavior.
ON_DEMAND_PREWARM_ENABLED = False

# Unified C2 predictive prewarm switch.
ON_DEMAND_PREDICTIVE_PREWARM_ENABLED = True

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
