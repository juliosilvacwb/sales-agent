"""Unit tests for JwtRs256TokenAdapter and RsaKeyManager."""
import os
import time
import pytest
from src.domain.model.auth_models import TokenClaims
from src.domain.exception.auth_exceptions import (
    AuthenticationError,
    InvalidTokenError,
    ExpiredTokenError,
)
from src.adapter.outbound.auth.jwt_token_adapter import JwtRs256TokenAdapter
from src.adapter.outbound.auth.rsa_key_manager import RsaKeyManager


@pytest.fixture(scope="module")
def rsa_keys():
    """Fixture providing a fresh RSA-2048 key pair in PEM format."""
    return RsaKeyManager.generate_key_pair(key_size=2048)


class TestRsaKeyManager:
    """Test suite for RSA key generation and loading."""

    def test_generate_key_pair_structure(self, rsa_keys):
        private_pem, public_pem = rsa_keys
        assert "-----BEGIN PRIVATE KEY-----" in private_pem
        assert "-----END PRIVATE KEY-----" in private_pem
        assert "-----BEGIN PUBLIC KEY-----" in public_pem
        assert "-----END PUBLIC KEY-----" in public_pem

    def test_load_from_environment_variables(self, monkeypatch, rsa_keys):
        private_pem, public_pem = rsa_keys
        monkeypatch.setenv("RSA_PRIVATE_KEY_PEM", private_pem)
        monkeypatch.setenv("RSA_PUBLIC_KEY_PEM", public_pem)

        loaded_priv, loaded_pub = RsaKeyManager.load_or_generate()
        assert loaded_priv == private_pem
        assert loaded_pub == public_pem

    def test_load_or_generate_persists_to_filesystem(self, tmp_path):
        priv_path = str(tmp_path / "keys" / "private.pem")
        pub_path = str(tmp_path / "keys" / "public.pem")

        priv_pem, pub_pem = RsaKeyManager.load_or_generate(
            private_key_path=priv_path,
            public_key_path=pub_path,
        )

        assert os.path.exists(priv_path)
        assert os.path.exists(pub_path)

        # Second load should read existing files
        priv_loaded, pub_loaded = RsaKeyManager.load_or_generate(
            private_key_path=priv_path,
            public_key_path=pub_path,
        )
        assert priv_loaded == priv_pem
        assert pub_loaded == pub_pem


class TestJwtRs256TokenAdapter:
    """Test suite for RS256 token signing and verification adapter."""

    def test_sign_and_verify_roundtrip(self, rsa_keys):
        private_pem, public_pem = rsa_keys
        adapter = JwtRs256TokenAdapter(private_key_pem=private_pem)

        now = int(time.time())
        claims = TokenClaims(
            sub="test_analyst",
            iss="sales-auth-service",
            iat=now,
            exp=now + 3600,
            roles=("admin", "analyst"),
        )

        response = adapter.sign(claims)
        assert response.access_token is not None
        assert response.token_type == "Bearer"
        assert response.expires_in == 3600

        decoded = adapter.verify(response.access_token, public_pem)
        assert decoded.sub == claims.sub
        assert decoded.iss == claims.iss
        assert decoded.iat == claims.iat
        assert decoded.exp == claims.exp
        assert decoded.roles == ("admin", "analyst")

    def test_sign_without_private_key_raises_error(self):
        adapter = JwtRs256TokenAdapter(private_key_pem=None)
        now = int(time.time())
        claims = TokenClaims(
            sub="user",
            iss="iss",
            iat=now,
            exp=now + 3600,
        )
        with pytest.raises(AuthenticationError) as exc_info:
            adapter.sign(claims)
        assert "Chave privada RSA não configurada" in str(exc_info.value)

    def test_verify_expired_token_raises_expired_token_error(self, rsa_keys):
        private_pem, public_pem = rsa_keys
        adapter = JwtRs256TokenAdapter(private_key_pem=private_pem)

        now = int(time.time())
        expired_claims = TokenClaims(
            sub="expired_user",
            iss="sales-auth-service",
            iat=now - 7200,
            exp=now - 3600,
        )

        token_resp = adapter.sign(expired_claims)
        with pytest.raises(ExpiredTokenError):
            adapter.verify(token_resp.access_token, public_pem)

    def test_verify_tampered_token_raises_invalid_token_error(self, rsa_keys):
        private_pem, public_pem = rsa_keys
        adapter = JwtRs256TokenAdapter(private_key_pem=private_pem)

        now = int(time.time())
        claims = TokenClaims(
            sub="user",
            iss="sales-auth-service",
            iat=now,
            exp=now + 3600,
        )
        token_resp = adapter.sign(claims)

        # Tamper payload part of JWT
        parts = token_resp.access_token.split(".")
        tampered_token = f"{parts[0]}.eyJzdWIiOiAiaGFja2VyIn0.{parts[2]}"

        with pytest.raises(InvalidTokenError):
            adapter.verify(tampered_token, public_pem)

    def test_verify_token_signed_with_different_key(self, rsa_keys):
        private_pem1, public_pem1 = rsa_keys
        _priv2, public_pem2 = RsaKeyManager.generate_key_pair()

        adapter = JwtRs256TokenAdapter(private_key_pem=private_pem1)
        now = int(time.time())
        claims = TokenClaims(
            sub="user",
            iss="sales-auth-service",
            iat=now,
            exp=now + 3600,
        )
        token_resp = adapter.sign(claims)

        # Verify with different public key
        with pytest.raises(InvalidTokenError):
            adapter.verify(token_resp.access_token, public_pem2)
