"""Tests for the incident response advisory agent."""

from __future__ import annotations

import unittest

from safeai.intelligence.backend import AIMessage, AIResponse
from safeai.intelligence.incident import IncidentAdvisor
from safeai.intelligence.sanitizer import BANNED_METADATA_KEYS


class FakeAIBackend:
    def __init__(self, response_content: str = "", model: str = "fake") -> None:
        self.calls: list[list[AIMessage]] = []
        self._response_content = response_content
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def complete(self, messages: list[AIMessage], **kwargs) -> AIResponse:
        self.calls.append(messages)
        return AIResponse(content=self._response_content, model=self._model)


class IncidentAdvisorTests(unittest.TestCase):
    def _make_event(self) -> dict:
        return {
            "event_id": "evt_123",
            "timestamp": "2025-06-15T10:30:00Z",
            "boundary": "input",
            "action": "block",
            "policy_name": "block-secrets",
            "reason": "API key detected in input",
            "data_tags": ["secret.credential"],
            "agent_id": "coding-agent",
            "tool_name": "shell",
            "session_id": "sess-abc",
            "metadata": {
                "phase": "input_scan",
                "action_type": "scan",
                "secret_key": "ACTUAL_SECRET_VALUE",
                "matched_value": "sk-proj-1234abcd",
                "raw_content": "Full message with secrets embedded",
                "message_length": 250,
            },
        }

    def _make_context_events(self) -> list[dict]:
        return [
            {
                "event_id": "evt_120",
                "timestamp": "2025-06-15T10:29:00Z",
                "boundary": "action",
                "action": "allow",
                "policy_name": "default-allow",
                "reason": "No restrictive policy",
                "data_tags": [],
                "agent_id": "coding-agent",
                "tool_name": "read_file",
            },
            {
                "event_id": "evt_125",
                "timestamp": "2025-06-15T10:31:00Z",
                "boundary": "output",
                "action": "redact",
                "policy_name": "redact-pii",
                "reason": "PII in output",
                "data_tags": ["personal.pii"],
                "agent_id": "coding-agent",
            },
        ]

    def test_advise_success(self) -> None:
        response = "**Classification**: HIGH severity, secret exposure\n**Explanation**: ..."
        backend = FakeAIBackend(response_content=response)
        advisor = IncidentAdvisor(backend=backend)
        result = advisor.advise(event=self._make_event(), context_events=self._make_context_events())

        self.assertEqual(result.status, "success")
        self.assertEqual(result.advisor_name, "incident")
        self.assertIn("evt_123", result.summary)
        self.assertEqual(result.metadata["event_id"], "evt_123")

    def test_event_sanitization(self) -> None:
        """Verify banned metadata values never reach the AI prompt."""
        event = self._make_event()
        backend = FakeAIBackend(response_content="analysis")
        advisor = IncidentAdvisor(backend=backend)
        advisor.advise(event=event, context_events=[])

        user_msg = backend.calls[0][1].content
        # Banned values must not appear in the prompt
        self.assertNotIn("ACTUAL_SECRET_VALUE", user_msg)
        self.assertNotIn("sk-proj-1234abcd", user_msg)
        self.assertNotIn("Full message with secrets embedded", user_msg)
        # Safe metadata should appear
        self.assertIn("input_scan", user_msg)

    def test_classification_context_window(self) -> None:
        """Context events should be limited to 5 and sanitized."""
        many_events = [
            {
                "event_id": f"evt_{i}",
                "timestamp": f"2025-06-15T10:{i:02d}:00Z",
                "boundary": "input",
                "action": "allow",
                "data_tags": [],
                "agent_id": "agent",
                "metadata": {"raw_content": f"secret_{i}"},
            }
            for i in range(10)
        ]
        backend = FakeAIBackend(response_content="analysis")
        advisor = IncidentAdvisor(backend=backend)
        advisor.advise(event=self._make_event(), context_events=many_events)

        user_msg = backend.calls[0][1].content
        # Should include at most 5 context events
        context_lines = [l for l in user_msg.splitlines() if l.startswith("- [2025")]
        self.assertLessEqual(len(context_lines), 5)
        # No raw_content should leak
        for i in range(10):
            self.assertNotIn(f"secret_{i}", user_msg)

    def test_no_event_returns_error(self) -> None:
        backend = FakeAIBackend()
        advisor = IncidentAdvisor(backend=backend)
        result = advisor.advise()
        self.assertEqual(result.status, "error")
        self.assertEqual(len(backend.calls), 0)

    def test_backend_error(self) -> None:
        class FailingBackend:
            @property
            def model_name(self) -> str:
                return "fail"
            def complete(self, messages, **kwargs):
                raise RuntimeError("connection refused")

        advisor = IncidentAdvisor(backend=FailingBackend())
        result = advisor.advise(event=self._make_event())
        self.assertEqual(result.status, "error")

    def test_all_banned_keys_stripped_from_prompt(self) -> None:
        """Every banned metadata key's value must be absent from the prompt."""
        event = self._make_event()
        # Add all possible banned keys
        for key in BANNED_METADATA_KEYS:
            event["metadata"][key] = f"BANNED_VALUE_{key.upper()}"

        backend = FakeAIBackend(response_content="done")
        advisor = IncidentAdvisor(backend=backend)
        advisor.advise(event=event)

        user_msg = backend.calls[0][1].content
        for key in BANNED_METADATA_KEYS:
            self.assertNotIn(
                f"BANNED_VALUE_{key.upper()}",
                user_msg,
                f"Banned value for '{key}' leaked into prompt",
            )


if __name__ == "__main__":
    unittest.main()
