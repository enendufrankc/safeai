#!/usr/bin/env python3
"""
SafeAI automated deployment script.

Deploys SafeAI as a zero-trust security layer into a target project:
  1. Verifies/installs safeai-sdk
  2. Runs `safeai init` to scaffold config
  3. Runs `safeai intelligence auto-config --apply` to generate policies
  4. Applies agent bindings (MCP server config or native hooks)
  5. Optionally starts the local observability server (dashboard + metrics + audit API)

Usage:
    python deploy_safeai.py --project-path /path/to/project [options]

Options:
    --project-path PATH     Target project directory (default: cwd)
    --agent TYPE            Agent type: claude-code | cursor | generic (default: auto-detect)
    --binding TYPE          Binding mode: mcp | hooks (default: auto-detect)
    --no-intelligence       Skip intelligence auto-config phase
    --provider PROVIDER     LLM provider for intelligence: openai | anthropic | ollama
    --model MODEL           LLM model for intelligence (provider-dependent)
    --api-key-env VAR       Env var name holding the LLM API key
    --mcp-host-config PATH  Path to MCP host config file to update
    --observability         Start the local observability server after deployment
    --obs-port PORT         Port for the observability server (default: 8910)
    --obs-host HOST         Host for the observability server (default: 127.0.0.1)
    --slack-webhook URL     Slack webhook URL for alerts
    --webhook-url URL       Generic webhook URL for alerts
    --dry-run               Print commands without executing them
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd: list[str], cwd: Path = None, dry_run: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    cwd_str = str(cwd) if cwd else None
    print(f"  $ {' '.join(cmd)}" + (f"  [cwd={cwd_str}]" if cwd_str else ""))
    if dry_run:
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    result = subprocess.run(cmd, cwd=cwd_str, capture_output=False, text=True)
    if check and result.returncode != 0:
        print(f"\n[ERROR] Command failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)
    return result


def step(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def info(msg: str):
    print(f"  [+] {msg}")


def warn(msg: str):
    print(f"  [!] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Phase 1: Verify / install safeai-sdk
# ---------------------------------------------------------------------------

def ensure_safeai(dry_run: bool):
    step("Phase 1: Verify SafeAI installation")
    if shutil.which("safeai"):
        result = subprocess.run(["safeai", "--version"], capture_output=True, text=True)
        info(f"safeai found: {result.stdout.strip() or 'unknown version'}")
        return

    warn("safeai CLI not found — installing safeai-sdk[mcp] ...")
    installer = "uv" if shutil.which("uv") else "pip"
    if installer == "uv":
        run(["uv", "pip", "install", "safeai-sdk[mcp]"], dry_run=dry_run)
    else:
        run([sys.executable, "-m", "pip", "install", "safeai-sdk[mcp]"], dry_run=dry_run)
    info("safeai-sdk installed.")


# ---------------------------------------------------------------------------
# Phase 2: safeai init
# ---------------------------------------------------------------------------

def run_safeai_init(project_path: Path, dry_run: bool):
    step("Phase 2: Initialize SafeAI (safeai init)")

    config_file = project_path / "safeai.yaml"
    if config_file.exists():
        info("safeai.yaml already exists — skipping init.")
        return

    # safeai init is interactive; use --non-interactive if available, otherwise pipe defaults
    result = run(
        ["safeai", "init"],
        cwd=project_path,
        dry_run=dry_run,
        check=False,
    )
    if result.returncode != 0:
        warn("safeai init exited non-zero — config may be incomplete.")
    else:
        info("SafeAI initialized successfully.")


# ---------------------------------------------------------------------------
# Phase 3: Configure intelligence backend
# ---------------------------------------------------------------------------

def configure_intelligence(
    project_path: Path,
    provider: str,
    model: str,
    api_key_env: str,
    dry_run: bool,
):
    step("Phase 3a: Configure intelligence backend")

    config_file = project_path / "safeai.yaml"
    if not config_file.exists():
        warn("safeai.yaml not found — cannot configure intelligence.")
        return

    import re

    content = config_file.read_text()

    # Default models per provider
    default_models = {
        "openai": "gpt-4o",
        "anthropic": "claude-opus-4-6",
        "ollama": "llama3",
    }
    resolved_model = model or default_models.get(provider, "gpt-4o")
    default_key_envs = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "ollama": "OLLAMA_API_KEY",
    }
    resolved_key_env = api_key_env or default_key_envs.get(provider, "OPENAI_API_KEY")

    intelligence_block = f"""
intelligence:
  enabled: true
  provider: {provider}
  model: {resolved_model}
  base_url: {"http://localhost:11434" if provider == "ollama" else "null"}
  api_key_env: {resolved_key_env}
  metadata_only: true
