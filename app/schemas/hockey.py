"""
Schemas Pydantic para HockeyTeam.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HockeyTeamBase(BaseModel):
    """Campos base compartilhados entre criação e leitura."""

    team_name: str = Field(..., description="Nome do time")
    year: int = Field(..., description="Temporada (ano)")
    wins: int = Field(..., ge=0)
    losses: int = Field(..., ge=0)
    ot_losses: int | None = Field(None, ge=0, description="Derrotas na prorrogação")
    win_pct: float = Field(..., ge=0.0, le=1.0, description="Percentual de vitórias")
    goals_for: int = Field(..., ge=0, description="Gols marcados (GF)")
    goals_against: int = Field(..., ge=0, description="Gols sofridos (GA)")
    goal_diff: int = Field(..., description="Diferença de gols")


class HockeyTeamCreate(HockeyTeamBase):
    """Schema usado internamente para persistir um time após o scraping."""

    job_id: uuid.UUID


class HockeyTeamResponse(HockeyTeamBase):
    """Schema de resposta da API com campos adicionais do banco."""

    id: int
    job_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
