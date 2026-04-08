import logging

from fastapi import APIRouter, Depends, Form, UploadFile, File
from pydantic import BaseModel, EmailStr

logger = logging.getLogger("uvicorn.error")

from ..services.incidents import (
    IncidentPayload,
    IncidentService,
    get_incident_service,
)

router = APIRouter()


class CreateIncidentResponse(BaseModel):
    success: bool
    id: str


@router.post("/api/incidents", response_model=CreateIncidentResponse, status_code=201)
async def create_incident(
    name: str = Form(),
    email: EmailStr = Form(),
    description: str = Form(),
    image: UploadFile | None = File(None),
    service: IncidentService = Depends(get_incident_service),
) -> CreateIncidentResponse:
    logger.info(
        "Received incident: name=%s, email=%s, description=%s, image=%s",
        name,
        email,
        description[:50] if description else None,
        image.filename if image and image.size else None,
    )

    image_bytes = None
    image_filename = None
    if image and image.size:
        image_bytes = await image.read()
        image_filename = image.filename

    payload = IncidentPayload(
        name=name,
        email=email,
        description=description,
        image=image_bytes,
        image_filename=image_filename,
    )

    result = await service.create_incident(payload)

    return CreateIncidentResponse(success=result.success, id=result.id)
