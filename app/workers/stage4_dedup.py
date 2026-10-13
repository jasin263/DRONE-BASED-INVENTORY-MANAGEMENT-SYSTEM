"""Stage 4: Deduplication.

Collapse reads with the same item key (serial, or SKU+lot+bbox cluster) in the same bin within a mission;
keep highest confidence.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Mission, ScanEvent, ScanItem


def stage4_dedup(mission_id: str, db: Session):
    """Stage 4: Deduplication.
    
    Collapse reads with same item key (serial, or SKU+lot) in same bin within mission;
    keep highest confidence.
    """
    
    mission_row = db.execute(
        select(Mission).where(Mission.mission_id == mission_id)
    ).scalar_one_or_none()
    if mission_row is None:
        return {"status": "error", "message": f"Mission {mission_id} not found", "collapsed": 0}

    # Get all active scan items for this mission.
    stmt = select(ScanItem).join(
        ScanEvent, ScanItem.scan_event_id == ScanEvent.id
    ).where(
        ScanEvent.mission_id == mission_row.id,
        ScanEvent.event_status == "active"
    )
    result = db.execute(stmt)
    items = result.scalars().all()
    
    collapsed = 0
    groups = {}
    
    # A serial uniquely identifies an item; otherwise use SKU/lot/bin.
    for item in items:
        if item.serial:
            group_key = ("serial", item.serial, item.location_id)
        elif item.sku_id is not None and item.lot is not None and item.location_id is not None:
            group_key = ("sku_lot_bin", item.sku_id, item.lot, item.location_id)
        else:
            continue
        groups.setdefault(group_key, []).append(item)
    
    # Collapse each group - keep highest confidence
    for group_key, group_items in groups.items():
        if len(group_items) <= 1:
            continue
        
        # Sort by confidence descending, keep the highest
        group_items.sort(key=lambda x: x.confidence or 0.0, reverse=True)
        
        # Mark all others as duplicates
        for duplicate_item in group_items[1:]:
            duplicate_item.is_duplicate = True
            collapsed += 1
    
    db.commit()
    
    return {
        "status": "success",
        "message": f"Stage 4 complete: {collapsed} items marked as duplicate",
        "collapsed": collapsed
    }