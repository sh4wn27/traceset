"""Shared pytest fixtures for Traceset tests."""

import pytest

from backend.config import get_settings


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    """Inject dummy secrets and clear lru_cache so services see the patched env."""
    get_settings.cache_clear()
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "eyJtest")
    yield
    get_settings.cache_clear()
