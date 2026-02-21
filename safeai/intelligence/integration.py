"""Integration advisory agent — generates framework-specific integration code."""

from __future__ import annotations

import re
from typing import Any

from safeai.intelligence.advisor import AdvisorResult, BaseAdvisor
from safeai.intelligence.backend import AIBackend, AIMessage
from safeai.intelligence.prompts.integration import (
    FRAMEWORK_DESCRIPTIONS,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)
from safeai.intelligence.sanitizer import MetadataSanitizer


class IntegrationAdvisor(BaseAdvisor):
    """Reads project structure and generates integration code for target frameworks."""

    def __init__(
        self,
        backend: AIBackend,
        sanitizer: MetadataSanitizer | None = None,
    ) -> None:
        super().__init__(backend, sanitizer)

    @property
    def name(self) -> str:
        return "integration"

    def advise(self, **kwargs: Any) -> AdvisorResult:
        target = kwargs.get("target", "generic").lower()
        project_path = kwargs.get("project_path", ".")

        try:
            structure = self._sanitizer.extract_codebase_structure(project_path)
        except Exception as exc:
            return self._error_result(f"Failed to analyze project: {exc}")

        framework_desc = FRAMEWORK_DESCRIPTIONS.get(target, FRAMEWORK_DESCRIPTIONS["generic"])

        user_prompt = USER_PROMPT_TEMPLATE.format(
            target=target,
            file_paths=", ".join(structure.file_paths[:80]),
            dependencies=", ".join(structure.dependencies[:40]),
            framework_hints=", ".join(structure.framework_hints) or "none detected",
            framework_description=framework_desc,
            target_lower=target.replace("-", "_"),
        )

        messages = [
            AIMessage(role="system", content=SYSTEM_PROMPT),
            AIMessage(role="user", content=user_prompt),
        ]

        try:
            response = self._backend.complete(messages)
        except Exception as exc:
            return self._error_result(f"AI backend error: {exc}")

        artifacts = _parse_file_artifacts(response.content)

        return AdvisorResult(
            advisor_name=self.name,
            status="success",
            summary=f"Generated {target} integration code ({len(artifacts)} file(s))",
            artifacts=artifacts,
            raw_response=response.content,
            model_used=response.model,
            metadata={
                "target": target,
                "project_path": str(project_path),
                "framework_hints": list(structure.framework_hints),
            },
        )


_FILE_MARKER_RE = re.compile(r"---\s*FILE:\s*(.+?)\s*---")


def _parse_file_artifacts(content: str) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    parts = _FILE_MARKER_RE.split(content)
    if len(parts) < 3:
        stripped = content.strip()
        if stripped:
            artifacts["integration.py"] = stripped
        return artifacts
    for i in range(1, len(parts) - 1, 2):
        filename = parts[i].strip()
        body = parts[i + 1].strip()
        body = re.sub(r"^```(?:yaml|yml|python)?\s*\n?", "", body)
        body = re.sub(r"\n?```\s*$", "", body)
        if body:
            artifacts[filename] = body
    return artifacts
