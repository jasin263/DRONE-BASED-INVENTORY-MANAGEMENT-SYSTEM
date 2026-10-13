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
