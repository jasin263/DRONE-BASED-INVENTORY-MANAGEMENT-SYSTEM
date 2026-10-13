"""Celery application used by the DIMS worker container."""

import os
import logging

from celery import Celery
from sqlalchemy import text

from .core.db import engine


redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
redis_port = os.getenv("REDIS_PORT", "6379")
redis_url = f"redis://{redis_host}:{redis_port}/0"
logger = logging.getLogger(__name__)

celery_app = Celery(
    "dims",
    broker=redis_url,
    backend=redis_url,
    include=[
        "app.workers.stage1_validate",
        "app.workers.stage2_decode_normalise",
        "app.workers.stage3_location_mapping",
        "app.workers.stage4_dedup",
        "app.workers.stage5_bin_count_confidence",
        "app.workers.stage6_reconciliation",
        "app.workers.stage7_publish",
    ],
)

celery_app.conf.beat_schedule = {
    "ensure-scan-event-partitions": {
        "task": "app.worker_app.ensure_scan_event_partitions",
        "schedule": float(os.getenv("PARTITION_MAINTENANCE_INTERVAL", "86400")),
    }
}


@celery_app.task(name="app.worker_app.ensure_scan_event_partitions")
def ensure_scan_event_partitions(months_ahead: int = 3) -> dict[str, object]:
    """Create monthly partitions and safely drain matching default-partition rows."""
    with engine.begin() as connection:
        default_rows = connection.execute(
            text("SELECT count(*) FROM scan_event_default")
        ).scalar_one()
        if default_rows:
            logger.warning(
                "scan_event_default contains %s rows; maintenance will redistribute matching months",
                default_rows,
            )
        result = connection.execute(
            text("SELECT ensure_scan_event_partitions(:months)"),
            {"months": months_ahead},
        ).scalar_one()
    return dict(result)

__all__ = ["celery_app"]
