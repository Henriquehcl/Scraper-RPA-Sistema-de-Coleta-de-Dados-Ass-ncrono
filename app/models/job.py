"""
Model do Job — representa uma tarefa de scraping agendada.

Ciclo de vida do status:
  pending → running → completed
                    ↘ failed
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.schemas.job import JobStatus, JobType


class Job(Base):
    __tablename__ = "jobs"

    # ──────────────────────────────────────────
    # Chave primária: UUID gerado pelo Python
    # ──────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ──────────────────────────────────────────
    # Tipo do job: hockey | oscar | all
    # ──────────────────────────────────────────
    type: Mapped[str] = mapped_column(
        Enum(JobType, name="job_type_enum"),
        nullable=False,
    )

    # ──────────────────────────────────────────
    # Status: pending | running | completed | failed
    # ──────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        Enum(JobStatus, name="job_status_enum"),
        nullable=False,
        default=JobStatus.PENDING,
    )

    # ──────────────────────────────────────────
    # Metadados de execução
    # ──────────────────────────────────────────
    items_collected: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ──────────────────────────────────────────
    # Timestamps
    # ──────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} type={self.type} status={self.status}>"
