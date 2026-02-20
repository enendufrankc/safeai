# SafeAI: UX/UI design document

## 1. Design philosophy

SafeAI is primarily a developer tool. Its primary interfaces are:
- A Python SDK (code-level integration)
- CLI tools (local development and testing)
- YAML configuration files (policies, schemas, contracts)
- A web dashboard (observability and management, post-MVP)

The design principle across all interfaces: invisible when working, clear when intervening.

## 2. Information architecture

### Developer-facing (SDK + CLI)

```
SafeAI
├── Installation & Setup
│   ├── pip install
│   ├── Quick start (first policy in 5 minutes)
│   └── Framework integration guides
├── Configuration
│   ├── Policy files (YAML)
│   ├── Tool contracts (YAML)
│   ├── Memory schemas (YAML)
│   └── Secret backends
├── SDK Reference
│   ├── Middleware / decorators
│   ├── Boundary interceptors
│   ├── Classification API
│   └── Audit log API
├── CLI Tools
│   ├── safeai init (scaffold config)
│   ├── safeai validate (check policies)
│   ├── safeai scan (test input/output)
│   ├── safeai logs (query audit trail)
│   └── safeai serve (run as local proxy)
└── Guides
    ├── Writing your first policy
    ├── Defining tool contracts
    ├── Setting up approval workflows
    └── Integrating with [framework]
```

### Security team-facing (dashboard, post-MVP)

```
Dashboard
├── Overview
│   ├── Active agents
│   ├── Policy violations (24h)
│   └── Approval queue
├── Policies
│   ├── Active policies (list)
│   ├── Policy editor
│   └── Policy test simulator
├── Audit Log
│   ├── Search & filter
│   ├── Event detail view
│   └── Export
├── Agents
│   ├── Registered agents (list)
│   ├── Agent detail (permissions, tools, recent activity)
│   └── Tool contracts
└── Settings
    ├── Classification rules
    ├── Notification channels
    └── Secret backend config
```

## 3. Screens and interactions

### 3.1 CLI: `safeai init`

Purpose: scaffold a SafeAI configuration for an existing project.

Flow:
1. Developer runs `safeai init` in their project root
2. Interactive prompts ask:
   - What framework are you using? (LangChain / Claude ADK / Google ADK / Custom / None)
   - What data sensitivity level? (Low / Medium / High)
   - Enable audit logging? (Yes / No)
3. Generates:
   - `safeai.yaml` — main config with sensible defaults
   - `policies/default.yaml` — starter policy set
   - `contracts/` — directory for tool contracts
   - `schemas/` — directory for memory schemas

Output example:
```
SafeAI initialized successfully.

Created:
  safeai.yaml           — main configuration
  policies/default.yaml — starter policies (5 rules)
  contracts/            — add tool contracts here
  schemas/              — add memory schemas here

Next steps:
  1. Review policies/default.yaml
  2. Add tool contracts for your agents
  3. Wrap your agent with SafeAI middleware

Run `safeai validate` to check your configuration.
```

### 3.2 CLI: `safeai scan`

Purpose: test how SafeAI would handle specific inputs or outputs.

Flow:
1. Developer provides input text: `safeai scan --input "My email is john@example.com and my SSN is 123-45-6789"`
2. SafeAI classifies and applies policies
3. Shows what would happen

Output example:
```
Input Scan Results
──────────────────
Original: "My email is john@example.com and my SSN is 123-45-6789"

Detections:
  [1] Email address (personal) at position 12-28
  [2] SSN (personal) at position 44-55

Policy applied: no-personal-data-in-input
Action: redact

Result: "My email is [REDACTED] and my SSN is [REDACTED]"
```

### 3.3 CLI: `safeai logs`

Purpose: query and view the audit trail.

Flow:
1. Developer runs `safeai logs --last 1h --action blocked`
2. Shows recent blocked events

Output example:
```
Audit Log (last 1h, action: blocked)
─────────────────────────────────────
TIME                 BOUNDARY  POLICY                    AGENT        TAGS
2026-02-19 14:23:01  output    no-secrets-in-output      support-bot  [secret]
2026-02-19 14:19:44  action    email-requires-approval   hr-agent     [personal]
2026-02-19 14:15:22  input     block-raw-credentials     user-input   [secret]

3 events found. Run `safeai logs --detail <id>` for full context.
```

### 3.4 SDK: middleware integration

Purpose: developers wrap their agent's tool execution with SafeAI middleware.

