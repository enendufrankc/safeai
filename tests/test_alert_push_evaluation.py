"""Tests for push-based alert evaluation, sliding window, and cooldown."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from safeai.core.audit import AuditEvent, AuditLogger
from safeai.dashboard.service import AlertRule, AlertRuleManager


def _make_event(
    *,
    boundary: str = "input",
    action: str = "block",
    agent_id: str = "test-agent",
    timestamp: str | None = None,
) -> dict:
    return {
        "event_id": f"evt_{id(boundary)}",
        "boundary": boundary,
        "action": action,
        "policy_name": "test-policy",
        "reason": "test reason",
        "data_tags": ["secret"],
        "agent_id": agent_id,
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
    }


def _make_rule(
    *,
    rule_id: str = "rule-1",
    threshold: int = 3,
    window: str = "15m",
    boundaries: list[str] | None = None,
    actions: list[str] | None = None,
) -> AlertRule:
    filters: dict = {}
    if boundaries:
        filters["boundaries"] = boundaries
    if actions:
        filters["actions"] = actions
    return AlertRule(
        rule_id=rule_id,
        name="Test Rule",
        threshold=threshold,
        window=window,
        filters=filters,
        channels=("file",),
    )


class TestEvaluateSingleEvent:
    def test_triggers_at_threshold(self, tmp_path: Path) -> None:
        manager = AlertRuleManager(rules_file=None, alert_log_file=tmp_path / "alerts.log", cooldown_seconds=0)
        rule = _make_rule(threshold=3, actions=["block"])
        manager.upsert(rule)

        # First two events: no trigger
        for _ in range(2):
            triggered = manager.evaluate_single_event(_make_event(action="block"))
            assert len(triggered) == 0

        # Third event: triggers
        triggered = manager.evaluate_single_event(_make_event(action="block"))
        assert len(triggered) == 1
        assert triggered[0]["rule_id"] == "rule-1"
        assert triggered[0]["count"] >= 3

    def test_non_matching_events_ignored(self) -> None:
        manager = AlertRuleManager(rules_file=None, alert_log_file=None, cooldown_seconds=0)
        rule = _make_rule(threshold=1, actions=["block"])
        manager.upsert(rule)
        triggered = manager.evaluate_single_event(_make_event(action="allow"))
        assert len(triggered) == 0

    def test_cooldown_deduplication(self, tmp_path: Path) -> None:
        manager = AlertRuleManager(
            rules_file=None, alert_log_file=tmp_path / "alerts.log", cooldown_seconds=300
        )
        rule = _make_rule(threshold=1, actions=["block"])
        manager.upsert(rule)

        # First trigger
        triggered = manager.evaluate_single_event(_make_event(action="block"))
        assert len(triggered) == 1

        # Second trigger within cooldown: suppressed
        triggered = manager.evaluate_single_event(_make_event(action="block"))
        assert len(triggered) == 0

    def test_sliding_window_expiry(self) -> None:
        manager = AlertRuleManager(rules_file=None, alert_log_file=None, cooldown_seconds=0)
        rule = _make_rule(threshold=3, window="1s", actions=["block"])
        manager.upsert(rule)

        # Add 2 events
        manager.evaluate_single_event(_make_event(action="block"))
        manager.evaluate_single_event(_make_event(action="block"))

        # Wait for window to expire
        time.sleep(1.1)

        # Third event: window expired, counter reset, not enough
        triggered = manager.evaluate_single_event(_make_event(action="block"))
        assert len(triggered) == 0

    def test_dispatches_to_external_channels(self, tmp_path: Path) -> None:
        from unittest.mock import MagicMock

        mock_channel = MagicMock()
        mock_channel.send.return_value = True
        manager = AlertRuleManager(rules_file=None, alert_log_file=None, cooldown_seconds=0)
        manager.set_alert_channels([mock_channel])
        rule = _make_rule(threshold=1, actions=["block"])
        manager.upsert(rule)
        manager.evaluate_single_event(_make_event(action="block"))
        mock_channel.send.assert_called_once()


class TestAuditLoggerCallback:
    def test_register_on_emit_fires(self, tmp_path: Path) -> None:
        logger = AuditLogger(str(tmp_path / "audit.log"))
        events_received: list[dict] = []
        logger.register_on_emit(lambda event: events_received.append(event))

        logger.emit(
            AuditEvent(
                boundary="input",
                action="block",
                policy_name="test",
                reason="test reason",
                data_tags=["secret"],
            )
        )
        assert len(events_received) == 1
        assert events_received[0]["boundary"] == "input"

    def test_callback_exception_does_not_crash_emit(self, tmp_path: Path) -> None:
        logger = AuditLogger(str(tmp_path / "audit.log"))

        def bad_callback(event: dict) -> None:
            raise RuntimeError("callback crash")

        logger.register_on_emit(bad_callback)

        # Should not raise
        logger.emit(
            AuditEvent(
                boundary="input",
                action="allow",
                policy_name="test",
                reason="test",
                data_tags=[],
            )
        )
        # Verify event was still written
        lines = (tmp_path / "audit.log").read_text().strip().splitlines()
        assert len(lines) == 1

    def test_multiple_callbacks(self, tmp_path: Path) -> None:
        logger = AuditLogger(str(tmp_path / "audit.log"))
        call_counts = [0, 0]

        def cb1(event: dict) -> None:
            call_counts[0] += 1

        def cb2(event: dict) -> None:
            call_counts[1] += 1

        logger.register_on_emit(cb1)
        logger.register_on_emit(cb2)
        logger.emit(
            AuditEvent(
                boundary="input",
                action="allow",
                policy_name="test",
                reason="test",
                data_tags=[],
            )
        )
        assert call_counts == [1, 1]
