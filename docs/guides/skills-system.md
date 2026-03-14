# Skills System

SafeAI ships a **skills system** that lets you install pre-built security packages into your project. Each skill is a self-contained bundle of detectors, policies, and configurations targeting a specific compliance domain or security concern.

!!! tip "Quick start"
    ```bash
    python -m safeai.cli.main skills search gdpr --project-path .
    python -m safeai.cli.main skills add gdpr-compliance --project-path .
    ```

## Overview

Skills are modular security packages that extend SafeAI with domain-specific protections. Instead of writing custom detectors and policies from scratch, you can install a skill that bundles everything needed for a compliance standard or threat category.

Each skill includes:

- **Detectors** — pattern-matching rules for the target domain
- **Policies** — pre-configured YAML rules with appropriate actions
- **Configuration** — default settings tuned for the use case

Skills are distributed through the **SafeAI Skills Registry** and managed via the CLI.

## Available Skills

SafeAI provides 8 pre-built security skill packages:

| Skill | Description | Domain |
|:------|:-----------|:-------|
| `gdpr-compliance` | GDPR data protection rules — PII detection, consent checks, data residency | Privacy / Compliance |
| `hipaa-compliance` | HIPAA health data safeguards — PHI detection, access controls, audit rules | Healthcare |
| `pci-dss` | PCI-DSS payment card protections — card number detection, encryption rules | Finance |
| `prompt-injection-shield` | Prompt injection and jailbreak defense — instruction override, DAN, extraction | AI Security |
| `secret-scanner` | Enhanced secret detection — API keys, tokens, credentials across 30+ providers | Secret Management |
| `toxicity-filter` | Toxicity and hate speech detection — profanity, threats, harassment, slurs | Content Safety |
| `topic-restriction` | Topic boundary enforcement — legal, medical, weapons, drugs, gambling | Content Policy |
| `dangerous-command-blocker` | Dangerous command detection — filesystem, container escape, cloud exfil, supply chain | Infrastructure Safety |

## Listing Installed Skills

View what skills are currently installed in your project:

```bash
python -m safeai.cli.main skills list --project-path /path/to/project
```

This reads the project's `skills-lock.json` and displays installed skills with their versions and status.

!!! info "Lock file"
    The `skills-lock.json` file in your project root tracks which skills are installed and their exact versions. This file should be committed to version control to ensure reproducible environments.

## Searching for Skills

Search the skills registry by keyword:

```bash
# Search for secret-related skills
python -m safeai.cli.main skills search secret --project-path /path/to/project

# Search for compliance skills
python -m safeai.cli.main skills search gdpr --project-path /path/to/project

# Search by category
python -m safeai.cli.main skills search compliance --project-path /path/to/project
```

The search command queries the [skills registry](https://github.com/enendufrankc/safeai) and returns matching skills with descriptions and metadata.

## Installing Skills

Install a skill from the registry:

```bash
# Install a single skill
python -m safeai.cli.main skills add prompt-injection-shield --project-path /path/to/project

# Verify installation
python -m safeai.cli.main skills list --project-path /path/to/project
```

When you install a skill, SafeAI:

1. Downloads the skill package from the registry
2. Copies detectors, policies, and configs into your project's `skills/` directory
3. Updates `skills-lock.json` with the installed version
4. Makes the skill's detectors available to the scanner immediately

!!! warning "Network required"
    Installing skills from the registry requires network access. The CLI fetches packages from GitHub-hosted repositories.

### Installing Multiple Skills

```bash
python -m safeai.cli.main skills add gdpr-compliance --project-path .
python -m safeai.cli.main skills add hipaa-compliance --project-path .
python -m safeai.cli.main skills add pci-dss --project-path .
```

## Removing Skills

Remove an installed skill:

```bash
python -m safeai.cli.main skills remove prompt-injection-shield --project-path /path/to/project

# Verify removal
python -m safeai.cli.main skills list --project-path /path/to/project
```

Removing a skill:

1. Deletes the skill's files from the `skills/` directory
2. Updates `skills-lock.json` to reflect the removal
3. Does **not** remove any custom policies you created on top of the skill

## Skills Registry

The skills registry (`skills-registry.json`) is the central catalog of available skills. It contains metadata for each skill:

```json title="skills-registry.json"
{
  "skills": [
    {
      "name": "prompt-injection-shield",
      "version": "0.8.1",
      "description": "Prompt injection and jailbreak defense",
      "category": "ai-security",
      "source": "github:enendufrankc/safeai-skills/prompt-injection-shield"
    }
  ]
}
```

### Registry Fields

| Field | Description |
|:------|:-----------|
| `name` | Unique skill identifier used in CLI commands |
| `version` | Semantic version of the skill package |
| `description` | Human-readable description |
| `category` | Classification (compliance, ai-security, content-safety, etc.) |
| `source` | GitHub repository path for the skill files |

## Creating Custom Skills

You can create your own skills by following the standard skill package structure:

```text
my-custom-skill/
├── detectors/
│   └── custom_detector.py
├── policies/
│   └── custom_policy.yaml
├── config/
│   └── defaults.yaml
└── skill.yaml
```

### Skill Manifest

Every skill needs a `skill.yaml` manifest:

```yaml title="skill.yaml"
name: my-custom-skill
version: 1.0.0
description: Custom security skill for my organization
category: custom
author: your-org

detectors:
  - detectors/custom_detector.py

policies:
  - policies/custom_policy.yaml

config:
  - config/defaults.yaml
```

### Publishing to the Registry

To share your skill:

1. Host the skill package in a GitHub repository
2. Submit a pull request to the SafeAI skills registry
3. Once merged, the skill becomes available via `safeai skills search` and `safeai skills add`

!!! tip "Local development"
    During development, you can test skills locally by copying the skill directory into your project's `skills/` folder without going through the registry.

## See Also

- [Content Moderation](content-moderation.md) — built-in detectors that skills extend
- [Policy Engine](policy-engine.md) — how skill policies integrate with your rules
- [Plugins](../integrations/plugins.md) — the plugin system that skills build on
- [CLI Reference](../cli/index.md) — full `skills` command documentation
