# Independent schematic-readability review — V11 baseline (for Claude)

**Reviewer:** ChatGPT (independent visual assessment)  
**Review date:** 2026-11-17  
**Repository / branch:** ekkus93/ai-kicad-designer / mcp  
**Source brief:** [V11 baseline ratings request](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/docs/ai_kicad_baseline_v11_ratings_for_chatgpt.md)  
**Corpus:** fixtures/pivot/experiments/review_baseline_v11_2026-11-17_run1/blind/ (B01–B15)

## Executive findings

The generator is making meaningful progress. The uncomplicated RC and LED drawings are now largely clear, and improvements to the regulator's input/output order and 555 power-interface grouping are visible. Nevertheless, **I would accept only 4 of the 15 images as sufficiently polished for the specific standard in the review request: something I would accept from a careful electrical engineer without requiring a presentation change**. The remaining 11 have identifiable drafting problems, ranging from minor symbol placement to noticeably disjoint functional blocks.

The 4/15 verdict is a **subjective binary presentation assessment of this one sample**, not a project-completion percentage or a claim that 11 schematics are electrically incorrect. Claude's input brief reports that all 15 pass KiCad ERC, native netlist equivalence, and enabled layout checks; those automated results were not independently rerun as part of this visual review. Electrical *suitability for an application* remains a separate topic.

The shuffled B-codes should not be equated with V10 codes. V10's previous independent review accepted 5/15 by the same general criterion. A 5-to-4 count change alone is not proof of regression: to measure progress, make a blinded, randomized, paired V10-versus-V11 comparison by **underlying circuit**, with both versions judged by the same rubric.

**Primary engineering conclusion:** improving KiCad-valid geometry is no longer sufficient. Most remaining defects are semantic: how power, unused units, signal stages, decouplers, return paths, and interfaces should be *grouped and arranged* for human readers.

## Rating protocol and scope

- I examined the B01–B15 close-ups (_2.png) and the full A4 pages (_1.png).
- A **good** label means the layout is clear and conventional enough to accept for this schematic-presentation benchmark; it is not a certification of a manufacturable design.
- A **defects** label means one or more corrections would make the schematic materially clearer.
- Observations in the **design-level issues** section are **not** used as layout defects: those may require changes to the intended electrical specification, not just rearrangement of its drawing.
- Issues identified visually as suspicious are not treated as proven netlist faults unless supported by the exported netlist/ERC evidence.

## Per-drawing verdicts and actionable notes

| Code | Circuit | Verdict | Primary reason |
|---|---|---|---|
| B01 | L7805 regulator | **defects** | Supply/return interface clutter and an odd input-side loop |
| B02 | RC low-pass | **good** | Clear left-to-right R–C signal path |
| B03 | NE5532 dual buffer | **defects** | Disjoint power, active, and parked amplifier blocks |
| B04 | NE555 astable (GND) | **defects** | Upside-down control-capacitor presentation; long output drop |
| B05 | NE5532 inverting gain | **defects** | Incoherent supply block / VMINUS arrow direction |
| B06 | NE555 LED flasher | **defects** | Crowded entry/return symbols and awkward C2 orientation |
| B07 | NE555 astable (REF) | **defects** | Same control-capacitor and output-routing patterns as B04 |
| B08 | LED with long values | **good** | Compact, readable series path and legible descriptions |
| B09 | RC-to-buffer | **defects** | Unnecessary input detour and detached power presentation |
| B10 | NE5532 non-inverting gain | **defects** | Unused op-amp unit isolated; power section out of balance |
| B11 | RC high-pass | **good** | Clear series capacitor and shunt resistor |
| B12 | LED between reference and negative supply | **defects** | Right-to-left functional presentation is unnecessarily hard to follow |
| B13 | Sallen–Key filter | **defects** | Separate power block poorly integrated with the filter / amplifier units |
| B14 | LED series | **good** | Recognizable, clean simple LED path |
| B15 | Dual-rail midpoint reference | **defects** | Confusing VREF/rail/capacitor presentation and block placement |

