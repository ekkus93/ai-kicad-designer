# M2h2 Routing Review

These editable KiCad projects and native SVG renders show current local outputs built with KiCad 10.0.6. Open each `.kicad_pro` project for detailed inspection. The `.kicad_sch` files are unchanged native outputs; SVG copies have only trailing whitespace removed.

## Cases

| Case | Review focus | Files |
| --- | --- | --- |
| Shared rail | Check shared reference and rail visibility across both chains. | [Project](shared-rail/M2f2TwoSignalChainsSharedRail.kicad_pro), [SVG](shared-rail/M2f2TwoSignalChainsSharedRail.svg) |
| V4-7 | Check output-interface ownership and signal flow. | [Project](v4-7/V4RegulatedDualTimerSystem.kicad_pro), [SVG](v4-7/V4RegulatedDualTimerSystem.svg) |
| V6-3 | Check reference/filter/feedback readability and output-interface ownership. | [Project](v6-3/V6ReferenceSallenKeyOutputRc.kicad_pro), [SVG](v6-3/V6ReferenceSallenKeyOutputRc.svg) |
| I4 B2 mixed | The common-return connector is now physically routed to both shunt-capacitor reference pins. The routed union measures 212.09 mm with seven bends; the input path remains 45.72 mm with six bends. Please judge whether the long return path reads clearly and whether the input's left-down-right bend is acceptable. | [Project](i4-b2-mixed/M2h2I4B2Mixed.kicad_pro), [SVG](i4-b2-mixed/M2h2I4B2Mixed.svg) |

## Change and verification

The I4 issue came from label connectivity: the connector and both capacitors had the same `RETURN` net label, but their emitted conductor geometry formed separate islands. The router now tries a deterministic, bounded physical tree for an external reference interface with multiple internal reference terminals. If it cannot prove the route under existing clearance and length limits, labels remain the fallback. A regression checks conductor reachability from the return interface to both capacitor gateways.

The locked current-source checks passed for I4 B2 mixed, V6-3, and DP2. Shared-rail and V4-7 native builds also succeeded. The last complete 90-case comparison was for the preceding source and failed five frozen criteria; this routing change still needs full five-run qualification and a new independent comparison before acceptance.

Production source SHA-256:

- `m2_compose.py`: `3d6881b72e16dfc7ae7c84a73aa6c9db2589ffa539217b5604457b7315c8b158`
- `m2_composition_candidate_rank.py`: `55a1f5dfd538267fa8ef160a945919db14ea99955a194bcfe299c6c796e54eae`
- `m2_route.py`: `8b8c74cacf1e5cc03f6d0ac7619c4764e6be5147624a993235a9c4d1bc0f3f1d`
