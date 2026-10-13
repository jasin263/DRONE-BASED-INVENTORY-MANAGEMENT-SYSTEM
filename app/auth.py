"""Keycloak JWT validation and role/site authorization dependencies."""

import json
import time
from dataclasses import dataclass
from threading import Lock
from urllib.request import urlopen

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings


ROLE_NAMES = (
    "Admin",
    "Inventory Controller",
    "Warehouse Supervisor",
    "Viewer",
    "System Integration",
)


@dataclass(frozen=True)
class Principal:
    subject: str
    username: str | None
    roles: frozenset[str]
    site_ids: frozenset[str]


_bearer = HTTPBearer(auto_error=False)
_jwks_lock = Lock()
_jwks: dict[str, object] | None = None
_jwks_expiry = 0.0


def _jwks_url() -> str:
    return (
        f"{settings.keycloak_server_url.rstrip('/')}/realms/"
        f"{settings.keycloak_realm}/protocol/openid-connect/certs"
    )


def _get_jwks() -> dict[str, object]:
    global _jwks, _jwks_expiry
    now = time.monotonic()
    if _jwks is not None and now < _jwks_expiry:
        return _jwks
    with _jwks_lock:
        if _jwks is None or now >= _jwks_expiry:
            with urlopen(_jwks_url(), timeout=settings.readiness_timeout_seconds) as response:
                _jwks = json.load(response)
            _jwks_expiry = now + settings.jwks_cache_seconds
    return _jwks


def _unauthorized(detail: str = "Authentication required") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _decode_token(token: str) -> dict[str, object]:
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        key = next((key for key in _get_jwks().get("keys", []) if key.get("kid") == kid), None)
        if key is None:
            raise _unauthorized("Signing key is not available")
        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.keycloak_audience,
            issuer=(
                f"{settings.keycloak_server_url.rstrip('/')}/realms/"
                f"{settings.keycloak_realm}"
            ),
            options={"verify_exp": True, "verify_iat": True},
        )
    except HTTPException:
        raise
    except (JWTError, OSError, ValueError, KeyError, StopIteration) as exc:
        raise _unauthorized("Invalid access token") from exc


def _principal(payload: dict[str, object]) -> Principal:
    realm_access = payload.get("realm_access") or {}
    roles = frozenset(
        role for role in realm_access.get("roles", []) if role in ROLE_NAMES
    )
    if not roles:
        raise _forbidden("The token has no DRIMS role")
    raw_sites = payload.get("site_ids") or payload.get("sites") or []
    site_ids = frozenset(str(site) for site in raw_sites)
    return Principal(
        subject=str(payload["sub"]),
        username=payload.get("preferred_username"),
        roles=roles,
        site_ids=site_ids,
    )


def get_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    return _principal(_decode_token(credentials.credentials))


def require_roles(*allowed_roles: str):
    allowed = frozenset(allowed_roles)

    def dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if not principal.roles.intersection(allowed):
            raise _forbidden("Insufficient role")
        return principal

    return dependency


def require_site_access(
    site_id: str | None = Query(default=None),
    principal: Principal = Depends(get_principal),
) -> Principal:
    if site_id and "Admin" not in principal.roles and site_id not in principal.site_ids:
        raise _forbidden("The token is not scoped to this site")
    return principal
