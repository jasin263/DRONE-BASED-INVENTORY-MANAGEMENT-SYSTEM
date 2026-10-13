from __future__ import annotations

import json
import statistics
from pathlib import Path


ROOT = Path("/data/abid/metadata")
rows = []
for path in sorted(ROOT.glob("*.json")):
    value = json.loads(path.read_text(encoding="utf-8"))
    items = list((value.get("BIN_FCSKU_DATA") or {}).values())
    expected = int(value.get("EXPECTED_QUANTITY") or 0)
    actual = sum(int(item.get("quantity") or 0) for item in items)
    rows.append((path.name, expected, actual, items))

mismatches = [(name, expected, actual) for name, expected, actual, _ in rows if expected != actual]
missing_dimensions = []
missing_weight = []
asin_bins: dict[str, set[str]] = {}
for name, _, _, items in rows:
    for item in items:
        asin = str(item.get("asin") or "")
        if not all(item.get(field) and item[field].get("value") is not None for field in ("height", "length", "width")):
            missing_dimensions.append((name, asin))
        if not item.get("weight") or item["weight"].get("value") is None:
            missing_weight.append((name, asin))
        if asin:
            asin_bins.setdefault(asin, set()).add(name)
expected_values = [expected for _, expected, _, _ in rows]
shared = {asin: sorted(bins) for asin, bins in asin_bins.items() if len(bins) > 1}

print(f"metadata_files={len(rows)}")
print(f"expected_quantity_match_rate={(len(rows) - len(mismatches)) / len(rows):.1%}")
print(f"mismatch_count={len(mismatches)}")
print(f"mismatch_sample={mismatches[:5]}")
print(f"missing_dimensions_count={len(missing_dimensions)}")
print(f"missing_weight_count={len(missing_weight)}")
print(f"distinct_asin_count={len(asin_bins)}")
print(f"shared_asin_count={len(shared)}")
print(f"shared_asin_sample={list(shared.items())[:5]}")
print(
    "expected_quantity_min_median_max="
    f"{min(expected_values)}/{statistics.median(expected_values)}/{max(expected_values)}"
)
print("sample_explanation=00001 has item quantities 4+2+6=12, matching EXPECTED_QUANTITY=12")
