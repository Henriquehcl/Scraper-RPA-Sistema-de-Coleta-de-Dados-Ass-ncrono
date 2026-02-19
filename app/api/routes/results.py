"""
Rotas de consulta de resultados coletados.

  GET /jobs/{job_id}/results → resultados de um job específico
  GET /results/hockey        → todos os dados de hockey
  GET /results/oscar         → todos os dados do oscar
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.hockey import HockeyTeamResponse
from app.schemas.oscar import OscarFilmResponse
from app.schemas.job import JobType
from app.services.job_service import JobService

router = APIRouter(tags=["Results"])


# ──────────────────────────────────────────────────────────────
# Resultados por job específico
# ──────────────────────────────────────────────────────────────
@router.get(
    "/jobs/{job_id}/results",
    summary="Resultados de um job específico",
)
async def get_job_results(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Retorna os dados coletados por um job específico.
    O formato da resposta varia de acordo com o tipo do job.
    """
    service = JobService(db)

    # Verifica se o job existe
    job = await service.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} não encontrado.",
        )

    # Retorna os dados conforme o tipo do job
    if job.type == JobType.HOCKEY:
        records = await service.get_hockey_results_by_job(job_id)
        return {
            "job_id": str(job_id),
            "type": job.type,
            "status": job.status,
            "count": len(records),
            "data": [HockeyTeamResponse.model_validate(r) for r in records],
        }

    if job.type == JobType.OSCAR:
        records = await service.get_oscar_results_by_job(job_id)
        return {
            "job_id": str(job_id),
            "type": job.type,
            "status": job.status,
            "count": len(records),
            "data": [OscarFilmResponse.model_validate(r) for r in records],
        }

    # Tipo ALL — retorna ambos
    hockey = await service.get_hockey_results_by_job(job_id)
    oscar = await service.get_oscar_results_by_job(job_id)
    return {
        "job_id": str(job_id),
        "type": job.type,
        "status": job.status,
        "hockey": {
            "count": len(hockey),
            "data": [HockeyTeamResponse.model_validate(r) for r in hockey],
        },
        "oscar": {
            "count": len(oscar),
            "data": [OscarFilmResponse.model_validate(r) for r in oscar],
        },
    }


# ──────────────────────────────────────────────────────────────
# Todos os resultados de hockey (todos os jobs)
# ──────────────────────────────────────────────────────────────
@router.get(
    "/results/hockey",
    response_model=list[HockeyTeamResponse],
    summary="Todos os dados de Hockey coletados",
)
async def get_all_hockey(
    db: AsyncSession = Depends(get_db),
) -> list[HockeyTeamResponse]:
    """Retorna todos os registros de times de hockey de todos os jobs."""
    service = JobService(db)
    records = await service.get_all_hockey_results()
    return records  # type: ignore[return-value]


# ──────────────────────────────────────────────────────────────
# Todos os resultados do Oscar (todos os jobs)
# ──────────────────────────────────────────────────────────────
@router.get(
    "/results/oscar",
    response_model=list[OscarFilmResponse],
    summary="Todos os dados do Oscar coletados",
)
async def get_all_oscar(
    db: AsyncSession = Depends(get_db),
) -> list[OscarFilmResponse]:
    """Retorna todos os registros de filmes do Oscar de todos os jobs."""
    service = JobService(db)
    records = await service.get_all_oscar_results()
    return records  # type: ignore[return-value]
