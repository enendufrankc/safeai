# SafeAI Compatibility Policy

This document defines compatibility guarantees for SafeAI interfaces, schemas, and releases.

## 1) Scope

This policy covers:

- Python SDK public APIs
- CLI commands and flags
- HTTP proxy/gateway APIs
- Configuration and policy schemas
- Migration behavior between released versions

Internal implementation details are not considered stable unless explicitly documented as public.

## 2) Versioning policy

### Pre-1.0 phase (`0.y.z`)

- `z` (patch): bug fixes and security fixes only; no intentional breaking changes.
- `y` (minor): new features and controlled breaking changes allowed only with migration notes.
- Breaking changes in pre-1.0 must be clearly called out in release notes.

### Stable phase (`1.0.0+`)

SafeAI follows SemVer:

- `MAJOR`: breaking change
- `MINOR`: backward-compatible feature additions
- `PATCH`: backward-compatible fixes

## 3) Schema compatibility

SafeAI schema files are versioned under `schemas/<version>/`.

Current schema version: `v1alpha1`.

Rules:

- Additive fields are backward-compatible.
- Field removal, rename, or behavior change is breaking.
- Enum value removal is breaking.
- Enum value addition is non-breaking only if consumers are documented to tolerate unknown values.

## 4) Deprecation policy

When deprecating a public field, flag, API, or behavior:

1. Mark it deprecated in docs and release notes.
2. Keep support for at least one minor release cycle before removal.
3. Provide a migration path with explicit before/after examples.

Security exceptions may accelerate deprecation/removal when needed to protect users.

## 5) Breaking change process

A breaking change requires:

- A design issue or proposal documenting rationale and alternatives
- Migration guidance in release notes
- Approval per `GOVERNANCE.md`
- Compatibility tests or fixtures showing expected behavior

## 6) Support window

Until first stable release, only `main` is supported for security fixes.
After stable release, supported versions and maintenance windows will be documented here.

## 7) Release note requirements

Each release must include:

- Compatibility impact summary
- Deprecations introduced
- Breaking changes (if any)
- Migration steps and fallback guidance

