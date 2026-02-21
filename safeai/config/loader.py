"""YAML config loading helpers."""

from __future__ import annotations

import json
from functools import lru_cache
from glob import glob
from pathlib import Path
from typing import Any, Iterable

import yaml  # type: ignore[import-untyped]
from jsonschema import Draft202012Validator

from safeai.config.models import SafeAIConfig


class PolicySchemaValidationError(ValueError):
    """Raised when a policy file does not match the SafeAI policy schema."""


class MemorySchemaValidationError(ValueError):
    """Raised when a memory schema file does not match SafeAI schema rules."""


class ContractSchemaValidationError(ValueError):
    """Raised when a tool contract file does not match SafeAI schema rules."""


class IdentitySchemaValidationError(ValueError):
    """Raised when an agent identity file does not match SafeAI schema rules."""


def load_yaml_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected object at top-level in {path}")
    return loaded


def load_config(path: str | Path) -> SafeAIConfig:
    path_obj = Path(path).expanduser().resolve()
    data = load_yaml_file(path_obj)
    return SafeAIConfig.model_validate(data)


def resolve_files(config_path: str | Path, patterns: list[str]) -> list[Path]:
    base = Path(config_path).expanduser().resolve().parent
    files: list[Path] = []
    seen: set[Path] = set()

    for pattern in patterns:
        raw = Path(pattern).expanduser()
        full_pattern = str(raw if raw.is_absolute() else base / pattern)
        for match in sorted(glob(full_pattern, recursive=True)):
            file_path = Path(match).resolve()
            if not file_path.is_file() or file_path in seen:
                continue
            seen.add(file_path)
            files.append(file_path)

    return files


def resolve_policy_files(config_path: str | Path, patterns: list[str]) -> list[Path]:
    return resolve_files(config_path, patterns)


def resolve_memory_schema_files(config_path: str | Path, patterns: list[str]) -> list[Path]:
    return resolve_files(config_path, patterns)


def resolve_contract_files(config_path: str | Path, patterns: list[str]) -> list[Path]:
    return resolve_files(config_path, patterns)


def resolve_identity_files(config_path: str | Path, patterns: list[str]) -> list[Path]:
    return resolve_files(config_path, patterns)


def load_policy_documents(
    config_path: str | Path,
    patterns: list[str],
    *,
    version: str = "v1alpha1",
) -> list[dict[str, Any]]:
    _, docs = load_policy_bundle(config_path, patterns, version=version)
    return docs


def load_memory_documents(
    config_path: str | Path,
    patterns: list[str],
    *,
    version: str = "v1alpha1",
) -> list[dict[str, Any]]:
    _, docs = load_memory_bundle(config_path, patterns, version=version)
    return docs


def load_contract_documents(
    config_path: str | Path,
    patterns: list[str],
    *,
    version: str = "v1alpha1",
) -> list[dict[str, Any]]:
    _, docs = load_contract_bundle(config_path, patterns, version=version)
    return docs


def load_identity_documents(
    config_path: str | Path,
    patterns: list[str],
    *,
    version: str = "v1alpha1",
) -> list[dict[str, Any]]:
    _, docs = load_identity_bundle(config_path, patterns, version=version)
    return docs


def load_policy_bundle(
    config_path: str | Path,
    patterns: list[str],
    *,
    version: str = "v1alpha1",
) -> tuple[list[Path], list[dict[str, Any]]]:
    files = resolve_policy_files(config_path, patterns)
    docs: list[dict[str, Any]] = []

    for file_path in files:
        loaded = load_yaml_file(file_path)
        validate_policy_document(loaded, file_path, version=version)
        docs.extend(_extract_policy_documents(loaded))

    return files, docs


def load_memory_bundle(
    config_path: str | Path,
    patterns: list[str],
    *,
    version: str = "v1alpha1",
) -> tuple[list[Path], list[dict[str, Any]]]:
    files = resolve_memory_schema_files(config_path, patterns)
    docs: list[dict[str, Any]] = []

    for file_path in files:
        loaded = load_yaml_file(file_path)
        validate_memory_document(loaded, file_path, version=version)
        docs.extend(_extract_memory_documents(loaded))

    return files, docs


def load_contract_bundle(
    config_path: str | Path,
    patterns: list[str],
    *,
    version: str = "v1alpha1",
) -> tuple[list[Path], list[dict[str, Any]]]:
    files = resolve_contract_files(config_path, patterns)
    docs: list[dict[str, Any]] = []

    for file_path in files:
        loaded = load_yaml_file(file_path)
        validate_contract_document(loaded, file_path, version=version)
        docs.extend(_extract_contract_documents(loaded))

    return files, docs


