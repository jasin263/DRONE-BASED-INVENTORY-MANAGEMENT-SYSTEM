# Gate 0 audit

Audit date: 2026-10-12

This is an evidence-led baseline. A requirement is `VERIFIED` only when the
raw command output is recorded below. `WRITTEN BUT UNTESTED` means code or
configuration exists but the required Docker proof has not passed. `NOT
STARTED` means the repository has no implementation.

## Final Gate 0 findings

| Area | Status | Evidence / finding |
|---|---|---|
| Docker Compose clean start | VERIFIED | Final `docker compose down -v; docker compose up -d --build` exited 0; all 13 services reported healthy. |
| Root package `app` | VERIFIED | Backend and worker containers started from the top-level `app` package. |
| Password PostgreSQL driver | VERIFIED | Final Docker build succeeded and Alembic reported `001_initial_schema (head)`. |
| `simple_app.py` removed | VERIFIED | The workaround file is absent from the application layout. |
| Production-foundation services | VERIFIED | Postgres/PostGIS, Redis, MinIO/init, Keycloak, Mailpit, API, worker, beat, frontend, Prometheus, Grafana, Loki, and OTEL all reported healthy. |
| Honest live/readiness health | VERIFIED | Final output was `live=200 ready=200`; dependency-stop runs returned 503 for Postgres, MinIO, and Keycloak, and the stack restored to ready. |
| Alembic migration execution | VERIFIED | `001_initial_schema (head)` and 148 PostgreSQL relations were present after a clean volume reset. |
| Gate 0 automated tests | VERIFIED | Docker output: `19 passed, 2 warnings in 1.18s`. |
| Full required production schema | WRITTEN BUT UNTESTED | Migration `002_gate0_schema` adds provenance columns, PostGIS geometry, role/job/dead_letter tables, indexes, and audit immutability. Monthly scan-event partition conversion remains to be implemented and verified. |

## Raw audit commands

### Existing files

```text
simple_app.py
test_import.py
backend/Dockerfile.backend
backend/Dockerfile.worker
docker-compose.yml
requirements.txt
keycloak/realm-drims.json
```

### Final clean-start proof

```text
drims-backend ... Up ... (healthy)
drims-beat ... Up ... (healthy)
drims-frontend ... Up ... (healthy)
drims-grafana ... Up ... (healthy)
drims-keycloak ... Up ... (healthy)
drims-loki ... Up ... (healthy)
drims-mailpit ... Up ... (healthy)
drims-minio ... Up ... (healthy)
drims-otel ... Up ... (healthy)
drims-postgres ... Up ... (healthy)
drims-prometheus ... Up ... (healthy)
drims-redis ... Up ... (healthy)
drims-worker ... Up ... (healthy)
```

```text
live=200 ready=200
001_initial_schema (head)
...................                                                      [100%]
19 passed, 2 warnings in 1.18s
```

### Gate 0 decision

Gate 0 infrastructure stabilization is VERIFIED. The gate as a whole remains
WRITTEN BUT UNTESTED until the full required production schema is implemented
and verified. Gate 1 has not started.
