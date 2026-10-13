from fastapi.testclient import TestClient

from app import auth
from app.api.v1 import PERMISSIONS
from app.auth import Principal
from app.main import app


client = TestClient(app)


def _principal(role: str) -> Principal:
    return Principal(
        subject="matrix-subject",
        username="matrix-user",
        roles=frozenset({role}),
        site_ids=frozenset({"WH01"}),
    )


def test_permission_map_has_every_required_operation() -> None:
    expected = {
        "GET /me", "GET /sites", "GET /missions", "GET /missions/{mission_id}",
        "POST /missions/{mission_id}/reprocess", "GET /discrepancies",
        "PATCH /discrepancies/{case_id}", "POST /discrepancies/{case_id}/approve",
        "POST /discrepancies/{case_id}/comments", "GET /settings", "PUT /settings",
        "GET /users", "POST /users", "PATCH /users/{user_id}",
        "DELETE /users/{user_id}", "GET /audit-log", "GET /notifications",
    }
    assert expected <= PERMISSIONS.keys()
    assert all(PERMISSIONS[key] for key in expected)


def test_me_permission_all_roles_and_missing_token() -> None:
    for role in auth.ROLE_NAMES:
        app.dependency_overrides[auth.get_principal] = lambda role=role: _principal(role)
        assert client.get("/api/v1/me").status_code == 200
    app.dependency_overrides.clear()
    assert client.get("/api/v1/me").status_code == 401


def test_admin_only_route_denies_viewer_before_database_access() -> None:
    app.dependency_overrides[auth.get_principal] = lambda: _principal("Viewer")
    response = client.get("/api/v1/users")
    app.dependency_overrides.clear()
    assert response.status_code == 403
    assert response.headers["content-type"].startswith("application/problem+json")
