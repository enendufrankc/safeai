# SafeAI — Complete End-to-End Testing Guide

> **Audience:** Someone with zero prior knowledge of SafeAI.
> **Goal:** Test every feature of SafeAI from installation through every API, CLI command, HTTP endpoint, plugin, adapter, and intelligence agent.
> **Structure:** 12 phases, 100+ test steps. Each step has the exact command or code to run and the expected output.

---

## Phase 0: Installation & Project Setup

### 0.1 Install SafeAI from PyPI

```bash
# Create a fresh virtual environment
python3 -m venv ~/.venvs/safeai-test
source ~/.venvs/safeai-test/bin/activate

# Install the SDK with ALL optional extras (vault, aws, mcp, docs)
pip install "safeai-sdk[all]"

# Verify installation
python -c "from safeai import SafeAI; print('SafeAI imported OK')"
safeai --help
```

**Expected:** SafeAI installs without errors. `safeai --help` prints available commands:
`init`, `validate`, `scan`, `logs`, `serve`, `hook`, `mcp`, `approvals`, `templates`,
`intelligence`, `setup`, `observe`, `alerts`.

### 0.2 Scaffold a New SafeAI Project

```bash
mkdir /tmp/safeai-e2e-test && cd /tmp/safeai-e2e-test

# Scaffold all config files (non-interactive to avoid prompts)
safeai init --path . --non-interactive
```

**Expected:** The following files/dirs are created:
```
safeai.yaml
policies/default.yaml
contracts/example.yaml
schemas/memory.yaml
agents/default.yaml
plugins/example.py
tenants/policy-sets.yaml
alerts/default.yaml
logs/           (directory)
```

### 0.3 Validate the Scaffolded Config

```bash
safeai validate --config safeai.yaml
```

**Expected:** Output says config is valid, no errors.

### 0.4 Review the Default Policy

Open `policies/default.yaml`. It should contain rules like:
- `block-secrets-everywhere` — priority 10, blocks secrets at all 3 boundaries
- `redact-personal-data-in-output` — priority 20, redacts PII in output
- `allow-input-by-default` — priority 1000, catch-all allow for input
- `allow-action-by-default` — priority 1000, catch-all allow for action
- `allow-output-by-default` — priority 1000, catch-all allow for output

---

## Phase 1: SDK Core — Input Scanning

All tests in this phase use Python. Create a file `test_phase1.py` and run with `python test_phase1.py`.

### 1.1 Create a SafeAI Instance with Quickstart

```python
from safeai import SafeAI

ai = SafeAI.quickstart()
print(f"Type: {type(ai)}")
print(f"Has scan_input: {hasattr(ai, 'scan_input')}")
print(f"Has guard_output: {hasattr(ai, 'guard_output')}")
```

**Expected:** All three print `True` / `<class 'safeai.api.SafeAI'>`.

### 1.2 Detect an OpenAI API Key

```python
result = ai.scan_input("Here is my key: sk-ABCDEF1234567890ABCDEF1234567890ABCDEF12345678")
print(f"Action:     {result.decision.action}")
print(f"Policy:     {result.decision.policy_name}")
print(f"Detections: {len(result.detections)}")
print(f"First tag:  {result.detections[0].tag}")
```

**Expected:**
```
Action:     block
Policy:     block-secrets-everywhere
Detections: 1
First tag:  secret.credential
```

### 1.3 Detect an AWS Access Key

```python
result = ai.scan_input("My AWS key is AKIAIOSFODNN7EXAMPLE")
print(f"Action: {result.decision.action}")
print(f"Tag:    {result.detections[0].tag}")
```

**Expected:** `Action: block`, `Tag: secret.credential`

### 1.4 Clean Input Passes Through

```python
result = ai.scan_input("Hello, this is a normal message with no secrets or PII.")
print(f"Action:     {result.decision.action}")
print(f"Detections: {len(result.detections)}")
```

**Expected:** `Action: allow`, `Detections: 0`

### 1.5 Detect Email Address

```python
result = ai.scan_input("Contact alice@example.com for details")
print(f"Action: {result.decision.action}")
print(f"Tag:    {result.detections[0].tag}")
```

**Expected:** `Action: allow` (default input policy allows PII — PII is only redacted at the **output** boundary).
`Tag: personal.pii`

### 1.6 Detect Phone Number

```python
result = ai.scan_input("Call me at 555-123-4567")
print(f"Detections: {len(result.detections)}")
if result.detections:
    print(f"Tag: {result.detections[0].tag}")
```

**Expected:** At least 1 detection with tag `personal.pii`.

### 1.7 Detect SSN

```python
result = ai.scan_input("SSN: 123-45-6789")
print(f"Detections: {len(result.detections)}")
if result.detections:
    print(f"Tag: {result.detections[0].tag}")
```

**Expected:** Detected, tag `personal.pii`.

### 1.8 Detect Credit Card

```python
result = ai.scan_input("Card number: 4111111111111111")
print(f"Detections: {len(result.detections)}")
if result.detections:
    print(f"Tag: {result.detections[0].tag}")
```

**Expected:** Detected, tag `personal.financial`.

### 1.9 Multiple Detections in One Input

```python
result = ai.scan_input("Email alice@example.com, key sk-ABCDEF1234567890ABCDEF1234567890ABCDEF12345678")
print(f"Action:     {result.decision.action}")
print(f"Detections: {len(result.detections)}")
tags = {d.tag for d in result.detections}
print(f"Tags found: {tags}")
```

