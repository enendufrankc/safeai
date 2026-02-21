"""safeai scan command."""

from __future__ import annotations

import click

from safeai.api import SafeAI


@click.command(name="scan")
@click.option("--config", "config_path", default="safeai.yaml", show_default=True, help="Config path.")
@click.option("--input", "input_text", required=True, help="Text to scan.")
@click.option(
    "--boundary",
    type=click.Choice(["input", "output"], case_sensitive=False),
    default="input",
    show_default=True,
)
def scan_command(config_path: str, input_text: str, boundary: str) -> None:
    """Scan sample text through input or output boundary policy."""
    safeai = SafeAI.from_config(config_path)

    if boundary == "input":
        scan_result = safeai.scan_input(input_text)
        filtered = scan_result.filtered
        decision = scan_result.decision
        detections = scan_result.detections
        fallback_used = False
    else:
        guard_result = safeai.guard_output(input_text)
        filtered = guard_result.safe_output
        decision = guard_result.decision
        detections = guard_result.detections
        fallback_used = guard_result.fallback_used

    click.echo(f"Decision: {decision.action}")
    click.echo(f"Policy: {decision.policy_name or 'default deny'}")
    click.echo(f"Reason: {decision.reason}")
    if boundary == "output":
        click.echo(f"Fallback used: {fallback_used}")
    click.echo(f"Detections: {len(detections)}")
    for idx, item in enumerate(detections, start=1):
        click.echo(f"  [{idx}] {item.detector} tag={item.tag} span={item.start}-{item.end}")
    click.echo("Result:")
    click.echo(filtered)
