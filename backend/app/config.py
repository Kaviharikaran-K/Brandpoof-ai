from functools import lru_cache
from urllib.parse import parse_qsl, urlencode

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "BrandProof AI"
    environment: str = "development"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 60 * 24
    database_url: str = "sqlite+aiosqlite:///./brandproof.db"
    upload_dir: str = "uploads"
    max_upload_mb: int = 10
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @field_validator("database_url")
    @classmethod
    def _normalise_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            value = "postgresql://" + value[len("postgres://"):]
        if value.startswith("postgresql://"):
            value = "postgresql+asyncpg://" + value[len("postgresql://"):]
        if value.startswith("postgresql+asyncpg://") and "?" in value:
            base, _, query = value.partition("?")
            params = parse_qsl(query, keep_blank_values=True)
            sslmode = next((v for k, v in params if k == "sslmode"), None)
            params = [(k, v) for k, v in params if k != "sslmode"]
            if sslmode is not None and not any(k == "ssl" for k, _ in params):
                params.append(("ssl", sslmode))
            value = base + ("?" + urlencode(params) if params else "")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
