"""
Schemas Pydantic para OscarFilm.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OscarFilmBase(BaseModel):
    """Campos base do filme do Oscar."""

    year: int = Field(..., description="Ano da cerimônia do Oscar")
    title: str = Field(..., description="Título do filme")
    nominations: int = Field(..., ge=0, description="Número de indicações")
    awards: int = Field(..., ge=0, description="Número de prêmios ganhos")
    best_picture: bool = Field(..., description="Se ganhou o prêmio de Melhor Filme")


class OscarFilmCreate(OscarFilmBase):
    """Schema usado internamente para persistir um filme após o scraping."""

    job_id: uuid.UUID


class OscarFilmResponse(OscarFilmBase):
    """Schema de resposta da API com campos adicionais do banco."""

    id: int
    job_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
