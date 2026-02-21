"""BYOM backend abstraction for AI inference."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import httpx


class AIBackendNotConfiguredError(RuntimeError):
    """Raised when no AI backend is configured."""


@dataclass(frozen=True)
class AIMessage:
    role: str  # "system", "user", "assistant"
    content: str


@dataclass(frozen=True)
class AIResponse:
    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class AIBackend(Protocol):
    def complete(self, messages: list[AIMessage], **kwargs: Any) -> AIResponse: ...

    @property
    def model_name(self) -> str: ...


class OllamaBackend:
    """Local inference via Ollama REST API."""

    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434") -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")

    @property
    def model_name(self) -> str:
        return self._model

    def complete(self, messages: list[AIMessage], **kwargs: Any) -> AIResponse:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
        }
        payload.update(kwargs)
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
        data = resp.json()
        msg = data.get("message", {})
        return AIResponse(
            content=msg.get("content", ""),
            model=data.get("model", self._model),
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
            raw=data,
        )


class OpenAICompatibleBackend:
    """OpenAI-compatible chat completions endpoint (OpenAI, Anthropic, Azure, vLLM, etc.)."""

    def __init__(
        self,
        model: str,
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    @property
    def model_name(self) -> str:
        return self._model

    def complete(self, messages: list[AIMessage], **kwargs: Any) -> AIResponse:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        payload.update(kwargs)
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            if resp.status_code != 200:
                try:
                    detail = resp.json()
                    err_msg = detail.get("error", {}).get("message", "") or resp.text
                except Exception:
                    err_msg = resp.text
                raise RuntimeError(
                    f"HTTP {resp.status_code} from {self._base_url}: {err_msg}"
                )
        data = resp.json()
        choices = data.get("choices", [])
        content = choices[0]["message"]["content"] if choices else ""
        usage_data = data.get("usage", {})
        return AIResponse(
            content=content,
            model=data.get("model", self._model),
            usage={
                "prompt_tokens": usage_data.get("prompt_tokens", 0),
                "completion_tokens": usage_data.get("completion_tokens", 0),
            },
            raw=data,
        )


class AIBackendRegistry:
    """Named registry of AI backends with a default."""

    def __init__(self) -> None:
        self._backends: dict[str, AIBackend] = {}
        self._default: str | None = None

    def register(self, name: str, backend: AIBackend, *, default: bool = False) -> None:
        self._backends[name] = backend
        if default or len(self._backends) == 1:
            self._default = name

    def get(self, name: str | None = None) -> AIBackend:
        key = name or self._default
        if key is None or key not in self._backends:
            raise AIBackendNotConfiguredError(
                "No AI backend configured. Register one with "
                "safeai.register_ai_backend() or set intelligence.backend in safeai.yaml."
            )
        return self._backends[key]

    def list_backends(self) -> list[str]:
        return list(self._backends.keys())

    @property
    def default_name(self) -> str | None:
        return self._default