### B01 — Regulator — defects

**Good:** Supply input J1 is on the left, L7805 in the middle, regulated output J2 on the right. Both bypass capacitors correctly read as input/output shunts to REF in the drawing, and the general power flow is now conventional.

**Bad:** The input connection includes a small rectangular detour just above/near J3 and the regulator input, with closely packed supply-entry annotations. The J3 reference/value placement competes with that wire and nearby power decorations. Visually this is much improved over versions with J3 stranded, but it does not yet look clean.

**Fix:** Reserve a compact power-entry region for J1/J3/flag/REF and route VIN directly from J1 to C1/U1. Place label and PWR_FLAG branches outside the connector's text footprint. Prefer a straight return reference row, without changing any pin-net assignments.

### B02 — RC low-pass — good

R1 (10 kΩ) is in the left-to-right signal path, C1 (10 nF) shunts the output to the return, and J3 is near J1. I would accept this schematic as a reasonable small filter drawing. Minor aesthetic optimization of wire lengths is optional, not necessary.

### B03 — Dual buffer — defects

**Good:** Both op-amp symbols are recognizable as voltage followers. C1 and C2 are correctly depicted as supply-to-REF bypass parts according to the intended topology.

**Bad:** Connector J1, power unit U1C, active unit U1A and parked unit U1B are spread as separate islands; the power unit sits between connector and signal stage rather than reading as a cohesive supply block. VPLUS/VMINUS labels project sideways and the 100 nF capacitors are geometrically asymmetric. The unused stage is below the active stage without a clear local association.

**Fix:** Place U1A/U1B as the recognizable signal/parked-unit pair; put U1C with its two bypass capacitors in a compact, separate power section; favor conventional rail glyph directions when space allows. This needs a group-layout proposal, not independent last-mile symbol rotation.

### B04 — 555 astable (GND) — defects

**Good:** R1/R2/C1 timing chain and the connections to DISCH/THRES/TRIG are easy to trace. J1 and J3 are now grouped.

**Bad:** C2 (CONT 10 nF) has its GND symbol above the capacitor, creating upside-down visual flow. The C2 wire extends parallel to VCC pin 8 in a crowded area. The output J2 is substantially below/right of the oscillator and is reached by an unnecessarily tall down-and-around route.

**Fix:** Use a small set of validated dogleg routes leaving CONT pin 5 away from pin 8; place the capacitor with its return conventionally directed down if feasible. Place J2 in the oscillator output's horizontal flow, so OUT is not a long dangling leg. Do not attempt to solve fixed pin spacing by increasing the minimum clearance requirement.

### B05 — Inverting amplifier — defects

**Good:** 10 kΩ input resistor, 100 kΩ feedback resistor, U1A reference input, and unused U1B's feedback are clearly legible. The signal stage is stronger than the supply section.

**Bad:** U1C appears substantially below the signal blocks, with VMINUS drawn by an upward-pointing arrow on the lower bypass path and an awkward rail arrangement relative to C2. The visually disconnected power/decoupler section reduces the drawing's cohesion.

**Fix:** Apply a standard topology-aware power-block layout to U1C/C1/C2: make relative net identities unambiguous, keep return symbols pointing toward return, prefer appropriate supply-symbol orientation, and score visual relationship to the active package. Do not change the specified dual-rail supply nets.

### B06 — 555 LED flasher — defects

**Good:** R1/R2/C1 are in the conventional timing arrangement; LED D1 and series resistor R3 sit together near the output. J1 and J3 are now together, a specific improvement over older 555 drawings.

**Bad:** C2's REF symbol sits above the 10 nF control-voltage capacitor; its lead shares a visually crowded corridor with the VCC pin 8 connection. The J1/R1 area has two nearby VCC glyphs plus a power flag. The REF power flag appears on an unnecessary-looking dangling branch beneath C1. These are not necessarily electrical errors, but they complicate the drawing.