"""

    if "intelligence:" in content:
        info("intelligence section already present in safeai.yaml — skipping.")
    else:
        if not dry_run:
            with open(config_file, "a") as f:
                f.write(intelligence_block)
        info(f"Added intelligence backend: provider={provider}, model={resolved_model}")

    # Validate the API key env var is set
    if not dry_run and not os.environ.get(resolved_key_env):
        warn(
            f"Environment variable {resolved_key_env} is not set. "
            "Intelligence auto-config will fail without it. "
            f"Export it before running: export {resolved_key_env}=<your-key>"
        )


# ---------------------------------------------------------------------------
# Phase 4: Intelligence auto-config
# ---------------------------------------------------------------------------

def run_intelligence_autoconfig(project_path: Path, dry_run: bool):
    step("Phase 3b: Intelligence auto-config (safeai intelligence auto-config --apply)")

    run(
        ["safeai", "intelligence", "auto-config", "--path", ".", "--apply"],
        cwd=project_path,
        dry_run=dry_run,
        check=False,
    )
    info("Intelligence auto-config complete. Generated artifacts applied to project root.")


# ---------------------------------------------------------------------------
# Phase 5: Agent detection
# ---------------------------------------------------------------------------

def detect_agent(project_path: Path) -> str:
    """Auto-detect the most likely agent from project structure."""
    if (project_path / ".claude").is_dir() or shutil.which("claude"):
        return "claude-code"
    if (project_path / ".cursor").is_dir():
        return "cursor"
    return "generic"


def detect_binding(agent: str) -> str:
    """Choose default binding mode for agent."""
    # Claude Code supports both; prefer hooks for tight integration
    return "hooks"


# ---------------------------------------------------------------------------
# Phase 6: Apply agent bindings
# ---------------------------------------------------------------------------

def apply_mcp_binding(project_path: Path, mcp_host_config: Path | None, dry_run: bool):
    step("Phase 4: Apply MCP server binding")

    config_path = project_path / "safeai.yaml"
    info(f"MCP server configured for: {config_path}")

    # Write a convenience launch script
    launch_script = project_path / "start-safeai-mcp.sh"
    if not dry_run:
        launch_script.write_text(
            f"#!/bin/sh\nsafeai mcp --config {config_path}\n"
        )
        launch_script.chmod(0o755)
    info(f"Created MCP launch script: {launch_script}")

    # Optionally patch MCP host config
    if mcp_host_config:
        _patch_mcp_host_config(mcp_host_config, config_path, dry_run)
    else:
        # Auto-detect Claude Desktop config
        claude_desktop_configs = _find_claude_desktop_config()
        if claude_desktop_configs:
            for cfg in claude_desktop_configs:
                _patch_mcp_host_config(cfg, config_path, dry_run)
        else:
            info(
                "No MCP host config found to patch automatically.\n"
                "  Add the following to your MCP host config manually:\n"
                f"""
  {{
    "mcpServers": {{
      "safeai": {{
        "command": "safeai",
        "args": ["mcp", "--config", "{config_path}"]
      }}
    }}
  }}
"""
            )


def _find_claude_desktop_config() -> list[Path]:
    """Look for Claude Desktop config files in standard locations."""
    candidates = []
    system = platform.system()
    if system == "Darwin":
        base = Path.home() / "Library" / "Application Support" / "Claude"
        candidates.append(base / "claude_desktop_config.json")
    elif system == "Linux":
        base = Path.home() / ".config" / "claude"
        candidates.append(base / "claude_desktop_config.json")
    elif system == "Windows":
        base = Path(os.environ.get("APPDATA", "")) / "Claude"
        candidates.append(base / "claude_desktop_config.json")
    return [p for p in candidates if p.exists()]


def _patch_mcp_host_config(config_file: Path, safeai_config: Path, dry_run: bool):
    info(f"Patching MCP host config: {config_file}")
    if dry_run:
        return
    try:
        data = json.loads(config_file.read_text()) if config_file.exists() else {}
        data.setdefault("mcpServers", {})
        data["mcpServers"]["safeai"] = {
            "command": "safeai",
            "args": ["mcp", "--config", str(safeai_config)],
        }
        config_file.write_text(json.dumps(data, indent=2))
        info(f"  MCP host config updated: {config_file}")
    except Exception as e:
        warn(f"  Failed to patch {config_file}: {e}")


def apply_hooks_binding(project_path: Path, agent: str, dry_run: bool):
    step(f"Phase 4: Apply native agent hooks (agent={agent})")

    config_arg = str(project_path / "safeai.yaml")

    if agent == "claude-code":
        run(
            ["safeai", "setup", "claude-code", "--config", config_arg, "--path", "."],
            cwd=project_path,
            dry_run=dry_run,
            check=False,
        )
        info("Claude Code hooks installed at .claude/settings.json")

    elif agent == "cursor":
        run(
            ["safeai", "setup", "cursor", "--config", config_arg, "--path", "."],
            cwd=project_path,
            dry_run=dry_run,
            check=False,
        )
        info("Cursor rules installed at .cursor/rules")

    else:
        # Generic: print instructions
        run(
            ["safeai", "setup", "generic", "--config", config_arg],
            cwd=project_path,
            dry_run=dry_run,
            check=False,
        )
        info(
            "Generic hook instructions printed above.\n"
            "  Pipe tool call JSON to: safeai hook --config safeai.yaml"
        )


# ---------------------------------------------------------------------------
# Phase 6: Observability server
# ---------------------------------------------------------------------------

def configure_observability(
    project_path: Path,
    obs_host: str,
    obs_port: int,
    slack_webhook: str | None,
    webhook_url: str | None,
    dry_run: bool,
):
    step("Phase 5: Configure observability")

    config_file = project_path / "safeai.yaml"
    if not config_file.exists():
        warn("safeai.yaml not found — cannot configure observability.")
        return

    content = config_file.read_text()

    # Build dashboard block
    dashboard_block = """
