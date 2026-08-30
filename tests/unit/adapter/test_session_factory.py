"""Unit tests for SessionFactory."""
import os
from unittest.mock import patch
from src.adapter.outbound.session_factory import SessionFactory
from src.adapter.outbound.memory.session_memory_adapter import SessionMemoryAdapter
from src.adapter.outbound.redis.redis_session_adapter import RedisSessionAdapter


def test_session_factory_default_memory():
    """Verify SessionFactory defaults to SessionMemoryAdapter when SESSION_STORE is unset or memory."""
    SessionFactory.reset_instance()
    with patch.dict(os.environ, {}, clear=True):
        store = SessionFactory.get_session_store(force_refresh=True)
        assert isinstance(store, SessionMemoryAdapter)


def test_session_factory_redis_provider():
    """Verify SessionFactory instantiates RedisSessionAdapter when SESSION_STORE=redis."""
    SessionFactory.reset_instance()
    env = {
        "SESSION_STORE": "redis",
        "REDIS_URL": "redis://custom-host:6379/1",
        "SESSION_TTL_SECONDS": "7200",
    }
    with patch.dict(os.environ, env, clear=True):
        with patch("redis.from_url") as mock_from_url:
            store = SessionFactory.get_session_store(force_refresh=True)
            assert isinstance(store, RedisSessionAdapter)
            assert store._ttl_seconds == 7200
            assert store._redis_url == "redis://custom-host:6379/1"
            mock_from_url.assert_called_once()
