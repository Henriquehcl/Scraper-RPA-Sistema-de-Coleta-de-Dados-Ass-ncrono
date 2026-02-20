# Importa todos os models para registrá-los na metadata do SQLAlchemy
from app.models.hockey import HockeyTeam
from app.models.job import Job
from app.models.oscar import OscarFilm

__all__ = ["Job", "HockeyTeam", "OscarFilm"]
