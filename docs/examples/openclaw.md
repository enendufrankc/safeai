# Use Case: OpenClaw Legal AI Platform

This walkthrough builds a production-ready AI legal assistant using SafeAI. OpenClaw is a fictional legal-tech startup that deploys AI agents to help attorneys draft contracts, search case law, and communicate with clients. Every boundary — input, output, tool call, agent message — is enforced by SafeAI.

By the end of this guide you will have configured and exercised every major SafeAI feature in a single, realistic application.

---

## The scenario

OpenClaw runs three AI agents:

| Agent | Role | Tools | Risk profile |
|:---|:---|:---|:---|
| `drafter` | Drafts contract clauses from templates | `search_templates`, `generate_clause` | Medium — accesses client names |
| `researcher` | Searches case law databases | `search_cases`, `fetch_ruling` | Low — reads public records |
| `reviewer` | Reviews drafts and communicates with attorneys | `send_email`, `flag_risk` | High — handles PII, sends external email |

The security requirements:

- No API keys or credentials may reach any LLM
- Client PII (names, emails, phone numbers) must be redacted in all outputs
- The `send_email` tool requires human approval before execution
- Only `reviewer` may use the `send_email` tool
- Agent-to-agent messages are scanned for sensitive data
- Every decision is audit-logged and queryable
- Secrets (API keys for case law DB) are accessed via scoped capability tokens
- Drafts stored in agent memory are encrypted with auto-expiry

---

## Step 1 — Install and scaffold

```bash
uv pip install safeai
safeai init --path .
```

This creates the config directory. Now replace the defaults with OpenClaw's configuration.

---

## Step 2 — Configure policies

```yaml title="policies/openclaw.yaml"
policies:
  # Secrets are blocked everywhere — highest priority
  - name: block-secrets
    boundary: [input, action, output]
    priority: 10
    condition:
      data_tags: [secret]
    action: block
    reason: "Credentials must never cross any boundary."

  # PII is redacted in outputs
  - name: redact-pii-output
    boundary: [output]
    priority: 20
    condition:
      data_tags: [personal.pii]
    action: redact
    reason: "Client PII must be redacted before leaving the system."

  # PII is blocked in inputs to the LLM
  - name: block-pii-input
    boundary: [input]
    priority: 25
    condition:
      data_tags: [personal.pii]
    action: block
    reason: "Client PII must not be sent to the model."

  # Destructive or external-facing tools require approval
  - name: approve-external-actions
    boundary: [action]
    priority: 30
    condition:
      data_tags: [external, destructive]
    action: require_approval
    reason: "External-facing actions require attorney approval."

  # Default allow
  - name: allow-remaining
    boundary: [input, action, output]
    priority: 1000
    condition: {}
    action: allow
    reason: "Allow when no restrictive policy matched."
```

---

## Step 3 — Define tool contracts

```yaml title="contracts/openclaw.yaml"
contracts:
  - tool_name: search_templates
    allowed_request_tags: [internal]
    allowed_response_fields: [template_id, title, body]

  - tool_name: generate_clause
    allowed_request_tags: [internal]
    allowed_response_fields: [clause_text, clause_id, warnings]

  - tool_name: search_cases
    allowed_request_tags: [internal]
    allowed_response_fields: [case_id, title, citation, summary]

  - tool_name: fetch_ruling
    allowed_request_tags: [internal]
    allowed_response_fields: [case_id, ruling_text, date, court]

  - tool_name: send_email
    allowed_request_tags: [external, personal.pii]
    allowed_response_fields: [message_id, status]

  - tool_name: flag_risk
    allowed_request_tags: [internal]
    allowed_response_fields: [risk_id, severity, description]
```

!!! note
    `send_email` explicitly allows `personal.pii` in its request tags because it needs the recipient's email address. But the policy engine still requires human approval for the `external` tag before the tool executes.

---

## Step 4 — Define agent identities

