# M2c2 — frozen blind M2 qualification

Frozen Git HEAD: `07efd669000bc1ab17f6d291660951e0d9012de9`. Source freeze SHA-256: `6b24503a888605b06dbbf7e78365c4d3e321eae53dc4a1aef3821badb22b166b` (57 tracked files; final hash audit unchanged). Corpus v2 SHA-256: `252020a88911a18fa401cb26d388eaa02bd65813696aaf823847f212c14bca14`. All eight IR hashes are in `ir.sha256.json` and independently checked in `ir_validation.json`.

KiCad: 10.0.6 via `/tmp/AppDir/AppRun` (SHA-256 `5587d7de2c45df07c3de73f4679dba77f73020a30d8e8a651a0779ceb08d86de`); binary SHA-256 `1108ea3589e75aa274adad754275709da326f89614a9c6ce6fc456a430ef1a4b`. Toolchain lock `30402012777b0557801dfc5f7d8fbcecfbb4037da6a09e8b5df6eeb699481a9c`, M2b asset lock `e657a0b87be86eedb22105bf160ccbdadfe87c232977617a71aee16e3d7445b8`, drafting policy `b51e4e0f6c62b868ddf1642949e5073b971ff3fe108b0f62d73466d3a6e82e48`. Locked toolchain validation passed.

## Automated qualification

| Case | Requested design | Generation | Electrical | ERC | Layout legality | Five runs | Automated | Failure class |
|---|---|---|---|---|---|---|---|---|
| H1 | `rc_lowpass_led_indicator` | FAIL | N/A | N/A | N/A | N/A | **FAIL** | unsupported passive composition |
| H2 | `rc_highpass_noninverting` | PASS | PASS | 0 violations | PASS | 5/5 PASS | **PASS** | — |
| H3 | `dual_rail_reference_buffer` | PASS | PASS | 0 violations | PASS | 5/5 PASS | **PASS** | — |
| H4 | `dual_active_opamp_chain` | FAIL | N/A | N/A | N/A | N/A | **FAIL** | unsupported active-stage function composition |
| H5 | `sallen_key_output_rc` | FAIL | N/A | N/A | N/A | N/A | **FAIL** | unsupported unplaced active-stage component |
| H6 | `regulated_led_load` | FAIL | N/A | N/A | N/A | N/A | **FAIL** | unplaced power-stage component |
| H7 | `timer_led_output` | FAIL | N/A | N/A | N/A | N/A | **FAIL** | unplaced timer component |
| H8 | `rc_inverting_amplifier` | FAIL | N/A | N/A | N/A | N/A | **FAIL** | unsupported unplaced active-stage component |

**Automated result: FAIL, 2/8 accepted.** H1 and H4–H8 are valid requested designs, remain in the denominator, and have preserved `runs/<case>/run1.failed/reports/failure.json` artifacts. They failed before KiCad export, so electrical/ERC/layout metrics are unavailable for those cases. No timeout occurred. H2 and H3 have actual `.kicad_sch`, `.kicad_pro`, fresh XML netlist, independent electrical report, ERC, complete layout vector, SVG, and manifest in each run directory.

## Reproducibility and layout

H2 and H3 each passed five clean builds. Compiler-owned project files, electrical partitions, ERC violations, complete layout vectors, normalized SVG geometry/text, and manifests after only enumerated KiCad date/path/title normalization agreed across all five runs. `reproducibility.json` records each file comparison; raw exports remain preserved.

Worst observed passing-sheet metrics: 331.47 mm wire length (H3), 12 bends (both), 33 wires (H2), 0.477794 page utilization (H2), 31.75 mm local motif span (H2), 27.94 mm support span (both), and 1.69 mm minimum required-text clearance (H3). Both sheets have zero observed collision, unrelated contact/crossing, flow reversal, and page-margin defects.

## Regression and human gates

Complete pytest suite: **100 passed**; this includes existing M1/M2 mutation and negative tests. Ruff lint and format checks passed for source, tests, and evaluation scripts. Hand-authored trailing-whitespace check: 77 files checked, zero findings. Toolchain lock, source freeze, eight IR hashes, and corpus hash verified unchanged.

Review packet: `review_packet/` has blinded SVG/PDF and blank score sheets for H2 and H3. `review_id_mapping.json` and `review_answers_private.md` are separate and must remain hidden until reviewers finish. No human ratings were fabricated. Human review status: **PENDING**.

**Final M2 status: BLIND FAIL.** The M2 exit threshold is 8/8 valid held-out requests, so the six automated failures preclude M2 PASS regardless of subsequent human scores. No implementation, threshold, or frozen IR repairs were made.
