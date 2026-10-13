# DRIMS operations runbook

## Start and stop

```powershell
docker compose up -d --build
docker compose ps
docker compose logs -f backend worker
docker compose down
```

For a destructive local reset only:

```powershell
docker compose down -v
docker compose up -d --build
```

## Health checks

- `/health/live` proves only that the API process is serving.
- `/health/ready` checks PostgreSQL, Redis, MinIO, and the Keycloak JWKS
  endpoint. It returns `503` if any dependency is unavailable.

## First response

1. Run `docker compose ps`.
2. Inspect the unhealthy service logs.
3. Do not bypass healthchecks or use a local host process.
4. Preserve the failing output for the incident record.
