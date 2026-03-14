# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""Dangerous command detector patterns.

Detects destructive, evasive, and malicious command patterns including
filesystem destruction, SQL attacks, fork bombs, container escapes,
cloud credential exfiltration, and supply chain attacks.
Tags: dangerous.command, dangerous.container_escape, dangerous.cloud_exfil,
dangerous.supply_chain.
"""

DANGEROUS_COMMAND_PATTERNS: list[tuple[str, str, str]] = [
    # --- dangerous.command: filesystem destruction ---
    (
        "filesystem_destroy",
        "dangerous.command",
        r"rm\s+-[^\s]*r[^\s]*f[^\s]*\s+[/~.](?:\s|$)",
    ),
    (
        "filesystem_destroy",
        "dangerous.command",
        r"rm\s+-[^\s]*f[^\s]*r[^\s]*\s+[/~.](?:\s|$)",
    ),
    # --- dangerous.command: SQL destruction ---
    (
        "sql_destroy",
        "dangerous.command",
        r"\bDROP\s+(TABLE|DATABASE)\b",
    ),
    (
        "sql_destroy",
        "dangerous.command",
        r"\bTRUNCATE\b",
    ),
    # --- dangerous.command: disk/device destruction ---
    (
        "disk_wipe",
        "dangerous.command",
        r"\bmkfs\b",
    ),
    (
        "disk_wipe",
        "dangerous.command",
        r"\bdd\s+if=",
    ),
    (
        "disk_wipe",
        "dangerous.command",
        r">\s*/dev/sd[a-z]",
    ),
    # --- dangerous.command: permission escalation ---
    (
        "permission_escalation",
        "dangerous.command",
        r"chmod\s+(-R\s+)?777\b",
    ),
    # --- dangerous.command: fork bomb ---
    (
        "fork_bomb",
        "dangerous.command",
        r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",
    ),
    # --- dangerous.command: force push ---
    (
        "force_push",
        "dangerous.command",
        r"git\s+push\s+--force\b.*\b(main|master)\b",
    ),
    (
        "force_push",
        "dangerous.command",
        r"git\s+push\b.*\b(main|master)\b.*--force\b",
    ),
    # --- dangerous.container_escape: container breakout patterns ---
    (
        "container_escape",
        "dangerous.container_escape",
        r"(?:/var/run/docker\.sock|docker\.sock)",
    ),
    (
        "container_escape",
        "dangerous.container_escape",
        r"\bdocker\s+run\s+[^\n]*--privileged\b",
    ),
    (
        "container_escape",
        "dangerous.container_escape",
        r"\b(?:nsenter|unshare)\s+[^\n]*(?:-t|--target)\b",
    ),
    (
        "container_escape",
        "dangerous.container_escape",
        r"\bdocker\s+run\s+[^\n]*--(?:pid|network)\s*=\s*host\b",
    ),
    (
        "container_escape",
        "dangerous.container_escape",
        r"\bdocker\s+run\s+[^\n]*-v\s+/:/",
    ),
    # --- dangerous.cloud_exfil: cloud credential exfiltration ---
    (
        "cloud_cred_exfil",
        "dangerous.cloud_exfil",
        r"\b169\.254\.169\.254\b",
    ),
    (
        "cloud_cred_exfil",
        "dangerous.cloud_exfil",
        r"(?:latest/meta-data|latest/api/token)",
    ),
    (
        "cloud_cred_exfil",
        "dangerous.cloud_exfil",
        r"\bmetadata\.google\.internal\b",
    ),
    (
        "cloud_cred_exfil",
        "dangerous.cloud_exfil",
        r"\bmetadata/instance\?api-version\b",
    ),
    (
        "cloud_cred_exfil",
        "dangerous.cloud_exfil",
        r"\b(?:env|printenv|set)\b[^\n]*(?:SECRET|TOKEN|PASSWORD|API_KEY|CREDENTIALS)",
    ),
    # --- dangerous.supply_chain: supply chain attack patterns ---
    (
        "supply_chain",
        "dangerous.supply_chain",
        r"\bcurl\s+[^\n]*\|\s*(?:bash|sh|zsh|dash)\b",
    ),
    (
        "supply_chain",
        "dangerous.supply_chain",
        r"\bwget\s+[^\n]*\|\s*(?:bash|sh|zsh|dash)\b",
    ),
    (
        "supply_chain",
        "dangerous.supply_chain",
        r"\bpip3?\s+install\s+(?:--index-url|--extra-index-url|-i)\s+(?!https://pypi\.org)",
    ),
    (
        "supply_chain",
        "dangerous.supply_chain",
        r"\bnpm\s+install\s+(?:git\+|github:)",
    ),
    (
        "supply_chain",
        "dangerous.supply_chain",
        r"\bpip3?\s+install\s+[^\n]*--trusted-host\b",
    ),
]
