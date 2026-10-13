"""Celery application used by the DIMS worker container."""

import os

from celery import Celery


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

__all__ = ["celery_app"]

