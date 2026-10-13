from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.db import engine
from app.main import app


def test_product_name_is_drims():
    assert settings.app_title.startswith("DRIMS")


def test_version_is_set():
    assert settings.app_version


def test_confidence_weights_sum_to_one():
    assert settings.w1_default + settings.w2_default + settings.w3_default == 1.0


def test_confidence_threshold_is_bounded():
    assert 0 < settings.bin_count_confidence_threshold <= 1


def test_retention_policies_are_positive():
    assert settings.scan_data_retention_days > settings.image_retention_hot_days > 0


def test_database_uses_psycopg_v3():
    assert engine.url.drivername == "postgresql+psycopg"


def test_live_health_is_process_only():
    response = TestClient(app).get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_identifies_api():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert response.json()["message"].startswith("DRIMS")


def test_status_endpoint_is_versioned():
    response = TestClient(app).get("/api/v1/status")
    assert response.status_code == 200
    assert response.json()["version"] == "v1"


def test_openapi_is_available():
    schema = TestClient(app).get("/openapi.json").json()
    assert schema["info"]["title"].startswith("DRIMS")


def test_versioned_router_is_registered():
    paths = TestClient(app).get("/openapi.json").json()["paths"]
    assert "/api/v1/status" in paths


def test_database_pool_is_configured():
    assert engine.pool.size() >= 1


def test_cors_has_frontend_origin():
    assert any("localhost:3000" in origin for origin in settings.cors_origins)


def test_keycloak_realm_is_configured():
    assert settings.keycloak_realm == "drims"


def test_minio_endpoint_is_configured():
    assert settings.minio_endpoint


def test_redis_endpoint_is_configured():
    assert settings.redis_host and settings.redis_port == 6379


def test_api_exposes_ready_route():
    routes = TestClient(app).get("/openapi.json").json()["paths"]
    assert "/health/ready" in routes


def test_api_exposes_inventory_map_route():
    routes = TestClient(app).get("/openapi.json").json()["paths"]
    assert "/api/v1/inventory-map" in routes


def test_problem_json_handler_is_registered():
    assert Exception in app.exception_handlers
