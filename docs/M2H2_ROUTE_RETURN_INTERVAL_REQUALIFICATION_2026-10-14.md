# M2h2 generic route return-interval requalification — 2026-10-14

**Qualification subject:** `7d4c1ef2c925b536b36cd5c0f33c124e22278fb3` (behavior-affecting).
**Status:** three independent locked-KiCad five-run suites requested; no acceptance asserted by dispatch.

## Change under test

The generic `route_backtracking_penalty` previously charged every pair of same-side legs of a continuous conductor trunk. For an N-way fanout, this counted overlapping nested intervals as separate returns and exaggerated the soft routing penalty quadratically. The new implementation scores only consecutive leg intervals, retaining the summed grid-length cost of actual neighboring returns. It preserves the higher-priority semantic objective, all hard route and geometry constraints, existing anti-overfitting boundaries, and all frozen independent acceptance thresholds.

New `tests/test_m2_route_backtracking_fanout.py` covers a multiway fanout, split/reversed equivalent conductor geometry, independent-tree additivity, and the original two-leg U-shaped route. This does **not** claim better visual selection in the frozen corpus; candidate search still limits V6-3 to one proved geometry and its interface-side violation remains open.

## Evidence and source-matched qualification

- Source commit: [7d4c1ef2](https://github.com/ekkus93/ai-kicad-designer/commit/7d4c1ef2c925b536b36cd5c0f33c124e22278fb3)
- Source-head Fast Validation (run [38551543532](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38551543532)) was running as of qualification request; static/Ruff passed; other jobs must be checked when terminal.
- Development composition probe (run [38551543493](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38551543493)) completed successfully on exact source; it is **diagnostic**, not native aesthetic acceptance.
- Previous pre-change independent 90-case comparison (run [38549388901](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38549388901), subject `464588cfd427261923beb813635ef48208a4eb83`) FAILED five frozen gates: hard defect closure, individual hard defect nonworsening, routing-aesthetic nonworsening, repeated-structure frozen tolerance, and `i4_specific_improvement`. Pre-change historical→fresh totals: interface-side 77→44, stage inversions 1→0, functional fragmentation 14743.4342→14677.3962 mm; **U-detours 691→865** and branch inconsistency 1529.08→1758.95 mm remain worse.
- Previous native-render inventory run [38549388840](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38549388840) passed normalized hashes, not native engineering inspection.
- Request new locked runner: 56 positives ×5 and V3-8 negative, I1–I6 interactions ×5, nine structural classes ×5, plus development probe on this documentation-only descendant of the exact behavior source.

After all three full source-matched suites actually pass, independently audit the new persisted evidence root against all 90 frozen baseline cases, repeat 137-case×5 normalized native-render inventory, inspect native renders, and reconcile sections 15–21. Do not edit frozen thresholds, historical evidence, schema, or mark incomplete TODO items complete.

**Commit request markers:** `[m2h2-final-qualification] [m2h2-interaction-qualification] [m2h2-structural-qualification] [m2h2-development-probe]`.
