# CLI Reference

SafeAI ships a single `safeai` command with subcommands for scanning, serving, auditing, and managing your safety configuration.

```bash
uv pip install safeai
safeai --help
```

---

## `safeai init`

Scaffold a `.safeai/` configuration directory in the current project.

```bash
safeai init
```

This creates:

| Path | Purpose |
|------|---------|
| `.safeai/safeai.yaml` | Main configuration file |
| `.safeai/policies/` | Policy rule files |
| `.safeai/schemas/` | Memory and contract schemas |
| `.safeai/agents/` | Agent identity documents |
| `.safeai/plugins/example.py` | Plugin starter template |
| `.safeai/tenants/` | Multi-tenant policy sets |
| `.safeai/alerts/` | Alert rule definitions |

!!! tip
    Run `safeai init` at the root of every repository that uses AI agents. The scaffold provides safe defaults that you can customize incrementally.

---

## `safeai scan`

Scan text through the SafeAI boundary engine and return the enforcement decision.

```bash
safeai scan --boundary <BOUNDARY> --input <TEXT>
```

### Flags

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--boundary` | `input \| output` | Yes | Which boundary to evaluate |
| `--input` | string | Yes | The text payload to scan |

### Examples

```bash
# Scan an input prompt for secrets and PII
safeai scan --boundary input --input "My SSN is 123-45-6789"

# Scan model output before returning to a user
safeai scan --boundary output --input "Here is the API key: sk-abc123..."
```

The command prints the enforcement result (allow, block, redact, or flag) along with any matched detections.

---

## `safeai validate`

Validate your SafeAI configuration files: policies, schemas, memory definitions, and agent identity documents.

```bash
safeai validate --config <PATH>
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--config` | path | `.safeai/safeai.yaml` | Path to the SafeAI config file |

### Examples

```bash
# Validate the default config
safeai validate

# Validate a specific config file
safeai validate --config /etc/safeai/production.yaml
```

Output includes counts of policies loaded, memory schemas validated, and agent identity documents found.

!!! warning
    Always run `safeai validate` in CI before deploying configuration changes. Invalid policies can cause unexpected enforcement behavior at runtime.

---

## `safeai logs`

Query the audit log for boundary enforcement decisions.

```bash
safeai logs [FLAGS]
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--tail` | int | `20` | Number of recent events to return |
| `--boundary` | `input \| output \| action` | all | Filter by boundary type |
| `--action` | `allow \| block \| redact \| flag` | all | Filter by enforcement action |
| `--agent` | string | all | Filter by agent name |
| `--last` | duration | all time | Time window (e.g., `1h`, `30m`, `7d`) |
| `--text-output` | flag | off | Plain-text table output (default is JSON) |
| `--detail` | string | -- | Show full detail for a specific event ID |

### Examples

```bash
# Last 20 events, JSON output
safeai logs

# Last 10 block decisions in the past hour, plain text
safeai logs --tail 10 --action block --last 1h --text-output

# Filter by agent and boundary
safeai logs --agent research-agent --boundary input --tail 50

# Full detail for a specific event
safeai logs --detail evt_a1b2c3d4
```

!!! info
    Audit events include `event_id`, `context_hash`, session/source/destination IDs, matched policy, detection tags, and the enforcement action taken.

---

## `safeai serve`

Start the SafeAI proxy server in sidecar or gateway mode.

```bash
safeai serve [FLAGS]
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--mode` | `sidecar \| gateway` | `sidecar` | Proxy operating mode |
| `--port` | int | `8000` | Port to listen on |
| `--config` | path | `.safeai/safeai.yaml` | Path to the SafeAI config file |

### Modes

- **Sidecar** -- Runs alongside a single agent process. All traffic from that agent passes through SafeAI for scanning and enforcement.
- **Gateway** -- Sits between multiple agents and upstream services. Requires source/destination agent context on each request for multi-agent enforcement.

### Examples

```bash
# Start a sidecar on the default port
safeai serve