```yaml title="agents/openclaw.yaml"
agents:
  - agent_id: drafter
    allowed_tools: [search_templates, generate_clause]
    clearance_tags: [internal]

  - agent_id: researcher
    allowed_tools: [search_cases, fetch_ruling]
    clearance_tags: [internal]

  - agent_id: reviewer
    allowed_tools: [send_email, flag_risk, search_templates, generate_clause]
    clearance_tags: [internal, external, personal.pii]
```

Only `reviewer` has clearance for `external` and `personal.pii` tags. If `drafter` tries to call `send_email`, SafeAI blocks it before the function runs.

---

## Step 5 — Define memory schemas

```yaml title="schemas/memory.yaml"
schemas:
  - field: draft_text
    type: string
    retention: 24h
    encrypted: true

  - field: client_name
    type: string
    retention: 1h
    encrypted: true

  - field: session_notes
    type: string
    retention: 7d
    encrypted: false
```

Draft text and client names are encrypted at rest with automatic expiry. Session notes are retained for a week but not encrypted since they contain no PII.

---

## Step 6 — Initialize SafeAI in Python

```python title="openclaw/runtime.py"
from safeai import SafeAI

# Load all config: policies, contracts, identities, memory schemas
ai = SafeAI.from_config("safeai.yaml")
```

That single line assembles the full policy engine, contract registry, identity registry, approval manager, memory controller, and audit logger.

---

## Step 7 — Input scanning

Every prompt from an attorney goes through `scan_input` before reaching the LLM.

```python title="openclaw/chat.py"
def handle_attorney_message(message: str, agent_id: str = "drafter") -> str:
    # Scan for secrets and PII before the message reaches the model
    scan = ai.scan_input(message, agent_id=agent_id)

    if scan.decision.action == "block":
        return f"Blocked: {scan.decision.reason}"

    # Safe to forward to the LLM
    response = call_llm(scan.filtered)

    # Guard the response before showing it to the attorney
    guard = ai.guard_output(response, agent_id=agent_id)
    return guard.safe_output
```

**What happens:**

```python
# Secret detected — blocked at the input boundary
handle_attorney_message("Use API key sk-live-abc123 to access the DB")
# => "Blocked: Credentials must never cross any boundary."

# PII detected — blocked at the input boundary
handle_attorney_message("Draft a clause for alice@acme.com")
# => "Blocked: Client PII must not be sent to the model."

# Clean input — allowed through
handle_attorney_message("Draft a non-compete clause for a SaaS company")
# => "The following non-compete clause is recommended for SaaS agreements..."
```

---

## Step 8 — Output guarding

Even when inputs are clean, the LLM may hallucinate PII or reproduce memorized data.

```python
# The model hallucinates a phone number in its response
response = "Contact the client at 555-867-5309 for signature."
guard = ai.guard_output(response, agent_id="reviewer")

print(guard.safe_output)
# => "Contact the client at [REDACTED] for signature."

print(guard.decision.action)
# => "redact"
```

---

## Step 9 — Tool interception with contracts

Every tool call passes through the action boundary. SafeAI validates the request against the tool's contract, checks the agent's identity and clearance, and filters the response.

```python title="openclaw/tools.py"
def search_templates(query: str) -> dict:
    """Search the template database."""
    return {
        "template_id": "tmpl-42",
        "title": "SaaS Non-Compete",
        "body": "The Employee agrees not to...",
        "internal_score": 0.95,  # internal field — not in contract
    }


# Intercept the request
request_result = ai.intercept_tool_request(
    tool_name="search_templates",
    parameters={"query": "non-compete SaaS"},
    data_tags=["internal"],
    agent_id="drafter",
)

print(request_result.decision.action)
# => "allow"

# Execute the tool
raw_response = search_templates("non-compete SaaS")

# Intercept the response — strips fields not in the contract
response_result = ai.intercept_tool_response(
    tool_name="search_templates",
    response=raw_response,
    agent_id="drafter",
    request_data_tags=["internal"],
)

print(response_result.filtered_response)
# => {"template_id": "tmpl-42", "title": "SaaS Non-Compete", "body": "The Employee agrees not to..."}
# Note: "internal_score" is stripped — it's not in allowed_response_fields

print(response_result.stripped_fields)
# => ["internal_score"]
```

