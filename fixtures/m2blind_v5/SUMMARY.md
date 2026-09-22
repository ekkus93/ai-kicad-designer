# M2g1 — corpus.v5 frozen blind qualification

**Final status: M2 CORPUS.V5 BLIND GATE FAIL**

The frozen automated result is **4/8 accepted**. The required held-out threshold is 8/8. Human review was not initiated, no review packet was created, and no implementation or frozen-input repair was attempted.

## Freeze and identity

- Git HEAD: `7c28afa28b88761cc35ddfecae4dfa8f4da60ba9`
- Implementation freeze SHA-256: `9f3716069c08427b8183a552b246e605091a61d811410f2b827a693d10844069`
- Corpus v5 SHA-256: `a4337ce3dd2b24bd359462bd63ef408b9b4bb05200315bd414b36db832077ec4`
- KiCad 10.0.6 AppRun SHA-256: `5587d7de2c45df07c3de73f4679dba77f73020a30d8e8a651a0779ceb08d86de`
- kicad-cli binary SHA-256: `1108ea3589e75aa274adad754275709da326f89614a9c6ce6fc456a430ef1a4b`
- Toolchain lock: `30402012777b0557801dfc5f7d8fbcecfbb4037da6a09e8b5df6eeb699481a9c`
- M2b asset lock: `e657a0b87be86eedb22105bf160ccbdadfe87c232977617a71aee16e3d7445b8`
- Policy lock: `b51e4e0f6c62b868ddf1642949e5073b971ff3fe108b0f62d73466d3a6e82e48`
- Python: CPython 3.12.10; platform `Linux-7.0.0-31-generic-x86_64-with-glibc2.39`; CPU `AMD Ryzen 7 5825U with Radeon Graphics`.

## Automated qualification

| Case | Electrical | ERC | Layout | Five runs | Result | Failure class |
|---|---|---:|---|---|---|---|
| V5-1 | N/A | N/A | FAIL before metric publication | not performed | **FAIL** | wire/body collision on active supply support |
| V5-2 | PASS | 0 | PASS | 5/5 PASS | **PASS** | — |
| V5-3 | PASS | 0 | FAIL | not performed | **FAIL** | observed layout-spread hard gate |
| V5-4 | PASS | 0 | PASS | 5/5 PASS | **PASS** | — |
| V5-5 | PASS | 0 | PASS | 5/5 PASS | **PASS** | — |
| V5-6 | N/A | N/A | FAIL before metric publication | not performed | **FAIL** | wire/body collision on regulator output support |
| V5-7 | PASS | 0 | FAIL | not performed | **FAIL** | observed local explicit-path hard gate |
| V5-8 | PASS | 0 | PASS | 5/5 PASS | **PASS** | — |

V5-1 and V5-6 stopped before KiCad export. V5-3 and V5-7 reached real KiCad export/render, exact independent electrical comparison, and zero-violation ERC before failing independent layout hard gates. All four passing cases reproduced governed project files, electrical partitions, ERC, composition evidence, complete metric vectors, normalized SVG, and manifest/check evidence across five clean builds.

## Worst passing-sheet metrics

- observed wire length: 916.94 mm (V5-5)
- observed content: 189.23 mm wide and 137.16 mm high (V5-8)
- observed local/motif span: 34.29 mm (V5-8)
- observed support locality: 34.29 mm (V5-8)
- observed feedback span: 15.24 mm (V5-2 and V5-4)
- observed page utilization: 0.635952 (V5-8)
- minimum observed text/wire clearance: 0.42 mm (V5-2)
- observed wire/bend counts: 67 wires and 25 bends (V5-5)

Every passing sheet recorded zero observed body overlap, wire-through-body/text, unrelated crossing/pin contact, endpoint mismatch, flow reversal, stage-order reversal, and page-margin defects.

## Regression and audits

- Complete pytest: **147 passed in 82.24 seconds**, covering all requested regression categories.
- Ruff lint and Ruff format: PASS for source, tests, and new V5 tooling.
- `git diff --check` and hand-authored whitespace checks: PASS.
- Implementation, external toolchain, corpus, and all IR freeze audits: PASS.
- Historical `m2blind`, `m2blind_v3`, `m2blind_v4`, `m2d1`, `m2e1`, `m2e1a`, and `m2f2` trees: unchanged.
- Frozen active source search for V5 IDs, design names, and exact inventory hashes: zero matches.
- Review packet: not generated because the automated gate failed.

Recorded first-run build runtime: 31.451 seconds. Audit pass: True. Metric vectors: 4 passing cases.

**M2 CORPUS.V5 BLIND GATE FAIL**
