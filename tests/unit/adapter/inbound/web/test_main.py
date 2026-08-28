import pytest
from fastapi.testclient import TestClient
from src.adapter.inbound.web.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_static_files_directory_created(mocker):
    # Simply test that the static route exists in the app's routes
    routes = [route.path for route in app.routes]
    assert "/health" in routes
    # Static files mount doesn't always show up exactly as "/static" in routes in the same way,
    # but let's check for its name
    route_names = [getattr(route, "name", None) for route in app.routes]
    assert "static" in route_names
