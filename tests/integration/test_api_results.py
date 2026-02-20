"""
Testes de integração para os endpoints de resultados.

Verifica que:
  - GET /results/hockey retorna lista (mesmo vazia)
  - GET /results/oscar retorna lista (mesmo vazia)
  - GET /jobs/{job_id}/results retorna estrutura correta
  - GET /jobs/{job_id}/results retorna 404 para job inexistente
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hockey import HockeyTeam
from app.models.oscar import OscarFilm
from app.schemas.job import JobType


@pytest.mark.asyncio
class TestResultsEndpoints:
    """Testes dos endpoints de consulta de resultados."""

    async def test_get_all_hockey_returns_200(self, api_client: AsyncClient) -> None:
        """GET /results/hockey deve retornar 200."""
        response = await api_client.get("/results/hockey")
        assert response.status_code == 200

    async def test_get_all_hockey_returns_list(self, api_client: AsyncClient) -> None:
        """Resposta de GET /results/hockey deve ser uma lista."""
        response = await api_client.get("/results/hockey")
        assert isinstance(response.json(), list)

    async def test_get_all_oscar_returns_200(self, api_client: AsyncClient) -> None:
        """GET /results/oscar deve retornar 200."""
        response = await api_client.get("/results/oscar")
        assert response.status_code == 200

    async def test_get_all_oscar_returns_list(self, api_client: AsyncClient) -> None:
        """Resposta de GET /results/oscar deve ser uma lista."""
        response = await api_client.get("/results/oscar")
        assert isinstance(response.json(), list)

    async def test_get_job_results_returns_404_for_unknown(self, api_client: AsyncClient) -> None:
        """GET /jobs/{job_id}/results deve retornar 404 para job inexistente."""
        fake_id = uuid.uuid4()
        response = await api_client.get(f"/jobs/{fake_id}/results")
        assert response.status_code == 404

    async def test_get_job_results_hockey_structure(
        self, api_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET /jobs/{job_id}/results para job de hockey deve ter campos esperados."""
        # Criar job de hockey
        post_response = await api_client.post("/crawl/hockey")
        job_id = post_response.json()["job_id"]

        # Inserir dado de hockey manualmente no banco
        hockey_record = HockeyTeam(
            job_id=uuid.UUID(job_id),
            team_name="Test Team",
            year=2020,
            wins=30,
            losses=20,
            ot_losses=5,
            win_pct=0.6,
            goals_for=200,
            goals_against=180,
            goal_diff=20,
        )
        db_session.add(hockey_record)
        await db_session.flush()

        response = await api_client.get(f"/jobs/{job_id}/results")
        data = response.json()

        assert response.status_code == 200
        assert data["type"] == JobType.HOCKEY.value
        assert "data" in data
        assert data["count"] >= 1

    async def test_get_job_results_oscar_structure(
        self, api_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET /jobs/{job_id}/results para job de oscar deve ter campos esperados."""
        post_response = await api_client.post("/crawl/oscar")
        job_id = post_response.json()["job_id"]

        oscar_record = OscarFilm(
            job_id=uuid.UUID(job_id),
            year=2010,
            title="Test Film",
            nominations=9,
            awards=6,
            best_picture=True,
        )
        db_session.add(oscar_record)
        await db_session.flush()

        response = await api_client.get(f"/jobs/{job_id}/results")
        data = response.json()

        assert response.status_code == 200
        assert data["type"] == JobType.OSCAR.value
        assert data["count"] >= 1

    async def test_hockey_results_appear_in_global_list(
        self, api_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Dados de hockey inseridos devem aparecer em GET /results/hockey."""
        post_response = await api_client.post("/crawl/hockey")
        job_id = post_response.json()["job_id"]

        record = HockeyTeam(
            job_id=uuid.UUID(job_id),
            team_name="Global Team",
            year=2022,
            wins=40,
            losses=15,
            ot_losses=None,
            win_pct=0.727,
            goals_for=220,
            goals_against=170,
            goal_diff=50,
        )
        db_session.add(record)
        await db_session.flush()

        response = await api_client.get("/results/hockey")
        teams = response.json()
        names = [t["team_name"] for t in teams]

        assert "Global Team" in names
