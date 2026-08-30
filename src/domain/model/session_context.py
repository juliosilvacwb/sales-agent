"""Domain entity for a Session Context."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Optional

from src.domain.exception.session_exceptions import InvalidSessionIdError

SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
MAX_SESSION_ID_LENGTH = 128
DEFAULT_SESSION_TTL_SECONDS = 86400  # 24 hours
SESSION_KEY_PREFIX = "sales_agent:session"


@dataclass(frozen=True)
class SessionContext:
    """Encapsulates metadata and domain validation for a conversational session.
    
    Zero framework dependencies - pure Python dataclass.
    """
    session_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS
    timestamp: Optional[datetime] = None

    def __post_init__(self) -> None:
        SessionContext.validate_session_id(self.session_id)
        if self.timestamp is None:
            object.__setattr__(self, "timestamp", self.created_at)

    @staticmethod
    def validate_session_id(session_id: str) -> None:
        """Validates that a session_id matches security constraints and length requirements."""
        if not session_id or not isinstance(session_id, str):
            raise InvalidSessionIdError(str(session_id), "Session ID cannot be empty or non-string")
        if len(session_id) > MAX_SESSION_ID_LENGTH:
            raise InvalidSessionIdError(
                session_id, f"Session ID exceeds maximum length of {MAX_SESSION_ID_LENGTH} characters"
            )
        if not SESSION_ID_PATTERN.match(session_id):
            raise InvalidSessionIdError(
                session_id, "Session ID must contain only alphanumeric characters, underscores, and hyphens"
            )

    @staticmethod
    def format_redis_key(session_id: str, prefix: str = SESSION_KEY_PREFIX) -> str:
        """Formats the isolated Redis cache key for the given session ID."""
        SessionContext.validate_session_id(session_id)
        return f"{prefix}:{session_id}"

    @property
    def redis_key(self) -> str:
        """Returns the namespaced Redis key for this session context."""
        return self.format_redis_key(self.session_id)
