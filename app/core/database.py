"""
Configuração do banco de dados PostgreSQL com SQLAlchemy assíncrono.

Etapas:
  1. Cria o engine assíncrono usando asyncpg
  2. Cria a sessão assíncrona (AsyncSession)
  3. Expõe `get_db` como dependency injection para as rotas FastAPI
  4. Expõe `create_tables` para inicializar o schema no startup
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ──────────────────────────────────────────────────────────────
# Engine assíncrono — pool de conexões gerenciado pelo SQLAlchemy
# ──────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,  # verifica conexões inativas antes de usar
    pool_size=10,
    max_overflow=20,
)

# Fábrica de sessões assíncronas
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ──────────────────────────────────────────────────────────────
# Base declarativa — todas as models herdam desta classe
# ──────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ──────────────────────────────────────────────────────────────
# Dependency Injection para FastAPI
# ──────────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Fornece uma sessão de banco para cada requisição e garante fechamento."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ──────────────────────────────────────────────────────────────
# Criação de tabelas (usado no startup da aplicação)
# ──────────────────────────────────────────────────────────────
async def create_tables() -> None:
    """Cria todas as tabelas definidas nas models se não existirem."""
    # Importa models para registrá-las na metadata do Base
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
