# Independent assessment of KiCad review baseline v10 (2026-11-14)

**Reviewed from:** `docs/ai_kicad_baseline_ratings_for_chatgpt.md` and the fifteen linked close-ups on the repository `mcp` branch. The document is a request for independent baseline ratings, not a completed set of Claude ratings. The accompanying manifest reports all fifteen pass KiCad native, ERC, netlist-equivalence and enabled presentation checks. These checks do not establish analog performance.

**Rater:** ChatGPT / visual, human-facing layout assessment; **rating scope:** supplied close-up PNGs and representative full A4 pages, with the provided intended netlists. No SPICE or physical testing.

**Strict baseline result:** 5 good/acceptable; 10 defects requiring improvement. “Good” means readable and reasonably acceptable *for this schematic presentation benchmark*, not optimized or ready for PCB manufacture.

## Individual ratings

| Code | Assessment | Main observation |
|---|---|---|
| B01 | GOOD | Dual unity buffers: simple, traceable signal/feedback loops; power section somewhat spread out. |
| B02 | GOOD | Non-inverting amplifier: very clear gain network, clean parked second channel. |
| B03 | DEFECTS | 7805 regulator: output connector is to the left of the input; functional flow is backwards. |
| B04 | DEFECTS | LED with long value: two giant connector U-turns, plus non-numeric resistance metadata. |
| B05 | DEFECTS | 555 LED flasher: output, LED and control bypass use long perimeter wiring. |
| B06 | GOOD | RC low-pass: simple and readable, though return routing could be shortened. |
| B07 | GOOD | Inverting amplifier: strong signal-stage topology; improved independent power block. |
| B08 | DEFECTS | Reverse-supply LED: obvious but unnecessarily enormous rectangular route. |
| B09 | DEFECTS | RC-to-buffer: filter is clear; power/unused-op-amp blocks are dispersed. |
| B10 | DEFECTS | 555 astable GND: reasonable timer ladder, remote output and inconsistent ground arrow. |
| B11 | DEFECTS | LED series: two connector-facing U-turns dominate this tiny circuit. |
| B12 | DEFECTS | Divider VREF: long midpoint bus, awkward decoupling routing and separated unused amp. |
| B13 | GOOD | RC high-pass: simple, readable and well ordered, with a slightly long return. |
| B14 | DEFECTS | Sallen–Key: good active-filter structure, awkward and isolated power-unit region. |
| B15 | DEFECTS | 555 astable REF: same remote-output and symbol-orientation issues as B10. |

## Case-specific defects (machine-readable content)

### B01 — GOOD
- No blocking presentation defect in this strict rating; further refinement is possible.

### B02 — GOOD
- No blocking presentation defect in this strict rating; further refinement is possible.

### B03 — DEFECTS
- J2.1 / VOUT; regulated-output connector is placed to the far left of J1 and U1 even though U1.3 is on the right; left edge of drawing
- J3.1 / REF; return connector is detached from the otherwise coherent regulator and capacitor return block, making the interface needlessly scattered; upper left
- J1.1 / VIN; supply wire makes a redundant up-across-down detour before U1.1 rather than proceeding directly into a left-to-right regulator block; above C1

### B04 — DEFECTS
- J1.1 / R123.1; input connector faces away from the series resistor, forcing a wide U-shaped path over the top; top-left to upper-right
- J2.1 / D24.1; return wire travels around the bottom edge rather than using a short direct/reference connection; lower portion of drawing
- R123; value field mixes the electrical value with the word precision, which should be separate metadata for downstream BOM/SPICE parsing; right of resistor

### B05 — DEFECTS
- U1.3 / OUT / J2.1; OUT wire routes around the top and far-left perimeter to reach the LED/output branch; outer edges of drawing
- R3 / D1; LED indicator branch is too far from U1 output and visually dominates the left margin rather than forming a compact functional block; far left
- C2.1 / U1.5 CONT; control-pin capacitor wire makes a long rectangular detour above U1 instead of a compact local bypass; top center
- J1 / J3; supply and return entry connectors are placed below the timing network and far apart from the main signal/output flow; lower portion

### B06 — GOOD
- No blocking presentation defect in this strict rating; further refinement is possible.

### B07 — GOOD
- No blocking presentation defect in this strict rating; further refinement is possible.

