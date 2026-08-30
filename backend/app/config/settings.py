"""Runtime configuration.

The database backend is switchable so the analytics core can run on SQLite
during development and on PostgreSQL/PostGIS for the full deployment, without
any change to the SQLAlchemy models.  See DECISIONS.md, entry D-001.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "PRAHARI"
    engine_version: str = "0.1.0"

    # "sqlite" or "postgres"
    db_backend: str = "sqlite"
    sqlite_path: str = str(BACKEND_ROOT / "prahari.db")
    postgres_url: str = "postgresql+psycopg2://prahari:prahari@localhost:5432/prahari"

    @property
    def database_url(self) -> str:
        if self.db_backend == "postgres":
            return self.postgres_url
        return f"sqlite:///{self.sqlite_path}"

    @property
    def has_postgis(self) -> bool:
        """Distance work uses PostGIS when available, geo_utils.haversine otherwise."""
        return self.db_backend == "postgres"


settings = Settings()