**Expected:** `Action: block` (secret detected). `Detections: >= 2`. Tags include `secret.credential` and `personal.pii`.

### 1.10 Structured Input Scanning

```python
result = ai.scan_structured_input(
    {"user": {"email": "alice@example.com"}, "note": "hello"},
    agent_id="test-agent"
)
print(f"Action:     {result.decision.action}")
print(f"Detections: {len(result.detections)}")
print(f"Filtered:   {result.filtered}")
```

**Expected:** Email detected in nested dict. `result.filtered` has the value redacted or removed.

### 1.11 File Input Scanning

```python
import tempfile, json, os

# Create a temp file with a secret
with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    json.dump({"api_key": "sk-ABCDEF1234567890ABCDEF1234567890ABCDEF12345678"}, f)
    tmp_path = f.name

result = ai.scan_file_input(tmp_path, agent_id="test-agent")
print(f"Result keys: {list(result.keys())}")
print(f"Blocked:     {'block' in str(result)}")
os.unlink(tmp_path)
```

**Expected:** File is scanned and the secret is detected. Result dict contains decision info.

### 1.12 Quickstart with Custom Options

```python
# Block PII at input boundary (not default)
ai_strict = SafeAI.quickstart(block_pii=True, redact_pii=False)
result = ai_strict.scan_input("Email alice@example.com")
print(f"Action: {result.decision.action}")
```

**Expected:** `Action: block` (PII blocked at input with `block_pii=True`).

```python
# Allow secrets through (disable secret blocking)
ai_lax = SafeAI.quickstart(block_secrets=False)
result = ai_lax.scan_input("sk-ABCDEF1234567890ABCDEF1234567890ABCDEF12345678")
print(f"Action: {result.decision.action}")
```

**Expected:** `Action: allow` (secrets allowed with `block_secrets=False`).

---

## Phase 2: SDK Core — Output Guarding

### 2.1 Redact PII in Output

```python
ai = SafeAI.quickstart()

result = ai.guard_output("Contact alice@example.com for help")
print(f"Action:      {result.decision.action}")
print(f"Safe output: {result.safe_output}")
```

**Expected:** `Action: redact`. `Safe output:` the email is replaced with `[REDACTED]` or similar.

### 2.2 Block Secrets in Output

```python
result = ai.guard_output("Here is the key: sk-ABCDEF1234567890ABCDEF1234567890ABCDEF12345678")
print(f"Action: {result.decision.action}")
```

**Expected:** `Action: block`. Secrets are blocked at all boundaries.

### 2.3 Clean Output Passes Through

```python
result = ai.guard_output("The weather is sunny today.")
print(f"Action:      {result.decision.action}")
print(f"Safe output: {result.safe_output}")
```

**Expected:** `Action: allow`. `Safe output:` identical to input.

---

## Phase 3: SDK Core — Tool & Agent Interception (Action Boundary)

### 3.1 Intercept a Tool Request with Secret Tags

```python
result = ai.intercept_tool_request(
    tool_name="web_search",
    parameters={"query": "test"},
    data_tags=["secret.credential"],
    agent_id="agent-A"
)
print(f"Action:  {result.decision.action}")
print(f"Reason:  {result.decision.reason}")
```

**Expected:** `Action: block` — secret tag triggers `block-secrets-everywhere` policy.

### 3.2 Intercept a Clean Tool Request

```python
result = ai.intercept_tool_request(
    tool_name="web_search",
    parameters={"query": "weather"},
    data_tags=[],
    agent_id="agent-A"
)
print(f"Action: {result.decision.action}")
```

**Expected:** `Action: allow`.

### 3.3 Intercept a Tool Response

```python
result = ai.intercept_tool_response(
    tool_name="web_search",
    response={"result": "Contact alice@example.com"},
    agent_id="agent-A"
)
print(f"Action:   {result.decision.action}")
print(f"Filtered: {result.filtered_response}")
```

**Expected:** PII in the response is detected. The `filtered_response` has the email redacted.

### 3.4 Intercept Agent-to-Agent Message

```python
result = ai.intercept_agent_message(
    message="Hello, here is the data you requested.",
    source_agent_id="agent-A",
    destination_agent_id="agent-B"
)
print(f"Decision: {result['decision']['action']}")
print(f"Filtered: {result['filtered_message']}")
```

**Expected:** `Decision: allow`. Message passes clean.

```python
result = ai.intercept_agent_message(
    message="The API key is sk-ABCDEF1234567890ABCDEF1234567890ABCDEF12345678",
    source_agent_id="agent-A",
    destination_agent_id="agent-B"
)
print(f"Decision: {result['decision']['action']}")
```

**Expected:** `Decision: block`. Secret detected in agent message.

---

## Phase 4: Config-Driven Setup & Policy Engine

### 4.1 Load from Config File

```python
import os
os.chdir("/tmp/safeai-e2e-test")  # where we scaffolded in Phase 0

ai = SafeAI.from_config("safeai.yaml")
print(f"Type:    {type(ai)}")
print(f"Loaded:  OK")
```

**Expected:** Loads successfully from the scaffolded config.

### 4.2 Policy Hot Reload

```python
# Reload with no changes — should return False
changed = ai.reload_policies()
print(f"Changed: {changed}")
```

**Expected:** `Changed: False`

```python
# Force reload — always returns True
changed = ai.force_reload_policies()
print(f"Force reloaded: {changed}")
```

**Expected:** `Force reloaded: True`

### 4.3 Modify Policy and Reload