dashboard:
  enabled: true
  rbac_enabled: false
  users:
    - user_id: admin
      role: admin
      tenants: ["*"]
"""

    # Build alerting block
    channels_lines = "    default_channels: [file]\n"
    if slack_webhook:
        channels_lines += f"    slack_webhook_url: {slack_webhook}\n"
        channels_lines = "    default_channels: [file, slack]\n" + channels_lines
    if webhook_url:
        channels_lines += f"    webhook_url: {webhook_url}\n"

    alerting_block = f"""
alerting:
  enabled: true
  cooldown_seconds: 60
  channels:
{channels_lines}"""

    if not dry_run:
        with open(config_file, "a") as f:
            if "dashboard:" not in content:
                f.write(dashboard_block)
            if "alerting:" not in content:
                f.write(alerting_block)

    info(f"Observability dashboard configured at http://{obs_host}:{obs_port}/dashboard")
    info(f"Prometheus metrics at http://{obs_host}:{obs_port}/v1/metrics")
    info(f"Health check at http://{obs_host}:{obs_port}/v1/health")
    info(f"Audit query API at http://{obs_host}:{obs_port}/v1/audit/query")


def start_observability_server(
    project_path: Path,
    obs_host: str,
    obs_port: int,
    dry_run: bool,
):
    step(f"Starting observability server on http://{obs_host}:{obs_port}")

    config_arg = str(project_path / "safeai.yaml")

    # Write a start script for future use
    start_script = project_path / "start-safeai-obs.sh"
    if not dry_run:
        start_script.write_text(
            f"#!/bin/sh\n"
            f"safeai serve --host {obs_host} --port {obs_port} --config {config_arg}\n"
        )
        start_script.chmod(0o755)
    info(f"Created observability start script: {start_script}")

    info("Starting server in background (logs to logs/safeai-serve.log) ...")
    if not dry_run:
        log_file = open(project_path / "logs" / "safeai-serve.log", "a")
        subprocess.Popen(
            ["safeai", "serve", "--host", obs_host, "--port", str(obs_port), "--config", config_arg],
            cwd=str(project_path),
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
        )
        import time
        time.sleep(2)  # give it a moment to bind

    info(f"Observability server started:")
    info(f"  Dashboard:       http://{obs_host}:{obs_port}/dashboard")
    info(f"  Prometheus:      http://{obs_host}:{obs_port}/v1/metrics")
    info(f"  Health:          http://{obs_host}:{obs_port}/v1/health")
    info(f"  Audit query:     http://{obs_host}:{obs_port}/v1/audit/query  (POST)")
    info(f"  Agent activity:  http://{obs_host}:{obs_port}/v1/dashboard/observe/agents")
    info(f"  Intelligence:    http://{obs_host}:{obs_port}/v1/intelligence/status")


# ---------------------------------------------------------------------------
# Phase 7: Validate and smoke test
# ---------------------------------------------------------------------------

def validate_and_test(project_path: Path, dry_run: bool):
    step("Phase 5: Validate deployment")

    run(
        ["safeai", "validate"],
        cwd=project_path,
        dry_run=dry_run,
        check=False,
    )

    run(
        ["safeai", "scan", "Hello, my SSN is 123-45-6789"],
        cwd=project_path,
        dry_run=dry_run,
        check=False,
    )
    info("Validation complete. Check output above for any errors.")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(project_path: Path, agent: str, binding: str, obs_host: str, obs_port: int, obs_running: bool):
    step("Deployment Summary")
    obs_lines = (
        f"\n  Observability:  http://{obs_host}:{obs_port}/dashboard\n"
        f"  Prometheus:     http://{obs_host}:{obs_port}/v1/metrics\n"
        f"  Audit API:      http://{obs_host}:{obs_port}/v1/audit/query\n"
        f"  Server log:     {project_path}/logs/safeai-serve.log"
        if obs_running else
        f"\n  Tip: Re-run with --observability to start the local monitoring dashboard."
    )
    print(f"""
  Project:        {project_path}
  Agent:          {agent}
  Binding mode:   {binding}

  Config:         {project_path}/safeai.yaml
  Policies:       {project_path}/policies/
  Contracts:      {project_path}/contracts/
  Audit log:      {project_path}/logs/audit.log
{obs_lines}

  Next steps:
    - Review generated policies in policies/
    - Review generated contracts in contracts/
    - Run: safeai logs --last 20            (watch enforcement)
    - Run: safeai observe agents --last 1h  (agent activity)
    - Run: safeai intelligence recommend    (ongoing policy tuning)
