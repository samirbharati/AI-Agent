"""
AgentForge backend — validated application configuration.

All settings are loaded from environment variables or a .env file.
Validation happens at import time; the application will refuse to start
if required values are missing or malformed.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


class _EnvEnum(str):
    """Lightweight string enum for environment names."""


VALID_ENVS = {"development", "production", "test"}


# ---------------------------------------------------------------------------
# Settings model
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    """
    Application-wide configuration.

    Values are read (in order) from:
      1. Environment variables (highest priority).
      2. A .env file in the backend directory.
      3. Field defaults (lowest priority).
    """

    model_config = SettingsConfigDict(
        env_file=_BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────
    app_env: Annotated[str, Field(default="development")] = "development"
    app_host: str = "0.0.0.0"  # noqa: S104 — intentional, configurable server bind address
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_log_level: str = Field(default="INFO")
    secret_key: str = Field(default="CHANGE_ME_generate_a_long_random_string_here")

    # ── Database ───────────────────────────────────────────────────────────
    database_url: str = Field(
        default="sqlite+aiosqlite:///./agentforge.db",
    )

    # ── Ollama / Local LLM ─────────────────────────────────────────────────
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="qwen2.5-coder:7b")
    ollama_num_ctx: int = Field(default=4096, ge=512, le=32768)
    ollama_max_tokens: int = Field(default=2048, ge=64, le=8192)
    llm_timeout_seconds: int = Field(default=180, ge=10, le=600)
    max_concurrent_llm_requests: int = Field(default=1, ge=1, le=4)

    # ── Workflow ───────────────────────────────────────────────────────────
    max_repair_attempts: int = Field(default=3, ge=1, le=10)
    workspace_base_dir: str = Field(default="../workspace/projects")

    # ── CORS ───────────────────────────────────────────────────────────────
    cors_origins: str = Field(default="http://localhost:5173,http://localhost:3000")

    # ── Observability ──────────────────────────────────────────────────────
    log_retention_days: int = Field(default=30, ge=1, le=365)

    # ── Free Developer Services Integrations ──────────────────────────────
    # 1. GitHub & GitHub Actions
    github_enabled: bool = Field(default=True)
    github_token: str = Field(default="")
    github_owner: str = Field(default="")
    github_default_repo: str = Field(default="")

    # 2. Security Scanners (Semgrep, Gitleaks, Trivy)
    semgrep_enabled: bool = Field(default=True)
    gitleaks_enabled: bool = Field(default=True)
    trivy_enabled: bool = Field(default=True)

    # 3. OpenObserve Log Ingestion
    openobserve_enabled: bool = Field(default=False)
    openobserve_endpoint: str = Field(default="http://localhost:5080")
    openobserve_user: str = Field(default="")
    openobserve_password: str = Field(default="")
    openobserve_stream: str = Field(default="agentforge_events")

    # 4. Bugsink Error Reporting
    bugsink_enabled: bool = Field(default=False)
    bugsink_dsn: str = Field(default="")

    # 5. Better Stack Uptime & Heartbeats
    betterstack_enabled: bool = Field(default=False)
    betterstack_heartbeat_url: str = Field(default="")
    betterstack_api_token: str = Field(default="")

    # 6. Cloudflare Pages & Tunnel
    cloudflare_enabled: bool = Field(default=False)
    cloudflare_api_token: str = Field(default="")
    cloudflare_account_id: str = Field(default="")
    cloudflare_tunnel_token: str = Field(default="")

    # 7. Backblaze B2 S3-Compatible Storage
    b2_enabled: bool = Field(default=False)
    b2_endpoint_url: str = Field(default="https://s3.us-west-004.backblazeb2.com")
    b2_key_id: str = Field(default="")
    b2_app_key: str = Field(default="")
    b2_bucket_name: str = Field(default="")

    # 8. Authentication & RBAC
    auth_enabled: bool = Field(default=False)
    auth_jwt_secret: str = Field(default="agentforge-insecure-local-jwt-secret-key-32chars")

    # ── Derived / computed ─────────────────────────────────────────────────
    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def workspace_path(self) -> Path:
        raw = Path(self.workspace_base_dir)
        if not raw.is_absolute():
            raw = (_BACKEND_ROOT / raw).resolve()
        return raw

    # ── Validators ─────────────────────────────────────────────────────────
    @field_validator("app_env")
    @classmethod
    def validate_env(cls, v: str) -> str:
        if v not in VALID_ENVS:
            raise ValueError(f"app_env must be one of {VALID_ENVS}, got {v!r}")
        return v

    @field_validator("app_log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"app_log_level must be one of {valid}, got {v!r}")
        return upper

    @field_validator("secret_key")
    @classmethod
    def warn_insecure_secret(cls, v: str) -> str:
        if v.startswith("CHANGE_ME"):
            logger.warning(
                "SECRET_KEY is set to the example placeholder. "
                "Generate a secure random key for production use."
            )
        return v

    @model_validator(mode="after")
    def validate_workspace_dir(self) -> Settings:
        """Ensure the workspace base directory is accessible (create if needed)."""
        path = self.workspace_path
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ValueError(f"Cannot create workspace directory {path}: {exc}") from exc
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    The cache is cleared in tests via ``get_settings.cache_clear()``.
    """
    settings = Settings()
    _configure_logging(settings)
    _log_startup_summary(settings)
    return settings


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def _configure_logging(settings: Settings) -> None:
    """Configure root logger with the configured level."""
    logging.basicConfig(
        level=getattr(logging, settings.app_log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def _log_startup_summary(settings: Settings) -> None:
    """Log a safe summary of active configuration (no secrets)."""
    logger.info("AgentForge configuration loaded")
    logger.info("  env            : %s", settings.app_env)
    logger.info("  host:port      : %s:%s", settings.app_host, settings.app_port)
    logger.info("  database_url   : %s", _redact(settings.database_url))
    logger.info("  ollama_base_url: %s", settings.ollama_base_url)
    logger.info("  ollama_model   : %s", settings.ollama_model)
    logger.info("  ollama_num_ctx : %s", settings.ollama_num_ctx)
    logger.info("  max_repair     : %s", settings.max_repair_attempts)
    logger.info("  workspace      : %s", settings.workspace_path)


def _redact(value: str, show_chars: int = 20) -> str:
    """Return a value with the middle portion redacted."""
    if len(value) <= show_chars:
        return value
    return value[:show_chars] + "…[redacted]"
