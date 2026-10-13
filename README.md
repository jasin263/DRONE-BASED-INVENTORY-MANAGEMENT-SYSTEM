# DRIMS

Drone Inventory Management System for turning receiving-system scan data into
verified bin counts and warehouse reconciliation cases.

## Start

Docker is the supported runtime. From the repository root:

```powershell
docker compose down -v
docker compose up -d --build
docker compose ps
```

The dashboard is available at `http://localhost:3000`. The API live and
readiness probes are available at `/health/live` and `/health/ready`.

Alembic migrations run automatically from the backend entrypoint. To run them
manually inside the backend container, use:

```powershell
docker compose exec backend alembic -c /app/backend/db/alembic.ini upgrade head
docker compose exec backend alembic -c /app/backend/db/alembic.ini current
```

## Repository boundaries

DRIMS begins at the receiving-system data contract. Drone flight control,
warehouse connectivity, ERP ownership, and physical scanning are external
systems.

## Status

Gate-by-gate verification is recorded in [`docs/audit.md`](docs/audit.md),
[`docs/runbook.md`](docs/runbook.md), and [`docs/assumptions.md`](docs/assumptions.md).
