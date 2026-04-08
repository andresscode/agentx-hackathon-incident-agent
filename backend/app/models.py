import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, LargeBinary, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class IncidentStatus(enum.StrEnum):
    PENDING = "pending"
    TRIAGING = "triaging"
    TRIAGED = "triaged"
    RESOLVED = "resolved"


class IncidentPriority(enum.StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IncidentCategory(enum.StrEnum):
    BUG = "bug"
    SECURITY = "security"
    OUTAGE = "outage"
    PERFORMANCE = "performance"
    DATA_ISSUE = "data_issue"
    OTHER = "other"


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    image_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    image_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus), nullable=False, default=IncidentStatus.PENDING
    )
    # Fields populated by the triage agent
    priority: Mapped[IncidentPriority | None] = mapped_column(
        Enum(IncidentPriority), nullable=True
    )
    category: Mapped[IncidentCategory | None] = mapped_column(
        Enum(IncidentCategory), nullable=True
    )
    triage_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
