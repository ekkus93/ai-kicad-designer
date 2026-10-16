# M2h2 Routing Review

These editable KiCad projects and native SVG renders show current local outputs built with KiCad 10.0.6. Open each `.kicad_pro` project for detailed inspection. The `.kicad_sch` files are unchanged native outputs; SVG copies have only trailing whitespace removed.

## Cases

| Case | Review focus | Files |
| --- | --- | --- |
| Shared rail | Check shared reference and rail visibility across both chains. | [Project](shared-rail/M2f2TwoSignalChainsSharedRail.kicad_pro), [SVG](shared-rail/M2f2TwoSignalChainsSharedRail.svg) |
| V4-7 | Check output-interface ownership and signal flow. | [Project](v4-7/V4RegulatedDualTimerSystem.kicad_pro), [SVG](v4-7/V4RegulatedDualTimerSystem.svg) |
| V6-3 | Check reference/filter/feedback readability and output-interface ownership. | [Project](v6-3/V6ReferenceSallenKeyOutputRc.kicad_pro), [SVG](v6-3/V6ReferenceSallenKeyOutputRc.svg) |
| I4 B2 mixed | OUTPUT_1 and OUTPUT_2 connectors sit on the outer right frontier, with OUTPUT_1 staggered inward just enough to clear the return route. OUTPUT_2 connects R3 to J4 (53.34 mm); OUTPUT_1 measures 60.96 mm. RETURN connects J2 to both shunt-capacitor references in 203.20 mm, down from 236.22 mm in the prior review. INPUT measures 57.15 mm. Please review the connector spacing and the shorter return path by C1. | [Project](i4-b2-mixed/M2h2I4B2Mixed.kicad_pro), [SVG](i4-b2-mixed/M2h2I4B2Mixed.svg) |

## Change and verification

The I4 issue came from label connectivity: matching labels made OUTPUT_2 and RETURN electrically connected while their visible conductors were absent or split into islands. Routing prioritizes physical external signal outputs and penalizes routes that frame another interface pin. Output connectors use a measured right-side frontier beyond other placed content. When several outputs share that edge, they are staggered using a measured clearance from the adjacent route envelope; this keeps each connector outside the wiring while avoiding unnecessary displacement of the return branches. Connector fields prefer a nearby clear slot opposite the pin escape, with geometry checks deciding whether the slot is usable. The selected layout connects OUTPUT_1, OUTPUT_2, and RETURN physically while preserving clearance and per-net length limits. Candidate ranking previously prioritized avoiding interface enclosure ahead of route length, and the fully aligned output alternative exceeded the RETURN net length cap. The staggered frontier candidate clears OUTPUT_1 and lets the RETURN route shorten by 33.02 mm.

Redundant local labels are omitted when the net has one continuous conductor component; labels remain only when they are needed to join separate wire islands. The current I4 artifact was built with locked KiCad 10.0.6. Electrical analysis passed with the same five pin groups and zero ERC violations, unrouted pins, unrelated wire crossings, or wires through symbol bodies. Full five-run qualification and the 90-case comparative audit have not been run for this source revision.

Production source SHA-256:

- `m2_compose.py`: `906d6f44b8a5aa7f6e24eb6a689521ea7648fb50ebf624c06472503434122fb0`
- `m2_composition_candidate_rank.py`: `55a1f5dfd538267fa8ef160a945919db14ea99955a194bcfe299c6c796e54eae`
- `m2_route.py`: `b5a88ecdd80adef2f5646d693198095411141829a4b7933ddc41b1100278162f`
- `m2_fragments.py`: `7b75bd9ca62da83214db101d5c8fdc6bd6fa9a93cb3bd050165a1e3b5a6d3d6d`
- `m2_pack.py`: `3e2d190533d84f778ad47c48eb83185ae8ecfb574454acdb5345055a9908231f`
