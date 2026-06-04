"""Compatibility wrapper for the shared DashScope provider implementation."""

from laplace.util.dashscope_provider import (
    ChatResponse,
    DashScopeChatModel,
    DashScopeCompletionProvider,
)

__all__ = [
    "ChatResponse",
    "DashScopeChatModel",
    "DashScopeCompletionProvider",
]