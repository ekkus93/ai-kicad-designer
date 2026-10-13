# M2h2 exact-source qualification after diagnostic-report update (2026-10-13)

**Status: THREE FIVE-RUN LOCKED-KICAD SUITES REQUESTED — NOT YET QUALIFIED OR AESTHETICALLY ACCEPTED.**

The earlier exact behavior source `b8a69cc9b57750b2758ebf1b187fccd2ba443b7c` passed base 56×5/V3-8-negative [38462094064](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38462094064), I1–I6×5 [38462094056](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38462094056) and structural×5 [38462094429](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38462094429), with original locked KiCad toolchain [38462094273](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38462094273) PASS.

Follow-up `204721d119451bc7b66a98b86905ebb7aa9542f6` added source-neutral measured route-geometry diagnostics and regressions (`src/ai_kicad/m2_composition_tradeoff_report.py`, `tests/test_m2_composition_tradeoff_report.py`) and expanded generic source-neutral development probes (V4/V6, shared-rail, passive fanout). The [development probe 38466268895](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38466268895) PASSED.

The [previous audit request 38466888229](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38466888229) and [inventory 38466888046](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38466888046) **FAILED exact-source identity checking**, correctly rejecting the newer diagnostic module SHA against the older `b8a69cc9` qualification root. This is a source-provenance mismatch, not a waiverable observation or a KiCad structural failure. No source hash checks, frozen tolerances or historical evidence are relaxed.

This **documentation-only** descendant requests three complete fresh locked-KiCad 10.0.6 five-run suites for the current exact `master` source, including all updated `src/ai_kicad` module hashes:

1. 56 positive base cases ×5 plus original V3-8 negative.
2. All I1–I6 interactions ×5.
3. All required nine structural classes ×5.

After all three PASS, use their single exact qualification SHA and its persisted `$HOME/m2h2-evidence/<qualification-sha>/` root for new source-matched independent historical 90-case comparison and normalized 137-case×5 native SVG inventory. Confirm native base/structural transfer; then expand engineering visual inspection to every distinct case. Any further behavior or report module change invalidates the exact-source qualification and requires requalification. Until positive evidence closes all frozen visual criteria, TODO sections 15–21 stay unchecked and overall status is **INCOMPLETE**.
