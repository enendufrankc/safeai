"""SafeAI integration adapters example — LangChain wrapper."""

from safeai import SafeAI

ai = SafeAI.quickstart()


# --- Simulated LangChain tool ---
class FakeTool:
    """Minimal tool interface matching LangChain's BaseTool shape."""

    name = "search"
    description = "Search the web"

    def run(self, query: str) -> str:
        return f"Results for: {query}"


# Wrap with SafeAI boundary enforcement
from safeai.middleware.langchain import wrap_langchain_tool  # noqa: E402

tool = FakeTool()
safe_tool = wrap_langchain_tool(ai, tool, agent_id="demo-agent")

# Safe query
result = safe_tool.run("latest Python release")
print(f"Safe query result: {result}")

# Query containing a secret — will be intercepted
result = safe_tool.run("search for sk-ABCDEF1234567890ABCDEF")
print(f"Secret query result: {result}")
