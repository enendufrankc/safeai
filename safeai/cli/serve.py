"""safeai serve command."""

from __future__ import annotations

import click
import uvicorn

from safeai.proxy.server import create_app


@click.command(name="serve")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8910, show_default=True, type=int)
def serve_command(host: str, port: int) -> None:
    """Run SafeAI proxy server."""
    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="info")
