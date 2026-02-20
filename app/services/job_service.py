"""
JobService — camada de negócio para gerenciamento de Jobs.

Responsabilidades:
  - Criar novos jobs no banco
  - Atualizar status (running, completed, failed)
  - Consultar jobs e seus resultados
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hockey import HockeyTeam
from app.models.job import Job
from app.models.oscar import OscarFilm
from app.schemas.job import JobStatus, JobType


class JobService:
    """Encapsula todas as operações de banco relacionadas a Jobs."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ──────────────────────────────────────────
    # Criação de job
    # ──────────────────────────────────────────
    async def create_job(self, job_type: JobType) -> Job:
        """Cria um novo job com status PENDING e retorna o objeto persistido."""
        job = Job(type=job_type, status=JobStatus.PENDING)
        self.db.add(job)
        await self.db.flush()  # obtém o id gerado sem commitar ainda
        await self.db.refresh(job)
        return job

    # ──────────────────────────────────────────
    # Consulta de jobs
    # ──────────────────────────────────────────
    async def get_job(self, job_id: uuid.UUID) -> Job | None:
        """Busca um job pelo ID."""
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def list_jobs(self) -> list[Job]:
        """Retorna todos os jobs ordenados do mais recente ao mais antigo."""
        result = await self.db.execute(
            select(Job).order_by(Job.created_at.desc())
        )
        return list(result.scalars().all())

    # ──────────────────────────────────────────
    # Atualização de status
    # ──────────────────────────────────────────
    async def mark_running(self, job_id: uuid.UUID) -> None:
        """Atualiza status para RUNNING quando o worker inicia o crawling."""
        job = await self.get_job(job_id)
        if job:
            job.status = JobStatus.RUNNING
            job.updated_at = datetime.now(datetime.UTC)

    async def mark_completed(self, job_id: uuid.UUID, items_collected: int) -> None:
        """Atualiza status para COMPLETED e registra quantos itens foram coletados."""
        job = await self.get_job(job_id)
        if job:
            job.status = JobStatus.COMPLETED
            job.items_collected = items_collected
            job.updated_at = datetime.now(datetime.UTC)

    async def mark_failed(self, job_id: uuid.UUID, error: str) -> None:
        """Atualiza status para FAILED e salva a mensagem de erro."""
        job = await self.get_job(job_id)
        if job:
            job.status = JobStatus.FAILED
            job.error_message = error
            job.updated_at = datetime.now(datetime.UTC)

    # ──────────────────────────────────────────
    # Consulta de resultados por job
    # ──────────────────────────────────────────
    async def get_hockey_results_by_job(self, job_id: uuid.UUID) -> list[HockeyTeam]:
        """Retorna todos os times de hockey coletados por um job específico."""
        result = await self.db.execute(
            select(HockeyTeam).where(HockeyTeam.job_id == job_id)
        )
        return list(result.scalars().all())

    async def get_oscar_results_by_job(self, job_id: uuid.UUID) -> list[OscarFilm]:
        """Retorna todos os filmes do Oscar coletados por um job específico."""
        result = await self.db.execute(
            select(OscarFilm).where(OscarFilm.job_id == job_id)
        )
        return list(result.scalars().all())

    # ──────────────────────────────────────────
    # Consulta de todos os resultados
    # ──────────────────────────────────────────
    async def get_all_hockey_results(self) -> list[HockeyTeam]:
        """Retorna todos os dados de hockey coletados (todos os jobs)."""
        result = await self.db.execute(
            select(HockeyTeam).order_by(HockeyTeam.year, HockeyTeam.team_name)
        )
        return list(result.scalars().all())

    async def get_all_oscar_results(self) -> list[OscarFilm]:
        """Retorna todos os dados do Oscar coletados (todos os jobs)."""
        result = await self.db.execute(
            select(OscarFilm).order_by(OscarFilm.year, OscarFilm.title)
        )
        return list(result.scalars().all())
