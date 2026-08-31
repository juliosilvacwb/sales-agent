"""Unit tests for Authentication domain models, exceptions, and services."""
import time
import pytest
from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock

from src.domain.exception.auth_exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    InvalidTokenError,
    ExpiredTokenError,
    MissingTokenError,
)
from src.domain.model.auth_models import (
    TokenClaims,
    AuthCredentials,
    TokenResponse,
)
from src.domain.service.credential_validator import CredentialValidator
from src.application.service.authentication_service import AuthenticationApplicationService
from src.application.port.outbound.token_port import TokenSignerPort, TokenVerifierPort
from src.application.port.outbound.public_key_provider_port import PublicKeyProviderPort
from src.application.port.inbound.authenticate_user_use_case import AuthenticateUserUseCase


class TestAuthExceptions:
    """Test suite for authentication exception hierarchy."""

    def test_exception_inheritance(self):
        assert issubclass(InvalidCredentialsError, AuthenticationError)
        assert issubclass(InvalidTokenError, AuthenticationError)
        assert issubclass(ExpiredTokenError, InvalidTokenError)
        assert issubclass(ExpiredTokenError, AuthenticationError)
        assert issubclass(MissingTokenError, AuthenticationError)

    def test_invalid_credentials_error_message(self):
        err = InvalidCredentialsError("Credenciais inválidas")
        assert "Credenciais inválidas" in str(err)

    def test_invalid_token_error_attributes(self):
        err = InvalidTokenError(reason="Signature verification failed")
        assert err.reason == "Signature verification failed"
        assert "Signature verification failed" in str(err)

    def test_expired_token_error(self):
        err = ExpiredTokenError()
        assert "Token expirado" in str(err)
        assert err.reason == "Token expirado"

    def test_missing_token_error(self):
        err = MissingTokenError(reason="Header absent")
        assert err.reason == "Header absent"
        assert "Header absent" in str(err)


class TestAuthModels:
    """Test suite for domain value objects and immutability."""

    def test_token_claims_creation_and_expiration(self):
        now = int(time.time())
        claims_valid = TokenClaims(
            sub="test_user",
            iss="sales-auth-service",
            iat=now - 10,
            exp=now + 3600,
            roles=("user", "admin"),
        )
        assert claims_valid.sub == "test_user"
        assert claims_valid.iss == "sales-auth-service"
        assert claims_valid.roles == ("user", "admin")
        assert claims_valid.is_expired is False

        claims_expired = TokenClaims(
            sub="test_user",
            iss="sales-auth-service",
            iat=now - 3700,
            exp=now - 100,
            roles=("user",),
        )
        assert claims_expired.is_expired is True

    def test_token_claims_immutability(self):
        now = int(time.time())
        claims = TokenClaims(
            sub="user",
            iss="iss",
            iat=now,
            exp=now + 100,
        )
        with pytest.raises(FrozenInstanceError):
            claims.sub = "other"  # type: ignore

    def test_auth_credentials_creation_and_immutability(self):
        creds = AuthCredentials(username="admin", password="password123")
        assert creds.username == "admin"
        assert creds.password == "password123"

        with pytest.raises(FrozenInstanceError):
            creds.username = "new_user"  # type: ignore

    def test_token_response_defaults(self):
        resp = TokenResponse(access_token="sample.jwt.token")
        assert resp.access_token == "sample.jwt.token"
        assert resp.token_type == "Bearer"
        assert resp.expires_in == 3600

        with pytest.raises(FrozenInstanceError):
            resp.expires_in = 7200  # type: ignore


class TestCredentialValidator:
    """Test suite for timing-safe CredentialValidator."""

    def setup_method(self):
        self.validator = CredentialValidator()

    def test_valid_credentials_returns_true(self):
        creds = AuthCredentials(username="admin", password="securepassword")
        result = self.validator.validate(
            credentials=creds,
            expected_username="admin",
            expected_password="securepassword",
        )
        assert result is True

    def test_invalid_username_raises_exception(self):
        creds = AuthCredentials(username="wrong_user", password="securepassword")
        with pytest.raises(InvalidCredentialsError) as exc_info:
            self.validator.validate(
                credentials=creds,
                expected_username="admin",
                expected_password="securepassword",
            )
        assert "Credenciais inválidas" in str(exc_info.value)

    def test_invalid_password_raises_exception(self):
        creds = AuthCredentials(username="admin", password="wrongpassword")
        with pytest.raises(InvalidCredentialsError) as exc_info:
            self.validator.validate(
                credentials=creds,
                expected_username="admin",
                expected_password="securepassword",
            )
        assert "Credenciais inválidas" in str(exc_info.value)


class TestAuthenticationApplicationService:
    """Test suite for AuthenticationApplicationService."""

    def test_authenticate_success(self):
        validator = CredentialValidator()
        mock_signer = MagicMock(spec=TokenSignerPort)
        mock_signer.sign.return_value = TokenResponse(
            access_token="signed.mock.jwt",
            token_type="Bearer",
            expires_in=3600,
        )

        service = AuthenticationApplicationService(
            validator=validator,
            token_signer=mock_signer,
            expected_username="admin",
            expected_password="changeme",
            token_expiration_minutes=60,
            issuer="sales-auth-service",
        )

        creds = AuthCredentials(username="admin", password="changeme")
        response = service.authenticate(creds)

        assert response.access_token == "signed.mock.jwt"
        assert response.token_type == "Bearer"
        assert response.expires_in == 3600
        mock_signer.sign.assert_called_once()
        signed_claims = mock_signer.sign.call_args[0][0]
        assert signed_claims.sub == "admin"
        assert signed_claims.iss == "sales-auth-service"

    def test_authenticate_failure_invalid_credentials(self):
        validator = CredentialValidator()
        mock_signer = MagicMock(spec=TokenSignerPort)

        service = AuthenticationApplicationService(
            validator=validator,
            token_signer=mock_signer,
            expected_username="admin",
            expected_password="changeme",
        )

        creds = AuthCredentials(username="admin", password="wrong_password")
        with pytest.raises(InvalidCredentialsError):
            service.authenticate(creds)

        mock_signer.sign.assert_not_called()


class TestAbstractPorts:
    """Verify that port interfaces are truly abstract."""

    def test_token_signer_port_is_abstract(self):
        with pytest.raises(TypeError):
            TokenSignerPort()  # type: ignore

    def test_token_verifier_port_is_abstract(self):
        with pytest.raises(TypeError):
            TokenVerifierPort()  # type: ignore

    def test_public_key_provider_port_is_abstract(self):
        with pytest.raises(TypeError):
            PublicKeyProviderPort()  # type: ignore

    def test_authenticate_user_use_case_is_abstract(self):
        with pytest.raises(TypeError):
            AuthenticateUserUseCase()  # type: ignore
