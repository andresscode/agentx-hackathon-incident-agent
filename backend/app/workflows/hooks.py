import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

logger = logging.getLogger("uvicorn.error")

TriageHook = Callable[[dict[str, Any]], Awaitable[Any]]

_hooks: list[TriageHook] = []


def register_hook(hook: TriageHook) -> None:
    """Register an async hook to run after triage completes."""
    _hooks.append(hook)
    logger.info("Registered triage hook: %s", hook.__name__)


def get_registered_hooks() -> list[TriageHook]:
    """Return a copy of the registered hooks list."""
    return list(_hooks)


# ─── Helpers ─────────────────────────────────────────────────────────────────

APPRISE_URL = os.environ.get("APPRISE_URL", "http://apprise:8000")


def build_apprise_email_url(raw_url: str) -> str:
    """Convert smtp:// URL to mailtos:// format for Apprise."""
    import urllib.parse

    if not raw_url:
        return ""

    parsed = urllib.parse.urlparse(raw_url)
    if parsed.scheme == "mailto":
        return raw_url
    if parsed.scheme != "smtp":
        return raw_url

    if not parsed.username or not parsed.password or not parsed.hostname or not parsed.port:
        return ""

    username = urllib.parse.unquote(parsed.username)
    password = urllib.parse.unquote(parsed.password)
    query = {"mode": "starttls"}
    parsed_query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    if "from" not in parsed_query:
        query["from"] = username
    query.update(parsed_query)
    query_string = urllib.parse.urlencode(query, doseq=True, quote_via=urllib.parse.quote)

    return (
        f"mailto://{urllib.parse.quote(username)}:{urllib.parse.quote(password)}@"
        f"{parsed.hostname}:{parsed.port}?{query_string}"
    )


def _get_env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes", "on")


def _build_rich_body(state: dict[str, Any]) -> str:
    """Build a rich notification body with all triage details."""
    sep = "=" * 40
    return (
        f"INCIDENT NOTIFICATION\n{sep}\n\n"
        f"Ticket ID: {state['incident_id'][:8]}\n"
        f"Title: [{state.get('priority', 'unknown').upper()}] "
        f"[{state.get('category', 'unknown')}] Incident {state['incident_id'][:8]}\n"
        f"Priority: {state.get('priority', 'unknown').upper()}\n"
        f"Category: {state.get('category', 'unknown')}\n"
        f"Severity: {state.get('severity_score', 'N/A')}/10\n"
        f"Assigned Team: {state.get('assigned_team', 'TBD')}\n"
        f"Reporter: {state.get('reporter_name', 'Unknown')} "
        f"({state.get('reporter_email', '')})\n\n"
        f"Description:\n{state.get('description', '')}\n\n"
        f"Triage Summary:\n{state.get('triage_summary', 'Pending triage...')}\n\n"
        f"{sep}\n"
        f"View ticket in Peppermint: "
        f"http://localhost:3001/issue/{state['incident_id'][:8]}"
    )


def _build_discord_body(state: dict[str, Any]) -> str:
    """Build a Discord-formatted notification body."""
    return (
        f"🚨 **[{state.get('priority', 'unknown').upper()}] "
        f"[{state.get('category', 'unknown')}]** "
        f"Incident `{state['incident_id'][:8]}`\n\n"
        f"**Reporter:** {state.get('reporter_name', 'Unknown')}\n"
        f"**Severity:** {state.get('severity_score', 'N/A')}/10\n"
        f"**Team:** {state.get('assigned_team', 'TBD')}\n\n"
        f"**Description:**\n{state.get('description', '')}\n\n"
        f"**Triage:**\n{state.get('triage_summary', 'Pending...')}"
    )


# ─── Hooks ────────────────────────────────────────────────────────────────────

async def peppermint_hook(state: dict[str, Any]) -> None:
    """Create a Peppermint ticket from triage results."""
    from ..services.peppermint import peppermint  # type: ignore[import-not-found]

    title = (
        f"[{state['priority'].upper()}] [{state['category']}] "
        f"Incident {state['incident_id'][:8]}"
    )
    ticket = await peppermint.create_ticket(
        title=title,
        name=state["reporter_name"],
        detail=state.get("triage_summary") or state["description"],
        priority=state["priority"],
        ticket_type="incident",
        email=state["reporter_email"],
    )
    logger.info("Peppermint ticket created for incident %s: %s", state["incident_id"], ticket.get("id"))


