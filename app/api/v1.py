"""Version 1 API routes and the single RBAC permission map."""

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import Principal, get_principal
from app.deps import get_db_session
from app.models import (
    AppUser,
    AuditLog,
    CaseComment,
    DiscrepancyCase,
    Location,
    Mission,
    Setting,
    Site,
)


router = APIRouter()

PERMISSIONS: dict[str, frozenset[str]] = {
    "GET /me": frozenset({"Admin", "Inventory Controller", "Warehouse Supervisor", "Viewer", "System Integration"}),
    "GET /sites": frozenset({"Admin", "Inventory Controller", "Warehouse Supervisor", "Viewer", "System Integration"}),
    "GET /missions": frozenset({"Admin", "Inventory Controller", "Warehouse Supervisor", "Viewer", "System Integration"}),
    "GET /missions/{mission_id}": frozenset({"Admin", "Inventory Controller", "Warehouse Supervisor", "Viewer", "System Integration"}),
    "POST /missions/{mission_id}/reprocess": frozenset({"Admin", "Inventory Controller", "System Integration"}),
    "GET /discrepancies": frozenset({"Admin", "Inventory Controller", "Warehouse Supervisor", "Viewer", "System Integration"}),
    "PATCH /discrepancies/{case_id}": frozenset({"Admin", "Inventory Controller", "Warehouse Supervisor"}),
    "POST /discrepancies/{case_id}/approve": frozenset({"Admin", "Warehouse Supervisor"}),
    "POST /discrepancies/{case_id}/comments": frozenset({"Admin", "Inventory Controller", "Warehouse Supervisor"}),
    "GET /settings": frozenset({"Admin", "Inventory Controller", "Warehouse Supervisor", "Viewer", "System Integration"}),
    "PUT /settings": frozenset({"Admin", "Inventory Controller"}),
    "GET /users": frozenset({"Admin"}),
    "POST /users": frozenset({"Admin"}),
    "PATCH /users/{user_id}": frozenset({"Admin"}),
    "DELETE /users/{user_id}": frozenset({"Admin"}),
    "GET /audit-log": frozenset({"Admin", "Viewer"}),
    "GET /notifications": frozenset({"Admin", "Inventory Controller", "Warehouse Supervisor", "Viewer", "System Integration"}),
}

DATASET_OUTPUTS = Path(__file__).resolve().parents[2] / "Dataset" / "drone_inventory_outputs"


def require_permission(operation: str):
    allowed = PERMISSIONS[operation]

    def dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if not principal.roles.intersection(allowed):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return principal

    return dependency


def _site_ids(principal: Principal) -> set[str] | None:
    return None if "Admin" in principal.roles else set(principal.site_ids)


def _audit(
    db: Session,
    principal: Principal,
    action: str,
    table_name: str,
    record_id: int,
    old_values: Any = None,
    new_values: Any = None,
) -> None:
    user_id = _actor_id(db, principal)
    db.add(
        AuditLog(
            table_name=table_name,
            record_id=record_id,
            action=action,
            old_values=old_values,
            new_values=new_values,
            user_id=user_id,
        )
    )


def _actor_id(db: Session, principal: Principal) -> int | None:
    if not principal.username:
        return None
    user_id = db.query(AppUser.id).filter(AppUser.username == principal.username).scalar()
    if user_id is not None:
        return user_id
    actor = AppUser(
        username=principal.username,
        password_hash="managed-by-keycloak",
        role=next(iter(principal.roles), "Viewer"),
    )
    db.add(actor)
    db.flush()
    return actor.id


def _mission_dict(mission: Mission) -> dict[str, Any]:
    return {
        "id": mission.id,
        "mission_id": mission.mission_id,
        "site_id": mission.site_id,
        "status": mission.status,
        "coverage_pct": mission.coverage_pct,
        "total_scans": mission.total_scans,
        "total_bins_visited": mission.total_bins_visited,
    }


@router.get("/status")
async def status_route() -> dict[str, str]:
    return {"status": "ok", "version": "v1"}


@router.get("/me")
def me(principal: Principal = Depends(require_permission("GET /me"))) -> dict[str, Any]:
    return {
        "subject": principal.subject,
        "username": principal.username,
        "roles": sorted(principal.roles),
        "site_ids": sorted(principal.site_ids),
    }


@router.get("/sites")
def sites(
    principal: Principal = Depends(require_permission("GET /sites")),
    db: Session = Depends(get_db_session),
) -> list[dict[str, Any]]:
    query = db.query(Site)
    site_ids = _site_ids(principal)
    if site_ids is not None:
        query = query.filter(Site.code.in_(site_ids))
    return [{"id": site.id, "code": site.code, "name": site.name} for site in query.all()]


