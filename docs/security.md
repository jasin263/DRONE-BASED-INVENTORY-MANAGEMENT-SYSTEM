# DRIMS frontend security evidence

## Dependency audit

The initial Docker install reported 9 vulnerabilities (6 moderate, 1 high, and 2 critical), including vulnerable `tinypool`, `vite`, `react-router`, and `echarts` versions. Dependencies were upgraded in the frontend manifest and lockfile.

Verified in Docker after the upgrade:

```text
found 0 vulnerabilities
```

The audit command was run in the Node 20 build environment; host npm is not required.

## Remaining security work

The Gate 1 authentication and authorization evidence is still open. In particular, backend JWT validation/RBAC and the full per-role Playwright matrix are not yet verified. Dependency audit success does not constitute authorization proof.

## Development credentials

The Compose defaults and imported Keycloak realm contain development-only
credentials for local Docker use: `admin/adminpass`,
`inventory_controller/controllerpass`, `warehouse_supervisor/supervisorpass`,
`viewer/viewerpass`, and `system_integration/integrationpass`. They must be
overridden or removed before any shared, staging, or production deployment.
The `drims-api` Keycloak client and its secret are development-only values.
The realm maps each development user's `site_ids` attribute into the access
token and adds the `drims-api` audience. Replace the secret and disable direct
grants before any non-development deployment.
