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


def _build_html_email(
    reference: str,
    name: str,
    description: str,
    peppermint_url: str | None = None,
    triage_summary: str | None = None,
) -> str:
    """Build a professional HTML email with inline styles."""
    summary_section = ""
    if triage_summary:
        clean = triage_summary[:400].replace("\n", "<br>")
        summary_section = f"""
            <tr>
                <td style="padding: 0 32px 16px; font-family: Arial, Helvetica, sans-serif; font-size: 14px; color: #475569;">
                    <strong style="color: #1e293b;">Triage Summary:</strong><br>
                    {clean}
                </td>
            </tr>
        """

    view_link = ""
    if peppermint_url:
        view_link = f"""
            <tr>
                <td style="padding: 0 32px 24px;">
                    <a href="{peppermint_url}"
                       style="display: inline-block; padding: 10px 24px; background-color: #2563eb; color: #ffffff;
                              text-decoration: none; border-radius: 6px; font-family: Arial, Helvetica, sans-serif;
                              font-size: 14px; font-weight: bold;">
                        View Ticket in Peppermint →
                    </a>
                </td>
            </tr>
        """

    return f"""
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#f0f0f0" style="background-color: #f0f0f0;">
            <tr>
                <td align="center" style="padding: 32px 16px;">
                    <table role="presentation" width="600" cellpadding="0" cellspacing="0" bgcolor="#ffffff"
                           style="border-radius: 12px; overflow: hidden; max-width: 600px; width: 100%;">
                        <!-- Header -->
                        <tr>
                            <td bgcolor="#1e293b" style="background-color: #1e293b; padding: 32px; border-radius: 12px 12px 0 0;">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td style="font-family: Arial, Helvetica, sans-serif; color: #ffffff; font-size: 24px; font-weight: bold;">
                                            We received your report
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding-top: 8px; font-family: Arial, Helvetica, sans-serif; color: #94a3b8; font-size: 14px;">
                                            Reference: {reference}
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        <!-- Body -->
                        <tr>
                            <td style="padding: 32px;">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td style="font-family: Arial, Helvetica, sans-serif; font-size: 16px; color: #334155;">
                                            Hi {name},
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding-top: 16px; font-family: Arial, Helvetica, sans-serif; font-size: 14px; color: #475569; line-height: 1.6;">
                                            Thank you for your incident report. Our team has been notified and is reviewing the issue now.
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding-top: 24px; font-family: Arial, Helvetica, sans-serif; font-size: 16px; color: #1e293b; font-weight: bold;">
                                            Your Report
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding-top: 8px; font-family: Arial, Helvetica, sans-serif; font-size: 14px; color: #475569; line-height: 1.6;">
                                            {description.replace("\n", "<br>")}
                                        </td>
                                    </tr>
                                    {summary_section}
                                    {view_link}
                                </table>
                            </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 16px 32px 24px; border-top: 1px solid #e2e8f0; background-color: #f8fafc;">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td style="font-family: Arial, Helvetica, sans-serif; font-size: 12px; color: #94a3b8; line-height: 1.5;">
                                            You're receiving this because you submitted a report. If you have questions, reply to this email.
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    """.strip()


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


def _build_html_body(state: dict[str, Any]) -> str:
    """Build a polished HTML email body for end-user notifications."""
    import html as html_mod

    reporter = state.get("reporter_name", "")
    description = html_mod.escape(state.get("description", ""))
    ticket_id = state["incident_id"][:8]
    greeting = (
        f"Hi {html_mod.escape(reporter)},"
        if reporter
        else "Hi,"
    )

    return (
        "<html>"
        "<body style='margin:0;padding:0;background:#f4f4f5;"
        "font-family:Arial,Helvetica,sans-serif;'>"
        "<table width='100%' cellpadding='0' cellspacing='0'"
        " style='background:#f4f4f5;padding:32px 0;'>"
        "<tr><td align='center'>"
        "<table width='600' cellpadding='0' cellspacing='0'"
        " style='background:#fff;border-radius:8px;"
        "overflow:hidden;"
        "box-shadow:0 1px 3px rgba(0,0,0,0.1);'>"
        # Header
        "<tr><td style='background:#1e293b;"
        "padding:24px 32px;'>"
        "<h1 style='margin:0;color:#fff;font-size:20px;"
        "font-weight:600;'>We received your report</h1>"
        "<p style='margin:6px 0 0;color:#94a3b8;"
        f"font-size:13px;'>Reference: {ticket_id}</p>"
        "</td></tr>"
        # Greeting
        "<tr><td style='padding:28px 32px 12px;'>"
        "<p style='margin:0;color:#334155;"
        f"font-size:15px;line-height:1.6;'>{greeting}</p>"
        "<p style='margin:12px 0 0;color:#334155;"
        "font-size:15px;line-height:1.6;'>"
        "Thank you for reaching out. We've received your "
        "report and our team is already looking into it. "
        "We'll follow up with you as soon as we have an "
        "update.</p>"
        "</td></tr>"
        # Your Report
        "<tr><td style='padding:8px 32px 24px;'>"
        "<h3 style='margin:0 0 8px;color:#1e293b;"
        "font-size:14px;font-weight:600;'>Your Report</h3>"
        "<p style='margin:0;color:#475569;font-size:14px;"
        f"line-height:1.6;white-space:pre-wrap;'>"
        f"{description}</p>"
        "</td></tr>"
        # Footer
        "<tr><td style='background:#f8fafc;"
        "border-top:1px solid #e2e8f0;padding:20px 32px;'>"
        "<p style='margin:0;color:#94a3b8;font-size:12px;"
        "line-height:1.5;text-align:center;'>"
        "You're receiving this because you submitted a "
        "report. If you have questions, reply to this "
        "email.</p>"
        "</td></tr>"
        "</table>"
        "</td></tr></table>"
        "</body></html>"
    )