@router.get("/missions")
def missions(
    principal: Principal = Depends(require_permission("GET /missions")),
    db: Session = Depends(get_db_session),
) -> list[dict[str, Any]]:
    query = db.query(Mission).join(Site)
    site_ids = _site_ids(principal)
    if site_ids is not None:
        query = query.filter(Site.code.in_(site_ids))
    return [_mission_dict(item) for item in query.order_by(Mission.created_at.desc()).all()]


@router.get("/missions/{mission_id}")
def mission_detail(
    mission_id: str,
    principal: Principal = Depends(require_permission("GET /missions/{mission_id}")),
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    item = db.query(Mission).join(Site).filter(Mission.mission_id == mission_id).first()
    if not item or (_site_ids(principal) is not None and item.site.code not in principal.site_ids):
        raise HTTPException(status_code=404, detail="Mission not found")
    return _mission_dict(item)


@router.post("/missions/{mission_id}/reprocess", status_code=202)
def reprocess_mission(
    mission_id: str,
    principal: Principal = Depends(require_permission("POST /missions/{mission_id}/reprocess")),
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    item = db.query(Mission).filter(Mission.mission_id == mission_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Mission not found")
    old = {"status": item.status}
    item.status = "PROCESSING"
    _audit(db, principal, "UPDATE", "mission", item.id, old, {"status": item.status})
    db.commit()
    return {"mission_id": mission_id, "status": "PROCESSING", "queued": True}


@router.get("/discrepancies")
def discrepancies(
    principal: Principal = Depends(require_permission("GET /discrepancies")),
    db: Session = Depends(get_db_session),
) -> list[dict[str, Any]]:
    query = db.query(DiscrepancyCase).join(Mission).join(Site)
    site_ids = _site_ids(principal)
    if site_ids is not None:
        query = query.filter(Site.code.in_(site_ids))
    return [
        {"id": item.id, "mission_id": item.mission_id, "location_id": item.location_id,
         "outcome": item.outcome, "status": item.status, "variance_value": item.variance_value}
        for item in query.order_by(DiscrepancyCase.created_at.desc()).all()
    ]


@router.patch("/discrepancies/{case_id}")
def update_discrepancy(
    case_id: int,
    payload: dict[str, Any],
    principal: Principal = Depends(require_permission("PATCH /discrepancies/{case_id}")),
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    item = db.get(DiscrepancyCase, case_id)
    if not item:
        raise HTTPException(status_code=404, detail="Discrepancy not found")
    old = {"status": item.status, "assigned_to": item.assigned_to}
    for field in ("status", "assigned_to"):
        if field in payload:
            setattr(item, field, payload[field])
    new = {"status": item.status, "assigned_to": item.assigned_to}
    _audit(db, principal, "UPDATE", "discrepancy_case", item.id, old, new)
    db.commit()
    return {"id": item.id, **new}


@router.post("/discrepancies/{case_id}/approve")
def approve_discrepancy(
    case_id: int,
    principal: Principal = Depends(require_permission("POST /discrepancies/{case_id}/approve")),
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    item = db.get(DiscrepancyCase, case_id)
    if not item:
        raise HTTPException(status_code=404, detail="Discrepancy not found")
    old = {"status": item.status}
    item.status = "approved"
    _audit(db, principal, "UPDATE", "discrepancy_case", item.id, old, {"status": item.status})
    db.commit()
    return {"id": item.id, "status": item.status}


@router.post("/discrepancies/{case_id}/comments", status_code=201)
def comment_discrepancy(
    case_id: int,
    payload: dict[str, Any],
    principal: Principal = Depends(require_permission("POST /discrepancies/{case_id}/comments")),
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    if not db.get(DiscrepancyCase, case_id):
        raise HTTPException(status_code=404, detail="Discrepancy not found")
    comment = CaseComment(
        case_id=case_id,
        user_id=_actor_id(db, principal),
        comment=str(payload.get("comment", "")),
    )
    db.add(comment)
    db.flush()
    _audit(db, principal, "INSERT", "case_comment", comment.id, None, {"comment": comment.comment})
    db.commit()
    return {"id": comment.id, "comment": comment.comment}


@router.get("/settings")
def settings(
    principal: Principal = Depends(require_permission("GET /settings")),
    db: Session = Depends(get_db_session),
) -> list[dict[str, Any]]:
    return [{"key": item.key, "value": item.value, "description": item.description} for item in db.query(Setting).all()]


@router.put("/settings")
def update_settings(
    payload: dict[str, Any],
    principal: Principal = Depends(require_permission("PUT /settings")),
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    key = str(payload.get("key", ""))
    if not key:
        raise HTTPException(status_code=422, detail="key is required")
    item = db.query(Setting).filter(Setting.key == key).first()
    old = item.value if item else None
    if item is None:
        item = Setting(key=key, value=payload.get("value"), description=payload.get("description"))
        db.add(item)
        db.flush()
        action = "INSERT"
    else:
        item.value = payload.get("value")
        item.description = payload.get("description", item.description)
        action = "UPDATE"
    _audit(db, principal, action, "setting", item.id, {"value": old}, {"value": item.value})
    db.commit()
    return {"key": item.key, "value": item.value}


@router.get("/users")
def users(
    principal: Principal = Depends(require_permission("GET /users")),
    db: Session = Depends(get_db_session),
) -> list[dict[str, Any]]:
    return [{"id": item.id, "username": item.username, "email": item.email, "role": item.role, "site_id": item.site_id}
            for item in db.query(AppUser).all()]


@router.post("/users", status_code=201)
def create_user(
    payload: dict[str, Any],
    principal: Principal = Depends(require_permission("POST /users")),
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    item = AppUser(
        username=str(payload["username"]),
        email=payload.get("email"),
        password_hash="managed-by-keycloak",
        role=payload.get("role", "Viewer"),
        site_id=payload.get("site_id"),
    )
    db.add(item)
    db.flush()
    _audit(db, principal, "INSERT", "app_user", item.id, None, {"username": item.username, "role": item.role})
    db.commit()
    return {"id": item.id, "username": item.username}


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    payload: dict[str, Any],
    principal: Principal = Depends(require_permission("PATCH /users/{user_id}")),
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    item = db.get(AppUser, user_id)
    if not item:
        raise HTTPException(status_code=404, detail="User not found")
    old = {"role": item.role, "site_id": item.site_id, "is_active": item.is_active}
    for field in ("role", "site_id", "is_active"):
        if field in payload:
            setattr(item, field, payload[field])
    new = {"role": item.role, "site_id": item.site_id, "is_active": item.is_active}
    _audit(db, principal, "UPDATE", "app_user", item.id, old, new)
    db.commit()
    return {"id": item.id, **new}


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    principal: Principal = Depends(require_permission("DELETE /users/{user_id}")),
    db: Session = Depends(get_db_session),
) -> None:
    item = db.get(AppUser, user_id)
    if not item:
        raise HTTPException(status_code=404, detail="User not found")
    _audit(db, principal, "DELETE", "app_user", item.id, {"username": item.username}, None)
    db.delete(item)
    db.commit()


@router.get("/audit-log")
def audit_log(
    principal: Principal = Depends(require_permission("GET /audit-log")),
    db: Session = Depends(get_db_session),
) -> list[dict[str, Any]]:
    return [{"id": item.id, "action": item.action, "table_name": item.table_name, "record_id": item.record_id,
             "created_at": item.created_at.isoformat() if item.created_at else None}
            for item in db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(500).all()]


@router.get("/notifications")
def notifications(
    principal: Principal = Depends(require_permission("GET /notifications")),
) -> list[dict[str, Any]]:
    return []


@router.get("/inventory-map")
def inventory_map(
    site_id: str | None = Query(default=None),
    principal: Principal = Depends(require_permission("GET /missions")),
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Production route: reads persisted locations and counts, never workspace CSVs."""
    if site_id and "Admin" not in principal.roles and site_id not in principal.site_ids:
        raise HTTPException(status_code=403, detail="The token is not scoped to this site")
    query = db.query(Location).join(Site)
    site_ids = _site_ids(principal)
    if site_id:
        query = query.filter(Site.code == site_id)
    elif site_ids is not None:
        query = query.filter(Site.code.in_(site_ids))
    return {"bins": [{"id": item.id, "bin_code": item.bin_code, "label_code": item.label_code, "site_id": item.site_id}
                     for item in query.all()], "source": "database"}


@router.get("/demo/inventory-map")
def demo_inventory_map(
    principal: Principal = Depends(require_permission("GET /missions")),
) -> dict[str, Any]:
    """DEMO-ONLY: read the unverified workspace CSV outputs."""
    try:
        locations = _read_csv("location.csv")
        counts = {row["location_id"]: row for row in _read_csv("bin_count.csv")}
        return {
            "source": "Dataset/drone_inventory_outputs",
            "bins": [{"location_id": row.get("location_id"), "label": row.get("label_code"),
                      "items": counts.get(row.get("location_id"), {}).get("items")}
                     for row in locations],
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _read_csv(filename: str) -> list[dict[str, str]]:
    path = DATASET_OUTPUTS / filename
    if not path.is_file():
        raise FileNotFoundError(f"Dataset file is missing: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))
