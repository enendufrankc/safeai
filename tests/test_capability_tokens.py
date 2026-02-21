"""Capability-token issuance and action-boundary enforcement tests."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from safeai import SafeAI
from safeai.core.audit import AuditLogger
from safeai.core.classifier import Classifier
from safeai.core.contracts import ToolContractRegistry, normalize_contracts
from safeai.core.identity import AgentIdentityRegistry, normalize_agent_identities
from safeai.core.interceptor import ActionInterceptor, ToolCall
from safeai.core.policy import PolicyEngine, normalize_rules
from safeai.secrets.capability import CapabilityTokenManager


class _FrozenClock:
    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **delta_kwargs: int) -> None:
        self.now = self.now + timedelta(**delta_kwargs)


def _policy_engine() -> PolicyEngine:
    return PolicyEngine(
        normalize_rules(
            [
                {
                    "name": "allow-action-default",
                    "boundary": ["action"],
                    "action": "allow",
                    "reason": "allow",
                    "priority": 1000,
                }
            ]
        )
    )


def _contract_registry() -> ToolContractRegistry:
    return ToolContractRegistry(
        normalize_contracts(
            [
                {
                    "version": "v1alpha1",
                    "contract": {
                        "tool_name": "send_email",
                        "accepts": {
                            "tags": ["internal"],
                            "fields": ["to", "subject", "body"],
                        },
                        "emits": {
                            "tags": ["internal"],
                            "fields": ["status", "message_id"],
                        },
                        "side_effects": {
                            "reversible": False,
                            "requires_approval": True,
                        },
                    },
                }
            ]
        )
    )


def _identity_registry() -> AgentIdentityRegistry:
    return AgentIdentityRegistry(
        normalize_agent_identities(
            [
                {
                    "version": "v1alpha1",
                    "agent": {
                        "agent_id": "ops-bot",
                        "tools": ["send_email"],
                        "clearance_tags": ["internal"],
                    },
                }
            ]
        )
    )


class CapabilityTokenTests(unittest.TestCase):
    def test_issue_validate_and_expire_token(self) -> None:
        clock = _FrozenClock(datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc))
        manager = CapabilityTokenManager(clock=clock)

        token = manager.issue(
            agent_id="ops-bot",
            tool_name="send_email",
            actions=["invoke", "INVOKE"],
            ttl="10m",
            secret_keys=["SMTP_TOKEN", "SMTP_TOKEN"],
            metadata={"purpose": "send-once"},
        )
        self.assertTrue(token.token_id.startswith("cap_"))
        self.assertEqual(token.scope.actions, ["invoke"])
        self.assertEqual(token.scope.secret_keys, ["SMTP_TOKEN"])

        allowed = manager.validate(
            token.token_id,
            agent_id="ops-bot",
            tool_name="send_email",
            action="invoke",
        )
        self.assertTrue(allowed.allowed)

        clock.advance(minutes=11)
        expired = manager.validate(
            token.token_id,
            agent_id="ops-bot",
            tool_name="send_email",
            action="invoke",
        )
        self.assertFalse(expired.allowed)
        self.assertIn("expired", expired.reason)

    def test_session_binding_is_enforced(self) -> None:
        clock = _FrozenClock(datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc))
        manager = CapabilityTokenManager(clock=clock)
        token = manager.issue(
            agent_id="ops-bot",
            tool_name="send_email",
            actions=["invoke"],
            ttl="10m",
            session_id="sess-1",
        )

        missing_session = manager.validate(
            token.token_id,
            agent_id="ops-bot",
            tool_name="send_email",
            action="invoke",
        )
        self.assertFalse(missing_session.allowed)
        self.assertIn("session binding mismatch", missing_session.reason)

        wrong_session = manager.validate(
            token.token_id,
            agent_id="ops-bot",
            tool_name="send_email",
            action="invoke",
            session_id="sess-2",
        )
        self.assertFalse(wrong_session.allowed)
        self.assertIn("session binding mismatch", wrong_session.reason)

        valid = manager.validate(
            token.token_id,
            agent_id="ops-bot",
            tool_name="send_email",
            action="invoke",
            session_id="sess-1",
        )
        self.assertTrue(valid.allowed)

    def test_revoke_list_active_and_purge(self) -> None:
        clock = _FrozenClock(datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc))
        manager = CapabilityTokenManager(clock=clock)
        revoked = manager.issue(
            agent_id="ops-bot",
            tool_name="send_email",
            actions=["invoke"],
            ttl="10m",
        )
        expiring = manager.issue(
            agent_id="ops-bot",
            tool_name="send_email",
            actions=["invoke"],
            ttl="1m",
        )
        active = manager.issue(
            agent_id="ops-bot",
            tool_name="send_email",
            actions=["invoke"],
            ttl="20m",
        )

        self.assertTrue(manager.revoke(revoked.token_id))
        self.assertFalse(manager.revoke(revoked.token_id))
        self.assertIsNone(manager.get(revoked.token_id))

        clock.advance(minutes=2)
        active_tokens = manager.list_active(agent_id="ops-bot", tool_name="send_email")
        self.assertEqual([row.token_id for row in active_tokens], [active.token_id])
        self.assertIsNone(manager.get(expiring.token_id))

        purged = manager.purge_expired()
        self.assertEqual(purged, 2)
        still_active = manager.list_active(agent_id="ops-bot", tool_name="send_email")
        self.assertEqual([row.token_id for row in still_active], [active.token_id])

    def test_invalid_ttl_format_raises(self) -> None:
        manager = CapabilityTokenManager()
        with self.assertRaises(ValueError):
            manager.issue(
                agent_id="ops-bot",
                tool_name="send_email",
                actions=["invoke"],
                ttl="tomorrow",
            )

    def test_interceptor_blocks_when_capability_invalid_and_logs_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit = AuditLogger(str(Path(tmp_dir) / "audit.log"))
            interceptor = ActionInterceptor(
                policy_engine=_policy_engine(),
                audit_logger=audit,
                contract_registry=_contract_registry(),
                identity_registry=_identity_registry(),
                capability_manager=CapabilityTokenManager(),
            )
            result = interceptor.intercept_request(
                ToolCall(
                    tool_name="send_email",
                    agent_id="ops-bot",
                    parameters={"to": "ops@example.com"},
                    data_tags=["internal"],
                    capability_token_id="cap_missing",
                    capability_action="invoke",
                )
            )
            self.assertEqual(result.decision.action, "block")
            self.assertEqual(result.decision.policy_name, "capability-token")
            self.assertEqual(result.filtered_params, {})

            events = audit.query(boundary="action", phase="request", policy_name="capability-token", limit=1)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["metadata"]["decision_source"], "capability-token")
            self.assertEqual(events[0]["metadata"]["capability_token_id"], "cap_missing")

    def test_sdk_exposes_capability_token_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            clock = _FrozenClock(datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc))
            manager = CapabilityTokenManager(clock=clock)
            sdk = SafeAI(
                policy_engine=_policy_engine(),
                classifier=Classifier(),
                audit_logger=AuditLogger(str(Path(tmp_dir) / "audit.log")),
                contract_registry=_contract_registry(),
                identity_registry=_identity_registry(),
                capability_manager=manager,
            )
            token = sdk.issue_capability_token(
                agent_id="ops-bot",
                tool_name="send_email",
                actions=["invoke"],
                ttl="10m",
                session_id="sess-1",
            )
            request = sdk.intercept_tool_request(
                "send_email",
                {"to": "ops@example.com", "subject": "S", "body": "B"},
                data_tags=["internal"],
                agent_id="ops-bot",
                session_id="sess-1",
                capability_token_id=token.token_id,
                capability_action="invoke",
            )
            self.assertEqual(request.decision.action, "allow")
            self.assertEqual(request.filtered_params["to"], "ops@example.com")

            blocked = sdk.intercept_tool_request(
                "send_email",
                {"to": "ops@example.com"},
                data_tags=["internal"],
                agent_id="ops-bot",
                session_id="sess-wrong",
                capability_token_id=token.token_id,
                capability_action="invoke",
            )
            self.assertEqual(blocked.decision.action, "block")
            self.assertEqual(blocked.decision.policy_name, "capability-token")


if __name__ == "__main__":
    unittest.main()
