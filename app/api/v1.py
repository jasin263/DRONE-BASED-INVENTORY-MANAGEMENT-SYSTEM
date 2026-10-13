"""Version 1 API routes."""

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.auth import Principal, require_roles, require_site_access


router = APIRouter()

DATASET_OUTPUTS = (
    Path(__file__).resolve().parents[2] / "Dataset" / "drone_inventory_outputs"
)
# DEMO-ONLY: this endpoint reads checked-in synthetic CSV output directly.
# Replace it with persisted pipeline results before production use.


def _read_csv(filename: str) -> list[dict[str, str]]:
    path = DATASET_OUTPUTS / filename
    if not path.is_file():
        raise FileNotFoundError(f"Dataset file is missing: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _as_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _as_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


@lru_cache(maxsize=1)
def _inventory_map() -> dict[str, Any]:
    locations = _read_csv("location.csv")
    counts = {
        row["location_id"]: row for row in _read_csv("bin_count.csv")
    }
    discrepancy_counts: dict[str, int] = {}
    for row in _read_csv("discrepancy_cases.csv"):
        location_id = row.get("location_id")
        if location_id:
            discrepancy_counts[location_id] = discrepancy_counts.get(location_id, 0) + 1

    bins: list[dict[str, Any]] = []
    for location in locations:
        location_id = location["location_id"]
        count = counts.get(location_id, {})
        discrepancy_count = discrepancy_counts.get(location_id, 0)
        status = "discrepancy" if discrepancy_count else str(
            count.get("status", "unscanned")
        ).lower()
        bins.append(
            {
                "location_id": location_id,
                "label": location.get("label_code"),
                "zone": location.get("zone"),
                "aisle": _as_int(location.get("aisle")),
                "rack": _as_int(location.get("rack")),
                "level": _as_int(location.get("level")),
                "bin": _as_int(location.get("bin")),
                "x": _as_float(location.get("x_c")),
                "y": _as_float(location.get("y_c")),
                "z": _as_float(location.get("z_c")),
                "expected_qty": _as_int(location.get("expected_qty")),
                "items": _as_int(count.get("items")),
                "confidence": _as_float(count.get("conf")),
                "coverage": _as_float(count.get("coverage")),
                "status": status,
                "discrepancies": discrepancy_count,
            }
        )

    mission_ids = {
        row.get("mission_id")
        for row in _read_csv("mission_plan.csv")
        if row.get("mission_id")
    }
    scanned = sum(1 for item in bins if item["status"] != "unscanned")
    open_discrepancies = sum(discrepancy_counts.values())
    return {
        "mission_id": sorted(mission_ids)[-1] if mission_ids else None,
        "site_id": locations[0].get("site_id") if locations else None,
        "bins": bins,
        "summary": {
            "total_bins": len(bins),
            "scanned_bins": scanned,
            "items_seen": sum(item["items"] or 0 for item in bins),
            "open_discrepancies": open_discrepancies,
            "coverage": (
                sum(item["coverage"] or 0 for item in bins) / scanned
                if scanned
                else 0
            ),
        },
    }


@router.get("/status")
async def status() -> dict[str, str]:
    """Return API availability without requiring a database connection."""
    return {"status": "ok", "version": "v1"}


@router.get("/inventory-map")
async def inventory_map(
    principal: Principal = Depends(
        require_roles(
            "Admin",
            "Inventory Controller",
            "Warehouse Supervisor",
            "Viewer",
            "System Integration",
        )
    ),
    _site_principal: Principal = Depends(require_site_access),
) -> dict[str, Any]:
    """Return the dataset warehouse layout and inventory status by bin."""
    try:
        return _inventory_map()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
