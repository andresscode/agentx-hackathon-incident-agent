"""Test server to manually verify Peppermint & Apprise API calls."""

import httpx
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.services.peppermint import peppermint

app = FastAPI(title="Peppermint & Apprise Test Server")

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
    apprise_url = "http://localhost:8000/notify"  # Adjust to your Apprise URL

    payload = {"title": data.title, "body": data.body}
    if data.tag:
        payload["tag"] = data.tag

    async with httpx.AsyncClient() as client:
        resp = await client.post(apprise_url, json=payload)
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
