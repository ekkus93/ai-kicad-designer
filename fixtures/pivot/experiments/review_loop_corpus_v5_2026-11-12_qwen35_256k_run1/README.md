# Review-loop corpus under brief v5 (2026-11-12)

This is `tools/pivot/run_review_loop_corpus.py` at `63d71dc2`, run with brief v5 (`fixtures/pivot/schematic_review_brief_v5.json`), on `qwen35-256k:latest` with a 262144-token context and a 2048-token output cap. The host was Linux with KiCad 10.0.6 via `/tmp/AppDir/AppRun`. It is not the locked qualification host (`locked_host_qualification: false`).

**Purpose:** the first model review of the drawings centred on the page (`page_centring_2026-11-12_run1`).

**Results:**
- 15/15 designs accepted, each on its first review. No reply was rejected and no edit was requested.
- Every check passes, including the three v4 gates and `page_balance`.
- With UUIDs stripped, every accepted drawing is identical to its drawing in `page_centring_2026-11-12_run1`, so it is the v4 accepted drawing translated to the page centre.
- Reviews took 6.6–9.5 s each, 111 s in total, and 10–15k tokens per design.
- The model raised no issues. Its rationales are generic (for example, "balanced page composition"), so the acceptance shows only that the model does not object to the centred page. It is not an independent check of composition.

**Still pending:** the independent readability assessment and human electrical review (`summary.json`), minimum page fill for small circuits, and the text-association defects (R1/R2 text by the wrong part, led_series detached value).
