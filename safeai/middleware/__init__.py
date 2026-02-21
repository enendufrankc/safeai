"""Framework adapter interfaces."""

from safeai.middleware.autogen import SafeAIAutoGenAdapter
from safeai.middleware.claude_adk import SafeAIClaudeADKAdapter
from safeai.middleware.crewai import SafeAICrewAIAdapter
from safeai.middleware.google_adk import SafeAIGoogleADKAdapter
from safeai.middleware.langchain import SafeAIBlockedError, SafeAICallback, SafeAILangChainAdapter

__all__ = [
    "SafeAIAutoGenAdapter",
    "SafeAIClaudeADKAdapter",
    "SafeAICrewAIAdapter",
    "SafeAIGoogleADKAdapter",
    "SafeAIBlockedError",
    "SafeAICallback",
    "SafeAILangChainAdapter",
]
