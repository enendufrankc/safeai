# SafeAI User-End-to-End Test Plan

This guide is for testing SafeAI the way a normal user would actually encounter it:

1. get access to SafeAI
2. install it into a fresh environment
3. use it through the SDK and CLI
4. scaffold a real project
5. run the proxy and dashboard
6. integrate it into agents and supported frameworks
7. use templates, plugins, skills, approvals, alerts, and intelligence
8. optionally build it from source and run the full repository verification

This document is intentionally split into:

- `User path`: install and use SafeAI from scratch
- `Optional external integrations`: only needed for features backed by outside systems
- `Source-build path`: only needed if you want to build or validate the repository itself

If your goal is "test SafeAI exactly like a normal user", follow Phases 1 through 8 first.

## Feature Coverage Goal

The complete user-facing feature surface in this repository includes:

- Python package install and CLI
- SDK quickstart and full config mode
- policy engine
- input scanning
- output guarding
- structured payload scanning
- file scanning
- tool interception
- agent identity and agent-message interception
- approvals
- secret backends abstraction
- memory security
- audit logging and query
- proxy runtime
- dashboard
- alerts and observability
- templates and marketplace
- plugins
- coding-agent hook integration
- framework adapters: LangChain, CrewAI, AutoGen, Claude ADK, Google ADK
- MCP server
- intelligence commands
- skills system

Some features can be fully exercised locally. Others require optional external services. This guide marks those clearly.

## Phase 1: Get SafeAI Like a Normal User

You have two realistic user entry paths:

1. `Package user`
   Install from PyPI and use SafeAI immediately.
2. `Source user / builder`
   Clone the repository, install editable, and build with it.

Do the package-user path first.

### 1.1 Package-user install

Create a fresh virtual environment:

```bash
python3.12 -m venv ~/.venvs/safeai-user-test
source ~/.venvs/safeai-user-test/bin/activate

python -V
which python
```

Install the package from PyPI:

```bash
python -m pip install --upgrade pip
python -m pip install "safeai-sdk[all]"
```

Why `[all]`:

- includes Vault support
- includes AWS support
- includes MCP support

Sanity check:

```bash
python -c "from safeai import SafeAI; print('SafeAI imported OK')"
python -m safeai.cli.main --help
python -m pip show questionary
```

Expected:

- import works
- CLI help renders
- `questionary` is installed

### 1.2 Source-user install

Only do this if you also want to build with SafeAI or validate the repository itself.

```bash
git clone https://github.com/enendufrankc/safeai.git
cd safeai

python3.12 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[dev,all,docs]"

python -c "from safeai import SafeAI; print('SafeAI imported OK')"
python -m safeai.cli.main --help
```

## Phase 2: First-Time CLI and Project Setup

This is the first realistic user workflow after install.

### 2.1 Check the CLI surface

```bash
python -m safeai.cli.main --help
python -m safeai.cli.main init --help
python -m safeai.cli.main validate --help
python -m safeai.cli.main scan --help
python -m safeai.cli.main logs --help
python -m safeai.cli.main serve --help
python -m safeai.cli.main approvals --help
python -m safeai.cli.main templates --help
python -m safeai.cli.main hook --help
python -m safeai.cli.main setup --help
python -m safeai.cli.main mcp --help
python -m safeai.cli.main intelligence --help
python -m safeai.cli.main alerts --help
python -m safeai.cli.main observe --help
python -m safeai.cli.main skills --help
```

Expected:

- every command group renders help
- no import-time crash occurs

### 2.2 Scaffold a new SafeAI project

```bash
rm -rf /tmp/safeai-user-e2e
mkdir -p /tmp/safeai-user-e2e

python -m safeai.cli.main init --path /tmp/safeai-user-e2e --non-interactive
python -m safeai.cli.main validate --config /tmp/safeai-user-e2e/safeai.yaml
```

Expected files:

- `/tmp/safeai-user-e2e/safeai.yaml`
- `/tmp/safeai-user-e2e/policies/default.yaml`
- `/tmp/safeai-user-e2e/contracts/example.yaml`
- `/tmp/safeai-user-e2e/schemas/memory.yaml`
- `/tmp/safeai-user-e2e/agents/default.yaml`
- `/tmp/safeai-user-e2e/plugins/example.py`
- `/tmp/safeai-user-e2e/tenants/policy-sets.yaml`
- `/tmp/safeai-user-e2e/alerts/default.yaml`

## Phase 3: Use SafeAI Through the SDK

This is the core runtime user experience.

### 3.1 Quickstart mode

