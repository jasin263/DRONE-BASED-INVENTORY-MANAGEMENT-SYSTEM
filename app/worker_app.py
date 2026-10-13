"""Celery application used by the DIMS worker container."""

import os
from datetime import datetime, timezone

from celery import Celery
from sqlalchemy import text

from .core.db import engine


redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
redis_port = os.getenv("REDIS_PORT", "6379")
redis_url = f"redis://{redis_host}:{redis_port}/0"

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
        "schedule": 86400.0,
    }
}


@celery_app.task(name="app.worker_app.ensure_scan_event_partitions")
def ensure_scan_event_partitions() -> str:
    """Create the current and next two monthly scan-event partitions."""
    with engine.begin() as connection:
        connection.execute(text("SELECT ensure_scan_event_partitions(:months)"), {"months": 3})
    return datetime.now(timezone.utc).isoformat()

__all__ = ["celery_app"]