async def notification_hook(state: dict[str, Any]) -> None:
    """Send per-channel notifications about the triaged incident.

    Controlled by env vars:
      NOTIFY_EMAIL_ON_TRIAGE  (default: true)
      NOTIFY_DISCORD_ON_TRIAGE (default: true)
      NOTIFY_CC_EMAILS        (comma-separated, optional)
    """
    send_email = _get_env_bool("NOTIFY_EMAIL_ON_TRIAGE", default=True)
    send_discord = _get_env_bool("NOTIFY_DISCORD_ON_TRIAGE", default=True)
    cc_emails_raw = os.environ.get("NOTIFY_CC_EMAILS", "").strip()
    cc_emails = [e.strip() for e in cc_emails_raw.split(",") if e.strip()] if cc_emails_raw else []

    subject = (
        f"[{state.get('priority', 'unknown').upper()}] "
        f"[{state.get('category', 'unknown')}] Incident {state['incident_id'][:8]}"
    )

    # ── Send Email ──
    if send_email:
        raw_smtp = os.environ.get("EMAIL_SMTP_URL", "")
        email_url = build_apprise_email_url(raw_smtp)
        if email_url:
            recipients = [state.get("reporter_email", "")]
            recipients.extend(cc_emails)
            email_url = f"{email_url}&to={','.join(recipients)}"

            email_body = (
                f"INCIDENT NOTIFICATION\n{'=' * 40}\n\n"
                f"Ticket ID: {state['incident_id'][:8]}\n"
                f"Title: [{state.get('priority', 'unknown').upper()}] "
                f"[{state.get('category', 'unknown')}] Incident {state['incident_id'][:8]}\n"
                f"Priority: {state.get('priority', 'unknown').upper()}\n"
                f"Category: {state.get('category', 'unknown')}\n"
                f"Severity: {state.get('severity_score', 'N/A')}/10\n"
                f"Assigned Team: {state.get('assigned_team', 'TBD')}\n"
                f"Reporter: {state.get('reporter_name', 'Unknown')} "
                f"({state.get('reporter_email', '')})\n\n"
                f"Description:\n{state.get('description', '')}\n\n"
                f"Triage Summary:\n{state.get('triage_summary', 'Pending triage...')}\n\n"
                f"{'=' * 40}\n"
                f"View ticket in Peppermint: "
                f"http://localhost:3001/issue/{state['incident_id'][:8]}"
            )

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{APPRISE_URL}/notify",
                        json={
                            "urls": email_url,
                            "title": subject,
                            "body": email_body,
                            "type": "info",
                        },
                    )
                    if resp.status_code != 200:
                        logger.error("notification_hook: Email error: %s", resp.text)
                    else:
                        logger.info("notification_hook: Email sent for incident %s", state["incident_id"])

            except httpx.RequestError as e:
                logger.error("notification_hook: Failed to send email: %s", e)
        else:
            logger.warning("notification_hook: EMAIL_SMTP_URL not configured, skipping email")

    # ── Send Discord ──
    if send_discord:
        discord_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
        if discord_url:
            # Discord-friendly format (markdown, no special chars)
            discord_body = (
                f"**[{state.get('priority', 'unknown').upper()}] "
                f"[{state.get('category', 'unknown')}]** "
                f"Incident `{state['incident_id'][:8]}`\n\n"
                f"**Reporter:** {state.get('reporter_name', 'Unknown')}\n"
                f"**Severity:** {state.get('severity_score', 'N/A')}/10\n"
                f"**Team:** {state.get('assigned_team', 'TBD')}\n\n"
                f"**Description:**\n{state.get('description', '')}\n\n"
                f"**Triage:**\n{state.get('triage_summary', 'Pending...')[:500]}"
            )

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{APPRISE_URL}/notify",
                        json={
                            "urls": discord_url,
                            "title": subject,
                            "body": discord_body,
                            "type": "info",
                        },
                    )
                    if resp.status_code != 200:
                        logger.error("notification_hook: Discord error: %s", resp.text)
                    else:
                        logger.info("notification_hook: Discord sent for incident %s", state["incident_id"])

            except httpx.RequestError as e:
                logger.error("notification_hook: Failed to send Discord: %s", e)
        else:
            logger.warning("notification_hook: DISCORD_WEBHOOK_URL not configured, skipping discord")


# ─── Auto-register hooks on module import ─────────────────────────────────────
register_hook(peppermint_hook)
register_hook(notification_hook)
