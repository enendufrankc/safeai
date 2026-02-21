"""Compliance advisory agent — generates compliance policy sets."""

from __future__ import annotations

import re
from typing import Any

from safeai.intelligence.advisor import AdvisorResult, BaseAdvisor
from safeai.intelligence.backend import AIBackend, AIMessage
from safeai.intelligence.prompts.compliance import (
    COMPLIANCE_REQUIREMENTS,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)
from safeai.intelligence.sanitizer import MetadataSanitizer


class ComplianceAdvisor(BaseAdvisor):
    """Maps compliance frameworks to SafeAI policy sets."""

    def __init__(
        self,
        backend: AIBackend,
        sanitizer: MetadataSanitizer | None = None,
    ) -> None:
        super().__init__(backend, sanitizer)

    @property
    def name(self) -> str:
        return "compliance"

    def advise(self, **kwargs: Any) -> AdvisorResult:
        framework = kwargs.get("framework", "hipaa").lower()
        config_path = kwargs.get("config_path")

        requirements = COMPLIANCE_REQUIREMENTS.get(framework)
        if not requirements:
            return self._error_result(
                f"Unknown compliance framework: {framework}. "
                f"Supported: {', '.join(COMPLIANCE_REQUIREMENTS.keys())}"
            )

        config_summary = "(no config loaded)"
        if config_path:
            try:
                from safeai.config.loader import load_config

                cfg = load_config(config_path)
                config_summary = (
                    f"Policy files: {cfg.paths.policy_files}\n"
                    f"Contract files: {cfg.paths.contract_files}\n"
                    f"Identity files: {cfg.paths.identity_files}"
                )
            except Exception:
                pass

        user_prompt = USER_PROMPT_TEMPLATE.format(
            framework=framework.upper(),
            requirements=requirements,
            config_summary=config_summary,
            framework_lower=framework,
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
            summary=f"Generated {framework.upper()} compliance policies ({len(artifacts)} file(s))",
            artifacts=artifacts,
            raw_response=response.content,
            model_used=response.model,
            metadata={"framework": framework},
        )


_FILE_MARKER_RE = re.compile(r"---\s*FILE:\s*(.+?)\s*---")


def _parse_file_artifacts(content: str) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    parts = _FILE_MARKER_RE.split(content)
    if len(parts) < 3:
        stripped = content.strip()
        if stripped:
            artifacts["policies/compliance.yaml"] = stripped
        return artifacts
    for i in range(1, len(parts) - 1, 2):
        filename = parts[i].strip()
        body = parts[i + 1].strip()
        body = re.sub(r"^```(?:yaml|yml|python)?\s*\n?", "", body)
        body = re.sub(r"\n?```\s*$", "", body)
        if body:
            artifacts[filename] = body
    return artifacts