### B08 — DEFECTS
- J1.1 / R1.1; reference-side connector faces away from the LED path, so the wire goes far left/up/across to reach R1; upper perimeter
- J2.1 / VNEG; negative-supply connector is connected by an unnecessarily long rectangular return path; lower-left to lower-right

### B09 — DEFECTS
- U1B; parked amplifier is isolated at the lower left rather than grouped with U1A and identified clearly as unused; lower-left quadrant
- U1C / C1 / C2; power unit and decoupling form a separate asymmetrical block with mixed sideways symbol orientations; lower-right quadrant
- J1.1 / IN / R1; input travels upward and around the connector to reach the RC stage instead of following a direct input-to-filter path; upper left

### B10 — DEFECTS
- U1.3 / OUT / J2.1; long output wire wraps around the lower-right side of U1 to a remote J2 rather than using a short right-side output; right and bottom
- U1.1 / GND; right-pointing ground symbol at the IC clashes with downward ground-symbol convention elsewhere, obscuring the pin return direction; immediately below U1
- J1 / J3; supply and return connectors are stranded at the upper-left, separate from the timer functional block; upper-left corner

### B11 — DEFECTS
- J1.1 / R1.1; input conductor makes a large top-side U-turn because the left-side connector pin faces away from the series LED resistor; top
- J2.1 / D1.1; return conductor makes a matching bottom-side U-turn instead of a short return connection; bottom

### B12 — DEFECTS
- R1.2 / R2.1 / J1.5 / VREF; divider midpoint is spread across a long horizontal bus with no explicit VREF label near the central node; center-left
- U1C / C1 / C2; decoupling capacitors are tied through an awkward rectangular loop around the power unit instead of two obvious local rail-to-VREF branches; middle
- U1B / VREF; parked op-amp is far below the divider yet references the same midpoint, making the intended purpose of the reference network harder to infer; lower-left

### B13 — GOOD
- No blocking presentation defect in this strict rating; further refinement is possible.

### B14 — DEFECTS
- U1C / C1 / C2; power section is shoved to the far right with inconsistent sideways VPLUS/VMINUS/REF symbols and disjoint capacitor orientation; lower-right
- U1B; unused follower is separated from the active U1A by a large gap without a clear unused-channel label; upper-right
- J1.1 / R1.1; input is routed down along the connector instead of placing the connector to feed the resistor directly from the left; upper-left

### B15 — DEFECTS
- U1.3 / OUT / J2.1; long output route runs right and down, then returns left under the timer before reaching J2; lower-right
- U1.1 / REF; right-pointing return symbol beneath the timer conflicts with downward return symbols used at C1/C2/J3, complicating visual tracing; below U1
- J1 / J3; supply and return connectors are placed off to upper-left rather than grouped into a power-entry block; upper-left

## Positive results

- The generated circuits have recognizable functional relationships: op-amp negative feedback, 555 timing ladder, RC poles and a Sallen–Key filter.
- Native KiCad, ERC and exact target-netlist checks passing across the corpus is a meaningful baseline. The saved manifest records the passing checks on all 15; do not infer functional electronics correctness from these results.
- Local power-symbol usage often avoids the large global supply loops seen in October experiments, especially in B01/B02/B07.
- Most component references and values are visually legible; no obvious incorrect connection is established by these images relative to the specified target nets.

## Two different kinds of problems

**Presentation defects (what the review benchmark should label):** bad connector orientation, perimeter U-turns, output connector placed left of a regulator, inconsistent power-unit clustering, hard-to-follow long return buses, and text/owner association. These are drawing-quality issues even when netlists are correct.

**Engineering-design questions (do not let a layout reviewer silently change topology):**
- B12: a 10 kΩ/10 kΩ reference divider between supply rails has roughly 5 kΩ Thevenin impedance. It is not a stiff virtual ground; U1B is parked rather than buffering VREF. Suitability depends on load. Distinguish a midpoint reference benchmark from a production power-reference circuit.
- B05/B10/B15: the drawn 10 nF capacitor is on the 555 control input; it does **not** replace recommended supply bypassing at VCC-to-return near the IC. The intended parts lists contain no local 100 nF supply bypass; flag it for circuit-design review rather than modifying the layout benchmark target.
- B03: a 7805 regulator needs input voltage/load/thermal and datasheet-specific stability checks; the 330 nF/100 nF capacitors are not sufficient by themselves to certify a real design.
- B04: "12.4k precision" in a *value* field mixes resistance and narrative metadata and can hinder component processing, BOM or simulation; use Value=12.4k, tolerance/description in separate fields.
- For each op amp, verify common-mode/input-output swing relative to the defined rails, input bias currents, and loading. These are beyond ERC/equivalence.