```bash
python - <<'PY'
from safeai import SafeAI

ai = SafeAI.quickstart()

scan = ai.scan_input("token=sk-ABCDEF1234567890ABCDEF")
print("scan_input:", scan.decision.action)

guard = ai.guard_output("Contact alice@example.com")
print("guard_output:", guard.decision.action, guard.safe_output)

structured = ai.scan_structured_input(
    {"request": {"token": "sk-ABCDEF1234567890ABCDEF", "message": "deploy"}},
    agent_id="default-agent",
)
print("scan_structured_input:", structured.decision.action)
PY
```

Expected:

- secret input is blocked
- output email is redacted
- structured secret is blocked

### 3.2 Full config mode

```bash
python - <<'PY'
from pathlib import Path
from safeai import SafeAI

sdk = SafeAI.from_config(Path("/tmp/safeai-user-e2e/safeai.yaml"))

scan = sdk.scan_input("token=sk-ABCDEF1234567890ABCDEF")
print("scan_input:", scan.decision.action, scan.decision.policy_name)

guard = sdk.guard_output("Contact alice@example.com")
print("guard_output:", guard.decision.action, guard.safe_output)

structured = sdk.scan_structured_input(
    {"request": {"token": "sk-ABCDEF1234567890ABCDEF", "message": "deploy"}},
    agent_id="default-agent",
)
print("scan_structured_input:", structured.decision.action)

from pathlib import Path as P
tmp_file = P("/tmp/safeai-user-e2e/sample.json")
tmp_file.write_text('{"token":"sk-ABCDEF1234567890ABCDEF"}', encoding="utf-8")
file_result = sdk.scan_file_input(str(tmp_file), agent_id="default-agent")
print("scan_file_input:", file_result["decision"]["action"])

print("memory_write:", sdk.memory_write("user_preference", "en-US", agent_id="default-agent"))
print("memory_read:", sdk.memory_read("user_preference", agent_id="default-agent"))
print("audit_events:", len(sdk.query_audit(limit=20)))
PY
```

Expected:

- input secret blocked
- output email redacted
- structured secret blocked
- file secret blocked
- memory write succeeds
- memory read returns data
- audit events exist

## Phase 4: Use SafeAI Through the CLI

### 4.1 Scan and logs

```bash
python -m safeai.cli.main scan --config /tmp/safeai-user-e2e/safeai.yaml --boundary input --input "token=sk-ABCDEF1234567890ABCDEF"
python -m safeai.cli.main scan --config /tmp/safeai-user-e2e/safeai.yaml --boundary output --input "Contact alice@example.com"
python -m safeai.cli.main logs --file /tmp/safeai-user-e2e/logs/audit.log --tail 10 --json-output
```

### 4.2 Templates

```bash
python -m safeai.cli.main templates list --config /tmp/safeai-user-e2e/safeai.yaml
python -m safeai.cli.main templates show --config /tmp/safeai-user-e2e/safeai.yaml --name healthcare --format yaml
python -m safeai.cli.main templates search --category compliance
```

### 4.3 Alerts and observe

```bash
python -m safeai.cli.main alerts list --config /tmp/safeai-user-e2e/safeai.yaml
python -m safeai.cli.main observe agents --config /tmp/safeai-user-e2e/safeai.yaml --last 24h
python -m safeai.cli.main observe sessions --config /tmp/safeai-user-e2e/safeai.yaml --session sess-demo
```

Expected:

- scans return meaningful allow/block/redact output
- logs return JSON audit rows
- templates list built-in entries
- alerts and observe commands run without crashing

## Phase 5: Proxy, API, Dashboard, Approvals, and Operations

This is the full service-user path.

### 5.1 Start the proxy

```bash
python -m safeai.cli.main serve --mode sidecar --host 127.0.0.1 --port 8910 --config /tmp/safeai-user-e2e/safeai.yaml
```

### 5.2 Exercise core HTTP endpoints

In a second terminal:

```bash
curl -s http://127.0.0.1:8910/v1/health | python -m json.tool

curl -s -X POST http://127.0.0.1:8910/v1/scan/input \
  -H "content-type: application/json" \
  -d '{"text":"token=sk-ABCDEF1234567890ABCDEF","agent_id":"default-agent"}' | python -m json.tool

curl -s -X POST http://127.0.0.1:8910/v1/scan/structured \
  -H "content-type: application/json" \
  -d '{"payload":{"request":{"token":"sk-ABCDEF1234567890ABCDEF","message":"deploy"}},"agent_id":"default-agent"}' | python -m json.tool

curl -s -X POST http://127.0.0.1:8910/v1/guard/output \
  -H "content-type: application/json" \
  -d '{"text":"Contact alice@example.com","agent_id":"default-agent"}' | python -m json.tool

curl -s -X POST http://127.0.0.1:8910/v1/intercept/tool \
  -H "content-type: application/json" \
  -d '{"phase":"request","tool_name":"send_email","parameters":{"to":"ops@example.com","subject":"S","body":"B","priority":"high"},"data_tags":["internal"],"agent_id":"default-agent"}' | python -m json.tool

curl -s -X POST http://127.0.0.1:8910/v1/intercept/tool \
  -H "content-type: application/json" \
  -d '{"phase":"response","tool_name":"send_email","response":{"status":"sent","message_id":"m-1","recipient":"alice@example.com"},"data_tags":["internal"],"agent_id":"default-agent"}' | python -m json.tool

curl -s -X POST http://127.0.0.1:8910/v1/intercept/agent-message \
  -H "content-type: application/json" \
  -d '{"message":"Need approval context for deployment","source_agent_id":"planner-agent","destination_agent_id":"executor-agent","data_tags":["internal"],"session_id":"sess-gateway"}' | python -m json.tool

curl -s -X POST http://127.0.0.1:8910/v1/memory/write \
  -H "content-type: application/json" \
  -d '{"key":"user_preference","value":"en-US","agent_id":"default-agent"}' | python -m json.tool

curl -s -X POST http://127.0.0.1:8910/v1/memory/read \
  -H "content-type: application/json" \
  -d '{"key":"user_preference","agent_id":"default-agent"}' | python -m json.tool

curl -s -X POST http://127.0.0.1:8910/v1/audit/query \
  -H "content-type: application/json" \
  -d '{"boundary":"action","limit":50}' | python -m json.tool

curl -s -X POST http://127.0.0.1:8910/v1/policies/reload \
  -H "content-type: application/json" \
  -d '{"force":true}' | python -m json.tool

curl -s http://127.0.0.1:8910/v1/plugins | python -m json.tool
curl -s http://127.0.0.1:8910/v1/policies/templates | python -m json.tool
curl -s http://127.0.0.1:8910/v1/policies/templates/finance | python -m json.tool
curl -s http://127.0.0.1:8910/v1/metrics
curl -s http://127.0.0.1:8910/dashboard | head -20
```

Expected:

- health is OK
- scans behave correctly
- request filtering strips unapproved fields
- response filtering strips sensitive fields
- agent messaging works
- memory works
- audit query returns entries
- policy reload succeeds
- plugin/template endpoints return data
- metrics endpoint exposes Prometheus-style text
- dashboard loads

### 5.3 Approval workflow

Add a rule requiring approval:

```bash
python - <<'PY'
from pathlib import Path
import yaml

policy_path = Path("/tmp/safeai-user-e2e/policies/default.yaml")
doc = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
doc["policies"].insert(0, {
    "name": "email-requires-approval",
    "boundary": ["action"],
    "priority": 5,
    "condition": {"tools": ["send_email"], "data_tags": ["internal"]},
    "action": "require_approval",
    "reason": "send email approval gate",
})
policy_path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
PY
```

Create a pending request:

```bash
python - <<'PY'
from pathlib import Path
from safeai import SafeAI

sdk = SafeAI.from_config(Path("/tmp/safeai-user-e2e/safeai.yaml"))
result = sdk.intercept_tool_request(
    "send_email",
    {"to": "ops@example.com", "subject": "S", "body": "B"},
    data_tags=["internal"],
    agent_id="default-agent",
    session_id="sess-approval",
)
print(result.decision.action)
rows = sdk.list_approval_requests(status="pending", limit=10)
print(rows[0].request_id)
PY
```

Approve and verify:

```bash
python -m safeai.cli.main approvals list --config /tmp/safeai-user-e2e/safeai.yaml --status pending --json-output
python -m safeai.cli.main approvals approve <REQUEST_ID> --config /tmp/safeai-user-e2e/safeai.yaml --approver security-oncall --note "approved"
python -m safeai.cli.main approvals deny does-not-exist --config /tmp/safeai-user-e2e/safeai.yaml --approver security-oncall --note "negative-test"
```

Expected:

- pending request is created
- approval works
- denial of a fake ID fails cleanly

## Phase 6: Agents, Coding Hooks, and Framework Integrations

This phase tests the "use SafeAI with agents and frameworks" story.

### 6.1 Coding-agent setup commands