def load_identity_bundle(
    config_path: str | Path,
    patterns: list[str],
    *,
    version: str = "v1alpha1",
) -> tuple[list[Path], list[dict[str, Any]]]:
    files = resolve_identity_files(config_path, patterns)
    docs: list[dict[str, Any]] = []

    for file_path in files:
        loaded = load_yaml_file(file_path)
        validate_identity_document(loaded, file_path, version=version)
        docs.extend(_extract_identity_documents(loaded))

    return files, docs


def validate_policy_document(document: dict[str, Any], source: Path, *, version: str = "v1alpha1") -> None:
    validator = _schema_validator("policy", version)
    _raise_on_schema_errors(
        validator=validator,
        document=document,
        source=source,
        error_type=PolicySchemaValidationError,
        label="Policy schema validation",
    )


def validate_memory_document(document: dict[str, Any], source: Path, *, version: str = "v1alpha1") -> None:
    validator = _schema_validator("memory", version)
    _raise_on_schema_errors(
        validator=validator,
        document=document,
        source=source,
        error_type=MemorySchemaValidationError,
        label="Memory schema validation",
    )


def validate_contract_document(document: dict[str, Any], source: Path, *, version: str = "v1alpha1") -> None:
    validator = _schema_validator("tool-contract", version)
    _raise_on_schema_errors(
        validator=validator,
        document=document,
        source=source,
        error_type=ContractSchemaValidationError,
        label="Tool contract schema validation",
    )


def validate_identity_document(document: dict[str, Any], source: Path, *, version: str = "v1alpha1") -> None:
    validator = _schema_validator("agent-identity", version)
    _raise_on_schema_errors(
        validator=validator,
        document=document,
        source=source,
        error_type=IdentitySchemaValidationError,
        label="Agent identity schema validation",
    )


def _raise_on_schema_errors(
    *,
    validator: Draft202012Validator,
    document: dict[str, Any],
    source: Path,
    error_type: type[ValueError],
    label: str,
) -> None:
    errors = sorted(
        validator.iter_errors(document),
        key=lambda err: (_format_json_path(err.absolute_path), err.message),
    )
    if not errors:
        return

    first = errors[0]
    location = _format_json_path(first.absolute_path)
    extra = f" ({len(errors) - 1} additional error(s))" if len(errors) > 1 else ""
    raise error_type(f"{label} failed for {source}: {location}: {first.message}{extra}")


def _extract_policy_documents(document: dict[str, Any]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    policy = document.get("policy")
    if isinstance(policy, dict):
        docs.append(policy)

    policies = document.get("policies", [])
    if isinstance(policies, list):
        docs.extend(item for item in policies if isinstance(item, dict))

    return docs


def _extract_memory_documents(document: dict[str, Any]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    memory = document.get("memory")
    if isinstance(memory, dict):
        docs.append({"version": document.get("version", "v1alpha1"), "memory": memory})

    memories = document.get("memories", [])
    if isinstance(memories, list) and memories:
        docs.append({"version": document.get("version", "v1alpha1"), "memories": memories})

    return docs


def _extract_contract_documents(document: dict[str, Any]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    contract = document.get("contract")
    if isinstance(contract, dict):
        docs.append({"version": document.get("version", "v1alpha1"), "contract": contract})

    contracts = document.get("contracts", [])
    if isinstance(contracts, list) and contracts:
        docs.append({"version": document.get("version", "v1alpha1"), "contracts": contracts})

    return docs


def _extract_identity_documents(document: dict[str, Any]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    agent = document.get("agent")
    if isinstance(agent, dict):
        docs.append({"version": document.get("version", "v1alpha1"), "agent": agent})

    agents = document.get("agents", [])
    if isinstance(agents, list) and agents:
        docs.append({"version": document.get("version", "v1alpha1"), "agents": agents})

    return docs


def _format_json_path(path_parts: Iterable[Any]) -> str:
    location = "$"
    for part in path_parts:
        if isinstance(part, int):
            location += f"[{part}]"
        else:
            location += f".{part}"
    return location


@lru_cache(maxsize=16)
def _schema_validator(schema_name: str, version: str) -> Draft202012Validator:
    schema_path = _schema_path(schema_name, version)
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found for '{schema_name}' version '{version}': {schema_path}")

    with schema_path.open("r", encoding="utf-8") as fh:
        schema = json.load(fh)

    return Draft202012Validator(schema)


def _schema_path(schema_name: str, version: str) -> Path:
    module_path = Path(__file__).resolve()
    filename = f"{schema_name}.schema.json"
    project_schema = module_path.parents[2] / "schemas" / version / filename
    package_schema = module_path.parents[1] / "schemas" / version / filename

    if project_schema.exists():
        return project_schema
    if package_schema.exists():
        return package_schema
    return project_schema
