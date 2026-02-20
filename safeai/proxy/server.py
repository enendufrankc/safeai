"""FastAPI app factory for sidecar/gateway mode."""

from __future__ import annotations

from fastapi import FastAPI

from safeai.proxy.routes import router
from safeai.proxy.ws import register_websocket_routes


def create_app() -> FastAPI:
    app = FastAPI(title="SafeAI Proxy", version="0.1.0rc1")
    app.include_router(router)
    register_websocket_routes(app)
    return app
