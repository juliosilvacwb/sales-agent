"""Redis session persistence adapter for distributed chat histories."""
import json
import logging
import os
from typing import Any, Optional

import redis
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.messages import messages_from_dict, messages_to_dict

from src.application.port.outbound.session_store_port import SessionStorePort
from src.domain.exception.session_exceptions import SessionConnectionError, SessionStorageError
from src.domain.model.session_context import (
    DEFAULT_SESSION_TTL_SECONDS,
    SESSION_KEY_PREFIX,
    SessionContext,
)

logger = logging.getLogger(__name__)


class RedisSessionAdapter(SessionStorePort):
    """Distributed session storage backed by Redis with automated TTL renewal."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        key_prefix: str = SESSION_KEY_PREFIX,
        redis_client: Optional[Any] = None,
    ) -> None:
        """
        Args:
            redis_url: Connection string for Redis instance/cluster (defaults to REDIS_URL env var).
            ttl_seconds: Time-to-live in seconds for session keys (defaults to SESSION_TTL_SECONDS env var).
            key_prefix: Namespacing prefix for session keys.
            redis_client: Optional pre-configured Redis client (useful for mocks/tests).
        """
        resolved_url = (redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")).strip()
        resolved_ttl = (
            ttl_seconds
            if ttl_seconds is not None
            else int(os.getenv("SESSION_TTL_SECONDS", str(DEFAULT_SESSION_TTL_SECONDS)))
        )
        
        self._redis_url = resolved_url
        self._ttl_seconds = resolved_ttl
        self._key_prefix = key_prefix
        
        if redis_client is not None:
            self._client = redis_client
        else:
            self._client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )

    def _format_key(self, session_id: str) -> str:
        return SessionContext.format_redis_key(session_id, prefix=self._key_prefix)

    def get_history(self, session_id: str) -> BaseChatMessageHistory:
        """Retrieves and deserializes chat message history from Redis."""
        SessionContext.validate_session_id(session_id)
        key = self._format_key(session_id)
        
        try:
            raw_data = self._client.get(key)
            if not raw_data:
                logger.debug("No existing session found in Redis for key %s. Initializing new history.", key)
                return InMemoryChatMessageHistory()

            parsed_list = json.loads(raw_data)
            messages = messages_from_dict(parsed_list)
            return InMemoryChatMessageHistory(messages=messages)
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error("Redis connection failure while getting session %s: %s", session_id, e)
            raise SessionConnectionError(f"Failed to connect to Redis for session '{session_id}': {e}") from e
        except Exception as e:
            logger.error("Error retrieving session history from Redis for %s: %s", session_id, e)
            raise SessionStorageError(f"Failed to retrieve session '{session_id}': {e}") from e

    def save_history(self, session_id: str, history: BaseChatMessageHistory) -> None:
        """Serializes and persists chat message history in Redis with TTL expiration."""
        SessionContext.validate_session_id(session_id)
        key = self._format_key(session_id)

        try:
            serialized_dicts = messages_to_dict(history.messages)
            payload = json.dumps(serialized_dicts)
            self._client.set(key, payload, ex=self._ttl_seconds)
            logger.debug("Successfully saved session %s to Redis with TTL=%ds", key, self._ttl_seconds)
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error("Redis connection failure while saving session %s: %s", session_id, e)
            raise SessionConnectionError(f"Failed to connect to Redis for session '{session_id}': {e}") from e
        except Exception as e:
            logger.error("Error saving session history to Redis for %s: %s", session_id, e)
            raise SessionStorageError(f"Failed to save session '{session_id}': {e}") from e

    def clear_history(self, session_id: str) -> None:
        """Deletes the session key from Redis."""
        SessionContext.validate_session_id(session_id)
        key = self._format_key(session_id)

        try:
            self._client.delete(key)
            logger.debug("Deleted session key %s from Redis", key)
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error("Redis connection failure while deleting session %s: %s", session_id, e)
            raise SessionConnectionError(f"Failed to connect to Redis for session '{session_id}': {e}") from e
        except Exception as e:
            logger.error("Error deleting session history from Redis for %s: %s", session_id, e)
            raise SessionStorageError(f"Failed to clear session '{session_id}': {e}") from e

    def exists(self, session_id: str) -> bool:
        """Checks whether the session key exists in Redis."""
        SessionContext.validate_session_id(session_id)
        key = self._format_key(session_id)

        try:
            return bool(self._client.exists(key))
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error("Redis connection failure while checking session %s: %s", session_id, e)
            raise SessionConnectionError(f"Failed to connect to Redis for session '{session_id}': {e}") from e
        except Exception as e:
            logger.error("Error checking session existence in Redis for %s: %s", session_id, e)
            raise SessionStorageError(f"Failed to check existence for session '{session_id}': {e}") from e
