# Review-loop corpus under brief v7 (2026-11-12)

This is `tools/pivot/run_review_loop_corpus.py` at `a2c7d198`, run with brief v7 (`fixtures/pivot/schematic_review_brief_v7.json`), on `qwen35-256k:latest` (digest `b528609af3c0`, the reviewer used in the earlier runs) with a 262144-token context and a 2048-token output cap. The host was Linux with KiCad 10.0.6 via `/tmp/AppDir/AppRun`. It is not the locked qualification host (`locked_host_qualification: false`).

This is run2. run1 (`review_loop_corpus_v7_2026-11-12_qwen35_256k_run1`) recorded TOOL_ERROR for every design, because the reviewer model had been removed from Ollama by the reboot. It is left untracked and not used.

**Results:**
- 15/15 designs accepted, each on its first review. No replies were rejected and no edits were requested.
- With UUIDs stripped, 14 accepted drawings are identical to `page_centring_2026-11-12_run1`.
- inverting_gain differs: its U1C label moved beside the pin column under v7 (see `text_and_ground_v7_2026-11-12_run1`).
- The model's rationales are generic. As in the v5 run, the acceptance does not independently show the layout is good.

**Still pending:** the independent readability assessment and human electrical review (`summary.json`), minimum page fill for small circuits, and the own-wiring loops that v7 does not measure.
