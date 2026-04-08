import logging
import uuid
from dataclasses import dataclass

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session, get_session
from ..models import Incident, IncidentStatus

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

    async def triage_incident(self, incident_id: str) -> None:
        """Background task: run the agentic triage workflow for an incident."""
        # Use a fresh session since background tasks outlive the request session
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

            # TODO: implement agentic triage workflow here
            # - Classify category and priority
            # - Generate triage summary
            # - Notify relevant teams
            logger.info("Triage: started for incident %s", incident_id)

            incident.status = IncidentStatus.TRIAGED
            await session.commit()
            logger.info("Triage: completed for incident %s", incident_id)


def get_incident_service(
    session: AsyncSession = Depends(get_session),
) -> IncidentService:
    return IncidentService(session)
