"""Test server to manually verify Peppermint & Apprise API calls."""

import os
import httpx
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.services.peppermint import peppermint

app = FastAPI(title="Peppermint & Apprise Test Server")

# Configuration - Reads APPRISE_URL from Docker environment
APPRISER_API = os.getenv("APPRISE_URL", "http://apprise:8000")

# ─── Peppermint Endpoints ─────────────────────────────────────────────────────

@app.get("/peppermint/health")
async def peppermint_health():
    """Check if Peppermint is reachable."""
    return await peppermint.request("GET", "/auth/check")


@app.post("/peppermint/ticket/create")
async def create_ticket(
    title: str,
    name: str,
    priority: str = "medium",
    ticket_type: str = "incident",
    email: str = "test@hackathon.com",
):
    """Create a test ticket."""
    try:
        return await peppermint.create_ticket(
            title=title,
            name=name,
            priority=priority,
            ticket_type=ticket_type,
            email=email,
        )
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/peppermint/tickets/all")
async def get_all_tickets():
    """Get all tickets."""
    return await peppermint.get_all_tickets()


@app.get("/peppermint/ticket/{ticket_id}")
async def get_ticket(ticket_id: str):
    """Get a specific ticket."""
    try:
        return await peppermint.get_ticket(ticket_id)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.put("/peppermint/ticket/{ticket_id}/status")
async def update_ticket_status(ticket_id: str, status: str):
    """Update ticket workflow status.

    status: needs_support | in_progress | in_review | done
    """
    try:
        return await peppermint.update_ticket(ticket_id, status=status)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.put("/peppermint/ticket/{ticket_id}/close")
async def close_ticket(ticket_id: str):
    """Close a ticket (set isComplete=true)."""
    try:
        return await peppermint.close_ticket(ticket_id)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.put("/peppermint/ticket/{ticket_id}/reopen")
async def reopen_ticket(ticket_id: str):
    """Reopen a ticket (set isComplete=false)."""
    try:
        return await peppermint.reopen_ticket(ticket_id)
    except Exception as e:
        raise HTTPException(500, str(e))


# ─── Apprise Endpoints ────────────────────────────────────────────────────────

class AppriseNotify(BaseModel):
    """Apprise notification payload."""
    title: str
    body: str
    tag: Optional[str] = None  # e.g., "slack", "email", "discord"


class SimpleEmailNotify(BaseModel):
    """Simple email notification payload — no URL building needed."""
    to: str
    subject: str = "Notification"
    body: str


@app.post("/apprise/notify")
async def apprise_notify(data: AppriseNotify):
    """Send a notification via Apprise.

    Requires Apprise API running at APPRISER_URL.
    """
    payload = {"title": data.title, "body": data.body}
    if data.tag:
        payload["urls"] = data.tag  # Use tag as url selector if provided


@app.post("/apprise/email")
async def apprise_email_notify(data: SimpleEmailNotify):
    """Send an email to a specific recipient.

    No complex URL building needed — the backend uses EMAIL_SMTP_URL from .env
    and appends the recipient automatically.
    """
    from .services.notifications import build_apprise_email_url

    raw_email_url = os.getenv("EMAIL_SMTP_URL", "")
    if not raw_email_url:
        return {
            "success": False,
            "message": "EMAIL_SMTP_URL not configured in .env",
            "status_code": 400
        }

    # Convert smtp:// -> mailtos:// format for Apprise, then add recipient
    email_url = build_apprise_email_url(raw_email_url)
    if not email_url:
        return {
            "success": False,
            "message": "EMAIL_SMTP_URL is invalid. Use format: smtp://user:pass@smtp.gmail.com:587",
            "status_code": 400
        }
    if "&to=" not in email_url:
        email_url = f"{email_url}&to={data.to}"

    timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{APPRISER_API}/notify",
                json={
                    "urls": email_url,
                    "title": data.subject,
                    "body": data.body,
                },
            )

        return {
            "success": resp.status_code == 200,
            "recipient": data.to,
            "message": "Email sent successfully" if resp.status_code == 200 else resp.text,
            "status_code": resp.status_code
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to send email: {str(e)}",
            "status_code": 500
        }


# ─── Combined Workflow Test ───────────────────────────────────────────────────

