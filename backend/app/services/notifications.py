import logging
import os
from dataclasses import dataclass

import httpx

logger = logging.getLogger("uvicorn.error")

APPRISE_URL = os.environ.get("APPRISE_URL", "http://apprise:8000")


@dataclass
class IncidentNotification:
    incident_id: str
    name: str
    email: str
    description: str


async def notify_incident_created(data: IncidentNotification) -> dict[str, str | bool]:
    slack_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    email_url = os.environ.get("EMAIL_SMTP_URL", "")

    urls = [u for u in [slack_url, email_url] if u]

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
