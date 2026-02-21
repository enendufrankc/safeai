# Changelog

All notable changes to SafeAI are documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/).

---

## 0.7.0 -- 2026-02-21

### Added

- Intelligence layer with 5 AI advisory agents: auto-config, policy recommender, incident explainer, compliance mapper, and integration generator (`safeai/intelligence/`).
- BYOM (Bring Your Own Model) backend abstraction with `AIBackend` protocol, `AIBackendRegistry`, `OllamaBackend`, and `OpenAICompatibleBackend` (`safeai/intelligence/backend.py`).
- `MetadataSanitizer` that strips raw values (secrets, PII, matched patterns) from audit events before they enter any AI prompt (`safeai/intelligence/sanitizer.py`).
- `BaseAdvisor` ABC and `AdvisorResult` frozen dataclass for all intelligence agents (`safeai/intelligence/advisor.py`).
- Codebase structure extraction via `ast.parse` for safe metadata-only project analysis (`safeai/intelligence/sanitizer.py`).
- Prompt template packages for all 5 agents with built-in compliance requirement mappings (HIPAA, PCI-DSS, SOC2, GDPR) and framework integration templates (`safeai/intelligence/prompts/`).
- CLI command group `safeai intelligence` with 5 subcommands: `auto-config`, `recommend`, `explain`, `compliance`, `integrate` (`safeai/cli/intelligence.py`).
- SDK methods on `SafeAI` class: `register_ai_backend()`, `list_ai_backends()`, `intelligence_auto_config()`, `intelligence_recommend()`, `intelligence_explain()`, `intelligence_compliance()`, `intelligence_integrate()` (`safeai/api.py`).
- Proxy intelligence endpoints: `GET /v1/intelligence/status`, `POST /v1/intelligence/explain`, `POST /v1/intelligence/recommend`, `POST /v1/intelligence/compliance` (`safeai/proxy/routes.py`).
- Dashboard intelligence endpoint with RBAC: `POST /v1/dashboard/intelligence/explain` with `intelligence:explain` permission (`safeai/dashboard/routes.py`).
- `IntelligenceConfig` and `IntelligenceBackendConfig` Pydantic models nested under `SafeAIConfig.intelligence` (`safeai/config/models.py`).
- 8 new test files with 94 tests covering backends, sanitizer, all 5 agents, and CLI (`tests/test_intelligence_*.py`).

### Changed

- Package version moved to `0.7.0`.
- CLI entrypoint now includes `intelligence` command group.
- Intelligence layer is disabled by default (`intelligence.enabled: false`). All features require explicit opt-in.

---

## 0.6.0 -- 2026-02-20

### Added

- Plugin loading system for custom detectors, adapters, and policy templates from local plugin files (`safeai/plugins/manager.py`, `safeai/config/defaults/plugins/example.py`).
- Additional framework adapters for CrewAI and AutoGen with request/response interception parity (`safeai/middleware/crewai.py`, `safeai/middleware/autogen.py`).
- Structured payload and file-content scanning APIs in SDK and proxy routes (`scan_structured_input`, `scan_file_input`, `/v1/scan/structured`, `/v1/scan/file`).
- Policy template catalog with built-in template packs for `finance`, `healthcare`, and `support`, plus plugin template integration (`safeai/templates/catalog.py`, `safeai/config/defaults/policies/templates/*.yaml`).
- New CLI commands for policy templates (`safeai templates list`, `safeai templates show`).
- Contributor onboarding playbook for ecosystem extension workflows.
- Universal coding agent hook (`safeai hook`) and setup system (`safeai setup claude-code`, `safeai setup cursor`).
- MCP server integration (`safeai mcp`).

### Changed

- `safeai init` now scaffolds a plugin starter file at `plugins/example.py`.
- Proxy API surface now exposes plugin discovery and policy template discovery endpoints (`/v1/plugins`, `/v1/policies/templates`, `/v1/policies/templates/{template_name}`).
- Package version moved to `0.6.0`.
- Proxy app and health metadata moved to `0.6.0`.

---

## 0.5.0 -- 2026-02-20

### Added

