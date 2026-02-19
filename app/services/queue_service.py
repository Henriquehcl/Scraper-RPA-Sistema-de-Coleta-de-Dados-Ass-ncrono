"""
QueueService — integração com RabbitMQ usando aio-pika.

Etapas da comunicação:
  1. Publisher (API): publica mensagem JSON na fila ao receber POST /crawl/*
  2. Consumer (Worker): consome mensagem, executa crawler e atualiza job
"""

import json
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import aio_pika
from aio_pika import Message, DeliveryMode
from aio_pika.abc import AbstractChannel, AbstractConnection

from app.core.config import settings
from app.schemas.job import CrawlMessage

logger = logging.getLogger(__name__)


class QueuePublisher:
    """
    Publica mensagens no RabbitMQ.
    Instanciado no startup da API e reutilizado entre requisições.
    """

    def __init__(self) -> None:
        self._connection: AbstractConnection | None = None
        self._channel: AbstractChannel | None = None

    # ──────────────────────────────────────────
    # Ciclo de vida da conexão
    # ──────────────────────────────────────────
    async def connect(self) -> None:
        """Abre conexão e canal com o RabbitMQ."""
        self._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        self._channel = await self._connection.channel()

        # Declara a fila como durável para sobreviver a reinicializações
        await self._channel.declare_queue(
            settings.queue_name,
            durable=True,
        )
        logger.info("QueuePublisher conectado ao RabbitMQ.")

    async def disconnect(self) -> None:
        """Fecha conexão e canal."""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        logger.info("QueuePublisher desconectado do RabbitMQ.")

    # ──────────────────────────────────────────
    # Publicação de mensagem
    # ──────────────────────────────────────────
    async def publish(self, message: CrawlMessage) -> None:
        """
        Serializa CrawlMessage como JSON e publica na fila.
        Usa DeliveryMode.PERSISTENT para garantir que a mensagem
        não seja perdida em caso de reinicialização do broker.
        """
        if self._channel is None:
            raise RuntimeError("QueuePublisher não está conectado.")

        body = message.model_dump_json().encode()

        await self._channel.default_exchange.publish(
            Message(
                body=body,
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json",
            ),
            routing_key=settings.queue_name,
        )
        logger.info(
            "Mensagem publicada: job_id=%s type=%s",
            message.job_id,
            message.job_type,
        )


# ──────────────────────────────────────────────────────────────
# Singleton do publisher — compartilhado pelo estado da aplicação
# ──────────────────────────────────────────────────────────────
queue_publisher = QueuePublisher()


# ──────────────────────────────────────────────────────────────
# Context manager para o consumer (usado pelo Worker)
# ──────────────────────────────────────────────────────────────
@asynccontextmanager
async def get_consumer_channel() -> AsyncGenerator[AbstractChannel, None]:
    """
    Abre uma conexão dedicada para consumo de mensagens.
    Usado pelo processo Worker, não pela API.
    """
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)  # processa 1 mensagem por vez
        yield channel
    finally:
        if not connection.is_closed:
            await connection.close()
