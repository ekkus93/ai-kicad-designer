# M2h2 source-matched comparative audit — 2026-10-13

Status: **FAILED; do not mark human-readable composition COMPLETE**.

## Exact evidence

- Qualified production source: `f909475058724c190dce26a66e0943866d72f62f`.
- Independent historical 90-case audit: https://github.com/ekkus93/ai-kicad-designer/actions/runs/38344818593 (FAIL).
- Native-render normalized inventory: https://github.com/ekkus93/ai-kicad-designer/actions/runs/38344818965 (PASS).
- Base and structural native render transfer: runs 38343164560 and 38341672220 (PASS).
- Base 56×5/V3-8 negative, I1–I6×5, structural×5: runs 38341411894, 38341411990, 38341411880 (PASS).
- All-three-job Fast Validation on documentation-only descendant: run 38344818543 (PASS).

## Frozen comparative criteria that remain failing

`baseline_hard_defects_cleared`, `individual_hard_defects_never_worsen`, `routing_aesthetics_nonworsening`, `repeated_structure_within_frozen_tolerance`, `i4_specific_improvement`.

## Historical → qualified-source totals (90 matched cases)

| Metric | Historical | Fresh |
| --- | ---: | ---: |
| Stage inversions | 1 | 0 |
| Interface-side violations | 77 | 44 |
| Functional fragmentation (mm) | 14743.4342 | 14674.8561 |
| Edge-biased cases | 64 | 53 |
| Low-utilization cases | 2 | 0 |
| U-shaped detours | 691 | 858 |
| Branch inconsistency (mm) | 1529.08 | 1714.5 |

The corpus-wide functional-fragmentation nonworsening criterion **passes**. The other five named frozen criteria **fail**. Do not infer per-case hard-defect closure from improving aggregate totals.

## Mixed-case witness

`i4__b2_mixed`: hard defects 4→0 and edge bias true→false, but fragmentation 73.6602→99.0602 mm, U-detours 2→6, and branch inconsistency 21.59→29.21 mm. Thus the targeted visual criterion remains open.

## Next work

Investigate and repair generic candidate generation/ranking and emitted-route geometry to reduce individual hard defects, U-detours, sibling-branch inconsistency, and repeated-structure drift without special-casing names, loosening frozen thresholds, or modifying historical evidence. Requalify any behavior change on locked KiCad 10.0.6, repeat independent comparison and normalized render inventory, and perform case-by-case engineering inspection before checking sections 15–21 of the canonical TODO.

Evidence root: `$HOME/m2h2-evidence/f909475058724c190dce26a66e0943866d72f62f/`. The audit JSON is preserved there. GitHub artifact upload failed due to storage quota, but this did not cause the comparative failure.
