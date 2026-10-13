# M2h2 native engineering review — 2026-10-13

Status: **PARTIAL NATIVE INSPECTION; FROZEN COMPARATIVE ACCEPTANCE FAILED**.

Qualified production/evidence source: `54eeb3c66112448c46eaaea9bd68ec0bd8941b35`.
Preserved evidence: `$HOME/m2h2-evidence/54eeb3c66112448c46eaaea9bd68ec0bd8941b35/`.
Locked KiCad 10.0.6 five-run base, I1–I6, and structural qualification: runs
38373962344, 38373962280, and 38373962437 — **PASS**.
[Independent 90-case historical audit](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38379445241) — **FAIL** on five frozen criteria.
[137-case normalized five-run native-render inventory](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38379445528) — **PASS**.
Neither source qualification nor normalized reproducibility establishes aesthetic acceptance.

## Verified native inspection: `i4__b2_mixed`

[Native KiCad SVG-derived PNG transfer](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38379954922) succeeded. The independent inspection, SHA-256 provenance, qualitative observations, and case-level quantitative falsification are recorded in
[`docs/M2H2_I4_B2_MIXED_NATIVE_VISUAL_INSPECTION_2026-10-13.md`](M2H2_I4_B2_MIXED_NATIVE_VISUAL_INSPECTION_2026-10-13.md).
This is **one** native case, not an all-case engineering review. In particular, J4 remains on the upper output row while its R3 final producer is on the lower branch. The avoidable-looking return jog is a routing-aesthetic concern, not an electrical defect.

The source-matched historical comparison confirms `i4__b2_mixed` hard defects **4→0**, but fragmentation **73.6602→99.0602 mm**, U-detours **2→6**, and branch inconsistency **21.59→29.21 mm** all worsen. The `i4_specific_improvement` criterion therefore fails.

## Independent full-corpus audit

All 90 historical cases were compared against the exact qualified source, with no missing cases. Stage inversions **1→0**, interface-side violations **77→44**, functional fragmentation **14743.4342→14674.8561 mm**, and edge-biased cases **64→53** improve. U-detours **691→858** and branch inconsistency **1529.08→1714.5 mm** regress.

The failed frozen criteria are `baseline_hard_defects_cleared`,
`individual_hard_defects_never_worsen`, `routing_aesthetics_nonworsening`,
`repeated_structure_within_frozen_tolerance`, and `i4_specific_improvement`.
Concrete per-case hard regressions include shared-rail `base__m2f2-two_signal_chains_shared_rail` (local label disconnects **1→2**) and `base__v6-3` (interface-side violations **0→1**). These remain actionable falsification targets.

## Generic candidate tradeoff: mixed-output row locality

The [source-matched generic development probe](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38373962147) records selected seed 4, round 0, versus a legal proved seed 1, round 0. Both have zero stage inversions, reversal distance, interface-side violations, and interface-owner distance. The alternative reduces directed-output row drift **68→28** and routed union length **335.28→287.02 mm**, but worsens frontier distance **46→61** and route backtracking **78→88**. The production lexicographic selection therefore favors seed 4, which has better higher-priority frontier/backtracking evidence. This is a **diagnosis**, not proof that seed 1 passes the independent visual observer or is an acceptable production replacement. Generic candidate tradeoff reporting now exposes signed metric deltas without modifying selection or frozen thresholds.

The next production experiment should determine whether bounded, source-neutral lower-right output placements can improve row ownership *without* sacrificing higher-priority flow, frontier, and route obligations. Test renamed/permuted multi-output archetypes and the independent full corpus; do not special-case J4, R3, net names, or `i4__b2_mixed`.

## Inspection accounting

- [x] Confirm native SVG identity/hash and exact five-run source provenance for the inspected mixed case.
- [x] Inspect signal entry, direction, and ownership of both output interfaces in the mixed case.
- [x] Inspect mixed-case fanout geometry and avoidable U-detours or dominant empty areas.
- [x] Inspect mixed-case support, labels, whitespace, and visual traceability.
- [x] Record mixed-case current-source observer metrics and native-preview observations without waivers.
- [ ] Expand native engineering inspection to **every distinct governed case**, including dense, repeated, feedback, shared-rail, and structural-band cases.
- [x] Compare all 90 historical cases independently without relaxing frozen tolerances (**audit performed; criteria failed**).
- [ ] Resolve every frozen comparative failure with source-matched positive evidence and re-run final qualification.

No overall visual PASS, source freeze, or sections 15–21 closure is claimed. Frozen tolerances and historical evidence remain unchanged.
