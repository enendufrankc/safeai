"""Middleware base protocol."""

from __future__ import annotations

from typing import Any, Protocol


class MiddlewareAdapter(Protocol):
    def wrap(self, fn):
        """Wrap a tool or agent callable."""


class BaseMiddleware:
    """Base middleware implementation used by framework adapters."""

    def __init__(self, safeai) -> None:
        self.safeai = safeai

    def wrap(self, fn):
        return self.safeai.wrap(fn)

    def middleware(self) -> dict[str, Any]:
        return {"name": self.__class__.__name__}
