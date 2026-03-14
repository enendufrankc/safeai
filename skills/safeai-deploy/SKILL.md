---
name: safeai-deploy
description: >
  Deploys and configures SafeAI as a zero-trust security layer in any target project.
  Covers the full deployment lifecycle: installing SafeAI, scaffolding config (safeai init),
  auto-generating tailor-made policies and contracts via the intelligence layer
  (safeai intelligence auto-config --apply), and applying agent bindings — either the
  MCP server (safeai mcp) for compatible hosts or native agent hooks (safeai setup) for
  Claude Code, Cursor, or generic agents. Use when the user wants to add SafeAI to a
  project, set up zero-trust runtime security, protect tool calls with boundary enforcement,
  configure SafeAI for Claude Code, Cursor, or any autonomous agent, deploy the SafeAI
  MCP server, generate security policies for a codebase, or integrate SafeAI into
  LangChain, CrewAI, AutoGen, or Claude ADK projects.
tier: stable
owner: SafeAI Contributors
domain: security
functional-area: ai-safety
---

# SafeAI Deploy Skill

Deploys SafeAI as a zero-trust security layer into any project in three phases:

1. **Init** — scaffold config files and project structure
2. **Intelligence** — auto-generate policies and contracts tuned to the codebase
3. **Agent Bindings** — wire up MCP server or native hooks for the target agent

## Deployment Script

Use `scripts/deploy_safeai.py` for the full automated deployment. It handles all three phases end-to-end.

```bash
# Full deployment (interactive — detects agent type automatically)
python scripts/deploy_safeai.py --project-path /path/to/project

# Non-interactive with explicit agent binding
python scripts/deploy_safeai.py --project-path /path/to/project \
  --agent claude-code \
  --binding mcp          # or: hooks

# Skip intelligence auto-config (use default policies only)
python scripts/deploy_safeai.py --project-path /path/to/project --no-intelligence
```

**Script phases:**
1. Verify/install safeai-sdk
2. `safeai init` — scaffold `safeai.yaml`, `policies/`, `contracts/`, `agents/`, `schemas/`, `plugins/`
3. `safeai intelligence auto-config --apply` — LLM-generated policies/contracts written to project root
4. Agent binding — MCP or hooks based on `--agent` / `--binding`

## Manual Step-by-Step

### Phase 1: Init

```bash
cd /path/to/project
safeai init
```

Creates: `safeai.yaml`, `policies/default.yaml`, `contracts/`, `agents/`, `schemas/`, `plugins/`, `logs/`

### Phase 2: Intelligence Auto-Config

```bash
safeai intelligence auto-config --path . --apply
```

Analyzes the codebase and writes generated artifacts to `.safeai-generated/` then copies them to the project root. Requires the `intelligence` section in `safeai.yaml` to be configured with a provider and API key env var.

**Configure intelligence backend in `safeai.yaml`:**
```yaml
intelligence:
  enabled: true
  provider: openai          # openai | anthropic | ollama
  model: gpt-4o             # or claude-opus-4-6, llama3, etc.
  base_url: null            # set for ollama: http://localhost:11434
  api_key_env: OPENAI_API_KEY
  metadata_only: true       # never sends raw data to LLM — only metadata
```

### Phase 3: Agent Bindings

#### Option A — MCP Server (for MCP-compatible hosts)

```bash
safeai mcp --config safeai.yaml
```

Add to your MCP host config (e.g., Claude Desktop `claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "safeai": {
      "command": "safeai",
      "args": ["mcp", "--config", "/path/to/project/safeai.yaml"]
    }
  }
}
```

MCP tools available: `scan_input`, `guard_output`, `scan_structured`, `query_audit`, `list_policies`, `check_tool`

#### Option B — Native Agent Hooks

**Claude Code:**
```bash
safeai setup claude-code --config safeai.yaml --path .
```
Writes `.claude/settings.json` with `PreToolUse` and `PostToolUse` hooks.

**Cursor:**
```bash
safeai setup cursor --config safeai.yaml --path .
```
Writes `.cursor/rules` with SafeAI enforcement rules.

**Generic (any agent via stdio):**
```bash
safeai setup generic --config safeai.yaml
# Pipe tool call JSON to: safeai hook --config safeai.yaml
echo '{"event":"pre_tool_use","tool_name":"Bash","tool_input":{"command":"ls"}}' | safeai hook
```

## Hook Event Format

The `safeai hook` command reads JSON from stdin:
```json
{
  "event": "pre_tool_use",
  "agent_id": "claude-code",
  "tool_name": "Bash",
  "tool_input": {"command": "git push --force"},
  "tool_output": null
}
```
Exit codes: `0` = allow, `1` = block, `2` = error

## Verifying Deployment

```bash
# Validate config files
safeai validate

# Test a scan
safeai scan "My SSN is 123-45-6789"

# Check audit log
safeai logs --last 20
```

## Local Observability Endpoint

Pass `--observability` to start a local monitoring server alongside the deployment:

```bash
python deploy_safeai.py --project-path . --observability --obs-port 8910
```

This configures and starts `safeai serve`, exposing:

| Endpoint | Purpose |
|----------|---------|
| `http://localhost:8910/dashboard` | HTML security operations dashboard (approval queue, incidents, compliance) |
| `GET /v1/health` | Health check + per-agent request counts |
| `GET /v1/metrics` | Prometheus-format metrics (request counts, decision actions, latency histograms) |
| `POST /v1/audit/query` | Queryable audit log (filter by agent, tool, tag, time range, session) |
| `GET /v1/dashboard/observe/agents` | Agent activity timeline |
| `GET /v1/dashboard/observe/sessions/{id}` | Full session event trace |
| `GET /v1/dashboard/overview` | KPI summary (events, blocks, redactions, approvals) |
| `GET /v1/dashboard/incidents` | Policy violation list |
| `GET /v1/dashboard/approvals` | Pending approval queue |
| `GET /v1/intelligence/status` | Intelligence backend health |

Alert channels can be configured at deploy time:
```bash
python deploy_safeai.py --project-path . --observability \
  --slack-webhook https://hooks.slack.com/... \
  --webhook-url https://my-siem.internal/ingest
```

Manual start (after deployment):
```bash
safeai serve --host 127.0.0.1 --port 8910 --config safeai.yaml
# or use the generated script:
./start-safeai-obs.sh
```

For full observability reference (Prometheus metrics, audit query examples, alert rules, dashboard RBAC):
- `references/observability.md`

## Integration Patterns

For SDK/framework integrations (LangChain, CrewAI, AutoGen, Claude ADK), see:
- `references/integration-patterns.md` — code snippets for each framework

For policy and contract authoring, see:
- `references/policy-contracts.md` — policy schema, action types, example files

## Key Config Sections

| Section | Purpose |
|---------|---------|
| `paths` | Glob patterns for policy/contract/schema/agent/plugin files |
| `intelligence` | AI backend for auto-config |
| `audit` | Audit log path |
| `approvals` | Approval workflow settings |
| `plugins` | Plugin discovery (custom detectors/adapters/templates) |
| `alerting` | Alert channels (Slack, webhook, email) |
| `dashboard` | Web UI (RBAC, users, alert rules) |

## Important Behaviors

- **Default-deny**: All boundaries block by default; policies explicitly allow
- **Tag-based**: Detector → data tags → policy matching (not line-by-line scanning)
- **Three boundaries**: Input (scan_input), Action (intercept_tool_request), Output (guard_output)
- **Hot-reload**: Policies reload on file change — no restart needed
- **Metadata-only intelligence**: LLM never receives raw secrets or PII, only structural metadata