```bash
python -m safeai.cli.main setup generic --config /tmp/safeai-user-e2e/safeai.yaml
python -m safeai.cli.main setup claude-code --config /tmp/safeai-user-e2e/safeai.yaml --path /tmp/safeai-user-e2e
python -m safeai.cli.main setup cursor --config /tmp/safeai-user-e2e/safeai.yaml --path /tmp/safeai-user-e2e
```

Verify installed files:

- `/tmp/safeai-user-e2e/.claude/settings.json`
- `/tmp/safeai-user-e2e/.cursor/rules`

### 6.2 Hook adapter

Safe command:

```bash
printf '%s' '{"tool_name":"Bash","tool_input":{"command":"echo hello"},"event":"pre_tool_use"}' | \
python -m safeai.cli.main hook --config /tmp/safeai-user-e2e/safeai.yaml --profile claude-code
echo $?
```

Blocked command:

```bash
printf '%s' '{"tool_name":"Bash","tool_input":{"command":"export KEY=sk-ABCDEF1234567890ABCDEF"},"event":"pre_tool_use"}' | \
python -m safeai.cli.main hook --config /tmp/safeai-user-e2e/safeai.yaml --profile claude-code
echo $?
```

Expected:

- safe input exits `0`
- secret input exits non-zero and prints `BLOCKED`

### 6.3 Framework adapter smoke tests

Run this exact script:

```bash
python - <<'PY'
from pathlib import Path
from safeai import SafeAI

sdk = SafeAI.from_config(Path("/tmp/safeai-user-e2e/safeai.yaml"))

def send_email(**kwargs):
    return {"status": "sent", "message_id": "msg-1", "recipient": "alice@example.com"}

for name, adapter in [
    ("langchain", sdk.langchain_adapter()),
    ("crewai", sdk.crewai_adapter()),
    ("autogen", sdk.autogen_adapter()),
]:
    wrapped = adapter.wrap_tool(
        "send_email",
        send_email,
        agent_id="default-agent",
        request_data_tags=["internal"],
    )
    result = wrapped(to="ops@example.com", subject="S", body="B", priority="high")
    print(name, result)
PY
```

Expected:

- request field `priority` is stripped before tool execution
- response field `recipient` is stripped before returning

### 6.4 Claude ADK and Google ADK

Primary verification for these is automated in:

- `tests/test_claude_adk_adapter.py`
- `tests/test_google_adk_adapter.py`

As a user smoke test, at minimum verify the package imports and adapter accessors work in your environment:

```bash
python - <<'PY'
from pathlib import Path
from safeai import SafeAI

sdk = SafeAI.from_config(Path("/tmp/safeai-user-e2e/safeai.yaml"))
print(hasattr(sdk, "claude_adk_adapter"))
print(hasattr(sdk, "google_adk_adapter"))
PY
```

## Phase 7: Plugins, Templates, Marketplace, Skills, and MCP

These are the extension surfaces normal advanced users care about.

### 7.1 Built-in plugin and template discovery

```bash
curl -s http://127.0.0.1:8910/v1/plugins | python -m json.tool
curl -s http://127.0.0.1:8910/v1/policies/templates | python -m json.tool
```

### 7.2 Local plugin starter

Confirm the scaffolded starter exists:

```bash
ls -la /tmp/safeai-user-e2e/plugins/example.py
python -c "import runpy; runpy.run_path('/tmp/safeai-user-e2e/plugins/example.py')"
```

### 7.3 Skills system

List and search:

```bash
python -m safeai.cli.main skills list --project-path /tmp/safeai-user-e2e
python -m safeai.cli.main skills search secret --project-path /tmp/safeai-user-e2e
python -m safeai.cli.main skills search gdpr --project-path /tmp/safeai-user-e2e
```

Install and remove one registry skill:

```bash
python -m safeai.cli.main skills add prompt-injection-shield --project-path /tmp/safeai-user-e2e
python -m safeai.cli.main skills list --project-path /tmp/safeai-user-e2e
python -m safeai.cli.main skills remove prompt-injection-shield --project-path /tmp/safeai-user-e2e
```

Expected:

- skill search returns results if network access is available
- add installs files into the project
- remove cleans them up

### 7.4 Template marketplace over network

```bash
python -m safeai.cli.main templates search --category compliance
python -m safeai.cli.main templates install healthcare-hipaa
```

This requires network access.

### 7.5 MCP

Help check:

```bash
python -m safeai.cli.main mcp --help
```

Run the server:

```bash
python -m safeai.cli.main mcp --config /tmp/safeai-user-e2e/safeai.yaml
```

