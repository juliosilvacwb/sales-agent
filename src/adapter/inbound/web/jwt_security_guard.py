"""FastAPI inbound security guard for JWT token verification."""
import os
import time
import logging
from typing import Optional
from fastapi import Header, HTTPException, status
from src.domain.model.auth_models import TokenClaims
from src.domain.exception.auth_exceptions import (
    AuthenticationError,
    InvalidTokenError,
    ExpiredTokenError,
)
from src.application.port.outbound.token_port import TokenVerifierPort
from src.application.port.outbound.public_key_provider_port import PublicKeyProviderPort
from src.adapter.outbound.auth.jwt_token_adapter import JwtRs256TokenAdapter
from src.adapter.outbound.auth.http_public_key_provider import HttpPublicKeyProvider

logger = logging.getLogger(__name__)

# Singletons for adapter instances
_token_verifier_instance: Optional[TokenVerifierPort] = None
_public_key_provider_instance: Optional[PublicKeyProviderPort] = None


def get_token_verifier() -> TokenVerifierPort:
    """Dependency provider for TokenVerifierPort."""
    global _token_verifier_instance
    if _token_verifier_instance is None:
        _token_verifier_instance = JwtRs256TokenAdapter()
    return _token_verifier_instance


def set_token_verifier(verifier: TokenVerifierPort) -> None:
    """Set custom token verifier instance (for testing)."""
    global _token_verifier_instance
    _token_verifier_instance = verifier


def get_public_key_provider() -> PublicKeyProviderPort:
    """Dependency provider for PublicKeyProviderPort."""
    global _public_key_provider_instance
    if _public_key_provider_instance is None:
        _public_key_provider_instance = HttpPublicKeyProvider()
    return _public_key_provider_instance


def set_public_key_provider(provider: PublicKeyProviderPort) -> None:
    """Set custom public key provider instance (for testing)."""
    global _public_key_provider_instance
    _public_key_provider_instance = provider


def is_auth_enabled() -> bool:
    """Check if authentication enforcement is enabled via environment variable."""
    return os.getenv("AUTH_ENABLED", "false").lower() in ("true", "1", "yes")


def verify_jwt_token(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> TokenClaims:
    """FastAPI dependency to extract, validate, and verify Bearer JWT token from request header.

    Args:
        authorization: Value of the HTTP Authorization header.

    Returns:
        Decoded TokenClaims if token is valid (or fallback claims if AUTH_ENABLED=false).

    Raises:
        HTTPException: 401 Unauthorized if token is missing, malformed, invalid, or expired.
    """
    if not is_auth_enabled():
        logger.debug("Authentication disabled via AUTH_ENABLED=false. Bypassing token validation.")
        now = int(time.time())
        return TokenClaims(
            sub="anonymous_dev",
            iss="local-bypass",
            iat=now,
            exp=now + 86400,
            roles=("user", "admin"),
        )

    if not authorization:
        logger.warning("Missing Authorization header in request to protected endpoint")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ausente ou cabeçalho inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].strip().lower() != "bearer" or not parts[1].strip():
        logger.warning("Malformed Authorization header format: %s", authorization)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de token inválido. Use 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1].strip()

    try:
        provider = get_public_key_provider()
        public_key_pem = provider.get_public_key()
        verifier = get_token_verifier()
        claims = verifier.verify(token, public_key_pem)
        logger.info("Successfully verified JWT token for sub: %s", claims.sub)
        return claims
    except ExpiredTokenError as exc:
        logger.warning("Token verification failed (expired): %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except (InvalidTokenError, AuthenticationError) as exc:
        logger.warning("Token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error during token verification: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