---

## Step 10 — Agent identity enforcement

The `drafter` agent tries to call `send_email` — a tool it's not authorized to use.

```python
result = ai.intercept_tool_request(
    tool_name="send_email",
    parameters={"to": "attorney@firm.com", "body": "Draft ready for review."},
    data_tags=["external"],
    agent_id="drafter",  # drafter is NOT allowed to use send_email
)

print(result.decision.action)
# => "block"
print(result.decision.reason)
# => "Agent 'drafter' is not authorized for tool 'send_email'"
```

Only `reviewer` can call `send_email`:

```python
result = ai.intercept_tool_request(
    tool_name="send_email",
    parameters={"to": "attorney@firm.com", "body": "Draft ready for review."},
    data_tags=["external"],
    agent_id="reviewer",
)

print(result.decision.action)
# => "require_approval" (because data_tags include "external")
```

---

## Step 11 — Human approval workflow

The `send_email` call was tagged `external`, so the policy engine returns `require_approval`. SafeAI creates an approval request that an attorney must review.

```python
# List pending approvals
pending = ai.list_approval_requests(status="pending")
for req in pending:
    print(f"[{req.request_id}] {req.tool_name} by {req.agent_id}: {req.reason}")

# Attorney approves the request
ai.approve_request(
    pending[0].request_id,
    approver_id="attorney-jane",
    note="Reviewed draft, safe to send.",
)

# Now retry the tool call with the approved request ID
result = ai.intercept_tool_request(
    tool_name="send_email",
    parameters={"to": "attorney@firm.com", "body": "Draft ready for review."},
    data_tags=["external"],
    agent_id="reviewer",
    approval_request_id=pending[0].request_id,
)

print(result.decision.action)
# => "allow"
```

From the CLI:

```bash
# List pending approvals
safeai approvals list --status pending

# Approve
safeai approvals approve req_abc123 --approver attorney-jane --note "Approved"

# Deny
safeai approvals deny req_def456 --approver attorney-jane --note "Draft needs revision"
```

---

## Step 12 — Capability tokens for secret access

The `researcher` agent needs an API key to query the case law database. Instead of giving the agent the raw key, SafeAI issues a scoped, time-limited capability token.

```python
# Issue a token scoped to researcher + search_cases, valid for 10 minutes
token = ai.issue_capability_token(
    agent_id="researcher",
    tool_name="search_cases",
    actions=["invoke"],
    ttl="10m",
    secret_keys=["CASELAW_API_KEY"],
)

print(token.token_id)
# => "cap_a1b2c3..."

# Resolve the secret using the token
import os
os.environ["CASELAW_API_KEY"] = "real-api-key-here"

resolved = ai.resolve_secret(
    token_id=token.token_id,
    secret_key="CASELAW_API_KEY",
    agent_id="researcher",
    tool_name="search_cases",
)

print(resolved.value)
# => "real-api-key-here"

# If drafter tries to use the same token — denied
try:
    ai.resolve_secret(
        token_id=token.token_id,
        secret_key="CASELAW_API_KEY",
        agent_id="drafter",  # wrong agent
        tool_name="search_cases",
    )
except Exception as e:
    print(e)
    # => "Capability token not valid for agent 'drafter'"
```

Tokens auto-expire after their TTL. Revoke early if needed:

```python
ai.revoke_capability_token(token.token_id)
ai.purge_expired_capability_tokens()
```

---

## Step 13 — Encrypted agent memory

The `drafter` agent stores work-in-progress drafts in encrypted memory.

```python
# Store a draft — encrypted at rest, auto-expires in 24h
ai.memory_write("draft_text", "The Employee agrees not to...", agent_id="drafter")

# Read it back
draft = ai.memory_read("draft_text", agent_id="drafter")
print(draft)
# => "The Employee agrees not to..."

# Store client name — encrypted, expires in 1h
ai.memory_write("client_name", "Alice Johnson", agent_id="drafter")

# After 1 hour, the field is automatically purged
# Or purge manually:
purged = ai.memory_purge_expired()
print(f"Purged {purged} expired entries")
```

