# M2h2 qualified-source comparison: residual routing and structural regressions (2026-10-14)

**State:** independent comparison FAILED; normalized native-render inventory PASSED. This record is diagnostic, not acceptance.

## Exact evidence identity

- Behavior and five-run qualification root: `e0da993190fc51a1ad1249c7e9a22855319c9172`, persisted at `$HOME/m2h2-evidence/e0da993190fc51a1ad1249c7e9a22855319c9172/`.
- Documentation-only audit dispatch: `df9946b97fa87caab9438009b185169109deedfb`.
- [Historical 90-case independent audit, run 38611663994](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38611663994): **FAIL**, with all 90 cases present. Failed frozen criteria: `baseline_hard_defects_cleared`, `individual_hard_defects_never_worsen`, `routing_aesthetics_nonworsening`, `repeated_structure_within_frozen_tolerance`, `i4_specific_improvement`.
- [137-case × five-run normalized native render inventory, run 38611663887](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38611663887): **PASS**, proving normalized geometry reproducibility, not aesthetic acceptance.
- Exact-source base 56/V3-8, I1–I6 and structural qualification passed in runs 38602260592, 38602260383 and 38602260751; Fast Validation 38602260439 and pinned KiCad identity 38602260921 also passed.

## Frozen historical versus qualified-source measurements

| Metric | Historical | Qualified source | Interpretation |
| --- | ---: | ---: | --- |
| Stage inversions | 1 | 0 | Improved |
| Interface-side violations | 77 | 38 | Improved, not eliminated |
| Functional fragmentation (mm) | 14743.4342 | 14583.4162 | Improved |
| Edge-biased cases | 64 | 54 | Improved |
| Low-utilization cases | 2 | 0 | Improved |
| U-shaped detours | 691 | 880 | Regressed |
| Branch inconsistency (mm) | 1529.08 | 1771.65 | Regressed |

The independent diagnostic ranks `base__m2f2-two_signal_chains_shared_rail` among unresolved hard-defect witnesses: its local-label disconnect count increased from 1 to 2 while interface-side violations remain at 2. That is a generic shared-rail routing/attribution witness, **not** permission to special-case that fixture.

## Dependency-first remediation

1. Re-run the source-neutral development composition probe for `shared_rail`, `v6-3`, `v4-7`, `i4__b2_mixed`, `passive_fanout` and existing comparative witnesses. Preserve selection, rejected-search, route-strategy and semantic-penalty ledgers. Determine whether a valid lower-defect candidate was generated but lost in ranking, or no valid candidate was proved.
2. Fix generic conductor topology / legal-candidate generation before soft ranking where no candidate exists. Target unnecessary return legs, shared-rail junction/label ownership, and branch geometry without weakening electrical, routing, or composition hard gates.
3. Verify per-case nonworsening and repeated-stage alignment; test declaration-order, net-name and fragment-order invariance and unrelated cases to guard against overfitting.
4. After any behavior change, run exact-head Fast Validation, pinned KiCad, all three full five-run suites, independent 90-case frozen comparison, 137-case normalized inventory, and case-by-case native engineering inspection. Reconcile TODO sections 15–21 only from affirmative evidence.

**Infrastructure observation:** the historical audit job also failed its upload-artifact step because GitHub Actions reported artifact storage quota exhaustion. This is separate from the genuine frozen-comparison failure. Preserve runner-local evidence; do not mistake a missing uploaded artifact for an absence of computed metrics.

No historical baseline, frozen criterion, observer, KiCad pin, production behavior or final acceptance checkbox is changed by this record.