```python
import yaml

# Read current policy
with open("policies/default.yaml") as f:
    policy = yaml.safe_load(f)

# Add a new rule: block all PII at input too
policy["policies"].insert(1, {
    "name": "block-pii-at-input",
    "boundary": "input",
    "priority": 15,
    "condition": {"data_tags": ["personal", "personal.pii"]},
    "action": "block",
    "reason": "PII blocked at input for testing."
})

with open("policies/default.yaml", "w") as f:
    yaml.dump(policy, f)

# Reload and verify new rule
changed = ai.force_reload_policies()
print(f"Reloaded: {changed}")

result = ai.scan_input("alice@example.com")
print(f"Action: {result.decision.action}")
# Should now block PII at input
```

**Expected:** After reload, PII is blocked at input because of the new rule.

### 4.4 Restore Original Policy

```python
# Remove the test rule we added
policy["policies"] = [r for r in policy["policies"] if r["name"] != "block-pii-at-input"]
with open("policies/default.yaml", "w") as f:
    yaml.dump(policy, f)
ai.force_reload_policies()
print("Policy restored.")
```

---

## Phase 5: Capability Tokens & Secret Resolution

### 5.1 Issue a Capability Token

```python
token = ai.issue_capability_token(
    agent_id="agent-A",
    tool_name="web_search",
    actions=["invoke"],
    ttl="10m"
)
print(f"Token ID:  {token.token_id}")
print(f"Agent:     {token.agent_id}")
print(f"Tool:      {token.tool_name}")
print(f"Expires:   {token.expires_at}")
```

**Expected:** Returns a token with a unique ID, bound to agent-A and web_search.

### 5.2 Validate the Token (Correct Agent + Tool)

```python
validation = ai.validate_capability_token(
    token.token_id,
    agent_id="agent-A",
    tool_name="web_search"
)
print(f"Valid:  {validation.allowed}")
print(f"Reason: {validation.reason}")
```

**Expected:** `Valid: True`.

### 5.3 Validate with Wrong Agent (Should Fail)

```python
validation = ai.validate_capability_token(
    token.token_id,
    agent_id="agent-B",
    tool_name="web_search"
)
print(f"Valid:  {validation.allowed}")
print(f"Reason: {validation.reason}")
```

**Expected:** `Valid: False`. Reason mentions agent mismatch.

### 5.4 Validate with Wrong Tool (Should Fail)

```python
validation = ai.validate_capability_token(
    token.token_id,
    agent_id="agent-A",
    tool_name="delete_database"
)
print(f"Valid:  {validation.allowed}")
```

**Expected:** `Valid: False`.

### 5.5 Revoke the Token

```python
revoked = ai.revoke_capability_token(token.token_id)
print(f"Revoked: {revoked}")

# Now validate again — should fail
validation = ai.validate_capability_token(
    token.token_id,
    agent_id="agent-A",
    tool_name="web_search"
)
print(f"Valid after revoke: {validation.allowed}")
```

**Expected:** `Revoked: True`. `Valid after revoke: False`.

### 5.6 Purge Expired Tokens

```python
# Issue a short-lived token (1 second)
short_token = ai.issue_capability_token(
    agent_id="agent-A",
    tool_name="test",
    actions=["invoke"],
    ttl="1s"
)

import time
time.sleep(2)

purged = ai.purge_expired_capability_tokens()
print(f"Purged: {purged}")  # Should be >= 1
```

**Expected:** `Purged: >= 1`.

### 5.7 Secret Resolution via Env Backend

```python
import os

# Set an environment variable as our "secret"
os.environ["MY_TEST_SECRET"] = "super-secret-value-12345"

# Register the env backend (may already be registered)
from safeai.secrets import EnvBackend
try:
    ai.register_secret_backend("env", EnvBackend())
except Exception:
    pass  # Already registered

# List backends
backends = ai.list_secret_backends()
print(f"Backends: {backends}")

# Issue a token that grants access to this secret
token = ai.issue_capability_token(
    agent_id="agent-A",
    tool_name="web_search",
    actions=["invoke"],
    ttl="10m",
    secret_keys=["MY_TEST_SECRET"]
)

# Resolve the secret
secret = ai.resolve_secret(
    token_id=token.token_id,
    secret_key="MY_TEST_SECRET",
    agent_id="agent-A",
    tool_name="web_search",
    backend="env"
)
print(f"Resolved: {secret.value}")
```

**Expected:** `Backends: ['env']`. `Resolved: super-secret-value-12345`.

### 5.8 Secret Resolution with Wrong Agent (Should Fail)

```python
try:
    secret = ai.resolve_secret(
        token_id=token.token_id,
        secret_key="MY_TEST_SECRET",
        agent_id="agent-WRONG",
        tool_name="web_search",
        backend="env"
    )
    print("ERROR: Should have raised an exception!")
except Exception as e:
    print(f"Correctly denied: {type(e).__name__}: {e}")
```

**Expected:** Raises an exception (access denied).

---

## Phase 6: Approval Workflow

### 6.1 Add an Approval-Required Policy

```python
import yaml

with open("policies/default.yaml") as f:
    policy = yaml.safe_load(f)

# Add a rule that requires approval for a specific tool
policy["policies"].insert(0, {
    "name": "require-approval-for-delete",
    "boundary": "action",
    "priority": 5,
    "condition": {"tool_name": "delete_record"},
    "action": "require_approval",
    "reason": "Destructive operations need human approval."
})

with open("policies/default.yaml", "w") as f:
    yaml.dump(policy, f)

ai.force_reload_policies()
print("Approval policy added.")
```

