"""
HockeyCrawler — coleta dados da tabela de times de hockey com paginação HTML.

Fonte: https://www.scrapethissite.com/pages/forms/
Estratégia: requests + BeautifulSoup (página HTML estática com paginação)

Etapas do crawling:
  1. Buscar página inicial para descobrir total de páginas
  2. Iterar por todas as páginas usando ?page_num=X
  3. Parsear a tabela HTML e extrair cada linha
  4. Normalizar e retornar lista de dicts
"""

import asyncio
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.crawlers.base import BaseCrawler

BASE_URL = "https://www.scrapethissite.com/pages/forms/"


class HockeyCrawler(BaseCrawler):
    """
    Crawler para times de hockey usando requests síncrono
    executado em thread pool para não bloquear o event loop.
    """

    def __init__(self) -> None:
        super().__init__(source_name="hockey")
        self.base_url = BASE_URL

    # ──────────────────────────────────────────
    # Método principal (interface do BaseCrawler)
    # ──────────────────────────────────────────
    async def crawl(self) -> list[dict[str, Any]]:
        """Executa o scraping completo de todos os times de hockey."""
        self._log_start()
        try:
            # Executa a parte síncrona (requests/BS4) em thread pool
            records = await asyncio.get_event_loop().run_in_executor(
                None, self._fetch_all_pages
            )
            self._log_done(len(records))
            return records
        except Exception as exc:
            self._log_error(exc)
            raise

    # ──────────────────────────────────────────
    # Lógica síncrona de scraping
    # ──────────────────────────────────────────
    def _fetch_all_pages(self) -> list[dict[str, Any]]:
        """
        Percorre todas as páginas do site e agrega os registros.
        Detecta o total de páginas na primeira requisição.
        """
        records: list[dict[str, Any]] = []

        with httpx.Client(timeout=30.0) as client:
            # Etapa 1: buscar página 1 e detectar total de páginas
            first_page_html = self._get_page(client, page_num=1)
            first_soup = BeautifulSoup(first_page_html, "html.parser")
            total_pages = self._get_total_pages(first_soup)

            # Etapa 2: parsear página 1
            records.extend(self._parse_table(first_soup))

            # Etapa 3: iterar páginas restantes
            for page_num in range(2, total_pages + 1):
                html = self._get_page(client, page_num=page_num)
                soup = BeautifulSoup(html, "html.parser")
                records.extend(self._parse_table(soup))

        return records

    def _get_page(self, client: httpx.Client, page_num: int) -> str:
        """Realiza a requisição HTTP para uma página específica."""
        response = client.get(self.base_url, params={"page_num": page_num})
        response.raise_for_status()
        return response.text

    def _get_total_pages(self, soup: BeautifulSoup) -> int:
        """
        Extrai o número total de páginas a partir da paginação do site.
        Retorna 1 como fallback se não encontrar paginação.
        """
        # A paginação usa links com classe 'page-link' contendo números
        page_links = soup.select("ul.pagination li.page-item a.page-link")
        page_numbers: list[int] = []

        for link in page_links:
            text = link.get_text(strip=True)
            if text.isdigit():
                page_numbers.append(int(text))

        return max(page_numbers) if page_numbers else 1

    # ──────────────────────────────────────────
    # Parser da tabela HTML
    # ──────────────────────────────────────────
    def _parse_table(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """
        Extrai e normaliza os dados da tabela de times.

        Colunas esperadas na tabela (em ordem):
          Team Name | Year | Wins | Losses | OT Losses | Win % | GF | GA | Diff
        """
        records: list[dict[str, Any]] = []
        rows = soup.select("table.table tbody tr.team")

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 9:
                continue  # linha inválida/incompleta, ignora

            try:
                record = {
                    "team_name": cells[0].get_text(strip=True),
                    "year": int(cells[1].get_text(strip=True)),
                    "wins": int(cells[2].get_text(strip=True)),
                    "losses": int(cells[3].get_text(strip=True)),
                    "ot_losses": self._parse_int_or_none(
                        cells[4].get_text(strip=True)
                    ),
                    "win_pct": float(cells[5].get_text(strip=True)),
                    "goals_for": int(cells[6].get_text(strip=True)),
                    "goals_against": int(cells[7].get_text(strip=True)),
                    "goal_diff": int(cells[8].get_text(strip=True)),
                }
                records.append(record)
            except (ValueError, IndexError) as exc:
                self.logger.warning("Linha ignorada por erro de parsing: %s", exc)
                continue

        return records

    @staticmethod
    def _parse_int_or_none(value: str) -> int | None:
        """Converte string para int ou retorna None se vazia."""
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(stripped)
        except ValueError:
            return None
