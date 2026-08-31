"""Unit tests for JwtSecurityGuard and HttpPublicKeyProvider."""
import json
import time
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from src.domain.model.auth_models import TokenClaims
from src.domain.exception.auth_exceptions import (
    AuthenticationError,
    InvalidTokenError,
    ExpiredTokenError,
)
from src.application.port.outbound.token_port import TokenVerifierPort
from src.application.port.outbound.public_key_provider_port import PublicKeyProviderPort
from src.adapter.inbound.web.jwt_security_guard import (
    verify_jwt_token,
    set_token_verifier,
    set_public_key_provider,
)
from src.adapter.outbound.auth.http_public_key_provider import HttpPublicKeyProvider


@pytest.fixture(autouse=True)
def reset_guard_dependencies():
    """Reset singletons after each test."""
    yield
    set_token_verifier(None)  # type: ignore
    set_public_key_provider(None)  # type: ignore


class TestJwtSecurityGuard:
    """Test suite for FastAPI dependency guard."""

    def test_auth_disabled_returns_bypass_claims(self, monkeypatch):
        monkeypatch.setenv("AUTH_ENABLED", "false")
        claims = verify_jwt_token(authorization=None)
        assert claims.sub == "anonymous_dev"
        assert "admin" in claims.roles

    def test_missing_authorization_header_raises_401(self, monkeypatch):
        monkeypatch.setenv("AUTH_ENABLED", "true")
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt_token(authorization=None)
        assert exc_info.value.status_code == 401
        assert exc_info.value.headers.get("WWW-Authenticate") == "Bearer"

    def test_malformed_authorization_scheme_raises_401(self, monkeypatch):
        monkeypatch.setenv("AUTH_ENABLED", "true")
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt_token(authorization="Basic dXNlcjpwYXNz")
        assert exc_info.value.status_code == 401
        assert "Formato de token inválido" in exc_info.value.detail

    def test_valid_bearer_token_returns_claims(self, monkeypatch):
        monkeypatch.setenv("AUTH_ENABLED", "true")
        mock_provider = MagicMock(spec=PublicKeyProviderPort)
        mock_provider.get_public_key.return_value = "-----BEGIN PUBLIC KEY-----\nMOCK\n-----END PUBLIC KEY-----"

        mock_verifier = MagicMock(spec=TokenVerifierPort)
        now = int(time.time())
        expected_claims = TokenClaims(
            sub="valid_user",
            iss="sales-auth-service",
            iat=now,
            exp=now + 3600,
            roles=("user",),
        )
        mock_verifier.verify.return_value = expected_claims

        set_public_key_provider(mock_provider)
        set_token_verifier(mock_verifier)

        claims = verify_jwt_token(authorization="Bearer valid.jwt.token")
        assert claims == expected_claims
        mock_verifier.verify.assert_called_once_with("valid.jwt.token", mock_provider.get_public_key())

    def test_expired_token_raises_401(self, monkeypatch):
        monkeypatch.setenv("AUTH_ENABLED", "true")
        mock_provider = MagicMock(spec=PublicKeyProviderPort)
        mock_provider.get_public_key.return_value = "mock_public_key"

        mock_verifier = MagicMock(spec=TokenVerifierPort)
        mock_verifier.verify.side_effect = ExpiredTokenError("Token expirado")

        set_public_key_provider(mock_provider)
        set_token_verifier(mock_verifier)

        with pytest.raises(HTTPException) as exc_info:
            verify_jwt_token(authorization="Bearer expired.jwt.token")
        assert exc_info.value.status_code == 401
        assert "Token inválido ou expirado" in exc_info.value.detail

    def test_invalid_token_raises_401(self, monkeypatch):
        monkeypatch.setenv("AUTH_ENABLED", "true")
        mock_provider = MagicMock(spec=PublicKeyProviderPort)
        mock_provider.get_public_key.return_value = "mock_public_key"

        mock_verifier = MagicMock(spec=TokenVerifierPort)
        mock_verifier.verify.side_effect = InvalidTokenError("Tampered signature")

        set_public_key_provider(mock_provider)
        set_token_verifier(mock_verifier)

        with pytest.raises(HTTPException) as exc_info:
            verify_jwt_token(authorization="Bearer tampered.jwt.token")
        assert exc_info.value.status_code == 401
        assert "Token inválido ou expirado" in exc_info.value.detail


class TestHttpPublicKeyProvider:
    """Test suite for HttpPublicKeyProvider."""

    def test_fetch_public_key_success_and_caching(self):
        provider = HttpPublicKeyProvider(auth_service_url="http://auth-service:8001")
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "public_key": "-----BEGIN PUBLIC KEY-----\nKEY\n-----END PUBLIC KEY-----"
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            key1 = provider.get_public_key()
            assert "-----BEGIN PUBLIC KEY-----" in key1
            assert mock_urlopen.call_count == 1

            # Second call should use in-memory cache
            key2 = provider.get_public_key()
            assert key2 == key1
            assert mock_urlopen.call_count == 1

    def test_fetch_public_key_network_error_raises_auth_error(self):
        provider = HttpPublicKeyProvider(auth_service_url="http://invalid-host:8001")
        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            with pytest.raises(AuthenticationError) as exc_info:
                provider.get_public_key()
            assert "Erro de comunicação com o serviço de autenticação" in str(exc_info.value) or "Erro inesperado" in str(exc_info.value)
