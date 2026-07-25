"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration for the local prediction API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    model_artifact_root: Path = Field(default=Path("artifacts"))
    model_version: str | None = Field(default=None)
    verify_artifact_checksums: bool = True
    max_upload_mb: int = Field(default=25, ge=1)
    max_rows_per_well: int = Field(default=100_000, ge=1)
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_log_level: str = "INFO"
    cors_allowed_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173"
    )

    @field_validator("model_version", mode="before")
    @classmethod
    def _empty_version_to_none(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("verify_artifact_checksums", mode="before")
    @classmethod
    def _parse_bool(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return True
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
        raise ValueError(
            f"Invalid boolean for VERIFY_ARTIFACT_CHECKSUMS: {value!r}"
        )

    @field_validator("api_log_level")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        level = str(value).strip().upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if level not in allowed:
            raise ValueError(f"API_LOG_LEVEL must be one of {sorted(allowed)}")
        return level

    @model_validator(mode="after")
    def _resolve_artifact_root(self) -> "Settings":
        root = Path(self.model_artifact_root)
        if not root.is_absolute():
            root = (_project_root() / root).resolve()
        self.model_artifact_root = root
        return self

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb) * 1024 * 1024

    @property
    def cors_origins(self) -> list[str]:
        return [part.strip() for part in self.cors_allowed_origins.split(",") if part.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
