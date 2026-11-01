"""
Tests for the configuration module.

These tests verify that:
  - Valid configuration is accepted.
  - Invalid values are rejected at startup.
  - The cache can be cleared between tests.
  - Sensitive values are not logged in plain text.
  - The workspace directory is created automatically.
"""

from __future__ import annotations

import pytest


class TestSettingsValidation:
    """Settings field validation tests."""

    def test_valid_app_env_development(self):
        from app.config import Settings

        s = Settings(app_env="development")
        assert s.app_env == "development"
        assert s.is_development is True
        assert s.is_production is False
        assert s.is_test is False

    def test_valid_app_env_production(self):
        from app.config import Settings

        s = Settings(app_env="production")
        assert s.app_env == "production"
        assert s.is_production is True

    def test_valid_app_env_test(self):
        from app.config import Settings

        s = Settings(app_env="test")
        assert s.is_test is True

    def test_invalid_app_env_raises(self):
        from app.config import Settings
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="app_env must be one of"):
            Settings(app_env="staging")

    def test_log_level_normalised_to_uppercase(self):
        from app.config import Settings

        s = Settings(app_log_level="debug")
        assert s.app_log_level == "DEBUG"

    def test_invalid_log_level_raises(self):
        from app.config import Settings
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="app_log_level must be one of"):
            Settings(app_log_level="VERBOSE")

    def test_port_range_validated(self):
        from app.config import Settings
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(app_port=0)

        with pytest.raises(ValidationError):
            Settings(app_port=99999)

    def test_ollama_num_ctx_range(self):
        from app.config import Settings
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(ollama_num_ctx=100)  # below minimum

        s = Settings(ollama_num_ctx=8192)
        assert s.ollama_num_ctx == 8192

    def test_max_repair_attempts_range(self):
        from app.config import Settings
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(max_repair_attempts=0)

        with pytest.raises(ValidationError):
            Settings(max_repair_attempts=11)

    def test_cors_origins_list_parsed(self):
        from app.config import Settings

        s = Settings(cors_origins="http://localhost:5173,http://localhost:3000")
        assert "http://localhost:5173" in s.cors_origins_list
        assert "http://localhost:3000" in s.cors_origins_list
        assert len(s.cors_origins_list) == 2

    def test_cors_origins_single(self):
        from app.config import Settings

        s = Settings(cors_origins="http://localhost:3000")
        assert s.cors_origins_list == ["http://localhost:3000"]


class TestSettingsCache:
    """Tests for the cached settings singleton."""

    def test_get_settings_returns_same_instance(self, reset_settings_cache):
        from app.config import get_settings

        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_cache_cleared_between_tests(self, reset_settings_cache):
        """Each test gets a fresh settings instance after cache clear."""
        from app.config import get_settings

        s1 = get_settings()
        get_settings.cache_clear()
        s2 = get_settings()
        # Different Python objects but same values
        assert s1.app_env == s2.app_env


class TestRedact:
    """Tests for the _redact helper (no secrets in logs)."""

    def test_short_value_not_truncated(self):
        from app.config import _redact

        assert _redact("short") == "short"

    def test_long_value_redacted(self):
        from app.config import _redact

        result = _redact("a" * 100, show_chars=10)
        assert result.startswith("a" * 10)
        assert "[redacted]" in result
        assert len(result) < 100


class TestWorkspacePath:
    """Tests for workspace directory handling."""

    def test_workspace_path_is_absolute(self):
        from app.config import Settings

        s = Settings()
        assert s.workspace_path.is_absolute()

    def test_workspace_created_if_missing(self, tmp_path):
        from app.config import Settings

        ws = tmp_path / "test_workspace"
        assert not ws.exists()

        s = Settings(workspace_base_dir=str(ws))
        assert ws.exists()
        assert s.workspace_path == ws
