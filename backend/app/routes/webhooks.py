"""Webhook endpoints for external services (Peppermint, etc)."""

import json
import logging
import re

import httpx
from fastapi import APIRouter, Request

from ..config import settings

logger = logging.getLogger("uvicorn.error")

router = APIRouter()


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
    subject = f"✅ Ticket Resolved: {data['title']}"
    body = (
        f"Your ticket has been marked as completed.\n\n"
        f"Ticket ID: {data['id']}\n"
        f"Title: {data['title']}\n\n"
        f"Details: {data['detail']}\n\n"
        f"If you have any further questions or the issue persists, "
        f"please reply to this ticket."
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
