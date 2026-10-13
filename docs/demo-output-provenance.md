# Demo inventory output provenance

The files under `Dataset/drone_inventory_outputs/` are workspace-supplied CSV
outputs. No generator script or source citation for these files exists in the
repository, and no independent ground-truth package was supplied with them.
They therefore remain **demo-only** and must not be treated as production
pipeline output or ground truth.

The inventory-map endpoint reads these files directly:

- `location.csv`: 5,000 rows
- `bin_count.csv`: 5,000 rows
- `discrepancy_cases.csv`: 907 rows
- `mission_plan.csv`: 5,000 rows

The runtime manifest records the columns, row counts, byte counts, and
SHA-256 checksum for each file. The values include expected quantities,
counts, discrepancies, outcomes, and mission fields, but their provenance and
ground-truth status are unverified. The endpoint must be replaced by persisted
results from the real ingestion and pipeline stages before production use.
