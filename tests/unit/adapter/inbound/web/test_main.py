import pytest
from fastapi.testclient import TestClient
from src.adapter.inbound.web.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_redirect():
    """Verify that the root endpoint redirects to the static web interface."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_http_security_headers_present():
    """Verify HTTP security headers (nosniff, DENY, referrer-policy) are injected on responses."""
    response = client.get("/health")
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_static_files_and_cors_mount_configuration():
    """Verify static files mount configuration and hardened CORS options header handling."""
    # Check static route registration
    route_names = [getattr(route, "name", None) for route in app.routes]
    assert "static" in route_names

    # Check CORS preflight response for allowed origin
    response = client.options(
        "/chat",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    # Check CORS preflight response for disallowed origin
    disallowed_response = client.options(
        "/chat",
        headers={
            "Origin": "http://evil-attacker.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert disallowed_response.headers.get("access-control-allow-origin") != "http://evil-attacker.com"


def test_openapi_schema_endpoint():
    """Verify OpenAPI schema generation and documented endpoints."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Sales Data Analysis API"
    assert "/chat" in schema["paths"]
    assert "post" in schema["paths"]["/chat"]
