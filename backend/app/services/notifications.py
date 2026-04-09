import logging
import os
from dataclasses import dataclass
import urllib.parse

import httpx

logger = logging.getLogger("uvicorn.error")

APPRISE_URL = os.environ.get("APPRISE_URL", "http://apprise:8000")


def build_apprise_email_url(raw_url: str) -> str:
    if not raw_url:
        return ""

    parsed = urllib.parse.urlparse(raw_url)
    if parsed.scheme == "mailto":
        return raw_url
    if parsed.scheme != "smtp":
        return raw_url

    if not parsed.username or not parsed.password or not parsed.hostname or not parsed.port:
        logger.warning("EMAIL_SMTP_URL is invalid; skipping email notification URL")
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


@dataclass
class IncidentNotification:
    incident_id: str
    name: str
    email: str
    description: str


async def notify_incident_created(data: IncidentNotification) -> dict[str, str | bool]:
    slack_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    raw_email_url = os.environ.get("EMAIL_SMTP_URL", "")
    discord_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    email_url = build_apprise_email_url(raw_email_url)

    urls = [u for u in [slack_url, email_url, discord_url] if u]

    if not urls:
        logger.warning("No notification URLs configured, skipping notification")
        return {"success": False, "message": "No notification URLs configured"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{APPRISE_URL}/notify",
                json={
                    "urls": ",".join(urls),
                    "title": f"New Incident: {data.incident_id}",
                    "body": (
                        f"Incident {data.incident_id} created by "
                        f"{data.name} ({data.email})\n\n{data.description}"
                    ),
                    "type": "info",
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                return {"success": False, "message": f"Apprise error: {response.text}"}

            return {"success": True, "message": "Incident notification sent"}

    except httpx.RequestError as e:
        logger.error("Failed to connect to Apprise: %s", e)
        return {"success": False, "message": f"Failed to connect to Apprise: {e!s}"}


async def send_email(to: str, subject: str, body: str) -> dict[str, str | bool]:
    """Send an email to a specific recipient using the configured SMTP settings."""
    raw_email_url = os.environ.get("EMAIL_SMTP_URL", "")
    email_url = build_apprise_email_url(raw_email_url)

    if not email_url:
        logger.warning("EMAIL_SMTP_URL not configured, skipping email")
        return {"success": False, "message": "EMAIL_SMTP_URL not configured"}

    # Append recipient to the URL
    if "&to=" not in email_url:
        email_url = f"{email_url}&to={urllib.parse.quote(to)}"
    else:
        email_url = f"{email_url},{urllib.parse.quote(to)}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{APPRISE_URL}/notify",
                json={
                    "urls": email_url,
                    "title": subject,
                    "body": body,
                    "type": "info",
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                return {"success": False, "message": f"Apprise error: {response.text}"}

            return {"success": True, "message": "Email sent successfully"}

    except httpx.RequestError as e:
        logger.error("Failed to connect to Apprise: %s", e)
        return {"success": False, "message": f"Failed to connect to Apprise: {e!s}"}
