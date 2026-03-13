# SafeAI v0.8.0 Release Notes

Date: 2026-02-20  
Status: Phase 8 release gate passed

## Scope included

1. Alerting system
- alert push evaluation and alert channels (file, webhook, Slack)
- `safeai alerts` CLI commands

2. Observability
- agent timeline and session trace
- `safeai observe` CLI

3. Template marketplace
- community index with search, install, and uninstall
- SHA-256 verification for downloaded templates

4. Agent profiles
- coding agent policy enforcement via agent profiles

5. PyPI publishing
- published to PyPI as `safeai-sdk`

6. CI security workflows
- CodeQL, dependency-review, secret-scan, vulnerability-scan, and governance-gate workflows
- docs deployment workflow
- `.gitleaks.toml` configuration

## Validation summary

- `ruff check safeai tests` passed.
- `mypy safeai` passed.
- `pytest` passed (`322` tests).

## Packaging note

- Local wheel/sdist build remains blocked in this environment because `python3 -m build` requires module `build`, which is not installed locally.
- CI release should build artifacts in a controlled environment with build dependencies available.
