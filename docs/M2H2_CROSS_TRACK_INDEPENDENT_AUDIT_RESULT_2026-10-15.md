# M2h2 cross-track independent comparison — 2026-10-15

**Status: FAIL (five frozen comparative criteria).** The independent [90-case artifact audit 38739515011](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38739515011) evaluated the preserved locked-KiCad evidence for exact source `91bf253f718f082359374fb04f0918e37749ca7f`. Its complete base 56×5/V3-8-negative, I1–I6×5, and nine structural-class×5 qualifications all passed ([base 38732857698](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38732857698), [interaction 38732857751](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38732857751), [structural 38732857721](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38732857721)). The [137-case native render inventory 38739514965](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38739514965) independently passed five-run normalized render reproducibility.

## Frozen historical comparison

| Metric | Historical | Exact-source fresh |
| --- | ---: | ---: |
| Stage-order inversions | 1 | 0 |
| Interface-side violations | 77 | 48 |
| Functional fragmentation (mm) | 14743.4342 | 14672.3162 |
| Page edge-biased cases | 64 | 51 |
| U-shaped detours | 691 | 842 |
| Branch inconsistency (mm) | 1529.08 | 1725.93 |

The following five frozen criteria remain **FAILED**: `baseline_hard_defects_cleared`, `individual_hard_defects_never_worsen`, `routing_aesthetics_nonworsening`, `repeated_structure_within_frozen_tolerance`, and `i4_specific_improvement`. Other seven comparison criteria passed. These figures are identical to the preceding independent [source audit 38729570577](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38729570577): the bounded generic interior cross-track addition has not measurably changed this frozen 90-case comparison.

## Concrete unresolved witnesses

- Shared-rail two-chain case: local-label disconnects 1→2; interface violations remain 2; branch inconsistency worsens by 27.94 mm.
- V4-7: interface-side violations 0→1; fragmentation worsens 38.10 mm; branch inconsistency worsens 22.86 mm.
- V6-3: interface-side violations 0→1; fragmentation worsens 12.70 mm; branch inconsistency worsens 22.86 mm. The development probe for this source reported just one fully proved placement candidate.
- Passive two-level fanout and its long-fields variant: local-label disconnects 1→2.
- `i4__b2_mixed`: its interface-side and local-label hard defects are zero, but page-edge bias remains and detours worsen; it fails the required individual improvement criterion.

## Next engineering work

The routing track selection in `src/ai_kicad/m2_route.py` deserves a generic dense-obstacle regression: for every interior track between two endpoints, `abs(track-a) + abs(track-b)` is constant. Selecting only the first eight therefore systematically excludes far-side lanes when there are more than eight. A bounded, deterministic, span-diverse sampling strategy should be tested without changing any routing budget or frozen constraint. This is an **identified implementation candidate**, not a committed production fix.

After any production change, rerun exact-head fast validation and the three full five-run locked-KiCad suites, then the independent frozen comparison and native render inventory. Native engineering inspection and TODO sections 15–21 remain **OPEN**. Do not alter frozen observers, thresholds, baselines, or the KiCad 10.0.6 toolchain to make the audit pass.
