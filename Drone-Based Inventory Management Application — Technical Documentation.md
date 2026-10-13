Drone-Based Inventory Management Application — Technical Documentation 

# Drone-Based Inventory Management Application — Technical Documentation 

Oct 9, 2026 · @Renuka 

## 1. Purpose and scope 

We build the software layer that takes scan data from the existing drone data-receiving system, turns it into verified stock counts per location, and reconciles them against the book stock in the WMS/ERP. Drone hardware, flight control and the receiving system itself are owned by others; our boundary starts at the data handed to us. 

|In scope (our team)|Out of scope|
|---|---|
|Ingestion of scan payloads, images and<br>telemetry from the receiving system|Drone hardware, firmware, sensors,<br>batteries|
|Validation, decoding, deduplication and<br>location mapping|Flight planning, autonomy, collision<br>avoidance|
|Reconciliation against WMS/ERP book stock|The ground station / receiving system and<br>its storage|
|Discrepancy workflow, dashboards, reports,<br>alerts|Physical recounts and stock adjustments in<br>the ERP (we only propose them)|
|APIs, web UI, security, deployment and<br>monitoring|Network and Wi-Fi coverage in the<br>warehouse|



Intended readers: developers, QA, DevOps, the integration partner who owns the receiving system, and the client's warehouse operations lead. 

## 2. System context and assumptions 

The application sits between the drone receiving system (upstream) and the client's WMS/ERP (downstream reference), and serves warehouse users through a web UI. The design assumes the receiving system can push data to us or expose it for pull; both are supported so the integration choice can be finalised later. 

Page 1 of 17 

Drone-Based Inventory Management Application — Technical Documentation 

|Data type from<br>receiving system|Content|Expected<br>format|Use in our application|
|---|---|---|---|
|Mission<br>metadata|Mission ID, warehouse,<br>zone, start/end time,<br>drone ID, operator|JSON|Groups all scans of one<br>counting run|
|Scan events|Barcode / QR / RFID<br>values, symbology, read<br>confidence, timestamp|JSON / CSV|Core input for item<br>identification|
|Location tags|Rack-location barcode<br>or fiducial marker read,<br>or coordinates|JSON|Maps each scan to a bin /<br>slot|
|Telemetry|Position (x, y, z),<br>heading, timestamp per<br>frame|JSON / CSV|Fallback location<br>mapping, coverage<br>checks|
|Images|Frame images of each<br>rack face, optionally<br>with bounding boxes|JPEG/PNG +<br>JSON sidecar|Evidence for<br>discrepancies, optional AI<br>re-decoding|



Working assumptions, to confirm with the receiving-system owner: 

- Every payload carries a mission ID and a UTC timestamp. 

- Each rack location has a scannable location label, or the receiving system provides coordinates in a warehouse frame we can map to bins. 

- Images are available within the same mission, either inline (pre-signed URL) or as a batch upload after landing. 

- The WMS/ERP exposes book stock per location via API or a scheduled export (CSV / database view). 

- A single mission produces up to about 5,000 locations, 20,000 scan events and 10,000 images; sizing in section 4 uses these figures. 

## 3. Functional requirements 

The application must turn each drone mission into a reconciled count with a reviewable list of discrepancies. Priority uses MoSCoW: M = must, S = should, C = could. 

Page 2 of 17 

Drone-Based Inventory Management Application — Technical Documentation 

