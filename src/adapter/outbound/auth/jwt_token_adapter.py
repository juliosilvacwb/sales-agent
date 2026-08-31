"""RS256 JWT Token signing and verification adapter using PyJWT and cryptography."""
import logging
from typing import Optional, List
import jwt
from src.domain.model.auth_models import TokenClaims, TokenResponse
from src.domain.exception.auth_exceptions import (
    AuthenticationError,
    InvalidTokenError,
    ExpiredTokenError,
)
from src.application.port.outbound.token_port import TokenSignerPort, TokenVerifierPort

logger = logging.getLogger(__name__)


class JwtRs256TokenAdapter(TokenSignerPort, TokenVerifierPort):
    """Adapter implementing RS256 JWT token creation and cryptographic verification."""

    def __init__(
        self,
        private_key_pem: Optional[str] = None,
        allowed_algorithms: Optional[List[str]] = None,
    ) -> None:
        self._private_key_pem = private_key_pem
        self._allowed_algorithms = allowed_algorithms or ["RS256"]

    def sign(self, claims: TokenClaims) -> TokenResponse:
        """Sign domain claims using the RSA Private Key.

        Args:
            claims: TokenClaims to be encoded into JWT.

        Returns:
            TokenResponse containing access_token, token_type, and expires_in.

        Raises:
            AuthenticationError: If private key is not configured for signing.
        """
        if not self._private_key_pem:
            raise AuthenticationError("Chave privada RSA não configurada para emissão de tokens")

        payload = {
            "sub": claims.sub,
            "iss": claims.iss,
            "iat": claims.iat,
            "exp": claims.exp,
            "roles": list(claims.roles),
        }

        try:
            token = jwt.encode(
                payload,
                self._private_key_pem,
                algorithm="RS256",
            )
        except Exception as exc:
            logger.error("Failed to sign JWT token: %s", exc, exc_info=True)
            raise AuthenticationError(f"Falha ao assinar token JWT: {exc}") from exc

        expires_in = max(0, claims.exp - claims.iat)
        return TokenResponse(
            access_token=token,
            token_type="Bearer",
            expires_in=expires_in,
        )

    def verify(self, token: str, public_key_pem: str) -> TokenClaims:
        """Verify and decode an RS256 JWT token using the RSA Public Key.

        Args:
            token: Encoded JWT string.
            public_key_pem: RSA Public Key in PEM format.

        Returns:
            TokenClaims domain value object.

        Raises:
            ExpiredTokenError: If token expiration (exp) has passed.
            InvalidTokenError: If token signature or structure is invalid.
        """
        try:
            payload = jwt.decode(
                token,
                public_key_pem,
                algorithms=self._allowed_algorithms,
                options={"require": ["exp", "iat", "sub", "iss"]},
            )
        except jwt.ExpiredSignatureError as exc:
            logger.warning("Token expired: %s", exc)
            raise ExpiredTokenError("Token expirado") from exc
        except jwt.PyJWTError as exc:
            logger.warning("Invalid JWT token: %s", exc)
            raise InvalidTokenError(str(exc)) from exc
        except Exception as exc:
            logger.error("Unexpected error during token verification: %s", exc, exc_info=True)
            raise InvalidTokenError("Falha na validação do token") from exc

        roles = tuple(payload.get("roles", ["user"]))
        return TokenClaims(
            sub=payload["sub"],
            iss=payload["iss"],
            iat=int(payload["iat"]),
            exp=int(payload["exp"]),
            roles=roles,
        )
