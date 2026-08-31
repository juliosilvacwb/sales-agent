"""Outbound ports for JWT token signing and verification."""
from abc import ABC, abstractmethod
from src.domain.model.auth_models import TokenClaims, TokenResponse


class TokenSignerPort(ABC):
    """Output port interface for signing domain claims into asymmetric RS256 JWT tokens."""

    @abstractmethod
    def sign(self, claims: TokenClaims) -> TokenResponse:
        """Sign domain claims using the RSA private key and return a TokenResponse.

        Args:
            claims: Token claims to encode and sign.

        Returns:
            TokenResponse containing the signed access_token, token_type, and expires_in seconds.
        """
        pass


class TokenVerifierPort(ABC):
    """Output port interface for cryptographically verifying RS256 JWT tokens using an RSA public key."""

    @abstractmethod
    def verify(self, token: str, public_key_pem: str) -> TokenClaims:
        """Verify and decode an RS256 JWT token using the provided RSA public key.

        Args:
            token: Encoded JWT string.
            public_key_pem: RSA Public Key in PEM format.

        Returns:
            Decoded TokenClaims value object.

        Raises:
            ExpiredTokenError: If the token's expiration timestamp has passed.
            InvalidTokenError: If the token signature is invalid, tampered, or malformed.
        """
        pass
