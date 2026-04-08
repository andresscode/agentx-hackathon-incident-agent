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


@app.post("/apprise/notify")
async def apprise_notify(data: AppriseNotify):
    """Send a notification via Apprise.

    Requires Apprise API running at APPRISER_URL.
    """
    payload = {"title": data.title, "body": data.body}
    if data.tag:
        payload["urls"] = data.tag  # Use tag as url selector if provided

    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{APPRISER_API}/notify", json=payload)
        return {"status": resp.status_code, "body": resp.text}


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
    title: str = "test value"
    description: str = "test description"
    notify_email: str = "test-user@example.com"


@app.post("/test/ticket-and-notify")
async def test_ticket_and_notify(data: IncidentAlert):
    """Create a ticket AND send an email in one call."""

    # 1. Create the Ticket
    ticket = await peppermint.create_ticket(
        title=data.title,
        name=data.title,
        detail=data.description,
        priority="critical",
        ticket_type="incident",
    )

    # 2. Send the Email via Apprise
    email_url = f"mailtos://agentx.nameless:tjmmywblobrggdba@gmail.com?smtp=smtp.gmail.com&port=587&mode=starttls&to={data.notify_email}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{APPRISER_API}/notify",
            json={
                "urls": email_url,
                "title": f"New Incident: {data.title}",
                "body": f"A new ticket has been created.\n\nDetails:\n{data.description}\n\nTicket ID: {ticket['id']}",
            },
        )

    return {
        "success": True,
        "ticket_created": {
            "id": ticket["id"],
            "title": data.title,
            "status": "created"
        },
        "notification_sent": {
            "channel": "email",
            "recipient": data.notify_email,
            "status": "success" if resp.status_code == 200 else "failed"
        }
    }