## Recommended generator changes, in priority order

1. **P0 — connector pin facing and signal flow.** Decide connector orientation from the target of its outgoing pin and left-to-right block ordering. A single-pin left connector with its pin facing left should be rotated/flipped or moved before trying to route a long U-turn. Re-test B04, B08, B11, B06 and B13. Put output connectors to the right of their functional blocks (B03, B05, B10, B15).
2. **P0 — topology-aware grouping before routing.** Partition the netlist into semantic blocks (connectors, analog signal chain, regulator, 555 timing ladder, decoupling, parked op amp). Assign anchors and relative placement *before* detailed orthogonal routing. Do not allow the router to undo block hierarchy.
3. **P1 — a structural wire-detour metric.** Penalize paths that exit a convex/block envelope and re-enter without electrical need, long U-turns around terminals, repeated perimeter hops, and connector-to-nearest-device routes much longer than Manhattan optimum. Score per *net and endpoint pair*, not just raw wire length or page-box proximity; never optimize at the expense of correct connectivity.
4. **P1 — generalized supply/return blocks.** Pair each decoupling capacitor with the supply pin and reference/ground it serves; keep the unit, cap symbols and rail glyphs visually coherent. Use matching local net symbols rather than a meandering global supply path. For 555s, distinguish control-voltage bypass from supply decoupling.
5. **P1 — independent and auditable quality decisions.** Freeze exact 15 image hashes, intended graphs, schematic revisions, model settings and a human-labelled good/defect set. Score the 15 individually; all-PASS in the native checker is not an all-GOOD human baseline. Keep semantic design-review flags separate.
6. **P1 — candidate generation and ranking.** For each semantic issue, the deterministic editor can offer several electrically verified whole-block layout candidates; the small LLM should rank them and identify *why* the visual result is preferable. Include a do-nothing candidate. No unaudited freeform geometry mutation.
7. **P1 — transactional safety.** Every layout edit must preserve the authoritative net partition, component pins and ERC state, with rollback on changes. Preserve before/after PNGs and R2 measures; report if a machine PASS remains despite human DEFECTS.
8. **P2 — metadata and readability conventions.** Separate value from descriptions/tolerances; standardize symbol orientation and display conventions; add explicit REF/VREF labels for generated midpoints, and intentionally placed parked-amplifier blocks.
9. **P2 — cross-topology held-out validation.** Add MOSFET/BJT stages, LDOs with EN, digital decoupling/reset, mixed-signal interfaces, protection networks, differential amps and multi-page designs. Do not tune exclusively on these 15 cases.

## Acceptance tests worth adding

- B04/B08/B11: no source/return connector pin that faces away from its device can generate a U-turn longer than necessary without a documented constraint reason.
- B03: in a linear regulator block, VIN is visually left of U1 and VOUT/J2 visually right of U1; capacitors remain by input/output.
- B05/B10/B15: 555 output net does not route around the full timer to reach its named output connector when that connector can be placed near U1.3.
- B07/B09/B12/B14: power-unit and decoupling group has readable topology and a clear separation from signal-stage lines; alternate power symbols preserve exact KiCad connectivity.
- B06/B13: do not regress the readable two-component filter examples merely to improve a wire-length metric.
- Blind review scoring must include a true known-good group, with independent labels rather than assuming the native PASS set is GOOD.

## Assessment of readiness

**Near:** reproducible generation of native KiCad schematics matching intended part/net graphs, with enforced post-edit safety. **Still in progress:** consistent human-quality layout. **Not established:** autonomous selection of correct circuit topology/components for a specified real-world application, SPICE-level performance, footprints, PCB layout and manufacturing readiness. The main blocker is semantic layout planning (especially connectors and whole blocks), not simply more LLM context or additional single-element aesthetic rules.
