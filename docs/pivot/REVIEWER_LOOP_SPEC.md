# Reviewer loop: spec for the next round of work

**Status:** draft for owner review, 2026-11-14. Branch `mcp`.
**Tracks:** `docs/MCP_ARCHITECTURE_TODO.md` P6-011g to P6-011l, under P6-011.
**Sources:**
- the independent review `docs/ai_kicad_reviewer_independent_review_for_claude.md`, with recommendation IDs such as P0.3 and P1.4
- the applied-edit index `docs/pivot/REVIEWER_APPLIED_EDITS.md`
- the qualification runs `review_qualification_v9_*_2026-11-13_*`

## 1. Goal

The schematic review loop renders a drawing, has a model review it, applies the edits the model requests, and reviews again. It should improve a drawing round after round. Today it does not:
- In every corpus run since 9 November the model accepted on its first review, and none of its edits reached an accepted drawing.
- In October its applied edits often made drawings worse: longer wires, more bends, routes around the page edge.
- In the 13 November qualification runs, with the check verdicts withheld, it rejected good and defective drawings at about the same rate.

The loop is only as useful as its edits are safe and its verdicts are informative. This spec covers:
- **R1:** reporting that says honestly what was checked
- **R2:** measuring whether an edit made the drawing better or worse
- **R3:** giving the model a menu of edits known to be feasible, instead of making it guess coordinates
- **R4:** structured refusals
- **R5:** the default reviewer configuration
- **R6:** a benchmark that can tell whether any of this works

## 2. What already exists

These are in place and are not to be rebuilt:

| Piece | Where |
|---|---|
| Review loop: render, review, edit, re-review, bound to the exact drawing revision | `run_schematic_review` in `src/ai_kicad/pivot/schematic_review.py` |
| Independent checks: KiCad ERC, netlist electrical equivalence, observed layout, rail presentation, power-symbol clearance and direction, field locality, separation, ownership and wire separation, bodyless-unit clearance, rail detour, page balance | `NativeSchematicEngine.assess`, `src/ai_kicad/pivot/readability_checks.py` |
| Versioned briefs v1–v9 deciding which checks and layout rules apply | `fixtures/pivot/schematic_review_brief_v*.json`, `schematic_review_brief.py` |
| Reviewer input options: PNG (default), `--svg`, `--description`, `--with-images`, `--think`, `--withhold-checks` | reviewer, service, `tools/pivot/run_review_loop_corpus.py` |
| Up to 4 edits per review (`--max-actions`), each applied and checked in turn | loop |
| **Safe edits (P0.1):** an edit that makes `native_tools`, `erc` or `electrical_equivalence` fail, or changes nothing, is rolled back. The previous drawing stays current and the model is told why | loop, `ccf9e5cc` |
| **No repeats (P1.3, partly):** asking again for an edit already refused on the same revision ends the run with `NO_PROGRESS` | loop, `ccf9e5cc` |
| Rails drawn with local power symbols, not long wires (P0.2, P1.2), within the 25.4 mm cap | briefs v3+, `a4d4a3ca`, `cb479802` |
| Power block layout for op-amp power units (P2.1, partly) | briefs v8/v9 |
| Qualification harness: 61 cases, blind mode, input options | `tools/pivot/qualify_review_v3.py` |

## 3. Requirements

### R1 — Status levels instead of one verdict (review P0.3)

`ACCEPTED_FOR_REVIEW` today means only "every configured check passed and the model accepted". Each run result (`result.json`) and corpus summary must also report separate levels. Each is `PASS`, `FAIL` or `PENDING`, and each records its basis:

| Level | Meaning | Basis |
|---|---|---|
| `NATIVE_VALID` | KiCad loads, exports and plots the sheet | `native_tools` |
| `ELECTRICALLY_EQUIVALENT` | the drawing's netlist matches the intended circuit, and ERC passes | `electrical_equivalence`, `erc` |
| `PRESENTATION_PASS` | every readability check the brief enables passes | the brief's presentation checks |
| `QUALITY_NOT_WORSE` | the accepted drawing is no worse than the starting drawing on the R2 measures | R2 |
| `MODEL_ACCEPTED` | the reviewer accepted with no open issues | the review |
| `DESIGN_REQUIREMENTS_CHECKED` | the circuit was checked against its application requirements | `PENDING`; out of scope, see §6 |
| `HUMAN_REVIEWED` | a person reviewed readability and electrical correctness | `PENDING` until recorded |

