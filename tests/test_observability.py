"""Tests for agent observability features."""

from __future__ import annotations

from safeai.proxy.metrics import ProxyMetrics


class TestProxyMetricsAgentTracking:
    def test_agent_summary_empty(self) -> None:
        metrics = ProxyMetrics()
        assert metrics.agent_summary() == []

    def test_agent_summary_tracks_requests(self) -> None:
        metrics = ProxyMetrics()
        metrics.observe_request(
            endpoint="/v1/scan/input",
            status_code=200,
            latency_seconds=0.01,
            agent_id="agent-1",
        )
        metrics.observe_request(
            endpoint="/v1/scan/input",
            status_code=200,
            latency_seconds=0.02,
            agent_id="agent-1",
        )
        metrics.observe_request(
            endpoint="/v1/guard/output",
            status_code=200,
            latency_seconds=0.01,
            agent_id="agent-2",
        )
        summary = metrics.agent_summary()
        assert len(summary) == 2
        agent_1 = next(a for a in summary if a["agent_id"] == "agent-1")
        assert agent_1["request_count"] == 2
        assert agent_1["last_seen"] is not None

    def test_agent_summary_ignores_unknown(self) -> None:
        metrics = ProxyMetrics()
        metrics.observe_request(
            endpoint="/v1/scan/input",
            status_code=200,
            latency_seconds=0.01,
            agent_id="unknown",
        )
        assert metrics.agent_summary() == []

    def test_agent_summary_ignores_none(self) -> None:
        metrics = ProxyMetrics()
        metrics.observe_request(
            endpoint="/v1/scan/input",
            status_code=200,
            latency_seconds=0.01,
        )
        assert metrics.agent_summary() == []

    def test_tool_summary_tracks_requests(self) -> None:
        metrics = ProxyMetrics()
        metrics.observe_request(
            endpoint="/v1/intercept/tool",
            status_code=200,
            latency_seconds=0.01,
            tool_name="file_read",
        )
        metrics.observe_request(
            endpoint="/v1/intercept/tool",
            status_code=200,
            latency_seconds=0.01,
            tool_name="file_read",
        )
        metrics.observe_request(
            endpoint="/v1/intercept/tool",
            status_code=200,
            latency_seconds=0.01,
            tool_name="web_search",
        )
        summary = metrics.tool_summary()
        assert len(summary) == 2
        assert summary[0]["tool_name"] == "file_read"
        assert summary[0]["request_count"] == 2

    def test_tool_summary_empty(self) -> None:
        metrics = ProxyMetrics()
        assert metrics.tool_summary() == []

    def test_backward_compat_no_agent_tool(self) -> None:
        """observe_request still works without agent_id/tool_name kwargs."""
        metrics = ProxyMetrics()
        metrics.observe_request(
            endpoint="/v1/scan/input",
            status_code=200,
            latency_seconds=0.05,
            decision_action="allow",
        )
        prom = metrics.render_prometheus()
        assert "safeai_proxy_requests_total" in prom


class TestDashboardObservability:
    def test_agent_timeline_groups_correctly(self, tmp_path) -> None:
        from safeai.core.audit import AuditEvent, AuditLogger

        audit_path = tmp_path / "audit.log"
        logger = AuditLogger(str(audit_path))
        logger.emit(AuditEvent(
            boundary="input", action="block", policy_name="test",
            reason="test", data_tags=["secret"], agent_id="agent-a",
            timestamp="2024-01-01T00:01:00+00:00",
        ))
        logger.emit(AuditEvent(
            boundary="output", action="allow", policy_name="test",
            reason="ok", data_tags=[], agent_id="agent-b",
            timestamp="2024-01-01T00:02:00+00:00",
        ))
        logger.emit(AuditEvent(
            boundary="input", action="allow", policy_name="test",
            reason="ok", data_tags=[], agent_id="agent-a",
            timestamp="2024-01-01T00:03:00+00:00",
        ))
        all_events = logger.query(limit=100, newest_first=True)
        agents: dict[str, int] = {}
        for evt in all_events:
            aid = str(evt.get("agent_id", "unknown"))
            agents[aid] = agents.get(aid, 0) + 1
        assert agents.get("agent-a", 0) == 2
        assert agents.get("agent-b", 0) == 1

    def test_session_trace_chronological(self, tmp_path) -> None:
        from safeai.core.audit import AuditEvent, AuditLogger

        audit_path = tmp_path / "audit.log"
        logger = AuditLogger(str(audit_path))
        logger.emit(AuditEvent(
            boundary="input", action="allow", policy_name="test",
            reason="ok", data_tags=[], agent_id="agent-a",
            session_id="sess-1", timestamp="2024-01-01T00:03:00+00:00",
        ))
        logger.emit(AuditEvent(
            boundary="output", action="allow", policy_name="test",
            reason="ok", data_tags=[], agent_id="agent-a",
            session_id="sess-1", timestamp="2024-01-01T00:01:00+00:00",
        ))
        trace = logger.query(session_id="sess-1", newest_first=False, limit=100)
        assert len(trace) == 2
        assert trace[0]["timestamp"] <= trace[1]["timestamp"]
