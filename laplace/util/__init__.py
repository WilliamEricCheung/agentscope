"""Reusable Laplace utility scripts and helper APIs."""

from __future__ import annotations

from importlib import import_module
from typing import Any


_SYMBOL_TO_MODULE = {
    "DashScopeCompletionProvider": "laplace.util.dashscope_provider",
    "HttpStatelessClient": "laplace.util.mcp_tool_discovery",
    "LaplaceMCPManifestSource": "laplace.util.server_config",
    "MCPServerValidator": "laplace.util.validate_mcp_servers",
    "MCPToolDiscoverer": "laplace.util.mcp_tool_discovery",
    "MCPBenchCommandSource": "laplace.util.server_config",
    "ServerConfig": "laplace.util.server_config",
    "StdIOStatefulClient": "laplace.util.mcp_tool_discovery",
}

_ALIASES = {}

__all__ = sorted(_SYMBOL_TO_MODULE)


def __getattr__(name: str) -> Any:
    """Resolve exported utility symbols lazily.

    Args:
        name (`str`):
            Requested attribute name.

    Returns:
        `Any`:
            Exported object from the backing utility module.

    Raises:
        `AttributeError`:
            Raised when the name is not exported.
    """

    module_name = _SYMBOL_TO_MODULE.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name)
    exported_name = _ALIASES.get(name, name)
    return getattr(module, exported_name)


def __dir__() -> list[str]:
    """Return package attribute names for interactive discovery.

    Returns:
        `list[str]`:
            Sorted attribute list.
    """

    return sorted(set(globals()) | set(__all__))
