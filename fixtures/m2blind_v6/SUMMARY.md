# M2h1 — corpus.v6 frozen blind qualification

**Final status: M2 CORPUS.V6 BLIND GATE FAIL**

The frozen automated result is **3/8 accepted**. The M2 threshold is 8/8, so
human review was not started, no review packet was created, and no
implementation, threshold, observer, or frozen-IR repair was made.

## Freeze and execution identity

- Frozen committed Git HEAD:
  `59b44e368345f0a24b3c98c07e9c1a6548a166de`
- Implementation-freeze SHA-256:
  `3e729a2fe1d1acb16477c655052991c6d5d4dbdb3ed3bbf10541c8e31ca8012d`
  (11,873 tracked files, all behavior-affecting tracked files included)
- Corpus v6 SHA-256:
  `e9bccdaf6670fc6d47a272f79418fa6d92f85b0d255636c258e826a85d39c951`
- KiCad 10.0.6 AppRun SHA-256:
  `5587d7de2c45df07c3de73f4679dba77f73020a30d8e8a651a0779ceb08d86de`
- Underlying `kicad-cli` SHA-256:
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
  `AMD Ryzen 7 5825U with Radeon Graphics`.

All eight IR hashes are frozen in `ir.sha256.json`. The external executable,
library, asset, policy, toolchain, source, corpus, and IR hashes matched at the
start, before every build, and at the final audit.

## Automated qualification

| Case | Generation / KiCad | Electrical | ERC | Layout/path | Five runs | Result | Failure class |
|---|---|---|---:|---|---|---|---|
| V6-1 | PASS | PASS (12/12 partitions) | 0 | PASS | 5/5 reproducible | **PASS** | — |
| V6-2 | PASS | PASS | 0 | FAIL | not performed | **FAIL** | observed stage-order reversal |
| V6-3 | emitted, then rejected | not evaluated | 7 | not evaluated | not performed | **FAIL** | ERC/emitted disconnections |
| V6-4 | FAIL before emission | not evaluated | not evaluated | not evaluated | not performed | **FAIL** | packing budget exhausted |
| V6-5 | PASS | PASS (10/10 partitions) | 0 | PASS | 5/5 reproducible | **PASS** | — |
| V6-6 | PASS | PASS | 0 | FAIL | not performed | **FAIL** | observed local path span |
| V6-7 | PASS | PASS (14/14 partitions) | 0 | PASS | 5/5 reproducible | **PASS** | — |
| V6-8 | FAIL before emission | not evaluated | not evaluated | not evaluated | not performed | **FAIL** | layout budget exhausted / net detour |

V6-2 produced a real KiCad project and fresh XML, passed independent
electrical equivalence and zero-violation ERC, but the independent layout
observer rejected functional stage order. V6-3 produced a project and fresh
XML, but KiCad reported four errors and three warnings: disconnected passive
pins, disconnected op-amp pin 5, an undriven op-amp input, and three
unconnected wire endpoints. V6-4 exhausted all 32 packing candidates; its best
recorded content bound still exceeded the 140 mm height limit. V6-6 passed
electrical equivalence and ERC but measured two required local paths at
88.9 mm against the 80 mm hard limit. V6-8 exhausted 32 bounded attempts with
the final VCC conductor-tree detour at 381 mm against the 250 mm limit.

The successful cases contain complete semantic plans, fragment/variant
choices, reservations, routes, canonical conductor trees, junction/path
evidence, real projects, fresh XML, independent electrical reports, ERC,
SVGs, layout vectors, attempt traces, and manifests. Failed cases retain the
available staged evidence under `runs/<case>/run1.failed/`.

## Reproducibility and metrics

V6-1, V6-5, and V6-7 each passed five clean builds in independent output
directories. Compiler-owned schematic/project bytes, independent electrical
partitions, ERC, semantic composition, fragment/variant and reservation
evidence, canonical conductor trees, junction/path evidence, complete layout
vectors, normalized SVG geometry/text, and normalized manifest/check evidence
agreed across all five runs. Normalization was limited to the documented SVG
title, XML source/date, ERC source/date, and raw CLI staging paths.

Worst passing-sheet metrics:

- observed content: 199.39 mm wide and 124.46 mm high (V6-7)
- observed wire length: 1045.21 mm (V6-7)
- observed feedback span: 15.24 mm (V6-1)
- observed motif fragmentation: 31.75 mm (V6-5)
- observed support locality: 24.13 mm (V6-1)
- observed page utilization: 0.608051 (V6-7)
- bounded passing attempts/repairs: 13 attempts and 12 repairs (V6-1)
- maximum bounded attempts including failures: 32 (V6-8; V6-4 also recorded
  32 packing candidates)

Total recorded V6 build runtime was 127.097 seconds.

## Harness note

The initial inherited V4 evaluation harness incorrectly treated M2g2's
informational attempt, repair, raw-wire, and actual-junction counts as
violations for V6-1, V6-5, and V6-7. Their frozen build manifests and actual
hard-gate fields all passed. `initial_harness_results.json` preserves that raw
classification. The V6-only harness was corrected to distinguish those
informational counts; implementation, observer, thresholds, corpus, IRs, and
run-1 artifacts were unchanged. Builds 2–5 then reproduced all three cases.

## Regression and contamination audits

- Complete pytest: **174 passed in 89.36 seconds**. This includes M1
  observer/mutation tests, M2 identity tests, all 12 tuning cases, v2–v5 known
  regressions, M2e1/M2e1a probes, M2f2 probes, and M2g2 generic,
  development-probe, and stress-variant coverage.
- Ruff lint and format: PASS for active source, tests, and all new V6 tooling.
- `git diff --check` and the applicable hand-authored whitespace scan: PASS.
- Frozen tracked implementation/configuration files: unchanged; no tracked
  diff exists.
- Corpus v6 and all eight IR hashes: unchanged.
- Historical `m2blind`, `m2blind_v3`, `m2blind_v4`, `m2blind_v5`, `m2d1`,
  `m2e1`, `m2e1a`, `m2f2`, and `m2g2` evidence roots: unchanged.
- Active frozen `src/ai_kicad` search for V6 IDs, design names, project names,
  exact IR hashes, and exact inventory hashes: zero matches.
- Anti-contamination audit: PASS.
- Review packet: not generated because the automated gate failed.

Machine-readable detail is in `automated_results.json`,
`reproducibility.json`, `metric_summary.json`, `regression_results.json`,
`anti_contamination.json`, and `workspace_audit.json`.

**M2 CORPUS.V6 BLIND GATE FAIL**
