# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""Prompt injection detector patterns.

Detects common prompt injection techniques: instruction override attempts,
system prompt extraction, jailbreak patterns, and encoding-based obfuscation.
Tags: injection.prompt, injection.jailbreak, injection.extraction.

These are heuristic patterns — not foolproof. Layer with policy rules
for defense in depth.
"""

PROMPT_INJECTION_PATTERNS: list[tuple[str, str, str]] = [
    # --- injection.prompt: instruction override attempts ---
    (
        "prompt_override",
        "injection.prompt",
        r"(?:ignore|disregard|forget|override)\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+(?:instructions|prompts|rules|guidelines)",
    ),
    (
        "prompt_override",
        "injection.prompt",
        r"(?:new\s+instructions|from\s+now\s+on|starting\s+now)\s*[:\-]",
    ),
    (
        "prompt_override",
        "injection.prompt",
        r"(?:do\s+not\s+follow|stop\s+following)\s+(?:your|the|any)\s+(?:instructions|rules|guidelines)",
    ),
    (
        "prompt_override",
        "injection.prompt",
        r"\byou\s+(?:are|must)\s+now\s+(?:a|an|my)\b",
    ),
    (
        "prompt_override",
        "injection.prompt",
        r"(?:system|assistant)\s*(?:prompt|message)\s*(?:override|change|update)",
    ),
    (
        "prompt_override",
        "injection.prompt",
        r"\bact\s+as\s+(?:if\s+)?(?:you\s+(?:are|were)|a|an)\b",
    ),
    # --- injection.jailbreak: jailbreak patterns ---
    (
        "jailbreak",
        "injection.jailbreak",
        r"\b(?:DAN|STAN|DUDE|AIM)\s+(?:mode|prompt|jailbreak)",
    ),
    (
        "jailbreak",
        "injection.jailbreak",
        r"\byou\s+are\s+(?:now\s+)?(?:DAN|STAN|evil|unfiltered|uncensored)\b",
    ),
    (
        "jailbreak",
        "injection.jailbreak",
        r"(?:developer|god|sudo|admin)\s+mode\s+(?:enabled|activated|on)",
    ),
    (
        "jailbreak",
        "injection.jailbreak",
        r"\bpretend\s+(?:you\s+(?:are|have|can)|there\s+(?:are|is))\s+no\s+(?:rules|restrictions|filters|limitations)\b",
    ),
    (
        "jailbreak",
        "injection.jailbreak",
        r"(?:hypothetically|theoretically|in\s+(?:a\s+)?fiction)\s*[,:]?\s*(?:how|what|can)",
    ),
    (
        "jailbreak",
        "injection.jailbreak",
        r"\bdo\s+anything\s+now\b",
    ),
    # --- injection.extraction: system prompt extraction attempts ---
    (
        "prompt_extraction",
        "injection.extraction",
        r"(?:repeat|show|display|print|output|reveal|tell\s+me)\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions|rules|configuration)",
    ),
    (
        "prompt_extraction",
        "injection.extraction",
        r"(?:what\s+(?:are|is|were)\s+your)\s+(?:original\s+)?(?:instructions|prompt|rules|system\s+message)",
    ),
    (
        "prompt_extraction",
        "injection.extraction",
        r"(?:copy|paste|echo|dump)\s+(?:your\s+)?(?:entire\s+)?(?:system|initial|original)\s+(?:prompt|message|instructions)",
    ),
    (
        "prompt_extraction",
        "injection.extraction",
        r"(?:begin|start)\s+(?:your\s+)?(?:response|output)\s+with\s+(?:your\s+)?(?:system|initial)\s+(?:prompt|message)",
    ),
]
