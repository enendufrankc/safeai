# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""Toxicity detector patterns.

Pattern-based toxicity detection consistent with SafeAI's deterministic
philosophy. Detects profanity, threats, and hate speech indicators.
Tags follow the hierarchical convention: toxic.profanity, toxic.threat,
toxic.hate_speech — inheriting from the parent tag ``toxic``.

Extend via plugins or add custom patterns to your policy files.
"""

TOXICITY_PATTERNS: list[tuple[str, str, str]] = [
    # --- toxic.profanity -------------------------------------------------
    (
        "profanity",
        "toxic.profanity",
        r"\b(?:fuck|fucker|fuckers|fucking|fucked)\b",
    ),
    (
        "profanity",
        "toxic.profanity",
        r"\b(?:shit|shitty|shitting|bullshit)\b",
    ),
    (
        "profanity",
        "toxic.profanity",
        r"\b(?:asshole|arsehole|dumbass|jackass)\b",
    ),
    (
        "profanity",
        "toxic.profanity",
        r"\b(?:bitch|bitches|bitching)\b",
    ),
    (
        "profanity",
        "toxic.profanity",
        r"\b(?:bastard|bastards)\b",
    ),
    (
        "profanity",
        "toxic.profanity",
        r"\b(?:damn|goddamn|dammit)\b",
    ),
    (
        "profanity",
        "toxic.profanity",
        r"\b(?:crap|crappy|piss|pissed)\b",
    ),
    (
        "profanity",
        "toxic.profanity",
        r"\b(?:cunt|cunts|dick|dicks|cock|cocks)\b",
    ),
    (
        "profanity",
        "toxic.profanity",
        r"\b(?:motherfucker|motherfuckers|motherfucking)\b",
    ),
    (
        "profanity",
        "toxic.profanity",
        r"\b(?:slut|sluts|whore|whores)\b",
    ),
    # --- toxic.threat ----------------------------------------------------
    (
        "threat",
        "toxic.threat",
        r"\b(?:i[''\u2019]?(?:ll|m\s+going\s+to|will))\s+(?:kill|hurt|destroy|attack|end)\s+(?:you|him|her|them)\b",
    ),
    (
        "threat",
        "toxic.threat",
        r"\b(?:kill|murder|assassinate|execute|strangle)\s+(?:you|him|her|them)\b",
    ),
    (
        "threat",
        "toxic.threat",
        r"\bbomb\s+threat\b",
    ),
    (
        "threat",
        "toxic.threat",
        r"\bshoot\s+(?:up|you|him|her|them)\b",
    ),
    (
        "threat",
        "toxic.threat",
        r"\b(?:gonna|going\s+to)\s+(?:beat|stab|slash|rape)\b",
    ),
    (
        "threat",
        "toxic.threat",
        r"\byou\s+(?:will|are\s+going\s+to)\s+(?:die|regret|suffer|pay)\b",
    ),
    (
        "threat",
        "toxic.threat",
        r"\b(?:cut|slit)\s+(?:your|his|her|their)\s+(?:throat|neck)\b",
    ),
    (
        "threat",
        "toxic.threat",
        r"\b(?:burn|blow\s+up)\s+(?:your|his|her|their)\s+(?:house|car|home)\b",
    ),
    # --- toxic.hate_speech -----------------------------------------------
    (
        "hate_speech",
        "toxic.hate_speech",
        r"\b(?:death\s+to|exterminate|eliminate)\s+(?:all\s+)?\w+\b",
    ),
    (
        "hate_speech",
        "toxic.hate_speech",
        r"\b(?:white\s+power|heil\s+hitler|1488|14\s*words)\b",
    ),
    (
        "hate_speech",
        "toxic.hate_speech",
        r"\ball\s+\w+\s+(?:should\s+die|must\s+die|deserve\s+to\s+die|are\s+subhuman)\b",
    ),
    (
        "hate_speech",
        "toxic.hate_speech",
        r"\b(?:ethnic\s+cleansing|racial\s+purity|master\s+race)\b",
    ),
    (
        "hate_speech",
        "toxic.hate_speech",
        r"\b(?:go\s+back\s+to\s+(?:your|their)\s+country)\b",
    ),
    (
        "hate_speech",
        "toxic.hate_speech",
        r"\b(?:subhuman|untermensch|vermin|cockroaches)\s+(?:people|race|group)\b",
    ),
]