Memory handles let you share encrypted references between agents without exposing the raw value:

```python
# Resolve an encrypted memory handle (policy-gated)
value = ai.resolve_memory_handle("handle_draft_001", agent_id="reviewer")
```

---

## Step 14 — Agent-to-agent messaging

When `drafter` sends a completed draft to `reviewer`, the message crosses a trust boundary and is scanned for sensitive content.

```python
result = ai.intercept_agent_message(
    message="Draft complete. Client Alice Johnson (alice@acme.com) approved the terms.",
    source_agent_id="drafter",
    destination_agent_id="reviewer",
    session_id="session-42",
)

print(result["decision"]["action"])
# => "block" or "redact" depending on policy
# The message contains PII (email, name) — policy decides what to do

print(result["data_tags"])
# => ["personal.pii"]

print(result["filtered_message"])
# => "" (blocked) or "[REDACTED]" (redacted)
```

!!! tip
    Design agent-to-agent messages to pass references (IDs, handle keys) instead of raw PII. SafeAI enforces this pattern by scanning every message.

---

## Step 15 — Structured payload scanning

When the `drafter` agent receives a complex JSON payload from an integration, SafeAI scans every nested field.

```python
payload = {
    "client": {
        "name": "Alice Johnson",
        "email": "alice@acme.com",
        "phone": "555-867-5309",
    },
    "contract": {
        "type": "non-compete",
        "jurisdiction": "Delaware",
    },
}

result = ai.scan_structured_input(payload, agent_id="drafter")

print(result.decision.action)
# => "block" (PII found in nested fields)

for detection in result.detections:
    print(f"  {detection.path}: {detection.tag} ({detection.detector})")
# => client.name: personal.pii (name_detector)
# => client.email: personal.pii (email_detector)
# => client.phone: personal.pii (phone_detector)
```

File scanning works the same way:

```python
result = ai.scan_file_input("intake_form.json", agent_id="drafter")
print(result["decision"]["action"])
```

---

## Step 16 — Audit trail

Every decision SafeAI makes is logged. Query the audit trail to investigate incidents or generate compliance reports.

```python
# All blocked events in the last hour
blocked = ai.query_audit(action="block", since="1h")
for event in blocked:
    print(f"[{event['boundary']}] {event['reason']} (agent={event['agent_id']})")

# All decisions for a specific agent
drafter_events = ai.query_audit(agent_id="drafter", limit=50)

# All approval-related events
approvals = ai.query_audit(action="require_approval", boundary="action")
```

From the CLI:

```bash
# Recent blocks
safeai logs --action block --last 1h

# All events for the reviewer agent
safeai logs --agent reviewer --tail 50

# Detailed view of a specific event
safeai logs --detail evt_abc123 --text-output

# Export for compliance
safeai logs --last 30d --json-output > compliance-report.jsonl
```

---

## Step 17 — Framework adapter integration

In production, OpenClaw uses LangChain for orchestration. SafeAI wraps every tool transparently.

```python title="openclaw/agent.py"
from safeai import SafeAI
from safeai.middleware.langchain import SafeAIBlockedError

ai = SafeAI.from_config("safeai.yaml")
adapter = ai.langchain_adapter()


def search_templates(query: str) -> dict:
    return {"template_id": "tmpl-42", "title": "SaaS Non-Compete", "body": "..."}


def send_email(to: str, body: str) -> dict:
    return {"message_id": "msg-1", "status": "sent"}


# Wrap tools — SafeAI intercepts every call automatically
safe_search = adapter.wrap_tool(
    "search_templates", search_templates,
    agent_id="drafter",
    request_data_tags=["internal"],
)

safe_email = adapter.wrap_tool(
    "send_email", send_email,
    agent_id="reviewer",
    request_data_tags=["external", "personal.pii"],
)

# Use wrapped tools normally — SafeAI is invisible when things go right
result = safe_search(query="non-compete SaaS")
print(result)
# => {"template_id": "tmpl-42", "title": "SaaS Non-Compete", "body": "..."}

# Unauthorized call raises SafeAIBlockedError
try:
    safe_email(to="alice@acme.com", body="Draft ready")
except SafeAIBlockedError as e:
    print(f"Blocked: {e.reason}")
    # => "Blocked: External-facing actions require attorney approval."
```

