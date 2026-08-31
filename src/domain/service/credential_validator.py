"""Domain service for constant-time credential validation."""
import hmac
from src.domain.model.auth_models import AuthCredentials
from src.domain.exception.auth_exceptions import InvalidCredentialsError


class CredentialValidator:
    """Pure domain service that validates authentication credentials using timing-attack safe comparison."""

    def validate(
        self,
        credentials: AuthCredentials,
        expected_username: str,
        expected_password: str,
    ) -> bool:
        """Validate user credentials against expected values using constant-time comparison.

        Args:
            credentials: User-provided credentials (username and password).
            expected_username: Authorized username.
            expected_password: Authorized password.

        Returns:
            True if credentials match.

        Raises:
            InvalidCredentialsError: If credentials do not match expected values.
        """
        is_username_valid = hmac.compare_digest(
            credentials.username.encode("utf-8"),
            expected_username.encode("utf-8"),
        )
        is_password_valid = hmac.compare_digest(
            credentials.password.encode("utf-8"),
            expected_password.encode("utf-8"),
        )

        if not (is_username_valid and is_password_valid):
            raise InvalidCredentialsError("Credenciais inválidas")

        return True
