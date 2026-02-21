"""Base advisor abstraction for all intelligence agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from safeai.intelligence.backend import AIBackend
from safeai.intelligence.sanitizer import MetadataSanitizer


@dataclass(frozen=True)
class AdvisorResult:
    advisor_name: str
    status: str  # "success", "error", "no_backend"
    summary: str  # Human-readable
    artifacts: dict[str, str] = field(default_factory=dict)
    raw_response: str = ""
    model_used: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAdvisor(ABC):
    """Abstract base class for all intelligence advisory agents."""

    def __init__(
        self,
        backend: AIBackend,
        sanitizer: MetadataSanitizer | None = None,
    ) -> None:
        self._backend = backend
        self._sanitizer = sanitizer or MetadataSanitizer()

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def advise(self, **kwargs: Any) -> AdvisorResult: ...

    def _error_result(self, message: str) -> AdvisorResult:
        return AdvisorResult(
            advisor_name=self.name,
            status="error",
            summary=message,
        )