|ID|Module|Requirement|Priority|
|---|---|---|---|
|FR-01|Ingestion|Receive mission metadata, scans, telemetry and<br>images via REST push, file drop (S3/SFTP) or<br>scheduled pull|M|
|FR-02|Ingestion|Validate every payload against a versioned schema;<br>reject or quarantine invalid records with a reason|M|
|FR-03|Ingestion|Process re-sent payloads idempotently (no double<br>counting)|M|
|FR-04|Processing|Normalise barcodes (GS1, EAN-13, Code-128, QR,<br>RFID EPC) to internal SKU / lot / serial|M|
|FR-05|Processing|Assign every item scan to a bin using location<br>labels, falling back to telemetry coordinates|M|
|FR-06|Processing|Deduplicate repeated reads of the same item<br>across frames|M|
|FR-07|Processing|Score each bin's count with a confidence value and<br>flag low-confidence bins|M|
|FR-08|Processing|Re-decode unread labels from images using<br>computer vision|C|
|FR-09|Reconciliation|Fetch book stock from WMS/ERP at mission start<br>and compare per bin, SKU and lot|M|
|FR-10|Reconciliation|Classify each result: match, shortage, excess,<br>misplaced, unknown item, empty-bin mismatch,<br>not scanned|M|
|FR-11|Discrepancy|Create a discrepancy case with image evidence;<br>allow assign, comment, approve or reject|M|
|FR-12|Discrepancy|Push approved adjustments to WMS/ERP or export<br>them for manual posting|S|
|FR-13|Dashboard|Show mission status, coverage %, inventory record<br>accuracy (IRA) and open discrepancies by zone|M|
|FR-14|Reporting|Export cycle-count, discrepancy and accuracy-<br>trend reports to Excel / PDF|M|
|FR-15|Alerts|Notify by email / Teams when a mission fails,<br>coverage drops below threshold or high-value<br>discrepancies appear|S|



Page 3 of 17 

Drone-Based Inventory Management Application — Technical Documentation 

|ID|Module|Requirement|Priority|
|---|---|---|---|
|FR-16|Master data|Maintain warehouse layout (zones, aisles, racks,<br>bins), SKU master sync and threshold settings|M|
|FR-17|Admin|Manage users, roles, sites and integration<br>credentials|M|
|FR-18|Audit|Record every change to counts, cases and settings<br>with user and time|M|



User roles: **Admin** (configuration, users), **Inventory controller** (reviews and approves discrepancies), **Warehouse supervisor** (views missions, assigns recounts), **Viewer / auditor** (read-only reports), and a **System integration account** for the receiving system. 

## 4. Non-functional requirements 

A full mission must be reconciled and visible on the dashboard within 15 minutes of the last payload arriving. Targets below are starting values to agree with the client. 

|Area|Target|
|---|---|
|Ingestion throughput|200 scan events/s sustained; 50 image uploads/s<br>with object storage|
|Processing latency|Mission of 5,000 bins reconciled in ≤ 15 min; single-<br>bin recompute ≤ 5 s|
|API response|p95 ≤ 500 ms for UI reads; ≤ 2 s for report<br>generation start|
|Availability|99.5% monthly for ingestion and UI; ingestion<br>buffered so no data is lost during downtime|
|Scalability|Horizontal scaling of API and workers; multi-<br>warehouse, multi-tenant ready (site ID on every<br>record)|
|Data retention|Scan data 2 years; images 90 days hot, then archive<br>tier; audit logs 7 years (configurable)|
|Count accuracy|Target IRA reporting ≥ 98% agreement with manual<br>recount on pilot zones|
|Security|TLS 1.2+, encryption at rest, RBAC, SSO (OIDC),<br>OWASP ASVS L2|



Page 4 of 17 

Drone-Based Inventory Management Application — Technical Documentation 

|Area|Target|
|---|---|
|Auditability|Immutable audit trail for counts, cases,<br>adjustments and configuration|
|Usability|Responsive web UI; tablet use on the warehouse<br>floor; English first, i18n-ready|
|Maintainability|≥ 80% unit-test coverage on processing and<br>reconciliation logic; versioned APIs and schemas|



## 5. High-level architecture 

The application is a set of containerised services around a message queue: the gateway only validates and stores, workers do all processing, and the API serves the UI from processed results. 



