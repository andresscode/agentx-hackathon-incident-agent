import logging
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from ..config import settings

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


def _build_apprise_email_url(raw_url: str) -> str:
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

    Controlled by settings module (env-backed):
      settings.NOTIFY_EMAIL_ON_TRIAGE
      settings.NOTIFY_DISCORD_ON_TRIAGE
      settings.NOTIFY_CC_EMAILS
    """
    urls: list[str] = []

    # ── Email ──
    if settings.NOTIFY_EMAIL_ON_TRIAGE:
        email_url = _build_apprise_email_url(settings.EMAIL_SMTP_URL)
        if email_url:
            recipients = [state.get("reporter_email", "")]
            recipients.extend(settings.NOTIFY_CC_EMAILS)
            email_url = f"{email_url}&to={','.join(recipients)}"
            urls.append(email_url)
        else:
            logger.warning("notification_hook: EMAIL_SMTP_URL not configured, skipping email")

    # ── Discord ──
    if settings.NOTIFY_DISCORD_ON_TRIAGE:
        if settings.DISCORD_WEBHOOK_URL:
            urls.append(settings.DISCORD_WEBHOOK_URL)
        else:
            logger.warning("notification_hook: DISCORD_WEBHOOK_URL not configured, skipping discord")

    if not urls:
        logger.info("notification_hook: no channels configured, skipping")
        return

    subject = (
        f"[{state.get('priority', 'unknown').upper()}] "
        f"[{state.get('category', 'unknown')}] Incident {state['incident_id'][:8]}"
    )

    body = _build_rich_body(state)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.APPRISE_URL}/notify",
                json={
                    "urls": ",".join(urls),
                    "title": subject,
                    "body": body,
                    "type": "info",
                },
            )
            if resp.status_code != 200:
                logger.error("notification_hook: Apprise error: %s", resp.text)
            else:
                logger.info("notification_hook: sent for incident %s", state["incident_id"])

    except httpx.RequestError as e:
        logger.error("notification_hook: failed to connect to Apprise: %s", e)


# ─── Auto-register hooks on module import ─────────────────────────────────────
register_hook(peppermint_hook)
register_hook(notification_hook)
