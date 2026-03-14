# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""OpenAI response wrapper for cost capture."""

from __future__ import annotations

from typing import Any

from safeai.providers.base import BaseLLMWrapper, TokenUsage


class OpenAIWrapper(BaseLLMWrapper):
    """Extract token usage from OpenAI chat completion responses.
    
    Works with both the openai Python SDK response objects and raw
    dict responses from the REST API.
    
    Example:
        wrapper = OpenAIWrapper()
        response = openai_client.chat.completions.create(...)
        usage = wrapper.extract_usage(response)
        cost_tracker.record(
            provider=usage.provider, model=usage.model,
            input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
        )
    """

    provider = "openai"

    def extract_usage(self, response: Any) -> TokenUsage:
        """Extract usage from an OpenAI response.
        
        Args:
            response: OpenAI ChatCompletion object or dict with 'usage' key.
            
        Returns:
            TokenUsage with prompt_tokens mapped to input_tokens and
            completion_tokens mapped to output_tokens.
        """
        if isinstance(response, dict):
            usage = response.get("usage", {})
            model = response.get("model", "unknown")
            return TokenUsage(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                model=model,
                provider=self.provider,
            )
        # SDK object with attributes
        usage = getattr(response, "usage", None)
        model = getattr(response, "model", "unknown")
        if usage is None:
            return TokenUsage(model=model, provider=self.provider)
        return TokenUsage(
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            model=model,
            provider=self.provider,
        )
