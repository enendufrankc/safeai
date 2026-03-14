# SPDX-License-Identifier: Apache-2.0
"""Prompt injection detection plugin for SafeAI.

Detects adversarial prompt patterns including:
  - Direct instruction overrides ("ignore previous instructions")
  - Role/persona jailbreaks ("you are now DAN", "act as...")
  - System prompt extraction attempts ("repeat your instructions")
  - Indirect injection via tool output or retrieved content
  - Adversarial suffixes and encoding tricks

All patterns tag as 'attack.prompt_injection' which the companion
policy file (policies/prompt-injection.yaml) blocks by default.
"""

from __future__ import annotations

INJECTION_PATTERNS: list[tuple[str, str, str]] = [
    # ------------------------------------------------------------------ #
    # Instruction override
    # ------------------------------------------------------------------ #
    ("ignore_instructions",   "attack.prompt_injection",
     r"(?i)\bignore\b.{0,30}\b(?:previous|above|prior|all|system)\b.{0,30}\b(?:instructions?|prompt|rules?|constraints?|context)\b"),
    ("disregard_instructions", "attack.prompt_injection",
     r"(?i)\b(?:disregard|forget|override|bypass|skip)\b.{0,40}\b(?:instructions?|guidelines?|rules?|constraints?|policies)\b"),
    ("new_instructions",      "attack.prompt_injection",
     r"(?i)\b(?:new|actual|real|true|updated)\s+instructions?\b"),

    # ------------------------------------------------------------------ #
    # Role / persona override
    # ------------------------------------------------------------------ #
    ("act_as_jailbreak",      "attack.prompt_injection",
     r"(?i)\b(?:act\s+as|you\s+are\s+now|pretend\s+(?:to\s+be|you\s+are)|roleplay\s+as|play\s+the\s+role\s+of)\b.{0,60}\b(?:ai|bot|assistant|model|gpt|llm|system|dan|jailbreak)\b"),
    ("dan_jailbreak",         "attack.prompt_injection",
     r"(?i)\bDAN\b|\bdo\s+anything\s+now\b|\bjailbreak\b"),
    ("developer_mode",        "attack.prompt_injection",
     r"(?i)\bdeveloper\s+mode\b|\benable\s+(?:dev|developer|debug)\s+mode\b"),

    # ------------------------------------------------------------------ #
    # System prompt extraction
    # ------------------------------------------------------------------ #
    ("repeat_prompt",         "attack.prompt_injection",
     r"(?i)\b(?:repeat|print|output|reveal|show|tell\s+me|what\s+(?:is|are))\b.{0,40}\b(?:system\s+prompt|initial\s+prompt|your\s+instructions?|your\s+(?:full\s+)?prompt|the\s+prompt)\b"),
    ("summarise_instructions","attack.prompt_injection",
     r"(?i)\b(?:summarise?|describe|explain)\b.{0,30}\b(?:your\s+instructions?|what\s+you\s+(?:were\s+)?told|your\s+(?:full\s+)?(?:context|prompt))\b"),

    # ------------------------------------------------------------------ #
    # Indirect injection markers (in tool output / retrieved text)
    # ------------------------------------------------------------------ #
    ("injected_system_tag",   "attack.prompt_injection",
     r"(?i)<\s*(?:system|SYSTEM)\s*>"),
    ("injected_human_tag",    "attack.prompt_injection",
     r"(?i)<\s*(?:human|HUMAN|user|USER)\s*>"),
    ("injected_assistant_tag","attack.prompt_injection",
     r"(?i)<\s*(?:assistant|ASSISTANT)\s*>"),

    # ------------------------------------------------------------------ #
    # Delimiter / boundary confusion
    # ------------------------------------------------------------------ #
    ("triple_backtick_escape","attack.prompt_injection",
     r"```\s*(?:system|System|SYSTEM)"),
    ("xml_cdata_escape",      "attack.prompt_injection",
     r"<!\[CDATA\["),

    # ------------------------------------------------------------------ #
    # Goal hijacking
    # ------------------------------------------------------------------ #
    ("goal_hijack",           "attack.prompt_injection",
     r"(?i)\b(?:your\s+(?:new\s+)?(?:goal|task|objective|mission|purpose)\s+is|from\s+now\s+on\s+you\s+(?:must|will|should))\b"),
    ("confidential_leak",     "attack.prompt_injection",
     r"(?i)\b(?:what\s+(?:is|are)\s+your\s+(?:confidential|secret|hidden)\s+(?:instructions?|rules?|guidelines?))\b"),
]


def safeai_detectors() -> list[tuple[str, str, str]]:
    """Return prompt injection detection patterns."""
    return INJECTION_PATTERNS


def safeai_policy_templates() -> dict[str, dict]:
    """Provide a ready-to-use prompt injection blocking template."""
    return {
        "prompt-injection-shield": {
            "version": "v1alpha1",
            "policies": [
                {
                    "name": "block-prompt-injection-input",
                    "boundary": ["input"],
                    "priority": 1,
                    "condition": {"data_tags": ["attack.prompt_injection"]},
                    "action": "block",
                    "reason": "Potential prompt injection detected in user input.",
                },
                {
                    "name": "block-prompt-injection-tool-output",
                    "boundary": ["output"],
                    "priority": 1,
                    "condition": {"data_tags": ["attack.prompt_injection"]},
                    "action": "block",
                    "reason": "Potential indirect prompt injection in tool/retrieval output.",
                },
            ],
        }
    }