# Start a gateway on port 9000 with a custom config
safeai serve --mode gateway --port 9000 --config /etc/safeai/prod.yaml
```

!!! note
    The proxy exposes a full REST API surface including `/v1/scan/input`, `/v1/scan/output`, `/v1/tools/intercept`, `/v1/memory/*`, `/v1/audit/logs`, `/v1/metrics`, and more. See the [Proxy / Sidecar guide](../integrations/proxy-sidecar.md) for full endpoint documentation.

---

## `safeai hook`

Universal coding-agent hook. This command reads a pending tool call from stdin, enforces SafeAI policies, and returns the decision.

```bash
safeai hook
```

The hook is designed to be called by coding agents (Claude Code, Cursor, etc.) as a pre-execution gate. It:

1. Reads the tool name and arguments from stdin (JSON).
2. Loads the agent profile for the calling agent.
3. Evaluates the action against configured policies and tool contracts.
4. Returns `allow`, `block`, or `require_approval` with an explanation.

!!! tip
    You do not need to invoke `safeai hook` manually. Use `safeai setup` to install it automatically for your coding agent.

---

## `safeai setup`

Install SafeAI hooks into a supported coding agent.

```bash
safeai setup <AGENT>
```

### Supported agents

| Agent | Command |
|-------|---------|
| Claude Code | `safeai setup claude-code` |
| Cursor | `safeai setup cursor` |

### Examples

```bash
# Install the hook for Claude Code
safeai setup claude-code

# Install the hook for Cursor
safeai setup cursor
```

The installer registers `safeai hook` as the pre-execution callback in the agent's configuration, so every tool invocation is evaluated by SafeAI before execution.

---

## `safeai approvals`

Manage the human-in-the-loop approval workflow for actions that require explicit authorization.

```bash
safeai approvals <SUBCOMMAND> [FLAGS]
```

### Subcommands

| Subcommand | Description |
|------------|-------------|
| `list` | Show pending approval requests |
| `approve` | Approve a pending request by ID |
| `deny` | Deny a pending request by ID |

### Examples

```bash
# List all pending approvals
safeai approvals list

# Approve a specific request
safeai approvals approve req_abc123

# Deny a specific request with a reason
safeai approvals deny req_def456 --reason "Outside permitted scope"
```

!!! info "How approvals work"
    When a policy rule sets `action: require_approval`, the tool call is paused and an approval request is created. The agent cannot proceed until a human operator approves or denies the request via this command or the dashboard UI.

---

## `safeai templates`

Browse and inspect the built-in policy template catalog.

```bash
safeai templates <SUBCOMMAND>
```

### Subcommands

| Subcommand | Description |
|------------|-------------|
| `list` | List all available policy templates |
| `show TEMPLATE` | Display the full content of a named template |

### Examples

```bash
# List all templates (built-in + plugins)
safeai templates list

# Show the healthcare template pack
safeai templates show healthcare

# Show the finance template
safeai templates show finance
```

Built-in template packs include `finance`, `healthcare`, and `support`. Plugin-provided templates are discovered automatically when plugins are loaded.

---

## `safeai mcp`

Start the SafeAI MCP (Model Context Protocol) server for tool-based integration with MCP-compatible clients.

```bash
safeai mcp
```

The MCP server exposes SafeAI's scanning, policy evaluation, and audit capabilities as MCP tools, allowing MCP-compatible agents and IDEs to call SafeAI directly through the protocol.

!!! note
    The MCP server uses stdio transport by default and is intended to be launched by an MCP client, not run standalone.

---

## `safeai intelligence`

AI advisory commands for configuration generation, policy recommendations, incident explanation, compliance mapping, and integration code generation.

```bash
safeai intelligence <SUBCOMMAND> [FLAGS]
```

### Subcommands

| Subcommand | Description |
|------------|-------------|
| `auto-config` | Generate SafeAI configuration from project structure |
| `recommend` | Suggest policy improvements from audit data |
| `explain` | Classify and explain a security incident |
| `compliance` | Generate compliance policy sets |
| `integrate` | Generate framework-specific integration code |

### `auto-config`

```bash
safeai intelligence auto-config [--path .] [--framework langchain] [--output-dir .safeai-generated] [--apply] [--config safeai.yaml]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--path` | path | `.` | Project path to analyze |
| `--framework` | string | auto-detect | Framework hint (e.g., langchain, crewai) |
| `--output-dir` | path | `.safeai-generated` | Directory for generated files |
| `--apply` | flag | off | Copy generated files to project root |
| `--config` | path | `safeai.yaml` | Path to safeai.yaml |

### `recommend`

```bash
safeai intelligence recommend [--since 7d] [--output-dir .safeai-generated] [--config safeai.yaml]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--since` | duration | `7d` | Time window for audit analysis |
| `--output-dir` | path | `.safeai-generated` | Directory for generated files |
| `--config` | path | `safeai.yaml` | Path to safeai.yaml |

### `explain`

```bash
safeai intelligence explain <EVENT_ID> [--config safeai.yaml]
```

Takes a single event ID as argument and prints the classification and explanation.

### `compliance`

```bash
safeai intelligence compliance --framework <FRAMEWORK> [--output-dir .safeai-generated] [--config safeai.yaml]
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--framework` | `hipaa\|pci-dss\|soc2\|gdpr` | Yes | Compliance framework to map |
| `--output-dir` | path | No | Directory for generated files |
| `--config` | path | No | Path to safeai.yaml |

### `integrate`

```bash
safeai intelligence integrate --target <FRAMEWORK> [--path .] [--output-dir .safeai-generated] [--config safeai.yaml]
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--target` | string | Yes | Target framework (langchain, crewai, autogen, etc.) |
| `--path` | path | No | Project path |
| `--output-dir` | path | No | Directory for generated files |
| `--config` | path | No | Path to safeai.yaml |

!!! warning "Requires AI backend"
    All intelligence commands require `intelligence.enabled: true` in `safeai.yaml` and a configured AI backend. See the [Intelligence Layer guide](../guides/intelligence.md) for setup instructions.