Also required:
- **ERC disclosure:** the result lists the ERC check categories that are ignored.
- **Edit outcome class:** each applied edit records one of:
  - `FUNCTIONAL_REPAIR`: it fixed a failing connectivity check, for example `regenerate_schematic` on `rc_corrupted`
  - `PRESENTATION_FIX`: it fixed a failing presentation check
  - `LAYOUT_CHANGE`: no check changed
  - `LOCAL_FIX_ONLY`: it fixed something but made an R2 measure worse

  A run's outcome class is the most significant class among its kept edits.
- **Backward compatibility:** `ACCEPTED_FOR_REVIEW` stays for existing tools. Its documentation must say it implies only `ELECTRICALLY_EQUIVALENT`, `PRESENTATION_PASS` and `MODEL_ACCEPTED`.

### R2 — Quality delta for every edit (review P1.4)

For every candidate drawing, compute these measures from the native schematic. For every applied edit, record their change from the previous drawing, and for every run, from candidate 000 to the final drawing.

| Measure | Definition |
|---|---|
| wire length | total wire length (mm) |
| detour | sum over asserted rails of the `rail_route_detour` excess (mm) |
| bends | wire corners: points where exactly two non-collinear wires meet |
| perimeter wires | wire segments longer than *L₁* lying within *D₁* of the drawing's bounding box |
| text clearance | the minimum text-to-wire distance (`observed_text_wire_clearance_mm`) |
| field ownership | the worst `owner_advantage_mm` over visible fields |
| page balance | the existing `page_balance` measure |
| power symbol count | per rail |

Rules:
- **Worse:** an edit is *worse* on a measure when the measure moves the wrong way by more than its tolerance. Tolerances are *T* per measure; see open question Q2.
- **Kept but labelled:** an edit that fixes a failing check but is worse on any measure is kept, and labelled `LOCAL_FIX_ONLY` (R1).
- **Rolled back:** an edit that fixes no check and is worse on any measure is rolled back like a connectivity break, with the reason sent to the model.
- **Not a gate on its own:** wire length alone must not decide this. More wire is acceptable when it fixes a check.
- **Reporting:** the corpus summary reports, per design, the run's net delta, and per run, how many edits were kept, labelled `LOCAL_FIX_ONLY`, or rolled back for quality.

### R3 — A menu of feasible edits (review P1.1)

The model should choose among edits the editor has already proved feasible, instead of inventing millimetre coordinates.

1. **Building the menu.** For each review, the editor builds a menu of candidate edits for the issues it can measure:
   - **field relocation:** clear spots for a part's reference or value, from the field-placement search
   - **symbol nudge:** grid offsets of a part that keep connectivity and pass collision checks
   - **rail symbol placement:** clear spots and directions for a rail's power symbol
   - **wire reroute:** for a rail group, if one exists
2. **Pre-checking each entry.** Every entry is pre-checked: applied in scratch, with connectivity verified and the R2 delta computed. Only entries that keep connectivity are listed. Each entry has an ID, a one-line description, and its R2 delta.
3. **Sending it.** The menu goes in the reviewer handoff, capped at *N* entries per issue class (open question Q3).
4. **Choosing.** The model may pick entries by ID with a new action, `choose_edit` (`{"operation": "choose_edit", "id": "…"}`), or request a free-form edit as today. Free-form edits still go through the R1/R2 checks.
5. **Identifying units.** Parts are named by canonical `(reference, unit)`. A malformed reference list such as `references=['U1','unit','3']` is refused with a structured reason.

### R4 — Structured refusals (review P1.3, remainder)

When the editor refuses an edit or rolls it back, the feedback to the model must be machine-readable. It must include:
- the reason class: `connectivity`, `no_change`, `quality`, `infeasible_route`, `invalid_request` or `repeat`
- the failing checks or measures, with values
- where possible, one to three feasible alternatives from the R3 menu

Repeats are already refused (`ccf9e5cc`). A request equivalent to a refused one, meaning the same operation and target with parameters within one grid step, should also be refused.

### R5 — Default reviewer configuration

Based on the 13 November qualification runs:
- **Input:** SVG source as text plus both PNGs (`--svg --with-images`). This had the fewest unusable answers, 3 of 61, against 10 for the description alone.
- **Reasoning:** off. With `qwen35-256k` it looped until the output cap on 14 of 23 cases.
- **Verdicts:** withheld (`--withhold-checks`).
- **Edits:** up to 4 per review.

