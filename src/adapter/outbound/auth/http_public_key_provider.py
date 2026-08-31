"""HTTP client adapter for fetching and caching the Auth Service's RSA Public Key."""
import os
import json
import logging
import urllib.request
import urllib.error
from typing import Optional
from src.application.port.outbound.public_key_provider_port import PublicKeyProviderPort
from src.domain.exception.auth_exceptions import AuthenticationError

logger = logging.getLogger(__name__)


class HttpPublicKeyProvider(PublicKeyProviderPort):
    """Fetches and caches the RSA Public Key from the remote Auth Microservice."""

    def __init__(self, auth_service_url: Optional[str] = None) -> None:
        self._auth_service_url = (
            auth_service_url or os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
        ).rstrip("/")
        self._cached_public_key: Optional[str] = None

    def get_public_key(self) -> str:
        """Retrieve the RSA Public Key in PEM format.

        Returns cached in-memory key if available; otherwise fetches from Auth Microservice.

        Returns:
            RSA Public Key PEM string.

        Raises:
            AuthenticationError: If unable to reach the Auth Service or parse the key.
        """
        if self._cached_public_key is not None:
            return self._cached_public_key

        return self.refresh_public_key()

    def refresh_public_key(self) -> str:
        """Force fetch and update the RSA Public Key from Auth Microservice.

        Returns:
            Updated RSA Public Key PEM string.

        Raises:
            AuthenticationError: If request fails.
        """
        url = f"{self._auth_service_url}/auth/public-key"
        logger.info("Fetching RSA Public Key from Auth Microservice at: %s", url)
        try:
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/json", "User-Agent": "SalesAgent-SecurityGuard/1.0"},
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status != 200:
                    raise AuthenticationError(
                        f"Falha ao obter chave pública: HTTP status {response.status}"
                    )
                body = response.read().decode("utf-8")
                data = json.loads(body)
                public_key = data.get("public_key")
                if not public_key or not isinstance(public_key, str):
                    raise AuthenticationError("Resposta de chave pública inválida da Auth Service")

                self._cached_public_key = public_key.strip()
                logger.info("RSA Public Key successfully cached in memory")
                return self._cached_public_key
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            logger.error("Error communicating with Auth Service at %s: %s", url, exc)
            raise AuthenticationError(
                f"Erro de comunicação com o serviço de autenticação ({url}): {exc}"
            ) from exc
        except Exception as exc:
            logger.error("Unexpected error fetching public key: %s", exc, exc_info=True)
            raise AuthenticationError(f"Erro inesperado ao obter chave pública: {exc}") from exc