### 6.2 Trigger the Approval Gate

```python
result = ai.intercept_tool_request(
    tool_name="delete_record",
    parameters={"record_id": "123"},
    data_tags=[],
    agent_id="agent-A"
)
print(f"Action: {result.decision.action}")
# Should be 'require_approval' or block with pending approval
```

### 6.3 List Pending Approvals

```python
pending = ai.list_approval_requests(status="pending")
print(f"Pending count: {len(pending)}")
if pending:
    req = pending[0]
    print(f"Request ID:  {req.request_id}")
    print(f"Agent:       {req.agent_id}")
    print(f"Tool:        {req.tool_name}")
```

### 6.4 Approve the Request

```python
if pending:
    approved = ai.approve_request(
        pending[0].request_id,
        approver_id="security-admin",
        note="Approved for testing"
    )
    print(f"Approved: {approved}")
```

**Expected:** `Approved: True`.

### 6.5 Deny a Request

```python
# Trigger another approval
result2 = ai.intercept_tool_request(
    tool_name="delete_record",
    parameters={"record_id": "456"},
    data_tags=[],
    agent_id="agent-A"
)
pending2 = ai.list_approval_requests(status="pending")
if pending2:
    denied = ai.deny_request(
        pending2[0].request_id,
        approver_id="security-admin",
        note="Denied for testing"
    )
    print(f"Denied: {denied}")
```

### 6.6 Clean Up Approval Policy

```python
policy["policies"] = [r for r in policy["policies"] if r["name"] != "require-approval-for-delete"]
with open("policies/default.yaml", "w") as f:
    yaml.dump(policy, f)
ai.force_reload_policies()
print("Approval policy removed.")
```

---

## Phase 7: Encrypted Memory

### 7.1 Write and Read Memory

```python
wrote = ai.memory_write("user_email", "alice@example.com", agent_id="agent-A")
print(f"Written: {wrote}")

value = ai.memory_read("user_email", agent_id="agent-A")
print(f"Read back: {value}")
```

**Expected:** `Written: True`. `Read back:` the value (may be an encrypted handle or the raw value depending on config).

### 7.2 Read Non-Existent Key

```python
value = ai.memory_read("nonexistent_key_xyz", agent_id="agent-A")
print(f"Missing key: {value}")
```

**Expected:** `Missing key: None`.

### 7.3 Purge Expired Memory

```python
purged = ai.memory_purge_expired()
print(f"Purged entries: {purged}")
```

**Expected:** Returns an integer (0 if nothing expired).

---

## Phase 8: Audit Log & Query

### 8.1 Query Audit Events

After running the tests above, there should be audit events logged.

```python
events = ai.query_audit(limit=10)
print(f"Event count: {len(events)}")
if events:
    e = events[0]
    print(f"Keys:      {list(e.keys())}")
    print(f"Boundary:  {e.get('boundary')}")
    print(f"Action:    {e.get('action')}")
    print(f"Agent:     {e.get('agent_id')}")
```

**Expected:** Returns a list of dicts. Each event has keys like `event_id`, `timestamp`, `boundary`, `action`, `agent_id`.

### 8.2 Filter by Boundary

```python
input_events = ai.query_audit(boundary="input", limit=5)
print(f"Input events: {len(input_events)}")
for e in input_events:
    assert e["boundary"] == "input", f"Wrong boundary: {e['boundary']}"
print("All correct boundary.")
```

### 8.3 Filter by Action

```python
block_events = ai.query_audit(action="block", limit=5)
print(f"Block events: {len(block_events)}")
```

---

## Phase 9: CLI End-to-End Testing

Run these commands in the terminal from `/tmp/safeai-e2e-test`.

### 9.1 Scan — Block a Secret

```bash
cd /tmp/safeai-e2e-test
safeai scan --config safeai.yaml --boundary input --input "sk-ABCDEF1234567890ABCDEF1234567890ABCDEF12345678"
```

**Expected:** Output shows `block` action with policy `block-secrets-everywhere`.

### 9.2 Scan — Allow Clean Input

```bash
safeai scan --config safeai.yaml --boundary input --input "Hello world"
```

**Expected:** Output shows `allow` action.

### 9.3 Scan — Redact PII in Output

```bash
safeai scan --config safeai.yaml --boundary output --input "Contact alice@example.com"
```

**Expected:** Output shows `redact` action with policy `redact-personal-data-in-output`.

### 9.4 View Audit Logs

```bash
safeai logs --file logs/audit.log --tail 10 --json-output --pretty
```

**Expected:** JSON-formatted audit events from the scans above.

### 9.5 Filter Logs by Boundary

```bash
safeai logs --file logs/audit.log --tail 5 --boundary input
```

**Expected:** Only `input` boundary events shown.

### 9.6 Filter Logs by Action

```bash
safeai logs --file logs/audit.log --tail 5 --action block
```

**Expected:** Only `block` events shown.

### 9.7 List Approval Requests

```bash
safeai approvals list --config safeai.yaml --status all --json-output
```

**Expected:** JSON list of approval requests (if any from Phase 6).

### 9.8 List Policy Templates

```bash
safeai templates list --config safeai.yaml
```

**Expected:** Shows built-in templates: `coding-agent`, `finance`, `healthcare`, `support`.

### 9.9 Show a Template

```bash
safeai templates show --config safeai.yaml --name healthcare --format yaml
```

**Expected:** Prints the healthcare template YAML with HIPAA-oriented rules.

### 9.10 Search Templates

```bash
safeai templates search --query "finance"
```

