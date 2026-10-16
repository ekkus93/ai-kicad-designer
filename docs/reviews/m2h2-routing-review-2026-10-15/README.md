# M2h2 Routing Review

These editable KiCad projects and native SVG renders show current local outputs built with KiCad 10.0.6. Open each `.kicad_pro` project for detailed inspection. The `.kicad_sch` files are unchanged native outputs; SVG copies have only trailing whitespace removed.

## Cases

| Case | Review focus | Files |
| --- | --- | --- |
| Shared rail | Check shared reference and rail visibility across both chains. | [Project](shared-rail/M2f2TwoSignalChainsSharedRail.kicad_pro), [SVG](shared-rail/M2f2TwoSignalChainsSharedRail.svg) |
| V4-7 | Check output-interface ownership and signal flow. | [Project](v4-7/V4RegulatedDualTimerSystem.kicad_pro), [SVG](v4-7/V4RegulatedDualTimerSystem.svg) |
| V6-3 | Check reference/filter/feedback readability and output-interface ownership. | [Project](v6-3/V6ReferenceSallenKeyOutputRc.kicad_pro), [SVG](v6-3/V6ReferenceSallenKeyOutputRc.svg) |
| I4 B2 mixed | OUTPUT_2 connects R3 to J4 (43.18 mm, four bends). RETURN connects J2 to both shunt-capacitor references (170.18 mm, seven bends). INPUT measures 55.88 mm with four bends. Please judge whether J4 reads clearly with its label beside the connector and the return route nearby. | [Project](i4-b2-mixed/M2h2I4B2Mixed.kicad_pro), [SVG](i4-b2-mixed/M2h2I4B2Mixed.svg) |

## Change and verification

The I4 issue came from label connectivity: matching labels made OUTPUT_2 and RETURN electrically connected while their visible conductors were absent or split into islands. Routing prioritizes physical external signal outputs and ranks candidate routes to avoid running along three sides of another interface pin. Connector fields prefer a nearby clear slot on the side opposite the pin escape, with measured geometry checks deciding whether the slot is usable. The selected layout connects OUTPUT_2 and RETURN physically while preserving clearance and net-length limits.

Redundant local labels are omitted when the net has one continuous conductor component; labels remain only when they are needed to join separate wire islands. The current I4 artifact was built with locked KiCad 10.0.6. Electrical analysis passed with the same five pin groups and zero ERC violations, unrouted pins, unrelated wire crossings, or wires through symbol bodies. Full five-run qualification and the 90-case comparative audit have not been run for this source revision.

Production source SHA-256:

- `m2_compose.py`: `b4e997ca7b900c5eb91618f640fa7a0f7acdf87353cb8873cb7df1a4547f5ff3`
- `m2_composition_candidate_rank.py`: `55a1f5dfd538267fa8ef160a945919db14ea99955a194bcfe299c6c796e54eae`
- `m2_route.py`: `b9030b308b5a9342b0be01cbcbfc48647dc2bf5b2df36015c72b0f042e2d3ffc`
- `m2_fragments.py`: `7b75bd9ca62da83214db101d5c8fdc6bd6fa9a93cb3bd050165a1e3b5a6d3d6d`
