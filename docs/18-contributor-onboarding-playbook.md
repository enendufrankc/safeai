# External Contributor Onboarding Playbook

## Purpose

This playbook defines how external contributors can safely and effectively contribute to SafeAI ecosystem features (plugins, adapters, policy templates, and scanning extensions).

## 1. First-day setup

1. Fork and clone the repository.
2. Install development dependencies:

```bash
python3 -m pip install -e ".[dev]"
```

3. Scaffold a local config and defaults:

```bash
safeai init
```

4. Verify local quality gates:

```bash
ruff check safeai tests
mypy safeai
python3 -m unittest discover -s tests -v
```

## 2. Contribution lanes

Choose one lane and keep the PR scoped:

1. Plugin contributions
- Add plugin implementation under `plugins/` (or in your own package) and include `safeai_detectors`, `safeai_adapters`, or `safeai_policy_templates`.
- Add tests validating plugin loading and behavior.

2. Framework adapter contributions
- Add adapter implementation under `safeai/middleware/`.
- Ensure request/response interception parity with existing adapters.
- Add adapter tests in `tests/test_<adapter>_adapter.py`.

3. Policy template contributions
- Add new template files in `safeai/config/defaults/policies/templates/`.
- Include at least one real-world scenario and one safety rationale in comments/docs.

4. Scanning extension contributions
- Extend structured/file scanning without weakening default deny behavior.
- Add regression tests for false negatives and policy action correctness.

## 3. Mandatory PR checklist

- [ ] Includes tests for changed behavior.
- [ ] Updates docs and changelog where applicable.
- [ ] Preserves fail-closed behavior for security controls.
- [ ] Avoids logging raw secrets or sensitive payload values.
- [ ] Follows semver compatibility and migration expectations.

## 4. Plugin author contract

Supported plugin exports:

1. `safeai_detectors() -> list[tuple[name, tag, regex]]`
2. `safeai_adapters() -> dict[str, adapter_factory_or_class]`
3. `safeai_policy_templates() -> dict[str, policy_template_document]`

Guidelines:
- Keep detector tags scoped and specific (for example `personal.financial.account`).
- Avoid broad regexes that create excessive false positives.
- Adapter factories must return instances bound to the provided SafeAI runtime.

## 5. Security review expectations

Changes touching these areas require stricter review:

1. `safeai/core/interceptor.py`
2. `safeai/core/policy.py`
3. `safeai/core/memory.py`
4. `safeai/secrets/*`
5. `safeai/dashboard/*`
6. `safeai/plugins/*`

For these changes:
- Include threat considerations in PR description.
- Add explicit negative tests (blocked/denied paths).
- Document audit evidence emitted by the change.

## 6. Release and compatibility discipline

- Backward-incompatible API changes require migration notes in `CHANGELOG.md`.
- New template packs and plugin capabilities should be additive by default.
- Keep public APIs stable unless a major version change is planned.

## 7. Maintainer interaction model

- Use issues first for large or ambiguous scope.
- Expect review feedback focused on security regressions, not just style.
- Split large changes into phases to shorten review and reduce risk.

## 8. Fast path for first external contribution

Recommended first PR:

1. Add one small policy template pack.
2. Add one focused test file.
3. Update this playbook with lessons learned.