@app.post("/test/full-workflow")
async def test_full_workflow():
    """Test: Create ticket → Update status → Close."""

    # 1. Create ticket
    ticket = await peppermint.create_ticket(
        title="Workflow Test",
        name="Test Workflow",
        detail="Testing full ticket workflow",
        priority="medium",
        ticket_type="incident",
    )
    ticket_id = ticket["id"]

    # 2. Update to in_progress
    await peppermint.update_ticket(ticket_id, status="in_progress")

    # 3. Close ticket
    await peppermint.close_ticket(ticket_id)

    # 4. Get final state
    final = await peppermint.get_ticket(ticket_id)

    return {
        "workflow": "complete",
        "ticket_id": ticket_id,
        "final_state": final,
    }


class IncidentAlert(BaseModel):
    """Incident data with optional notification email."""
    # Ticket fields
    title: str = "test value"
    description: str = "test description"
    priority: str = "critical"  # low, medium, high, critical
    ticket_type: str = "incident"  # incident, request, problem
    reporter_name: str = "System"
    reporter_email: str = "system@example.com"
    environment: str = "production"  # production, staging, dev
    affected_service: str = "unknown"
    tags: Optional[list[str]] = None

    # Email notification fields
    notify_email: Optional[str] = None  # Set to enable email notification
    cc_emails: Optional[list[str]] = None  # Additional email recipients
    email_subject: Optional[str] = None  # Custom email subject

    # Discord notification fields
    notify_discord: bool = False  # Set to enable Discord notification
    discord_title: Optional[str] = None  # Custom Discord title


class FullIncidentAlert(BaseModel):
    """Full incident alert — creates ticket + optional email + optional discord."""
    # Ticket fields
    title: str
    description: str
    priority: str = "critical"
    ticket_type: str = "incident"
    reporter_name: str = "System"
    reporter_email: str = "system@example.com"
    environment: str = "production"
    affected_service: str = "unknown"
    tags: Optional[list[str]] = None

    # Email (optional — omit or set null to skip)
    notify_email: Optional[str] = None
    cc_emails: Optional[list[str]] = None
    email_subject: Optional[str] = None

    # Discord (optional — omit or set true to enable)
    notify_discord: bool = False
    discord_title: Optional[str] = None


@app.post("/test/full-incident")
async def test_full_incident(data: FullIncidentAlert):
    """Create a ticket AND send notifications (email + discord).

    Both are optional: omit notify_email to skip email.
    Set notify_discord=false to skip Discord.
    If both are skipped, only the ticket is created.
    """
    from .services.notifications import build_apprise_email_url

    # 1. Create the Ticket
    ticket = await peppermint.create_ticket(
        title=data.title,
        name=data.title,
        detail=f"[{data.environment.upper()}] {data.description}\n\n"
               f"Reporter: {data.reporter_name} ({data.reporter_email})\n"
               f"Service: {data.affected_service}\n"
               f"Tags: {', '.join(data.tags) if data.tags else 'none'}",
        priority=data.priority,
        ticket_type=data.ticket_type,
        email=data.reporter_email,
    )

    # 2. Build all notification URLs
    urls = []
    email_configured = False
    discord_configured = False

    # 2a. Email
    if data.notify_email:
        raw_email_url = os.getenv("EMAIL_SMTP_URL", "")
        email_url = build_apprise_email_url(raw_email_url)
        if email_url:
            recipients = [data.notify_email]
            if data.cc_emails:
                recipients.extend(data.cc_emails)
            email_url = f"{email_url}&to={','.join(recipients)}"
            urls.append(email_url)
            email_configured = True

    # 2b. Discord
    if data.notify_discord:
        discord_url = os.getenv("DISCORD_WEBHOOK_URL", "")
        if discord_url:
            urls.append(discord_url)
            discord_configured = True

    # If no notification channels, just return ticket info
    if not urls:
        return {
            "success": True,
            "ticket_created": {
                "id": ticket["id"],
                "title": data.title,
                "priority": data.priority,
                "environment": data.environment,
                "affected_service": data.affected_service,
                "reporter": f"{data.reporter_name} <{data.reporter_email}>",
                "status": "created"
            },
            "notifications_sent": {
                "message": "No notification channels configured — ticket created only"
            }
        }

    # 3. Build content
    subject = data.email_subject or f"🚨 [{data.priority.upper()}] {data.title}"
    body = (
        f"INCIDENT NOTIFICATION\n"
        f"{'='*40}\n\n"
        f"Ticket ID: {ticket['id']}\n"
        f"Title: {data.title}\n"
        f"Priority: {data.priority.upper()}\n"
        f"Environment: {data.environment}\n"
        f"Affected Service: {data.affected_service}\n"
        f"Reporter: {data.reporter_name} ({data.reporter_email})\n"
        f"{'Tags: ' + ', '.join(data.tags) if data.tags else ''}\n\n"
        f"Description:\n{data.description}\n\n"
        f"{'='*40}\n"
        f"View ticket in Peppermint: http://localhost:3001/issue/{ticket['id']}"
    )

    # 4. Send all notifications
    timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{APPRISER_API}/notify",
            json={
                "urls": ",".join(urls),
                "title": data.discord_title or subject,
                "body": body,
            },
        )

    notify_ok = resp.status_code == 200

    return {
        "success": True,
        "ticket_created": {
            "id": ticket["id"],
            "title": data.title,
            "priority": data.priority,
            "environment": data.environment,
            "affected_service": data.affected_service,
            "reporter": f"{data.reporter_name} <{data.reporter_email}>",
            "status": "created"
        },
        "notifications_sent": {
            "email": {
                "enabled": data.notify_email is not None,
                "to": data.notify_email,
                "cc": data.cc_emails or [],
                "status": "success" if (notify_ok and email_configured) else ("not_configured" if data.notify_email else "skipped")
            },
            "discord": {
                "enabled": data.notify_discord,
                "status": "success" if (notify_ok and discord_configured) else ("not_configured" if data.notify_discord else "skipped")
            }
        }
    }


