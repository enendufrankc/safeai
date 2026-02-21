"""Capability token management with TTL- and scope-based validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from uuid import uuid4

from safeai.core.models import CapabilityScopeModel, CapabilityTokenModel

Clock = Callable[[], datetime]


@dataclass(frozen=True)
class CapabilityValidationResult:
    allowed: bool
    reason: str
    token: CapabilityTokenModel | None


class CapabilityTokenManager:
    """In-memory capability token issuer and validator."""

    def __init__(self, *, clock: Clock | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._tokens: dict[str, CapabilityTokenModel] = {}

    def issue(
        self,
        *,
        agent_id: str,
        tool_name: str,
        actions: list[str],
        ttl: str = "10m",
        secret_keys: list[str] | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CapabilityTokenModel:
        issued_at = self._clock()
        expires_at = issued_at + _parse_duration(ttl)
        token = CapabilityTokenModel(
            token_id=f"cap_{uuid4().hex[:24]}",
            agent_id=agent_id,
            issued_at=issued_at,
            expires_at=expires_at,
            session_id=session_id,
            scope=CapabilityScopeModel(
                tool_name=tool_name,
                actions=actions,
                secret_keys=secret_keys or [],
            ),
            metadata=dict(metadata or {}),
        )
        self._tokens[token.token_id] = token
        return token

    def get(self, token_id: str) -> CapabilityTokenModel | None:
        token = self._tokens.get(str(token_id).strip())
        if token is None:
            return None
        if token.revoked_at is not None:
            return None
        if _is_expired(token, now=self._clock()):
            return None
        return token

    def validate(
        self,
        token_id: str,
        *,
        agent_id: str,
        tool_name: str,
        action: str = "invoke",
        session_id: str | None = None,
    ) -> CapabilityValidationResult:
        token = self._tokens.get(str(token_id).strip())
        if token is None:
            return CapabilityValidationResult(
                allowed=False,
                reason=f"capability token '{token_id}' not found",
                token=None,
            )
        if token.revoked_at is not None:
            return CapabilityValidationResult(
                allowed=False,
                reason=f"capability token '{token_id}' is revoked",
                token=token,
            )
        if _is_expired(token, now=self._clock()):
            return CapabilityValidationResult(
                allowed=False,
                reason=f"capability token '{token_id}' is expired",
                token=token,
            )
        if token.agent_id != str(agent_id).strip():
            return CapabilityValidationResult(
                allowed=False,
                reason="capability token agent binding mismatch",
                token=token,
            )
        if token.scope.tool_name != str(tool_name).strip():
            return CapabilityValidationResult(
                allowed=False,
                reason="capability token tool binding mismatch",
                token=token,
            )
        normalized_action = str(action).strip().lower()
        if normalized_action not in token.scope.actions:
            return CapabilityValidationResult(
                allowed=False,
                reason=f"capability token does not allow action '{normalized_action}'",
                token=token,
            )
        requested_session = str(session_id).strip() if session_id else None
        if token.session_id and token.session_id != requested_session:
            return CapabilityValidationResult(
                allowed=False,
                reason="capability token session binding mismatch",
                token=token,
            )
        return CapabilityValidationResult(
            allowed=True,
            reason="capability token valid",
            token=token,
        )

    def revoke(self, token_id: str) -> bool:
        token = self._tokens.get(str(token_id).strip())
        if token is None:
            return False
        if token.revoked_at is not None:
            return False
        updated = token.model_copy(update={"revoked_at": self._clock()})
        self._tokens[updated.token_id] = CapabilityTokenModel.model_validate(updated.model_dump())
        return True

    def purge_expired(self) -> int:
        now = self._clock()
        purged = 0
        for token_id in list(self._tokens.keys()):
            token = self._tokens[token_id]
            if token.revoked_at is not None or _is_expired(token, now=now):
                self._tokens.pop(token_id, None)
                purged += 1
        return purged

    def list_active(
        self,
        *,
        agent_id: str | None = None,
        tool_name: str | None = None,
    ) -> list[CapabilityTokenModel]:
        now = self._clock()
        rows: list[CapabilityTokenModel] = []
        for token in self._tokens.values():
            if token.revoked_at is not None or _is_expired(token, now=now):
                continue
            if agent_id and token.agent_id != str(agent_id).strip():
                continue
            if tool_name and token.scope.tool_name != str(tool_name).strip():
                continue
            rows.append(token)
        rows.sort(key=lambda item: item.issued_at, reverse=True)
        return rows


def _is_expired(token: CapabilityTokenModel, *, now: datetime) -> bool:
    reference = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    return token.expires_at <= reference


def _parse_duration(value: str) -> timedelta:
    match = re.match(r"^\s*(\d+)\s*([smhdw])\s*$", str(value).lower())
    if not match:
        raise ValueError(f"Invalid duration '{value}'. Use forms like 30s, 15m, 2h, 7d.")

    amount = int(match.group(1))
    unit = match.group(2)
    if unit == "s":
        return timedelta(seconds=amount)
    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    if unit == "d":
        return timedelta(days=amount)
    return timedelta(weeks=amount)
