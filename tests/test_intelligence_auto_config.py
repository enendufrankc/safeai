"""Tests for the auto-config advisory agent."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from safeai.intelligence.auto_config import AutoConfigAdvisor, _parse_file_artifacts
from safeai.intelligence.backend import AIMessage, AIResponse
from safeai.intelligence.sanitizer import MetadataSanitizer


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


class ParseFileArtifactsTests(unittest.TestCase):
    def test_parses_file_markers(self) -> None:
        content = (
            "Some preamble\n"
            "--- FILE: safeai.yaml ---\n"
            "version: v1alpha1\n"
            "--- FILE: policies/gen.yaml ---\n"
            "policies:\n  - name: test\n"
        )
        artifacts = _parse_file_artifacts(content)
        self.assertIn("safeai.yaml", artifacts)
        self.assertIn("policies/gen.yaml", artifacts)
        self.assertIn("v1alpha1", artifacts["safeai.yaml"])

    def test_no_markers_returns_whole_content_as_safeai_yaml(self) -> None:
        content = "version: v1alpha1\npolicies: []"
        artifacts = _parse_file_artifacts(content)
        self.assertIn("safeai.yaml", artifacts)
        self.assertEqual(artifacts["safeai.yaml"], content)

    def test_strips_code_fences(self) -> None:
        content = (
            "--- FILE: safeai.yaml ---\n"
            "```yaml\n"
            "version: v1alpha1\n"
            "```\n"
        )
        artifacts = _parse_file_artifacts(content)
        self.assertNotIn("```", artifacts["safeai.yaml"])

    def test_empty_content(self) -> None:
        artifacts = _parse_file_artifacts("")
        self.assertEqual(artifacts, {})


class AutoConfigAdvisorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        Path(self.tmpdir, "app.py").write_text(
            "from langchain import LLMChain\n\nclass MyAgent:\n    pass\n",
            encoding="utf-8",
        )
        Path(self.tmpdir, "pyproject.toml").write_text(
            '[project]\nname = "test"\ndependencies = [\n  "langchain>=0.1",\n]\n',
            encoding="utf-8",
        )

    def test_advise_success(self) -> None:
        response = (
            "--- FILE: safeai.yaml ---\n"
            "version: v1alpha1\n"
            "--- FILE: policies/generated.yaml ---\n"
            "policies:\n  - name: block-secrets\n"
        )
        backend = FakeAIBackend(response_content=response)
        advisor = AutoConfigAdvisor(backend=backend)
        result = advisor.advise(project_path=self.tmpdir)

        self.assertEqual(result.status, "success")
        self.assertEqual(result.advisor_name, "auto-config")
        self.assertIn("safeai.yaml", result.artifacts)
        self.assertIn("policies/generated.yaml", result.artifacts)
        self.assertEqual(result.model_used, "fake")

    def test_prompt_contains_project_structure(self) -> None:
        backend = FakeAIBackend(response_content="--- FILE: safeai.yaml ---\nversion: v1alpha1")
        advisor = AutoConfigAdvisor(backend=backend)
        advisor.advise(project_path=self.tmpdir)

        self.assertEqual(len(backend.calls), 1)
        messages = backend.calls[0]
        # System prompt should be first
        self.assertEqual(messages[0].role, "system")
        # User prompt should contain project structure
        user_msg = messages[1].content
        self.assertIn("app.py", user_msg)
        self.assertIn("langchain", user_msg)

    def test_framework_hint_included(self) -> None:
        backend = FakeAIBackend(response_content="--- FILE: safeai.yaml ---\ntest")
        advisor = AutoConfigAdvisor(backend=backend)
        advisor.advise(project_path=self.tmpdir, framework_hint="crewai")

        user_msg = backend.calls[0][1].content
        self.assertIn("crewai", user_msg)

    def test_invalid_project_path(self) -> None:
        backend = FakeAIBackend()
        advisor = AutoConfigAdvisor(backend=backend)
        result = advisor.advise(project_path="/nonexistent/path/abc123")
        self.assertEqual(result.status, "error")

    def test_backend_error_returns_error_result(self) -> None:
        class FailingBackend:
            @property
            def model_name(self) -> str:
                return "fail"

            def complete(self, messages, **kwargs):
                raise RuntimeError("connection failed")

        advisor = AutoConfigAdvisor(backend=FailingBackend())
        result = advisor.advise(project_path=self.tmpdir)
        self.assertEqual(result.status, "error")
        self.assertIn("backend error", result.summary.lower())

    def test_only_sanitized_data_in_prompts(self) -> None:
        """Verify no file body content enters the prompt — only structural metadata."""
        # Write a file with sensitive content
        Path(self.tmpdir, "secret.py").write_text(
            '# API_KEY = "sk-1234abcdef"\ndef get_key():\n    return os.environ["KEY"]\n',
            encoding="utf-8",
        )
        backend = FakeAIBackend(response_content="--- FILE: safeai.yaml ---\ntest")
        advisor = AutoConfigAdvisor(backend=backend)
        advisor.advise(project_path=self.tmpdir)

        user_msg = backend.calls[0][1].content
        # File name should appear (structural)
        self.assertIn("secret.py", user_msg)
        # Actual secret value should NOT appear
        self.assertNotIn("sk-1234abcdef", user_msg)
        # Function name may appear (structural), but not body
        self.assertNotIn('os.environ["KEY"]', user_msg)


if __name__ == "__main__":
    unittest.main()
