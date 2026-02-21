---
description: "Install SafeAI with pip or uv — includes optional extras for vault, AWS, MCP, and documentation tooling."
---

# Installation

SafeAI installs as a standard Python package with optional extras for vault integration, AWS services, and MCP server support. The core package has minimal dependencies and works out of the box for most use cases.

## Requirements

- **Python >= 3.10**
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

!!! tip "Why uv?"
    [uv](https://docs.astral.sh/uv/) is a fast Python package manager written in Rust. It's 10-100x faster than pip, handles virtual environments automatically, and is the tool used in SafeAI's CI pipeline. We recommend it for all SafeAI workflows.

    Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Basic Install

=== "uv (recommended)"

    ```bash
    uv pip install safeai
    ```

=== "pip"

    ```bash
    pip install safeai
    ```

This installs the core framework with secret scanning, PII redaction, policy enforcement, tool control, and action approval.

## Optional Extras

SafeAI provides optional dependency groups for extended functionality:

| Extra   | Description                                                  |
|---------|--------------------------------------------------------------|
| `vault` | HashiCorp Vault integration for secret rotation and storage  |
| `aws`   | AWS Secrets Manager and KMS support                          |
| `mcp`   | Model Context Protocol server for tool-level guardrails      |
| `all`   | All optional dependencies bundled together                   |
| `docs`  | MkDocs Material documentation tooling                        |

=== "uv (recommended)"

    ```bash
    uv pip install "safeai[vault]"
    uv pip install "safeai[aws]"
    uv pip install "safeai[mcp]"
    uv pip install "safeai[all]"
    ```

=== "pip"

    ```bash
    pip install safeai[vault]
    pip install safeai[aws]
    pip install safeai[mcp]
    pip install safeai[all]
    ```

!!! tip "Choosing extras"
    If you are unsure which extras you need, start with the base install. You can always add extras later without reinstalling the core package.

## Development Install

To contribute or run tests locally, clone the repository and install with development dependencies:

=== "uv (recommended)"

    ```bash
    git clone https://github.com/enendufrankc/safeai.git
    cd safeai
    uv sync --extra dev --extra all
    ```

=== "pip"

    ```bash
    git clone https://github.com/enendufrankc/safeai.git
    cd safeai
    pip install -e ".[dev,all]"
    ```

This includes linting, testing, and documentation tooling on top of the full runtime dependencies.

## Verify Installation

Run the following command to confirm SafeAI is installed and importable:

```bash
python -c "from safeai import SafeAI; print('OK')"
```

You should see:

```
OK
```

!!! warning "Import errors"
    If you see a `ModuleNotFoundError`, make sure you are using the correct Python environment. With uv, dependencies are managed automatically. With pip, use a virtual environment (`python -m venv .venv`) to avoid conflicts.

## Next Steps

Once installed, head to the [Quickstart](quickstart.md) guide to run your first scan in two lines of code.
