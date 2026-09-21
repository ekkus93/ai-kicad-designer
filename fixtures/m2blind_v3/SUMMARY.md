# M2d2 — corpus.v3 frozen blind composition qualification

**Final status: M2 CORPUS.V3 BLIND GATE FAIL**

The frozen automated result is **3/8 accepted**. The M2 held-out threshold is
8/8, so human review was neither started nor fabricated, no review packet was
created, and no implementation or frozen-input repair was attempted.

## Freeze and execution identity

- Git HEAD: `f8ea5b055aad1a9e97a659e025c20e185a626533`
- Implementation freeze SHA-256:
  `45e1dfb55d15b35881e42934f7e8265c08fa6f59f4d7fe2e3e0ae978093daa6d`
  (214 tracked behavior/evaluation files plus external toolchain and historical
  evidence snapshots)
- Corpus v3 SHA-256:
  `aafcfd0d031180409b9f5f18e8589f1d2753a6f0a9908bd76dd45aa04184a93f`
- KiCad: 10.0.6 through `/tmp/AppDir/AppRun`, SHA-256
  `5587d7de2c45df07c3de73f4679dba77f73020a30d8e8a651a0779ceb08d86de`;
  underlying `kicad-cli` SHA-256
  `1108ea3589e75aa274adad754275709da326f89614a9c6ce6fc456a430ef1a4b`
- Toolchain lock SHA-256:
  `30402012777b0557801dfc5f7d8fbcecfbb4037da6a09e8b5df6eeb699481a9c`
- M2b asset lock SHA-256:
  `e657a0b87be86eedb22105bf160ccbdadfe87c232977617a71aee16e3d7445b8`
- Policy lock SHA-256:
  `b51e4e0f6c62b868ddf1642949e5073b971ff3fe108b0f62d73466d3a6e82e48`
- Drafting profile SHA-256:
  `03b8701ccc034b788e5b65ebcd8888c14e34474ad42875d7d1df5dc7089b302d`
- Python: CPython 3.12.10 from `.venv/bin/python`; platform
  `Linux-7.0.0-31-generic-x86_64-with-glibc2.39`; CPU
  `AMD Ryzen 7 5825U with Radeon Graphics`

The locked executable, shared-library, symbol-asset, policy, and source hashes
all matched at the start, before every build, and at the final audit.

## Automated qualification

All eight frozen IRs passed the standalone frozen parser/resolver authoring
check. Generation/layout was then attempted once for every case. Only cases
that passed all automated gates received four additional clean runs.

| Case | Input | Generation / KiCad | Electrical | ERC | Layout | Five-run reproducibility | Automated | Exact failure class and evidence |
|---|---|---|---|---|---|---|---|---|
| V3-1 | PASS | PASS | PASS | 0 violations | PASS | 5/5 PASS | **PASS** | — |
| V3-2 | PASS | FAIL before KiCad | N/A | N/A | N/A | not performed | **FAIL** | `power_stage_interface_ownership`: `power stage requires one interface per rail` |
| V3-3 | PASS | FAIL before KiCad | N/A | N/A | N/A | not performed | **FAIL** | `timer_output_interface_ownership`: `timer requires supply, output and reference interfaces` |
| V3-4 | PASS | FAIL before KiCad | N/A | N/A | N/A | not performed | **FAIL** | `mixed_unit_feedback_classification`: `parked unit feedback disconnected` |
| V3-5 | PASS | PASS | PASS | 0 violations | PASS | 5/5 PASS | **PASS** | — |
| V3-6 | PASS | PASS | PASS | 0 violations | PASS | 5/5 PASS | **PASS** | — |
| V3-7 | PASS | FAIL before KiCad | N/A | N/A | N/A | not performed | **FAIL** | `a4_margin_infeasibility`: `content exceeds A4 margin` |
| V3-8 | PASS | FAIL before KiCad | N/A | N/A | N/A | not performed | **FAIL** | `incompatible_core_composition`: `incompatible local core contributors: ['timer', 'power_stage']` |

The five rejected cases retain their first-attempt `reports/failure.json` under
`runs/<case>/run1.failed/`. They failed after `validate_resolve` and before real
KiCad export, so no electrical, ERC, render, or layout vector exists for them.
They remain in the denominator. Total build runtime was 27.728 seconds.

## Reproducibility and passing-sheet metrics

V3-1, V3-5, and V3-6 each passed five independent clean builds. For all three,
the compiler-owned `.kicad_sch` and `.kicad_pro` bytes, independently observed
electrical partitions, ERC results, complete layout vectors, normalized KiCad
SVG geometry/text, and normalized manifests/all evidence files agreed across
all five runs. Normalization was limited to the already documented KiCad SVG
title, XML source path/date, ERC date, and raw CLI staging path.

Worst values among the three passing sheets were:

- 482.6 mm observed wire length, 40 observed wires, and 16 observed bends
  (V3-5)
- 0.594179 page utilization and 123.19 mm content height (V3-5)
- 41.91 mm local wire span and 31.75 mm motif-fragmentation span (V3-5)
- 27.94 mm support-locality span (all passing sheets)
- 15.24 mm observed feedback span (all passing sheets)
- 1.69 mm minimum observed text-to-wire clearance (V3-6)

Every passing sheet had zero body overlap, wire-through-body/text, unrelated
crossing/pin-contact, pin-endpoint mismatch, flow reversal, stage-order
reversal, and unrouted-pin findings, with both compiler and observed page
margin gates passing.

## Regression and contamination audit

- Complete pytest: **118 passed in 84.34 seconds**. This includes the M1
  mutation/observer, M2 identity, M2c1 tuning, and M2d1 known corpus.v2
  regression suites.
- Ruff lint: PASS.
- Ruff format check: PASS (27 files).
- `git diff --check`: PASS.
- Hand-authored trailing-whitespace scan: 56 files, zero findings.
- Every implementation-freeze hash: unchanged.
- Corpus v3 and all eight IR hashes: unchanged.
- `fixtures/m2blind/` historical corpus.v2 evidence: unchanged at its frozen
  157-file snapshot (144 tracked files plus preserved local evidence files).
- `fixtures/m2d1/` known repair/regression evidence: unchanged at its frozen
  785-file snapshot (743 tracked files plus preserved local evidence files).
- Git HEAD: unchanged; no tracked compiler/configuration source diff and no
  source commit occurred during evaluation.
- Frozen `src/ai_kicad/` search for every V3 case ID, design ID, and generated
  project name: zero matches.

Detailed machine-readable evidence is in `automated_results.json`,
`reproducibility.json`, `metric_summary.json`, `regression_results.json`, and
`anti_contamination.json`. No `review_packet/` exists because the automated
gate did not pass 8/8.

**M2 CORPUS.V3 BLIND GATE FAIL**