@app.post("/test/ticket-and-notify")
async def test_ticket_and_notify(data: IncidentAlert):
    """Create a ticket AND send notifications (email + discord) in one call."""
    from .services.notifications import build_apprise_email_url

    # 1. Create the Ticket with full details
    ticket = await peppermint.create_ticket(
        title=data.title,
        name=data.title,
        detail=f"[{data.environment.upper()}] {data.description}\n\n"
               f"Reporter: {data.reporter_name} ({data.reporter_email})\n"
               f"Service: {data.affected_service}\n"
               f"Tags: {', '.join(data.tags) if data.tags else 'none'}",
        priority=data.priority,
        ticket_type=data.ticket_type,
        email=data.reporter_email,
    )

    # Build notification URLs
    urls = []
    notifications_sent = []

    # 2a. Email notification
    email_status = "not_requested"
    if data.notify_email:
        raw_email_url = os.getenv("EMAIL_SMTP_URL", "")
        email_url = build_apprise_email_url(raw_email_url)
        if not email_url:
            email_status = "error: EMAIL_SMTP_URL not configured"
        else:
            recipients = [data.notify_email]
            if data.cc_emails:
                recipients.extend(data.cc_emails)
            email_url = f"{email_url}&to={','.join(recipients)}"
            urls.append(email_url)

    # 2b. Discord notification
    discord_status = "not_requested"
    if data.notify_discord:
        discord_url = os.getenv("DISCORD_WEBHOOK_URL", "")
        if not discord_url:
            discord_status = "error: DISCORD_WEBHOOK_URL not configured"
        else:
            urls.append(discord_url)

    if not urls:
        return {
            "success": True,
            "ticket_created": {
                "id": ticket["id"],
                "title": data.title,
                "priority": data.priority,
                "environment": data.environment,
                "affected_service": data.affected_service,
                "reporter": f"{data.reporter_name} <{data.reporter_email}>",
                "status": "created"
            },
            "notifications_sent": {
                "message": "No notification channels enabled. Set notify_email or notify_discord."
            }
        }

    # 3. Build notification content
    subject = data.email_subject or f"🚨 [{data.priority.upper()}] {data.title}"
    body = (
        f"INCIDENT NOTIFICATION\n"
        f"{'='*40}\n\n"
        f"Ticket ID: {ticket['id']}\n"
        f"Title: {data.title}\n"
        f"Priority: {data.priority.upper()}\n"
        f"Environment: {data.environment}\n"
        f"Affected Service: {data.affected_service}\n"
        f"Reporter: {data.reporter_name} ({data.reporter_email})\n"
        f"{'Tags: ' + ', '.join(data.tags) if data.tags else ''}\n\n"
        f"Description:\n{data.description}\n\n"
        f"{'='*40}\n"
        f"View ticket in Peppermint: http://localhost:3001/issue/{ticket['id']}"
    )

    # 4. Send all notifications at once
    timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{APPRISER_API}/notify",
            json={
                "urls": ",".join(urls),
                "title": data.discord_title or subject,
                "body": body,
            },
        )

    if resp.status_code == 200:
        email_status = "success" if data.notify_email else "not_requested"
        discord_status = "success" if data.notify_discord else "not_requested"

    return {
        "success": True,
        "ticket_created": {
            "id": ticket["id"],
            "title": data.title,
            "priority": data.priority,
            "environment": data.environment,
            "affected_service": data.affected_service,
            "reporter": f"{data.reporter_name} <{data.reporter_email}>",
            "status": "created"
        },
        "notifications_sent": {
            "email": {
                "enabled": data.notify_email is not None,
                "to": data.notify_email,
                "cc": data.cc_emails or [],
                "status": email_status
            },
            "discord": {
                "enabled": data.notify_discord,
                "status": discord_status
            }
        }
    }


