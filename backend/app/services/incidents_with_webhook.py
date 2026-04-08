import asyncio
import os
import secrets
import string
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from ..exceptions import ServiceError


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


class IncidentService(ABC):
    @abstractmethod
    async def create_incident(self, data: IncidentPayload) -> IncidentResult: ...


class MockSuccessService(IncidentService):
    def __init__(self) -> None:
        self.backend_url = os.environ.get("BACKEND_URL", "http://localhost:8000")

    async def create_incident(self, data: IncidentPayload) -> IncidentResult:
        await asyncio.sleep(1.5)
        chars = string.ascii_uppercase + string.digits
        suffix = "".join(secrets.choice(chars) for _ in range(6))
        incident_id = f"INC-{suffix}"

        # Send notification via webhook
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.backend_url}/api/webhook/incident-created",
                    json={
                        "incident_id": incident_id,
                        "name": data.name,
                        "email": data.email,
                        "description": data.description,
                    },
                    timeout=10.0,
                )
        except Exception:
            # Don't fail the incident creation if notification fails
            pass

        return IncidentResult(success=True, id=incident_id)


class MockFailureService(IncidentService):
    async def create_incident(self, _: IncidentPayload) -> IncidentResult:
        await asyncio.sleep(1.5)
        raise ServiceError("Service unavailable. Please try again later.")


_USE_FAILURE_MOCK = False


def get_incident_service() -> IncidentService:
    return MockFailureService() if _USE_FAILURE_MOCK else MockSuccessService()