<!-- Start of picture text -->
Drone data is queued, processed and reconciled before anyone sees it<br>Dashed: external systems : shaded: our application - accent: core processing<br>DroneExternal: datascans, receivingtelemetry, system images WMSExternal:/ ERP. book stock, SKU master<br>push, file or pull Inventory application (our scope) stock in, adjustments out<br>Ingestion gateway ERP connector<br>REST push, file drop or scheduled pull Book-stock snapshot and SKU master syne<br>Schema checks, idempotency, rate limits Posts approved stock adjustments<br>Message queue + dead-letter Data stores<br>Redis or RabbitMQ; Kafka at high volume PostgreSQL + PostGIS: missions, counts, cases<br>Object storage: raw payloads and images<br>Processing workers Application API (FastAPI)<br>1. Decode and normalise codes (GS1, EPC) REST /api/v1 with OpenAPI and RBAC<br>2. Map scans to bins (label, then telemetry) Report jobs and live progress (WebSocket)<br>3. Deduplicate, count, score confidence<br>4, Reconcile against book-stock snapshot<br>5. Open cases, update KPls, send alerts<br>Identity provider Web UI (React)<br>SSO (OIDC) for users and system accounts Dashboard, missions, rack map, cases, reports<br><!-- End of picture text -->

application architecture · 2 external feeds, 6 internal components 

Page 5 of 17 

Drone-Based Inventory Management Application — Technical Documentation 

Because raw payloads are stored before processing, any stage can be replayed after a fix or a threshold change without flying the mission again. 

## 6. Data ingestion and integration design 

All inbound data lands in one ingestion gateway that validates, stores the raw payload, and queues it for processing; nothing is processed synchronously in the request. Three channels are supported so we can match whatever the receiving system offers. 

|Channel|Mechanism|When to use|
|---|---|---|
|REST push<br>(preferred)|`POST /ingest/v1/...`with API<br>key or OAuth2 client credentials;<br>batches of up to 1,000 events|Receiving system can call HTTPS<br>endpoints in near real time|
|File drop|Receiving system uploads<br>ZIP/CSV/JSON + images to an S3<br>bucket or SFTP folder; object-<br>created event triggers ingestion|Batch upload after the drone<br>lands|
|Scheduled pull|Our connector polls the receiving<br>system's API or database view<br>every N minutes|Receiving system cannot push|
|WMS/ERP<br>connector|REST/OData API or nightly CSV<br>export of book stock and SKU<br>master|Reference data for reconciliation|



Inbound endpoints: 

Page 6 of 17 

Drone-Based Inventory Management Application — Technical Documentation 

|Endpoint|Purpose|
|---|---|
|`POST /ingest/v1/missions`|Register or update a mission (start,<br>end, status)|
|`POST /ingest/v1/missions/{missionId}/scans`|Batch of scan events|
|`POST`|Batch of position frames|
|`/ingest/v1/missions/{missionId}/telemetry`||
|`POST`|Get pre-signed URLs to upload|
|`/ingest/v1/missions/{missionId}/images:presi`<br>`gn`|images directly to object storage|
|`POST`|Signal end of mission; triggers final|
|`/ingest/v1/missions/{missionId}/complete`|reconciliation|



### Scan event schema (v1): 

```
{
  "schemaVersion": "1.0",
  "missionId": "MSN-2026-10-09-WH01-003",
  "eventId": "7b1e0c2a-4f8d-4a51-9a3e-1c2d3e4f5a6b",
  "droneId": "DR-07",
  "timestamp": "2026-10-09T05:42:17.315Z",
  "readType": "BARCODE",
  "symbology": "GS1-128",
  "value": "(01)08901234567890(10)LOT2409(21)SN000123",
  "confidence": 0.94,
  "locationTag": "WH01-A12-R03-L2-B04",
  "position": { "x": 34.2, "y": 118.6, "z": 4.1, "frame": "WH01" },
  "imageRef": "s3://drone-raw/WH01/MSN-.../frame_004211.jpg",
  "bbox": [412, 230, 588, 310]
}
```

### Validation and reliability rules: 

JSON Schema validation per `schemaVersion` ; unknown versions go to quarantine, not to processing. 

- `eventId` is the idempotency key; duplicates return `200` with `duplicate: true` and 

- are not re-queued. 

