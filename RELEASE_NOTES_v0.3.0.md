# SafeAI v0.3.0 Release Notes

Date: 2026-02-20  
Status: Phase 3 release gate passed

## Scope included

1. Approval workflow runtime gate
- policy-driven `require_approval` requests now create approval records
- approval decisions can be approved or denied with binding checks (agent/tool/session)
- persistent approval records support CLI-driven decisions across SDK processes

2. Secret management hardening
- capability-gated secret manager interface finalized
- production Vault and AWS backends implemented
- secret resolution emits audit events without logging secret values

3. Memory security upgrades
- encrypted memory fields are stored as opaque encrypted handles
- handle resolution requires control-layer API and policy evaluation
- automatic memory retention purge now runs during memory operations and logs purge events

4. Framework integrations
- Claude ADK adapter with request/response interception
- Google ADK adapter with request/response interception
- adapters align behavior with existing LangChain integration

5. Quality and test gates
- approval workflow tests (runtime + CLI)
- encrypted memory handle tests
- Claude/Google ADK adapter tests
- phase-3 end-to-end security tests

## Validation summary

- `ruff check safeai tests` passed.
- `mypy safeai` passed.
- `python3 -m unittest discover -s tests -v` passed (`84` tests).

## Packaging note

- Local wheel/sdist build remains blocked in this environment because `python3 -m build` requires module `build`, which is not installed locally.
- CI release should build artifacts in a controlled environment with build dependencies available.
