import os

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.notifications import IncidentNotification, notify_incident_created

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
async def send_notification(request: NotificationRequest) -> dict[str, str | bool]:
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
                timeout=30.0,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Apprise service error: {response.text}",
                )

            return {"success": True, "message": "Notification sent"}

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503, detail=f"Failed to connect to Apprise service: {e!s}"
        ) from e


@router.post("/api/webhook/incident-created")
async def incident_created_webhook(
    data: IncidentCreatedWebhook,
) -> dict[str, str | bool]:
    """Webhook endpoint for external callers to trigger incident notifications"""
    return await notify_incident_created(
        IncidentNotification(
            incident_id=data.incident_id,
            name=data.name,
            email=data.email,
            description=data.description,
        )
    )
