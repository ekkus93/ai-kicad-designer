# Proposed Solution: Generator Layout Open Problems (16 November 2026)

**For:** Claude / AI KiCad Designer engineering team  
**Review type:** Independent analysis and recommended implementation plan  
**Branch:** `mcp`  
**Source document:** [Generator layout: open problems](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/docs/ai_kicad_generator_open_problems_2026-11-16.md)  
**Relevant experiment:** `fixtures/pivot/experiments/supply_blocks_v11_2026-11-16_run3`  
**Relevant specifications:** `docs/pivot/REVIEWER_LOOP_SPEC.md` (R7–R8), `docs/MCP_ARCHITECTURE_TODO.md` (P6-011p/q/s/u/v/w)  
**Inspected code:** `src/ai_kicad/pivot/{supply_blocks,block_moves,connector_flow,power_symbols,schematic_review_native}.py`  
**Code observation:** Based on the `mcp` implementation inspected on 2026-11-16. This is a proposal, **not** a claim that the changes below have been implemented or tested.

## Executive recommendation

**Proceed on both primary issues, but add the missing editing operations instead of making the existing coordinate search larger.** The current generator produces electrically equivalent, ERC-clean schematics, yet its placement primitives cannot express a few common schematic transformations.

| Item | Decision | Priority | Acceptance |
|---|---|---|---|
| J3 shared REF and supply grouping | **Pursue option A**: localize common-rail connectivity, then relocate | **P1, first** | J3 grouped with J1; native netlist/ ERC/ geometry pass |
| C2 close parallel run next to 555 pin 8 | **Pursue option A**: measure parallel exposure and offer limited dogleg routes | **P1, second** | Less sustained close parallelism, without new defects |
| B12 reference capacitors | **Pursue** role-based supply-to-reference classification | P2 | VREF connection retained; both capacitors recognized |
| Sideways VPLUS arrows | **Pursue selectively**, with coordinated placement; don't endlessly search | P2 | Improvement when feasible; explicit constrained result otherwise |
| P6-011q → s → u/v/w | **Keep the sequence**, with a bounded regression checkpoint after P6-011p | Next | Blind independent readability comparison before reviewer rollout |

Do not replace native electrical checks, weaken the protected observer, modify the protected M2 composer, or hand-tune positions for named designs. All functional changes must remain behind **brief v11**; v1–v10 generated output must remain byte-identical.

## A. Why the current generator stalls

There are two missing types of edits:

1. **Topology-preserving representation changes:** replace part of a physically continuous rail wire with separate local net symbols, without changing the electrical net.
2. **Route-shape changes:** leave a crowded pin and bend away early, rather than requiring a straight wire and searching only for new part coordinates.

Specific code observations:

- `supply_blocks._try_redraw()` places a capacitor along the served pin's outward axis and generates a direct connection. Rotation and return-symbol stub are varied, but the served connection does not receive a general orthogonal dogleg.
- `supply_blocks.place_supply_blocks_text()` skips a capacitor when its distance is at most `BESIDE_MM` and its connection is `direct`. The flasher's C2 already meets those conditions despite an undesirable visual parallel run.
- `block_moves._try_moves()` invokes `move_symbols_text()` on a single unit. On shared wire trees, `move_symbols_text()` removes and reconstructs connections, which may be impossible without first converting shared REF wiring into local power-symbol connections.
- `supply_blocks.served_pins()` recognizes capacitor pairs only where one side is a recognized supply pin's net and the other is in the set of returns. A legitimate midpoint-reference node such as B12's VREF need not belong to that return set.
- Full scratch assessment on every candidate makes expanding search expensive. The open-problems document reports ~150 s for the flasher, and 300–410 s with the unsuccessful enlarged placement search.

These are limitations of the *expressible edits and their ordering*, not evidence that Qwen needs more context or that KiCad cannot represent the desired circuits.

## B. First implementation: transactional REF localization for J3

### Desired end state

**Before**: J3 shares a continuous visible REF wire with C1, so relocating J3 forces a shared-wire reroute.

~~~text
      C1
       |
       +------- J3 Return
       |
      REF
~~~

**After**: both terminals belong to the same global KiCad REF net through local symbols, but their physical wires can be short and independent.

~~~text
      C1                   J1 Supply
       |                       |
      REF                     VCC

                            J3 Return
                                |
                               REF
~~~

This is not a netlist change. A named KiCad power symbol must provide the same *actual global net identity* at each location.

### Proposed primitive

Implement a pivot-side operation conceptually named `localize_rail_connector` (or `detach_shared_rail_branch` + `attach_local_rail_symbol`). Reuse existing wire-tree, power-symbol, native edit, and connector-routing helpers.