- Phase 5 dashboard backend APIs for overview, incident query, approval queue decisions, compliance reports, tenant policy sets, and alert rule evaluation (`safeai/dashboard/routes.py`, `safeai/dashboard/service.py`).
- Browser dashboard UI at `/dashboard` for security operations visibility and approvals workflow execution.
- RBAC and tenant-isolation controls for dashboard endpoints with scoped users and tenant filtering.
- Multi-tenant policy-set storage scaffold and management defaults (`safeai/config/defaults/tenants/policy-sets.yaml`).
- Alert-rule configuration and alert event log sink with default alert scaffolding (`safeai/config/defaults/alerts/default.yaml`).
- Phase 5 integration coverage for dashboard flows, approvals UI, compliance reports, tenant isolation, and alerting (`tests/test_dashboard_phase5.py`).

### Changed

- `safeai init` now scaffolds dashboard enterprise defaults (`tenants/policy-sets.yaml`, `alerts/default.yaml`).
- `safeai.yaml` schema defaults now include dashboard RBAC/user settings and alert/tenant file locations.
- Proxy runtime now wires dashboard services and routes into sidecar/gateway app startup.
- Package version moved to `0.5.0`.
- Proxy app and health metadata moved to `0.5.0`.

---

## 0.4.0 -- 2026-02-20

### Added

- Full proxy HTTP boundary API surface: input scan, output guard, tool interception, agent-message interception, memory APIs, audit query, and policy reload endpoints (`safeai/proxy/routes.py`).
- Proxy upstream forwarding mode (`/v1/proxy/forward`) with input pre-scan and output guard filtering before returning upstream responses.
- Gateway mode runtime checks requiring source/destination agent context for multi-agent enforcement paths.
- In-process Prometheus-style request counters, decision counters, and latency histograms exposed at `/v1/metrics` (`safeai/proxy/metrics.py`).
- Phase 4 proxy integration and regression benchmark suites (`tests/test_proxy_api.py`, `tests/test_proxy_benchmark.py`).

### Changed

- `safeai serve` now supports explicit proxy mode, config path, and upstream base URL options (`safeai/cli/serve.py`).
- SDK now exposes agent-to-agent action enforcement path for gateway/proxy execution (`safeai/api.py`).
- Package version moved to `0.4.0`.
- Proxy app and health metadata moved to `0.4.0`.

---

## 0.3.0 -- 2026-02-20

### Added

- Approval workflow manager with persistent request state, approval/denial decisions, and validation bindings (`safeai/core/approval.py`).
- Runtime approval gate integration for policy `require_approval` outcomes at the action boundary (`safeai/core/interceptor.py`).
- CLI approval operations: `safeai approvals list|approve|deny` (`safeai/cli/approvals.py`).
- Secret-resolution audit events (without secret payload exposure) and SDK secret backend management APIs (`safeai/api.py`).
- Encrypted memory handle storage with per-agent handle resolution and policy-gated resolve path (`safeai/core/memory.py`, `safeai/api.py`).
- Memory retention purge automation hooks with memory-boundary audit events (`safeai/api.py`).
- Production Claude ADK and Google ADK adapters with request/response interception parity (`safeai/middleware/claude_adk.py`, `safeai/middleware/google_adk.py`).
- Phase 3 security and integration coverage for approvals, handles, secrets, and new adapters (`tests/test_approval_workflow.py`, `tests/test_memory_security.py`, `tests/test_phase3_security_e2e.py`, `tests/test_claude_adk_adapter.py`, `tests/test_google_adk_adapter.py`).
- Optional dependency groups for Vault/AWS secret backends (`pyproject.toml` extras: `vault`, `aws`, `all`).

### Changed

- Package version moved to `0.3.0`.
- Default scaffold now includes approval and memory runtime sections in `safeai.yaml`.
- Proxy app version metadata moved to `0.3.0`.

---

## 0.2.0 -- 2026-02-20

### Added

- Tool contract registry and schema-backed loading/validation.
- Action-boundary request contract checks and response field filtering.
- Agent identity registry with tool binding and clearance-tag enforcement.
- Full action-boundary audit payloads (`event_id`, `context_hash`, session/source/destination IDs, phase metadata).
- Advanced `safeai logs` querying (`data_tag`, `phase`, `session`, event detail view, metadata filters, time range controls).
- Production-ready LangChain adapter (`SafeAILangChainAdapter`, `SafeAICallback`, `SafeAIBlockedError`).
- End-to-end tool-control test coverage and adapter integration tests.
- Agent identity schema (`schemas/v1alpha1/agent-identity.schema.json`) and default `agents/default.yaml` scaffold.

### Changed

- Starter policies now include default allow rules for `action` and `output` after restrictive policies.
- `safeai validate` now reports agent identity document counts.
- `safeai init` now scaffolds agent identity defaults.

---

## 0.1.0rc1 -- 2026-02-20

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
