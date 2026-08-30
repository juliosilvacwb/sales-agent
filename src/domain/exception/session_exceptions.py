"""Domain-specific exceptions for Session Management."""


class SessionDomainError(Exception):
    """Base domain exception for all session-related failures."""


class InvalidSessionIdError(SessionDomainError):
    """Raised when a session identifier violates format or length constraints."""

    def __init__(self, session_id: str, reason: str) -> None:
        self.session_id = session_id
        self.reason = reason
        super().__init__(f"Invalid session_id '{session_id}': {reason}")


class SessionStorageError(SessionDomainError):
    """Raised when a persistence or retrieval operation fails on the session store."""


class SessionConnectionError(SessionStorageError):
    """Raised when connection to the distributed session store fails or times out."""
