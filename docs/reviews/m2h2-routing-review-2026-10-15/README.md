# M2h2 Routing Review

These editable KiCad projects and native SVG renders show current local outputs built with KiCad 10.0.6. Open each `.kicad_pro` project for detailed inspection. The `.kicad_sch` files are unchanged native outputs; SVG copies have only trailing whitespace removed.

## Cases

| Case | Review focus | Files |
| --- | --- | --- |
| Shared rail | Check shared reference and rail visibility across both chains. | [Project](shared-rail/M2f2TwoSignalChainsSharedRail.kicad_pro), [SVG](shared-rail/M2f2TwoSignalChainsSharedRail.svg) |
| V4-7 | Check output-interface ownership and signal flow. | [Project](v4-7/V4RegulatedDualTimerSystem.kicad_pro), [SVG](v4-7/V4RegulatedDualTimerSystem.svg) |
| V6-3 | Check reference/filter/feedback readability and output-interface ownership. | [Project](v6-3/V6ReferenceSallenKeyOutputRc.kicad_pro), [SVG](v6-3/V6ReferenceSallenKeyOutputRc.svg) |
| I4 B2 mixed | The series-only branch R3 → J4 now sits above the main row, so the C1/C2 return rail runs straight along the bottom and no connector is boxed in by the return wiring (interface enclosure count 0, previously 1). Connector leads are straight: the two-pitch hooks at every connector are gone. OUTPUT_2 connects R3 to J4 in 39.37 mm (was 53.34 mm); OUTPUT_1 measures 85.09 mm (was 60.96 mm, J3 now sits below the row on the outer frontier); RETURN measures 165.10 mm (was 203.20 mm); INPUT measures 76.20 mm (was 57.15 mm, J1 sits above J2 in the left interface column). Total routed length 443.23 mm. Please review the input/return connector column on the left and the Output 1 lane below the row. | [Project](i4-b2-mixed/M2h2I4B2Mixed.kicad_pro), [SVG](i4-b2-mixed/M2h2I4B2Mixed.svg) |

## Change and verification

The I4 issue came from label connectivity: matching labels made OUTPUT_2 and RETURN electrically connected while their visible conductors were absent or split into islands. Routing prioritizes physical external signal outputs and penalizes routes that frame another interface pin. Output connectors use a measured right-side frontier beyond other placed content. When several outputs share that edge, they are staggered using a measured clearance from the adjacent route envelope; this keeps each connector outside the wiring while avoiding unnecessary displacement of the return branches. Connector fields prefer a nearby clear slot opposite the pin escape, with geometry checks deciding whether the slot is usable. The selected layout connects OUTPUT_1, OUTPUT_2, and RETURN physically while preserving clearance and per-net length limits. Candidate ranking previously prioritized avoiding interface enclosure ahead of route length, and the fully aligned output alternative exceeded the RETURN net length cap. The staggered frontier candidate clears OUTPUT_1 and lets the RETURN route shorten by 33.02 mm.

Redundant local labels are omitted when the net has one continuous conductor component; labels remain only when they are needed to join separate wire islands.

### 2026-10-16 revision

Three general rules were added after the first I4 review, and all four artifacts here were rebuilt from the same source with locked KiCad 10.0.6 (zero ERC violations, unrouted pins, unrelated crossings or wires through text in every case):

- **Straight connector leads.** A single-port connector keeps one straight outward lead. When its net label would overlap the visible pin number, the label hangs on a short orthogonal label stub off the lead's end instead of bending the lead itself. Connector envelopes are unchanged, so packing of unrelated cases is unchanged. Composition drops a redundant label together with the stub that carried it, and prunes any other dead-end spur back to a pin, junction or retained label, so a dropped label can no longer leave an unconnected wire end. This also repairs an ERC regression of the earlier revision in which omitted labels left dangling escape stubs (for example the unused-amplifier PARK lead in V6-3).
- **Reference-free siblings stack away from the reference rail.** In a fanout column whose stages all escape their reference downward, a sibling with no reference of its own is stacked above the siblings that own one, and the signal row stays aligned with the reference-bearing siblings. Hung below, its row would cut between the reference terminals and their rail, which is what forced the previous return loop around Output 2.
- **Combined interface frontier candidate.** In addition to the single-role input and output frontier candidates, one candidate moves inputs and outputs to their frontiers together. For I4 the output-only candidate still wins (the combined one boxes the left interfaces), but the candidate is now available to the route-aware selector.

I4 B2 mixed after this revision: routed union 443.23 mm, zero enclosures, zero crossings, all outputs physically routed, no labels. V6-3's signal input is now physically wired to R3 and its PARK spur is gone; its other known defects (label-only Filtered output, stacked rail connectors) are unchanged and remain open in the TODO. V4-7 and shared-rail are byte-identical to a build from the previous revision's source; their committed copies had been built from an older commit and are refreshed here. Full five-run qualification and the 90-case comparative audit have not been run for this source revision. On the unmodified previous revision, `tests/test_m2h2_contracts.py::test_measured_row_compaction_and_stagger_are_legal_structural_classes` already failed (VMINUS route length bound) and still fails; it passes on `master` and is tracked as an open branch regression.

Production source SHA-256:

- `m2_compose.py`: `72fe9208b45f26d0fa3f26b4d1f130d13b8fcdf83ab2226b10419f7dc6443fb8`
- `m2_composition_candidate_rank.py`: `55a1f5dfd538267fa8ef160a945919db14ea99955a194bcfe299c6c796e54eae`
- `m2_route.py`: `b5a88ecdd80adef2f5646d693198095411141829a4b7933ddc41b1100278162f`
- `m2_fragments.py`: `b3c00c23840dbb3914b52d36ef88c36f0519b9dd3107a4da0201992bed389973`
- `m2_pack.py`: `0a85f7afbe35b15765473e44348d152151571f2947bfeacb4cb4850c091ea3d7`
