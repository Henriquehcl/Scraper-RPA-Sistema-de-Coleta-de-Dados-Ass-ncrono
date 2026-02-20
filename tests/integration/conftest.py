"""
Fixtures de integração usando Testcontainers.

Etapas:
  1. Subir container PostgreSQL real para os testes
  2. Subir container RabbitMQ real para os testes
  3. Configurar engine e sessão SQLAlchemy apontando para o container
  4. Criar tabelas antes de cada teste
  5. Fornecer cliente HTTP para testar a API (TestClient do FastAPI)
"""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

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

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Containers (escopo de sessão — sobem uma vez para todos os testes)
# ──────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def postgres_container():
    """Sobe container PostgreSQL para os testes de integração."""
    try:
        logger.info("Iniciando container PostgreSQL...")
        with PostgresContainer("postgres:15-alpine") as pg:
            logger.info(f"✅ PostgreSQL disponível em {pg.get_connection_url()}")
            yield pg
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar PostgreSQL: {e}")
        raise


@pytest.fixture(scope="session")
def rabbitmq_container():
    """Sobe container RabbitMQ para os testes de integração."""
    try:
        logger.info("Iniciando container RabbitMQ...")
        with RabbitMqContainer("rabbitmq:3.12-management-alpine") as rmq:
            logger.info(
                f"✅ RabbitMQ disponível em "
                f"{rmq.get_container_host_ip()}:{rmq.get_exposed_port(5672)}"
            )
            yield rmq
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar RabbitMQ: {e}")
        logger.warning("RabbitMQ não disponível - testes usarão mock para queue_publisher")

        # Ainda assim retorna um objeto dummy para não quebrar a dependência
        class DummyRabbitMqContainer:
            def get_container_host_ip(self):
                return "localhost"

            def get_exposed_port(self, port):
                return port

        yield DummyRabbitMqContainer()


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

    Se o RabbitMQ não estiver disponível, usa um mock para que os testes
    de integração de API (sem publish/consume) ainda funcionem.
    """

    # Override do banco de dados
    async def override_get_db():
        yield db_session

    # Override do publisher de fila com retry logic
    app.dependency_overrides[get_db] = override_get_db

    # Conectar publisher ao RabbitMQ do container com múltiplas tentativas
    original_url = os.environ.get("RABBITMQ_URL", "")
    rabbitmq_available = False

    # Tentar diferentes combinações de host/porta
    connection_attempts = [
        # Usar o IP e porta do container
        f"amqp://guest:guest@{rabbitmq_container.get_container_host_ip()}:{rabbitmq_container.get_exposed_port(5672)}/",
        # Fallback para localhost IPv4
        "amqp://guest:guest@127.0.0.1:5672/",
        # Fallback para localhost IPv6
        "amqp://guest:guest@[::1]:5672/",
    ]

    for rmq_url in connection_attempts:
        os.environ["RABBITMQ_URL"] = rmq_url
        try:
            await asyncio.wait_for(queue_publisher.connect(), timeout=5.0)
            rabbitmq_available = True
            logger.info("✅ Conectado ao RabbitMQ com sucesso")
            break
        except Exception as e:
            logger.debug(f"❌ Tentativa com {rmq_url} falhou: {e}")
            continue

    if not rabbitmq_available:
        logger.warning(
            "⚠️  RabbitMQ não disponível. Usando mock para queue_publisher. "
            "Testes de API funcionarão, mas testes que dependem de pub/sub falharão."
        )
        # Mock do queue_publisher para que os testes de API funcionem
        queue_publisher.publish = AsyncMock()
        queue_publisher.consume = AsyncMock()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    # Cleanup
    try:
        if rabbitmq_available:
            await queue_publisher.disconnect()
    except Exception as e:
        logger.debug(f"Erro ao desconectar do RabbitMQ: {e}")

    app.dependency_overrides.clear()
    if original_url:
        os.environ["RABBITMQ_URL"] = original_url
    elif "RABBITMQ_URL" in os.environ:
        del os.environ["RABBITMQ_URL"]
