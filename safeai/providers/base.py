# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""Base wrapper for LLM provider clients."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TokenUsage:
    """Token usage extracted from an LLM response."""
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = "unknown"
    provider: str = "unknown"


class BaseLLMWrapper:
    """Base class for LLM provider wrappers.
    
    Subclasses implement extract_usage() to parse provider-specific
    response formats. The wrapper can be composed with CostTracker
    to automatically record costs.
    """

    provider: str = "unknown"

    def extract_usage(self, response: Any) -> TokenUsage:
        """Extract token usage from a provider response.
        
        Args:
            response: The raw response object from the LLM provider.
            
        Returns:
            TokenUsage with extracted token counts and model info.
        """
        raise NotImplementedError
