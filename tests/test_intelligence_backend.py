"""Tests for the AI backend registry and protocol."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch, MagicMock

from safeai.intelligence.backend import (
    AIBackend,
    AIBackendNotConfiguredError,
    AIBackendRegistry,
    AIMessage,
    AIResponse,
    OllamaBackend,
    OpenAICompatibleBackend,
)


class FakeAIBackend:
    """Test double for AIBackend protocol."""

    def __init__(self, response_content: str = "", model: str = "fake") -> None:
        self.calls: list[list[AIMessage]] = []
        self._response_content = response_content
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def complete(self, messages: list[AIMessage], **kwargs) -> AIResponse:
        self.calls.append(messages)
        return AIResponse(
            content=self._response_content,
            model=self._model,
            usage={"prompt_tokens": 10, "completion_tokens": 5},
            raw={},
        )


class AIMessageTests(unittest.TestCase):
    def test_frozen_dataclass(self) -> None:
        msg = AIMessage(role="user", content="hello")
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "hello")
        with self.assertRaises(AttributeError):
            msg.role = "system"  # type: ignore[misc]


class AIResponseTests(unittest.TestCase):
    def test_frozen_dataclass(self) -> None:
        resp = AIResponse(content="ok", model="test")
        self.assertEqual(resp.content, "ok")
        self.assertEqual(resp.model, "test")
        self.assertEqual(resp.usage, {})

    def test_with_usage(self) -> None:
        resp = AIResponse(
            content="ok",
            model="test",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )
        self.assertEqual(resp.usage["prompt_tokens"], 10)


class ProtocolTests(unittest.TestCase):
    def test_fake_backend_satisfies_protocol(self) -> None:
        backend = FakeAIBackend()
        self.assertIsInstance(backend, AIBackend)

    def test_ollama_satisfies_protocol(self) -> None:
        backend = OllamaBackend()
        self.assertIsInstance(backend, AIBackend)

    def test_openai_satisfies_protocol(self) -> None:
        backend = OpenAICompatibleBackend(model="gpt-4")
        self.assertIsInstance(backend, AIBackend)


class AIBackendRegistryTests(unittest.TestCase):
    def test_register_and_get(self) -> None:
        registry = AIBackendRegistry()
        backend = FakeAIBackend()
        registry.register("test", backend)
        self.assertIs(registry.get("test"), backend)

    def test_first_registered_is_default(self) -> None:
        registry = AIBackendRegistry()
        b1 = FakeAIBackend(model="first")
        b2 = FakeAIBackend(model="second")
        registry.register("first", b1)
        registry.register("second", b2)
        self.assertIs(registry.get(), b1)

    def test_explicit_default(self) -> None:
        registry = AIBackendRegistry()
        b1 = FakeAIBackend(model="first")
        b2 = FakeAIBackend(model="second")
        registry.register("first", b1)
        registry.register("second", b2, default=True)
        self.assertIs(registry.get(), b2)

    def test_get_raises_when_empty(self) -> None:
        registry = AIBackendRegistry()
        with self.assertRaises(AIBackendNotConfiguredError):
            registry.get()

    def test_get_raises_for_unknown_name(self) -> None:
        registry = AIBackendRegistry()
        registry.register("test", FakeAIBackend())
        with self.assertRaises(AIBackendNotConfiguredError):
            registry.get("nonexistent")

    def test_list_backends(self) -> None:
        registry = AIBackendRegistry()
        registry.register("a", FakeAIBackend())
        registry.register("b", FakeAIBackend())
        self.assertEqual(sorted(registry.list_backends()), ["a", "b"])

    def test_default_name(self) -> None:
        registry = AIBackendRegistry()
        self.assertIsNone(registry.default_name)
        registry.register("test", FakeAIBackend())
        self.assertEqual(registry.default_name, "test")


class OllamaBackendTests(unittest.TestCase):
    def test_model_name(self) -> None:
        backend = OllamaBackend(model="llama3.2")
        self.assertEqual(backend.model_name, "llama3.2")

    @patch("safeai.intelligence.backend.httpx.Client")
    def test_complete_calls_api(self, mock_client_cls: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "model": "llama3.2",
            "message": {"role": "assistant", "content": "Hello!"},
            "prompt_eval_count": 10,
            "eval_count": 5,
        }
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        backend = OllamaBackend(model="llama3.2", base_url="http://localhost:11434")
        messages = [AIMessage(role="user", content="test")]
        result = backend.complete(messages)

        self.assertEqual(result.content, "Hello!")
        self.assertEqual(result.model, "llama3.2")
        self.assertEqual(result.usage["prompt_tokens"], 10)
        self.assertEqual(result.usage["completion_tokens"], 5)
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        self.assertIn("/api/chat", call_args[0][0])


class OpenAICompatibleBackendTests(unittest.TestCase):
    def test_model_name(self) -> None:
        backend = OpenAICompatibleBackend(model="gpt-4")
        self.assertEqual(backend.model_name, "gpt-4")

    @patch("safeai.intelligence.backend.httpx.Client")
    def test_complete_calls_api(self, mock_client_cls: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "model": "gpt-4",
            "choices": [{"message": {"content": "Response here"}}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 10},
        }
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        backend = OpenAICompatibleBackend(
            model="gpt-4",
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
        )
        messages = [AIMessage(role="user", content="test")]
        result = backend.complete(messages)

        self.assertEqual(result.content, "Response here")
        self.assertEqual(result.model, "gpt-4")
        self.assertEqual(result.usage["prompt_tokens"], 20)
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        self.assertIn("/chat/completions", call_args[0][0])
        headers = call_args[1]["headers"]
        self.assertEqual(headers["Authorization"], "Bearer sk-test")

    @patch("safeai.intelligence.backend.httpx.Client")
    def test_empty_choices(self, mock_client_cls: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"model": "gpt-4", "choices": [], "usage": {}}
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        backend = OpenAICompatibleBackend(model="gpt-4")
        result = backend.complete([AIMessage(role="user", content="test")])
        self.assertEqual(result.content, "")


if __name__ == "__main__":
    unittest.main()
