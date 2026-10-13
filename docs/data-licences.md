# DRIMS public-data licences

## Amazon Bin Image Dataset

- Source: <https://registry.opendata.aws/amazon-bin-imagery>
- Storage: `s3://aft-vbi-pds`, anonymous public access, `us-east-1`
- Licence: Creative Commons Attribution-NonCommercial-ShareAlike 3.0 United States (CC BY-NC-SA 3.0 US)
- Use restriction: development, testing, and demo only. This dataset must never be shipped in a commercial DRIMS release.
- The requested documentation URL `https://docs.opendata.aws/aft-vbi-pds/readme.html` returned HTTP 404 during acquisition and is recorded as a blocker.

## Barcode sources

### ArTe-Lab 1D barcode dataset no. 1

- Source archive: <https://artelab.dista.uninsubria.it/downloads/datasets/barcode/hough_barcode_1d/1d_barcode_hough.zip>
- Acquisition: manually downloaded and extracted by the user; the loader does not download or unzip it.
- Citation: Zamberletti, Gallo and Albertini, "Robust Angle Invariant 1D Barcode Detection", ACPR 2013.
- Licence: licence not stated on the source page; evaluation use only; do not redistribute.
- Contents: original/edge/Hough-derived images, detection outputs, masks, and train/test image splits. Decoder evaluation must use only full-photo files from the test split; masks and Hough-space outputs are not barcode-decoding inputs.
- Decoder result for this extracted folder: NOT APPLICABLE. Pillow inspection shows the train/test files are single-channel 904x180 or 916x180 barcode patches, while the original/detection files are derived edge/Hough/mask outputs; no full colour barcode photographs are present in the supplied folder. Use dataset no. 2 (`1d_barcode_extended.zip`, or `1d_barcode_extended_plain.zip`) for photo-based decoder evaluation.

Previously inspected barcode sources were not loaded: the ArTe-Lab page did not expose a verified licence for the archive, the Muenster URL returned a research index without a BarcodeDB download/licence, the DEAL URL redirected to a KAIST page pointing to Zenodo rather than the requested archive, and the BarBeR PDF returned HTTP 403.