class DiscordTestNotification(BaseModel):
    """Discord notification payload."""
    title: str = "🚨 Test Incident Alert"
    message: str = "This is a test incident notification"
    webhook_url: Optional[str] = None  # Optional: overrides the .env default


@app.post("/test/discord-notify")
async def test_discord_notify(data: DiscordTestNotification):
    """Send a notification to Discord via Apprise.

    If webhook_url is provided, it sends there.
    Otherwise, it uses DISCORD_WEBHOOK_URL from .env.
    """
    # Use provided URL or fallback to environment variable
    discord_url = data.webhook_url or os.getenv("DISCORD_WEBHOOK_URL", "")

    if not discord_url:
        return {
            "success": False,
            "message": "DISCORD_WEBHOOK_URL not configured in .env or request body",
            "status_code": 400
        }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{APPRISER_API}/notify",
                json={
                    "urls": discord_url,
                    "title": data.title,
                    "body": data.message,
                },
                timeout=30.0,
            )
        
        return {
            "success": resp.status_code == 200,
            "message": resp.text if resp.status_code != 200 else "Discord notification sent successfully",
            "status_code": resp.status_code
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to send Discord notification: {str(e)}",
            "status_code": 500
        }


# ─── Peppermint Webhook Listener ──────────────────────────────────────────────

@app.post("/webhooks/peppermint")
async def peppermint_completed_ticket_webhook(payload: dict):
    """Receive webhook from Peppermint when a ticket changes status.
    
    If the ticket is marked as completed, sends an email to the original submitter via Apprise.
    """
    # Peppermint sends status: true when completed, or we can check isComplete
    is_completed = payload.get("status") or payload.get("isComplete", False)
    
    if not is_completed:
        return {"success": True, "message": "Status change ignored (ticket not finished)"}

    # Extract ticket details
    ticket_id = payload.get("id", "unknown")
    title = payload.get("title", "Unknown Ticket")
    email = payload.get("email", "")  # Submitter's email
    created_by = payload.get("createdBy", {})
    
    # Fallback: try to get email from createdBy if not at root level
    if not email and isinstance(created_by, dict):
        email = created_by.get("email", "")

    if not email:
        print(f"⚠️  Ticket {ticket_id} completed but no email found in payload")
        return {"success": False, "message": "No email found in webhook payload"}

    # Build the email URL using the submitter's email as recipient
    email_url = f"mailtos://agentx.nameless:tjmmywblobrggdba@gmail.com?smtp=smtp.gmail.com&port=587&mode=starttls&to={email}"

    try:
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{APPRISER_API}/notify",
                json={
                    "urls": email_url,
                    "title": f"✅ Ticket Resolved: {title}",
                    "body": f"Your ticket (ID: {ticket_id}) has been marked as completed.\n\nIf you have any further questions or the issue persists, please reply to this ticket.",
                },
            )
        
        print(f"✅ Completion email sent to {email} for ticket {ticket_id}")
        return {
            "success": True,
            "message": f"Completion notification sent to {email}",
            "ticket_id": ticket_id
        }
    except Exception as e:
        print(f"❌ Failed to send completion email to {email}: {e}")
        return {
            "success": False,
            "message": f"Failed to send notification: {str(e)}"
        }