The same pattern works with CrewAI, AutoGen, Claude ADK, and Google ADK — swap `langchain_adapter()` for `crewai_adapter()`, `autogen_adapter()`, etc.

---

## Step 18 — Proxy mode for non-Python services

OpenClaw's document management system is written in Go. It calls SafeAI via the REST API.

```bash
safeai serve --mode sidecar --port 8000 --config safeai.yaml
```

```bash title="From the Go service"
# Scan a prompt
curl -s -X POST http://localhost:8000/v1/scan/input \
  -H "content-type: application/json" \
  -d '{"text": "Draft clause for alice@acme.com", "agent_id": "drafter"}'

# Guard a response
curl -s -X POST http://localhost:8000/v1/guard/output \
  -H "content-type: application/json" \
  -d '{"text": "Contact the client at 555-867-5309", "agent_id": "reviewer"}'

# Query audit trail
curl -s -X POST http://localhost:8000/v1/audit/query \
  -H "content-type: application/json" \
  -d '{"action": "block", "limit": 10}'

# Check metrics
curl -s http://localhost:8000/v1/metrics
```

---

## Step 19 — Coding agent integration

OpenClaw developers use Claude Code to write contract templates. SafeAI hooks ensure no secrets leak during development.

```bash
# Install SafeAI hooks for Claude Code
safeai setup claude-code --config safeai.yaml --path .

# Or for Cursor
safeai setup cursor --config safeai.yaml --path .
```

Every command the coding agent runs is scanned through SafeAI's hook protocol. If the agent tries to embed an API key in a template, SafeAI blocks it before the file is written.

---

## What SafeAI prevented

In this single application, SafeAI enforced:

| Threat | SafeAI response | Feature |
|:---|:---|:---|
| API key in a prompt | **Blocked** at input boundary | Secret detection |
| Client email in a prompt | **Blocked** at input boundary | PII protection |
| Phone number in LLM response | **Redacted** in output | Output guarding |
| `drafter` calling `send_email` | **Blocked** — not in identity | Agent identity |
| `reviewer` sending email | **Held** for attorney approval | Approval workflow |
| Internal score in tool response | **Stripped** — not in contract | Tool contracts |
| PII in agent-to-agent message | **Blocked/redacted** | Agent messaging |
| PII in nested JSON payload | **Detected** with field path | Structured scanning |
| Raw API key access | **Scoped** via capability token | Capability tokens |
| Draft stored in memory | **Encrypted** with auto-expiry | Encrypted memory |
| Every decision | **Logged** with context hash | Audit logging |

All of this with a single `SafeAI.from_config("safeai.yaml")` call and standard YAML configuration.

---

## Full project structure

```
openclaw/
├── safeai.yaml              # Main SafeAI configuration
├── policies/
│   └── openclaw.yaml        # Policy rules
├── contracts/
│   └── openclaw.yaml        # Tool contracts
├── agents/
│   └── openclaw.yaml        # Agent identities
├── schemas/
│   └── memory.yaml          # Memory schemas
├── openclaw/
│   ├── runtime.py           # SafeAI initialization
│   ├── chat.py              # Input scanning + output guarding
│   ├── tools.py             # Tool definitions
│   └── agent.py             # LangChain integration
└── tests/
    └── test_security.py     # Boundary enforcement tests
```

---

## Next steps

- [Installation](../getting-started/installation.md) — get SafeAI running
- [Policy Engine](../guides/policy-engine.md) — deep dive into rule design
- [Tool Contracts](../guides/tool-contracts.md) — define what each tool can see
- [Approval Workflows](../guides/approval-workflows.md) — configure human-in-the-loop gates
- [Integrations](../integrations/index.md) — connect to your framework
