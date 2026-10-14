# M2H2 Gateway-Median Independent Audit Request — 2026-10-13

This documentation-only checkpoint requests an independent frozen historical 90-case composition comparison against exact persisted qualification source `2b28f3d3535b6acf4296b310d701269a6e648c84`.

The exact source completed the three required locked-KiCad 10.0.6 five-run qualification suites: base 56 positives and V3-8 negative (run 38510201425), I1–I6 (run 38510201373), and nine structural classes (run 38510201351). The source-matched base/structural render transfers also passed (runs 38511684094 and 38513117316). Its Fast Validation static job failed solely because Ruff requested a formatting change to the gateway-row median test; this was corrected without production behavior changes in descendant `bc7d2a72d5d8198ddf3738579c8f6f9cda1029f0` and its exact-head Fast Validation has now passed (run 38514307703).

This request does not claim visual acceptance. Preserve the frozen historical corpus, independent observer thresholds, locked KiCad hashes, all previous evidence and open TODO sections 15–21. Review the independent audit results before any new acceptance claim.

## Independent results — 2026-10-13

- Exact-source [Fast Validation run 38514307703](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38514307703) **PASSED all three jobs** after the test-only Ruff correction; no production routing behavior changed.
- [90-case historical comparative audit run 38514307722](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38514307722) **FAILED** five unchanged frozen criteria: baseline hard-defect closure, individual hard-defect nonworsening, routing aesthetics, repeated-structure tolerance, and mixed-output improvement. It covered all 90 cases. This is an acceptance failure, not a CI infrastructure failure.
- [137-case normalized native-render inventory run 38514307692](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38514307692) **PASSED**. Reproducibility is not visual acceptance.

| Metric | Historical | Qualified gateway-median source |
| --- | ---: | ---: |
| Stage-order inversions | 1 | 0 |
| Interface-side violations | 77 | 44 |
| Functional fragmentation | 14,743.4342 mm | 14,677.3962 mm |
| Edge-biased cases | 64 | 55 |
| U-shaped detours | 691 | 865 |
| Branch inconsistency | 1,529.08 mm | 1,758.95 mm |

The gateway-median strategy did **not** improve the frozen comparative totals relative to the preceding independently audited routing source. Specific regressions persist: shared-rail local label disconnects 1→2, V6-3 interface-side violations 0→1, and `i4__b2_mixed` U-detours 2→7 with persistent page edge bias. No acceptance criterion, baseline, observer tolerance, KiCad identity, or TODO section 15–21 checkbox is relaxed.

The development probe now emits a bounded per-net route-strategy inventory to determine whether the new trunk is selected and to focus the next generic routing remediation on proven candidate/geometry deficiencies. This additional diagnostic does not modify production routing or claim aesthetic improvement.
