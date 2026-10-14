# M2h2 exact-source independent audit launch — 2026-10-14

**Qualification source:** `464588cfd427261923beb813635ef48208a4eb83`

**Status:** All three locked-KiCad five-run qualification suites passed. Independent human-composition acceptance and engineering visual inspection remain open.

## Verified exact-source CI evidence

- Base 56 positives ×5 / V3-8 negative: https://github.com/ekkus93/ai-kicad-designer/actions/runs/38533390897 — PASS
- I1–I6 interactions ×5: https://github.com/ekkus93/ai-kicad-designer/actions/runs/38533390932 — PASS
- Nine structural classes ×5: https://github.com/ekkus93/ai-kicad-designer/actions/runs/38533391009 — PASS
- Fast Validation: https://github.com/ekkus93/ai-kicad-designer/actions/runs/38533391033 — PASS
- Locked KiCad 10.0.6 toolchain: https://github.com/ekkus93/ai-kicad-designer/actions/runs/38533391069 — PASS
- Development composition probe: https://github.com/ekkus93/ai-kicad-designer/actions/runs/38533390965 — PASS
- Base native render transfer: https://github.com/ekkus93/ai-kicad-designer/actions/runs/38537011045 — PASS
- Structural native render transfer: https://github.com/ekkus93/ai-kicad-designer/actions/runs/38538396087 — PASS

## Exact-source independent acceptance audit

This documentation-only checkpoint requests independent comparison of the persisted `$HOME/m2h2-evidence/464588cfd427261923beb813635ef48208a4eb83/` against the frozen 90-case historical baseline, followed by the normalized 137-case ×5 native-render inventory.

The last completed independent comparison ([run 38457583899](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38457583899)) FAILED five frozen criteria:
- `baseline_hard_defects_cleared`
- `individual_hard_defects_never_worsen`
- `routing_aesthetics_nonworsening`
- `repeated_structure_within_frozen_tolerance`
- `i4_specific_improvement`

No tolerance, historical artifact, benchmark baseline, KiCad toolchain version, observer, oracle, or final acceptance checkbox may be changed to bypass these gates.

## Development-probe observations, not acceptance

- `v6-3`: selected candidate still has one interface-side violation and one stage inversion; no equally flow/side-correct alternative found in bounded candidate search.
- `i4__b2_mixed`: selected candidate has zero stage inversions and zero interface-side violations, but route backtracking 88 and routed union 287.02 mm; lower-backtracking candidate 78 has longer union 335.28 mm and worse output-owner row drift.
- `v4-7`: selected candidate has 670.56 mm routed union and 20 bends, versus a 697.23 mm / 19-bend alternative with equal higher-priority semantics.

These findings are diagnostic, not proof of frozen comparative visual acceptance. Sections 15–21 of `docs/M2H2_HUMAN_READABLE_SCHEMATIC_COMPOSITION_TODO_2026-10-07.md` remain OPEN until independent exact-source reports pass and case-by-case native engineering review is complete.

## Trigger and validation contract

Commit marker: `[m2h2-artifact-audit] [m2h2-render-inventory] [m2h2-audit-source:464588cfd427261923beb813635ef48208a4eb83]`.

Run workflows against this specific persisted source root, not the documentation-only descendant's nonexistent qualification tree. Capture workflow run IDs, report artifacts, and failures. Do not mark acceptance based on dispatch alone.
