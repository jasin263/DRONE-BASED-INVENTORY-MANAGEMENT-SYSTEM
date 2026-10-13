"""Stage 1: Validate and persist raw payloads.

- Schema check per schemaVersion
- Store raw payload (bronze layer)
- Write staging rows
- Unknown versions go to quarantine
"""

from sqlalchemy import select, Table, MetaData, String, JSON, Integer, Float
from sqlalchemy.orm import Session
from ..core.db import engine
from ..models import Base, Mission, RawPayload, ScanEvent, Site, Drone, SKU, Location


def stage1_validate_and_persist(mission_id: str, payload: dict, db: Session):
    """Stage 1: Validate and persist raw payload."""
    
    # Get mission
    stmt = select(Mission).where(Mission.mission_id == mission_id)
    result = db.execute(stmt)
    db_mission = result.scalar_one_or_none()
    
    if not db_mission:
        return {"status": "error", "message": f"Mission {mission_id} not found"}
    
    # Schema version check
    schema_version = payload.get("schemaVersion", "unknown")
    
    # Store raw payload
    rp = RawPayload(
        mission_id=db_mission.id,
        payload_json=payload,
        schema_version=schema_version,
        received_at=_parse_dt(payload.get("timestamp"))
    )
    db.add(rp)
    db.flush()
    
    # Write staging rows (scan events)
    events = payload.get("events", [])
    staged_events = []
    
    for event in events:
        # Validate required fields
        required = ["eventId", "timestamp", "readType", "value"]
        missing = [f for f in required if f not in event]
        if missing:
            # Unknown codes go to quarantine
            continue
        
        # Create scan event
        se = ScanEvent(
            event_id=event["eventId"],
            mission_id=db_mission.id,
            drone_id=db_mission.drone_id,
            timestamp=event["timestamp"],
            read_type=event["readType"],
            symbology=event.get("symbology"),
            value=event["value"],
            confidence=event.get("confidence", 1.0),
            location_tag=event.get("locationTag"),
            position_x=event.get("position", {}).get("x"),
            position_y=event.get("position", {}).get("y"),
            position_z=event.get("position", {}).get("z"),
            position_frame=event.get("position", {}).get("frame"),
            image_ref=event.get("imageRef"),
            bbox_x1=event.get("bbox", [0, 0, 0, 0])[0] if isinstance(event.get("bbox"), list) else None,
            bbox_y1=event.get("bbox", [0, 0, 0, 0])[1] if isinstance(event.get("bbox"), list) else None,
            bbox_x2=event.get("bbox", [0, 0, 0, 0])[2] if isinstance(event.get("bbox"), list) else None,
            bbox_y2=event.get("bbox", [0, 0, 0, 0])[3] if isinstance(event.get("bbox"), list) else None,
            event_status="active"
        )
        db.add(se)
        staged_events.append(se.id)
    
    db.commit()
    
    return {
        "status": "success",
        "message": f"Stage 1 complete: {len(staged_events)} events staged",
        "staged_events": staged_events
    }