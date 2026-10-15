# Cross-track source independent qualification follow-up — 2026-10-15

**Exact qualification source:** `91bf253f718f082359374fb04f0918e37749ca7f` on `master`. This commit is documentation-only and does not change the behavior under independent comparison.

The new bounded generic interior cross-track routing candidates were introduced in `0220f250c32b06fbaa1b78dca1088e9d41318503`. Exact-source locked KiCad 10.0.6 qualifications now **PASS**:
- 56 base cases × five runs, including the historical V3-8 negative: [Final Qualification 38732857698](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38732857698).
- I1–I6 interaction cases × five runs: [Final Interactions 38732857751](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38732857751).
- Nine structural classes × five runs: [Structural Qualification 38732857721](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38732857721).
- Locked toolchain identity: [Diagnostic 38732857740](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38732857740).
- Source-matched base native render transfer: [Base Render Audit 38736810047](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38736810047).

This checkpoint **requests, but does not pre-accept**, two independent audits from the same preserved `$HOME/m2h2-evidence/91bf253f718f082359374fb04f0918e37749ca7f/` root: (1) the frozen historical 90-case comparative artifact audit, and (2) the 137-case × five-run normalized native KiCad render inventory. These are triggered by the exact-source commit-message markers; neither uses the documentation descendant as the qualification source.

The previous independent audit of source `20ca22ccd0349f33cdbcd9bd32dda78af7b25d8c` ([run 38729570577](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38729570577)) **FAILED five frozen criteria**: hard-defect closure, individual hard-defect nonworsening, routing aesthetics, repeated-structure tolerance, and `i4__b2_mixed` improvement. It found shared-rail local-label disconnections, V4-7 and V6-3 wrong-side interfaces, excess U-detours, and repeated-branch inconsistency. Those failures remain open until source-matched independent evidence proves otherwise. Case-by-case engineering native-render inspection and TODO sections 15–21 remain open. Do not weaken observers, historical evidence, hard gates, or acceptance tolerances.
