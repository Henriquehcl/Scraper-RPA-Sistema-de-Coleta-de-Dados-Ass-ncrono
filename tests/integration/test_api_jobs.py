"""
Testes de integração para os endpoints GET /jobs/*.

Verifica que:
  - GET /jobs lista todos os jobs
  - GET /jobs/{job_id} retorna job existente
  - GET /jobs/{job_id} retorna 404 para job inexistente
"""

import uuid

import pytest
from httpx import AsyncClient

from app.schemas.job import JobStatus, JobType


@pytest.mark.asyncio
class TestJobsEndpoints:
    """Testes dos endpoints de consulta de jobs."""

    async def test_list_jobs_returns_200(
        self, api_client: AsyncClient
    ) -> None:
        """GET /jobs deve retornar 200."""
        response = await api_client.get("/jobs")
        assert response.status_code == 200

    async def test_list_jobs_returns_list(
        self, api_client: AsyncClient
    ) -> None:
        """Resposta de GET /jobs deve ser uma lista."""
        response = await api_client.get("/jobs")
        assert isinstance(response.json(), list)

    async def test_list_jobs_includes_created_jobs(
        self, api_client: AsyncClient
    ) -> None:
        """Jobs criados devem aparecer na listagem."""
        # Criar um job
        post_response = await api_client.post("/crawl/hockey")
        job_id = post_response.json()["job_id"]

        # Listar jobs
        list_response = await api_client.get("/jobs")
        job_ids = [j["id"] for j in list_response.json()]

        assert job_id in job_ids

    async def test_get_job_by_id_returns_200(
        self, api_client: AsyncClient
    ) -> None:
        """GET /jobs/{job_id} deve retornar 200 para job existente."""
        post_response = await api_client.post("/crawl/oscar")
        job_id = post_response.json()["job_id"]

        response = await api_client.get(f"/jobs/{job_id}")
        assert response.status_code == 200

    async def test_get_job_by_id_correct_data(
        self, api_client: AsyncClient
    ) -> None:
        """Job retornado deve ter os campos corretos."""
        post_response = await api_client.post("/crawl/hockey")
        job_id = post_response.json()["job_id"]

        response = await api_client.get(f"/jobs/{job_id}")
        data = response.json()

        assert data["id"] == job_id
        assert data["type"] == JobType.HOCKEY.value
        assert data["status"] == JobStatus.PENDING.value
        assert "created_at" in data
        assert "updated_at" in data

    async def test_get_job_returns_404_for_unknown(
        self, api_client: AsyncClient
    ) -> None:
        """GET /jobs/{job_id} deve retornar 404 para UUID inexistente."""
        fake_id = uuid.uuid4()
        response = await api_client.get(f"/jobs/{fake_id}")
        assert response.status_code == 404

    async def test_get_job_returns_404_detail(
        self, api_client: AsyncClient
    ) -> None:
        """Resposta 404 deve conter campo 'detail'."""
        fake_id = uuid.uuid4()
        response = await api_client.get(f"/jobs/{fake_id}")
        assert "detail" in response.json()
