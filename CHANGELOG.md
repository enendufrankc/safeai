# Changelog

## 0.1.0rc1 - 2026-02-20

### Added

- Policy schema validation and hot reload support.
- Hierarchical data-tag policy matching (`personal` matches `personal.pii`, etc.).
- Output fallback templates for `block` and `redact` actions.
- Schema-bound memory controller with type checks, retention, and expiry purge.
- Audit query interface with CLI filters (`boundary`, `action`, `policy`, `agent`, `tool`, `since`, `last`).
- Unit, integration, and performance gate tests.
- Quickstart documentation and SDK end-to-end example.
- Architecture review record and CI quality workflow.

### Changed

- Release candidate version bumped to `0.1.0rc1`.
- Validation command now checks memory schemas in addition to policies.
