from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = Field(..., description="URL de conexión principal de PostgreSQL")
    MONGODB_URI: str | None = Field(
        default=None,
        description="URI de conexión de MongoDB; opcional mientras PostgreSQL siga activo",
    )
    MONGODB_DATABASE: str = Field(default="biblioteca")
    TEST_DATABASE_URL: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/FASTAPI_BIBLIOTECA_TEST",
        description="URL de conexión para pruebas de PostgreSQL",
    )
    SECRET_KEY: str = Field(..., min_length=32, description="Clave secreta JWT. Mínimo 32 caracteres")
    ALGORITHM: str = Field(default="HS256", description="Algoritmo de firma JWT")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, ge=1)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1)
    CLOUDINARY_CLOUD_NAME: str = Field(default="")
    CLOUDINARY_API_KEY: str = Field(default="")
    CLOUDINARY_API_SECRET: str = Field(default="")
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        description="Orígenes permitidos por CORS",
    )
    ENVIRONMENT: Literal["dev", "test", "prod"] = Field(default="dev")

    @field_validator("SECRET_KEY")
    @classmethod
    def validar_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("SECRET_KEY debe tener al menos 32 caracteres")
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
