# SafeAI v0.1.0-rc1 Release Notes

Date: 2026-02-20
Status: Release candidate cut for Phase 1 gate validation

## Scope included

1. Policy engine
- schema validation
- deterministic first-match evaluation
- hot reload hooks
- hierarchical tag matching

2. Boundary enforcement
- input scanner
- output guard
- output fallback template rendering

3. Memory
- schema-bound writes
- type enforcement
- retention and expiry purge

4. Audit
- structured event logging
- query interface in SDK and CLI

5. Quality gates
- unit tests
- integration tests
- benchmark regression gates
- CI quality workflow for lint/type/test checks

## Local validation summary

- `python3 -m unittest discover -s tests -v` passed.
- `python3 -m compileall safeai tests` passed.
- local wheel build is blocked in this environment (`setuptools` missing, network-restricted dependency install).
