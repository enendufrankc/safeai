# Contributing Guide

Thank you for your interest in contributing to SafeAI. This guide explains how to get involved, what we expect from contributions, and how to get your changes merged.

---

## Ways to Contribute

- **Report bugs** -- File an issue with reproduction steps and expected vs. actual behavior.
- **Suggest features** -- Open a feature request issue describing the use case and proposed solution.
- **Improve documentation** -- Fix typos, clarify explanations, add examples, or write new guides.
- **Write code** -- Fix bugs, implement features, add detectors, or build framework adapters.
- **Review pull requests** -- Provide constructive feedback on open PRs.

!!! tip "Start with an issue"
    For anything beyond a small typo fix, please open an issue first. This lets maintainers provide early feedback on direction and scope before you invest significant effort.

---

## Development Standards

All contributions must meet these quality standards:

- **Tests are required.** Every new feature or bug fix must include corresponding tests. Run the full test suite before submitting:

    ```bash
    uv run pytest tests/ -v
    ```

- **Keep changes focused.** Each pull request should address a single concern. Avoid mixing unrelated changes in one PR.

- **Update documentation.** If your change affects user-facing behavior, update the relevant docs pages.

- **Pass CI.** All quality gates must pass: tests, linting, type checks, and coverage thresholds.

    ```bash
    # Run the full quality gate locally
    uv run pytest tests/ -v --tb=short
    uv run ruff check safeai/ tests/
    uv run mypy safeai/
    ```

---

## Commit Sign-Off (DCO)

All commits must be signed off to certify you have the right to submit the contribution under the project's license. Use the `-s` flag:

```bash
git commit -s -m "feat: add phone number detector for UK formats"
```

This adds a `Signed-off-by` line to your commit message, indicating agreement with the [Developer Certificate of Origin](https://developercertificate.org/).

---

## AI-Assisted Contributions

We welcome contributions that use AI coding assistants. If AI tools were used in creating your contribution:

- Disclose AI assistance in the PR description.
- You remain fully responsible for the correctness, security, and quality of the code.
- All contributions, regardless of how they were authored, must meet the same review standards.

---

## Pull Request Requirements

Every pull request must include the following in its description:

1. **Why** -- What problem does this solve? Link to the relevant issue.
2. **What** -- Summary of the changes made.
3. **Security impact** -- Does this change affect boundary enforcement, policy evaluation, secret handling, or audit logging? If yes, describe how.
4. **Verification** -- How was this tested? Include test output or screenshots where applicable.
5. **Compatibility** -- Does this change break any existing APIs, config formats, or CLI flags?

### PR template

```markdown
## Why
<!-- Link to issue and describe the problem -->

## What
<!-- Summarize the changes -->

## Security Impact
<!-- None / Describe impact on enforcement boundaries -->

## Verification
<!-- Test commands, output, or screenshots -->

## Compatibility
<!-- Breaking changes, deprecations, or migration steps -->
```

---

## Security-Related Changes

Changes that touch boundary enforcement, policy evaluation, secret handling, encryption, audit logging, or access control require elevated review:

- **2 maintainer approvals** (instead of the standard 1)
- **1 security owner approval**
- Explicit security impact analysis in the PR description
- Dedicated test coverage for the security-relevant behavior

!!! warning
    Do not include real secrets, API keys, or credentials in test fixtures. Use clearly fake values (e.g., `sk-test-fake-key-000`).

---

## Getting Help

- Open a [GitHub Discussion](https://github.com/enendufrankc/safeai/discussions) for questions.
- Tag `@maintainers` in your issue or PR if you need a review.
- Check the [Onboarding Playbook](onboarding.md) for a structured first-contribution path.