**Expected:** Returns templates matching "finance".

### 9.11 List Alert Rules

```bash
safeai alerts list --config safeai.yaml
```

**Expected:** Shows configured alert rules from `alerts/default.yaml`.

### 9.12 Add an Alert Rule

```bash
safeai alerts add --config safeai.yaml \
  --rule-id test-high-blocks \
  --name "High Block Rate" \
  --threshold 3 \
  --window 15m \
  --channel file
```

**Expected:** Rule added. Confirm with `safeai alerts list`.

### 9.13 Test Alert Evaluation

```bash
safeai alerts test --config safeai.yaml --last 1h
```

**Expected:** Evaluates rules against recent events. Shows which rules would fire.

### 9.14 Observe Agents

```bash
safeai observe agents --config safeai.yaml --last 24h
```

**Expected:** Lists agent IDs with event counts from recent activity.

### 9.15 Setup for Claude Code

```bash
mkdir -p /tmp/test-setup
safeai setup claude-code --config safeai.yaml --path /tmp/test-setup
```

**Expected:** Installs SafeAI hooks into the target directory for Claude Code integration.

### 9.16 Setup for Cursor

```bash
safeai setup cursor --config safeai.yaml --path /tmp/test-setup
```

**Expected:** Installs hooks for Cursor IDE integration.

### 9.17 Setup Generic

```bash
safeai setup generic --config safeai.yaml
```

**Expected:** Prints generic integration instructions.

### 9.18 Hook — Block Dangerous Tool Call

```bash
echo '{"tool_name":"bash","tool_input":{"command":"rm -rf /"}}' | \
  safeai hook --config safeai.yaml
```

**Expected:** SafeAI intercepts the tool call and applies policy. Output indicates scanning result.

### 9.19 Hook — Allow Safe Tool Call

```bash
echo '{"tool_name":"bash","tool_input":{"command":"echo hello"}}' | \
  safeai hook --config safeai.yaml
```

**Expected:** Tool call passes policy check.

---

## Phase 10: Proxy HTTP API Testing

### 10.1 Start the Proxy Server

```bash
# In a separate terminal:
cd /tmp/safeai-e2e-test
safeai serve --mode sidecar --port 8910 --config safeai.yaml
```

**Expected:** Server starts. Output: `Uvicorn running on http://127.0.0.1:8910`.

Wait a few seconds, then run all curl commands below in another terminal.

### 10.2 Health Check

```bash
curl -s http://localhost:8910/v1/health | python -m json.tool
```

**Expected:**
```json
{
    "status": "ok",
    "mode": "sidecar",
    "version": "0.8.1"
}
```

### 10.3 Scan Input — Block Secret

```bash
curl -s -X POST http://localhost:8910/v1/scan/input \
  -H "Content-Type: application/json" \
  -d '{"text": "sk-ABCDEF1234567890ABCDEF1234567890ABCDEF12345678", "agent_id": "test"}' \
  | python -m json.tool
```

**Expected:** Response contains `"action": "block"`, `"policy_name": "block-secrets-everywhere"`.

### 10.4 Scan Input — Allow Clean

```bash
curl -s -X POST http://localhost:8910/v1/scan/input \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "agent_id": "test"}' \
  | python -m json.tool
```

**Expected:** `"action": "allow"`.

### 10.5 Scan Structured Input

```bash
curl -s -X POST http://localhost:8910/v1/scan/structured \
  -H "Content-Type: application/json" \
  -d '{"payload": {"email": "alice@example.com"}, "agent_id": "test"}' \
  | python -m json.tool
```

**Expected:** Detects email PII in structured payload.

### 10.6 Guard Output — Redact PII

```bash
curl -s -X POST http://localhost:8910/v1/guard/output \
  -H "Content-Type: application/json" \
  -d '{"text": "Contact alice@example.com", "agent_id": "test"}' \
  | python -m json.tool
```

**Expected:** `"action": "redact"`. `safe_output` has email replaced.

### 10.7 Intercept Tool — Block with Secret Tags

```bash
curl -s -X POST http://localhost:8910/v1/intercept/tool \
  -H "Content-Type: application/json" \
  -d '{
    "phase": "request",
    "tool_name": "search",
    "parameters": {"q": "test"},
    "data_tags": ["secret.credential"],
    "agent_id": "test"
  }' | python -m json.tool
```

**Expected:** `"action": "block"`.

### 10.8 Intercept Agent Message

```bash
curl -s -X POST http://localhost:8910/v1/intercept/agent-message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello agent B",
    "source_agent_id": "agent-A",
    "destination_agent_id": "agent-B"
  }' | python -m json.tool
```

**Expected:** `"action": "allow"`. Clean message passes.

### 10.9 Memory Write

```bash
curl -s -X POST http://localhost:8910/v1/memory/write \
  -H "Content-Type: application/json" \
  -d '{"key": "proxy_test_key", "value": "proxy_test_value", "agent_id": "test"}' \
  | python -m json.tool
```

**Expected:** `200 OK`. Memory written.

### 10.10 Memory Read

```bash
curl -s -X POST http://localhost:8910/v1/memory/read \
  -H "Content-Type: application/json" \
  -d '{"key": "proxy_test_key", "agent_id": "test"}' \
  | python -m json.tool
```

**Expected:** Returns the stored value.

### 10.11 Purge Expired Memory

```bash
curl -s -X POST http://localhost:8910/v1/memory/purge-expired | python -m json.tool
```

**Expected:** Returns `{"purged": <count>}`.

### 10.12 Query Audit Logs via API

