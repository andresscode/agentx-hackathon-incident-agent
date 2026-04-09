import logging
from collections.abc import Awaitable, Callable
from typing import Any

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


async def peppermint_hook(state: dict[str, Any]) -> None:
    """Create a Peppermint ticket from triage results."""
    from ..services.peppermint import peppermint  # type: ignore[import-not-found]

    title = (
        f"[{state['priority'].upper()}] [{state['category']}] "
        f"Incident {state['incident_id'][:8]}"
    )
    await peppermint.create_ticket(
        title=title,
        name=state["reporter_name"],
        detail=state.get("triage_summary") or state["description"],
        priority=state["priority"],
        ticket_type="incident",
        email=state["reporter_email"],
    )
    logger.info("Peppermint ticket created for incident %s", state["incident_id"])


async def notification_hook(state: dict[str, Any]) -> None:
    """Send Apprise notification (Slack + email) about the triaged incident."""
    from ..services.notifications import (  # type: ignore[import-not-found]
        IncidentNotification,
        notify_incident_created,
    )

    await notify_incident_created(
        IncidentNotification(
            incident_id=state["incident_id"],
            name=state["reporter_name"],
            email=state["reporter_email"],
            description=state.get("triage_summary") or state["description"],
        )
    )
    logger.info("Notification sent for incident %s", state["incident_id"])
