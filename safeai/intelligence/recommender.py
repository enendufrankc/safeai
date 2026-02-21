"""Policy Recommender advisory agent — suggests improvements from audit aggregates."""

from __future__ import annotations

import re
from typing import Any

from safeai.intelligence.advisor import AdvisorResult, BaseAdvisor
from safeai.intelligence.backend import AIBackend, AIMessage
from safeai.intelligence.prompts.recommender import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from safeai.intelligence.sanitizer import MetadataSanitizer


class RecommenderAdvisor(BaseAdvisor):
    """Reads audit aggregates and suggests policy improvements."""

    def __init__(
        self,
        backend: AIBackend,
        sanitizer: MetadataSanitizer | None = None,
    ) -> None:
        super().__init__(backend, sanitizer)

    @property
    def name(self) -> str:
        return "recommender"

    def advise(self, **kwargs: Any) -> AdvisorResult:
        events = kwargs.get("events")
        since = kwargs.get("since", "7d")
        config_path = kwargs.get("config_path")

        # If no events passed directly, load from config
        if events is None and config_path:
            try:
                from safeai.api import SafeAI

                sai = SafeAI.from_config(config_path)
                events = sai.query_audit(last=since)
            except Exception as exc:
                return self._error_result(f"Failed to load audit data: {exc}")

        if events is None:
            events = []

        aggregate = self._sanitizer.aggregate_events(events)

        def _format_counts(d: dict[str, int]) -> str:
            if not d:
                return "(none)"
            return "\n".join(f"  {k}: {v}" for k, v in sorted(d.items(), key=lambda x: -x[1]))

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
            since=since,
            total_events=aggregate.total_events,
            events_by_action=_format_counts(aggregate.events_by_action),
            events_by_boundary=_format_counts(aggregate.events_by_boundary),
            events_by_policy=_format_counts(aggregate.events_by_policy),
            events_by_agent=_format_counts(aggregate.events_by_agent),
            events_by_tool=_format_counts(aggregate.events_by_tool),
            events_by_tag=_format_counts(aggregate.events_by_tag),
            config_summary=config_summary,
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
            summary=(
                f"Analyzed {aggregate.total_events} events over {since}. "
                f"Generated {len(artifacts)} recommendation file(s)."
            ),
            artifacts=artifacts,
            raw_response=response.content,
            model_used=response.model,
            metadata={
                "since": since,
                "total_events": aggregate.total_events,
                "action_counts": aggregate.events_by_action,
                "boundary_counts": aggregate.events_by_boundary,
            },
        )


_FILE_MARKER_RE = re.compile(r"---\s*FILE:\s*(.+?)\s*---")


def _parse_file_artifacts(content: str) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    parts = _FILE_MARKER_RE.split(content)
    if len(parts) < 3:
        return artifacts
    for i in range(1, len(parts) - 1, 2):
        filename = parts[i].strip()
        body = parts[i + 1].strip()
        body = re.sub(r"^```(?:yaml|yml)?\s*\n?", "", body)
        body = re.sub(r"\n?```\s*$", "", body)
        if body:
            artifacts[filename] = body
    return artifacts
