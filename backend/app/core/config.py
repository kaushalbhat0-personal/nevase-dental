import os
from typing import Any

from pydantic import Field, model_validator
from typing_extensions import Self
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SECRET_FALLBACK = "fallback-not-for-prod"


class Settings(BaseSettings):
    """Application settings from environment (Render) and optional local `.env`."""

    DATABASE_URL: str = Field(
        ...,
        description="SQLAlchemy database URL (required). Set via environment on production.",
    )
    SECRET_KEY: str = Field(
        default=_DEV_SECRET_FALLBACK,
        description="JWT signing secret. Use a strong value in production.",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Doctor slots: optional time-off clamp to weekly availability (local wall-clock intersection).
    DOCTOR_SLOT_CLIP_PARTIAL_TIME_OFF_TO_AVAILABILITY: bool = False

    # Clinic identity
    CLINIC_NAME: str = "Nevase Multispecialist Dental Clinic"
    CLINIC_SLUG: str = "nevase-dental"

    # Slot read cache: disable for debugging; backend "memory" is default (Redis reserved for future).
    DOCTOR_SLOT_CACHE_ENABLED: bool = True

    # When true, POST mark-completed requires ``Idempotency-Key`` (strict dedupe of completion side effects).
    REQUIRE_APPOINTMENT_COMPLETION_IDEMPOTENCY_KEY: bool = False
    #: Short-lived cache for GET /admin/integrity-scan responses (seconds; 0 disables).
    INTEGRITY_SCAN_CACHE_SECONDS: int = 0
    #: Per client identity (JWT sub or IP) sliding window budget for integrity scans.
    INTEGRITY_SCAN_RATE_LIMIT_PER_MINUTE: int = 12
    #: Optional Slack/Discord webhook for integrity scan issues and idempotency drift alerts.
    INTEGRITY_ALERT_WEBHOOK_URL: str | None = None

    # CORS settings - EXPLICIT ORIGINS ONLY (FastAPI CORSMiddleware doesn't support wildcards)
    # For Vercel preview URLs, add them explicitly or set ALLOWED_ORIGINS=* in .env for development only
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @model_validator(mode="before")
    @classmethod
    def database_url_from_environment(cls, data: Any) -> Any:
        """Require DATABASE_URL from merged env / .env with a clear error (matches os.getenv semantics)."""
        if not isinstance(data, dict):
            return data
        val = data.get("DATABASE_URL")
        if val is None or (isinstance(val, str) and not val.strip()):
            val = os.getenv("DATABASE_URL")
        if val is None or (isinstance(val, str) and not str(val).strip()):
            raise ValueError("DATABASE_URL not set")
        return {**data, "DATABASE_URL": str(val).strip()}

    @property
    def cors_origins(self) -> list[str]:
        if not self.ALLOWED_ORIGINS:
            # Fallback for production if env var is not set
            if self.ENVIRONMENT == "production":
                return ["https://nevase-dental.vercel.app"]
            return ["http://localhost:5173", "http://127.0.0.1:5173"]

        origins = [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]
        # Filter out wildcard entries.
        #
        # FastAPI/Starlette CORSMiddleware expects explicit origins for credentialed requests.
        # We keep the filtering conservative: any entry containing '*' is ignored.
        explicit_origins = [o for o in origins if "*" not in o]

        # Ensure production frontend is always included in production
        if self.ENVIRONMENT == "production":
            prod_origin = "https://nevase-dental.vercel.app"
            if prod_origin not in explicit_origins:
                explicit_origins.append(prod_origin)

        # If nothing valid remains, fall back to permissive behavior to avoid bricking local dev.
        # Prefer setting explicit `ALLOWED_ORIGINS` instead of relying on this.
        return explicit_origins if explicit_origins else ["*"]

    @model_validator(mode="after")
    def production_must_not_use_dev_defaults(self) -> Self:
        if self.ENVIRONMENT == "production":
            if "sqlite" in self.DATABASE_URL.lower():
                raise ValueError(
                    "DATABASE_URL must not use SQLite in production; use PostgreSQL."
                )
            if self.SECRET_KEY == _DEV_SECRET_FALLBACK:
                raise ValueError(
                    "SECRET_KEY must be set to a strong secret in production (not the dev fallback)."
                )
            if not self.REQUIRE_APPOINTMENT_COMPLETION_IDEMPOTENCY_KEY:
                raise ValueError(
                    "REQUIRE_APPOINTMENT_COMPLETION_IDEMPOTENCY_KEY must be true in production "
                    "so appointment completion persists idempotent outcomes."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
