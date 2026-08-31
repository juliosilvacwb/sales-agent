"""Inbound port for user authentication use case."""
from abc import ABC, abstractmethod
from src.domain.model.auth_models import AuthCredentials, TokenResponse


class AuthenticateUserUseCase(ABC):
    """Input port interface for authenticating credentials and issuing JWT tokens."""

    @abstractmethod
    def authenticate(self, credentials: AuthCredentials) -> TokenResponse:
        """Authenticate user credentials and issue an RS256 JWT access token.

        Args:
            credentials: User credentials (username and password).

        Returns:
            TokenResponse with access_token, token_type, and expiration.

        Raises:
            InvalidCredentialsError: If credentials are invalid.
        """
        pass
