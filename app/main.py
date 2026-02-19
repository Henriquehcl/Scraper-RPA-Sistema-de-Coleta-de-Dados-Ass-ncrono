"""
Ponto de entrada da aplicação FastAPI.

Etapas do startup:
  1. Criar tabelas no PostgreSQL (se não existirem)
  2. Conectar o QueuePublisher ao RabbitMQ
  3. Registrar os roteadores da API

Etapas do shutdown:
  1. Desconectar o QueuePublisher
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import crawl, jobs, results
from app.core.config import settings
from app.core.database import create_tables
from app.services.queue_service import queue_publisher

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Lifespan: startup e shutdown da aplicação
# ──────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    logger.info("Iniciando aplicação: %s", settings.app_name)

    # Etapa 1: criar tabelas no banco
    await create_tables()
    logger.info("Tabelas do banco verificadas/criadas.")

    # Etapa 2: conectar ao RabbitMQ
    await queue_publisher.connect()
    logger.info("Conectado ao RabbitMQ.")

    yield  # aplicação em execução

    # ── Shutdown ──
    logger.info("Encerrando aplicação...")
    await queue_publisher.disconnect()


# ──────────────────────────────────────────────────────────────
# Instância da aplicação FastAPI
# ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description=(
        "API para agendamento e consulta de jobs de scraping web. "
        "Usa RabbitMQ para processamento assíncrono e PostgreSQL para persistência."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ──────────────────────────────────────────────────────────────
# Middleware
# ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────
# Registro dos roteadores
# ──────────────────────────────────────────────────────────────
app.include_router(crawl.router)
app.include_router(jobs.router)
app.include_router(results.router)


# ──────────────────────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Verifica se a API está respondendo."""
    return {"status": "ok", "app": settings.app_name}