```bash
curl -s -X POST http://localhost:8910/v1/audit/query \
  -H "Content-Type: application/json" \
  -d '{"boundary": "input", "limit": 5}' \
  | python -m json.tool
```

**Expected:** Returns audit events filtered to input boundary.

### 10.13 Reload Policies via API

```bash
curl -s -X POST http://localhost:8910/v1/policies/reload \
  -H "Content-Type: application/json" \
  -d '{"force": true}' \
  | python -m json.tool
```

**Expected:** `{"reloaded": true}`.

### 10.14 List Policy Templates

```bash
curl -s http://localhost:8910/v1/policies/templates | python -m json.tool
```

**Expected:** JSON array of template objects (healthcare, finance, etc.).

### 10.15 Get Specific Template

```bash
curl -s http://localhost:8910/v1/policies/templates/healthcare | python -m json.tool
```

**Expected:** Full healthcare template YAML rendered as JSON.

### 10.16 List Plugins

```bash
curl -s http://localhost:8910/v1/plugins | python -m json.tool
```

**Expected:** JSON array of loaded plugins.

### 10.17 Prometheus Metrics

```bash
curl -s http://localhost:8910/v1/metrics
```

**Expected:** Prometheus-format text with counters like `safeai_requests_total`, `safeai_decisions_total`.

### 10.18 Intelligence Status

```bash
curl -s http://localhost:8910/v1/intelligence/status | python -m json.tool
```

**Expected:** JSON with intelligence layer status (may show no backend configured if no AI backend set up).

---

## Phase 11: Dashboard & Enterprise Features

All requests below go to the same proxy server started in Phase 10. Dashboard endpoints use RBAC via the `x-safeai-user` header.

### 11.1 Dashboard HTML

```bash
curl -s http://localhost:8910/dashboard | head -20
```

**Expected:** HTML content with SafeAI dashboard structure.

### 11.2 Dashboard Overview

```bash
curl -s "http://localhost:8910/v1/dashboard/overview?last=24h" \
  -H "x-safeai-user: security-admin" \
  | python -m json.tool
```

**Expected:** JSON with event counts, decision breakdown, recent activity.

### 11.3 Query Events via Dashboard

```bash
curl -s -X POST http://localhost:8910/v1/dashboard/events/query \
  -H "Content-Type: application/json" \
  -H "x-safeai-user: security-admin" \
  -d '{"boundary": "input", "limit": 5}' \
  | python -m json.tool
```

**Expected:** Returns filtered events.

### 11.4 List Incidents

```bash
curl -s "http://localhost:8910/v1/dashboard/incidents?last=24h" \
  -H "x-safeai-user: security-admin" \
  | python -m json.tool
```

**Expected:** JSON with incidents (blocks, denials, etc.).

### 11.5 Dashboard Approvals

```bash
curl -s "http://localhost:8910/v1/dashboard/approvals?status=all&limit=10" \
  -H "x-safeai-user: security-admin" \
  | python -m json.tool
```

**Expected:** JSON list of approval requests.

### 11.6 Compliance Report

```bash
curl -s -X POST http://localhost:8910/v1/dashboard/compliance/report \
  -H "Content-Type: application/json" \
  -H "x-safeai-user: security-admin" \
  -d '{"last": "24h"}' \
  | python -m json.tool
```

**Expected:** Compliance report with policy coverage and event summary.

### 11.7 List Tenants

```bash
curl -s http://localhost:8910/v1/dashboard/tenants \
  -H "x-safeai-user: security-admin" \
  | python -m json.tool
```

**Expected:** JSON array with at least a `default` tenant.

### 11.8 Get Tenant Policies

```bash
curl -s http://localhost:8910/v1/dashboard/tenants/default/policies \
  -H "x-safeai-user: security-admin" \
  | python -m json.tool
```

**Expected:** Policies for the default tenant.

### 11.9 Alert Rules via Dashboard

```bash
curl -s http://localhost:8910/v1/dashboard/alerts/rules \
  -H "x-safeai-user: security-admin" \
  | python -m json.tool
```

**Expected:** JSON array of alert rules.

### 11.10 Create Alert Rule via Dashboard

```bash
curl -s -X POST http://localhost:8910/v1/dashboard/alerts/rules \
  -H "Content-Type: application/json" \
  -H "x-safeai-user: security-admin" \
  -d '{
    "rule_id": "dashboard-test-rule",
    "name": "Dashboard Test Rule",
    "threshold": 3,
    "window": "15m",
    "filters": {"actions": ["block"]},
    "channels": ["file"]
  }' | python -m json.tool
```

**Expected:** Rule created successfully.

### 11.11 Evaluate Alerts

```bash
curl -s -X POST http://localhost:8910/v1/dashboard/alerts/evaluate \
  -H "Content-Type: application/json" \
  -H "x-safeai-user: security-admin" \
  -d '{"last": "1h"}' \
  | python -m json.tool
```

**Expected:** Evaluation results showing which rules fired.

### 11.12 Alert History

```bash
curl -s "http://localhost:8910/v1/dashboard/alerts/history?limit=10" \
  -H "x-safeai-user: security-admin" \
  | python -m json.tool
```

**Expected:** JSON array of past alert firings.

### 11.13 Observe Agents via Dashboard

```bash
curl -s "http://localhost:8910/v1/dashboard/observe/agents?last=24h" \
  -H "x-safeai-user: security-admin" \
  | python -m json.tool
```

**Expected:** Agent activity summary.

### 11.14 Observe Metrics

