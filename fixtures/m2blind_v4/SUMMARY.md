# M2f1 — corpus.v4 frozen blind qualification

**Final status: M2 CORPUS.V4 BLIND GATE FAIL**

The frozen automated result is **7/8 accepted**. The required held-out threshold is
8/8. V4-7 failed the observed layout-spread hard gate, so human review was not
started, no review packet was generated, and no implementation or frozen-IR repair
was attempted.

## Freeze and identity

- Git HEAD: `5d3083ed83e699dbfd9da8b7226c4f4314de54be`
- Implementation freeze SHA-256: `153e2943c5105febef91e8832c567d8ec76894c9907b78726558ccda15461c2d`
- Corpus v4 SHA-256: `34e0f51a757b6c116cd5815e962571fe9993b510e95796cef34e11c0a2385dd2`
- KiCad 10.0.6 AppRun SHA-256: `5587d7de2c45df07c3de73f4679dba77f73020a30d8e8a651a0779ceb08d86de`
- kicad-cli binary SHA-256: `1108ea3589e75aa274adad754275709da326f89614a9c6ce6fc456a430ef1a4b`
- Toolchain lock: `30402012777b0557801dfc5f7d8fbcecfbb4037da6a09e8b5df6eeb699481a9c`
- M2b asset lock: `e657a0b87be86eedb22105bf160ccbdadfe87c232977617a71aee16e3d7445b8`
- Policy lock: `b51e4e0f6c62b868ddf1642949e5073b971ff3fe108b0f62d73466d3a6e82e48`
- Python: CPython 3.12.10; platform `Linux-7.0.0-31-generic-x86_64-with-glibc2.39`;
  CPU `AMD Ryzen 7 5825U with Radeon Graphics`.

## Automated qualification

| Case | Electrical | ERC | Layout | Five-run reproducibility | Result | Failure class |
|---|---|---|---|---|---|---|
| V4-1 | PASS | 0 violations | PASS | 5/5 PASS | **PASS** | — |
| V4-2 | PASS | 0 violations | PASS | 5/5 PASS | **PASS** | — |
| V4-3 | PASS | 0 violations | PASS | 5/5 PASS | **PASS** | — |
| V4-4 | PASS | 0 violations | PASS | 5/5 PASS | **PASS** | — |
| V4-5 | PASS | 0 violations | PASS | 5/5 PASS | **PASS** | — |
| V4-6 | PASS | 0 violations | PASS | 5/5 PASS | **PASS** | — |
| V4-7 | PASS (available failure artifact) | 0 violations | **FAIL** | not applicable | **FAIL** | `observed_layout_spread_hard_gate` |
| V4-8 | PASS | 0 violations | PASS | 5/5 PASS | **PASS** | — |

V4-7 reached real KiCad export, independent electrical comparison, zero ERC
violations, SVG rendering, and semantic-composition evidence. It was rejected with
`observed layout spreads unnecessarily across the page`; its failed build tree is
preserved under `runs/V4-7/run1.failed/`.

An initial evaluation-harness pass incorrectly treated informational
`semantic_block_count` and `semantic_edge_count` fields as violation counts. The raw
initial result is preserved in `initial_harness_results.json`. The classification was
corrected without changing thresholds, implementation, IR, or run artifacts.

## Passing-sheet worst metrics

- observed wire length: 575.31 mm (V4-6)
- observed content: 189.23 mm wide (V4-6); 114.3 mm high (V4-3)
- observed local wire span: 41.91 mm (V4-5)
- observed support locality: 34.29 mm (V4-6)
- observed feedback span: 15.24 mm (V4-5)
- page utilization: 0.465187 (V4-6)
- minimum text/wire clearance: 1.65 mm (V4-8)

All seven passing cases reproduced compiler-owned schematic/project bytes,
independently observed partitions, ERC, semantic composition, complete layout vectors,
normalized KiCad SVG geometry/text, and normalized manifest/check evidence across five
clean builds.

## Regression and audits

- Pytest: 136 passed in 82.27 seconds, covering every requested regression category.
- Ruff lint: PASS.
- Ruff format: **FAIL** for three new qualification scripts; no repair was made.
- `git diff --check`: PASS.
- Hand-authored whitespace scan: 59 files, zero findings.
- Implementation, external toolchain, corpus, and all IR freeze audits: PASS.
- Historical `m2blind`, `m2blind_v3`, `m2d1`, `m2e1`, and `m2e1a` trees: unchanged.
- Frozen implementation search for all V4 IDs and design names: zero matches.
- Review packet: not generated because the automated gate failed.

**M2 CORPUS.V4 BLIND GATE FAIL**
