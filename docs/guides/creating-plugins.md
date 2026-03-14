# Creating SafeAI Plugins

Plugins let you extend SafeAI with custom detectors, adapters, and policy
templates—without forking the core project. This guide walks through every
plugin type, from a three-line detector to a full adapter, and explains how to
test, configure, and publish your work.

---

## What Is a SafeAI Plugin?

A SafeAI plugin is a Python file (or package) that provides one or more of the
following extensions:

| Extension type | Purpose |
|----------------|---------|
| **Detector** | Regex-based pattern that flags secrets, PII, or unsafe content |
| **Adapter** | Middleware that hooks into an LLM framework (LangChain, CrewAI, …) |
| **Template** | Reusable policy YAML that can be applied to any project |

Plugins are loaded at startup via the `plugins` section of `safeai.yaml`.

---

## Minimal Plugin — Custom Detector

The fastest way to add a detector is a single file with a `PATTERNS` list:

```python
# my_detector.py
PATTERNS = [
    ("MyInternalToken", "secret", r"MYCO-[A-Z0-9]{32}"),
]
```

Each tuple is `(name, tag, regex_pattern)`. SafeAI's scanner picks up every
entry in `PATTERNS` and includes it in structured scans automatically.

---

## Plugin File Structure

A plugin can be a **single `.py` file** or a **Python package** (directory with
`__init__.py`). Recommended layout for a package:

```
safeai-plugin-acme/
├── acme_plugin/
│   ├── __init__.py        # exports PATTERNS, adapters, templates
│   ├── detectors.py       # custom PATTERNS list
│   ├── adapters.py        # custom adapter classes
│   └── templates/
│       └── acme-policy.yaml
├── tests/
│   └── test_detectors.py
├── pyproject.toml
└── README.md
```

**Naming convention:** prefix your package with `safeai-plugin-` on PyPI so the
community can discover it easily.

---

## Custom Detector Plugins

### Pattern Tuples

Define a module-level `PATTERNS` list. Each entry is a 3-tuple:

```python
PATTERNS = [
    # (name, tag, regex)
    ("AcmeAPIKey",    "secret",  r"acme_key_[a-f0-9]{40}"),
    ("AcmeClientID",  "secret",  r"acme_client_[A-Z0-9]{16}"),
    ("InternalEmail", "pii",     r"[a-zA-Z0-9_.+-]+@acme\.internal"),
]
```

* **name** – human-readable identifier shown in scan results.
* **tag** – category used by the policy engine (`secret`, `pii`, `unsafe`, or
  any custom tag your policies reference).
* **regex** – a Python `re`-compatible regular expression. Patterns are compiled
  with `re.MULTILINE`.

### Priority & Ordering

Patterns are evaluated in definition order. Place high-confidence patterns
first so they match before broader fallback rules.

### Multi-File Detectors

You can split patterns across files. Export them from `__init__.py`:

```python
# acme_plugin/__init__.py
from acme_plugin.detectors import PATTERNS  # noqa: F401
```

---

## Custom Adapter Plugins

Adapters wrap LLM framework clients to intercept calls and enforce policies.

### Adapter Interface

Create a class that exposes a `wrap(client)` method:

```python
from __future__ import annotations
from typing import Any


class AcmeAdapter:
    """Adapter that hooks into Acme's LLM client."""

    def __init__(self, policy_engine: Any) -> None:
        self.policy_engine = policy_engine

    def wrap(self, client: Any) -> Any:
        original_call = client.call

        def guarded_call(*args: Any, **kwargs: Any) -> Any:
            prompt = kwargs.get("prompt", args[0] if args else "")
            decision = self.policy_engine.evaluate(prompt)
            if decision.blocked:
                raise RuntimeError(f"Blocked by SafeAI: {decision.reason}")
            return original_call(*args, **kwargs)

        client.call = guarded_call
        return client
```

Key points:

