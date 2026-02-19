"""
Rotas de gerenciamento de Jobs — GET /jobs e GET /jobs/{job_id}
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.job import JobResponse
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get(
    "",
    response_model=list[JobResponse],
    summary="Listar todos os jobs",
)
async def list_jobs(
    db: AsyncSession = Depends(get_db),
) -> list[JobResponse]:
    """Retorna todos os jobs ordenados do mais recente ao mais antigo."""
    service = JobService(db)
    jobs = await service.list_jobs()
    return jobs  # type: ignore[return-value]


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Consultar status de um job específico",
)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """
    Retorna os detalhes e status atual de um job.
    Status possíveis: pending | running | completed | failed
    """
    service = JobService(db)
    job = await service.get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} não encontrado.",
        )

    return job  # type: ignore[return-value]
