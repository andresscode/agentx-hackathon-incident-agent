"""Centralized application configuration.

All settings loaded from environment variables with sensible defaults.
Import `settings` anywhere — it's a singleton.
"""

import os


class Settings:
    """Application settings. Add new settings here as the project grows."""

    # ─── Database ───────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@db:5432/incident_agent",
    )

    # ─── LLM Provider ───────────────────────────────────────────────
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openrouter")
    LLM_MODEL: str | None = os.getenv("LLM_MODEL")

    # ─── Notifications ──────────────────────────────────────────────
    NOTIFY_EMAIL_ON_TRIAGE: bool = os.getenv("NOTIFY_EMAIL_ON_TRIAGE", "true").lower() in (
        "true", "1", "yes", "on"
    )
    NOTIFY_DISCORD_ON_TRIAGE: bool = os.getenv("NOTIFY_DISCORD_ON_TRIAGE", "true").lower() in (
        "true", "1", "yes", "on"
    )
    NOTIFY_CC_EMAILS: list[str] = [
        e.strip()
        for e in os.getenv("NOTIFY_CC_EMAILS", "").split(",")
        if e.strip()
    ]

    EMAIL_SMTP_URL: str = os.getenv("EMAIL_SMTP_URL", "")
    DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
    APPRISE_URL: str = os.getenv("APPRISE_URL", "http://apprise:8000")

    # ─── Peppermint ─────────────────────────────────────────────────
    PEPPERMINT_URL: str = os.getenv("PEPPERMINT_URL", "http://peppermint:5003/api/v1")
    PEPPERMINT_EMAIL: str = os.getenv("PEPPERMINT_EMAIL", "admin@admin.com")
    PEPPERMINT_PASSWORD: str = os.getenv("PEPPERMINT_PASSWORD", "1234")

    # ─── Observability ──────────────────────────────────────────────
    PHOENIX_COLLECTOR_ENDPOINT: str | None = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")


settings = Settings()
