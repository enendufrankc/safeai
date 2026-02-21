"""CLI commands for the SafeAI intelligence layer."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import click


def _build_backend_from_config(cfg):
    """Build an AIBackend from IntelligenceConfig."""
    from safeai.intelligence.backend import OllamaBackend, OpenAICompatibleBackend

    bcfg = cfg.intelligence.backend
    provider = bcfg.provider.lower()

    if provider == "ollama":
        return OllamaBackend(model=bcfg.model, base_url=bcfg.base_url)

    # openai, openai-compatible, anthropic, azure, etc.
    api_key = ""
    if bcfg.api_key_env:
        api_key = os.environ.get(bcfg.api_key_env, "")
    return OpenAICompatibleBackend(
        model=bcfg.model,
        api_key=api_key,
        base_url=bcfg.base_url,
    )


def _load_config_and_backend(config_path: str | None):
    """Load SafeAI config and build an AI backend."""
    from safeai.config.loader import load_config

    cfg_path = config_path or "safeai.yaml"
    cfg = load_config(cfg_path)

    if not cfg.intelligence.enabled:
        raise click.ClickException(
            "Intelligence layer is disabled. "
            "Set 'intelligence.enabled: true' in safeai.yaml."
        )

    backend = _build_backend_from_config(cfg)
    return cfg, backend


def _write_artifacts(artifacts: dict[str, str], output_dir: str, apply: bool) -> None:
    """Write artifacts to output directory and optionally apply."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for filename, content in artifacts.items():
        dest = out / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        click.echo(f"  wrote {dest}")

    if apply:
        for filename, content in artifacts.items():
            target = Path(".") / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(out / filename), str(target))
            click.echo(f"  applied {target}")


@click.group("intelligence")
def intelligence_group() -> None:
    """AI advisory commands for configuration and understanding."""


@intelligence_group.command("auto-config")
@click.option("--path", default=".", help="Project path to analyze.")
@click.option("--framework", default=None, help="Framework hint (e.g., langchain, crewai).")
@click.option("--output-dir", default=".safeai-generated", help="Directory for generated files.")
@click.option("--apply", is_flag=True, help="Copy generated files to project root.")
@click.option("--config", "config_path", default=None, help="Path to safeai.yaml.")
def auto_config_command(
    path: str,
    framework: str | None,
    output_dir: str,
    apply: bool,
    config_path: str | None,
) -> None:
    """Generate SafeAI configuration from project structure."""
    from safeai.intelligence.auto_config import AutoConfigAdvisor
    from safeai.intelligence.sanitizer import MetadataSanitizer

    cfg, backend = _load_config_and_backend(config_path)
    sanitizer = MetadataSanitizer(metadata_only=cfg.intelligence.metadata_only)
    advisor = AutoConfigAdvisor(backend=backend, sanitizer=sanitizer)
    result = advisor.advise(project_path=path, framework_hint=framework)

    if result.status != "success":
        raise click.ClickException(result.summary)

    click.echo(f"[auto-config] {result.summary}")
    _write_artifacts(result.artifacts, output_dir, apply)


@intelligence_group.command("recommend")
@click.option("--since", default="7d", help="Time window for audit analysis.")
@click.option("--output-dir", default=".safeai-generated", help="Directory for generated files.")
@click.option("--config", "config_path", default=None, help="Path to safeai.yaml.")
def recommend_command(since: str, output_dir: str, config_path: str | None) -> None:
    """Suggest policy improvements from audit data."""
    from safeai.intelligence.recommender import RecommenderAdvisor
    from safeai.intelligence.sanitizer import MetadataSanitizer

    cfg, backend = _load_config_and_backend(config_path)
    sanitizer = MetadataSanitizer(metadata_only=cfg.intelligence.metadata_only)
    advisor = RecommenderAdvisor(backend=backend, sanitizer=sanitizer)
    result = advisor.advise(since=since, config_path=config_path or "safeai.yaml")

    if result.status != "success":
        raise click.ClickException(result.summary)

    click.echo(f"[recommend] {result.summary}")
    _write_artifacts(result.artifacts, output_dir, apply=False)


@intelligence_group.command("explain")
@click.argument("event_id")
@click.option("--config", "config_path", default=None, help="Path to safeai.yaml.")
def explain_command(event_id: str, config_path: str | None) -> None:
    """Classify and explain a security incident."""
    from safeai.intelligence.incident import IncidentAdvisor
    from safeai.intelligence.sanitizer import MetadataSanitizer

    cfg, backend = _load_config_and_backend(config_path)
    sanitizer = MetadataSanitizer(metadata_only=cfg.intelligence.metadata_only)
    advisor = IncidentAdvisor(backend=backend, sanitizer=sanitizer)
    result = advisor.advise(event_id=event_id, config_path=config_path or "safeai.yaml")

    if result.status != "success":
        raise click.ClickException(result.summary)

    click.echo(f"[explain] {result.summary}")
    if result.raw_response:
        click.echo(result.raw_response)


@intelligence_group.command("compliance")
@click.option(
    "--framework",
    required=True,
    type=click.Choice(["hipaa", "pci-dss", "soc2", "gdpr"], case_sensitive=False),
    help="Compliance framework.",
)
@click.option("--output-dir", default=".safeai-generated", help="Directory for generated files.")
@click.option("--config", "config_path", default=None, help="Path to safeai.yaml.")
def compliance_command(framework: str, output_dir: str, config_path: str | None) -> None:
    """Generate compliance policy sets."""
    from safeai.intelligence.compliance import ComplianceAdvisor
    from safeai.intelligence.sanitizer import MetadataSanitizer

    cfg, backend = _load_config_and_backend(config_path)
    sanitizer = MetadataSanitizer(metadata_only=cfg.intelligence.metadata_only)
    advisor = ComplianceAdvisor(backend=backend, sanitizer=sanitizer)
    result = advisor.advise(framework=framework, config_path=config_path or "safeai.yaml")

    if result.status != "success":
        raise click.ClickException(result.summary)

    click.echo(f"[compliance] {result.summary}")
    _write_artifacts(result.artifacts, output_dir, apply=False)


@intelligence_group.command("integrate")
@click.option("--target", required=True, help="Target framework (e.g., langchain, crewai).")
@click.option("--path", default=".", help="Project path.")
@click.option("--output-dir", default=".safeai-generated", help="Directory for generated files.")
@click.option("--config", "config_path", default=None, help="Path to safeai.yaml.")
def integrate_command(
    target: str,
    path: str,
    output_dir: str,
    config_path: str | None,
) -> None:
    """Generate integration code for a target framework."""
    from safeai.intelligence.integration import IntegrationAdvisor
    from safeai.intelligence.sanitizer import MetadataSanitizer

    cfg, backend = _load_config_and_backend(config_path)
    sanitizer = MetadataSanitizer(metadata_only=cfg.intelligence.metadata_only)
    advisor = IntegrationAdvisor(backend=backend, sanitizer=sanitizer)
    result = advisor.advise(target=target, project_path=path)

    if result.status != "success":
        raise click.ClickException(result.summary)

    click.echo(f"[integrate] {result.summary}")
    _write_artifacts(result.artifacts, output_dir, apply=False)
