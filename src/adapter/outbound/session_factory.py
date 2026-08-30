"""Factory for resolving the active SessionStorePort adapter based on environment configuration."""
import os
import logging
from typing import Optional

from src.application.port.outbound.session_store_port import SessionStorePort
from src.adapter.outbound.memory.session_memory_adapter import SessionMemoryAdapter, session_memory_adapter
from src.adapter.outbound.redis.redis_session_adapter import RedisSessionAdapter
from src.domain.model.session_context import DEFAULT_SESSION_TTL_SECONDS

logger = logging.getLogger(__name__)


class SessionFactory:
    """Provides the configured SessionStorePort instance according to environment settings."""

    _instance: Optional[SessionStorePort] = None

    @classmethod
    def get_session_store(cls, force_refresh: bool = False) -> SessionStorePort:
        """Retrieves or instantiates the configured session store provider.
        
        Supported providers via `SESSION_STORE`:
            - 'redis': Distributed session cache via Redis.
            - 'memory': Thread-safe in-memory LRU store (default).
        """
        if cls._instance is not None and not force_refresh:
            return cls._instance

        provider = os.getenv("SESSION_STORE", "memory").strip().lower()
        ttl_seconds = int(os.getenv("SESSION_TTL_SECONDS", str(DEFAULT_SESSION_TTL_SECONDS)))

        if provider == "redis":
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()
            logger.info("Initializing RedisSessionAdapter with url: %s, ttl: %ds", redis_url, ttl_seconds)
            cls._instance = RedisSessionAdapter(redis_url=redis_url, ttl_seconds=ttl_seconds)
        else:
            logger.info("Initializing in-memory SessionMemoryAdapter (default/fallback)")
            cls._instance = session_memory_adapter

        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Resets the cached singleton instance (used in tests and reconfiguration)."""
        cls._instance = None