- Responses: `202 Accepted` for queued batches, `207 Multi-Status` listing rejected records with reasons, `401/403` for auth, `413` for oversized batches, `429` with `RetryAfter` for rate limiting. 

Page 7 of 17 

Drone-Based Inventory Management Application — Technical Documentation 

- Raw payloads are stored unchanged in object storage (bronze layer) for replay and audit. 

- Failed processing goes to a dead-letter queue with alerting; operators can replay from the UI. 

## 7. Processing and reconciliation pipeline 

Each mission flows through seven stages run by queue workers; every stage writes its output so any stage can be re-run without repeating the drone flight. 

1. **Validate and persist** — schema check, store raw payload, write clean rows to the staging tables (silver layer). 

2. **Decode and normalise** — parse GS1 application identifiers (01 GTIN, 10 lot, 17 expiry, 21 serial), map GTIN/EPC to internal SKU through the SKU master; unknown codes are kept as `UNKNOWN_ITEM` . 

3. **Location mapping** — primary: nearest preceding location-label read in the same rack face within a time window (default 3 s); fallback: telemetry position mapped to bin polygons from the layout model; result carries the method used. 

4. **Deduplication** — collapse reads with the same item key (serial, or SKU + lot + bbox cluster) in the same bin within a mission; keep the highest-confidence read. 

5. **Bin count and confidence** — count = distinct items per bin per SKU/lot. Bin confidence combines read confidence, location-mapping method and image coverage (formula below); bins below the threshold (default 0.80) are flagged for review. 

6. **Reconciliation** — compare counted vs book stock (snapshot taken at mission start) per site, bin, SKU and lot, and classify the result. 

7. **Publish** — write results (gold layer), open discrepancy cases, update dashboard aggregates, send alerts. 

Bin confidence: 

```
C_{bin} = w_1 \cdot \overline{c}_{read} + w_2 \cdot m_{loc} + w_3 \cdot
r_{coverage}, \quad w_1 + w_2 + w_3 = 1
```

Here average read confidence, location method score (1.0 for label, 0.7 for telemetry) and the share of the bin's face captured in images are weighted; default weights are 0.5, 0.3 and 0.2, tuned during the pilot. 

Reconciliation outcomes: 

|Outcome|Rule|Default action|
|---|---|---|
|Match|Counted = book for SKU/lot in bin|None|



Page 8 of 17 

Drone-Based Inventory Management Application — Technical Documentation 

|Outcome|Rule|Default action|
|---|---|---|
|Shortage|Counted < book|Case if variance value ><br>threshold|
|Excess|Counted > book|Case if variance value ><br>threshold|
|Misplaced|SKU found in bin B but booked only in bin<br>A|Case; suggest transfer|
|Unknown item|Code not in SKU master|Case for master-data team|
|Empty<br>mismatch|Book says empty, items seen (or reverse)|Case|
|Not scanned|Bin in mission plan with no reads or<br>confidence < threshold|Recount task|



Inventory record accuracy is reported as the share of scanned bins with outcome Match. The CV re-decoding step (FR-08) is an optional plug-in between stages 2 and 3, using a barcode/label detection model on unread image regions. 

## 8. Data model 

PostgreSQL holds structured data in three layers (staging, core, reporting); images and raw payloads stay in object storage and are referenced by key. Every table carries `site_id` , `created_at` and `updated_at` . 

|Table|Key columns|Notes|
|---|---|---|
|`site`|site_id, name, timezone|One per warehouse|
|`location`|location_id, site_id, zone, aisle,<br>rack, level, bin, label_code,<br>polygon (PostGIS)|Warehouse layout; polygon<br>used for telemetry mapping|
|`sku`|sku_id, gtin, epc_prefix,<br>description, uom, unit_value|Synced from ERP|
|`drone`|drone_id, model, sensor_type|Reference only|
|`mission`|mission_id, site_id, drone_id,<br>planned_zone, started_at,<br>ended_at, status, coverage_pct|Status: RECEIVING →<br>PROCESSING →<br>RECONCILED / FAILED|