**Fix:** Apply the dogleg/parallel-exposure optimization at C2; canonicalize redundant same-net power symbols; move the REF flag to a short, deliberate power-entry branch next to J3, without changing ERC semantics.

### B07 — 555 astable (REF) — defects

This resembles B04, with REF rather than GND. The timing network is readable and connectors are grouped, but C2's REF symbol is above the capacitor, the control-voltage lead runs in the crowded pin-5/pin-8 channel, and the output connector sits at the end of a long vertical drop. Reuse the same generalized fixes; do **not** introduce an additional circuit-specific 555 layout rule.

### B08 — Long-label LED — good

J1 → R123 → D24 → J2 is exceptionally clear compared with older large-loop drawings. The unusually long resistor and LED descriptions remain readable and unambiguous. **Data-quality note only:** the part value '12.4k precision' and LED description would be easier for BOM, simulation and part selection if quantitative value and descriptive metadata were stored separately. Do not change the requested netlist because of that annotation.

### B09 — RC-to-buffer — defects

**Good:** R1/C3 form a recognizable low-pass stage driving U1A as a voltage follower; the parked U1B is obvious.

**Bad:** The connection from connector J1 pin 1 heads upward and around before reaching R1, despite a largely straight signal line being possible. The supply power unit/decouplers form a detached visual cluster below the amplifier stages, including a reversed-looking VMINUS marker. There is extra horizontal whitespace within an otherwise modest circuit.

**Fix:** Orient and place J1 as a left-side source whose pin exits toward R1; reflow the signal block as one unit; reserve an adjacent, coherent power block. Penalize signal-path detour relative to an unobstructed shortest orthogonal route.

### B10 — Non-inverting amplifier — defects

**Good:** Feedback topology around R1/R2 and U1A is recognizable and electrically credible relative to the specified design.

**Bad:** U1B is located high above the actual amplifier, apparently detached from the package's active signal context. U1C/C1/C2 are far left of the signal block. The page is geometrically valid but visually fragmented, and power arrows are not conventionally arranged.

**Fix:** Group U1B near U1A as a parked unit without allowing it to compete with signal routing. Group U1C and bypass capacitors in a compact local power panel. Solve both as group moves in one constrained layout proposal, then perform full native checks.

### B11 — RC high-pass — good

C1 in the signal path and R1 shunting OUT to J3 Return are clear. The layout is simple, conventional and unambiguous. Minor whitespace and wire-length changes are optional.

### B12 — Negative-supply LED — defects

**Good:** R1 and D1 form a clear series branch and no connectivity violation is evident from the drawing.

**Bad:** The diagram places 'Negative supply' on the left and 'Reference' on the right, while the conventional current-direction reading of this indicator is from the higher-potential reference, through the resistor/LED, toward the negative supply. It therefore reads right-to-left, and the odd top and lower U-shaped wires make this simple indicator unnecessarily hard to scan.

**Fix:** For a two-terminal indicator, put the electrical source/higher-potential endpoint (here reference) on the left or top, then resistor and LED, then negative supply/return on the right or bottom. Preserve the actual diode polarity and specified pin-net graph; don't infer wiring solely from connector names.

### B13 — Sallen–Key filter — defects

**Good:** The two-resistor path, shunt C3, return/cross-network C4, buffer U1A and OUT node are reasonably recognizable; no necessary netlist issue is apparent from the image.

**Bad:** A relatively long C4 loop spans the signal section; some of that may be necessary to communicate the active filter, but the power block U1C/C1/C2 sits well to the right, isolated from U1A/U1B. The unused U1B and active U1A have an awkwardly tight vertical pairing beneath the feedback. Supply glyphs around U1C are not optimally oriented.

**Fix:** Preserve the filter's recognizable feedback topology, but plan the network and output/feedback arcs first, reserve a compact area for both op-amp units and their power panel, and optimize the route of C4 without allowing wires through components or labels.

