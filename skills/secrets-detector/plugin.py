# SPDX-License-Identifier: Apache-2.0
"""Extended secrets and credentials detector for SafeAI.

Adds 40+ detection patterns on top of the built-in SafeAI detectors,
covering provider-specific API keys, tokens, connection strings, and
private key material.

All patterns use the same tag hierarchy as SafeAI built-ins:
  secret.credential  — high-confidence credential (block by default)
  secret.token       — generic token / bearer
  secret.key         — cryptographic key material
  secret.connection  — database / service connection strings
"""

from __future__ import annotations

EXTENDED_PATTERNS: list[tuple[str, str, str]] = [
    # ------------------------------------------------------------------ #
    # Anthropic / Claude
    # ------------------------------------------------------------------ #
    ("anthropic_key", "secret.credential", r"\bsk-ant-[A-Za-z0-9\-_]{32,}\b"),

    # ------------------------------------------------------------------ #
    # GitHub
    # ------------------------------------------------------------------ #
    ("github_pat_classic", "secret.credential", r"\bghp_[A-Za-z0-9]{36}\b"),
    ("github_pat_fine", "secret.credential", r"\bgithub_pat_[A-Za-z0-9_]{82}\b"),
    ("github_oauth", "secret.credential", r"\bgho_[A-Za-z0-9]{36}\b"),
    ("github_app_token", "secret.credential", r"\bghs_[A-Za-z0-9]{36}\b"),
    ("github_refresh", "secret.credential", r"\bghr_[A-Za-z0-9]{76}\b"),

    # ------------------------------------------------------------------ #
    # AWS
    # ------------------------------------------------------------------ #
    ("aws_secret_key", "secret.credential", r"(?i)aws.{0,20}secret.{0,20}['\"][0-9a-zA-Z/+]{40}['\"]"),
    ("aws_session_token", "secret.token", r"\bAQoD[A-Za-z0-9+/]{100,}={0,2}\b"),

    # ------------------------------------------------------------------ #
    # Google / GCP
    # ------------------------------------------------------------------ #
    ("gcp_api_key", "secret.credential", r"\bAIza[0-9A-Za-z\-_]{35}\b"),
    ("gcp_service_account", "secret.credential",
     r'"type"\s*:\s*"service_account"'),
    ("google_oauth", "secret.credential",
     r"\b1//[0-9A-Za-z\-_]{43,}\b"),

    # ------------------------------------------------------------------ #
    # Azure
    # ------------------------------------------------------------------ #
    ("azure_conn_string", "secret.connection",
     r"DefaultEndpointsProtocol=https;AccountName=[^;]+;AccountKey=[A-Za-z0-9+/=]{88};"),
    ("azure_sas_token", "secret.token",
     r"(?i)sig=[A-Za-z0-9%+/=]{43,}"),

    # ------------------------------------------------------------------ #
    # Stripe
    # ------------------------------------------------------------------ #
    ("stripe_secret", "secret.credential", r"\bsk_live_[0-9a-zA-Z]{24}\b"),
    ("stripe_restricted", "secret.credential", r"\brk_live_[0-9a-zA-Z]{24}\b"),
    ("stripe_test", "secret.credential", r"\bsk_test_[0-9a-zA-Z]{24}\b"),

    # ------------------------------------------------------------------ #
    # Slack
    # ------------------------------------------------------------------ #
    ("slack_bot_token", "secret.credential", r"\bxoxb-[0-9]{11}-[0-9]{11}-[A-Za-z0-9]{24}\b"),
    ("slack_user_token", "secret.credential", r"\bxoxp-[0-9]{11}-[0-9]{11}-[0-9]{11}-[A-Za-z0-9]{32}\b"),
    ("slack_webhook", "secret.credential",
     r"https://hooks\.slack\.com/services/T[A-Za-z0-9]+/B[A-Za-z0-9]+/[A-Za-z0-9]+"),

    # ------------------------------------------------------------------ #
    # Twilio
    # ------------------------------------------------------------------ #
    ("twilio_auth_token", "secret.credential", r"(?i)twilio.{0,20}['\"][0-9a-f]{32}['\"]"),
    ("twilio_sid", "secret.credential", r"\bAC[0-9a-f]{32}\b"),

    # ------------------------------------------------------------------ #
    # SendGrid / Mailgun
    # ------------------------------------------------------------------ #
    ("sendgrid_key", "secret.credential", r"\bSG\.[A-Za-z0-9\-_]{22}\.[A-Za-z0-9\-_]{43}\b"),
    ("mailgun_key", "secret.credential", r"\bkey-[0-9a-zA-Z]{32}\b"),

    # ------------------------------------------------------------------ #
    # npm / PyPI
    # ------------------------------------------------------------------ #
    ("npm_token", "secret.credential", r"\bnpm_[A-Za-z0-9]{36}\b"),
    ("pypi_token", "secret.credential", r"\bpypi-[A-Za-z0-9\-_]{32,}\b"),

    # ------------------------------------------------------------------ #
    # JWT
    # ------------------------------------------------------------------ #
    ("jwt_token", "secret.token",
     r"\beyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\b"),

    # ------------------------------------------------------------------ #
    # Private key material
    # ------------------------------------------------------------------ #
    ("rsa_private_key", "secret.key", r"-----BEGIN RSA PRIVATE KEY-----"),
    ("ec_private_key", "secret.key", r"-----BEGIN EC PRIVATE KEY-----"),
    ("openssh_private_key", "secret.key", r"-----BEGIN OPENSSH PRIVATE KEY-----"),
    ("pgp_private_key", "secret.key", r"-----BEGIN PGP PRIVATE KEY BLOCK-----"),
    ("generic_private_key", "secret.key", r"-----BEGIN PRIVATE KEY-----"),

    # ------------------------------------------------------------------ #
    # Database connection strings
    # ------------------------------------------------------------------ #
    ("postgres_conn", "secret.connection",
     r"postgres(?:ql)?://[^:]+:[^@]+@[^/]+/\S+"),
    ("mysql_conn", "secret.connection",
     r"mysql://[^:]+:[^@]+@[^/]+/\S+"),
    ("mongodb_conn", "secret.connection",
     r"mongodb(?:\+srv)?://[^:]+:[^@]+@\S+"),
    ("redis_conn", "secret.connection",
     r"redis://(?:[^:]+:[^@]+@)?\S+"),

    # ------------------------------------------------------------------ #
    # Miscellaneous
    # ------------------------------------------------------------------ #
    ("basic_auth_url", "secret.credential",
     r"https?://[A-Za-z0-9._%+\-]+:[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+"),
    ("bearer_header", "secret.token",
     r"(?i)authorization:\s*bearer\s+[A-Za-z0-9\-_=.+/]{20,}"),
    ("password_assignment", "secret.credential",
     r"(?i)(?:password|passwd|pwd)\s*[:=]\s*['\"]?[^\s'\"]{8,}['\"]?"),
]


def safeai_detectors() -> list[tuple[str, str, str]]:
    """Return extended secrets/credential detector patterns."""
    return EXTENDED_PATTERNS
