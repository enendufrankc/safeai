# SafeAI: system design document (SDD)

## 1. Architecture overview

SafeAI is a runtime control layer that intercepts AI agent data flows at three boundary points (input, action, output) and enforces declarative security policies. It is designed as a composable system deployable as an in-process SDK, a local sidecar, or a centralized gateway.

### High-level architecture

```
                    ┌─────────────────────────────────────────────┐
                    │              SafeAI Control Layer            │
                    │                                             │
 User/System ──▶   │  ┌─────────┐  ┌──────────┐  ┌───────────┐  │  ──▶ User/System
                    │  │  Input  │  │  Action   │  │  Output   │  │
                    │  │ Scanner │  │Interceptor│  │  Guard    │  │
                    │  └────┬────┘  └─────┬─────┘  └─────┬─────┘  │
                    │       │             │              │         │
                    │       ▼             ▼              ▼         │
                    │  ┌──────────────────────────────────────┐   │
                    │  │          Policy Engine               │   │
                    │  └──────────────────────────────────────┘   │
                    │       │             │              │         │
                    │       ▼             ▼              ▼         │
                    │  ┌──────────┐ ┌──────────┐ ┌────────────┐  │
                    │  │Classifier│ │ Memory   │ │   Audit    │  │
                    │  │          │ │Controller│ │   Logger   │  │
                    │  └──────────┘ └──────────┘ └────────────┘  │
                    │                                             │
                    └─────────────────────────────────────────────┘
                                        │
                                        ▼
                              ┌──────────────────┐
                              │  Secret Backend  │
                              │  (Vault, Env,    │
                              │   AWS SM, etc.)  │
                              └──────────────────┘
```

### Deployment modes

```
Mode 1: SDK (In-Process)                Mode 2: Sidecar
┌──────────────────────┐                ┌──────────┐    ┌──────────┐
│    Agent Process     │                │  Agent   │◄──▶│ SafeAI   │
│  ┌────────────────┐  │                │ Process  │    │ Sidecar  │
│  │   Agent Code   │  │                └──────────┘    └──────────┘
│  │       │        │  │
│  │  ┌────▼─────┐  │  │                Mode 3: Gateway
│  │  │ SafeAI   │  │  │                ┌──────────┐
│  │  │Middleware │  │  │       Agents──▶│ SafeAI   │──▶ Tools
│  │  └──────────┘  │  │                │ Gateway  │
│  └────────────────┘  │                └──────────┘
└──────────────────────┘
```

## 2. Component design

### 2.1 Input scanner

The input scanner classifies and filters data entering the AI system.

Interface:
```python
class InputScanner:
    def scan(self, data: InputData) -> ScanResult:
        """Classify input, apply policies, return filtered data."""

class ScanResult:
    original: InputData
    classified: list[Detection]     # What was found
    filtered: InputData             # Data after policy application
    decision: Decision              # allow | redact | block
    audit_event: AuditEvent
```

Processing pipeline:
1. Receive raw input (text, structured data, file reference)
2. Run classifiers to detect sensitive patterns
3. Tag detections with data categories
4. Evaluate input policies against tags
5. Apply policy action (pass through, redact, block)
6. Emit audit event
7. Return filtered input

Classifiers:
- Pattern classifiers: compiled regex for emails, phone numbers, SSNs, credit cards, API keys
- Custom classifiers: user-defined regex patterns from policy files
- Structural classifiers: JSON path-aware classification for structured data

### 2.2 Action interceptor

The action interceptor validates and controls tool calls and agent-to-agent messages.

Interface:
```python
class ActionInterceptor:
    def intercept_request(self, call: ToolCall) -> InterceptResult:
        """Validate tool call against contracts and policies."""

    def intercept_response(self, call: ToolCall, response: ToolResponse) -> FilteredResponse:
        """Filter tool response before agent receives it."""

class ToolCall:
    tool_name: str
    agent_id: str
    parameters: dict
    data_tags: list[str]

class InterceptResult:
    decision: Decision              # allow | block | require_approval
    filtered_params: dict           # Parameters after policy application
    capability_token: str | None    # Injected credential reference
    audit_event: AuditEvent
```

Processing pipeline (request):
1. Receive tool call from agent
2. Look up tool contract
3. Validate parameter data tags against contract's accepted tags
4. Evaluate action policies
5. If capability-based: inject ephemeral credential
6. If approval required: pause and wait for human decision
7. Emit audit event
8. Forward allowed call to tool

Processing pipeline (response):
1. Receive tool response
2. Classify response fields
3. Strip fields with tags not authorized for the calling agent
4. Emit audit event
5. Return filtered response to agent

### 2.3 Output guard

The output guard is the final check before data leaves the system.

Interface:
```python
class OutputGuard:
    def guard(self, output: OutputData) -> GuardResult:
        """Scan output, apply policies, return safe response."""

class GuardResult:
    original: OutputData
    classified: list[Detection]
    safe_output: OutputData         # Output after policy application
    decision: Decision
    fallback_used: bool
    audit_event: AuditEvent
```

Processing pipeline:
1. Receive agent output
2. Run classifiers
3. Evaluate output policies
4. Apply action: pass through, redact sensitive segments, or block and use fallback
5. Emit audit event
6. Return safe output

### 2.4 Policy engine

The policy engine evaluates policies against request context to produce decisions.

Design:
- Pure function: `evaluate(context, policies) -> decision`
- Stateless, no side effects during evaluation
- Deterministic, same input always produces same output

