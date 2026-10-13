from fastapi.testclient import TestClient

from app import auth
from app.auth import Principal
from app.main import app


client = TestClient(app)


def _principal(role: str, sites: tuple[str, ...] = ("WH01",)) -> Principal:
    return Principal(
        subject="test-subject",
        username="test-user",
        roles=frozenset({role}),
        site_ids=frozenset(sites),
    )


def test_inventory_requires_bearer_token():
    response = client.get("/api/v1/inventory-map")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_inventory_allows_each_configured_role(monkeypatch):
    for role in auth.ROLE_NAMES:
        app.dependency_overrides[auth.get_principal] = lambda role=role: _principal(role)
        response = client.get("/api/v1/inventory-map")
        assert response.status_code == 200, role
    app.dependency_overrides.clear()


def test_inventory_rejects_wrong_site_scope():
    app.dependency_overrides[auth.get_principal] = lambda: _principal("Viewer", ("OTHER",))
    response = client.get("/api/v1/inventory-map?site_id=WH01")
    app.dependency_overrides.clear()
    assert response.status_code == 403


def test_inventory_rejects_token_without_role():
    app.dependency_overrides[auth.get_principal] = lambda: Principal(
        subject="test-subject",
        username="test-user",
        roles=frozenset(),
        site_ids=frozenset({"WH01"}),
    )
    response = client.get("/api/v1/inventory-map")
    app.dependency_overrides.clear()
    assert response.status_code == 403