* The adapter receives the **policy engine** at construction time.
* `wrap()` monkey-patches or decorates the client so every call passes through
  SafeAI's policy evaluation.
* Return the (possibly wrapped) client so callers can use it transparently.

### Registering Adapters

Export an `ADAPTERS` dict from your plugin module:

```python
ADAPTERS = {
    "acme": AcmeAdapter,
}
```

SafeAI discovers adapters via this mapping when the plugin is loaded.

---

## Custom Template Plugins

Templates are YAML files that define reusable policy configurations.

### Template Format

```yaml
# templates/acme-strict.yaml
name: acme-strict
description: Strict policy for Acme Corp projects
version: "1.0"

rules:
  - id: no-internal-secrets
    detector: AcmeAPIKey
    action: block
    message: "Acme API keys must not appear in prompts."

  - id: pii-redact
    detector: InternalEmail
    action: redact
    message: "Internal email addresses are automatically redacted."
```

### Registering Templates

Export a `TEMPLATES` list pointing to YAML paths relative to your plugin:

```python
from pathlib import Path

TEMPLATES = [
    Path(__file__).parent / "templates" / "acme-strict.yaml",
]
```

---

## Configuring Plugins in `safeai.yaml`

Add a `plugins` section to your project's `safeai.yaml`:

```yaml
plugins:
  enabled: true
  plugin_files:
    - ./my_detector.py
    - ./acme_plugin
    - safeai-plugin-acme        # installed via pip
```

* **`enabled`** – master switch; set to `false` to disable all plugins without
  removing configuration.
* **`plugin_files`** – list of paths (relative to the project root) or
  installed package names. SafeAI resolves each entry at startup.

### Load Order

Plugins are loaded in the order listed. If two plugins define a pattern with
the same name, the **last one wins**.

---

## Testing Plugins

### Testing Detector Patterns

Use plain `re` to validate your patterns independently:

```python
import re
from acme_plugin.detectors import PATTERNS


def test_acme_api_key_matches():
    _, _, pattern = PATTERNS[0]
    assert re.search(pattern, "token: acme_key_" + "a1b2c3d4" * 5)


def test_acme_api_key_no_false_positive():
    _, _, pattern = PATTERNS[0]
    assert re.search(pattern, "this is just normal text") is None
```

### Integration Test with SafeAI Scanner

```python
from safeai.scanning import scan_text

# Assumes your plugin is configured in safeai.yaml
results = scan_text("Here is my key: acme_key_" + "a" * 40)
assert any(r.name == "AcmeAPIKey" for r in results)
```

### Running Tests

```bash
# From your plugin directory
python -m pytest tests/ -v
```

---

## Publishing Plugins

### Option 1: Skills Registry

Add your plugin to the SafeAI skills registry so it can be installed with
`safeai skills install`:

```json
{
  "name": "safeai-plugin-acme",
  "version": "1.0.0",
  "description": "Acme Corp detectors and policies",
  "entry": "acme_plugin",
  "author": "your-github-handle"
}
```

Submit a pull request to the
[SafeAI skills registry](https://github.com/your-org/safeai/skills-registry.json)
to list your plugin.

### Option 2: PyPI

Package your plugin as a standard Python project and publish to PyPI:

```bash
pip install build twine
python -m build
twine upload dist/*
```

Users install with:

```bash
pip install safeai-plugin-acme
```

Then reference the installed package name in `safeai.yaml`:

```yaml
plugins:
  enabled: true
  plugin_files:
    - safeai-plugin-acme
```

---

## Quick Reference

| What you want | Export from your plugin |
|---------------|----------------------|
| Custom detectors | `PATTERNS = [(name, tag, regex), ...]` |
| Custom adapters | `ADAPTERS = {"name": AdapterClass, ...}` |
| Custom templates | `TEMPLATES = [Path(...), ...]` |

Happy building! If you run into issues, open a discussion in the SafeAI
repository or check the [troubleshooting guide](troubleshooting.md).
