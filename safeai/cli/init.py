"""safeai init command."""

from __future__ import annotations

import shutil
from importlib.metadata import version as pkg_version
from pathlib import Path

import click
import yaml

from safeai.cli import ui

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


def _get_version() -> str:
    """Return the installed safeai-sdk version, or 'dev'."""
    try:
        return pkg_version("safeai-sdk")
    except Exception:
        return "dev"


def _scaffold_files(
    base: Path, package_root: Path
) -> tuple[list[Path], list[Path]]:
    """Copy default config files into the project directory."""
    created: list[Path] = []
    skipped: list[Path] = []
    for rel_target, rel_source in DEFAULT_FILES.items():
        source = package_root / rel_source
        target = base / rel_target
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            skipped.append(rel_target)
            continue
        shutil.copyfile(source, target)
        created.append(rel_target)
    return created, skipped


def _write_intelligence_config(base: Path, intel_config: dict) -> None:
    """Merge intelligence config into safeai.yaml."""
    safeai_yaml = base / "safeai.yaml"
    with open(safeai_yaml) as f:
        config = yaml.safe_load(f) or {}
    config["intelligence"] = intel_config
    with open(safeai_yaml, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def _prompt_intelligence_config() -> dict | None:
    """Interactive prompt to configure the intelligence layer."""
    ui.bar()
    ui.step_active("Intelligence Layer Setup")
    ui.bar("SafeAI can use an AI backend to auto-generate policies,")
    ui.bar("explain incidents, and recommend improvements.")
    ui.bar()

    enable = ui.confirm("Enable the intelligence layer?", default=True)
    if not enable:
        ui.step_done("Intelligence layer", "skipped")
        return None

    ui.bar()
    ui.step_active("Choose your AI provider")

    provider_names = list(PROVIDERS.keys())
    chosen_name = ui.select("Provider", choices=provider_names, default=provider_names[0])
    selected = PROVIDERS[chosen_name]

    provider = selected["provider"]
    model = selected["model"]
    base_url = selected["base_url"]
    api_key_env = selected["api_key_env"]

    # For "Other", prompt for details
    if model is None:
        model = ui.text_input("Model name")
    if base_url is None:
        base_url = ui.text_input("Base URL")

    # Allow overriding defaults
    if ui.confirm("Customize model and URL?", default=False):
        model = ui.text_input("Model", default=model or "")
        base_url = ui.text_input("Base URL", default=base_url or "")

    # API key env var
    if provider == "openai-compatible" and api_key_env is None:
        api_key_env = ui.text_input("Environment variable for API key (or 'none')", default="none")
        if api_key_env.lower() == "none":
            api_key_env = None

    ui.bar()
    ui.step_done("Provider", chosen_name)
    ui.step_done("Model", model or "")
    if api_key_env:
        ui.step_done("API key env", api_key_env)

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
    version = _get_version()

    # ── Banner ──────────────────────────────────────────────────────
    ui.banner(version)
    ui.step_done("Project path", str(base))
    ui.bar()

    # ── Scaffold files ──────────────────────────────────────────────
    ui.step_active("Scaffolding config files...")
    created, skipped = _scaffold_files(base, package_root)

    for path in created:
        ui.file_result("created", str(path))
    for path in skipped:
        ui.file_result("skipped", str(path))
    if not skipped:
        ui.file_result("skipped", "(none)")

    # ── Intelligence setup ──────────────────────────────────────────
    intel_config = None
    if not non_interactive:
        intel_config = _prompt_intelligence_config()

    if intel_config:
        _write_intelligence_config(base, intel_config)

        # Summary box
        rows = [
            ("provider", intel_config["backend"]["provider"]),
            ("model", intel_config["backend"]["model"] or ""),
        ]
        if "api_key_env" in intel_config["backend"]:
            rows.append(("api_key", intel_config["backend"]["api_key_env"]))
        ui.summary_box("Configuration Summary", rows)
    else:
        ui.bar()
        if not non_interactive:
            ui.bar("Intelligence layer skipped. Enable it later in safeai.yaml.", style="dim")
        ui.bar()

    # ── Next steps ──────────────────────────────────────────────────
    ui.next_steps(
        [
            "safeai intelligence auto-config --path . --apply",
            "safeai serve --mode sidecar --port 8910",
        ]
    )

    ui.step_end("Done. Happy guarding!")
