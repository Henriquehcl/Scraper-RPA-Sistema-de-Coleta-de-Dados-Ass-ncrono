"""
Schemas Pydantic para Jobs — validação, serialização e contratos da API.
"""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


# ──────────────────────────────────────────────────────────────
# Enums compartilhados entre schemas e models
# ──────────────────────────────────────────────────────────────
class JobType(str, Enum):
    HOCKEY = "hockey"
    OSCAR = "oscar"
    ALL = "all"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ──────────────────────────────────────────────────────────────
# Schemas de resposta da API
# ──────────────────────────────────────────────────────────────
class JobResponse(BaseModel):
    """Resposta padrão ao criar ou consultar um job."""

    id: uuid.UUID
    type: JobType
    status: JobStatus
    items_collected: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobCreatedResponse(BaseModel):
    """Resposta imediata ao agendar um novo job (POST /crawl/*)."""

    job_id: uuid.UUID
    status: JobStatus
    message: str


# ──────────────────────────────────────────────────────────────
# Mensagem publicada no RabbitMQ
# ──────────────────────────────────────────────────────────────
class CrawlMessage(BaseModel):
    """Payload da mensagem publicada na fila de crawling."""

    job_id: uuid.UUID
    job_type: JobType
