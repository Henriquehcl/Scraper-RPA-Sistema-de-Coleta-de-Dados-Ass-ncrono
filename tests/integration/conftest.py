"""
Fixtures de integração usando Testcontainers.

Etapas:
  1. Subir container PostgreSQL real para os testes
  2. Subir container RabbitMQ real para os testes
  3. Configurar engine e sessão SQLAlchemy apontando para o container
  4. Criar tabelas antes de cada teste
  5. Fornecer cliente HTTP para testar a API (TestClient do FastAPI)
"""

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer
from testcontainers.rabbitmq import RabbitMqContainer

from app.core.database import Base, get_db
from app.main import app
from app.services.queue_service import queue_publisher


# ──────────────────────────────────────────────────────────────
# Containers (escopo de sessão — sobem uma vez para todos os testes)
# ──────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def postgres_container():
    """Sobe container PostgreSQL para os testes de integração."""
    with PostgresContainer("postgres:15-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def rabbitmq_container():
    """Sobe container RabbitMQ para os testes de integração."""
    with RabbitMqContainer("rabbitmq:3.12-management-alpine") as rmq:
        yield rmq


# ──────────────────────────────────────────────────────────────
# Engine e sessão apontando para o container de teste
# ──────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def test_engine(postgres_container):
    """Cria engine assíncrono para o banco de testes."""
    url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2", "postgresql+asyncpg"
    )
    engine = create_async_engine(url, echo=False)
    return engine


@pytest_asyncio.fixture(scope="session")
async def setup_db(test_engine):
    """Cria todas as tabelas no banco de testes."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(test_engine, setup_db) -> AsyncGenerator[AsyncSession, None]:
    """Sessão de banco isolada por teste (rollback ao final)."""
    AsyncTestSession = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with AsyncTestSession() as session:
        yield session
        await session.rollback()


# ──────────────────────────────────────────────────────────────
# Cliente HTTP para testar a API FastAPI
# ──────────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def api_client(
    db_session: AsyncSession,
    rabbitmq_container,
) -> AsyncGenerator[AsyncClient, None]:
    """
    Cliente HTTP assíncrono que chama a API FastAPI em memória.
    Substitui as dependências de DB e fila pelos containers de teste.
    """

    # Override do banco de dados
    async def override_get_db():
        yield db_session

    # Override do publisher de fila
    rmq_url = (
        f"amqp://guest:guest@{rabbitmq_container.get_container_host_ip()}"
        f":{rabbitmq_container.get_exposed_port(5672)}/"
    )

    app.dependency_overrides[get_db] = override_get_db

    # Conectar publisher ao RabbitMQ do container
    original_url = os.environ.get("RABBITMQ_URL", "")
    os.environ["RABBITMQ_URL"] = rmq_url

    await queue_publisher.connect()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    # Cleanup
    await queue_publisher.disconnect()
    app.dependency_overrides.clear()
    if original_url:
        os.environ["RABBITMQ_URL"] = original_url