Interface:
```python
class PolicyEngine:
    def evaluate(self, context: PolicyContext) -> PolicyDecision:
        """Evaluate all matching policies and return decision."""

    def load(self, policy_files: list[Path]) -> None:
        """Load and validate policy files."""

    def reload(self) -> None:
        """Hot-reload policy files."""

class PolicyContext:
    boundary: str                   # input | action | output
    data_tags: list[str]
    agent_id: str
    tool_name: str | None
    action_type: str | None

class PolicyDecision:
    action: str                     # allow | redact | block | require_approval
    policy_name: str
    reason: str
```

Evaluation order:
1. Collect all policies matching the boundary type
2. Filter by condition match (data tags, tool name, agent ID)
3. Apply first matching policy (explicit ordering)
4. If no policy matches, apply default-deny

### 2.5 Data classifier

The data classifier detects and tags sensitive data in text and structured content.

Architecture:
```python
class Classifier:
    def classify(self, data: str | dict) -> list[Detection]:
        """Run all active detectors against data."""

class Detection:
    detector: str                   # Which detector found it
    tag: str                        # Data tag (personal, secret, etc.)
    location: Location              # Where in the data
    confidence: float               # 0.0 to 1.0
```

Detector types:
- Built-in: pre-compiled regex patterns for common PII and secrets
- Custom: user-defined regex patterns from policy files
- Structural: JSON field path matching for structured data

### 2.6 Memory controller

The memory controller enforces schema-based memory writes and retention.

Interface:
```python
class MemoryController:
    def write(self, key: str, value: Any, agent_id: str) -> WriteResult:
        """Validate and write to memory if schema allows."""

    def read(self, key: str, agent_id: str) -> Any:
        """Read from memory with access control."""

    def purge_expired(self) -> int:
        """Remove expired entries. Returns count purged."""
```

Enforcement:
- Memory schema loaded from YAML
- Writes to undefined fields are silently dropped
- Fields tagged `secret` or `personal` are stored as encrypted handles
- Background purge runs on configurable interval

### 2.7 Audit logger

The audit logger records all boundary decisions for compliance and debugging.

Design:
- Append-only log
- Structured JSON format
- Never contains raw sensitive data (only tags, hashes, and decisions)
- Pluggable backends (file, stdout, database, cloud logging)

Event schema:
```json
{
  "timestamp": "2026-02-19T14:23:01Z",
  "event_id": "evt_7f3k9x2m",
  "boundary": "output",
  "agent_id": "support-bot",
  "policy_name": "no-secrets-in-output",
  "action": "blocked",
  "data_tags": ["secret"],
  "tool_name": null,
  "context_hash": "sha256:abc123...",
  "reason": "Secrets must never cross any boundary"
}
```

## 3. Data flow

### Standard request flow (SDK mode)

```
User Input
    │
    ▼
Input Scanner ──classify──▶ Policy Engine ──decision──▶ allow/redact/block
    │                                                        │
    ▼ (filtered input)                                       │
Agent Reasoning                                              │
    │                                                        │
    ▼                                                        │
Tool Call ──▶ Action Interceptor ──▶ Policy Engine ──▶ allow/block/approve
    │              │                                         │
    │              ▼ (inject capability)                     │
    │         Tool Execution                                 │
    │              │                                         │
    │              ▼                                         │
    │         Response Filter ──▶ strip unauthorized fields   │
    │              │                                         │
    ▼ (filtered response)                                    │
Agent Reasoning                                              │
    │                                                        │
    ▼                                                        │
Output ──▶ Output Guard ──▶ Policy Engine ──▶ allow/redact/block
    │                                              │
    ▼ (safe output)                                │
User Response                                Audit Logger
```

## 4. Technology stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Core library | Python 3.10+ | Ecosystem alignment with AI/ML |
| Policy files | YAML | Human-readable, version-controllable |
| Pattern matching | `re` (compiled) | Fast, no dependencies |
| Schema validation | Pydantic | Type safety, automatic validation |
| HTTP proxy (sidecar/gateway) | FastAPI + uvicorn | Async, fast, Python-native |
| Audit logging | structlog | Structured, pluggable |
| CLI | Click | Clean, well-tested |
| Testing | pytest | Standard Python testing |
| Configuration | pydantic-settings | Type-safe config loading |

## 5. Performance design

Target: < 50ms overhead per boundary crossing.

Strategies:
- Compiled regex patterns (loaded once, reused)
- Policy evaluation is a simple loop over matched rules (no complex query engine)
- Classification runs synchronously in-process (no network calls)
- No LLM calls for enforcement decisions
- Stateless policy evaluation enables horizontal scaling
- Audit logging is async (non-blocking)

## 6. Failure modes

| Failure | Behavior | Rationale |
|---------|----------|-----------|
| Policy file invalid | Reject load, keep previous policies | Never run without valid policies |
| Classifier error | Block the crossing, log error | Fail closed, not open |
| Audit backend unavailable | Buffer locally, retry | Don't block requests for logging |
| Secret backend unavailable | Block capability-gated actions | No credentials means no access |
| Memory backend unavailable | Reject memory writes | Don't lose data silently |

Fail closed. When in doubt, block and log.

## 7. Security of SafeAI itself

- SafeAI does not store raw sensitive data in its own logs or state
- Configuration files should be treated as sensitive (they contain policy logic)
- The control layer should run with minimal OS-level privileges
- TLS is required for sidecar and gateway modes in production
- SafeAI's own dependencies are minimized and auditable
