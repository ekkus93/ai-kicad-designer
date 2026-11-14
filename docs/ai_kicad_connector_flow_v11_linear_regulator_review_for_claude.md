# AI KiCad Designer — V11 Linear Regulator Schematic Review

**Reviewed:** 2026-11-14  
**Branch:** `mcp`  
**Experiment:** `fixtures/pivot/experiments/connector_flow_v11_2026-11-14_run1/linear_regulator/`  
**Drawing:** [V11 drawing](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/connector_flow_v11_2026-11-14_run1/linear_regulator/review-images/drawing.png)  
**Drawing Git blob SHA:** `6dcdeef94878368df649fc00be8374f52cb79295`  
**Earlier comparison:** [V10 baseline drawing](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/drawings/linear_regulator/review-images/drawing.png)

## Verdict

**V11 is an improvement over V10, but it looks strange for good reasons.** Electrical connectivity passes, and the input/output connector flow is now sensible. The return connector J3 remains stranded far from the rest of the regulator, and some short wire jogs and junction marks make the otherwise straightforward circuit look more complicated than necessary.

This is primarily a **presentation-quality problem**, not a demonstrated electrical netlist error. A passing ERC or intended-netlist comparison is not a functional evaluation of real-world electrical performance.

## 1. What's good

The circuit contains:

| Component | Value | Purpose |
|---|---|---|
| U1 | L7805 | 5 V linear regulator |
| C1 | 330 nF | Input bypass capacitor |
| C2 | 100 nF | Output bypass capacitor |
| J1 | Supply input | Unregulated input connector |
| J2 | Regulated output | 5 V output connector |
| J3 | Return | Common reference connector |

The saved native assessment finds the expected and observed net partitions match:

- **VIN:** J1.1, C1.1, U1.1.
- **VOUT:** U1.3, C2.1, J2.1.
- **REF:** J3.1, C1.2, C2.2, U1.2.

The saved KiCad ERC contains no violations. The experiment reports `native_tools`, `erc`, `electrical_equivalence` and all enabled layout checks as PASS. Four ERC categories are ignored: `single_global_label`, `four_way_junction`, `simulation_model_issue`, and `footprint_filter`.

**The left-to-right flow is much better.** It now reads:

**J1 → VIN / C1 → U1 → VOUT / C2 → J2**

In V10, the output connector was incorrectly placed to the left of the regulator. In V11, J2 is on the correct side and J1 faces into the circuit. The regulator, capacitors and REF bus are grouped reasonably well, making the three-terminal circuit recognizable.

## 2. What's bad and how to fix it

### A. Return connector J3 is stranded at upper-left — medium priority

J3 appears separated from J1, U1 and the common REF bus. Because a REF power symbol identifies its net, this is electrically valid; visually, however, it looks like an unrelated component.

**Fix:** Place J3 directly below or near J1 as part of the power-entry interface, or attach J3 to the common REF bus below C1/C2. The generator should understand that the return connector belongs with the supply interface, not just find the nearest connection to a net with the same name.

### B. U1 ground/reference wiring has a needless jog — low priority

The connection from U1 pin 2 moves downward, makes a short horizontal offset, then meets the REF bus. Two junction dots appear very close together. This is electrically valid but visually awkward.

**Fix:** Prefer a single straight connection to the reference bus when geometry permits, and post-process tiny unnecessary jogs. Always re-export the native KiCad netlist after simplifying a route.

### C. VOUT has redundant-looking junction geometry — low priority

There are multiple nearby dots along the short VOUT wire. The C2 tap is meaningful, but the other dot near the VOUT label doesn't seem to clarify a distinct branch.

**Fix:** Canonicalize collinear wire segments and simplify superfluous visual junctions without deleting any junction required for native KiCad connectivity. Inspect the actual netlist rather than trusting rendered pixels.

### D. Connector placement is not coherent as a *group* — medium priority

J1 and J2 are appropriately positioned, but J3 is left behind. The current connector-flow step understands directional signal flow better than **return-path affinity**.

**Fix:** Represent VIN, VOUT and REF as a functional power-interface group before optimizing individual connector positions. Select a coherent group arrangement and then handle the local routing and text.

### E. The result still looks algorithmically composed

The regulator/capacitor section is relatively clear, yet the overall composition feels unfinished: a correct electrical graph has been turned into a geometric layout without treating the external interface as one engineering object.

**Fix:** Score semantic grouping explicitly, and let the engine move a connector together with its related symbol, label, power flag and local wires.

## 3. Why J3 remained where it is

The experiment's `presentation.json` records:

| Connector | Operation | Outcome |
|---|---|---|
| J1 | Mirror in place | Applied |
| J2 | Move next to VOUT | Applied |
| J3 | Try alternate placements | None accepted |

The J3 moves were refused because different candidates caused:

- the J3 value field to overlap a power flag;
- a wire to cross through the J3 symbol body;
- new field-clearance problems; or
- ambiguous wire/net attribution.

A connector-flow attempt also failed the `rail_route_detour` check for REF before a later plan succeeded.

**This is an architectural clue:** the engine's local move operation cannot solve a problem that requires moving several associated items together. J3 cannot be placed freely while its REF symbol, power flag, local wires and label geometry remain fixed.

Rather than weakening checks, generate a new **transactional composite candidate** that relocates the entire affected cluster, then validate it as a unit.

## 4. What a better arrangement would communicate

A conceptual target is:

```text
                           U1
                          L7805
                       ┌─────────┐
    VIN ─────────┬──────┤ IN      │
                 │      │        │
                 │      │  OUT   ├──────┬────── VOUT
                C1      │        │      │
               330n     │  GND   │     C2
                 │      └───┬────┘    100n
                 │          │          │
    REF ─────────┴──────────┴──────────┴────── REF
```

J1 should attach to VIN, J2 to VOUT, and J3 should be placed near the supply input or REF row. This is a conceptual grouping, not literal KiCad pin geometry.

## 5. Recommendations for Claude / AI KiCad Designer

| Priority | Improvement | Expected benefit |
|---|---|---|
| **P1** | Return-connector / power-interface affinity | Stops J3 appearing unrelated to its power circuit |
| **P1** | Transactional relocation of connector, REF symbol, PWR_FLAG, labels and wires | Makes feasible layouts that isolated moves reject |
| **P1** | Model VIN–VOUT–REF as a functional interface group | Generalizes to other regulators and power systems |
| P2 | Simplify small jogs in grounded pins | Cleaner local connections |
| P2 | Canonicalize redundant collinear segments / junctions | Clearer VOUT and REF presentation |
| P2 | Add semantic grouping metric | Catches drawings that pass geometric gates but read poorly |
| P3 | Optimize overall whitespace | More coherent page composition |

**Architectural suggestion:** Treat connector placement at the *functional-interface* level. Generate a few semantically coherent group layouts, compute feasible wire routes and label positions, run the complete KiCad checks on scratch copies, then choose the best valid option. Do not independently optimize each connector while leaving other pieces frozen.

### Regression tests to add

1. V11 regulator: J1 left, J2 right, J3 grouped with the power entry/return.
2. J3 relocation with nearby REF symbol and power flag: full-group move must preserve native netlist equivalence and ERC.
3. Short-jog or junction cleanup: require unchanged KiCad connectivity before acceptance.
4. Tests for *other* multi-terminal power interfaces, to avoid an L7805-specific hack.
5. Blind before/after visual scoring in addition to the deterministic geometry checks.

## 6. Why automatic checks pass

The saved `assessment.json` reports:

| Measure | V11 |
|---|---:|
| Total wire length | 125.73 mm |
| Wire bends | 5 |
| Unrelated wire crossings | 0 |
| Wires through symbols | 0 |
| Electrical equivalence | PASS |
| ERC | PASS |
| Layout checks | PASS |

These results are respectable, but none measures whether J3 belongs visually with the functional power interface. A schematic can satisfy geometric rules and still be semantically awkward.

A proposed new metric should consider **return connector distance from its associated interface block**, not merely proximity to an arbitrary REF symbol. That criterion should be validated on multiple circuit families.

## 7. Subjective assessment

| Category | Score |
|---|---:|
| Electrical connectivity relative to intended netlist | 10/10 |
| Regulator/capacitor placement | 9/10 |
| Input/output flow | 9/10 |
| Return connector placement | 4/10 |
| Wire/junction presentation | 7/10 |
| General readability | 8/10 |
| **Overall schematic presentation** | **7.5/10** |

The scores describe presentation or netlist matching, **not** a guarantee of correct electrical performance or design suitability.

## Conclusion

**V11 is an improvement over V10, but it is not a finished engineering-quality drawing.** Input/output flow works much better. The remaining problem is the relationship among the supply, output and return connectors: the system can place individual pieces safely, but cannot yet reliably **group and move interacting parts as one unit**.

**Next recommended task for Claude:** implement semantic power/return interface grouping and coordinated, electrically safe relocation/rerouting, using this V11 regulator as a regression fixture.

**Separate engineering-design review still required:** supply/input range, thermal dissipation, load requirements, regulator stability and capacitor requirements, and PCB implementation are not established by the image or netlist checks.
