"""
Rotas de agendamento de coletas — POST /crawl/*

Fluxo assíncrono:
  1. Cria job no banco com status PENDING
  2. Publica mensagem no RabbitMQ com job_id e tipo
  3. Retorna job_id imediatamente (não aguarda o crawling)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.job import CrawlMessage, JobCreatedResponse, JobStatus, JobType
from app.services.job_service import JobService
from app.services.queue_service import queue_publisher

router = APIRouter(prefix="/crawl", tags=["Crawl"])


async def _schedule_job(
    job_type: JobType,
    db: AsyncSession,
) -> JobCreatedResponse:
    """
    Helper compartilhado: cria job, publica na fila e retorna resposta.
    Utilizado pelos três endpoints de agendamento.
    """
    # Etapa 1: persistir o job como PENDING
    service = JobService(db)
    job = await service.create_job(job_type)

    # Etapa 2: publicar na fila para o worker processar
    message = CrawlMessage(job_id=job.id, job_type=job_type)
    await queue_publisher.publish(message)

    return JobCreatedResponse(
        job_id=job.id,
        status=JobStatus.PENDING,
        message=f"Job de coleta '{job_type.value}' agendado com sucesso.",
    )


@router.post(
    "/hockey",
    response_model=JobCreatedResponse,
    summary="Agendar coleta de dados de Hockey",
    status_code=202,
)
async def schedule_hockey_crawl(
    db: AsyncSession = Depends(get_db),
) -> JobCreatedResponse:
    """
    Agenda a coleta de dados do site de times de hockey.
    Retorna o job_id para acompanhamento via GET /jobs/{job_id}.
    """
    return await _schedule_job(JobType.HOCKEY, db)


@router.post(
    "/oscar",
    response_model=JobCreatedResponse,
    summary="Agendar coleta de dados do Oscar",
    status_code=202,
)
async def schedule_oscar_crawl(
    db: AsyncSession = Depends(get_db),
) -> JobCreatedResponse:
    """
    Agenda a coleta de filmes vencedores do Oscar.
    Retorna o job_id para acompanhamento via GET /jobs/{job_id}.
    """
    return await _schedule_job(JobType.OSCAR, db)


@router.post(
    "/all",
    response_model=JobCreatedResponse,
    summary="Agendar coleta de todas as fontes",
    status_code=202,
)
async def schedule_all_crawl(
    db: AsyncSession = Depends(get_db),
) -> JobCreatedResponse:
    """
    Agenda a coleta de todas as fontes (hockey + oscar) em um único job.
    Retorna o job_id para acompanhamento via GET /jobs/{job_id}.
    """
    return await _schedule_job(JobType.ALL, db)
