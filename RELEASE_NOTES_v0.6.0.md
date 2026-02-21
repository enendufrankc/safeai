# SafeAI v0.6.0 Release Notes

Date: 2026-02-20  
Status: Phase 6 release gate passed

## Scope included

1. Plugin system
- dynamic plugin loading for custom detectors, adapters, and policy templates
- plugin discovery from configured glob patterns in `safeai.yaml`
- plugin scaffold added to `safeai init` output (`plugins/example.py`)

2. Additional framework adapters
- new CrewAI adapter with request/response boundary enforcement
- new AutoGen adapter with request/response boundary enforcement

3. Structured and file-content scanning
- SDK support for nested structured scanning (`scan_structured_input`)
- SDK support for file-based scanning (`scan_file_input`) for JSON and text inputs
- proxy endpoints for structured/file scans (`/v1/scan/structured`, `/v1/scan/file`)

4. Expanded policy template packs
- built-in templates for `finance`, `healthcare`, and `support`
- template catalog with plugin template extension support
- CLI template operations: `safeai templates list`, `safeai templates show`

5. Contributor onboarding
- contributor playbook for plugin, adapter, template, and security review workflows (`docs/18-contributor-onboarding-playbook.md`)

## Validation summary

- `ruff check safeai tests` passed.
- `mypy safeai` passed.
- `python3 -m unittest discover -s tests -v` passed (`102` tests).

## Packaging note

- Local wheel/sdist build remains blocked in this environment because `python3 -m build` requires module `build`, which is not installed locally.
- CI release should build artifacts in a controlled environment with build dependencies available.
