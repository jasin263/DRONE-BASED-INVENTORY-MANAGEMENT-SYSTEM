from __future__ import annotations

from pathlib import Path

from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode
import zxingcpp


ROOT = Path(__import__("os").environ.get("BARCODE_ROOT", "/dataset"))
files = sorted(ROOT.glob("*.jpg"))[:200] if list(ROOT.glob("*.jpg")) else sorted((ROOT / "Test").glob("*.png"))[:100]
if not files:
    raise SystemExit("No test images found")
with Image.open(files[0]) as sample:
    if sample.mode not in {"RGB", "RGBA"} or (
        files[0].suffix.lower() == ".png" and min(sample.size) < 300
    ):
        print(
            "NOT_APPLICABLE: supplied test split contains barcode patches or derived images, "
            "not full colour barcode photographs"
        )
        raise SystemExit(0)
pyzbar_success = 0
zxing_success = 0
samples: list[dict[str, object]] = []

for path in files:
    with Image.open(path) as image:
        image = image.convert("RGB")
        py_results = pyzbar_decode(image)
        zx_results = zxingcpp.read_barcodes(image)
    pyzbar_values = [result.data.decode("utf-8", "replace") for result in py_results]
    zxing_values = [result.text for result in zx_results]
    pyzbar_success += bool(pyzbar_values)
    zxing_success += bool(zxing_values)
    if len(samples) < 5:
        samples.append({"file": path.name, "pyzbar": pyzbar_values, "zxingcpp": zxing_values})

count = len(files)
print(f"images={count}")
print(f"pyzbar_success={pyzbar_success} rate={pyzbar_success / count:.1%}")
print(f"zxingcpp_success={zxing_success} rate={zxing_success / count:.1%}")
print(f"samples={samples}")
