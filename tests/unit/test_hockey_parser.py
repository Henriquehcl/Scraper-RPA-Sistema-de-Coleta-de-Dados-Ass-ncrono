"""
Testes unitários do parser de Hockey.

Testa a lógica de extração de dados da tabela HTML sem realizar
chamadas reais à internet.
"""

import pytest
from bs4 import BeautifulSoup

from app.crawlers.hockey_crawler import HockeyCrawler


@pytest.fixture
def crawler() -> HockeyCrawler:
    return HockeyCrawler()


class TestHockeyParser:
    """Testes para o método _parse_table do HockeyCrawler."""

    def test_parse_table_returns_correct_count(
        self, crawler: HockeyCrawler, sample_hockey_html: str
    ) -> None:
        """Deve retornar 2 registros para 2 linhas na tabela."""
        soup = BeautifulSoup(sample_hockey_html, "html.parser")
        records = crawler._parse_table(soup)
        assert len(records) == 2

    def test_parse_table_correct_fields(
        self, crawler: HockeyCrawler, sample_hockey_html: str
    ) -> None:
        """Os campos do primeiro registro devem ser extraídos corretamente."""
        soup = BeautifulSoup(sample_hockey_html, "html.parser")
        records = crawler._parse_table(soup)
        first = records[0]

        assert first["team_name"] == "Boston Bruins"
        assert first["year"] == 2011
        assert first["wins"] == 46
        assert first["losses"] == 25
        assert first["ot_losses"] == 11
        assert first["win_pct"] == pytest.approx(0.561)
        assert first["goals_for"] == 246
        assert first["goals_against"] == 229
        assert first["goal_diff"] == 17

    def test_parse_table_second_record(
        self, crawler: HockeyCrawler, sample_hockey_html: str
    ) -> None:
        """O segundo registro deve ter goal_diff negativo."""
        soup = BeautifulSoup(sample_hockey_html, "html.parser")
        records = crawler._parse_table(soup)
        assert records[1]["goal_diff"] == -14

    def test_parse_table_empty(self, crawler: HockeyCrawler) -> None:
        """Tabela sem linhas de time deve retornar lista vazia."""
        html = "<html><body><table class='table'><tbody></tbody></table></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        records = crawler._parse_table(soup)
        assert records == []

    def test_parse_table_ignores_incomplete_rows(
        self, crawler: HockeyCrawler
    ) -> None:
        """Linhas com menos de 9 colunas devem ser ignoradas sem erro."""
        html = """
        <html><body>
        <table class="table">
          <tbody>
            <tr class="team"><td>Incomplete</td><td>2020</td></tr>
          </tbody>
        </table>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        records = crawler._parse_table(soup)
        assert records == []

    def test_parse_int_or_none_empty_string(self, crawler: HockeyCrawler) -> None:
        """String vazia deve retornar None."""
        assert crawler._parse_int_or_none("") is None
        assert crawler._parse_int_or_none("   ") is None

    def test_parse_int_or_none_valid(self, crawler: HockeyCrawler) -> None:
        """String numérica deve retornar int."""
        assert crawler._parse_int_or_none("42") == 42
        assert crawler._parse_int_or_none(" 7 ") == 7

    def test_get_total_pages_extracts_max(self, crawler: HockeyCrawler) -> None:
        """Deve retornar o maior número de página encontrado."""
        html = """
        <ul class="pagination">
          <li class="page-item"><a class="page-link" href="?page_num=1">1</a></li>
          <li class="page-item"><a class="page-link" href="?page_num=2">2</a></li>
          <li class="page-item"><a class="page-link" href="?page_num=3">3</a></li>
        </ul>
        """
        soup = BeautifulSoup(html, "html.parser")
        assert crawler._get_total_pages(soup) == 3

    def test_get_total_pages_fallback_to_one(
        self, crawler: HockeyCrawler
    ) -> None:
        """Sem paginação deve retornar 1."""
        soup = BeautifulSoup("<html></html>", "html.parser")
        assert crawler._get_total_pages(soup) == 1
