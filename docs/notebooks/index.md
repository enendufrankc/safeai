# Interactive Notebooks

SafeAI ships 11 Jupyter notebooks that demonstrate every major feature with runnable examples. Each notebook is self-contained and includes inline explanations alongside executable code.

[:octicons-mark-github-16: Browse all notebooks on GitHub](https://github.com/enendufrankc/safeai/tree/main/notebook/){ .md-button .md-button--primary }

---

## Notebook Catalog

### 01 -- API Call Test

**Zero-config quickstart with real Gemini API integration.**

Demonstrates SafeAI scanning a live Gemini API call end-to-end with no prior configuration. Shows how boundary enforcement works transparently on real model traffic.

[:octicons-file-code-16: `api_call_test.ipynb`](https://github.com/enendufrankc/safeai/tree/main/notebook/api_call_test.ipynb)

---

### 02 -- Structured Scanning

**Nested JSON payload and file scanning.**

Walks through scanning structured data -- nested dictionaries, lists, and file content -- using `scan_structured_input` and `scan_file_input`. Covers field-level detection and enforcement on complex payloads.

[:octicons-file-code-16: `structured_scanning.ipynb`](https://github.com/enendufrankc/safeai/tree/main/notebook/structured_scanning.ipynb)

---

### 03 -- Policy Engine

**Rules, priorities, tag hierarchies, and hot reload.**

Deep dive into the policy engine: writing rules, setting priorities, using hierarchical data tags (e.g., `personal` matching `personal.pii`), and hot-reloading policy files without restarting.

[:octicons-file-code-16: `policy_engine.ipynb`](https://github.com/enendufrankc/safeai/tree/main/notebook/policy_engine.ipynb)

---

### 04 -- Memory Controller

**Encrypted agent memory with schemas and auto-expiry.**

Shows how to store and retrieve encrypted memory entries with schema validation, per-agent isolation, retention policies, and automatic expiry purge.

[:octicons-file-code-16: `memory_controller.ipynb`](https://github.com/enendufrankc/safeai/tree/main/notebook/memory_controller.ipynb)

---

### 05 -- Tool Interception

**Tool contracts, agent identity, and field-level filtering.**

Demonstrates defining tool contracts with input/output schemas, binding tools to agent identities with clearance tags, and filtering response fields based on agent permissions.

[:octicons-file-code-16: `tool_interception.ipynb`](https://github.com/enendufrankc/safeai/tree/main/notebook/tool_interception.ipynb)

---

### 06 -- Approval Workflow

**Human-in-the-loop approval gates.**

End-to-end walkthrough of the approval workflow: configuring `require_approval` policies, creating approval requests, listing pending requests, and approving or denying them programmatically.

[:octicons-file-code-16: `approval_workflow.ipynb`](https://github.com/enendufrankc/safeai/tree/main/notebook/approval_workflow.ipynb)

---

### 07 -- Audit Logging

**Full decision trail with query filters.**

Explores the audit log system: capturing every boundary decision, querying by boundary type, action, agent, time range, and retrieving full event detail by ID.

[:octicons-file-code-16: `audit_logging.ipynb`](https://github.com/enendufrankc/safeai/tree/main/notebook/audit_logging.ipynb)

---

### 08 -- Agent Messaging

**Agent-to-agent message interception.**

Demonstrates scanning and enforcing policies on messages exchanged between agents in multi-agent systems. Covers source/destination context and gateway-mode enforcement.

[:octicons-file-code-16: `agent_messaging.ipynb`](https://github.com/enendufrankc/safeai/tree/main/notebook/agent_messaging.ipynb)

---

### 09 -- Capability Tokens

**Scoped, time-limited secret access tokens.**

Shows how to issue capability tokens with fine-grained scopes and TTLs, resolve secrets through the token system, and audit secret access without exposing payloads.

[:octicons-file-code-16: `capability_tokens.ipynb`](https://github.com/enendufrankc/safeai/tree/main/notebook/capability_tokens.ipynb)

---

### 10 -- Hook Adapter

**Universal hook adapter and agent profiles.**

Walks through the hook adapter system: defining agent profiles, registering SafeAI as a pre-execution hook for coding agents, and processing tool calls through the boundary engine.

[:octicons-file-code-16: `hook_adapter.ipynb`](https://github.com/enendufrankc/safeai/tree/main/notebook/hook_adapter.ipynb)

---

### 11 -- Proxy Server

**REST API sidecar with TestClient.**

Demonstrates running the SafeAI proxy server in-process using FastAPI's TestClient. Covers all major proxy endpoints: input scan, output guard, tool interception, memory, audit, and metrics.

[:octicons-file-code-16: `proxy_server.ipynb`](https://github.com/enendufrankc/safeai/tree/main/notebook/proxy_server.ipynb)

---

## Running the Notebooks

```bash
# Install SafeAI with notebook dependencies
pip install safeai[all]

# Launch Jupyter
jupyter notebook notebook/
```

!!! tip
    Each notebook initializes its own SafeAI instance with inline configuration, so you can run them independently in any order.