To fully validate MCP as a normal user, connect with an MCP-capable client and invoke:

- `scan_input`
- `guard_output`
- `scan_structured`
- `query_audit`
- `list_policies`
- `check_tool`

## Phase 8: Intelligence Layer

This feature is user-facing but requires an AI backend. It is not a pure local feature.

### 8.1 Help and disabled behavior

```bash
python -m safeai.cli.main intelligence --help
python -m safeai.cli.main intelligence auto-config --help
python -m safeai.cli.main intelligence recommend --help
python -m safeai.cli.main intelligence explain --help
python -m safeai.cli.main intelligence compliance --help
python -m safeai.cli.main intelligence integrate --help
```

### 8.2 Live intelligence with Ollama

Prerequisite:

```bash
ollama serve
ollama pull llama3.2
```

Configure `safeai.yaml` with:

- `intelligence.enabled: true`
- `intelligence.backend.provider: ollama`
- `intelligence.backend.base_url: http://localhost:11434`
- `intelligence.backend.model: llama3.2`

Then run:

```bash
python -m safeai.cli.main intelligence auto-config --path /tmp/safeai-user-e2e --output-dir /tmp/safeai-user-e2e/.safeai-generated --config /tmp/safeai-user-e2e/safeai.yaml
python -m safeai.cli.main intelligence recommend --since 7d --output-dir /tmp/safeai-user-e2e/.safeai-generated --config /tmp/safeai-user-e2e/safeai.yaml
python -m safeai.cli.main intelligence compliance --framework hipaa --output-dir /tmp/safeai-user-e2e/.safeai-generated --config /tmp/safeai-user-e2e/safeai.yaml
python -m safeai.cli.main intelligence integrate --target langchain --path /tmp/safeai-user-e2e --output-dir /tmp/safeai-user-e2e/.safeai-generated --config /tmp/safeai-user-e2e/safeai.yaml
```

Also verify proxy intelligence endpoints:

```bash
curl -s http://127.0.0.1:8910/v1/intelligence/status | python -m json.tool
```

## Phase 9: External Service Features

These features are part of SafeAI, but cannot be fully validated without external infrastructure.

### 9.1 Vault backend

Requires:

- a real Vault server
- valid auth
- test secrets

### 9.2 AWS Secrets Manager backend

Requires:

- valid AWS credentials
- test secrets in AWS

### 9.3 Marketplace and skills registry network access

Requires:

- internet access

## Phase 10: Source Build and Full Repository Verification

Only do this if you want to verify the repository implementation itself, not just the installed user experience.

### 10.1 Static checks

```bash
cd /Users/frank.enendu/Documents/Projects/SafeAI
source .venv/bin/activate

python -m compileall safeai tests
python -m ruff check safeai tests
python -m mypy safeai
python -m mkdocs build --strict
```

### 10.2 Automated test suite

Run both:

```bash
python -m unittest discover -s tests -v
pytest tests -q
```

You need both because `pytest` collects additional pytest-style tests that `unittest discover` does not.

## Pass Criteria

You can say "I tested SafeAI like a normal user across all implemented features" only if:

1. package installation works in a fresh environment
2. project scaffolding works
3. SDK quickstart and config mode work
4. CLI commands work
5. proxy and dashboard work
6. approvals work
7. coding-agent setup and hook flow work
8. framework adapter smoke tests work
9. skills/templates/plugins discovery works
10. MCP help and startup work
11. intelligence help works, and live intelligence works if you configured a backend
12. external-service-backed features are tested where infrastructure exists

If you also want to verify the repo itself, complete Phase 10.

## Known Gotchas

- If `safeai --help` fails but `python -m safeai.cli.main --help` works, your shell is using the wrong CLI entrypoint.
- intelligence features require a configured backend
- skills and marketplace features require network access
- Vault and AWS features require real external services for live testing
- `unittest discover` alone does not cover every test file in this repository

## Short Version

If you want the shortest real user path:

```bash
python3.12 -m venv ~/.venvs/safeai-user-test
source ~/.venvs/safeai-user-test/bin/activate
python -m pip install --upgrade pip
python -m pip install "safeai-sdk[all]"
python -m safeai.cli.main --help
python -m safeai.cli.main init --path /tmp/safeai-user-e2e --non-interactive
python -m safeai.cli.main validate --config /tmp/safeai-user-e2e/safeai.yaml
python -m safeai.cli.main serve --mode sidecar --host 127.0.0.1 --port 8910 --config /tmp/safeai-user-e2e/safeai.yaml
```

Then complete Phases 3 through 8.