Page 9 of 17 

Drone-Based Inventory Management Application — Technical Documentation 

|Table|Key columns|Notes|
|---|---|---|
|`raw_payload`|payload_id, mission_id, channel,<br>object_key, schema_version,<br>received_at, status|Bronze layer pointer|
|`scan_event`|event_id (PK), mission_id, ts,<br>read_type, symbology,<br>raw_value, confidence,<br>location_tag, x, y, z, image_key,<br>bbox|Staging; partitioned by month|
|`scan_item`|scan_item_id, event_id, sku_id,<br>lot, serial, expiry, location_id,<br>map_method, is_duplicate|Decoded and mapped read|
|`bin_count`|mission_id, location_id, sku_id,<br>lot, counted_qty,<br>bin_confidence|Result of stage 5|
|`book_snapshot`|mission_id, location_id, sku_id,<br>lot, book_qty, snapshot_at|ERP stock at mission start|
|`recon_result`|mission_id, location_id, sku_id,<br>lot, counted_qty, book_qty,<br>variance_qty, variance_value,<br>outcome|Gold layer|
|`discrepancy_case`|case_id, recon_result_id,<br>status, assignee, priority,<br>resolution, approved_by,<br>approved_at|Workflow|
|`case_comment`|comment_id, case_id, user_id,<br>body, created_at|Discussion and evidence|
|`adjustment`|adjustment_id, case_id, sku_id,<br>location_id, qty, erp_ref,<br>posted_status|Proposed / posted to ERP|
|`app_user`,<br>`role`,<br>`user_role`|—|RBAC; identity from SSO|
|`audit_log`|audit_id, entity, entity_id,<br>action, before, after (JSONB),<br>user_id, ts|Append-only|
|`setting`|site_id, key, value|Thresholds, weights, retention|



Page 10 of 17 

Drone-Based Inventory Management Application — Technical Documentation 

Relationships: a mission has many scan events → scan items → bin counts; each recon result may open one discrepancy case, which may produce one adjustment. 

## 9. API specification (application APIs) 

The UI and any external consumers use a versioned REST API under `/api/v1` , documented with OpenAPI 3 and secured with OIDC bearer tokens. Lists support `page` , `pageSize` , `sort` and filter parameters. 

|Method|Endpoint|Purpose|Roles|
|---|---|---|---|
|GET|`/missions`|List missions by site, date,<br>status|All|
|GET|`/missions/{id}`|Mission summary:<br>coverage, IRA, counts by<br>outcome|All|
|POST|`/missions/{id}/reprocess`|Re-run pipeline from a<br>chosen stage|Admin,<br>Controller|
|GET|`/missions/{id}/bins`|Bin-level counts with<br>confidence|All|
|GET|`/missions/{id}/recon-results`|Reconciliation rows; filter<br>by outcome, zone, SKU|All|
|GET|`/bins/{locationId}/history`|Count and variance<br>history of a bin|All|
|GET|`/discrepancies`|Case list with filters|All|
|PATCH|`/discrepancies/{id}`|Assign, change status, set<br>resolution|Controller,<br>Supervisor|
|POST|`/discrepancies/{id}/approve`|Approve and create<br>adjustment|Controller|
|POST|`/discrepancies/{id}/comments`|Add comment|Controller,<br>Supervisor|
|GET|`/images/{key}`|Short-lived signed URL for<br>evidence image|All|
|POST|`/adjustments/{id}/post`|Post adjustment to ERP|Controller|



Page 11 of 17 

Drone-Based Inventory Management Application — Technical Documentation 

|Method|Endpoint|Purpose|Roles|
|---|---|---|---|
|GET|`/dashboard/kpis`|IRA, coverage, open<br>cases, variance value by<br>site and period|All|
|POST|`/reports`|Start report job (type,<br>filters, format)|All|
|GET|`/reports/{jobId}`|Job status and download<br>link|All|
|GET/PUT|`/settings`|Thresholds, weights,<br>retention|Admin|
|CRUD|`/locations`,<br>`/skus`,<br>`/users`|Master data and user<br>management|Admin|



