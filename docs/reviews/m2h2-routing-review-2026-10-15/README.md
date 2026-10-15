# M2h2 Routing Review

These native KiCad projects and SVG renders are the exact run 1 outputs from the locally qualified branch-arm scoring source. Open the `.kicad_pro` file for editable inspection; the adjacent SVG is a quick view. KiCad 10.0.6 was used for native renders. The committed SVG copies have trailing whitespace stripped from each line to satisfy repository checks; the schematic files are unmodified.

## Cases to review

| Case | Review focus | Files |
| --- | --- | --- |
| Shared rail | Two-chain shared-rail layout; local label disconnects increased from 1 historical witness to 2 in the current output. | [KiCad project](shared-rail/M2f2TwoSignalChainsSharedRail.kicad_pro), [SVG](shared-rail/M2f2TwoSignalChainsSharedRail.svg) |
| V4-7 | Dual timer system; current output introduces one interface-side hard defect against a historically clean case. | [KiCad project](v4-7/V4RegulatedDualTimerSystem.kicad_pro), [SVG](v4-7/V4RegulatedDualTimerSystem.svg) |
| V6-3 | Reference Sallen-Key output; current output introduces one interface-side hard defect against a historically clean case. | [KiCad project](v6-3/V6ReferenceSallenKeyOutputRc.kicad_pro), [SVG](v6-3/V6ReferenceSallenKeyOutputRc.svg) |
| I4 B2 mixed | Mixed dual-output case; interface and label defects improve, while U-shaped detours rise 2→7 and branch inconsistency rises 21.59→29.21 mm. | [KiCad project](i4-b2-mixed/M2h2I4B2Mixed.kicad_pro), [SVG](i4-b2-mixed/M2h2I4B2Mixed.svg) |

## Provenance

- Qualification checkout: `81b1e7f3521d806bf60432bf4a139186abf3aa17` with the exact production source hashes recorded in the qualification manifests.
- `m2_compose.py` SHA-256: `3d6881b72e16dfc7ae7c84a73aa6c9db2589ffa539217b5604457b7315c8b158`.
- `m2_composition_candidate_rank.py` SHA-256: `55a1f5dfd538267fa8ef160a945919db14ea99955a194bcfe299c6c796e54eae`.
- Cases came from `.local/m2h2-branch-spread` qualification evidence; each selected run passed its electrical, serialization, and per-case qualification checks.
- The independent 90-case comparison still fails five frozen criteria: hard-defect closure, individual hard-defect nonworsening, routing aesthetics, repeated-structure tolerance, and I4-specific improvement. These files are submitted for engineering review, not as an acceptance claim.

## Review questions

- Are the signal progression and interface associations clear at a glance?
- For the shared rail, is the relationship between the reference trunk and both chains understandable?
- For V4-7 and V6-3, where should the affected interface connect or face to preserve the intended flow?
- For I4 B2 mixed, does the reduced interface clutter justify the visibly longer or more awkward return routing?
