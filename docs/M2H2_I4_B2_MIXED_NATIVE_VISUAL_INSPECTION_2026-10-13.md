# M2h2 native visual inspection: mixed two-output case — 2026-10-13

**Inspection type:** independent engineering/agent review of one native KiCad render, **not user approval and not final composition acceptance**.

## Provenance and reproducibility

- Qualified behavior/evidence source: `54eeb3c66112448c46eaaea9bd68ec0bd8941b35` (locked KiCad 10.0.6, five-run base/I1–I6/structural qualification).
- Exact-source preview request: `dee497a2d53aeca4c5d67e4b16104131b50821aa`, with `[m2h2-render-case:i4__b2_mixed]` and `[m2h2-audit-source:54eeb3c66112448c46eaaea9bd68ec0bd8941b35]`.
- [Native-render inventory and PNG transfer, run 38379954922](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38379954922): SUCCESS. Its `inventory` job emitted 57 ordered `m2h2.png-preview-transfer.1` base64-PNG chunks for `i4__b2_mixed`, indices 0–56, which were reassembled and visually inspected. The PNG is a preview of the native KiCad SVG, not an independently authored diagram.
- Source-matched native SVG SHA-256: `eda9ac9b8695d286d111a3ec3a8d69d8045b03e4f9e51d995c6530d06e95d84c`. Transferred preview PNG SHA-256: `3b50097079fcda9cf971eacfa5bb9c518ed342b308bdc1936e0e97ee1b6159bd`.
- [Independent full-90-case comparison, run 38379445241](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38379445241): **FAIL** against the same explicit qualified source. This audit is the authority for quantitative before/after metrics; a visually inspected preview does not supersede it.
- [Exact-head Fast Validation, run 38379954833](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38379954833): all three jobs passed for the documentation-only preview-request descendant. That does not prove visual closure.

## What the native render actually shows

The native A4 sheet has a clear left-to-right main signal line: input connector J1 at the left, series resistor R1, series resistor R2, and output connector J3 (`OUTPUT_1`) at the right. A second branch leaves the main signal path after R1, descends through series resistor R3, and returns to the upper-right output connector J4 (`OUTPUT_2`). Two capacitors C1/C2 shunt local signal nodes to the named `RETURN` net. Connector J2 (`Common return`) is at the far right and is linked to the shunts by named-net labels rather than a continuous drawn return rail.

**Positive observations:** both directed outputs are on the right, J1 is on the left, the two outputs have distinct labels, component and connector values are legible at the preview resolution, the two shunt capacitors are visually associated with their local signal nodes, and the branch source is recognizable. The lower branch does not appear to cross unrelated conductors. The main signal direction is immediately intelligible.

**Unresolved composition concerns (not electrical failures):**

1. The `OUTPUT_2` branch travels down through R3, horizontally across the lower row, and then rises to J4 on the same upper row as J3. This long vertical return jog makes the branch less direct than an output connector aligned to its own final producer; it is a concrete native-render example of the routing-aesthetic problem. It is **not** evidence that the routed net is electrically incorrect.
2. J4 is visually close to J3 but substantially above R3. The final-producer/output association is recoverable by following the wire, not obvious at first glance. A generic, source-preserving alternative would be to evaluate a legal lower-right connector row near the R3 output, subject to all existing placement/field/wire-clearance and electrical gates.
3. J2 and the C1/C2 return pins rely on repeated `RETURN` labels. This is valid schematic notation and is **not** a missing net connection, but the shared return infrastructure reads as three visually separated islands. Any coherence improvement must preserve legitimate label-mediated connections and not invent a continuous rail or change the netlist.
4. The circuit occupies a relatively shallow middle band of the A4 page with substantial free space below. This alone is not a frozen page-utilization violation: the independent observer reports `page_edge_bias=false` and `page_low_utilization=0` for the fresh case.

## Source-matched comparative falsification

The independent audit reports the following historical → fresh values for `i4__b2_mixed`:

| Metric | Historical | Fresh | Interpretation |
| --- | ---: | ---: | --- |
| Interface-side violations | 2 | 0 | Improved |
| Local label disconnections (observer) | 1 | 0 | Improved |
| Edge bias | true | false | Improved |
| Total hard composition defects | 4 | 0 | Improved |
| Functional fragmentation (mm) | 73.6602 | 99.0602 | **Worse** |
| U-shaped detours | 2 | 6 | **Worse** |
| Branch inconsistency (mm) | 21.59 | 29.21 | **Worse** |
| Repeated alignment within frozen tolerance | true | true | Preserved |

The exact-source `i4_specific_improvement` comparative criterion is **false**. The preview is consistent with the detour and branch-locality concerns but cannot by itself assign every independent observer witness. Do not claim this case passes aesthetic acceptance merely because its four historical hard defects are now zero.

Across all 90 baseline cases, the same audit reports stage inversions 1→0, interface-side violations 77→44, fragmentation 14743.4342→14674.8561 mm, edge-biased cases 64→53, U-detours **691→858**, and branch inconsistency **1529.08→1714.5 mm**. Five frozen criteria remain false: `baseline_hard_defects_cleared`, `individual_hard_defects_never_worsen`, `routing_aesthetics_nonworsening`, `repeated_structure_within_frozen_tolerance`, and `i4_specific_improvement`.

## Next engineering action

Use generic directed-output ownership and emitted-route candidate evidence to determine whether a **legal, semantically equivalent** lower-right J4 position is considered and why it loses to the current upper-row placement. Test with a renamed/permuted two-output branch archetype as well as this falsification seed; reject any fix that depends on case IDs, connector labels, or literal net names. Preserve existing hard geometry/electrical gates and frozen historical metrics. If a generic candidate-ranking or placement change is justified, re-run all three locked-KiCad five-run suites, source-matched 90-case audit, normalized native-render inventory, and engineering inspection. Do not tune acceptance thresholds to make this case pass.

**Checklist accounting:** this document is **one** inspected native mixed-case preview and a concrete negative engineering finding. It does not complete the required all-case inspection in section 18, source freeze in section 16, comparative closure in section 19, or final sections 17–21. Leave their checkboxes open. Historical evidence and frozen tolerances were not changed.
