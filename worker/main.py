"""
Worker — processo independente que consome mensagens do RabbitMQ e executa crawlers.

Etapas de cada ciclo de processamento:
  1. Receber mensagem da fila com job_id e job_type
  2. Atualizar status do job para RUNNING no banco
  3. Instanciar o crawler correto (hockey ou oscar)
  4. Executar o crawling
  5. Persistir os registros coletados no banco
  6. Atualizar status para COMPLETED ou FAILED
  7. Dar acknowledge (ACK) da mensagem na fila
"""

import asyncio
import json
import logging
import uuid

import aio_pika
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionFactory, create_tables
from app.crawlers.hockey_crawler import HockeyCrawler
from app.crawlers.oscar_crawler import OscarCrawler
from app.models.hockey import HockeyTeam
from app.models.oscar import OscarFilm
from app.schemas.job import CrawlMessage, JobType
from app.services.job_service import JobService
from app.services.queue_service import get_consumer_channel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Lógica de processamento de cada mensagem
# ──────────────────────────────────────────────────────────────
async def process_message(
    message: aio_pika.IncomingMessage,
) -> None:
    """
    Callback executado para cada mensagem recebida da fila.
    Gerencia o ciclo de vida completo: banco + crawling + persistência.
    """
    async with message.process():  # ACK automático ao sair sem exceção
        # Etapa 1: deserializar a mensagem
        payload = CrawlMessage.model_validate_json(message.body)
        job_id = payload.job_id
        job_type = payload.job_type

        logger.info("Processando job: id=%s type=%s", job_id, job_type)

        async with AsyncSessionFactory() as db:
            service = JobService(db)

            try:
                # Etapa 2: marcar job como RUNNING
                await service.mark_running(job_id)
                await db.commit()

                # Etapa 3 e 4: executar crawler(s) conforme tipo do job
                total_items = 0

                if job_type in (JobType.HOCKEY, JobType.ALL):
                    total_items += await _run_hockey_crawler(db, job_id)

                if job_type in (JobType.OSCAR, JobType.ALL):
                    total_items += await _run_oscar_crawler(db, job_id)

                # Etapa 6a: marcar como COMPLETED
                await service.mark_completed(job_id, items_collected=total_items)
                await db.commit()

                logger.info(
                    "Job concluído: id=%s — %d itens coletados",
                    job_id,
                    total_items,
                )

            except Exception as exc:
                # Etapa 6b: marcar como FAILED em caso de erro
                logger.error("Job falhou: id=%s — %s", job_id, exc, exc_info=True)
                await service.mark_failed(job_id, error=str(exc))
                await db.commit()


async def _run_hockey_crawler(db: AsyncSession, job_id: uuid.UUID) -> int:
    """Executa o crawler de hockey e persiste os registros no banco."""
    crawler = HockeyCrawler()
    records = await crawler.crawl()

    # Etapa 5: persistir cada registro associado ao job_id
    for record in records:
        team = HockeyTeam(job_id=job_id, **record)
        db.add(team)

    await db.flush()
    return len(records)


async def _run_oscar_crawler(db: AsyncSession, job_id: uuid.UUID) -> int:
    """Executa o crawler do Oscar e persiste os registros no banco."""
    crawler = OscarCrawler()
    records = await crawler.crawl()

    # Etapa 5: persistir cada registro associado ao job_id
    for record in records:
        film = OscarFilm(job_id=job_id, **record)
        db.add(film)

    await db.flush()
    return len(records)


# ──────────────────────────────────────────────────────────────
# Loop principal do worker
# ──────────────────────────────────────────────────────────────
async def main() -> None:
    """
    Inicializa o banco de dados, conecta ao RabbitMQ e
    entra em loop aguardando mensagens para processar.
    """
    logger.info("Iniciando Worker...")

    # Garantir que as tabelas existem
    await create_tables()

    async with get_consumer_channel() as channel:
        # Declarar a fila (idempotente — cria somente se não existir)
        queue = await channel.declare_queue(settings.queue_name, durable=True)

        logger.info(
            "Worker aguardando mensagens na fila '%s'...", settings.queue_name
        )

        # Consumir mensagens indefinidamente
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                await process_message(message)


if __name__ == "__main__":
    asyncio.run(main())
