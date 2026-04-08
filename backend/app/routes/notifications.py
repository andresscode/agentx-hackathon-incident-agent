import httpx
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

APPRISE_URL = os.environ.get("APPRISE_URL", "http://apprise:8000")


class NotificationRequest(BaseModel):
    urls: str
    title: str
    body: str
    notify_type: str = "info"


class IncidentCreatedWebhook(BaseModel):
    incident_id: str
    name: str
    email: str
    description: str


@router.post("/api/notify")
async def send_notification(request: NotificationRequest):
    """Send a notification via Apprise service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{APPRISE_URL}/notify",
                json={
                    "urls": request.urls,
                    "title": request.title,
                    "body": request.body,
                    "type": request.notify_type,
                },
                timeout=30.0
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Apprise service error: {response.text}"
                )

            return {"success": True, "message": "Notification sent"}

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to Apprise service: {str(e)}"
        )


@router.post("/api/webhook/incident-created")
async def incident_created_webhook(data: IncidentCreatedWebhook):
    """Webhook endpoint for incident creation notifications"""
    # Get notification URLs from environment
    slack_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    email_url = os.environ.get("EMAIL_SMTP_URL", "")

    urls = []
    if slack_url:
        urls.append(slack_url)
    if email_url:
        urls.append(email_url)

    if not urls:
        return {"success": False, "message": "No notification URLs configured"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{APPRISE_URL}/notify",
                json={
                    "urls": ",".join(urls),
                    "title": f"New Incident: {data.incident_id}",
                    "body": f"Incident {data.incident_id} created by {data.name} ({data.email})\n\n{data.description}",
                    "type": "info",
                },
                timeout=30.0
            )

            if response.status_code != 200:
                return {"success": False, "message": f"Apprise error: {response.text}"}

            return {"success": True, "message": "Incident notification sent"}

    except httpx.RequestError as e:
        return {"success": False, "message": f"Failed to connect to Apprise: {str(e)}"}