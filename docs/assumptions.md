# DRIMS - Drone Inventory Management System

## Phase 1 Assumptions

This document captures the key assumptions made during Phase 1 foundation development to resolve ambiguities in the specification.

### 1. Database & Storage
- **PostgreSQL 16 + PostGIS**: Used for all spatial and temporal data. PostGIS version 3.4 available and used.
- **MinIO with S3 API**: Used for object storage of scan images. Images stored hot for 90 days, then archived.
- **Redis 7**: Used as Celery broker for task queue. RabbitMQ/Kafka noted as swappable alternatives.
- **Connection authentication**: PostgreSQL password authentication is used in Docker and production configuration. No trust authentication is part of the supported path.

### 2. Architecture & Pipeline
- **Ingestion gateway**: ONLY validates, stores raw payloads (bronze), and queues. No synchronous processing.
- **Worker pipeline**: All 7 processing stages (validate â†’ decode â†’ location map â†’ dedup â†’ bin count â†’ reconcile â†’ publish) run as Celery workers.
- **Idempotency**: `eventId` serves as the idempotency key. Duplicate events return 200 with `duplicate:true` and are not re-queued.
- **Multi-site ready**: Every table has `site_id`, `created_at`, `updated_at` columns for multi-tenant support.
- **Replay capability**: Every pipeline stage persists its output so any stage can be replayed without re-flying a mission.

### 3. Data Model
- **scan_event table**: Partitioned by month (handled via application logic or pg_partman extension).
- **GS1 AIs**: Parsed from scan values: `(01)GTIN (10)LOT (17)EXPIRY (21)SERIAL`. Unknown codes become `UNKNOWN_ITEM`.
- **Location mapping**: Primary = nearest preceding location-label read in same rack face within 3s default window; fallback = telemetry position mapped to PostGIS bin polygons.
- **Bin confidence formula**: `C_bin = w1*avg_read_confidence + w2*location_method_score + w3*image_coverage_ratio` with `w1+w2+w3=1`, defaults 0.5/0.3/0.2.
- **Location scores**: 1.0 for label match, 0.7 for telemetry fallback.
- **Reconciliation thresholds**: Configurable via `setting` table. Default variance threshold for discrepancy cases: 10 units.
- **IRA (Item Reconciliation Accuracy)**: Share of scanned bins with outcome `Match`.

### 4. Ingestion Endpoints
- **POST /ingest/v1/missions**: Register/update mission (status: RECEIVING â†’ PROCESSING â†’ RECONCILED/FAILED)
- **POST /ingest/v1/missions/{missionId}/scans**: Batch up to 1,000 scan events
- **POST /ingest/v1/missions/{missionId}/telemetry**: Upload mission telemetry
- **POST /ingest/v1/missions/{missionId}/images:presign**: Pre-signed MinIO upload URLs
- **POST /ingest/v1/missions/{missionId}/complete**: Triggers final reconciliation
- **Response codes**: 202 queued, 413 oversize, 429 with Retry-After, 401/403 for auth
- **Unknown schema versions**: Go to quarantine

### 5. Roles & Security
- **Roles**: Admin, Inventory controller, Warehouse supervisor, Viewer/auditor, System integration account
- **RBAC**: Enforced at API layer with site scoping
- **TLS 1.2+**: Enforced for all connections
- **Secrets**: From environment variables only (no hardcoded secrets)
- **Rate limiting**: 200 scan events/s sustained ingestion; API p95 <= 500ms for UI reads
- **Size limits**: Max payload 10MB; max image 100MB
- **Parameterised queries**: All DB queries use parameterised statements
- **Private image bucket**: MinIO with signed URLs (valid <=10 min)
- **Append-only audit log**: For every change to counts, cases, adjustments and settings

### 6. Frontend & UI
- **Gate 1 shell**: Vite + React 18 + strict TypeScript, Ant Design, React Router, TanStack Query, and Keycloak OIDC PKCE.
- **Production serving**: The frontend is compiled in `node:20-alpine` and served by nginx with SPA fallback and security headers.
- **Authentication**: The browser uses the public `drims-web` Keycloak client with Authorization Code + PKCE. No browser client secret is stored.
- **Gate 2+ screens**: Dashboard data, mission workflows, map rendering, discrepancies, reports, master data, and administration are implemented only after their API contracts are verified.

### 7. Non-Functional Targets
- **5,000-bin mission**: ~20,000 scans, ~10,000 images reconciled within 15 min of last payload
- **Single-bin recompute**: <= 5 s
- **Retention**: Scan data 2 yrs, images 90 days hot then archive, audit logs 7 yrs (configurable)
- **Unit test coverage**: >= 80% on processing and reconciliation logic
- **API versioning**: Versioned APIs and schemas

### 8. Technology Stack Choices
- **Backend**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy + Alembic, Celery
- **DB**: PostgreSQL 16 + PostGIS (pg_partman for partition management)
- **Cache/Queue**: Redis 7 (Celery broker), swappable to RabbitMQ/Kafka
- **Object storage**: MinIO (S3 API)
- **Auth**: OIDC (Keycloak in Docker compose); machine clients use OAuth2 client credentials
- **Reports**: openpyxl (Excel), WeasyPrint (PDF)
- **Observability**: OpenTelemetry, Prometheus metrics endpoint
- **Deployment**: Docker, Helm chart skeleton for Kubernetes

### 9. Known Limitations (Phase 1)
- CV re-decoding of images (zxing-cpp/pyzbar/YOLO): Planned for Phase 5
- File-drop and scheduled-pull adapters: Planned for Phase 5
- ERP posting/export fallback: Planned for Phase 4
- Email/Teams webhook alerts: Planned for Phase 4
- Helm chart: Planned for Phase 4
- Security penetration testing: Planned for Phase 4

### 10. Environment-Specific Notes
- **Windows development**: The supported execution path is Docker; host Python and npm are not required.
- **Docker networking**: PostgreSQL trust auth for local Docker connections; production would use proper password auth
- **Python 3.13 compatibility**: Images install the runtime dependencies during the Docker build.