```bash
curl -s http://localhost:8910/v1/dashboard/observe/metrics \
  -H "x-safeai-user: security-admin" \
  | python -m json.tool
```

**Expected:** Agent and tool usage metrics.

### 11.15 Dashboard Templates

```bash
curl -s http://localhost:8910/v1/dashboard/templates \
  -H "x-safeai-user: security-admin" \
  | python -m json.tool
```

**Expected:** Template list.

### 11.16 Search Templates via Dashboard

```bash
curl -s -X POST http://localhost:8910/v1/dashboard/templates/search \
  -H "Content-Type: application/json" \
  -H "x-safeai-user: security-admin" \
  -d '{"query": "healthcare"}' \
  | python -m json.tool
```

**Expected:** Matching templates.

### 11.17 RBAC — Viewer Access (Read-Only)

```bash
# Viewer can read overview
curl -s "http://localhost:8910/v1/dashboard/overview?last=24h" \
  -H "x-safeai-user: security-viewer" \
  | python -m json.tool
```

**Expected:** Returns data (viewer has read access).

```bash
# Viewer cannot approve
curl -s -X POST http://localhost:8910/v1/dashboard/approvals/fake-id/approve \
  -H "Content-Type: application/json" \
  -H "x-safeai-user: security-viewer" \
  -d '{}' | python -m json.tool
```

**Expected:** Access denied or error (viewer cannot approve).

### 11.18 RBAC — Unknown User

```bash
curl -s "http://localhost:8910/v1/dashboard/overview?last=24h" \
  -H "x-safeai-user: unknown-user" \
  | python -m json.tool
```

**Expected:** Access denied or limited access.

---

## Phase 12: Plugins, Adapters, Intelligence & MCP

### 12.1 Plugin System

```python
ai = SafeAI.from_config("safeai.yaml")

# List loaded plugins
plugins = ai.list_plugins()
print(f"Plugins loaded: {len(plugins)}")
for p in plugins:
    print(f"  - {p}")

# List plugin-contributed adapters
adapters = ai.list_plugin_adapters()
print(f"Plugin adapters: {adapters}")
```

**Expected:** Shows plugins loaded from `plugins/*.py`. May include custom detectors, adapters, or templates contributed by the example plugin.

### 12.2 Policy Template Catalog

```python
# List all templates
templates = ai.list_policy_templates()
print(f"Templates: {len(templates)}")
for t in templates:
    print(f"  - {t.get('name', t)}")

# Load a specific template
healthcare = ai.load_policy_template("healthcare")
print(f"\nHealthcare template keys: {list(healthcare.keys())}")

# Search templates
results = ai.search_policy_templates(query="finance")
print(f"\nSearch 'finance': {len(results)} results")

# Install a template to local directory
path = ai.install_policy_template("healthcare")
print(f"Installed to: {path}")
```

**Expected:** 4 built-in templates (coding-agent, finance, healthcare, support). Healthcare template loads with policy rules. Install copies it locally.

### 12.3 LangChain Adapter

```python
ai = SafeAI.quickstart()
adapter = ai.langchain_adapter()
print(f"Adapter type: {type(adapter).__name__}")

# Wrap a function
def my_search(query: str) -> str:
    return f"Results for: {query}"

wrapped = adapter.wrap_tool(my_search, tool_name="search", agent_id="langchain-agent")

# Call with clean input
result = wrapped("weather today")
print(f"Clean call: {result}")

# Call with secret (should be intercepted)
try:
    result = wrapped("key is sk-ABCDEF1234567890ABCDEF1234567890ABCDEF12345678")
    print(f"Secret call: {result}")
except Exception as e:
    print(f"Blocked: {type(e).__name__}: {e}")
```

**Expected:** Clean call returns normally. Secret call is blocked.

### 12.4 CrewAI Adapter

```python
adapter = ai.crewai_adapter()
print(f"CrewAI adapter: {type(adapter).__name__}")
```

**Expected:** Returns a `SafeAICrewAIAdapter` instance.

### 12.5 AutoGen Adapter

```python
adapter = ai.autogen_adapter()
print(f"AutoGen adapter: {type(adapter).__name__}")
```

### 12.6 Claude ADK Adapter

```python
adapter = ai.claude_adk_adapter()
print(f"Claude ADK adapter: {type(adapter).__name__}")
```

### 12.7 Google ADK Adapter

```python
adapter = ai.google_adk_adapter()
print(f"Google ADK adapter: {type(adapter).__name__}")
```

### 12.8 Intelligence Layer — Auto Config

> **Prerequisite:** Set up an AI backend. SafeAI supports Ollama (local) or OpenAI.
>
> For Ollama: `ollama serve` then `ollama pull llama3.2`
> For OpenAI: `export OPENAI_API_KEY=your-key`

```python
# Register an AI backend first
from safeai.intelligence import OllamaBackend  # or OpenAIBackend

ai.register_ai_backend("ollama", OllamaBackend(model="llama3.2"))
print(f"AI backends: {ai.list_ai_backends()}")

# Auto-configure based on project structure
config = ai.intelligence_auto_config(project_path=".", framework_hint="langchain")
print(f"Auto-config result: {type(config)}")
```

**Expected:** Auto-config analyzes the project and generates recommended policies.

### 12.9 Intelligence — Recommendations

```python
recs = ai.intelligence_recommend(since="24h")
print(f"Recommendations: {type(recs)}")
```

**Expected:** AI-generated security recommendations based on recent audit events.

### 12.10 Intelligence — Compliance Mapping

