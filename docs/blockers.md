# DRIMS data blockers

- Client-only data is not public and must be supplied by the client: real drone mission payloads, real ERP/WMS book stock, production SKU master, warehouse layout/location labels, GS1-labelled item data, and production variance thresholds.
- Amazon Bin Image Dataset metadata and images are non-commercial CC BY-NC-SA 3.0 US data. They are allowed only for development, testing, and demo fixtures and must be excluded from production reports.
- The Amazon documentation URL returned HTTP 404 during acquisition.
- The user supplied and extracted ArTe-Lab dataset no. 1 locally. Its source page does not state a licence; it is recorded as evaluation use only and must not be redistributed. The supplied folder contains patches and derived Hough/mask outputs, not full-photo decoder inputs. Dataset no. 2 (`1d_barcode_extended.zip` or `1d_barcode_extended_plain.zip`) is still required for photo-based decoder evaluation.
- The supplied Muenster BarcodeDB homepage returned an unrelated research index without a verified download or licence.
- DEAL redirected to a KAIST page referencing Zenodo; the requested archive and licence were not downloaded.
- The BarBeR paper URL returned HTTP 403. No workaround was attempted.
- Synthetic generation remains blocked until a real ingestion endpoint and database `data_source` migration are added; no direct database writes or mock production records were used.
