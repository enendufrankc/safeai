"""Auto-Config advisory agent — generates SafeAI configuration from codebase structure."""

from __future__ import annotations

import re
from typing import Any

from safeai.intelligence.advisor import AdvisorResult, BaseAdvisor
from safeai.intelligence.backend import AIBackend, AIMessage
from safeai.intelligence.prompts.auto_config import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from safeai.intelligence.sanitizer import MetadataSanitizer


class AutoConfigAdvisor(BaseAdvisor):
    """Reads codebase structure and generates SafeAI configuration files."""

    def __init__(
        self,
        backend: AIBackend,
        sanitizer: MetadataSanitizer | None = None,
    ) -> None:
        super().__init__(backend, sanitizer)

    @property
    def name(self) -> str:
        return "auto-config"

    def advise(self, **kwargs: Any) -> AdvisorResult:
        project_path = kwargs.get("project_path", ".")
        framework_hint = kwargs.get("framework_hint")

        try:
            structure = self._sanitizer.extract_codebase_structure(project_path)
        except Exception as exc:
            return self._error_result(f"Failed to analyze project: {exc}")

        hint_extra = ""
        if framework_hint:
            hint_extra = f"User-specified framework: {framework_hint}"

        user_prompt = USER_PROMPT_TEMPLATE.format(
            file_paths=", ".join(structure.file_paths[:100]),
            imports=", ".join(structure.imports[:100]),
            class_names=", ".join(structure.class_names[:100]),
            function_names=", ".join(structure.function_names[:100]),
            decorators=", ".join(structure.decorators[:50]),
            dependencies=", ".join(structure.dependencies[:50]),
            framework_hints=", ".join(structure.framework_hints) or "none detected",
            framework_hint_extra=hint_extra,
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
            summary=f"Generated {len(artifacts)} configuration file(s) for project at {project_path}",
            artifacts=artifacts,
            raw_response=response.content,
            model_used=response.model,
            metadata={
                "project_path": str(project_path),
                "framework_hints": list(structure.framework_hints),
                "file_count": len(structure.file_paths),
                "class_count": len(structure.class_names),
                "function_count": len(structure.function_names),
            },
        )


_FILE_MARKER_RE = re.compile(r"---\s*FILE:\s*(.+?)\s*---")


def _parse_file_artifacts(content: str) -> dict[str, str]:
    """Parse AI response into filename → content mapping."""
    artifacts: dict[str, str] = {}
    parts = _FILE_MARKER_RE.split(content)
    # parts = [preamble, filename1, content1, filename2, content2, ...]
    if len(parts) < 3:
        # No file markers found — treat entire response as safeai.yaml
        stripped = content.strip()
        if stripped:
            artifacts["safeai.yaml"] = stripped
        return artifacts

    for i in range(1, len(parts) - 1, 2):
        filename = parts[i].strip()
        body = parts[i + 1].strip()
        # Strip markdown code fences if present
        body = re.sub(r"^```(?:yaml|yml)?\s*\n?", "", body)
        body = re.sub(r"\n?```\s*$", "", body)
        if body:
            artifacts[filename] = body

    return artifacts
