# Installation

SafeAI installs as a standard Python package with optional extras for vault integration, AWS services, and MCP server support. The core package has minimal dependencies and works out of the box for most use cases.

## Requirements

- **Python >= 3.10**
- pip (or any PEP 517-compatible installer)

## Basic Install

```bash
pip install safeai
```

This installs the core framework with secret scanning, PII redaction, policy enforcement, tool control, and action approval.

## Optional Extras

SafeAI provides optional dependency groups for extended functionality:

| Extra   | Install Command              | Description                                                  |
|---------|------------------------------|--------------------------------------------------------------|
| `vault` | `pip install safeai[vault]`  | HashiCorp Vault integration for secret rotation and storage  |
| `aws`   | `pip install safeai[aws]`    | AWS Secrets Manager and KMS support                          |
| `mcp`   | `pip install safeai[mcp]`    | Model Context Protocol server for tool-level guardrails      |
| `all`   | `pip install safeai[all]`    | All optional dependencies bundled together                   |

!!! tip "Choosing extras"
    If you are unsure which extras you need, start with the base install. You can always add extras later without reinstalling the core package.

## Development Install

To contribute or run tests locally, clone the repository and install in editable mode with development dependencies:

```bash
git clone https://github.com/frankcamacho/SafeAI.git
cd SafeAI
pip install -e ".[dev]"
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
    If you see a `ModuleNotFoundError`, make sure you are using the same Python environment where you ran `pip install`. Virtual environments (`venv`, `conda`) are strongly recommended to avoid conflicts.

## Next Steps

Once installed, head to the [Quickstart](quickstart.md) guide to run your first scan in two lines of code.