**Exact steps:**

1. Identify J3's connector pin, intended REF net, attached physical wire tree, all terminal anchors, labels, junctions, power symbols and PWR_FLAGs. Confirm the net is an explicitly asserted/global rail; **do not apply this transform to an arbitrary signal**.
2. Snapshot the base revision and its *native exported* expected pin-net partition. Use the intended design's pin/net mapping and independently check the symbol's global KiCad net name.
3. Determine the **minimal connector-specific branch** to detach. Do **not** delete the entire shared wire tree. If the original branch is not uniquely detachable, offer a more controlled rewrite: reconstruct only that net's essential fixed terminal groups with local REF symbols.
4. Ensure C1 and every other fixed REF terminal remain connected to REF after the branch is detached; add a local REF symbol on the fixed group if needed. Existing attached decorations must be retained or replaced intentionally.
5. Move J3 toward J1, carrying or recreating its appropriate REF symbol, label and PWR_FLAG. J3 can be disconnected *physically* from C1, but must remain on the *same global electrical net*.
6. Reposition conflicting fields for J1 and J3 together, and check that the PWR_FLAG still establishes intended ERC power-source semantics. Do not duplicate flags needlessly.
7. Remove orphaned junctions, redundant segments, or dangling labels only where safe.
8. Run geometric and field tests on the complete trial, followed by native KiCad netlist export and ERC. Commit the candidate atomically only if every hard gate passes; otherwise discard the scratch revision and record a structured refusal.

**Suggested pseudocode (conceptual, not existing API):**

~~~python
def localize_rail_connector(schematic, connector, rail_net, target):
    candidate = schematic.clone()
    before = export_native_pin_partition(schematic)
    assert globally_named_asserted_rail(candidate, rail_net)

    graph = extract_wire_graph(candidate, rail_net)
    detach_connector_specific_branch(candidate, graph, connector)
    ensure_global_rail_connection(candidate, graph.fixed_terminals, rail_net)

    relocate_connector_and_its_decorations(candidate, connector, target)
    ensure_global_rail_connection(candidate, [connector.pin], rail_net)
    reflow_affected_fields(candidate)

    assert export_native_pin_partition(candidate) == before
    assert native_erc(candidate).passes_required_checks()
    assert geometry_and_field_checks(candidate).pass_all_hard_checks()
    return candidate
~~~

### Safety details that cannot be skipped

- Compare **native pin partitions**, not only intended net-name text or cached geometry.
- Verify no adjacent/unrelated net has been merged. Check the set of terminal groups, not just J3/C1.
- Preserve pin-mounted flags and any power-driving indication; `PWR_FLAG` is not a substitute for a real supply connection.
- Distinguish an asserted global rail from a merely coincidentally named local label.
- Never remove a shared wire segment if doing so isolates another pin that lacks its own effective REF connection.
- A failed scratch candidate must not become the current revision.
- Cache failures by base SHA and canonical action, to avoid repeating the same impossible move.

**Acceptance test:** In the flasher, J3 is grouped close to J1 (target: within the existing `GROUPED_MM` criterion where feasible), original C1 and all U1 reference connections remain exactly as specified, ERC and all previously passing hard checks pass, and the visual power-entry region is clearly grouped. Run the same operation on the already-good regulator and both astable variants to detect regressions.

## C. Second implementation: close parallel conductor exposure for C2

### Why minimum clearance did not help

NE555 pins 5 (CONT) and 8 (VCC) leave the body only 2.54 mm apart. No placement algorithm can increase that inherent pin spacing. The visual complaint is an extended wire parallel to the VCC arrow/wire, **not** the first unavoidable millimetres near the pin.

The 1.27 mm KiCad routing grid is smaller than the separation between these pins: checking only "within one grid step" would miss the exact defect. Use a configurable separation window that includes 2.54 mm plus a small coordinate tolerance.

### Metric

On segments belonging to *different* nets, measure overlapping projection length of collinear-direction (parallel) runs whose perpendicular distance is at most a threshold `D` (start with **D = 2.54 mm + tolerance**).

For each pair, compute:

~~~text
exposure = max(0, overlapping_parallel_length - unavoidable_pin_neighborhood)
~~~

Aggregate separately by net pair and record exact endpoints/witnesses. **Do not double-count** the same length when a net has split collinear segments, and treat the tiny unavoidable pin-exit region as an exemption. This is a *schematic readability* score, not an electrical PCB spacing rule.

Start with a **report-only** metric and visually check false positives. Wires that run in parallel intentionally within a clear bus should not automatically count as defects; the measure should use semantic pin/net context when possible.

### New candidate generation