### B14 — LED series — good

J1 → R1 → D1 → J2 is a readable series chain. The slightly long horizontal connector extensions are acceptable for the benchmark and not sufficient to justify a defect verdict.

### B15 — Dual-rail midpoint reference — defects

**Good:** R1 and R2 clearly form the 10 kΩ/10 kΩ divider, with VREF between them. The capacitors visibly return to VREF and bridge toward the corresponding rails as intended.

**Bad:** VREF is carried across a long horizontal bus that also interacts visually with the U1C power-symbol region; supply arrows are inconsistently oriented. The op-amp signal/unused units are separated from the divider and power panel without a clear block relationship. The drawing is valid-looking but requires more effort to understand than the circuit merits.

**Fix:** Form a compact VPLUS–R1–VREF–R2–VMINUS reference column, group both supply-to-VREF capacitors as a symmetrical pair close to their served supply rails, and place U1C/U1A/U1B in a clearly organized second block. Retain the distinction between VREF and an actual ground.

## Independent electrical-design notes (NOT scored as layout defects)

These should be part of a separate engineering/design-requirements review, not silently inserted into a connectivity-preservation benchmark:

1. **555 variants B04/B06/B07:** 10 nF on the CONT pin is *not* dedicated VCC-to-GND decoupling. A practical bipolar NE555 design generally needs a local supply bypass capacitor, typically 100 nF ceramic close to pins 8 and 1, subject to the device/application datasheet.
2. **B06 LED indicator:** with the resistor/LED connected from VCC to OUT, the LED is active-low (the 555 sinks current). This is valid if intended.
3. **B15 divider reference:** two 10 kΩ resistors create about 5 kΩ of Thevenin output resistance when the supply rails are stiff. This is not automatically a low-impedance virtual ground for external loads. Do not connect the idle U1B as a reference buffer without an approved design change.
4. **B01 L7805:** suitability depends on VIN range, load, dropout, heat dissipation, stability and actual capacitor technology/placement.
5. **B08 component metadata:** separate the resistance's numeric value from words such as 'precision' and make LED identity/parameters structured.

The drawing benchmark does **not** validate component footprint completeness, electrical operating limits, SPICE behavior, or PCB manufacturability.

## Root-cause diagnosis

### Semantic layout vs. geometry

The 15/15 automatic PASS result is compatible with the observed readability defects because geometric checks typically catch collisions and missing connections, not bad **relationships**: which connector belongs with a return, which op-amp units should form one cluster, where a power panel belongs, and which direction a functional signal or current flow should read.

The repeated patterns are:

- Power-unit U1C and its capacitors placed independently of active U1A/parked U1B.
- An inappropriate glyph/arrow orientation surviving once the geometry already passes.
- 555 control capacitor close to its pin, but with sustained close parallel wiring and upside-down return presentation.
- J1 or J2 attached through a legal but visually unnecessary detour.
- Power flags and repeated rail symbols accumulating near otherwise simple connectors.

Those call for **structural candidate generation and a calibrated quality function**, not a larger coordinate search on each individual symbol.

### Avoid overfitting the corpus

Do not add a special 'B06 555 C2' rule or 'B15 divider' coordinates. Infer semantic roles from intended pin/net topology (e.g., power entry, reference, active stage, parked unit, bypass, signal filter, feedback) and generate reusable block templates or constrained relations.

## Prioritized development recommendations for Claude

