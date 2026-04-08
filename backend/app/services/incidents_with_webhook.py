import asyncio
import contextlib
import secrets
import string
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..exceptions import ServiceError
from .notifications import IncidentNotification, notify_incident_created


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
    async def create_incident(self, data: IncidentPayload) -> IncidentResult:
        await asyncio.sleep(1.5)
        chars = string.ascii_uppercase + string.digits
        suffix = "".join(secrets.choice(chars) for _ in range(6))
        incident_id = f"INC-{suffix}"

        with contextlib.suppress(Exception):
            await notify_incident_created(
                IncidentNotification(
                    incident_id=incident_id,
                    name=data.name,
                    email=data.email,
                    description=data.description,
                )
            )

        return IncidentResult(success=True, id=incident_id)


class MockFailureService(IncidentService):
    async def create_incident(self, _: IncidentPayload) -> IncidentResult:
        await asyncio.sleep(1.5)
        raise ServiceError("Service unavailable. Please try again later.")


_USE_FAILURE_MOCK = False


def get_incident_service() -> IncidentService:
    return MockFailureService() if _USE_FAILURE_MOCK else MockSuccessService()
