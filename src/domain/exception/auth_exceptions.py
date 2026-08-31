"""Domain-specific exceptions for Authentication."""


class AuthenticationError(Exception):
    """Base domain exception for all authentication-related failures."""


class InvalidCredentialsError(AuthenticationError):
    """Raised when authentication credentials (username/password) are invalid."""

    def __init__(self, message: str = "Credenciais inválidas") -> None:
        super().__init__(message)


class InvalidTokenError(AuthenticationError):
    """Raised when a JWT token is malformed, invalid or tampered with."""

    def __init__(self, reason: str = "Token inválido") -> None:
        self.reason = reason
        super().__init__(f"Token inválido: {reason}")


class ExpiredTokenError(InvalidTokenError):
    """Raised when a JWT token's expiration timestamp (exp) has passed."""

    def __init__(self, reason: str = "Token expirado") -> None:
        super().__init__(reason=reason)


class MissingTokenError(AuthenticationError):
    """Raised when the Authorization header or Bearer token is missing."""

    def __init__(self, reason: str = "Cabeçalho de autorização ausente") -> None:
        self.reason = reason
        super().__init__(f"Token ausente: {reason}")