These become the defaults of a new brief or service profile. Brief v9 stays reproducible. Re-qualify the defaults with R6 before treating any reviewer verdict as evidence.

### R6 — Benchmark and qualification (review P2.3)

The harness's "known-good" drawings predate the v8/v9 layout rules, and its defect matching counts generic words as hits. Replace both:

1. **New baseline corpus.** Regenerate the 15 corpus designs under the current brief. Have the owner, or the owner together with ChatGPT, mark each drawing *good*, or list its defects. Only drawings marked good form the known-good set. Their defect lists become new historical cases.
2. **Defect cases.** Keep the historical defects (re-checked against the current code) and the injected defects. Each case carries a hand-written defect label: the part, the problem, and its location.
3. **Scoring by label, not pattern.** Score a rejection as *naming the defect* only when it identifies the labelled part and problem. Do this by an explicit per-case check list, reviewed by hand on a sample. Retire the cue regexes.
4. **Edit quality.** For loop runs, report:
   - the connectivity regression rate (must be 0)
   - the rollback rate by reason
   - the R2 net delta per design
   - an edit quality win rate: blind A/B comparison of the start and final drawings by a human or ChatGPT on six criteria: electrical correctness, node traceability, power-section clarity, text association, functional-block arrangement and overall preference
5. **Hold-out circuits.** Add designs outside the 555 and op-amp families before claiming the layout rules generalise. See open question Q5.
6. **Records.** Each qualification run records, per case: the drawing hashes, the model ID, digest, context, options and input mode, the raw reply, and the scores. This is as today, plus the labels.

## 4. Acceptance criteria

These are adapted from the review's suggested criteria:

- **Safety:** no accepted, kept or current candidate has a connectivity regression. Every edit that breaks connectivity is rolled back. This is met for single edits by `ccf9e5cc`; keep it under R3.
- **Correctness:** no accepted drawing has an ERC error, and ignored ERC categories are disclosed (R1).
- **Presentation:** no text, symbol or pin-number overlaps, and no long perimeter wire added only to satisfy a rail rule (R2).
- **Quality:** a run reports its R2 net delta. A run that fixes a narrow issue but leaves the drawing worse reports `LOCAL_FIX_ONLY`, not an improvement.
- **Loop progress:** no identical or equivalent refused edit is repeated on the same revision. An infeasible request gets alternatives, or a structured blocker when there are none (R4).
- **Traceability:** every kept edit has a before/after diff, the status levels and its outcome class.
- **Reviewer usefulness:** on the R6 benchmark, the reviewer separates known-good from defective drawings better than chance by a margin the owner sets (Q4), with defect naming scored by label.

## 5. Open questions for the owner

- **Q1, status names:** are the R1 level names and meanings right? Should `QUALITY_NOT_WORSE` be a gate on `ACCEPTED_FOR_REVIEW`, or only reported?
- **Q2, tolerances:** what tolerances *T* per R2 measure, and what perimeter-wire thresholds *L₁* and *D₁*? Suggested starting points: wire length +5 %, bends +2, text clearance −0.635 mm, perimeter wire *L₁* = 50.8 mm within *D₁* = 2.54 mm of the box.
- **Q3, menu size:** how many menu entries per issue class? More entries help the model choose but lengthen the prompt. Suggested: 3.
- **Q4, success bar:** what result makes the reviewer "qualified"? For example: accepts at least 80 % of known-good drawings, rejects at least 80 % of defects, names the labelled defect in at least 50 %, and makes no false connectivity claims.
- **Q5, hold-out circuits:** which ones? Candidates: a transistor switch, an LDO with enable, a microcontroller decoupling block, an instrumentation amplifier.
- **Q6, raters:** who rates the R6 A/B comparisons: you, ChatGPT, or both? How are disagreements settled?
- **Q7, edits in the loop:** should free-form edits remain allowed once the R3 menu exists, or only menu choices for a first qualification?

## 6. Out of scope here

- **Electrical design review (review P2.2):** for example op-amp bias compensation, regulator dropout, or loading on the divider-based VREF. This is a separate pass with its own requirements. The reviewer may note such concerns as text, but must not request topology changes during a layout review.
- **Changes to the protected M2 composer or observers.** Placement changes stay in pivot-side steps.
- **PCB, footprints and fabrication.**
