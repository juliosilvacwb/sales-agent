"""Outbound port for fetching and providing the Auth Service's RSA Public Key."""
from abc import ABC, abstractmethod


class PublicKeyProviderPort(ABC):
    """Output port interface for fetching and caching the Auth Microservice's RSA Public Key."""

    @abstractmethod
    def get_public_key(self) -> str:
        """Fetch the RSA Public Key in PEM format.

        Implementations SHOULD cache the key in memory to avoid repeated network calls.

        Returns:
            RSA Public Key in PEM string format.

        Raises:
            AuthenticationError: If the public key cannot be retrieved from the Auth Service.
        """
        pass