Integration pattern (conceptual):

```python
from safeai import SafeAI, Policy

# Initialize with config
safeai = SafeAI.from_config("safeai.yaml")

# Wrap tool execution
@safeai.guard
def call_tool(tool_name, params):
    return tool_registry[tool_name].execute(params)

# Or use as middleware
agent = MyAgent(
    tools=[...],
    middleware=[safeai.middleware()]
)
```

What developers see when SafeAI blocks something:

```python
# In development mode - detailed error
SafeAIBlockedError: Policy 'no-secrets-in-output' blocked output
  Boundary: output
  Tags detected: [secret]
  Reason: Secrets must never cross any boundary
  Audit ID: evt_7f3k9x2m

# In production mode - safe fallback
"I cannot share that information. Let me help you differently."
```

### 3.5 Dashboard: overview (post-MVP)

Purpose: at-a-glance view of AI security posture.

Layout:
```
┌──────────────────────────────────────────────────────────┐
│  SafeAI Dashboard                              Settings  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Active Agents: 12        Policies: 23       Uptime: 99.9%│
│                                                          │
│  ┌─────────────────────┐  ┌────────────────────────────┐ │
│  │ Last 24 Hours       │  │ Approval Queue (3)         │ │
│  │                     │  │                            │ │
│  │ Requests:  45,201   │  │ ▸ HR agent: send offer     │ │
│  │ Allowed:   44,892   │  │ ▸ Deploy bot: push staging │ │
│  │ Redacted:     287   │  │ ▸ Support: share invoice   │ │
│  │ Blocked:       22   │  │                            │ │
│  │ Approvals:      8   │  │ [Review All]               │ │
│  └─────────────────────┘  └────────────────────────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Recent Policy Violations                             │ │
│  │                                                      │ │
│  │ 14:23  output  support-bot  secret detected  BLOCKED │ │
│  │ 14:19  action  hr-agent     email approval   PENDING │ │
│  │ 14:15  input   user-input   credentials      BLOCKED │ │
│  │ 13:58  output  analyst-bot  PII detected     REDACTED│ │
│  │                                                      │ │
│  │ [View Full Audit Log →]                              │ │
│  └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### 3.6 Dashboard: approval workflow (post-MVP)

Purpose: human approvers review and approve or deny high-risk agent actions.

Layout:
```
┌──────────────────────────────────────────────────────────┐
│  Approval Request #req_8k2m                              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Agent: hr-agent                                         │
│  Action: send_email                                      │
│  Triggered by: email-requires-approval                   │
│  Time: 2026-02-19 14:19:44                               │
│                                                          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Context                                              │ │
│  │                                                      │ │
│  │ Recipient: jane.doe@company.com                      │ │
│  │ Subject: "Your offer letter"                         │ │
│  │ Data tags: [personal, confidential]                  │ │
│  │ Attachment: offer_letter_JD_2026.pdf                 │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                          │
│  [Approve]  [Deny]  [Approve with conditions ▾]         │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## 4. Design system

### Colors
- Primary: Deep navy (#1a1a2e) — trust, stability
- Accent: Teal (#16c79a) — allowed/safe states
- Warning: Amber (#f5a623) — redacted/flagged states
- Error: Coral (#e74c3c) — blocked states
- Background: Near-white (#f8f9fa) for dashboard, terminal default for CLI

### Typography
- CLI: Monospace (terminal default)
- Dashboard: Inter (headers), JetBrains Mono (code/data)
- Documentation: System font stack

### Tone of voice

Calm, direct, technical. No exclamation marks in error messages. Errors explain what happened and what to do next. Never blame the user or the agent.

Good: "Policy 'no-secrets-in-output' blocked this response. The output contained data tagged as 'secret'. Review your policy or the tool contract."

Bad: "WARNING! DANGEROUS OUTPUT DETECTED! SafeAI saved you from a data breach!"

## 5. Accessibility

- CLI output uses semantic formatting (not color-only indicators)
- Dashboard meets WCAG 2.1 AA standards
- All interactive elements are keyboard-navigable
- Error messages are screen-reader friendly
- High-contrast mode available for dashboard

## 6. Developer experience priorities

1. First run to first value: under 10 minutes
2. Policy iteration: edit YAML, see results immediately (hot reload)
3. Debugging: clear error messages with audit IDs that link to full context
4. Testing: `safeai scan` lets developers test policies without running agents
5. Documentation: every error message links to relevant docs