Make the control-pin bypass eligible for re-layout even if it already passes the "near and direct" criteria, provided measured parallel exposure exceeds an advisory threshold.

For a pin such as U1.5, offer a tiny set of **route-shape** candidates rather than more capacitor locations along the same pin axis:

- current direct layout (baseline/keep);
- pin exit by 1 grid step, then elbow **away from** neighboring pin 8 and route to an offset capacitor;
- pin exit by 2 grid steps, then elbow away, if still valid;
- two candidate capacitor locations near the served pin, with correctly oriented return symbols and minimal label conflict.

Use standard orthogonal KiCad wires, valid snapped endpoints, and a proper connection at pin 5; ensure the route is unambiguous with respect to VCC at pin 8.

**Optimization order:** hard netlist/ERC/geometry constraints first; then less sustained close parallelism, recognizable pin association, conventional REF orientation, and finally shorter wire length/fewer bends.

**Explicit bounded budget:** no more than **12 cheap geometric candidates**, then **3 full KiCad scratch assessments** for this local issue. Count and report actual calls, latency, and rejected reasons. If nothing safely beats the direct route, retain it with a known presentation limitation; do not stall the release.

### Acceptance tests

- New metric flags the current C2–U1.8 close parallel run.
- An accepted dogleg candidate measurably reduces the exposed parallel length while remaining close enough to U1.5.
- Native ERC, intended-netlist equivalence and hard layout checks remain passing.
- Ordinary adjacent connections do not trigger spurious severe penalties.
- Worst-case candidate-validation budget remains bounded and recorded.

## D. B12: generalize supply-to-reference capacitor detection

In `supply_blocks.served_pins()`, the current condition is effectively:

~~~python
if net in supply_pins and other in returns:
    ...
~~~

This excludes capacitors attached to a reference voltage such as a two-resistor midpoint VREF, which is *not* necessarily a ground or return rail.

**Proposed generalized model:**

~~~text
Capacitor role = local supply-to-reference bypass / supply stabilization
supply_net = VPLUS (or VMINUS)
reference_net = VREF (explicitly recognized from topology)
served_pin = IC supply terminal actually on supply_net
~~~

Infer candidates from intended component/net graph, recognized supply-pin roles and reference-generation topology, not only string matches on net labels. Keep signal filter capacitors distinct from power/reference support capacitors.

For B12, preserve both VPLUS–VREF and VMINUS–VREF connections, and ensure neither is silently converted to VPLUS–GND or VMINUS–GND. The existing warning about the 10 kΩ/10 kΩ divider's approximately 5 kΩ Thévenin resistance remains a **design-review warning**, not a reason for the layout engine to change the target topology.

**Acceptance:** classify and locally place both B12 capacitors, preserve exact partitions, prevent overlap, and test at least one non-ground-reference example besides B12.

## E. Sideways VPLUS symbols: bounded block-level optimization

The current `power_block_directions()` correctly records upward orientation as the preferred direction for positive-supply glyphs, but attempts to turn an arrow can collide with text, wires and other components.

**Recommendation:** treat upward VPLUS as a strong *soft visual preference*, not a reason to violate a hard clearance rule.

Offer a limited group of trials that jointly consider: (a) symbol orientation, (b) short attach stub or route, (c) related capacitor/body position, and (d) reference/value text placement. Score the whole block, not the glyph in isolation. Cap the search to a few canonical arrangements, verify the best feasible trial, and record a constrained/known-gap outcome when none improves the schematic. Never silently reinterpret VPLUS/VMINUS connectivity.

## F. Performance and architecture

### Use staged candidate evaluation

| Stage | What runs | Purpose |
|---|---|---|
| 1: cheap structure | exact current nets, move feasibility, pin grid, symbolic graph, bbox prefilter | Reject impossible edits before creating full schematic |
| 2: geometry | actual route existence, symbol/field clearance, page bounds, preliminary wire metrics | Rank a small feasible shortlist |
| 3: native KiCad | full scratch netlist export, ERC, independent layout checks | Definitive accept/reject for every committed edit |

Native validation is **non-negotiable before keeping an edit**, but not necessary for every unpromising coordinate permutation. Never label a geometry-only candidate "native validated."

Cache native assessments by immutable **base schematic blob/revision + canonical action + grid-snapped geometry + brief/toolchain/KiCad version**. Invalidate across any content/config/version change. Collect diagnostics on proposed, geometry-passed, native-attempted, accepted, refused, and budget-exhausted candidates, plus elapsed wall time.

### Long-term: add a pivot-side semantic layout layer

Keep M2 composer and protected observers unchanged. Build a compact pivot-side representation of *functional blocks*, *nets*, *pin roles*, *interface ownership* and *allowed visual connection mechanisms*, then generate a handful of atomic native KiCad transformations.

