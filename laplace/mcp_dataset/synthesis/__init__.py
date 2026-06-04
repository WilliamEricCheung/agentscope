"""Synthesis toolkit for prompt-to-task and context-to-SDG data generation."""

from __future__ import annotations

from importlib import import_module
from typing import Any


_SYMBOL_TO_MODULE = {
    "BenchmarkTaskGenerator": "laplace.mcp_dataset.synthesis.prompt2task",
    "SDGTraceSynthesizer": "laplace.mcp_dataset.synthesis.context2sdg",
    "TaskQualityEvaluator": "laplace.mcp_dataset.synthesis.prompt2task",
    "TaskSynthesizer": "laplace.mcp_dataset.synthesis.prompt2task",
    "build_batch_trace_prompt": "laplace.mcp_dataset.synthesis.context2sdg",
    "build_server_transition_counts": "laplace.mcp_dataset.synthesis.context2sdg",
    "build_server_transition_matrix": "laplace.mcp_dataset.synthesis.context2sdg",
    "build_state_transition_counts": "laplace.mcp_dataset.synthesis.context2sdg",
    "build_state_transition_matrix": "laplace.mcp_dataset.synthesis.context2sdg",
    "load_laplace_server_catalog": "laplace.mcp_dataset.synthesis.context2sdg",
}

__all__ = sorted(_SYMBOL_TO_MODULE)


def __getattr__(name: str) -> Any:
    """Resolve synthesis package exports lazily.

    Args:
        name (`str`):
            Requested attribute name.

    Returns:
        `Any`:
            Exported symbol from the backing subpackage.

    Raises:
        `AttributeError`:
            Raised when the name is not exported.
    """

    module_name = _SYMBOL_TO_MODULE.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name)
    return getattr(module, name)


def __dir__() -> list[str]:
    """Return package attribute names for interactive discovery.

    Returns:
        `list[str]`:
            Sorted attribute list.
    """

    return sorted(set(globals()) | set(__all__))