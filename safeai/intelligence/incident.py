"""Incident Response advisory agent — classifies and explains security events."""

from __future__ import annotations

from typing import Any

from safeai.intelligence.advisor import AdvisorResult, BaseAdvisor
from safeai.intelligence.backend import AIBackend, AIMessage
from safeai.intelligence.prompts.incident import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from safeai.intelligence.sanitizer import MetadataSanitizer


class IncidentAdvisor(BaseAdvisor):
    """Reads a sanitized audit event and classifies/explains the incident."""

    def __init__(
        self,
        backend: AIBackend,
        sanitizer: MetadataSanitizer | None = None,
    ) -> None:
        super().__init__(backend, sanitizer)

    @property
    def name(self) -> str:
        return "incident"

    def advise(self, **kwargs: Any) -> AdvisorResult:
        event = kwargs.get("event")
        context_events = kwargs.get("context_events", [])
        event_id = kwargs.get("event_id")
        config_path = kwargs.get("config_path")

        # If given raw event dict, use it directly; else look up by event_id
        if event is None and event_id and config_path:
            try:
                from safeai.api import SafeAI

                sai = SafeAI.from_config(config_path)
                events = sai.query_audit(event_id=event_id)
                if not events:
                    return self._error_result(f"Event '{event_id}' not found.")
                event = events[0]
                context_events = sai.query_audit(last="1h", limit=5)
            except Exception as exc:
                return self._error_result(f"Failed to load event: {exc}")

        if event is None:
            return self._error_result("No event provided.")

        sanitized = self._sanitizer.sanitize_event(event)

        metadata_lines = []
        for k, v in sanitized.safe_metadata.items():
            metadata_lines.append(f"- {k}: {v}")
        metadata_section = "\n".join(metadata_lines) if metadata_lines else "(none)"

        context_lines = []
        for ctx_event in context_events[:5]:
            ctx = self._sanitizer.sanitize_event(ctx_event)
            context_lines.append(
                f"- [{ctx.timestamp}] {ctx.boundary}/{ctx.action} "
                f"policy={ctx.policy_name} agent={ctx.agent_id} "
                f"tags={','.join(ctx.data_tags)}"
            )
        context_section = "\n".join(context_lines) if context_lines else "(no context events)"

        user_prompt = USER_PROMPT_TEMPLATE.format(
            event_id=sanitized.event_id,
            timestamp=sanitized.timestamp,
            boundary=sanitized.boundary,
            action=sanitized.action,
            policy_name=sanitized.policy_name,
            reason=sanitized.reason,
            data_tags=", ".join(sanitized.data_tags),
            agent_id=sanitized.agent_id,
            tool_name=sanitized.tool_name,
            session_id=sanitized.session_id,
            metadata_section=metadata_section,
            context_section=context_section,
        )

        messages = [
            AIMessage(role="system", content=SYSTEM_PROMPT),
            AIMessage(role="user", content=user_prompt),
        ]

        try:
            response = self._backend.complete(messages)
        except Exception as exc:
            return self._error_result(f"AI backend error: {exc}")

        return AdvisorResult(
            advisor_name=self.name,
            status="success",
            summary=f"Incident analysis for event {sanitized.event_id}",
            raw_response=response.content,
            model_used=response.model,
            metadata={
                "event_id": sanitized.event_id,
                "boundary": sanitized.boundary,
                "action": sanitized.action,
                "policy_name": sanitized.policy_name,
                "context_event_count": len(context_events),
            },
        )