```python
compliance = ai.intelligence_compliance(framework="hipaa")
print(f"Compliance result: {type(compliance)}")
```

**Expected:** Generates HIPAA-oriented policy recommendations.

### 12.11 Intelligence — Integration Generator

```python
integration = ai.intelligence_integrate(target="langchain", project_path=".")
print(f"Integration code: {type(integration)}")
```

**Expected:** Generates boilerplate code for LangChain + SafeAI integration.

### 12.12 Intelligence via CLI

```bash
# Auto-config
safeai intelligence auto-config --path . --output-dir /tmp/intel-test --config safeai.yaml

# Compliance
safeai intelligence compliance --framework hipaa --output-dir /tmp/intel-test --config safeai.yaml

# Integration
safeai intelligence integrate --target langchain --path . --output-dir /tmp/intel-test --config safeai.yaml
```

**Expected:** Each generates files in `/tmp/intel-test`.

### 12.13 Intelligence via Proxy API

```bash
# Status
curl -s http://localhost:8910/v1/intelligence/status | python -m json.tool

# Recommendations
curl -s -X POST http://localhost:8910/v1/intelligence/recommend \
  -H "Content-Type: application/json" \
  -d '{"since": "24h"}' | python -m json.tool

# Compliance
curl -s -X POST http://localhost:8910/v1/intelligence/compliance \
  -H "Content-Type: application/json" \
  -d '{"framework": "hipaa"}' | python -m json.tool
```

### 12.14 MCP Server

```bash
# Start MCP server (uses stdio transport)
safeai mcp --config safeai.yaml
```

**Expected:** MCP server starts and listens on stdin/stdout. It exposes SafeAI tools (scan_input, guard_output, intercept_tool, etc.) as MCP tools that any MCP-compatible client can call.

To test interactively, send a JSON-RPC request via stdin:

```json
{"jsonrpc": "2.0", "method": "tools/list", "id": 1}
```

**Expected response:** List of available MCP tools.

---

## Phase 13: Edge Cases & Stress Testing

### 13.1 Empty Input

```python
ai = SafeAI.quickstart()
result = ai.scan_input("")
print(f"Empty input action: {result.decision.action}")
```

**Expected:** `allow` — empty string has nothing to detect.

### 13.2 Unicode with Embedded Secret

```python
result = ai.scan_input("こんにちは sk-ABCDEF1234567890ABCDEF1234567890ABCDEF12345678")
print(f"Unicode action: {result.decision.action}")
print(f"Detections:     {len(result.detections)}")
```

**Expected:** `block` — secret detected even with Unicode prefix.

### 13.3 Very Long Input

```python
long_input = "x" * 10000 + " sk-ABCDEF1234567890ABCDEF1234567890ABCDEF12345678"
result = ai.scan_input(long_input)
print(f"Long input action: {result.decision.action}")
```

**Expected:** `block` — secret at end of 10KB string is still detected.

### 13.4 Deeply Nested Structured Input

```python
nested = {"level1": {"level2": {"level3": {"level4": {"email": "deep@example.com"}}}}}
result = ai.scan_structured_input(nested, agent_id="test")
print(f"Deep nested detections: {len(result.detections)}")
```

**Expected:** Email detected at level 4.

### 13.5 Concurrent Scanning

```python
import concurrent.futures

ai = SafeAI.quickstart()

def scan_one(i):
    return ai.scan_input(f"Test message {i}")

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(scan_one, i) for i in range(100)]
    results = [f.result() for f in futures]

allowed = sum(1 for r in results if r.decision.action == "allow")
print(f"100 concurrent scans: {allowed} allowed")
```

**Expected:** All 100 return `allow` without errors.

---

## Cleanup

```bash
# Stop the proxy server (Ctrl+C in that terminal)

# Remove test artifacts
rm -rf /tmp/safeai-e2e-test /tmp/intel-test /tmp/test-setup

# Deactivate virtual environment
deactivate
```

---

## Success Criteria Summary

| Area | What to Verify |
|------|---------------|
| **Installation** | `pip install safeai-sdk[all]` works, `safeai --help` runs |
| **Init/Validate** | Scaffolds 8+ files, validates without errors |
| **7 Detectors** | API key, AWS key, generic token, email, phone, SSN, credit card all detect |
| **3 Boundaries** | Input (scan), Action (intercept), Output (guard) all enforce policy |
| **4 Actions** | allow, block, redact, require_approval all work |
| **Policy Engine** | YAML loading, priority ordering, hot reload, hierarchical tags |
| **Secrets** | Env backend resolution, token-scoped access, wrong-agent denial |
| **Tokens** | Issue, validate, revoke, purge lifecycle |
| **Approvals** | Create, list, approve, deny workflow |
| **Memory** | Write, read, encrypted handles, purge expired |
| **Audit** | Events logged, queryable by boundary/action/agent |
| **CLI** | All 30+ commands execute without crashes |
| **Proxy** | All 22 endpoints return correct status codes |
| **Dashboard** | All 23 endpoints respond, RBAC enforced |
| **RBAC** | Admin=full, viewer=read-only, unknown=denied |
| **5 Adapters** | LangChain, CrewAI, AutoGen, Claude ADK, Google ADK |
| **Plugins** | Load, register detectors/adapters/templates |
| **4 Templates** | coding-agent, finance, healthcare, support |
| **Intelligence** | auto-config, recommend, explain, compliance, integrate |
| **MCP** | Server starts, exposes tools via stdio |
| **Edge Cases** | Empty, unicode, long, nested, concurrent all handled |