A visible signal/feedback line and a named rail are different presentation concerns even when both are edges in the electrical graph. Route signal paths to show topology; use local power symbols when they improve rail clarity; keep power entry and return grouped. This should generalize without per-design coordinate rules.

## G. Implementation order and pass/fail criteria

| Order | Task | Hard acceptance |
|---|---|---|
| **1** | REF rail-localization primitive, then J3 move | J3 near J1; no net merges, drops, ERC or geometry failures |
| **2** | Parallel-exposure measurement and bounded C2 elbows | Lower exposure; appropriate support locality; full native PASS |
| **3** | Generalize B12 capacitor role classification | Both supply-to-VREF parts recognized; original nets unchanged |
| **4** | Bounded whole-block VPLUS re-aim | More consistent glyphs where safe; traceable refusal otherwise |
| **5** | Candidate-budget / cache instrumentation | No runaway 300–410 s C2 search; validation counts reproducible |
| **6** | P6-011q drawing conventions | Remove duplicate symbols, jogs and redundant dots without connectivity changes |
| **7** | P6-011s regenerated 15-design corpus and blind A/B | Demonstrate genuine readability improvement vs v10, preserve regressions |
| **8** | P6-011u → v → w: Qwen menu and qualification | Model selects among safe verified edits; show improvement vs generator and KEEP |

If a local P6-011p cosmetic objective cannot be improved safely under the defined budget, **document it as constrained and proceed**, rather than letting a single 555 fixture prevent broader work. No unverified exception should be declared a passing implementation of a mandatory acceptance clause: revise the spec explicitly if necessary.

### Targeted regression matrix

| Fixture/test | Positive and negative requirements |
|---|---|
| Flasher J3 shared REF | Group connector without changing C1, U1.1 or any other native REF terminal; preserve PWR_FLAG role |
| Regulator and both timer variants | Existing successful power-entry layouts must not regress |
| Flasher C2 parallel exposure | Detect existing long close parallel run; candidate decreases exposure |
| Neighboring-pin synthetic | Avoid falsely condemning inevitable short parallel pin exits |
| B12 VREF decoupling | Recognize two distinct rail-to-reference capacitors; keep net identity |
| Op-amp sideways VPLUS | Improve where feasible; refuse when blocked without damaging layout |
| Legacy briefs | Verify v1–v10 schematics remain byte-for-byte identical on frozen fixtures |
| Budget exhaustion | Deterministic cap and structured refusal, no unbounded geometric search |
| Transaction rollback | Deliberate REF/VMINUS short or orphaned pin rejected before becoming current |
| After-edit independent assessment | Native/ERC/equivalence/required layout checks independently PASS |

Suggested existing test files to extend: `tests/pivot/test_block_placement.py`, `test_connector_flow.py`, `test_schematic_group_edits.py`, `test_power_symbols.py` and an additional focused supply-block / parallel-exposure test module.

## H. Specification correction and stop policy

The November 16 clean-orientation acceptance clause currently asks for at least one grid-step clearance from unrelated pins/wires. That is not achievable at every 555 pin because the library symbol fixes the pin separation. Replace the requirement with a measured *extended parallel-exposure* preference, explicitly exempting unavoidable local pin exits.

Suggested specification wording:

> Among electrically and geometrically valid local bypass-capacitor arrangements, prefer placements and wire routes that minimize extended close parallel runs beside unrelated nets, preserve clear association with the served pin, and follow conventional reference-symbol orientation. A bounded search may report a documented no-safe-improvement outcome rather than altering connectivity or violating geometry.

Keep the existing P6-011p grouping requirement for J3 if the new transactional operation makes it feasible. If the required layout cannot be achieved within the budget, record and triage the specific blocker; do not change "FAIL" into "PASS" merely because ERC remains clean.

## Conclusion / instructions for Claude

**First implement localize-and-relocate for J3's shared REF rail.** That is a controlled, reusable operation with a crisp electrical-equivalence oracle. **Second implement parallel-exposure scoring and dogleg routes** for C2; never attempt to solve an intrinsic 2.54 mm pin spacing by enlarging a minimum-clearance rule. Then broaden supply-to-reference capacitor handling, make power-arrow orientation block-aware, and complete P6-011q.

Do not respond to these issues by increasing model context, introducing NE555-only layout hacks or multiplying full KiCad validations. Expand the *expressiveness of deterministic, electrically constrained layout edits*, test across circuit families, and re-rate the new 15-design baseline independently before investing further in Qwen reviewer selection.

**Status:** Recommendations only; implementation, tests and CI remain to be completed by Claude.
