"""
Testes unitários do OscarCrawler.

Testa a lógica de parsing sem inicializar o Selenium/WebDriver,
usando mocks para simular o comportamento dos elementos do browser.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.crawlers.oscar_crawler import OscarCrawler


@pytest.fixture
def crawler() -> OscarCrawler:
    return OscarCrawler()


def make_mock_row(title: str, nominations: int, awards: int, best_picture: str) -> MagicMock:
    """Helper: cria um mock de linha da tabela Selenium."""
    row = MagicMock()

    def find_element_side_effect(by, css):
        cell = MagicMock()
        mapping = {
            "td.film-title": title,
            "td.film-nominations": str(nominations),
            "td.film-awards": str(awards),
            "td.film-best-picture": best_picture,
        }
        cell.text = mapping.get(css, "")
        return cell

    row.find_element.side_effect = find_element_side_effect
    return row


class TestOscarParser:
    """Testes para _parse_film_table do OscarCrawler."""

    def test_parse_film_table_returns_records(self, crawler: OscarCrawler) -> None:
        """Deve retornar um dict por linha da tabela."""
        driver = MagicMock()
        driver.find_elements.return_value = [
            make_mock_row("The Hurt Locker", 9, 6, "*"),
            make_mock_row("Avatar", 9, 3, ""),
        ]

        records = crawler._parse_film_table(driver, year=2010)
        assert len(records) == 2

    def test_parse_film_table_correct_fields(self, crawler: OscarCrawler) -> None:
        """Os campos de cada registro devem estar corretos."""
        driver = MagicMock()
        driver.find_elements.return_value = [
            make_mock_row("The Hurt Locker", 9, 6, "*"),
        ]

        records = crawler._parse_film_table(driver, year=2010)
        record = records[0]

        assert record["year"] == 2010
        assert record["title"] == "The Hurt Locker"
        assert record["nominations"] == 9
        assert record["awards"] == 6
        assert record["best_picture"] is True

    def test_parse_film_table_best_picture_false(
        self, crawler: OscarCrawler
    ) -> None:
        """Campo best_picture deve ser False quando a célula estiver vazia."""
        driver = MagicMock()
        driver.find_elements.return_value = [
            make_mock_row("Avatar", 9, 3, ""),
        ]

        records = crawler._parse_film_table(driver, year=2010)
        assert records[0]["best_picture"] is False

    def test_parse_film_table_skips_bad_rows(self, crawler: OscarCrawler) -> None:
        """Linhas que lançam exceção devem ser ignoradas sem parar o loop."""
        good_row = make_mock_row("Good Film", 5, 2, "")
        bad_row = MagicMock()
        bad_row.find_element.side_effect = Exception("element not found")

        driver = MagicMock()
        driver.find_elements.return_value = [bad_row, good_row]

        records = crawler._parse_film_table(driver, year=2020)
        assert len(records) == 1
        assert records[0]["title"] == "Good Film"

    def test_parse_film_table_empty(self, crawler: OscarCrawler) -> None:
        """Tabela sem linhas deve retornar lista vazia."""
        driver = MagicMock()
        driver.find_elements.return_value = []

        records = crawler._parse_film_table(driver, year=2010)
        assert records == []

    @pytest.mark.asyncio
    async def test_crawl_delegates_to_executor(
        self, crawler: OscarCrawler
    ) -> None:
        """crawl() deve chamar _run_selenium via executor sem executá-lo diretamente."""
        with patch.object(
            crawler, "_run_selenium", return_value=[{"year": 2010, "title": "Test"}]
        ):
            # Simular executor chamando a função síncrona
            with patch(
                "asyncio.get_event_loop"
            ):
                mock_executor = MagicMock()
                mock_executor.return_value = [{"year": 2010, "title": "Test"}]
