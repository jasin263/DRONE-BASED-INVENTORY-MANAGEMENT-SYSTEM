"""Create DRIMS object-storage buckets before the API starts."""

import os
import time

from minio import Minio


client = Minio(
    "minio:9000",
    access_key=os.environ["MINIO_ROOT_USER"],
    secret_key=os.environ["MINIO_ROOT_PASSWORD"],
    secure=False,
)

for attempt in range(30):
    try:
        for bucket in ("drone-raw", "drone-images", "reference-data", "reports"):
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
        open("/tmp/initialized", "w", encoding="ascii").close()
        break
    except Exception:
        if attempt == 29:
            raise
        time.sleep(2)
