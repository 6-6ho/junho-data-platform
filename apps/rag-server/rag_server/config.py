"""Runtime configuration loaded from environment variables.

All settings are required at startup except the ones marked `Optional` — startup
will fail fast if any required env var is missing, which is preferable to
silently running with a broken auth setup.
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, env_file_encoding="utf-8")

    # Database
    db_host: str = Field(default="postgres", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="app", alias="DB_NAME")
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_password: str = Field(default="postgres", alias="DB_PASSWORD")

    # Embedding
    voyage_api_key: str | None = Field(default=None, alias="VOYAGE_API_KEY")
    voyage_model: str = Field(default="voyage-3-large", alias="VOYAGE_MODEL")
    voyage_dim: int = Field(default=1024, alias="VOYAGE_DIM")

    # OAuth / auth (Phase 3 — left optional until Phase 3 runs)
    oauth_issuer: str = Field(default="https://rag.6-6ho.com", alias="OAUTH_ISSUER")
    jwt_signing_key: str | None = Field(default=None, alias="RAG_JWT_SIGNING_KEY")
    rag_login_token: str | None = Field(default=None, alias="RAG_LOGIN_TOKEN")
    rag_allowed_user_sub: str = Field(default="junho", alias="RAG_ALLOWED_USER_SUB")

    @property
    def db_dsn(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
