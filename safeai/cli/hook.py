"""Universal hook adapter — reads JSON from stdin, enforces SafeAI boundaries."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

import click

from safeai.agents.profiles import AgentProfile, get_profile, resolve_tool_category
from safeai.api import SafeAI
from safeai.core.policy import PolicyContext

# ---------------------------------------------------------------------------
# Dangerous command patterns
# ---------------------------------------------------------------------------

_DANGEROUS_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"rm\s+-[^\s]*r[^\s]*f[^\s]*\s+[/~.](?:\s|$)"), "recursive delete of root/home/cwd"),
    (re.compile(r"rm\s+-[^\s]*f[^\s]*r[^\s]*\s+[/~.](?:\s|$)"), "recursive delete of root/home/cwd"),
    (re.compile(r"\bDROP\s+(TABLE|DATABASE)\b", re.IGNORECASE), "DROP TABLE/DATABASE"),
    (re.compile(r"\bTRUNCATE\b", re.IGNORECASE), "TRUNCATE"),
    (re.compile(r"\bmkfs\b"), "mkfs (format filesystem)"),
    (re.compile(r"\bdd\s+if="), "dd (raw disk write)"),
    (re.compile(r">\s*/dev/sd[a-z]"), "write to raw disk device"),
    (re.compile(r"chmod\s+(-R\s+)?777\b"), "chmod 777"),
    (re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"), "fork bomb"),
    (
        re.compile(r"git\s+push\s+--force\b.*\b(main|master)\b"),
        "force push to main/master",
    ),
    (
        re.compile(r"git\s+push\b.*\b(main|master)\b.*--force\b"),
        "force push to main/master",
    ),
    (re.compile(r"curl\s+.*\|\s*(sh|bash)\b"), "pipe-to-shell (curl)"),
    (re.compile(r"wget\s+.*\|\s*(sh|bash)\b"), "pipe-to-shell (wget)"),
]

SHELL_CATEGORIES = {"shell", "Bash", "run_command"}


def _classify_dangerous_command(text: str) -> str | None:
    """Return a reason string if *text* matches a known dangerous pattern."""
    for pattern, reason in _DANGEROUS_PATTERNS:
        if pattern.search(text):
            return reason
    return None


def _extract_text(
    tool_name: str,
    tool_input: dict[str, Any] | str | None,
    profile: AgentProfile | None,
) -> str:
    """Extract scannable text from tool input."""
    if isinstance(tool_input, str):
        return tool_input
    if not isinstance(tool_input, dict):
        return ""

    category = resolve_tool_category(tool_name, profile)

    # Shell commands
    if category in SHELL_CATEGORIES or tool_name in SHELL_CATEGORIES:
        return tool_input.get("command", tool_input.get("cmd", ""))

    # File operations — scan the content/text being written
    if category in {"file_write", "file_edit"}:
        return tool_input.get("content", tool_input.get("new_string", tool_input.get("text", "")))

    # Search — scan the pattern/query
    if category == "search":
        return tool_input.get("pattern", tool_input.get("query", ""))

    # Web — scan the URL
    if category == "web":
        return tool_input.get("url", tool_input.get("query", ""))

    # Fallback: concatenate all string values
    parts = [str(v) for v in tool_input.values() if isinstance(v, str)]
    return " ".join(parts)


def _run_pre_tool(
    safeai: SafeAI,
    tool_name: str,
    tool_input: dict[str, Any] | str | None,
    agent_id: str,
    session_id: str | None,
    profile: AgentProfile | None,
) -> None:
    """Enforce pre-tool-use boundary. Calls sys.exit on block."""
    text = _extract_text(tool_name, tool_input, profile)

    # 1. Scan input for secrets/PII
    scan = safeai.scan_input(text, agent_id=agent_id)
    if scan.decision.action == "block":
        click.echo(f"BLOCKED: {scan.decision.reason}")
        sys.exit(1)

    data_tags: list[str] = list(getattr(scan, "tags", []) or [])

    # 2. Classify dangerous commands for shell tools
    category = resolve_tool_category(tool_name, profile)
    if category in SHELL_CATEGORIES or tool_name in SHELL_CATEGORIES:
        danger_reason = _classify_dangerous_command(text)
        if danger_reason:
            data_tags.append("dangerous.command")

    # 3. Evaluate action boundary policies directly (no contract required)
    if data_tags:
        decision = safeai.policy_engine.evaluate(
            PolicyContext(
                boundary="action",
                data_tags=data_tags,
                agent_id=agent_id,
                tool_name=category,
            )
        )
        if decision.action == "block":
            click.echo(f"BLOCKED: {decision.reason}")
            sys.exit(1)


def _run_post_tool(
    safeai: SafeAI,
    tool_name: str,
    tool_output: str | None,
    agent_id: str,
    _session_id: str | None,
    _profile: AgentProfile | None,
) -> None:
    """Enforce post-tool-use boundary. Calls sys.exit on block."""
    if not tool_output:
        return

    result = safeai.guard_output(str(tool_output), agent_id=agent_id)
    if result.decision.action == "block":
        click.echo(f"BLOCKED: {result.decision.reason}")
        sys.exit(1)


@click.command("hook")
@click.option("--config", default="safeai.yaml", help="Path to safeai.yaml config file.")
@click.option(
    "--event",
    type=click.Choice(["pre_tool_use", "post_tool_use"]),
    default=None,
    help="Hook event type (overrides stdin JSON field).",
)
@click.option("--agent-id", default=None, help="Agent identifier (overrides stdin JSON field).")
@click.option("--profile", default=None, help="Agent profile name for tool-name mapping.")
def hook_command(config: str, event: str | None, agent_id: str | None, profile: str | None) -> None:
    """Universal hook adapter — enforce SafeAI boundaries for any coding agent."""
    # Read JSON envelope from stdin
    try:
        raw = sys.stdin.read()
        envelope = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        click.echo(f"ERROR: Invalid JSON on stdin: {exc}", err=True)
        sys.exit(2)

    # Resolve fields (CLI flags take precedence over stdin)
    event = event or envelope.get("event")
    if not event:
        click.echo("ERROR: No event specified (use --event or include 'event' in stdin JSON).", err=True)
        sys.exit(2)

    agent_id = agent_id or envelope.get("agent_id", "agent")
    session_id: str | None = envelope.get("session_id")
    tool_name: str = envelope.get("tool_name", "unknown")
    tool_input = envelope.get("tool_input")
    tool_output = envelope.get("tool_output")

    # Resolve profile
    resolved_profile: AgentProfile | None = None
    if profile:
        resolved_profile = get_profile(profile)

    # Load SafeAI
    try:
        safeai = SafeAI.from_config(config)
    except Exception as exc:
        click.echo(f"ERROR: Failed to load SafeAI config: {exc}", err=True)
        sys.exit(2)

    # Dispatch
    if event == "pre_tool_use":
        _run_pre_tool(safeai, tool_name, tool_input, agent_id, session_id, resolved_profile)
    elif event == "post_tool_use":
        _run_post_tool(safeai, tool_name, tool_output, agent_id, session_id, resolved_profile)
    else:
        click.echo(f"ERROR: Unknown event '{event}'.", err=True)
        sys.exit(2)

    # If we reach here, the tool call is allowed
    sys.exit(0)
