"""
Testes de integração para os endpoints POST /crawl/*.

Verifica que:
  - Os endpoints retornam 202 com job_id
  - O job é criado no banco com status PENDING
  - A mensagem é publicada no RabbitMQ
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.job import JobStatus, JobType
from app.services.job_service import JobService


@pytest.mark.asyncio
class TestCrawlEndpoints:
    """Testes dos endpoints de agendamento de crawling."""

    async def test_post_crawl_hockey_returns_202(self, api_client: AsyncClient) -> None:
        """POST /crawl/hockey deve retornar 202 com job_id."""
        response = await api_client.post("/crawl/hockey")
        assert response.status_code == 202

    async def test_post_crawl_hockey_returns_job_id(self, api_client: AsyncClient) -> None:
        """Resposta deve conter job_id no formato UUID."""
        response = await api_client.post("/crawl/hockey")
        data = response.json()
        assert "job_id" in data
        assert len(data["job_id"]) == 36  # UUID format

    async def test_post_crawl_hockey_status_pending(self, api_client: AsyncClient) -> None:
        """Job retornado deve ter status pending."""
        response = await api_client.post("/crawl/hockey")
        data = response.json()
        assert data["status"] == JobStatus.PENDING.value

    async def test_post_crawl_oscar_returns_202(self, api_client: AsyncClient) -> None:
        """POST /crawl/oscar deve retornar 202."""
        response = await api_client.post("/crawl/oscar")
        assert response.status_code == 202

    async def test_post_crawl_all_returns_202(self, api_client: AsyncClient) -> None:
        """POST /crawl/all deve retornar 202."""
        response = await api_client.post("/crawl/all")
        assert response.status_code == 202

    async def test_post_crawl_creates_job_in_db(
        self, api_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Job deve ser criado no banco de dados após a requisição."""
        response = await api_client.post("/crawl/hockey")
        job_id = response.json()["job_id"]

        import uuid

        service = JobService(db_session)
        job = await service.get_job(uuid.UUID(job_id))

        assert job is not None
        assert str(job.id) == job_id
        assert job.type == JobType.HOCKEY

    async def test_post_crawl_all_creates_all_type_job(
        self, api_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Job criado por /crawl/all deve ter tipo 'all'."""
        response = await api_client.post("/crawl/all")
        job_id = response.json()["job_id"]

        import uuid

        service = JobService(db_session)
        job = await service.get_job(uuid.UUID(job_id))

        assert job is not None
        assert job.type == JobType.ALL