Error format follows RFC 7807 ( `application/problem+json` ). Long-running actions (reprocess, reports, ERP posting) return `202` with a job ID; the UI receives progress through WebSocket or polling. 

## 10. Frontend modules 

A single-page React application, responsive for desktop and tablet, with seven screens. 

|Screen|What the user sees and does|
|---|---|
|Dashboard|KPI tiles (IRA, coverage, open cases, variance<br>value), accuracy trend, zone heatmap of<br>discrepancies, recent missions|
|Missions|Mission list with status; detail view with pipeline<br>progress, coverage map and outcome breakdown;<br>reprocess action|
|Warehouse map|2D rack-face view per aisle; bins coloured by<br>outcome and confidence; click a bin for counts,<br>book stock and images|
|Discrepancies|Work queue with filters; case detail with image<br>evidence (bounding boxes overlaid), history,<br>comments, approve / reject / recount|



Page 12 of 17 

Drone-Based Inventory Management Application — Technical Documentation 

|Screen|What the user sees and does|
|---|---|
|Reports|Pre-built reports (cycle count, discrepancy, aging,<br>accuracy trend) with Excel / PDF export and<br>scheduling|
|Master data|Layout import (CSV), SKU sync status, unknown-<br>code mapping|
|Administration|Users and roles, thresholds and weights,<br>integration keys, ingestion monitor and dead-letter<br>replay|



## 11. Security, access control and audit 

Users sign in through the client's identity provider (OIDC / SAML via Keycloak or Azure AD); machines authenticate with OAuth2 client credentials or scoped API keys. 

|Control|Implementation|
|---|---|
|Authentication|OIDC SSO with MFA for users; client-credentials<br>tokens for the receiving system and ERP connector|
|Authorisation|RBAC per role (section 3) plus site scoping,<br>enforced in the API layer|
|Transport|TLS 1.2+ everywhere; optional IP allow-list or mTLS<br>for the ingestion endpoint|
|Data at rest|Database and object storage encrypted (AES-256,<br>KMS-managed keys)|
|Images|Private bucket; access only through signed URLs<br>valid ≤ 10 min|
|Secrets|Vault / cloud secrets manager; no secrets in code<br>or images|
|Input safety|Schema validation, size limits, rate limiting,<br>parameterised queries|
|Audit|Append-only<br>`audit_log`for logins, case actions,<br>adjustments, settings; exportable for auditors|
|Vulnerability management|SAST, dependency and container scanning in CI;<br>annual penetration test|



Page 13 of 17 

Drone-Based Inventory Management Application — Technical Documentation 

|Control|Implementation|
|---|---|
|Privacy|Images may capture people on the floor; blur faces|
||before storage if the client requires it|



## 12. Technology stack and deployment 

The recommended stack is Python (FastAPI) on the backend, React on the frontend, PostgreSQL with PostGIS, and containers on Kubernetes; it runs on cloud or on-premises with the same images. 

Page 14 of 17 

Drone-Based Inventory Management Application — Technical Documentation 

|Layer|Choice|Reason|
|---|---|---|
|API and<br>ingestion|Python 3.12, FastAPI, Pydantic v2|Fast schema validation; same<br>language as the data/CV work|
|Workers|Celery or Dramatiq on Redis /<br>RabbitMQ (Kafka if > 1,000<br>events/s)|Stage-wise, retryable processing|
|Database|PostgreSQL 16 + PostGIS;<br>TimescaleDB optional for telemetry|Relational integrity plus spatial bin<br>mapping|
|Object storage|AWS S3 / Azure Blob / MinIO on-<br>prem|Images and raw payloads|
|Barcode / CV|zxing-cpp, pyzbar; YOLO-based<br>label detector (optional)|Decoding and re-decoding from<br>images|
|Frontend|React + TypeScript, Ant Design or<br>MUI, ECharts, Konva for the rack<br>view|Data-heavy UI and interactive<br>warehouse map|
|Reporting|openpyxl / WeasyPrint for exports;<br>optional Power BI on the reporting<br>schema|Client-friendly outputs|
|Identity|Keycloak or the client's Azure AD|SSO, RBAC|
|Containers|Docker, Kubernetes (EKS/AKS or<br>k3s on-prem), Helm|Portable deployment and scaling|
|CI/CD|GitHub Actions or GitLab CI; Argo<br>CD for deployment|Automated build, test, scan,<br>release|
|Observability|OpenTelemetry, Prometheus,<br>Grafana, Loki; Sentry for errors|Metrics, logs, traces, alerts|



