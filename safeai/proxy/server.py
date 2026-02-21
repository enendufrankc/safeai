"""FastAPI app factory for sidecar/gateway mode."""

from __future__ import annotations

import importlib.metadata
import os
from dataclasses import dataclass
from typing import Literal, cast

from fastapi import FastAPI

try:
    _VERSION = importlib.metadata.version("safeai")
except importlib.metadata.PackageNotFoundError:
    _VERSION = "0.0.0-dev"

from safeai import SafeAI
from safeai.config.loader import load_config
from safeai.dashboard.routes import router as dashboard_router
from safeai.dashboard.service import DashboardService
from safeai.proxy.metrics import ProxyMetrics
from safeai.proxy.routes import router
from safeai.proxy.ws import register_websocket_routes


@dataclass(frozen=True)
class ProxyRuntime:
    safeai: SafeAI
    mode: Literal["sidecar", "gateway"]
    upstream_base_url: str | None
    metrics: ProxyMetrics
    dashboard: DashboardService


def create_app(
    *,
    config_path: str | None = None,
    mode: str | None = None,
    upstream_base_url: str | None = None,
) -> FastAPI:
    resolved_config = str(config_path or os.getenv("SAFEAI_CONFIG") or "safeai.yaml")
    resolved_mode = str(mode or os.getenv("SAFEAI_PROXY_MODE") or "sidecar").strip().lower()
    if resolved_mode not in {"sidecar", "gateway"}:
        raise ValueError("Proxy mode must be 'sidecar' or 'gateway'.")
    resolved_mode_literal = cast(Literal["sidecar", "gateway"], resolved_mode)
    resolved_upstream = upstream_base_url or os.getenv("SAFEAI_UPSTREAM_BASE_URL")
    cfg = load_config(resolved_config)
    sdk = SafeAI.from_config(resolved_config)
    dashboard = DashboardService(sdk=sdk, config_path=resolved_config, config=cfg.dashboard)

    app = FastAPI(title="SafeAI Proxy", version=_VERSION)
    app.state.runtime = ProxyRuntime(
        safeai=sdk,
        mode=resolved_mode_literal,
        upstream_base_url=resolved_upstream,
        metrics=ProxyMetrics(),
        dashboard=dashboard,
    )
    app.include_router(router)
    app.include_router(dashboard_router)
    register_websocket_routes(app)
    return app
