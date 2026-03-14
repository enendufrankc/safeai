# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""Anthropic response wrapper for cost capture."""

from __future__ import annotations

from typing import Any

from safeai.providers.base import BaseLLMWrapper, TokenUsage


class AnthropicWrapper(BaseLLMWrapper):
    """Extract token usage from Anthropic message responses.
    
    Works with both the anthropic Python SDK response objects and raw
    dict responses from the REST API.
    
    Example:
        wrapper = AnthropicWrapper()
        response = anthropic_client.messages.create(...)
        usage = wrapper.extract_usage(response)
        cost_tracker.record(
            provider=usage.provider, model=usage.model,
            input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
        )
    """

    provider = "anthropic"

    def extract_usage(self, response: Any) -> TokenUsage:
        """Extract usage from an Anthropic response.
        
        Args:
            response: Anthropic Message object or dict with 'usage' key.
            
        Returns:
            TokenUsage with input_tokens and output_tokens extracted
            directly from the Anthropic usage format.
        """
        if isinstance(response, dict):
            usage = response.get("usage", {})
            model = response.get("model", "unknown")
            return TokenUsage(
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                model=model,
                provider=self.provider,
            )
        # SDK object with attributes
        usage = getattr(response, "usage", None)
        model = getattr(response, "model", "unknown")
        if usage is None:
            return TokenUsage(model=model, provider=self.provider)
        return TokenUsage(
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
            model=model,
            provider=self.provider,
        )
