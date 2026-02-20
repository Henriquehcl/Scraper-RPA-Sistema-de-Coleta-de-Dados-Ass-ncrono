"""
Testes unitários do JobService.

Usa mock de AsyncSession para testar a lógica de negócio
sem precisar de banco de dados real.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.job import Job
from app.schemas.job import JobStatus, JobType
from app.services.job_service import JobService


def make_mock_db() -> MagicMock:
    """Cria um mock de AsyncSession com os métodos necessários."""
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    return db


def make_mock_job(
    job_id: uuid.UUID = None,
    job_type: JobType = JobType.HOCKEY,
    status: JobStatus = JobStatus.PENDING,
) -> Job:
    """Cria um objeto Job com atributos preenchidos para testes."""
    job = MagicMock(spec=Job)
    job.id = job_id or uuid.uuid4()
    job.type = job_type
    job.status = status
    job.items_collected = 0
    job.error_message = None
    job.created_at = datetime.now(UTC)
    job.updated_at = datetime.now(UTC)
    return job


class TestJobServiceCreate:
    """Testes de criação de job."""

    @pytest.mark.asyncio
    async def test_create_job_adds_to_db(self) -> None:
        """create_job() deve chamar db.add() e retornar o job."""
        db = make_mock_db()
        job = make_mock_job()
        db.refresh.side_effect = lambda j: None  # simula refresh sem banco

        # Simular o job criado
        with patch("app.services.job_service.Job", return_value=job):
            service = JobService(db)
            result = await service.create_job(JobType.HOCKEY)

        db.add.assert_called_once_with(job)
        db.flush.assert_called_once()
        assert result is job

    @pytest.mark.asyncio
    async def test_create_job_sets_pending_status(self) -> None:
        """Job criado deve ter status PENDING."""
        db = make_mock_db()
        job = make_mock_job(status=JobStatus.PENDING)

        with patch("app.services.job_service.Job", return_value=job):
            service = JobService(db)
            result = await service.create_job(JobType.OSCAR)

        assert result.status == JobStatus.PENDING


class TestJobServiceGet:
    """Testes de consulta de jobs."""

    @pytest.mark.asyncio
    async def test_get_job_returns_none_when_not_found(self) -> None:
        """get_job() deve retornar None se o job não existir."""
        db = make_mock_db()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        service = JobService(db)
        result = await service.get_job(uuid.uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_job_returns_job_when_found(self) -> None:
        """get_job() deve retornar o job se existir."""
        job = make_mock_job()
        db = make_mock_db()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = job
        db.execute.return_value = result_mock

        service = JobService(db)
        result = await service.get_job(job.id)

        assert result is job

    @pytest.mark.asyncio
    async def test_list_jobs_returns_all(self) -> None:
        """list_jobs() deve retornar todos os jobs."""
        jobs = [make_mock_job(), make_mock_job()]
        db = make_mock_db()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = jobs
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        service = JobService(db)
        result = await service.list_jobs()

        assert len(result) == 2


class TestJobServiceStatusUpdate:
    """Testes de atualização de status."""

    @pytest.mark.asyncio
    async def test_mark_running_updates_status(self) -> None:
        """mark_running() deve atualizar o status do job para RUNNING."""
        job = make_mock_job(status=JobStatus.PENDING)
        db = make_mock_db()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = job
        db.execute.return_value = result_mock

        service = JobService(db)
        await service.mark_running(job.id)

        assert job.status == JobStatus.RUNNING

    @pytest.mark.asyncio
    async def test_mark_completed_updates_status_and_count(self) -> None:
        """mark_completed() deve definir status e items_collected."""
        job = make_mock_job(status=JobStatus.RUNNING)
        db = make_mock_db()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = job
        db.execute.return_value = result_mock

        service = JobService(db)
        await service.mark_completed(job.id, items_collected=150)

        assert job.status == JobStatus.COMPLETED
        assert job.items_collected == 150

    @pytest.mark.asyncio
    async def test_mark_failed_saves_error_message(self) -> None:
        """mark_failed() deve definir status FAILED e salvar a mensagem de erro."""
        job = make_mock_job(status=JobStatus.RUNNING)
        db = make_mock_db()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = job
        db.execute.return_value = result_mock

        service = JobService(db)
        await service.mark_failed(job.id, error="Connection timeout")

        assert job.status == JobStatus.FAILED
        assert job.error_message == "Connection timeout"

    @pytest.mark.asyncio
    async def test_mark_running_noop_when_job_not_found(self) -> None:
        """Atualizar status de job inexistente não deve lançar exceção."""
        db = make_mock_db()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        service = JobService(db)
        # Não deve lançar exceção
        await service.mark_running(uuid.uuid4())
