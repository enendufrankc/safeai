# CrewAI Integration

Wrap CrewAI tools so every agent action in your crew passes through SafeAI's policy engine -- secret detection, PII filtering, tool contracts, and audit logging are enforced transparently.

---

## Install

```bash
uv pip install safeai crewai
```

---

## Quick Start

```python
from safeai import SafeAI

ai = SafeAI()
adapter = ai.crewai_adapter()
safe_tool = adapter.wrap_tool("search", search_tool, agent_id="researcher")
```

---

## Detailed Usage

### Creating the Adapter

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")
adapter = ai.crewai_adapter()   # returns SafeAICrewAIAdapter
```

You can also import the adapter directly:

```python
from safeai.middleware.crewai import SafeAICrewAIAdapter
```

### Wrapping Tools

```python
from crewai.tools import BaseTool

class SearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Search the web for information"

    def _run(self, query: str) -> str:
        return f"Results for: {query}"

search_tool = SearchTool()

# Wrap with SafeAI
safe_search = adapter.wrap_tool(
    name="web_search",
    tool=search_tool,
    agent_id="researcher",
)
```

!!! info "Request and response interception"
    The adapter intercepts both the **request** (tool input) and the **response** (tool output). Inputs are scanned before execution; outputs are guarded before they reach the agent.

### Wrapping All Tools for a Crew

```python
from crewai import Agent, Task, Crew

tools = [SearchTool(), AnalyzeTool(), WriteTool()]

# Wrap every tool in one pass
safe_tools = [
    adapter.wrap_tool(t.name, t, agent_id="analyst")
    for t in tools
]

agent = Agent(
    role="Research Analyst",
    goal="Find and analyze data",
    tools=safe_tools,            # drop-in replacement
)
```

---

## Full Example

```python
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from safeai import SafeAI

# 1. SafeAI setup
ai = SafeAI.from_config("safeai.yaml")
adapter = ai.crewai_adapter()

# 2. Define a tool
class DatabaseQuery(BaseTool):
    name: str = "db_query"
    description: str = "Query the production database"

    def _run(self, sql: str) -> str:
        # ... execute query ...
        return "query results"

# 3. Wrap the tool
safe_db = adapter.wrap_tool("db_query", DatabaseQuery(), agent_id="data-agent")

# 4. Build the crew
researcher = Agent(
    role="Data Researcher",
    goal="Extract insights from the database",
    tools=[safe_db],
)

task = Task(
    description="Find top customers by revenue",
    agent=researcher,
    expected_output="A ranked list of customers",
)

crew = Crew(agents=[researcher], tasks=[task])
result = crew.kickoff()
```

!!! warning "Dangerous queries are blocked"
    If the agent tries to pass a SQL injection or leak credentials through the tool, SafeAI blocks the call and logs the violation -- the crew continues with the remaining safe tools.

---

## Configuration

```yaml
# safeai.yaml
policy:
  default_action: block
  secret_detection:
    enabled: true
  pii_protection:
    enabled: true
    action: redact

tool_contracts:
  db_query:
    allowed_agents: ["data-agent"]
    max_calls_per_minute: 30
    blocked_patterns:
      - "DROP TABLE"
      - "DELETE FROM"

audit:
  enabled: true
```

---

## API Reference

| Class | Description |
|-------|-------------|
| `SafeAICrewAIAdapter` | Main adapter returned by `ai.crewai_adapter()` |
| `adapter.wrap_tool()` | Wrap a single CrewAI tool with policy enforcement |

See [API Reference - Middleware](../reference/middleware.md) for full signatures.

---

## Next Steps

- [LangChain Integration](langchain.md) -- if you also use LangChain tools in your crew
- [Policy Engine](../guides/policy-engine.md) -- customize enforcement rules
- [Tool Contracts](../guides/tool-contracts.md) -- define per-tool permissions
