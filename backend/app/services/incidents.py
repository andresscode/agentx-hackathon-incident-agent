import logging
import uuid
from dataclasses import dataclass

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session, get_session
from ..models import Incident, IncidentCategory, IncidentPriority, IncidentStatus

logger = logging.getLogger("uvicorn.error")


@dataclass
class IncidentPayload:
    name: str
    email: str
    description: str
    image: bytes | None = None
    image_filename: str | None = None


@dataclass
class IncidentResult:
    success: bool
    id: str


class IncidentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_incident(self, data: IncidentPayload) -> IncidentResult:
        incident = Incident(
            name=data.name,
            email=data.email,
            description=data.description,
            image_data=data.image,
            image_filename=data.image_filename,
            status=IncidentStatus.PENDING,
        )
        self.session.add(incident)
        await self.session.commit()
        await self.session.refresh(incident)
        return IncidentResult(success=True, id=str(incident.id))

    async def get_incident(self, incident_id: str) -> Incident | None:
        """Fetch a single incident by ID."""
        result = await self.session.execute(
            select(Incident).where(Incident.id == uuid.UUID(incident_id))
        )
        return result.scalar_one_or_none()

    async def list_incidents(self) -> list[Incident]:
        """Fetch all incidents ordered by creation date (newest first)."""
        result = await self.session.execute(
            select(Incident).order_by(Incident.created_at.desc())
        )
        return list(result.scalars().all())

    async def triage_incident(self, incident_id: str) -> None:
        """Background task: run the agentic triage workflow for an incident."""
        from ..workflows.triage import triage_graph

        async with async_session() as session:
            result = await session.execute(
                select(Incident).where(Incident.id == uuid.UUID(incident_id))
            )
            incident = result.scalar_one_or_none()
            if not incident:
                logger.error("Triage: incident %s not found", incident_id)
                return

            incident.status = IncidentStatus.TRIAGING
            await session.commit()
            logger.info("Triage: started for incident %s", incident_id)

            try:
                initial_state = {
                    "incident_id": incident_id,
                    "description": incident.description,
                    "reporter_name": incident.name,
                    "reporter_email": incident.email,
                    "image_data": incident.image_data,
                    "image_filename": incident.image_filename,
                    "category": None,
                    "priority": None,
                    "severity_score": None,
                    "keywords": None,
                    "assigned_team": None,
                    "relevant_files": None,
                    "triage_summary": None,
                    "error": None,
                }

                final_state = await triage_graph.ainvoke(initial_state)

                if final_state.get("category"):
                    incident.category = IncidentCategory(final_state["category"])
                if final_state.get("priority"):
                    incident.priority = IncidentPriority(final_state["priority"])
                if final_state.get("severity_score"):
                    incident.severity_score = final_state["severity_score"]
                if final_state.get("assigned_team"):
                    incident.assigned_team = final_state["assigned_team"]
                if final_state.get("triage_summary"):
                    incident.triage_summary = final_state["triage_summary"]

                incident.status = IncidentStatus.TRIAGED

            except Exception:
                logger.exception("Triage failed for incident %s", incident_id)
                incident.triage_summary = (
                    "Triage failed due to an internal error. "
                    "Please review this incident manually."
                )
                incident.status = IncidentStatus.TRIAGED

            await session.commit()
            logger.info("Triage: completed for incident %s", incident_id)


def get_incident_service(
    session: AsyncSession = Depends(get_session),
) -> IncidentService:
    return IncidentService(session)
