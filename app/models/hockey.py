"""
Model HockeyTeam — armazena os dados coletados do site de times de hockey.

Fonte: https://www.scrapethissite.com/pages/forms/
"""

import uuid
from datetime import datetime, UTC

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HockeyTeam(Base):
    __tablename__ = "hockey_teams"

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
    team_name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, nullable=False)
    ot_losses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    win_pct: Mapped[float] = mapped_column(Float, nullable=False)
    goals_for: Mapped[int] = mapped_column(Integer, nullable=False)
    goals_against: Mapped[int] = mapped_column(Integer, nullable=False)
    goal_diff: Mapped[int] = mapped_column(Integer, nullable=False)

    # ──────────────────────────────────────────
    # Timestamp de criação do registro
    # ──────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<HockeyTeam {self.team_name} {self.year}>"
