# M2h2 finite-trunk-distance remediation qualification — 2026-10-15

## Exact source

Source and regression commit: `86e0917bd2b7ae79afb0d84caca14ea8d11eb4e2` on `master`.

The generic candidate-selection tie-break in `src/ai_kicad/m2_route.py` now measures Manhattan distance from a gateway to its *finite, axis-aligned trunk segment* instead of only either trunk endpoint. This repairs inflated scores for nearby gateways aligned with the interior of long trunks. It retains the existing primary canonical routed-union length preference, all safety gates, bounded eight-plan candidate search, hard routing limits, and deterministic tie-break ordering. The change is source-neutral and applies to horizontal and vertical trunks equally.

`tests/test_m2_distribution_trunk_distance.py` adds eleven geometric regression controls covering horizontal and vertical finite projections, out-of-span clamping, reversed endpoints, exact contacts, and diagonal rejection. The source/test diff is restricted to those two files.

## Fast validation and comparison

- [Fast Validation 38722673569](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38722673569): all three jobs PASS on exact source `86e0917bd2b7ae79afb0d84caca14ea8d11eb4e2`, including locked-runner complete pytest/current-source regressions, hosted contracts, Ruff/static and diff/whitespace checks.
- [Locked toolchain diagnostic 38722673519](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38722673519): PASS on exact source.
- Previous fully qualified behavior source `0b9d54a9aaf00839a4fdf6f70ac1c2c3d95824c5` [full 90-case independent audit 38722381533](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38722381533): FAIL on the five frozen criteria `baseline_hard_defects_cleared`, `individual_hard_defects_never_worsen`, `routing_aesthetics_nonworsening`, `repeated_structure_within_frozen_tolerance`, and `i4_specific_improvement`. This older comparison does **not** qualify the new fix.
- Previous exact-source [137-case x5 native render inventory 38722381538](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38722381538): PASS. It does **not** establish engineering visual acceptance.

## Fresh mandatory qualifications requested

Trigger *separately* the locked KiCad 10.0.6 56-base-positive x5 / V3-8-negative, I1–I6 interactions x5, and nine structural classes x5 suites, plus the generic composition development probe against this documentation-only descendant of the unchanged behavior source. All outputs are **PENDING** and may fail. After all three suites pass, require the independent complete 90-case historical comparison and 137-case x5 normalized native render inventory tied to the *same exact* new evidence source root, followed by case-by-case engineering inspection.

Preserve frozen tolerances and 90-case historical evidence, all observer/oracle hashes, source-stabilization and anti-overfitting audits, existing 210 × 140 mm / 80 / 60 / 250 mm hard gates, and all TODO section 15–21 unchecked acceptance items. A narrow ranking regression fix is not proof that the prior five comparison failures are resolved.
