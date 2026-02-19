"""
OscarCrawler — coleta dados de filmes vencedores do Oscar via JavaScript/AJAX.

Fonte: https://www.scrapethissite.com/pages/ajax-javascript/
Estratégia: Selenium para renderização da página + interação com botões de ano

Etapas do crawling:
  1. Inicializar o WebDriver (Chrome headless)
  2. Acessar a URL alvo
  3. Coletar todos os botões de ano disponíveis
  4. Para cada ano: clicar no botão, aguardar AJAX carregar, parsear tabela
  5. Fechar WebDriver
  6. Retornar lista de dicts com os filmes
"""

import asyncio
from typing import Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from app.core.config import settings
from app.crawlers.base import BaseCrawler

TARGET_URL = "https://www.scrapethissite.com/pages/ajax-javascript/"


class OscarCrawler(BaseCrawler):
    """
    Crawler para filmes do Oscar usando Selenium para páginas com AJAX.
    O WebDriver é criado e destruído a cada execução do método crawl().
    """

    def __init__(self) -> None:
        super().__init__(source_name="oscar")
        self.target_url = TARGET_URL
        self.timeout = settings.selenium_timeout

    # ──────────────────────────────────────────
    # Método principal (interface do BaseCrawler)
    # ──────────────────────────────────────────
    async def crawl(self) -> list[dict[str, Any]]:
        """Executa o scraping via Selenium em thread pool."""
        self._log_start()
        try:
            records = await asyncio.get_event_loop().run_in_executor(
                None, self._run_selenium
            )
            self._log_done(len(records))
            return records
        except Exception as exc:
            self._log_error(exc)
            raise

    # ──────────────────────────────────────────
    # Lógica síncrona com Selenium
    # ──────────────────────────────────────────
    def _run_selenium(self) -> list[dict[str, Any]]:
        """
        Abre o browser, navega pelo site e coleta todos os filmes por ano.
        Garante que o WebDriver seja fechado ao final (com ou sem erro).
        """
        driver = self._create_driver()
        records: list[dict[str, Any]] = []

        try:
            # Etapa 1: acessar a página principal
            driver.get(self.target_url)
            wait = WebDriverWait(driver, self.timeout)

            # Etapa 2: aguardar os botões de ano aparecerem
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "a.year-link")
                )
            )

            # Etapa 3: coletar todos os anos disponíveis (texto dos botões)
            year_buttons = driver.find_elements(By.CSS_SELECTOR, "a.year-link")
            years = [btn.text.strip() for btn in year_buttons if btn.text.strip()]

            # Etapa 4: para cada ano, clicar e extrair os filmes
            for year_text in years:
                try:
                    year_records = self._scrape_year(driver, wait, year_text)
                    records.extend(year_records)
                except Exception as exc:
                    self.logger.warning(
                        "Erro ao processar ano %s: %s", year_text, exc
                    )
                    continue

        finally:
            # Etapa 5: sempre fechar o browser
            driver.quit()

        return records

    def _scrape_year(
        self,
        driver: webdriver.Chrome,
        wait: WebDriverWait,
        year_text: str,
    ) -> list[dict[str, Any]]:
        """
        Clica no botão de um ano específico e extrai a tabela de filmes
        que é carregada via AJAX.
        """
        # Clicar no link do ano
        year_link = driver.find_element(
            By.XPATH, f"//a[contains(@class,'year-link') and text()='{year_text}']"
        )
        driver.execute_script("arguments[0].click();", year_link)

        # Aguardar tabela carregar (AJAX)
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "table.table tbody tr.film")
            )
        )

        # Parsear os filmes da tabela
        return self._parse_film_table(driver, int(year_text))

    def _parse_film_table(
        self, driver: webdriver.Chrome, year: int
    ) -> list[dict[str, Any]]:
        """
        Extrai os dados de cada linha da tabela de filmes.

        Colunas esperadas:
          Title | Nominations | Awards | Best Picture
        """
        records: list[dict[str, Any]] = []
        rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr.film")

        for row in rows:
            try:
                title = row.find_element(By.CSS_SELECTOR, "td.film-title").text.strip()
                nominations = int(
                    row.find_element(By.CSS_SELECTOR, "td.film-nominations").text.strip()
                )
                awards = int(
                    row.find_element(By.CSS_SELECTOR, "td.film-awards").text.strip()
                )
                # Best Picture: célula tem classe 'film-best-picture' com '*' ou vazio
                best_picture_cell = row.find_element(
                    By.CSS_SELECTOR, "td.film-best-picture"
                )
                best_picture = bool(best_picture_cell.text.strip())

                records.append(
                    {
                        "year": year,
                        "title": title,
                        "nominations": nominations,
                        "awards": awards,
                        "best_picture": best_picture,
                    }
                )
            except Exception as exc:
                self.logger.warning("Linha de filme ignorada: %s", exc)
                continue

        return records

    # ──────────────────────────────────────────
    # Configuração do WebDriver
    # ──────────────────────────────────────────
    def _create_driver(self) -> webdriver.Chrome:
        """
        Cria instância do Chrome WebDriver com configurações headless.
        Usa webdriver-manager para gerenciar o binário do ChromeDriver
        automaticamente.
        """
        chrome_options = Options()

        if settings.selenium_headless:
            chrome_options.add_argument("--headless=new")

        # Argumentos essenciais para rodar em containers Docker
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)
