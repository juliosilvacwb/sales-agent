"""Domain models and value objects for Authentication."""
from dataclasses import dataclass, field
import time


@dataclass(frozen=True)
class TokenClaims:
    """Immutable domain representation of decoded JWT claims."""

    sub: str
    iss: str
    iat: int
    exp: int
    roles: tuple[str, ...] = field(default_factory=lambda: ("user",))

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired based on current UTC timestamp."""
        return time.time() >= self.exp


@dataclass(frozen=True)
class AuthCredentials:
    """Immutable domain value object representing user login credentials."""

    username: str
    password: str


@dataclass(frozen=True)
class TokenResponse:
    """Immutable domain representation of a successful authentication token response."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
