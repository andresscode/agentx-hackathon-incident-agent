import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, EmailStr, Field

from ..exceptions import ServiceError
from ..llm_provider import get_llm
from ..prompts import PROMPT_INJECTION_SYSTEM_PROMPT
from ..services.incidents import (
    IncidentPayload,
    IncidentService,
    get_incident_service,
)

logger = logging.getLogger("uvicorn.error")

router = APIRouter()


class PromptInjectionVerdict(BaseModel):
    is_safe: bool = Field(
        description="True if the text is a legitimate incident report, "
        "False if it is a prompt injection or jailbreak attempt"
    )
    reason: str = Field(description="Brief explanation of the verdict")


class CreateIncidentResponse(BaseModel):
    success: bool
    id: str


@router.post("/api/incidents", response_model=CreateIncidentResponse, status_code=201)
async def create_incident(
    background_tasks: BackgroundTasks,
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

    # --- Prompt injection check (structured output) ---
    llm = get_llm()
    structured_llm = llm.with_structured_output(PromptInjectionVerdict)
    raw_verdict = await structured_llm.ainvoke(
        [
            SystemMessage(content=PROMPT_INJECTION_SYSTEM_PROMPT),
            HumanMessage(content=description),
        ]
    )
    if not isinstance(raw_verdict, PromptInjectionVerdict):
        logger.error(
            "Prompt injection check returned unexpected type: %s",
            type(raw_verdict),
        )
        raise ServiceError(
            "Unable to process your request. Please try again later.",
            status_code=500,
        )
    logger.info(
        "Prompt injection verdict: is_safe=%s, reason=%s",
        raw_verdict.is_safe,
        raw_verdict.reason,
    )
    if not raw_verdict.is_safe:
        raise ServiceError(
            "Unable to process your request. Please try again later.", status_code=400
        )

    # --- Save incident to DB ---
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

    # --- Kick off triage in the background ---
    background_tasks.add_task(service.triage_incident, result.id)

    return CreateIncidentResponse(success=result.success, id=result.id)
