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
    engine_version: str = "1.0.0"

    #: "development" or "production". The demo sign-in fallback refuses to run
    #: in production, so an unauthenticated build cannot reach a deployment.
    env: str = "development"

    # --- Firebase ---
    firebase_enabled: bool = False
    firebase_credentials_path: str = "app/config/firebase_credentials.json"
    firebase_storage_bucket: str = ""

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
    def credentials_file(self) -> Path:
        path = Path(self.firebase_credentials_path)
        return path if path.is_absolute() else BACKEND_ROOT / path

    @property
    def firebase_ready(self) -> bool:
        """True only when Firebase is switched on AND the key is actually there."""
        return self.firebase_enabled and self.credentials_file.exists()

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def has_postgis(self) -> bool:
        """Distance work uses PostGIS when available, geo_utils.haversine otherwise."""
        return self.db_backend == "postgres"


settings = Settings()
