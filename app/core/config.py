"""
Configurações centralizadas da aplicação usando Pydantic Settings.
Todas as variáveis de ambiente são lidas aqui e tipadas corretamente.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ──────────────────────────────────────────
    # Configurações gerais
    # ──────────────────────────────────────────
    app_name: str = "Scraper RPA API"
    debug: bool = False

    # ──────────────────────────────────────────
    # PostgreSQL
    # ──────────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "scraper_db"

    @property
    def database_url(self) -> str:
        """URL assíncrona para SQLAlchemy (asyncpg)."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """URL síncrona para Alembic e Testcontainers."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ──────────────────────────────────────────
    # RabbitMQ
    # ──────────────────────────────────────────
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_vhost: str = "/"

    @property
    def rabbitmq_url(self) -> str:
        """URL de conexão com o RabbitMQ."""
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/{self.rabbitmq_vhost}"
        )

    # ──────────────────────────────────────────
    # Nomes das filas
    # ──────────────────────────────────────────
    queue_name: str = "crawl_jobs"

    # ──────────────────────────────────────────
    # Selenium / WebDriver
    # ──────────────────────────────────────────
    selenium_headless: bool = True
    selenium_timeout: int = 30  # segundos

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Instância singleton usada em toda a aplicação
settings = Settings()
