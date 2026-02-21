"""Tests for the integration advisory agent."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from safeai.intelligence.backend import AIMessage, AIResponse
from safeai.intelligence.integration import IntegrationAdvisor
from safeai.intelligence.prompts.integration import FRAMEWORK_DESCRIPTIONS


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


class FrameworkDescriptionTests(unittest.TestCase):
    def test_langchain_description_exists(self) -> None:
        self.assertIn("langchain", FRAMEWORK_DESCRIPTIONS)
        self.assertIn("BaseCallbackHandler", FRAMEWORK_DESCRIPTIONS["langchain"])

    def test_crewai_description_exists(self) -> None:
        self.assertIn("crewai", FRAMEWORK_DESCRIPTIONS)

    def test_generic_description_exists(self) -> None:
        self.assertIn("generic", FRAMEWORK_DESCRIPTIONS)

    def test_all_descriptions_are_nonempty(self) -> None:
        for name, desc in FRAMEWORK_DESCRIPTIONS.items():
            self.assertTrue(len(desc) > 10, f"Description for {name} is too short")


class IntegrationAdvisorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        Path(self.tmpdir, "app.py").write_text(
            "from crewai import Agent, Task\n\nclass MyAgent(Agent):\n    pass\n",
            encoding="utf-8",
        )
        Path(self.tmpdir, "pyproject.toml").write_text(
            '[project]\nname = "test"\ndependencies = [\n  "crewai>=0.1",\n]\n',
            encoding="utf-8",
        )

    def test_advise_success(self) -> None:
        response = (
            "--- FILE: safeai_crewai_integration.py ---\n"
            "from safeai import SafeAI\n\n"
            "def wrap_agent(agent):\n    pass\n"
        )
        backend = FakeAIBackend(response_content=response)
        advisor = IntegrationAdvisor(backend=backend)
        result = advisor.advise(target="crewai", project_path=self.tmpdir)

        self.assertEqual(result.status, "success")
        self.assertEqual(result.advisor_name, "integration")
        self.assertIn("safeai_crewai_integration.py", result.artifacts)

    def test_framework_detection(self) -> None:
        """Prompt should include detected frameworks from project structure."""
        backend = FakeAIBackend(response_content="--- FILE: integration.py ---\ncode")
        advisor = IntegrationAdvisor(backend=backend)
        advisor.advise(target="crewai", project_path=self.tmpdir)

        user_msg = backend.calls[0][1].content
        self.assertIn("crewai", user_msg)
        self.assertIn("app.py", user_msg)

    def test_code_generation(self) -> None:
        response = (
            "--- FILE: safeai_langchain_integration.py ---\n"
            "```python\n"
            "from safeai import SafeAI\n"
            "from langchain.callbacks import BaseCallbackHandler\n"
            "```\n"
        )
        backend = FakeAIBackend(response_content=response)
        advisor = IntegrationAdvisor(backend=backend)
        result = advisor.advise(target="langchain", project_path=self.tmpdir)
        content = result.artifacts.get("safeai_langchain_integration.py", "")
        self.assertIn("SafeAI", content)
        self.assertNotIn("```", content)

    def test_unknown_framework_uses_generic(self) -> None:
        backend = FakeAIBackend(response_content="--- FILE: integration.py ---\ncode")
        advisor = IntegrationAdvisor(backend=backend)
        result = advisor.advise(target="unknown-framework", project_path=self.tmpdir)
        self.assertEqual(result.status, "success")
        # Should use generic description
        user_msg = backend.calls[0][1].content
        self.assertIn("Generic Python", user_msg)

    def test_backend_error(self) -> None:
        class FailingBackend:
            @property
            def model_name(self) -> str:
                return "fail"
            def complete(self, messages, **kwargs):
                raise RuntimeError("timeout")

        advisor = IntegrationAdvisor(backend=FailingBackend())
        result = advisor.advise(target="langchain", project_path=self.tmpdir)
        self.assertEqual(result.status, "error")

    def test_invalid_project_path(self) -> None:
        backend = FakeAIBackend()
        advisor = IntegrationAdvisor(backend=backend)
        result = advisor.advise(target="langchain", project_path="/nonexistent/path/xyz")
        self.assertEqual(result.status, "error")


if __name__ == "__main__":
    unittest.main()
