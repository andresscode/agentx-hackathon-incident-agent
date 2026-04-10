"""Webhook endpoints for external services (Peppermint, etc)."""

import json
import logging
import re

import httpx
from fastapi import APIRouter, Request

from ..config import settings

logger = logging.getLogger("uvicorn.error")

router = APIRouter()

# Track recently processed tickets to prevent duplicate notifications
# Format: {ticket_id: timestamp}
_processed_tickets: dict[str, float] = {}
DEDUP_WINDOW_SECONDS = 300  # Ignore duplicates for 5 minutes


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


def parse_peppermint_webhook_body(raw: dict) -> dict:
    """Parse the Peppermint webhook payload.

    Peppermint sends:
      {"headers": {...}, "body": "{\"data\": \"Ticket <id> created by <email>, status changed to Completed\"}"}
    """
    result = {
        "id": "unknown",
        "title": "Unknown Ticket",
        "email": "",
        "status": "unknown",
        "detail": "",
        "is_completed": False,
    }

    body_str = raw.get("body", "")
    if not body_str:
        return result

    # body might be a JSON string or plain text
    try:
        inner = json.loads(body_str)
        if isinstance(inner, dict):
            text = inner.get("data", body_str)
        else:
            text = str(inner)
    except (json.JSONDecodeError, TypeError):
        text = body_str

    # Extract ticket ID (UUID pattern)
    id_match = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", text)
    if id_match:
        result["id"] = id_match.group(0)

    # Extract email
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    if email_match:
        result["email"] = email_match.group(0)

    # Extract status
    status_match = re.search(r"status changed to (\w+)", text, re.IGNORECASE)
    if status_match:
        result["status"] = status_match.group(1)
        result["is_completed"] = result["status"].lower() in ("completed", "closed", "done", "resolved")

    # Use the full text as detail
    result["detail"] = text
    # Use part before "created by" as title
    title_match = re.match(r"Ticket [^\s]+ created by", text)
    if title_match:
        result["title"] = title_match.group(0).replace(" created by", "").replace("Ticket ", "")

    return result


@router.post("/webhooks/peppermint")
async def peppermint_ticket_webhook(request: Request):
    """Receive webhook from Peppermint when a ticket status changes.

    When a ticket is closed (completed), sends a completion email to the
    original submitter via Apprise.
    """
    try:
        payload = await request.json()
    except Exception:
        return {"success": False, "message": "Invalid JSON payload"}

    logger.info("Webhook payload received: %s", payload)

    # Parse the nested body format
    data = parse_peppermint_webhook_body(payload)
    logger.info(
        "Webhook parsed: id=%s, email=%s, status=%s, completed=%s",
        data["id"],
        data["email"],
        data["status"],
        data["is_completed"],
    )

    if not data["is_completed"]:
        logger.info("Webhook: ticket %s status change to %s (not completed, ignoring)", data["id"], data["status"])
        return {"success": True, "message": "Status change ignored (ticket not completed)"}

    # Build email URL
    email_url = build_apprise_email_url(settings.EMAIL_SMTP_URL)
    if not email_url:
        logger.error("Webhook: EMAIL_SMTP_URL not configured")
        return {"success": False, "message": "EMAIL_SMTP_URL not configured"}

    email_url = f"{email_url}&to={data['email']}"

    # Build completion email content

    ticket_ref = data["id"][:8] if len(data["id"]) > 8 else data["id"]
    subject = f"Your issue has been resolved (Ref: {ticket_ref})"
    body = (
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
        "<tr><td style='background:#16a34a;"
        "padding:24px 32px;'>"
        "<h1 style='margin:0;color:#fff;font-size:20px;"
        "font-weight:600;'>"
        "\u2705 Your issue has been resolved</h1>"
        "<p style='margin:6px 0 0;color:#dcfce7;"
        f"font-size:13px;'>Reference: {ticket_ref}</p>"
        "</td></tr>"
        # Body
        "<tr><td style='padding:28px 32px 12px;'>"
        "<p style='margin:0;color:#334155;"
        "font-size:15px;line-height:1.6;'>Hi,</p>"
        "<p style='margin:12px 0 0;color:#334155;"
        "font-size:15px;line-height:1.6;'>"
        "Good news! The issue you reported has been "
        "reviewed and resolved by our team.</p>"
        "<p style='margin:12px 0 0;color:#334155;"
        "font-size:15px;line-height:1.6;'>"
        "If you're still experiencing any problems or "
        "have additional questions, simply reply to this "
        "email and we'll be happy to help.</p>"
        "</td></tr>"
        # Footer
        "<tr><td style='background:#f8fafc;"
        "border-top:1px solid #e2e8f0;padding:20px 32px;'>"
        "<p style='margin:0;color:#94a3b8;font-size:12px;"
        "line-height:1.5;text-align:center;'>"
        "You're receiving this because you submitted a "
        "report. Thank you for your patience.</p>"
        "</td></tr>"
        "</table>"
        "</td></tr></table>"
        "</body></html>"
    )

    # Send via Apprise
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.APPRISE_URL}/notify",
                json={
                    "urls": email_url,
                    "title": subject,
                    "body": body,
                    "type": "info",
                    "format": "html",
                },
            )
            if resp.status_code != 200:
                logger.error("Webhook: Apprise error: %s", resp.text)
                return {"success": False, "message": f"Apprise error: {resp.text}"}

            logger.info("Webhook: completion email sent for ticket %s to %s", data["id"], data["email"])
            return {"success": True, "message": "Completion email sent", "recipient": data["email"]}

    except httpx.RequestError as e:
        logger.error("Webhook: Failed to connect to Apprise: %s", e)
        return {"success": False, "message": f"Failed to connect to Apprise: {e}"}