""")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Deploy SafeAI as a zero-trust security layer into a project."
    )
    parser.add_argument(
        "--project-path", default=".", help="Target project directory (default: cwd)"
    )
    parser.add_argument(
        "--agent",
        choices=["claude-code", "cursor", "generic"],
        default=None,
        help="Agent type (default: auto-detect)",
    )
    parser.add_argument(
        "--binding",
        choices=["mcp", "hooks"],
        default=None,
        help="Binding mode: mcp | hooks (default: auto-detect)",
    )
    parser.add_argument(
        "--no-intelligence",
        action="store_true",
        help="Skip intelligence auto-config phase",
    )
    parser.add_argument(
        "--provider",
        default="openai",
        choices=["openai", "anthropic", "ollama"],
        help="LLM provider for intelligence (default: openai)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="LLM model for intelligence (default: provider-specific)",
    )
    parser.add_argument(
        "--api-key-env",
        default=None,
        help="Env var name holding the LLM API key (default: provider-specific)",
    )
    parser.add_argument(
        "--mcp-host-config",
        default=None,
        help="Path to MCP host config JSON to patch (e.g. claude_desktop_config.json)",
    )
    parser.add_argument(
        "--observability",
        action="store_true",
        help="Start local observability server (dashboard + metrics + audit API)",
    )
    parser.add_argument(
        "--obs-port",
        type=int,
        default=8910,
        help="Port for the observability server (default: 8910)",
    )
    parser.add_argument(
        "--obs-host",
        default="127.0.0.1",
        help="Host for the observability server (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--slack-webhook",
        default=None,
        help="Slack incoming webhook URL for alerts",
    )
    parser.add_argument(
        "--webhook-url",
        default=None,
        help="Generic webhook URL for alerts",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them",
    )

    args = parser.parse_args()

    project_path = Path(args.project_path).resolve()
    if not project_path.is_dir():
        print(f"[ERROR] Project path does not exist: {project_path}", file=sys.stderr)
        sys.exit(1)

    mcp_host_config = Path(args.mcp_host_config).resolve() if args.mcp_host_config else None

    # Auto-detect agent and binding if not specified
    agent = args.agent or detect_agent(project_path)
    binding = args.binding or detect_binding(agent)

    print(f"\nSafeAI Deploy")
    print(f"  project:  {project_path}")
    print(f"  agent:    {agent}")
    print(f"  binding:  {binding}")
    print(f"  dry-run:  {args.dry_run}")

    # Execute phases
    ensure_safeai(args.dry_run)
    run_safeai_init(project_path, args.dry_run)

    if not args.no_intelligence:
        configure_intelligence(
            project_path,
            provider=args.provider,
            model=args.model,
            api_key_env=args.api_key_env,
            dry_run=args.dry_run,
        )
        run_intelligence_autoconfig(project_path, args.dry_run)

    if binding == "mcp":
        apply_mcp_binding(project_path, mcp_host_config, args.dry_run)
    else:
        apply_hooks_binding(project_path, agent, args.dry_run)

    if args.observability:
        configure_observability(
            project_path,
            obs_host=args.obs_host,
            obs_port=args.obs_port,
            slack_webhook=args.slack_webhook,
            webhook_url=args.webhook_url,
            dry_run=args.dry_run,
        )
        start_observability_server(project_path, args.obs_host, args.obs_port, args.dry_run)

    validate_and_test(project_path, args.dry_run)
    print_summary(project_path, agent, binding, args.obs_host, args.obs_port, args.observability)


if __name__ == "__main__":
    main()
