"""In-process Prometheus-style metrics for proxy endpoints."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from threading import RLock
from typing import Any


class ProxyMetrics:
    """Collect request counters and latency histograms."""

    _BUCKETS = (0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)

    def __init__(self) -> None:
        self._lock = RLock()
        self._request_count: dict[tuple[str, str, str], int] = defaultdict(int)
        self._decision_count: dict[tuple[str, str], int] = defaultdict(int)
        self._latency_count: dict[tuple[str], int] = defaultdict(int)
        self._latency_sum: dict[tuple[str], float] = defaultdict(float)
        self._latency_bucket_count: dict[tuple[str, float], int] = defaultdict(int)
        self._agent_request_count: dict[str, int] = defaultdict(int)
        self._agent_last_seen: dict[str, str] = {}
        self._tool_request_count: dict[str, int] = defaultdict(int)

    def observe_request(
        self,
        *,
        endpoint: str,
        status_code: int,
        latency_seconds: float,
        decision_action: str | None = None,
        agent_id: str | None = None,
        tool_name: str | None = None,
    ) -> None:
        endpoint_token = str(endpoint).strip() or "unknown"
        status_token = str(status_code)
        with self._lock:
            self._request_count[(endpoint_token, status_token, "http")] += 1
            if decision_action:
                self._decision_count[(endpoint_token, str(decision_action).strip().lower())] += 1
            self._latency_count[(endpoint_token,)] += 1
            self._latency_sum[(endpoint_token,)] += float(latency_seconds)
            for bound in self._BUCKETS:
                if latency_seconds <= bound:
                    self._latency_bucket_count[(endpoint_token, bound)] += 1
            self._latency_bucket_count[(endpoint_token, float("inf"))] += 1
            if agent_id and str(agent_id).strip().lower() != "unknown":
                agent_token = str(agent_id).strip().lower()
                self._agent_request_count[agent_token] += 1
                self._agent_last_seen[agent_token] = datetime.now(timezone.utc).isoformat()
            if tool_name and str(tool_name).strip():
                tool_token = str(tool_name).strip().lower()
                self._tool_request_count[tool_token] += 1

    def agent_summary(self) -> list[dict[str, Any]]:
        """Return per-agent request counts and last-seen timestamps."""
        with self._lock:
            return [
                {
                    "agent_id": agent_id,
                    "request_count": self._agent_request_count[agent_id],
                    "last_seen": self._agent_last_seen.get(agent_id),
                }
                for agent_id in sorted(self._agent_request_count.keys())
            ]

    def tool_summary(self) -> list[dict[str, Any]]:
        """Return per-tool request counts."""
        with self._lock:
            return [
                {"tool_name": tool_name, "request_count": count}
                for tool_name, count in sorted(
                    self._tool_request_count.items(), key=lambda x: (-x[1], x[0])
                )
            ]

    def render_prometheus(self) -> str:
        with self._lock:
            request_count = dict(self._request_count)
            decision_count = dict(self._decision_count)
            latency_count = dict(self._latency_count)
            latency_sum = dict(self._latency_sum)
            latency_bucket_count = dict(self._latency_bucket_count)

        lines: list[str] = []
        lines.append("# HELP safeai_proxy_requests_total Total proxy HTTP requests")
        lines.append("# TYPE safeai_proxy_requests_total counter")
        for (endpoint, status, protocol), value in sorted(request_count.items()):
            lines.append(
                f'safeai_proxy_requests_total{{endpoint="{endpoint}",status="{status}",protocol="{protocol}"}} {value}'
            )

        lines.append("# HELP safeai_proxy_decisions_total Total proxy decisions by action")
        lines.append("# TYPE safeai_proxy_decisions_total counter")
        for (endpoint, action), value in sorted(decision_count.items()):
            lines.append(f'safeai_proxy_decisions_total{{endpoint="{endpoint}",action="{action}"}} {value}')

        lines.append("# HELP safeai_proxy_request_latency_seconds Proxy request latency histogram")
        lines.append("# TYPE safeai_proxy_request_latency_seconds histogram")
        for (endpoint,), count in sorted(latency_count.items()):
            for bound in self._BUCKETS:
                value = latency_bucket_count.get((endpoint, bound), 0)
                lines.append(
                    f'safeai_proxy_request_latency_seconds_bucket{{endpoint="{endpoint}",le="{bound}"}} {value}'
                )
            inf_value = latency_bucket_count.get((endpoint, float("inf")), 0)
            lines.append(
                f'safeai_proxy_request_latency_seconds_bucket{{endpoint="{endpoint}",le="+Inf"}} {inf_value}'
            )
            lines.append(
                f'safeai_proxy_request_latency_seconds_sum{{endpoint="{endpoint}"}} {latency_sum.get((endpoint,), 0.0)}'
            )
            lines.append(
                f'safeai_proxy_request_latency_seconds_count{{endpoint="{endpoint}"}} {count}'
            )
        return "\n".join(lines) + "\n"
