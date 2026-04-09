import enum

from pydantic import BaseModel, Field

from ..models import IncidentCategory, IncidentPriority


class AssignedTeam(enum.StrEnum):
    SECURITY = "Security Team"
    PLATFORM = "Platform Team"
    PAYMENTS = "Payments Team"
    FRONTEND = "Frontend Team"
    INFRASTRUCTURE = "Infrastructure Team"
    DATA = "Data Team"
    GENERAL = "General Engineering"


class IncidentClassification(BaseModel):
    category: IncidentCategory
    priority: IncidentPriority
    severity_score: int = Field(ge=1, le=10, description="Severity from 1-10")
    keywords: list[str] = Field(
        min_length=3, max_length=5, description="Technical keywords for codebase search"
    )
    assigned_team: AssignedTeam
    reasoning: str = Field(description="Brief explanation of the classification")


class FileSelection(BaseModel):
    file_paths: list[str] = Field(
        min_length=1, max_length=5, description="Relevant file paths from the manifest"
    )
    reasoning: str = Field(description="Why these files are relevant")
