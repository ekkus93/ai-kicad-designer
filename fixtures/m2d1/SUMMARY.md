# M2d1 — compositional schematic layout repair

Status: **PASS**. This is a known, non-blind regression of the preserved M2c2 corpus v2. It does not revise or replace the historical blind result in `fixtures/m2blind/`, which remains **BLIND FAIL, 2/8 accepted** at commit `07efd669000bc1ab17f6d291660951e0d9012de9`.

## Implementation

`src/ai_kicad/m2_compose.py` introduces a small `StageGraph` and `LayoutFragment`. The graph is built from stable relationship IDs and shared input/output nets. A fragment records its geometry-owned symbol occurrences and semantic ports. The composer rejects duplicate owners, reports every occurrence lacking an owner, preserves the existing local motif wires, and splits shared net trunks at deterministic junction points when it attaches a branch.

The passive, active, regulator, and timer layout functions can now contribute partial local geometry. The composer adds passive series/shunt or polarity branches around those cores and performs the final ownership, text, clearance, routing, and page checks once. Two active functions in one qualified NE5532 package are placed as successive stages while retaining one shared power unit. No CP-SAT solver was introduced.

## Known corpus v2 regression

`qualification.json` records five clean builds of every known v2 design through locked KiCad 10.0.6. Each of the 40 builds passed independent emitted-netlist comparison, zero unexpected ERC violations, SVG export, compiler and observed layout hard gates, and page bounds. Compiler-owned project bytes, electrical reports, ERC results, layout vectors, and normalized SVG geometry/text reproduced across all five runs.

| Case | Repaired composition | Result |
|---|---|---|
| H1 | RC low-pass plus LED branch | PASS |
| H2 | RC high-pass into non-inverting stage | PASS |
| H3 | split-rail reference buffer | PASS |
| H4 | two active functions of one dual package | PASS |
| H5 | Sallen-Key stage into output RC | PASS |
| H6 | regulator core plus LED load | PASS |
| H7 | timer core plus LED load | PASS |
| H8 | input RC into inverting amplifier | PASS |

SVGs were visually inspected. Stage order, feedback/timing loops, regulator support, load branches, page fit, and text/body clearances are structurally reasonable. The observed hard-gate reports contain zero body overlaps, wire-through-body/text defects, unrelated crossings or pin contacts, endpoint mismatches, flow reversals, and page-margin defects.

## Additional generalization case

`regulated_rc_probe.json` is distinct from H1–H8. It composes the qualified regulator block with a downstream resistor/capacitor stage. `non_v2/result.json` records two real KiCad builds with passing independent electrical comparison, zero ERC violations, all layout hard gates, SVG export, and equal project bytes/reports/normalized SVG output.

## Regression and preservation

- Complete pytest: 118 passed, including M1, M2a, M2b, M2c1, mutation, identity, stale-report, and new M2d1 composition tests.
- Ruff lint and format: passed.
- `git diff --check`: passed.
- Corpus v2 SHA-256 remains `252020a88911a18fa401cb26d388eaa02bd65813696aaf823847f212c14bca14`.
- `git diff -- fixtures/m2blind` is empty. Original corpus, IR, automated results, summary, failure artifacts, and source-freeze evidence are unchanged.
- Source search found no H1–H8 key, corpus design ID, or reference-designator geometry dispatch in the implementation.

The historical evaluator's freeze guard remains intentional: it rejects the repaired source as differing from the frozen M2c2 implementation. Its scripts compile unchanged, and its preserved results were not rerun or rewritten.
