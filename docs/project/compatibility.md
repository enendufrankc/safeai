# Compatibility Policy

This document defines SafeAI's versioning scheme, compatibility guarantees, and the process for introducing breaking changes.

---

## Scope

This compatibility policy covers the following public interfaces:

| Interface | Examples |
|-----------|----------|
| **SDK (Python API)** | `SafeAI` class methods, `ScanResult` models, middleware base classes |
| **CLI** | Command names, flags, output formats |
| **HTTP API** | Proxy endpoints, request/response schemas, status codes |
| **Configuration schemas** | `safeai.yaml` structure, policy rule format, agent identity format |
| **Plugin entry points** | `safeai_detectors`, `safeai_adapters`, `safeai_policy_templates` |

Internal modules (anything not documented in the API Reference or this list) may change without notice.

---

## Pre-1.0 Versioning

SafeAI uses `0.y.z` versioning while the API stabilizes before the 1.0 release.

| Segment | Meaning |
|---------|---------|
| `z` (patch) | Bug fixes only. No new features, no breaking changes. |
| `y` (minor) | New features and controlled breaking changes. Every breaking change is documented in the [Changelog](../changelog.md) with migration guidance. |

!!! warning "Pre-1.0 stability"
    During the `0.y.z` phase, minor releases **may** include breaking changes. We minimize these and always document them, but strict backward compatibility is not guaranteed until 1.0.

---

## Post-1.0 Versioning

After the 1.0 release, SafeAI will follow strict [Semantic Versioning](https://semver.org/):

| Segment | Meaning |
|---------|---------|
| `z` (patch) | Bug fixes only |
| `y` (minor) | New features, backward-compatible |
| `x` (major) | Breaking changes |

---

## Schema Compatibility Rules

Configuration and data schemas follow these rules:

### Additive changes (backward-compatible)

These changes are allowed in any minor release:

- Adding new optional fields with sensible defaults
- Adding new enum values to existing fields
- Adding new policy rule types
- Adding new CLI flags with default behavior matching the previous release

### Breaking changes

These changes require a version bump and migration guidance:

- Removing or renaming fields
- Changing the type of an existing field
- Changing the default value of an existing field in a way that alters behavior
- Removing CLI flags or changing their meaning
- Changing HTTP endpoint paths or response structures

---

## Deprecation Policy

Before removing any public interface, SafeAI follows a deprecation cycle:

1. **Deprecation notice.** The feature is marked as deprecated in the documentation and emits a runtime deprecation warning when used.

2. **Migration guidance.** The deprecation notice includes instructions for migrating to the replacement.

3. **Minimum retention.** Deprecated features are retained for at least **2 minor releases** before removal.

4. **Removal.** The feature is removed in a subsequent minor release (pre-1.0) or major release (post-1.0). Removal is documented in the Changelog.

### Example timeline (pre-1.0)

| Version | Event |
|---------|-------|
| 0.7.0 | Feature X deprecated, warning added, migration guide published |
| 0.8.0 | Feature X still works, warning emitted |
| 0.9.0 | Feature X removed |

---

## Breaking Change Process

When a breaking change is necessary:

1. **Open an issue** explaining why the change is needed and what alternatives were considered.
2. **Get maintainer approval** (2 approvals for significant changes).
3. **Implement the deprecation** in the current release (if following the deprecation cycle).
4. **Document the change** in the Changelog with:
    - What changed
    - Why it changed
    - How to migrate
5. **Update all documentation** and examples to reflect the new behavior.

!!! tip "Avoiding breaking changes"
    Most features can be added in a backward-compatible way by using optional parameters with defaults, new endpoints alongside existing ones, or configuration flags that opt in to new behavior.

---

## Testing Compatibility

SafeAI's test suite includes backward-compatibility checks:

- **Config loading tests** verify that older config files still load correctly with default values for new fields.
- **CLI output tests** verify that existing flag combinations produce expected results.
- **Schema validation tests** verify that documents valid under the previous schema are still valid under the current one.

Contributors are expected to run these tests and avoid introducing unintentional breaking changes.
