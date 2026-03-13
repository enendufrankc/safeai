# SafeAI v0.8.1 Release Notes

Date: 2026-03-13  
Status: Patch release

## Scope included

1. Bug fixes
- use absolute URL for banner image so it renders on PyPI and GitHub
- add schema examples to auto-config prompt for correct YAML generation

2. Default configurations
- add default configurations for agents, alerts, contracts, and policies

3. Interactive CLI
- Clack-style interactive CLI for `safeai init`

## Validation summary

- `ruff check safeai tests` passed.
- `mypy safeai` passed.
- `pytest` passed (`322` tests).

## Packaging note

- Local wheel/sdist build remains blocked in this environment because `python3 -m build` requires module `build`, which is not installed locally.
- CI release should build artifacts in a controlled environment with build dependencies available.
