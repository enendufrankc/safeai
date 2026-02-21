"""safeai serve command."""

from __future__ import annotations

import click
import uvicorn

from safeai.proxy.server import create_app


@click.command(name="serve")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8910, show_default=True, type=int)
@click.option("--config", "config_path", default="safeai.yaml", show_default=True, help="Config path.")
@click.option(
    "--mode",
    default="sidecar",
    show_default=True,
    type=click.Choice(["sidecar", "gateway"], case_sensitive=False),
    help="Proxy deployment mode.",
)
@click.option(
    "--upstream-base-url",
    default=None,
    help="Optional upstream base URL for /v1/proxy/forward when path-only forwarding is used.",
)
def serve_command(
    host: str,
    port: int,
    config_path: str,
    mode: str,
    upstream_base_url: str | None,
) -> None:
    """Run SafeAI proxy server."""
    app = create_app(config_path=config_path, mode=mode, upstream_base_url=upstream_base_url)
    uvicorn.run(app, host=host, port=port, log_level="info")
