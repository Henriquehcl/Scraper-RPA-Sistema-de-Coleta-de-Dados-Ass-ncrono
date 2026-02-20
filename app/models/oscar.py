"""
Model OscarFilm — armazena os dados coletados do site de filmes vencedores do Oscar.

Fonte: https://www.scrapethissite.com/pages/ajax-javascript/
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OscarFilm(Base):
    __tablename__ = "oscar_films"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ──────────────────────────────────────────
    # Referência ao job que gerou este registro
    # ──────────────────────────────────────────
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ──────────────────────────────────────────
    # Campos coletados do site
    # ──────────────────────────────────────────
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    nominations: Mapped[int] = mapped_column(Integer, nullable=False)
    awards: Mapped[int] = mapped_column(Integer, nullable=False)
    best_picture: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ──────────────────────────────────────────
    # Timestamp de criação do registro
    # ──────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(datetime.UTC),
    )

    def __repr__(self) -> str:
        return f"<OscarFilm {self.title!r} ({self.year})>"
