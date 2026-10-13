"""Download and stage the approved public DRIMS development data."""

from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from minio import Minio
from PIL import Image


ROOT = Path(os.getenv("DATA_ROOT", "/data"))
ABID_ROOT = ROOT / "abid"
ARTELAB_ROOT = ROOT / "barcode" / "artelab_hough_no1"
MANIFEST_PATH = ROOT / "MANIFEST.json"
SAMPLE_SIZE = int(os.getenv("BIN_SAMPLE_SIZE", "5000"))
SAMPLE_MODE = os.getenv("BIN_SAMPLE_MODE", "random").lower()
SAMPLE_SEED = int(os.getenv("BIN_SAMPLE_SEED", "42"))
MAX_BYTES = 20 * 1024 * 1024 * 1024
BUCKET = "aft-vbi-pds"
REGION = "us-east-1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_manifest() -> dict[str, Any]:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {"generated_at": None, "entries": []}


def save_manifest(manifest: dict[str, Any]) -> None:
    manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def public_s3():
    return boto3.client(
        "s3",
        region_name=REGION,
        config=Config(
            signature_version=UNSIGNED,
            connect_timeout=15,
            read_timeout=45,
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


def list_sample(client) -> list[tuple[str, str, int, int]]:
    def list_prefix(prefix: str, suffix: str) -> dict[str, tuple[str, int]]:
        command = ["aws", "s3api", "list-objects-v2", "--bucket", BUCKET, "--prefix", prefix]
        if SAMPLE_MODE != "random":
            command.extend(["--max-items", str(SAMPLE_SIZE + 1)])
        command.extend(["--page-size", "1000", "--no-sign-request", "--output", "json"])
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
        objects: dict[str, tuple[str, int]] = {}
        for item in json.loads(completed.stdout).get("Contents", []):
            key = item["Key"]
            identifier = key.rsplit("/", 1)[-1]
            if identifier.endswith(suffix) and identifier[: -len(suffix)].isdigit():
                objects[identifier[: -len(suffix)]] = (key, item["Size"])
        return objects

    image_objects = list_prefix("bin-images/", ".jpg")
    metadata_objects = list_prefix("metadata/", ".json")
    ids = sorted(set(image_objects) & set(metadata_objects), key=lambda value: int(value))
    if SAMPLE_MODE == "random":
        random.Random(SAMPLE_SEED).shuffle(ids)
        ids = ids[:SAMPLE_SIZE]
    elif SAMPLE_MODE == "ordered":
        ids = ids[:SAMPLE_SIZE]
    else:
        raise ValueError("BIN_SAMPLE_MODE must be 'random' or 'ordered'")
    missing_images = sorted(set(metadata_objects) - set(image_objects), key=lambda value: int(value))[:SAMPLE_SIZE]
    missing_metadata = sorted(set(image_objects) - set(metadata_objects), key=lambda value: int(value))[:SAMPLE_SIZE]
    if missing_images or missing_metadata:
        raise RuntimeError(
            f"paired-object check failed: missing_images={missing_images[:5]}, "
            f"missing_metadata={missing_metadata[:5]}"
        )
    if len(ids) < SAMPLE_SIZE:
        raise RuntimeError(f"requested {SAMPLE_SIZE} paired bins but only found {len(ids)}")
    return [(image_objects[item][0], metadata_objects[item][0], image_objects[item][1], metadata_objects[item][1]) for item in ids]


def download_one(
    client, key: str, destination: Path, expected_size: int, expected_sha: str | None
) -> tuple[str, bool]:
    if destination.exists() and destination.stat().st_size == expected_size:
        local_sha = sha256(destination)
        if expected_sha is None or local_sha == expected_sha:
            return local_sha, True
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    client.download_file(BUCKET, key, str(temporary))
    if temporary.stat().st_size != expected_size:
        raise RuntimeError(f"size mismatch for {key}: {temporary.stat().st_size} != {expected_size}")
    temporary.replace(destination)
    return sha256(destination), False


def parse_metadata(path: Path) -> tuple[str | None, int | None, list[dict[str, Any]]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, list):
        value = {"items": value}
    item_map = value.get("BIN_FCSKU_DATA") or {}
    items = list(item_map.values()) if isinstance(item_map, dict) else (
        value.get("items") or value.get("products") or value.get("contents") or []
    )
    expected = value.get("EXPECTED_QUANTITY")
    if expected is None:
        expected = value.get("expected_quantity")
    if expected is None:
        expected = sum(int(item.get("quantity", 0) or 0) for item in items if isinstance(item, dict))
    bin_id = value.get("bin_id") or value.get("binId") or path.stem
    return bin_id, int(expected or 0), [item for item in items if isinstance(item, dict)]


def upload(client: Minio, bucket: str, prefix: str, path: Path, object_name: str) -> None:
    object_path = "/".join(part for part in (prefix, object_name) if part)
    client.fput_object(bucket, object_path, str(path), content_type="application/octet-stream")


def stage_artelab(manifest: dict[str, Any], minio_client: Minio) -> dict[str, Any] | None:
    if not ARTELAB_ROOT.exists():
        return None
    files = sorted(path for path in ARTELAB_ROOT.rglob("*") if path.is_file())
    if not files:
        raise RuntimeError(f"ArTe-Lab directory is present but empty: {ARTELAB_ROOT}")
    records: list[dict[str, Any]] = []
    for path in files:
        relative = path.relative_to(ARTELAB_ROOT).as_posix()
        records.append(
            {
                "path": f"barcode/artelab_hough_no1/{relative}",
                "object": f"barcode/artelab_hough_no1/{relative}",
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "data_source": "barcode_ref",
            }
        )
    entry = {
        "dataset": "ArTe-Lab 1D barcode dataset no. 1 (Hough barcode)",
        "source_url": "https://artelab.dista.uninsubria.it/downloads/datasets/barcode/hough_barcode_1d/1d_barcode_hough.zip",
        "acquisition": "manually downloaded and extracted",
        "access_date": datetime.now(timezone.utc).isoformat(),
        "licence": "licence not stated; evaluation use only; do not redistribute",
        "citation": 'Zamberletti, Gallo and Albertini, "Robust Angle Invariant 1D Barcode Detection", ACPR 2013',
        "file_count": len(records),
        "total_bytes": sum(item["bytes"] for item in records),
        "data_source": "barcode_ref",
        "files": records,
    }
    manifest["entries"] = [
        item for item in manifest.get("entries", [])
        if item.get("dataset") != entry["dataset"]
    ] + [entry]
    jobs = []
    with ThreadPoolExecutor(max_workers=int(os.getenv("UPLOAD_WORKERS", "4"))) as executor:
        for item in records:
            source = ARTELAB_ROOT / item["path"].split("barcode/artelab_hough_no1/", 1)[1]
            jobs.append(executor.submit(upload, minio_client, "reference-data", "", source, item["object"]))
        for job in as_completed(jobs):
            job.result()
    return entry


def process_pair(
    s3, pair: tuple[str, str, int, int], expected_hashes: dict[str, str]
) -> dict[str, Any]:
    image_key, metadata_key, image_size, metadata_size = pair
    identifier = image_key.rsplit("/", 1)[-1][:-4]
    image_path = ABID_ROOT / "images" / f"{identifier}.jpg"
    metadata_path = ABID_ROOT / "metadata" / f"{identifier}.json"
    image_hash, image_reused = download_one(
        s3, image_key, image_path, image_size, expected_hashes.get(image_key)
    )
    metadata_hash, metadata_reused = download_one(
        s3, metadata_key, metadata_path, metadata_size, expected_hashes.get(metadata_key)
    )
    with Image.open(image_path) as image:
        image.verify()
        width, height = image.size
    bin_id, expected_quantity, items = parse_metadata(metadata_path)
    return {
        "identifier": identifier,
        "image": {"key": image_key, "path": str(image_path.relative_to(ROOT)), "sha256": image_hash, "bytes": image_path.stat().st_size},
        "metadata": {"key": metadata_key, "path": str(metadata_path.relative_to(ROOT)), "sha256": metadata_hash, "bytes": metadata_path.stat().st_size, "bin_id": bin_id, "expected_quantity": expected_quantity, "items": items},
        "item_count": len(items),
        "dimensions": f"{width}x{height}",
        "reused_files": int(image_reused) + int(metadata_reused),
    }


def main() -> int:
    if SAMPLE_SIZE < 1:
        raise ValueError("BIN_SAMPLE_SIZE must be positive")
    manifest = load_manifest()
    expected_hashes: dict[str, str] = {}
    for prior_entry in manifest.get("entries", []):
        for item in prior_entry.get("images", []) + prior_entry.get("metadata", []):
            if item.get("key") and item.get("sha256"):
                expected_hashes[item["key"]] = item["sha256"]
    s3 = public_s3()
    print(
        f"Listing s3://{BUCKET}/ with --no-sign-request equivalent; "
        f"sample={SAMPLE_SIZE} mode={SAMPLE_MODE} seed={SAMPLE_SEED}",
        flush=True,
    )
    pairs = list_sample(s3)
    estimate = sum(image_size + metadata_size for _, _, image_size, metadata_size in pairs)
    print(f"Estimated download size: {estimate} bytes ({estimate / 1024 / 1024:.2f} MiB)", flush=True)
    if estimate > MAX_BYTES:
        raise RuntimeError(f"estimated download exceeds 20 GiB: {estimate} bytes")

    images: list[dict[str, Any]] = []
    metadata_rows: list[dict[str, Any]] = []
    distribution = {"zero_items": 0, "one_item": 0, "two_to_five_items": 0, "six_plus_items": 0}
    dimensions: dict[str, int] = {}
    total_image_bytes = 0
    with ThreadPoolExecutor(max_workers=int(os.getenv("DOWNLOAD_WORKERS", "16"))) as executor:
        futures = [executor.submit(process_pair, s3, pair, expected_hashes) for pair in pairs]
        results = []
        for index, future in enumerate(as_completed(futures), start=1):
            results.append(future.result())
            if index % 250 == 0 or index == len(pairs):
                print(f"Downloaded and validated {index}/{len(pairs)} bins", flush=True)
    results.sort(key=lambda item: int(item["identifier"]))
    reused_files = sum(result["reused_files"] for result in results)
    for result in results:
        item_count = result["item_count"]
        if item_count == 0:
            distribution["zero_items"] += 1
        elif item_count == 1:
            distribution["one_item"] += 1
        elif item_count <= 5:
            distribution["two_to_five_items"] += 1
        else:
            distribution["six_plus_items"] += 1
        dimensions[result["dimensions"]] = dimensions.get(result["dimensions"], 0) + 1
        total_image_bytes += result["image"]["bytes"]
        images.append(result["image"])
        metadata_rows.append(result["metadata"])
    if results:
        (ABID_ROOT / "sample_metadata.json").write_text(
            (ROOT / results[0]["metadata"]["path"]).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    minio_client = Minio(
        os.getenv("MINIO_ENDPOINT", "minio:9000"),
        access_key=os.getenv("MINIO_ROOT_USER", "minioadmin"),
        secret_key=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"),
        secure=False,
    )
    for bucket in ("drone-images", "reference-data"):
        if not minio_client.bucket_exists(bucket):
            minio_client.make_bucket(bucket)
    artelab_entry = stage_artelab(manifest, minio_client)
    upload_jobs = []
    with ThreadPoolExecutor(max_workers=int(os.getenv("UPLOAD_WORKERS", "4"))) as executor:
        for item in images:
            upload_jobs.append(executor.submit(upload, minio_client, "drone-images", "abid/bin-images", ROOT / item["path"], Path(item["path"]).name))
        for item in metadata_rows:
            upload_jobs.append(executor.submit(upload, minio_client, "reference-data", "abid/metadata", ROOT / item["path"], Path(item["path"]).name))
        for future in as_completed(upload_jobs):
            future.result()

    entry = {
        "dataset": "Amazon Bin Image Dataset",
        "source_url": "https://registry.opendata.aws/amazon-bin-imagery",
        "bucket": "s3://aft-vbi-pds",
        "region": REGION,
        "access_date": datetime.now(timezone.utc).isoformat(),
        "licence": "CC BY-NC-SA 3.0 US; development, testing and demo only; never shipped in a commercial release",
        "sample_size": SAMPLE_SIZE,
        "sample_mode": SAMPLE_MODE,
        "sample_seed": SAMPLE_SEED,
        "download_command": "docker compose --profile data-loader run --rm -e BIN_SAMPLE_SIZE=5000 data-loader",
        "estimated_bytes": estimate,
        "image_bytes": total_image_bytes,
        "image_count": len(images),
        "metadata_count": len(metadata_rows),
        "pair_count": len(images),
        "item_count_distribution": distribution,
        "dimensions": dimensions,
        "images": images,
        "metadata": metadata_rows,
    }
    manifest["entries"] = [item for item in manifest["entries"] if item.get("dataset") != entry["dataset"]]
    manifest["entries"].append(entry)
    save_manifest(manifest)
    print(json.dumps({"images": len(images), "metadata": len(metadata_rows), "image_bytes": total_image_bytes, "reused_files": reused_files, "distribution": distribution, "artelab_files": artelab_entry["file_count"] if artelab_entry else 0, "manifest": str(MANIFEST_PATH)}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
