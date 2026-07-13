"""
Shared pytest fixtures and configuration for the test suite.
"""
import os
import sys
import asyncio
import pytest

# Ensure environment variables are set before any backend import
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-characters-long!!")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-also-long-enough")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://llmops:llmops_pass@localhost:5432/llmops_test")
os.environ.setdefault("SYNC_DATABASE_URL", "postgresql://llmops:llmops_pass@localhost:5432/llmops_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_llm_response():
    """A standard mocked LLM provider response dict."""
    return {
        "content": "This is a mocked response.",
        "tokens_input": 50,
        "tokens_output": 20,
        "model": "gpt-4o-mini",
        "provider": "openai",
        "latency_ms": 250,
    }


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Ensure settings cache doesn't leak between tests."""
    from backend.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