| Priority | Workstream | Implementation guidance | Acceptance evidence |
|---|---|---|---|
| **P1** | Coherent power-unit layout | Group U1C, C1/C2 and supply/REF symbols into one block; jointly score position and glyph directions | B03/B05/B09/B10/B13/B15 visually improve without native netlist change |
| **P1** | 555 C2 route-shape editing | Measure near-parallel exposure on different nets; allow bounded elbow routes and conventional return placement | B04/B06/B07 lose sustained CONT/VCC visual crowding; ERC/netlist unchanged |
| **P1** | Active + parked op-amp affinity | Place U1B near U1A subject to clearance from functional feedback paths | B03/B10/B13 grouped without additional overlaps |
| **P2** | Source/return/interface flow | Place related connector terminals before routing; penalize detours and backwards flow | B01/B09/B12 have clearer interface and signal path |
| **P2** | Power-symbol / PWR_FLAG cleanup | Detect redundant glyphs and retain only purposeful flags, placed near power entry | B06 supply annotations clear; ERC remains PASS |
| **P2** | Calibrated visual scoring | Rate paired candidate images blind and correlate component-affinity, wire-detour and text/arrow metrics with expert preference | Documented before/after wins, disagreements, and negative cases |
| **P2** | Separate electrical-design review | Check supply limits, missing bypass, reference loading and component data | Design warnings reported separately; benchmark circuit not silently modified |

### Preferred pipeline

1. Extract the electrical graph from the intended circuit and native KiCad netlist, and identify unit/connector roles.
2. Propose functional block groupings and relative constraints: input → processing → output; power entry with return; active/parked units; supply-to-reference bypass blocks.
3. Produce a **small bounded set** of coherent layouts (block positions, orientations, local net-symbol strategies and wire-route shapes).
4. Cheaply screen for symbol/text clearance, achievable routing and obvious detours; retain only a shortlist.
5. For **every kept edit**, run native KiCad export, ERC, exact electrical-equivalence comparison and hard layout checks in a scratch transaction.
6. Score the passing candidates for semantic readability and compare against KEEP; do not force edits when no candidate materially improves readability.
7. Use Qwen3.5 9B as an optional reviewer choosing among **prevalidated** alternatives, not as the owner of arbitrary low-level coordinates.
8. Record candidate hashes, metric deltas, rejected reasons and human ratings so each improvement is reproducible.

## Suggested regression plan

At minimum, freeze the V11 artifacts (image hashes, native schematics and intended partitions) and add tests for:

- B01 power-entry grouping with J3 and no input-loop/text overlap.
- B03/B05/B10 power-unit placement and glyph orientation with REF/VPLUS/VMINUS unchanged.
- B04/B06/B07 pin-5 capacitor routes: shorter close-parallel exposure without introducing a pin-8 connection or losing KiCad equivalence.
- B06 redundant power symbols/flag branches cleaned without ERC regression.
- B09 connector input reaches R1 without the unnecessary top-edge detour.
- B12 LED direction reflects reference-to-negative current path while preserving diode pin polarity.
- B13 filter loop retains topological visibility while U1C joins a coherent IC grouping.
- B15 VREF net remains separate from VPLUS/VMINUS and all support capacitors keep their original nets.
- B02/B08/B11/B14 stay at least as readable: do not fix one family at the expense of accepted baselines.
- Legacy brief compatibility and explicit budget-exhaustion behavior.

**Blind evaluation:** match each V10 and V11 image by underlying circuit *after* independently rating each, randomize A/B order, collect preference/tie/defect-specific ratings from at least two raters when possible, and report both per-circuit and overall paired results. Do not infer improvement from total wire length or the crude pass count alone.

## Conclusion

**V11 has real local gains but is not yet a reliably professional schematic drafter.** The strongest progress is in uncomplicated RC/LED circuits and parts of the connector/power-entry logic. The stubborn defects are consistent and explainable: power blocks, op-amp subunits, return interfaces and close parallel routes need **semantic group planning and safe, coordinated edits**.

The next milestone is not '15/15 ERC PASS'; it is a measurable increase in independent preference for the generated drawings across circuit families, with electrical equivalence and safety retained. Prioritize topology-aware power-block layout and the C2 routing primitive, then demonstrate improvement on a new frozen benchmark rather than over-optimizing the specific images shown here.
