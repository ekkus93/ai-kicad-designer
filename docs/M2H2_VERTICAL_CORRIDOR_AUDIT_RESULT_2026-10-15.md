# M2h2 vertical-corridor independent audit result — 2026-10-15

Qualification source: `31c82669f5514d182ebad6fd6f28ca59a77689a4`.
Audit trigger: `3b135ec52abf5a2f26a133d713aa40d2f680d57c`.
Independent historical audit: https://github.com/ekkus93/ai-kicad-designer/actions/runs/38703218640 — **FAIL**, five frozen criteria.

All 90 preserved baseline cases were covered. Historical to current:
- Stage inversions: 1 to 0.
- Interface-side violations: 77 to 48.
- Functional fragmentation: 14743.4342 to 14672.3162 mm.
- Edge-biased cases: 64 to 51.
- Low-utilization cases: 2 to 0.
- U-detours: 691 to 842 (regression).
- Branch inconsistency: 1529.08 to 1725.93 mm (regression).

Failed criteria: `baseline_hard_defects_cleared`, `individual_hard_defects_never_worsen`, `routing_aesthetics_nonworsening`, `repeated_structure_within_frozen_tolerance`, and `i4_specific_improvement`.

Priority witnesses:
- Shared rail: local-label disconnections 1 to 2.
- V4-7: interface violations 0 to 1.
- V6-3: interface violations 0 to 1.
- Passive two-level fanout: local-label disconnections 1 to 2.
- I4 mixed: interface violations 2 to 0, but edge bias persists, fragmentation worsens by 25.4 mm, and U-detours increase by 5.
- I6 long three-branch: repeated structure remains outside frozen tolerance.

Do not mark TODO sections 15–21 complete. Preserve the frozen observer, historical corpus, hard gates, and locked KiCad toolchain. Prioritize generic production candidate generation, net-label locality, and route geometry, then requalify the new exact source and rerun the independent comparison. Native-render inventory and engineering inspection are separate gates.
