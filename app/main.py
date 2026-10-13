"""FastAPI application for DRIMS."""

import json
import socket
from urllib.request import urlopen

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import settings
from app.core.db import engine
from sqlalchemy import text

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description="Drone-Based Inventory Management System",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthReadyResponse(BaseModel):
    status: str
    checks: dict[str, str]


@app.get("/")
async def root():
    return {"message": "DRIMS API is running", "version": settings.app_version}

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "type": "https://drims.local/problems/internal-error",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "The request could not be completed.",
            "instance": str(request.url),
        },
        media_type="application/problem+json",
    )


@app.get("/health/live")
async def health_live():
    return {"status": "ok"}


def _check_dependencies() -> dict[str, str]:
    checks: dict[str, str] = {}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {type(exc).__name__}"

    try:
        with socket.create_connection(
            (settings.redis_host, settings.redis_port),
            timeout=settings.readiness_timeout_seconds,
        ):
            pass
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {type(exc).__name__}"

    try:
        scheme = "https" if settings.minio_secure else "http"
        with urlopen(
            f"{scheme}://{settings.minio_endpoint}/minio/health/live",
            timeout=settings.readiness_timeout_seconds,
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"MinIO returned HTTP {response.status}")
        checks["minio"] = "ok"
    except Exception as exc:
        checks["minio"] = f"error: {type(exc).__name__}"

    try:
        url = (
            f"{settings.keycloak_server_url.rstrip('/')}/realms/"
            f"{settings.keycloak_realm}/protocol/openid-connect/certs"
        )
        with urlopen(url, timeout=settings.readiness_timeout_seconds) as response:
            json.load(response)
        checks["keycloak"] = "ok"
    except Exception as exc:
        checks["keycloak"] = f"error: {type(exc).__name__}"
    return checks


@app.get("/health/ready", response_model=HealthReadyResponse)
async def health_ready():
    checks = _check_dependencies()
    ready = all(value == "ok" for value in checks.values())
    status_code = 200 if ready else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if ready else "not_ready", "checks": checks},
    )


# Include API v1 router
from app.api.v1 import router as v1_router
app.include_router(v1_router, prefix="/api/v1", tags=["v1"])

# Import models to ensure tables are created
from app import models  # noqa: F401 (registers SQLAlchemy models)
