import asyncio
import secrets
import string
from abc import ABC, abstractmethod
from dataclasses import dataclass

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
    async def create_incident(self, _: IncidentPayload) -> IncidentResult:
        await asyncio.sleep(1.5)
        suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        return IncidentResult(success=True, id=f"INC-{suffix}")


class MockFailureService(IncidentService):
    async def create_incident(self, _: IncidentPayload) -> IncidentResult:
        await asyncio.sleep(1.5)
        raise ServiceError("Service unavailable. Please try again later.")


_USE_FAILURE_MOCK = False


def get_incident_service() -> IncidentService:
    return MockFailureService() if _USE_FAILURE_MOCK else MockSuccessService()