def _extract_triage_summary(triage: str) -> str:
    """Pull the Summary section from triage markdown."""
    import re

    if not triage:
        return "Pending analysis..."
    match = re.search(
        r"###?\s*Summary\s*\n(.+?)(?:\n###?|\Z)",
        triage,
        re.DOTALL,
    )
    if not match:
        return "Pending analysis..."
    text = match.group(1).strip()
    # Strip markdown formatting
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


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


def _clean_for_peppermint(md: str) -> str:
    """Convert markdown triage summary to clean structured plain text."""
    import re

    md = md.replace('\\n', '\n')

    sections = {
        'summary': '',
        'probable root cause': '',
        'affected components': '',
        'recommended actions': '',
        'related code': '',
        'suggested runbook': '',
    }

    # Extract sections
    current = None
    for line in md.splitlines():
        stripped = line.strip().lower()
        matched = None
        for key in sections:
            if stripped == key or stripped.startswith(key + '\n') or re.match(r'^#{1,6}\s*' + key, stripped):
                matched = key
                break
        if matched:
            current = matched
            continue
        if current and line.strip():
            # Clean markdown syntax
            clean = line.replace('**', '').replace('*', '').replace('`', '')
            clean = re.sub(r'^[\s]*[-*+]\s', '  - ', clean)
            clean = re.sub(r'^#{1,6}\s*', '', clean)
            sections[current] += clean + '\n'

    # Build output
    parts = []
    parts.append('INCIDENT TRIAGE REPORT')
    parts.append('=' * 21)
    parts.append('')

    for section, content in sections.items():
        if not content.strip():
            continue
        parts.append(section.upper())
        parts.append('-' * len(section))
        parts.append(content.strip())
        parts.append('')

    return '\n'.join(parts).strip()


async def integrations_hook(state: dict[str, Any]) -> None:
    """Create Peppermint ticket, then send email + Discord with ticket link."""
    from ..services.peppermint import peppermint  # type: ignore[import-not-found]

    # ── 1. Create Peppermint Ticket ──
    title = (
        f"[{state['priority'].upper()}] [{state['category']}] "
        f"Incident {state['incident_id'][:8]}"
    )
    header = (
        f"Priority: {state.get('priority', 'unknown').upper()}\n"
        f"Category: {state.get('category', 'unknown').upper()}\n"
        f"Severity: {state.get('severity_score', 'N/A')}/10\n"
        f"Assigned Team: {state.get('assigned_team', 'TBD')}"
    )
    raw_summary = state.get("triage_summary") or state["description"]
    clean_detail = _clean_for_peppermint(raw_summary)
    full_detail = header + '\n\n' + clean_detail

    # Workaround: Peppermint double-escapes newlines on their side.
    # Replace \n with <br> so they survive Peppermint's rendering pipeline.
    full_detail = full_detail.replace('\n', '<br>')

    ticket = await peppermint.create_ticket(
        title=title,
        name=state["reporter_name"],
        detail=full_detail,
        priority=state["priority"],
        ticket_type="incident",
        email=state["reporter_email"],
    )
    ticket_id = ticket.get("id", state["incident_id"][:8])
    peppermint_url = f"http://localhost:3001/issue/{ticket_id}"
    logger.info("Peppermint ticket created for incident %s: %s", state["incident_id"], ticket_id)

    # ── 2. Send Email ──
    if settings.NOTIFY_EMAIL_ON_TRIAGE:
        email_url = _build_apprise_email_url(settings.EMAIL_SMTP_URL)
        if email_url:
            recipients = [state.get("reporter_email", "")]
            recipients.extend(settings.NOTIFY_CC_EMAILS)
            email_url = f"{email_url}&to={','.join(recipients)}"

            email_body = _build_html_body(state)
            email_subject = (
                "We received your report "
                f"(Ref: {state['incident_id'][:8]})"
            )

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{settings.APPRISE_URL}/notify",
                        json={
                            "urls": email_url,
                            "title": email_subject,
                            "body": email_body,
                            "type": "info",
                            "format": "html",
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

    # ── 3. Send Discord ──
    if settings.NOTIFY_DISCORD_ON_TRIAGE:
        if settings.DISCORD_WEBHOOK_URL:
            priority = state.get(
                'priority', 'unknown'
            ).upper()
            category = state.get('category', 'unknown')
            severity = state.get('severity_score', 'N/A')
            team = state.get('assigned_team', 'TBD')
            iid = state['incident_id'][:8]
            reporter = state.get(
                'reporter_name', 'Unknown'
            )
            desc = state.get('description', '')
            summary = _extract_triage_summary(
                state.get('triage_summary', '')
            )

            discord_body = (
                f"## \U0001f6a8 Incident `{iid}`\n\n"
                f"> **{desc}**\n\n"
                f"\U0001f4cb **Details**\n"
                f"- **Priority:** {priority}\n"
                f"- **Category:** {category}\n"
                f"- **Severity:** {severity}/10\n"
                f"- **Team:** {team}\n"
                f"- **Reporter:** {reporter}\n\n"
                f"\U0001f50d **Analysis**\n"
                f"{summary}\n\n"
                f"\U0001f517 [View in Peppermint]"
                f"({peppermint_url})"
            )

            try:
                async with httpx.AsyncClient(
                    timeout=30.0
                ) as client:
                    resp = await client.post(
                        f"{settings.APPRISE_URL}/notify",
                        json={
                            "urls": settings.DISCORD_WEBHOOK_URL,
                            "title": "",
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
register_hook(integrations_hook)
