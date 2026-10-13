"""Stage 6: Reconciliation.

Compare counted vs book snapshot per site, bin, SKU and lot.
Outcomes: Match, Shortage, Excess, Misplaced, Unknown item, Empty-bin mismatch, Not scanned.
"""

from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.orm import Session
from ..models import Mission, BinCount, BookSnapshot, ReconResult, DiscrepancyCase, CaseComment, UserRole, AppUser, Setting, mission, bin_count, book_snapshot, recon_result, discrepancy_case, case_comment, user_role, app_user, setting


def stage6_reconciliation(mission_id: str, db: Session):
    """Stage 6: Reconciliation.
    
    Compare counted vs book snapshot per site, bin, SKU and lot.
    Outcomes: Match, Shortage, Excess, Misplaced, Unknown item, Empty-bin mismatch, Not scanned.
    """
    
    # Get the book snapshot for this mission
    # Book snapshot taken at mission start - pre-computed counts
    stmt = select(book_snapshot.BookSnapshot).join(
        mission.Mission, book_snapshot.BookSnapshot.mission_id == mission.Mission.id
    ).where(mission.Mission.mission_id == mission_id)
    result = db.execute(stmt)
    book_snapshots = result.scalars().all()
    
    # Get the bin counts for this mission
    stmt = select(bin_count.BinCount).where(bin_count.BinCount.mission_id == mission_id)
    result = db.execute(stmt)
    bin_counts = result.scalars().all()
    
    reconciled = 0
    outcomes_count = {"Match": 0, "Shortage": 0, "Excess": 0, "Misplaced": 0, "Unknown_item": 0, "Empty_bin_mismatch": 0, "Not_scanned": 0}
    
    # Build a lookup of book snapshots
    book_lookup = {}
    for bs in book_snapshots:
        key = (bs.sku_id, bs.location_id, bs.lot) if bs.sku_id and bs.location_id else (None, None, None)
        book_lookup[key] = {
            "booked_count": bs.booked_count,
            "sku_id": bs.sku_id,
            "location_id": bs.location_id,
            "lot": bs.lot
        }
    
    # Build a lookup of bin counts
    count_lookup = {}
    for bc in bin_counts:
        key = (bc.sku_id, bc.location_id, bc.lot) if bc.sku_id and bc.location_id else (None, None, None)
        count_lookup[key] = {
            "counted_count": bc.count,
            "confidence_score": bc.confidence_score,
            "method": bc.method,
            "sku_id": bc.sku_id,
            "location_id": bc.location_id,
            "lot": bc.lot
        }
    
    # Compare each bin count against book snapshot
    for key, counted in count_lookup.items():
        sku_id, location_id, lot = key
        booked = book_lookup.get(key, {"booked_count": 0})
        
        booked_count = booked["booked_count"]
        counted_count = counted["counted_count"]
        
        # Determine outcome
        variance = counted_count - booked_count
        
        if variance == 0 and booked_count > 0:
            outcome = "Match"
        elif variance < 0 and booked_count > 0:
            # Counted less than booked - shortage
            outcome = "Shortage"
        elif variance > 0:
            # Counted more than booked - excess
            outcome = "Excess"
        elif booked_count == 0 and counted_count > 0:
            # Empty bin originally, now has items
            outcome = "Empty_bin_mismatch"
        elif booked_count > 0 and counted_count == 0:
            # Had booked stock, now nothing scanned - misplaced or not scanned
            # Check if SKU exists at different location
            outcome = "Not_scanned"
        else:
            outcome = "Unknown_item"
        
        # Check for misplaced: SKU in bin B but booked only in bin A
        # Look for other locations with same SKU + different lot
        misplaced_check = False
        if sku_id:
            # Look for this SKU at other locations
            other_locations = db.execute(
                select(bin_count.BinCount.location_id, bin_count.BinCount.count)
                .where(bin_count.BinCount.mission_id == mission_id,
                       bin_count.BinCount.sku_id == sku_id,
                       bin_count.BinCount.lot != lot if lot else True)
            ).all()
            
            if other_locations:
                # SKU found at multiple locations - could be misplaced
                for ol in other_locations:
                    if ol[0] != location_id:
                        misplaced_check = True
                        break
        
        if misplaced_check and booked_count > 0 and counted_count == 0:
            outcome = "Misplaced"
        
        # Create recon result
        from ..models import recon_result as recon_mod
        existing_stmt = select(recon_mod.ReconResult).where(
            recon_mod.ReconResult.mission_id == mission_id,
            recon_mod.ReconResult.sku_id == sku_id,
            recon_mod.ReconResult.location_id == location_id,
            recon_mod.ReconResult.lot == lot
        )
        existing_result = db.execute(existing_stmt).scalar_one_or_none()
        
        if not existing_result:
            recon = recon_mod.ReconResult(
                mission_id=mission_id,
                sku_id=sku_id,
                location_id=location_id,
                lot=lot,
                outcome=outcome,
                variance=variance,
                confidence=counted.get("confidence_score", 0.0)
            )
            db.add(recon)
            reconciled += 1
        
        outcomes_count[outcome] = outcomes_count.get(outcome, 0) + 1
    
    db.commit()
    
    # Open discrepancy cases for shortage/excess only if variance exceeds threshold
    threshold_stmt = select(setting.Setting).where(setting.Setting.key == "discrepancy_variance_threshold")
    threshold_result = db.execute(threshold_stmt)
    threshold_row = threshold_result.scalar_one_or_none()
    variance_threshold = threshold_row.value.get("variance", 10) if threshold_row and threshold_row.value else 10
    
    # Find shortage/excess cases exceeding threshold
    for outcome_name in ["Shortage", "Excess"]:
        if outcomes_count[outcome_name] > 0:
            # Get details of these cases
            for key, counted in count_lookup.items():
                sku_id, location_id, lot = key
                booked = book_lookup.get(key, {"booked_count": 0})
                variance = counted["counted_count"] - booked["booked_count"]
                
                if abs(variance) >= variance_threshold and outcome_name in ["Shortage", "Excess"]:
                    # Check if discrepancy case already exists
                    existing_stmt = select(discrepancy_case.DiscrepancyCase).where(
                        discrepancy_case.DiscrepancyCase.mission_id == mission_id,
                        discrepancy_case.DiscrepancyCase.sku_id == sku_id,
                        discrepancy_case.DiscrepancyCase.location_id == location_id,
                        discrepancy_case.DiscrepancyCase.lot == lot,
                        discrepancy_case.DiscrepancyCase.outcome == outcome_name
                    )
                    existing_case = db.execute(existing_stmt).scalar_one_or_none()
                    
                    if not existing_case:
                        # Determine assigned user based on role
                        # Inventory controller role
                        user_stmt = select(app_user.AppUser).join(
                            user_role.UserRole, app_user.AppUser.id == user_role.UserRole.user_id
                        ).where(user_role.UserRole.role == "Inventory Controller")
                        user_result = db.execute(user_stmt)
                        assigned_user = user_result.scalars().first()
                        
                        # Create discrepancy case
                        from ..models import discrepancy_case as dc_mod
                        dc = dc_mod.DiscrepancyCase(
                            mission_id=mission_id,
                            sku_id=sku_id,
                            location_id=location_id,
                            lot=lot,
                            outcome=outcome_name,
                            variance_value=abs(variance),
                            threshold_value=variance_threshold,
                            status="open",
                            assigned_to=assigned_user.id if assigned_user else None
                        )
                        db.add(dc)
                        
                        # Create case comment
                        from ..models import case_comment as cc_mod
                        comment = cc_mod.CaseComment(
                            case_id=dc.id,
                            user_id=assigned_user.id if assigned_user else 1,
                            comment=f"Auto-generated {outcome_name} discrepancy: variance={variance}"
                        )
                        db.add(comment)
    
    db.commit()
    
    return {
        "status": "success",
        "message": f"Stage 6 complete: {reconciled} reconciliation results",
        "reconciled": reconciled,
        "outcomes": outcomes_count
    }