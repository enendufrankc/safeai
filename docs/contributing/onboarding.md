# Onboarding Playbook

This playbook gets you from zero to your first merged contribution. Follow it step by step.

---

## First-Day Setup

### 1. Fork and clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/<your-username>/safeai.git
cd safeai
git remote add upstream https://github.com/enendufrankc/safeai.git
```

### 2. Install development dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,all]"
```

### 3. Scaffold the configuration

```bash
safeai init
```

### 4. Run quality gates

```bash
# Tests
pytest tests/ -v --tb=short

# Linting
ruff check safeai/ tests/

# Type checking
mypy safeai/

# Validate config
safeai validate
```

All four must pass before you submit any PR.

---

## Contribution Lanes

Choose the lane that matches your interest and skill level.

### Plugins

Build custom detectors, adapters, or policy templates as plugins.

- **Entry point group:** `safeai_detectors`, `safeai_adapters`, `safeai_policy_templates`
- **Starter file:** `.safeai/plugins/example.py` (created by `safeai init`)
- **Guide:** [Plugins integration guide](../integrations/plugins.md)

### Framework Adapters

Add SafeAI support for a new AI framework (e.g., LlamaIndex, Haystack).

- **Base class:** `safeai.middleware.base.BaseMiddleware`
- **Examples:** `safeai/middleware/langchain.py`, `safeai/middleware/crewai.py`
- **Requirements:** Implement `intercept_request` and `intercept_response` methods.

### Policy Templates

Create reusable policy packs for specific industries or use cases.

- **Location:** `safeai/config/defaults/policies/templates/`
- **Format:** YAML files following the policy schema
- **Built-in examples:** `finance`, `healthcare`, `support`

### Scanning Extensions

Add new detection capabilities (e.g., new PII types, custom patterns).

- **Base class:** `safeai.detectors.base.BaseDetector`
- **Examples:** `safeai/detectors/email.py`, `safeai/detectors/phone.py`
- **Registration:** Add to detector registry in `safeai/detectors/__init__.py`

---

## Mandatory PR Checklist

Before opening a pull request, verify all of the following:

- [ ] Tests pass: `pytest tests/ -v`
- [ ] Linting passes: `ruff check safeai/ tests/`
- [ ] Type checks pass: `mypy safeai/`
- [ ] Config validates: `safeai validate`
- [ ] Commit is signed off: `git commit -s -m "..."`
- [ ] PR description includes Why, What, Security Impact, Verification, Compatibility
- [ ] Documentation updated if user-facing behavior changed
- [ ] No real secrets or credentials in code or test fixtures

---

## Plugin Author Contract

If you are publishing a plugin package, follow these conventions:

| Entry Point Group | Purpose | Example |
|---|---|---|
| `safeai_detectors` | Custom detection patterns | `my_plugin:PhoneDetectorUK` |
| `safeai_adapters` | Framework middleware | `my_plugin:HaystackAdapter` |
| `safeai_policy_templates` | Reusable policy packs | `my_plugin:legal_template` |

Register entry points in your package's `pyproject.toml`:

```toml
[project.entry-points.safeai_detectors]
phone_uk = "my_plugin.detectors:PhoneDetectorUK"

[project.entry-points.safeai_adapters]
haystack = "my_plugin.adapters:HaystackAdapter"
```

---

## Security Review Expectations

If your contribution touches any of the following areas, it will undergo elevated security review:

- Boundary enforcement logic (`core/interceptor.py`, `core/guard.py`)
- Policy evaluation (`core/policy.py`)
- Secret handling (`secrets/`)
- Encryption or memory security (`core/memory.py`)
- Audit logging (`core/audit.py`)
- Access control or identity (`core/identity.py`, `secrets/capability.py`)

Expect:

- 2 maintainer approvals + 1 security owner approval
- Longer review timelines (up to 5 business days)
- Requests for additional test coverage or threat analysis

---

## Release and Compatibility Discipline

- SafeAI follows [semantic versioning](../project/compatibility.md) (pre-1.0: `0.y.z`).
- Do not introduce breaking changes without a deprecation cycle.
- New CLI flags, config keys, and API methods must be additive (backward-compatible).
- If a breaking change is unavoidable, document it in the PR and update the [Changelog](../changelog.md).

---

## Fast Path for First Contribution

Looking for a quick win? Try one of these:

1. **Fix a typo** in the docs or code comments.
2. **Add a test** for an untested edge case.
3. **Improve an error message** to be more actionable.
4. **Add a notebook example** demonstrating an existing feature.

Look for issues labeled `good first issue` on the [issue tracker](https://github.com/enendufrankc/safeai/issues?q=label%3A%22good+first+issue%22).

!!! success "You are ready"
    Once your first PR is merged, you are officially a SafeAI contributor. Welcome to the project.
