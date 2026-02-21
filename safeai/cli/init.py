"""safeai init command."""

from __future__ import annotations

import shutil
from pathlib import Path

import click
import yaml

DEFAULT_FILES = {
    Path("safeai.yaml"): Path("config/defaults/safeai.yaml"),
    Path("policies/default.yaml"): Path("config/defaults/policies/default.yaml"),
    Path("contracts/example.yaml"): Path("config/defaults/contracts/example.yaml"),
    Path("schemas/memory.yaml"): Path("config/defaults/schemas/memory.yaml"),
    Path("agents/default.yaml"): Path("config/defaults/agents/default.yaml"),
    Path("plugins/example.py"): Path("config/defaults/plugins/example.py"),
    Path("tenants/policy-sets.yaml"): Path("config/defaults/tenants/policy-sets.yaml"),
    Path("alerts/default.yaml"): Path("config/defaults/alerts/default.yaml"),
}

PROVIDERS = {
    "Ollama (local, free — no API key needed)": {
        "provider": "ollama",
        "model": "llama3.2",
        "base_url": "http://localhost:11434",
        "api_key_env": None,
    },
    "OpenAI": {
        "provider": "openai-compatible",
        "model": "gpt-4o",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
    },
    "Anthropic": {
        "provider": "openai-compatible",
        "model": "claude-sonnet-4-20250514",
        "base_url": "https://api.anthropic.com/v1",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
    "Google Gemini": {
        "provider": "openai-compatible",
        "model": "gemini-2.0-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "api_key_env": "GOOGLE_API_KEY",
    },
    "Mistral": {
        "provider": "openai-compatible",
        "model": "mistral-large-latest",
        "base_url": "https://api.mistral.ai/v1",
        "api_key_env": "MISTRAL_API_KEY",
    },
    "Groq": {
        "provider": "openai-compatible",
        "model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
    },
    "Azure OpenAI": {
        "provider": "openai-compatible",
        "model": "gpt-4o",
        "base_url": None,
        "api_key_env": "AZURE_OPENAI_API_KEY",
    },
    "Cohere": {
        "provider": "openai-compatible",
        "model": "command-r-plus",
        "base_url": "https://api.cohere.com/v1",
        "api_key_env": "COHERE_API_KEY",
    },
    "Together AI": {
        "provider": "openai-compatible",
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "base_url": "https://api.together.xyz/v1",
        "api_key_env": "TOGETHER_API_KEY",
    },
    "Fireworks AI": {
        "provider": "openai-compatible",
        "model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "api_key_env": "FIREWORKS_API_KEY",
    },
    "DeepSeek": {
        "provider": "openai-compatible",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "Other (any OpenAI-compatible endpoint)": {
        "provider": "openai-compatible",
        "model": None,
        "base_url": None,
        "api_key_env": None,
    },
}


def _prompt_intelligence_config() -> dict | None:
    """Interactive prompt to configure the intelligence layer."""
    click.echo()
    click.secho("Intelligence Layer Setup", bold=True)
    click.echo("SafeAI can use an AI backend to auto-generate policies,")
    click.echo("explain incidents, and recommend improvements.")
    click.echo()

    enable = click.confirm("Enable the intelligence layer?", default=True)
    if not enable:
        return None

    click.echo()
    click.secho("Choose your AI backend:", bold=True)
    provider_names = list(PROVIDERS.keys())
    for i, name in enumerate(provider_names, 1):
        click.echo(f"  {i}. {name}")
    click.echo()

    choice = click.prompt(
        "Select provider",
        type=click.IntRange(1, len(provider_names)),
        default=1,
    )
    selected = PROVIDERS[provider_names[choice - 1]]

    provider = selected["provider"]
    model = selected["model"]
    base_url = selected["base_url"]
    api_key_env = selected["api_key_env"]

    # For "Other", prompt for details
    if model is None:
        model = click.prompt("Model name", type=str)
    if base_url is None:
        base_url = click.prompt("Base URL", type=str)

    # Allow overriding defaults
    click.echo()
    if click.confirm("Customize model and URL?", default=False):
        model = click.prompt("Model", default=model, type=str)
        base_url = click.prompt("Base URL", default=base_url, type=str)

    # API key env var
    if provider == "openai-compatible" and api_key_env is None:
        api_key_env = click.prompt(
            "Environment variable for API key (or 'none')",
            default="none",
            type=str,
        )
        if api_key_env.lower() == "none":
            api_key_env = None

    config = {
        "enabled": True,
        "backend": {
            "provider": provider,
            "model": model,
            "base_url": base_url,
        },
        "metadata_only": True,
    }
    if api_key_env:
        config["backend"]["api_key_env"] = api_key_env

    return config


@click.command(name="init")
@click.option("--path", "target_path", default=".", show_default=True, help="Project directory.")
@click.option("--non-interactive", is_flag=True, help="Skip interactive prompts.")
def init_command(target_path: str, non_interactive: bool) -> None:
    """Scaffold default SafeAI config files and configure intelligence."""
    base = Path(target_path).expanduser().resolve()
    package_root = Path(__file__).resolve().parents[1]

    created: list[Path] = []
    skipped: list[Path] = []

    for rel_target, rel_source in DEFAULT_FILES.items():
        source = package_root / rel_source
        target = base / rel_target
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            skipped.append(target)
            continue
        shutil.copyfile(source, target)
        created.append(target)

    click.echo("SafeAI initialized")
    for path in created:
        click.echo(f"  created: {path}")
    for path in skipped:
        click.echo(f"  skipped: {path} (already exists)")

    # Interactive intelligence setup
    if not non_interactive:
        intel_config = _prompt_intelligence_config()
        if intel_config:
            safeai_yaml = base / "safeai.yaml"
            with open(safeai_yaml) as f:
                config = yaml.safe_load(f) or {}
            config["intelligence"] = intel_config
            with open(safeai_yaml, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            click.echo()
            click.secho("Intelligence layer configured!", fg="green", bold=True)
            click.echo(f"  provider: {intel_config['backend']['provider']}")
            click.echo(f"  model:    {intel_config['backend']['model']}")
            click.echo()
            click.echo("Next steps:")
            click.echo("  safeai intelligence auto-config --path . --apply")
            click.echo("  safeai serve --mode sidecar --port 8000")
        else:
            click.echo()
            click.echo("Intelligence layer skipped. You can enable it later in safeai.yaml.")