Environments: **dev** (synthetic mission data generator), **staging** (connected to the receiving system's test feed and an ERP sandbox), **production** . Databases are backed up daily with point-in-time recovery; target RPO 15 min, RTO 4 h. 

Key monitoring metrics: ingestion rate and rejects, queue depth and age, stage duration per mission, dead-letter count, ERP connector errors, API latency and error rate. 

Page 15 of 17 

Drone-Based Inventory Management Application — Technical Documentation 

## 13. Testing, delivery, risks and open questions 

Testing relies on a synthetic mission generator that produces scans, telemetry and images with known ground truth, so accuracy can be measured before real drone data arrives. 

|Test level|Focus|
|---|---|
|Unit|GS1 parsing, location mapping, deduplication,<br>confidence, reconciliation rules|
|Contract|Ingestion schemas against sample payloads from<br>the receiving system; ERP connector mocks|
|Integration|End-to-end mission: ingest → reconcile → case →<br>adjustment in staging|
|Performance|5,000-bin mission within 15 min; 200 events/s<br>sustained (k6 / Locust)|
|Accuracy|Pilot zones: drone count vs manual recount, target<br>≥ 98% agreement|
|Security|SAST/DAST, role-permission matrix tests,<br>penetration test before go-live|
|UAT|Inventory controllers run real missions and resolve<br>cases|



### Delivery phases: 

1. **Discovery and integration contract** — confirm data formats, channels and ERP access with the receiving-system owner and client. 

2. **MVP** — ingestion, decoding, label-based mapping, reconciliation, mission and discrepancy screens, basic reports. 

3. **Pilot** — one warehouse zone; tune thresholds and confidence weights; measure accuracy. 

4. **Hardening** — ERP posting, alerts, warehouse map, performance and security testing. 

5. **Rollout and enhancements** — all zones / sites; optional CV re-decoding and Power BI. 

|Risk|Impact|Mitigation|
|---|---|---|
|Receiving-system format|Ingestion breaks|Versioned schemas, contract|
|changes||tests, quarantine|
|Poor label readability|Low counts, many false|Confidence flags, image|
|(damage, angle, glare)|shortages|evidence, CV re-decoding|



Page 16 of 17 

Drone-Based Inventory Management Application — Technical Documentation 

|Risk|Impact|Mitigation|
|---|---|---|
|No location labels; telemetry<br>drift|Wrong bin assignment|Fiducial markers on racks;<br>tolerance zones; review queue|
|Book stock changes during<br>flight|False variances|Snapshot at mission start;<br>exclude bins with movements<br>during the window|
|ERP API limits or no write<br>access|Manual adjustment<br>posting|Export file fallback|
|Large image volumes|Storage cost, slow UI|Thumbnails, lifecycle tiering, lazy<br>loading|



### Open questions: 

- Which channel does the receiving system support: push API, file drop or pull? Sample payloads and images from at least one real mission 

- Read technology: barcode, RFID or both; are pallet and case labels GS1-compliant? 

- Do racks carry location labels, or must we rely on coordinates? 

- Which WMS/ERP, and do we get read and write API access? 

- Cloud (which provider) or on-premises hosting? 

- Variance value thresholds and approval levels for adjustments 

- Number of sites, missions per day and users at go-live 

Page 17 of 17 

