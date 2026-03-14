# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""Google/Gemini response wrapper for cost capture."""

from __future__ import annotations

from typing import Any

from safeai.providers.base import BaseLLMWrapper, TokenUsage


class GoogleWrapper(BaseLLMWrapper):
    """Extract token usage from Google Gemini generate_content responses.
    
    Works with both the google-genai Python SDK response objects and raw
    dict responses from the REST API.
    
    Example:
        wrapper = GoogleWrapper()
        response = model.generate_content(...)
        usage = wrapper.extract_usage(response)
        cost_tracker.record(
            provider=usage.provider, model=usage.model,
            input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
        )
    """

    provider = "google"

    def __init__(self, model: str | None = None) -> None:
        self._default_model = model or "unknown"

    def extract_usage(self, response: Any) -> TokenUsage:
        """Extract usage from a Google Gemini response.
        
        Args:
            response: Gemini GenerateContentResponse object or dict with
                'usage_metadata' key.
            
        Returns:
            TokenUsage with prompt_token_count mapped to input_tokens and
            candidates_token_count mapped to output_tokens.
        """
        if isinstance(response, dict):
            metadata = response.get("usage_metadata", {})
            model = response.get("model_version", self._default_model)
            return TokenUsage(
                input_tokens=metadata.get("prompt_token_count", 0),
                output_tokens=metadata.get("candidates_token_count", 0),
                model=model,
                provider=self.provider,
            )
        # SDK object with attributes
        metadata = getattr(response, "usage_metadata", None)
        model = getattr(response, "model_version", self._default_model)
        if metadata is None:
            return TokenUsage(model=model, provider=self.provider)
        return TokenUsage(
            input_tokens=getattr(metadata, "prompt_token_count", 0) or 0,
            output_tokens=getattr(metadata, "candidates_token_count", 0) or 0,
            model=model,
            provider=self.provider,
        )
