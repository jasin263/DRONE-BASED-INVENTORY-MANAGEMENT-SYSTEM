# DRIMS frontend

## Gate 1 routes

| Route | Access | Purpose |
|---|---|---|
| `/login` | Public | Keycloak OIDC Authorization Code + PKCE sign-in |
| `/` | Authenticated | Operations dashboard shell |
| `/missions` | Authenticated | Mission workspace entry |
| `/discrepancies` | Authenticated | Discrepancy workspace entry |
| `/warehouse-map` | Authenticated | Warehouse map entry |
| `/reports` | Authenticated | Reports entry |
| `/master-data` | Admin | Master data entry |
| `/administration` | Admin | Administration entry |
| `/audit-log` | Admin, Viewer | Audit entry |
| `/notifications` | Authenticated | Notification centre entry |
| `/help` | Authenticated | Help and version entry |
| `/403` | Authenticated | Access denied |

## Gate 1 components

- `AuthProvider`: Keycloak PKCE initialization, token refresh, profile, roles, login, and logout.
- `ProtectedRoute` and `RoleRoute`: client-side navigation guards. Backend authorization remains authoritative.
- `Shell`: responsive Ant Design layout, site selector, theme toggle, notifications, user menu, breadcrumbs, and status banner.
- `api.ts`: typed health response and RFC 7807 API error surface used by TanStack Query.
- nginx: SPA fallback, `/api/` reverse proxy, gzip, and baseline security headers.

## Verified API usage

- `GET /health/ready` is polled by the shell every 30 seconds.
- The shell only reports the system operational when the backend returns HTTP 200 with `status: ready`.
- Dependency failures are presented as an actionable status banner with retry.

Gate 2 pages intentionally do not claim data functionality until their backend endpoints and generated OpenAPI client contracts are verified.

The current `/api/v1/inventory-map` endpoint is **DEMO-ONLY**. It reads CSV files directly from
`Dataset/drone_inventory_outputs` (`location.csv`, `bin_count.csv`, `discrepancy_cases.csv`,
and `mission_plan.csv`) and does not read persisted pipeline results. It must be replaced with
database-backed published pipeline output before production use.

## Current Gate 1 evidence

- **VERIFIED:** Docker Node 20 frontend build, generated OpenAPI TypeScript client, six Vitest tests, two Dockerized Playwright smoke tests, npm audit with zero vulnerabilities, and nginx security headers/gzip.
- **WRITTEN BUT UNTESTED:** Full Keycloak login/PKCE callback, silent refresh, logout/session expiry, per-role navigation, API-side 401/403, axe, Lighthouse, responsive screenshots, and clean-start login against real API data.
- **NOT STARTED:** Gate 2 data pages and their required backend endpoints.

The Playwright smoke tests cover unauthenticated route behavior only; they do not prove the required authentication matrix or backend authorization.
