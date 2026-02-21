"""Tests for the policy recommender advisory agent."""

from __future__ import annotations

import unittest

from safeai.intelligence.backend import AIMessage, AIResponse
from safeai.intelligence.recommender import RecommenderAdvisor


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


class RecommenderAdvisorTests(unittest.TestCase):
    def _make_events(self) -> list[dict]:
        return [
            {"action": "block", "boundary": "input", "policy_name": "p1", "agent_id": "a1", "tool_name": "t1", "data_tags": ["secret"]},
            {"action": "allow", "boundary": "output", "policy_name": "p2", "agent_id": "a1", "tool_name": "t2", "data_tags": ["personal"]},
            {"action": "block", "boundary": "input", "policy_name": "p1", "agent_id": "a2", "tool_name": "t1", "data_tags": ["secret"]},
            {"action": "allow", "boundary": "action", "policy_name": "p3", "agent_id": "a2", "data_tags": []},
        ]

    def test_advise_success(self) -> None:
        response = (
            "## Gap Analysis\nNo coverage for output boundary secrets.\n\n"
            "--- FILE: policies/recommended.yaml ---\n"
            "version: v1alpha1\npolicies:\n  - name: block-output-secrets\n"
        )
        backend = FakeAIBackend(response_content=response)
        advisor = RecommenderAdvisor(backend=backend)
        result = advisor.advise(events=self._make_events(), since="7d")

        self.assertEqual(result.status, "success")
        self.assertEqual(result.advisor_name, "recommender")
        self.assertIn("policies/recommended.yaml", result.artifacts)
        self.assertEqual(result.metadata["total_events"], 4)

    def test_audit_aggregate_consumption(self) -> None:
        """Prompt should contain aggregate counts, not individual events."""
        backend = FakeAIBackend(response_content="No recommendations.")
        advisor = RecommenderAdvisor(backend=backend)
        advisor.advise(events=self._make_events())

        user_msg = backend.calls[0][1].content
        # Should contain aggregate counts
        self.assertIn("block: 2", user_msg)
        self.assertIn("allow: 2", user_msg)
        self.assertIn("input: 2", user_msg)
        # Should NOT contain individual event IDs
        self.assertNotIn("event_id", user_msg)

    def test_empty_events(self) -> None:
        backend = FakeAIBackend(response_content="No events to analyze.")
        advisor = RecommenderAdvisor(backend=backend)
        result = advisor.advise(events=[])
        self.assertEqual(result.status, "success")
        self.assertEqual(result.metadata["total_events"], 0)

    def test_gap_detection_in_prompt(self) -> None:
        """Aggregates should be passed correctly for gap detection."""
        backend = FakeAIBackend(response_content="ok")
        advisor = RecommenderAdvisor(backend=backend)
        advisor.advise(events=self._make_events())

        user_msg = backend.calls[0][1].content
        # Check policy names
        self.assertIn("p1", user_msg)
        self.assertIn("p2", user_msg)
        # Check tags
        self.assertIn("secret", user_msg)
        self.assertIn("personal", user_msg)

    def test_backend_error(self) -> None:
        class FailingBackend:
            @property
            def model_name(self) -> str:
                return "fail"
            def complete(self, messages, **kwargs):
                raise RuntimeError("timeout")

        advisor = RecommenderAdvisor(backend=FailingBackend())
        result = advisor.advise(events=[])
        self.assertEqual(result.status, "error")

    def test_recommendation_output_format(self) -> None:
        response = (
            "--- FILE: policies/recommended.yaml ---\n"
            "policies:\n"
            "  - name: close-output-gap\n"
            "    boundary: [output]\n"
            "    priority: 15\n"
            "    action: block\n"
        )
        backend = FakeAIBackend(response_content=response)
        advisor = RecommenderAdvisor(backend=backend)
        result = advisor.advise(events=self._make_events())
        self.assertIn("close-output-gap", result.artifacts.get("policies/recommended.yaml", ""))


if __name__ == "__main__":
    unittest.main()
