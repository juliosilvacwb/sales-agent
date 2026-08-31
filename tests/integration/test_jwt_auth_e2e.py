"""End-to-end integration tests for Auth Microservice and Sales Agent JWT security."""
import time
import pytest
from fastapi.testclient import TestClient

from auth_service.app import app as auth_app, public_pem, private_pem
from src.adapter.inbound.web.main import app as web_app
from src.adapter.inbound.web.jwt_security_guard import set_public_key_provider, set_token_verifier
from src.application.port.outbound.public_key_provider_port import PublicKeyProviderPort
from src.application.port.inbound.web_chat_use_case import WebChatUseCase
from src.application.dto.chat_dto import ChatResponseDTO
from src.adapter.inbound.web.chat_controller import get_web_chat_use_case_singleton
from src.adapter.outbound.auth.jwt_token_adapter import JwtRs256TokenAdapter
from src.domain.model.auth_models import TokenClaims


class LocalMockPublicKeyProvider(PublicKeyProviderPort):
    """Provides public key directly in test environment without live network port."""

    def __init__(self, key_pem: str) -> None:
        self._key_pem = key_pem

    def get_public_key(self) -> str:
        return self._key_pem


class MockWebChatUseCase(WebChatUseCase):
    """Mock use case returning a deterministic response for chat integration tests."""

    def process_chat_message(self, request):
        return ChatResponseDTO(
            session_id=request.session_id,
            response="Analytical answer: Total sales is R$ 1.000.000,00",
            data_queried=True,
            tool_calls=[],
        )


@pytest.fixture
def auth_client():
    """Test client for standalone Auth Microservice."""
    return TestClient(auth_app)


@pytest.fixture
def sales_client(monkeypatch):
    """Test client for Sales Agent web application with auth guard wired."""
    monkeypatch.setenv("AUTH_ENABLED", "true")
    provider = LocalMockPublicKeyProvider(public_pem)
    set_public_key_provider(provider)
    set_token_verifier(JwtRs256TokenAdapter())

    # Override web chat use case to isolate auth testing from LLM/agent bootstrap
    web_app.dependency_overrides[get_web_chat_use_case_singleton] = lambda: MockWebChatUseCase()
    client = TestClient(web_app)
    yield client
    web_app.dependency_overrides.clear()
    set_public_key_provider(None)  # type: ignore
    set_token_verifier(None)  # type: ignore


class TestAuthMicroserviceEndToEnd:
    """Test suite for Auth Microservice REST contract."""

    def test_health_endpoint(self, auth_client):
        response = auth_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_public_key_endpoint_returns_pem(self, auth_client):
        response = auth_client.get("/auth/public-key")
        assert response.status_code == 200
        data = response.json()
        assert "public_key" in data
        assert "-----BEGIN PUBLIC KEY-----" in data["public_key"]

    def test_login_success(self, auth_client):
        response = auth_client.post(
            "/auth/login",
            json={"username": "admin", "password": "changeme"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] > 0

    def test_login_failure_invalid_credentials_returns_401_sanitized(self, auth_client):
        response = auth_client.post(
            "/auth/login",
            json={"username": "admin", "password": "wrong_password"},
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "Credenciais inválidas"}


class TestSalesAgentProtectedEndpointEndToEnd:
    """Test suite for Sales Agent authentication security guard integration."""

    def test_public_health_endpoint_is_accessible_without_token(self, sales_client):
        response = sales_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_chat_without_token_returns_401(self, sales_client):
        response = sales_client.post(
            "/chat",
            json={"session_id": "sess-123", "message": "Qual o faturamento?"},
        )
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

    def test_chat_with_valid_token_returns_200(self, auth_client, sales_client):
        # 1. Obtain token from Auth Microservice
        auth_resp = auth_client.post(
            "/auth/login",
            json={"username": "admin", "password": "changeme"},
        )
        token = auth_resp.json()["access_token"]

        # 2. Access protected endpoint with Bearer token
        response = sales_client.post(
            "/chat",
            json={"session_id": "sess-123", "message": "Qual o faturamento?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "Total sales" in data["response"]
        assert data.get("status") == "success"

    def test_chat_with_expired_token_returns_401(self, sales_client):
        adapter = JwtRs256TokenAdapter(private_key_pem=private_pem)
        now = int(time.time())
        expired_claims = TokenClaims(
            sub="admin",
            iss="sales-auth-service",
            iat=now - 7200,
            exp=now - 3600,
        )
        token_resp = adapter.sign(expired_claims)

        response = sales_client.post(
            "/chat",
            json={"session_id": "sess-123", "message": "Qual o faturamento?"},
            headers={"Authorization": f"Bearer {token_resp.access_token}"},
        )
        assert response.status_code == 401
        assert "Token inválido ou expirado" in response.json()["detail"]

    def test_chat_with_tampered_token_returns_401(self, auth_client, sales_client):
        auth_resp = auth_client.post(
            "/auth/login",
            json={"username": "admin", "password": "changeme"},
        )
        token = auth_resp.json()["access_token"]
        parts = token.split(".")
        tampered_token = f"{parts[0]}.eyJzdWIiOiAiaGFja2VyIn0.{parts[2]}"

        response = sales_client.post(
            "/chat",
            json={"session_id": "sess-123", "message": "Qual o faturamento?"},
            headers={"Authorization": f"Bearer {tampered_token}"},
        )
        assert response.status_code == 401
