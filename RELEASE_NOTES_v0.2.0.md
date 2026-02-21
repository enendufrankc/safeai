# SafeAI v0.2.0 Release Notes

Date: 2026-02-20  
Status: Phase 2 release gate passed

## Scope included

1. Tool control enforcement
- tool contracts parsed, normalized, and validated from schema-backed YAML
- undeclared tools blocked by default
- request parameter filtering against contract accepted fields
- response field filtering against contract emitted fields and policy decisions

2. Agent identity and binding
- agent identity schema and loader
- per-agent tool binding checks
- per-agent clearance tag checks with hierarchical tag matching

3. Action-boundary audit depth
- enriched action audit events with:
  - `event_id`
  - `context_hash`
  - `session_id`
  - `source_agent_id`
  - `destination_agent_id`
  - request/response phase metadata
  - stripped/filtered field details

4. Developer operations
- advanced `safeai logs` filters (`data_tag`, `phase`, `session`, `event_id`, metadata key/value, `until`)
- `safeai logs --detail <event_id>` full-event inspection
- `safeai init` now scaffolds `agents/default.yaml`
- `safeai validate` now validates and reports agent identity documents

5. Framework integration
- production LangChain adapter:
  - `SafeAILangChainAdapter.wrap_tool`
  - `SafeAILangChainAdapter.wrap_langchain_tool`
  - `SafeAICallback`
  - `SafeAIBlockedError`

6. Quality and test gates
- tool-control E2E suite
- LangChain adapter tests
- advanced audit/log query tests

## Validation summary

- `ruff check safeai tests` passed.
- `python3 -m unittest discover -s tests -v` passed (`56` tests).
- `python3 -m compileall safeai tests` passed.
- `safeai init` and `safeai validate` smoke test passed with default scaffolding.
- local wheel/sdist build is currently blocked in this environment (`python3 -m build`: module `build` not installed).
