"""
BaseCrawler — classe abstrata que define o contrato para todos os crawlers.

Cada crawler concreto deve implementar o método `crawl()` que retorna
uma lista de dicionários com os dados coletados.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """
    Classe base para todos os crawlers da aplicação.

    Etapas esperadas em cada crawler concreto:
      1. Inicializar recursos (browser, sessão HTTP, etc.)
      2. Navegar pelas páginas/endpoints do site alvo
      3. Extrair e normalizar os dados
      4. Fechar/liberar recursos
      5. Retornar lista de dicts com os dados coletados
    """

    def __init__(self, source_name: str) -> None:
        self.source_name = source_name
        self.logger = logging.getLogger(f"{__name__}.{source_name}")

    @abstractmethod
    async def crawl(self) -> list[dict[str, Any]]:
        """
        Executa o processo completo de scraping.

        Returns:
            Lista de dicionários com os dados coletados.
            Cada dict corresponde a um registro a ser persistido.
        """
        ...

    def _log_start(self) -> None:
        self.logger.info("Iniciando crawling: %s", self.source_name)

    def _log_done(self, count: int) -> None:
        self.logger.info(
            "Crawling concluído: %s — %d registros coletados",
            self.source_name,
            count,
        )

    def _log_error(self, error: Exception) -> None:
        self.logger.error(
            "Erro no crawling de %s: %s",
            self.source_name,
            str(error),
            exc_info=True,
        )
