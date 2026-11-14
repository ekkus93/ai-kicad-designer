# Reviewer loop: spec for the next round of work

**Status:** decisions recorded 2026-11-14; ready for implementation. Branch `mcp`.
**Tracks:** `docs/MCP_ARCHITECTURE_TODO.md` P6-011g to P6-011l, under P6-011.
**Sources:**
- the independent review `docs/ai_kicad_reviewer_independent_review_for_claude.md`, with recommendation IDs such as P0.3 and P1.4
- the applied-edit index `docs/pivot/REVIEWER_APPLIED_EDITS.md`
- the qualification runs `review_qualification_v9_*_2026-11-13_*`
- the questions and their answers: `docs/ai_kicad_reviewer_loop_spec_questions.md`. The answers came from ChatGPT at the owner's request, and the owner added the corrections in §5. They are design decisions, not evidence that any drawing, label or result has been signed off.

## 1. Goal

The schematic review loop renders a drawing, has a model review it, applies the edits the model requests, and reviews again. It should improve a drawing round after round. Today it does not:
- In every corpus run since 9 November the model accepted on its first review, and none of its edits reached an accepted drawing.
- In October its applied edits often made drawings worse: longer wires, more bends, routes around the page edge.
- In the 13 November qualification runs, with the check verdicts withheld, it rejected good and defective drawings at about the same rate.

The loop is only as useful as its edits are safe and its verdicts are informative. This spec covers:
- **R1:** reporting that says honestly what was checked
- **R2:** measuring whether an edit made the drawing better or worse
- **R3:** giving the model a menu of edits known to be feasible, instead of making it guess coordinates
- **R4:** structured refusals and batch rules
- **R5:** a versioned default reviewer profile and how its model is chosen
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
| Per-design review budgets: `max_reviews` (8 in corpus runs), `max_seconds` (1800), `max_model_tokens` (120000), all configurable | loop, corpus runner |
| **Safe edits (P0.1):** an edit that makes `native_tools`, `erc` or `electrical_equivalence` fail, or changes nothing, is rolled back. The previous drawing stays current and the model is told why | loop, `ccf9e5cc` |
| **No repeats (P1.3, partly):** asking again for an edit already refused on the same revision ends the run with `NO_PROGRESS` | loop, `ccf9e5cc` |
| Rails drawn with local power symbols, not long wires (P0.2, P1.2), within the 25.4 mm cap | briefs v3+, `a4d4a3ca`, `cb479802` |
| Power block layout for op-amp power units (P2.1, partly) | briefs v8/v9 |
| Qualification harness: 61 cases, blind mode, input options | `tools/pivot/qualify_review_v3.py` |
| 15 reference circuits with intended netlists, and their generated drawings | `fixtures/m2b/*.json`, corpus experiment dirs |

## 3. Requirements

### R0 — Brief v10 and reproducibility

- **Brief v10:** every behaviour change here goes behind a new immutable brief, v10, or a versioned service profile it names. This covers the R2 policy, the R3 menu and menu-only mode, the R4 equivalence rule and the R5 defaults.
- **Earlier briefs:** v1–v9 keep their editing and model behaviour exactly.
- **R1 reporting** changes no decisions, so it is emitted under every brief. Historical result artifacts are never rewritten.
- **Run records:** each run records the brief SHA-256, model ID and digest, CLI options, toolchain and corpus revision.

### R1 — Status levels instead of one verdict (review P0.3)

Each run result (`result.json`) and corpus summary reports these levels. Each is `PASS`, `FAIL` or `PENDING`, with its basis (check names and values). Missing or incomplete evidence is `PENDING`, never `PASS`.

| Level | Meaning | Basis |
|---|---|---|
| `NATIVE_VALID` | KiCad loads, exports and plots the sheet | `native_tools` |
| `ELECTRICALLY_EQUIVALENT` | the netlist matches the intended circuit **and** ERC passes | `electrical_equivalence`, `erc` |
| `PRESENTATION_PASS` | every deterministic readability check the brief enables passes | the brief's presentation checks |
| `QUALITY_NOT_WORSE` | no R2 measure is worse than on candidate 000 | R2; **reported only, not a gate** |
| `MODEL_ACCEPTED` | the reviewer's actual verdict was accept with no open issues | the review |
| `DESIGN_REQUIREMENTS_CHECKED` | the circuit was checked against its application requirements | `PENDING`; out of scope, see §6 |
| `HUMAN_REVIEWED` | a person reviewed readability and electrical correctness | `PENDING` until recorded |

**Which drawing the levels describe:**
- **Top-level levels:** they describe the **last safely committed current candidate**, whether accepted or not. A rolled-back scratch candidate never becomes current. If no later safe candidate exists, current is 000.
- **Other candidates reported:** candidate 000 and the best passing candidate are also reported, each with its own levels, SHA-256 and R2 measures.
- **Comparison base:** `QUALITY_NOT_WORSE` compares current with 000. Best passing versus 000 is computed separately. Per-edit deltas compare against the previous committed candidate.

**Edit outcome:** each edit records three separate fields:
- **Primary effect,** one of:
  - `FUNCTIONAL_REPAIR`: it fixed a failing connectivity check
  - `PRESENTATION_FIX`: it fixed a failing presentation check
  - `LAYOUT_CHANGE`: no check changed

  Precedence is `FUNCTIONAL_REPAIR` > `PRESENTATION_FIX` > `LAYOUT_CHANGE`. A run's primary effect is the highest among its kept edits.
- **Quality overlay:** `LOCAL_FIX_ONLY` when a fix makes any R2 measure worse; `QUALITY_REGRESSION` when a check-neutral change makes one worse; otherwise none. The overlay never hides the primary effect.
- **Disposition:** `KEPT` or `ROLLED_BACK`, with the R4 reason class. `ROLLED_BACK` is a disposition, not an outcome.

**Historical mapping**, used as tests:

| Case | Primary effect | Overlay | Disposition |
|---|---|---|---|
| rc_corrupted, `regenerate_schematic` | `FUNCTIONAL_REPAIR` | — | `KEPT` |
| inverting_gain, power-unit field move | `PRESENTATION_FIX` | — | `KEPT` |
| noninverting_gain 003→004 | — | — | `ROLLED_BACK` (connectivity) |
| October rail-continuity fixes | `PRESENTATION_FIX` | `LOCAL_FIX_ONLY`, where R2 shows the regression | `KEPT` |

**ERC disclosure:** the result lists the ERC check categories that are ignored.

**`ACCEPTED_FOR_REVIEW`:** it stays for existing tools. It is documented as implying only `ELECTRICALLY_EQUIVALENT`, `PRESENTATION_PASS` and `MODEL_ACCEPTED`. It does not imply design suitability, PCB readiness, human review or measured improvement.

### R2 — Quality measures and deltas (review P1.4)

For every candidate, compute these measures from the native schematic. Record per-edit deltas (from the previous committed candidate) and per-run deltas (from 000). Store raw values and per-measure *worse* flags, not one combined score. Report every individual worsening, even when other measures improve.

| Measure | Definition | Worse when |
|---|---|---|
| wire length | total wire length (mm) | it grows by more than max(12.7 mm, 5 % of the previous value) |
| rail detour | per asserted rail, numeric excess of the drawn route over the shortest feasible one, with the path recorded | it grows by more than max(5.08 mm, 10 % of the previous excess) |
| bends | topology-aware corners: a point where exactly two non-collinear wires meet, after merging collinear export segments | more than 2 are added |
| perimeter wires | paths at least 50.8 mm long within 2.54 mm of the routing envelope, with endpoints recorded | any new one appears, or total perimeter-path length grows by more than 25.4 mm |
| text clearance | minimum text-to-wire distance (`observed_text_wire_clearance_mm`) | it falls by more than 0.635 mm. An actual overlap stays a hard failure |
| field ownership | worst owner advantage over visible fields; larger is better | it falls by more than 1.27 mm. An ownership check failure stays a hard failure |
| page balance | centre-offset fraction of page width and height, plus occupied-area fraction | the offset grows by more than 0.03. Small circuits are not forced to fill the page |
| power symbols | per-rail count, plus flags for orphaned, ambiguous, redundant (several on one terminal group) or colliding symbols | never on count alone; only the flags count as worse |

**Boxes:** two are computed and recorded.
- **Symbol-core box:** component and connector bodies and pin anchors, without wires or text. It is used for grouping and placement.
- **Routing envelope:** wire and power-symbol geometry, without field text. It is used for perimeter routes.

For each suspect perimeter path, also record whether it skirts the symbol-core box unnecessarily, and whether a shorter feasible alternative exists. The exact perimeter predicate is defined with positive and negative fixture drawings.

**Policy under v10:**
- **Report-only.** No edit is rolled back for R2 alone.
- **Hard rollbacks stay mandatory:** native load, export or plot failure; an ERC or equivalence regression; a changed target circuit; a disallowed hard geometric collision.
- **Labelling:** edits are labelled with the R1 overlay.
- **Enforcement mode:** an opt-in mode, off by default, rolls back check-neutral edits that are worse. It is tested separately. It may be turned on in a later brief only after R6 (P6-011l3) shows that the thresholds agree with blind ratings.

**Starting values:** the thresholds are hypotheses, not validated standards. They live in the brief, so they can be retuned.

**Reporting:** the corpus summary reports, per design, the run's net delta, and per run the number of edits kept, kept with an overlay, and rolled back by reason.

### R3 — A menu of feasible edits (review P1.1)

The model chooses among edits the editor has already proved feasible, instead of inventing millimetre coordinates.

1. **Classes:**
   - field relocation (reference or value)
   - unit-safe symbol nudge
   - rail power-symbol placement and direction
   - rail reroute, where a feasible one exists
2. **What gets proposed:**
   - Fixes for failing checks come first.
   - When every hard and presentation check passes, up to **2 optional improvements** may be offered: better grouping, removing a perimeter route, cutting a clear detour, clarifying field ownership. Each must be concrete and measurable, with no cosmetic churn.
   - An empty menu is allowed. The model may then accept, and is never pushed to invent a flaw.
   - Equivalent moves are deduplicated.
3. **Caps:**
   - at most **3 entries per class**
   - at most **8 entries in total**
   - fewer when fewer safe options exist; no fillers
4. **Pre-check budget per review round:**
   - at most **12 cheap geometric proposals**
   - at most **8 full native scratch validations** (ERC plus netlist equivalence)
   - about **20 s** in total

   All three limits are configurable per host. Rank and prune cheaply first. Every displayed entry must have passed the native validation; a geometry-only candidate is never described as feasible. When the budget runs out, show the verified subset, with a `budget_exhausted` reason. Record the time and KiCad invocation count per round.

   This budget limits menu building inside one round. It does not limit the number of review rounds: the per-design budgets (`max_reviews` and the others, §2) do that, and they stay configurable for complicated schematics.
5. **Caching:** cache native validations by base-revision SHA-256, canonical action, toolchain and brief version. Invalidate the cache when the source changes.
6. **Entry content:**
   - an ID
   - its exact target: reference, unit, field or net
   - what it fixes
   - its predicted R2 delta
7. **Choosing:** `{"operation": "choose_edit", "id": "…"}`. The applied result must match the entry's scratch result.
8. **Menu-only first:** under v10 the first qualification is **menu-only**, and free-form edits are refused with `invalid_request`. Free-form editing stays available behind an explicit experimental flag or profile. It goes through the same native, ERC and geometry checks and is benchmarked separately. Menu-only, free-form and hybrid modes are compared on identical frozen cases, and their metrics are never pooled.
9. **Units:** parts are named by canonical `(reference, unit)`. A malformed reference list such as `references=['U1','unit','3']` is refused with a structured reason.

### R4 — Structured refusals and batch rules (review P1.3, remainder)

**Refusal content:** a refused or rolled-back edit sends machine-readable feedback with:
- **reason class:** `connectivity`, `no_change`, `quality` (enforcement mode only), `infeasible_route`, `invalid_request`, `repeat` or `budget_exhausted`
- **evidence:** the failing checks or measures, with values
- **alternatives:** up to three feasible ones from the R3 menu, where they exist

**Equivalence:** before comparing, canonicalize the action type, net, reference and unit, target field, coordinates and grid.
- **Coordinate edits:** a request is equivalent to a refused one when it has the same target, and its snapped movement or placement is within **one grid step per axis**. That is 1.27 mm, or the drawing's recorded grid if different.
- **Rail edits:** compare the canonical net, operation, scope and options. A change in a meaningful parameter is not a duplicate.
- **Scope:** the refusal cache is keyed by the exact base-revision SHA-256, not the whole run.

**Batches:**
- **Validation:** every edit is validated on a scratch or staged revision, and a failed stage is never exposed as current.
- **Dependent bundles:** a review may mark its actions as a dependent bundle. A bundle is committed all-or-none against the same starting revision.
- **Independent actions:** otherwise, independent actions are committed one at a time, as today, with per-edit and final deltas reported.
- **Safety:** a batch never relaxes native, ERC or equivalence safety.

### R5 — Default reviewer profile and model choice

**v10 profile defaults:**
- SVG source as text plus both PNGs (`--svg --with-images`)
- reasoning off
- check verdicts withheld
- menu-only edits
- up to 4 edits per review
- R2 report-only

**Model:**
- **Provisional baseline:** `qwen35-256k` (Qwen 3.5 9B with a 256k context). It is a baseline, not the declared winner.
- **Comparison:** at least two distinct model families on the same frozen R6 cases. `qwen35-256k` and `qwen3.5:9b` are the same weights, so comparing them is only a context-size ablation. The second family is `devstral-small-2:24b`; `qwythos-codex-q4` is optional as a third. Record each model's digest.
- **Held constant:** prompt, inputs, reasoning mode, sampling and edit policy.
- **Reported:** detection and naming quality, A/B improvement, latency, tokens and memory.
- **Choice:** the smallest and fastest model that meets the §4 bar. More context alone does not win. Historical October runs do not decide the default.

**Requalification:** required after any material change to the model digest, prompt, input modality, brief or editor.

### R6 — Benchmark and qualification (review P2.3)

The harness's "known-good" drawings predate the v8/v9 layout rules, and its defect matching counts generic words as hits. Replace both. Machine checks alone cannot label a drawing good, because that would only measure agreement with our own checks. Labels must come from independent raters.

1. **Baseline corpus:**
   - **Drawings:** the 15 reference designs regenerated under v10, plus variants (different values or part orders) and the R6.5 hold-outs.
   - **Rating:** raters mark each drawing *good* or list its defects, through a rating page that records answers in a form Claude can read.
   - **Counts:** the bar needs at least **30 independently rated good and 30 defective** cases across at least **six circuit families or defect classes**. With fewer, a result is labelled **PILOT**, not QUALIFIED.
2. **Defect labels:** each label gives the part (reference, unit, pin or net), the defect type and its location.
   - **Injected defects:** labels are generated from their exact injection manifests. Each injection must be verified to produce an observable defect; one that changes nothing is not a positive case. A stratified 20 % sample, at least 2 per category (or all, if a category has fewer than 2), plus every ambiguous or failed probe, is checked by hand.
   - **Historical and baseline defects:** hand-written and independently verified.
   - **Provenance:** every label records who or what produced it.
3. **Scoring by label:** a rejection *names the defect* only when it identifies the correct part or net **and** the substantive defect type. Vague rail or label language does not count. Retire the cue regexes. Report rates per defect class, so an average cannot hide a class the reviewer misses.
4. **Loop and edit quality:**
   - **Loop metrics:** the connectivity regression rate (must be 0), the rollback rate by reason and the R2 net delta per design.
   - **Blind A/B ratings:** start and final drawings are rated on six criteria: electrical correctness, node traceability, power-section clarity, text association, functional-block arrangement and overall preference. Each is rated 0–4, or win/tie/loss, with a short observation.
   - **Raters:** two independent ratings where possible, the owner's and ChatGPT's. Order is randomized, candidate identities are hidden, and both get the intended circuit. Neither sees the other's ratings.
   - **Records:** raw scores, rationales, image hashes and rater identity or version.
   - **Disagreements:** marked, not overridden. Consequential ones go to a third pass, ideally an independent electronics engineer. Results are reported before and after adjudication.
   - ChatGPT's ratings are a second review. They are not a substitute for KiCad-measured correctness or human electrical sign-off.
   - **Calibration:** the ratings are used to check whether the R2 thresholds predict preferences. That decides whether R2's enforcement mode or a `QUALITY_NOT_WORSE` gate is ever turned on.
5. **Hold-out circuits:**
   - **Circuits:** a transistor low-side switch, an enable-controlled LDO, a microcontroller power, decoupling and reset block, and an instrumentation or differential amplifier. The first three are the priority; the last is partly an op-amp test.
   - **Protected code:** protected M2 composer and observer code is not changed to make them work.
   - **New support:** pivot-side symbol, fixture or composer support is a separately scoped piece of work, with its own tests, finished before the hold-outs are frozen.
   - **Unsupported cases:** their count is published, not dropped.
   - **No tuning:** prompts and rules are not tuned against frozen hold-outs.
6. **Records:** each qualification run records, per case:
   - the drawing hashes
   - the model ID, digest, context, options and input mode
   - the raw reply and the model's action or menu IDs
   - the labels, the scores and the negative results
7. **Readability assessment:** for P6-011b and P6-011f, a blind R6 rating set counts as the independent readability assessment if it:
   - uses this rubric
   - covers several circuit families and final drawings (not just edited successes)
   - includes at least **15 baseline drawings and 10 before/after pairs**
   - keeps the disagreements and defect notes

   It does **not** satisfy human electrical review or design-requirements checks.

## 4. Acceptance criteria

- **Safety:** no accepted, kept or current candidate has a connectivity regression. Every edit that breaks connectivity is rolled back. This is met for single edits by `ccf9e5cc`; it is kept under R3 and R4.
- **Correctness:** no accepted drawing has an ERC error, and ignored ERC categories are disclosed (R1).
- **Presentation:** no text, symbol or pin-number overlaps. Long perimeter wires are detected and reported (R2).
- **Quality:** a run reports its R2 net delta. A fix that leaves the drawing worse carries `LOCAL_FIX_ONLY`, not a claim of improvement.
- **Loop progress:** no identical or equivalent refused edit is repeated on the same revision. An infeasible request gets alternatives, or a structured blocker when there are none (R4).
- **Traceability:** every kept edit has a before/after diff, the status levels, and its primary effect, overlay and disposition.
- **Reviewer qualification bar:** frozen before any model comparison scores are seen, and measured on a new, frozen, blind, independently labelled set.
  - **Known-good acceptance:** at least 80 % of good drawings accepted.
  - **Defect detection:** at least 80 % of labelled defects rejected or correctly flagged, reported overall and per class.
  - **Defect naming:** correct part or net and defect type in at least 70 % of correctly rejected cases.
  - **Safety:** zero accepted or kept connectivity regressions, and zero knowingly accepted ERC or equivalence failures. Any one disqualifies the profile. Confident false connectivity claims are reported separately, with a target of zero.
  - **Edit usefulness:** across at least 10 non-trivial edited A/B pairs, the edited drawing is preferred in at least 60 % of non-ties, with no unreported serious regression.
  - **Coverage:** at least 30 good and 30 defective cases across at least six families or classes, otherwise PILOT. Confidence intervals are reported, with at least three seeds for model selection where practical.

## 5. Decisions and owner corrections

The answers to Q1–Q17 are in `docs/ai_kicad_reviewer_loop_spec_questions.md` and are reflected above. The owner added three corrections on 2026-11-14:
- **Same weights:** `qwen35-256k` is Qwen 3.5 9B with its context window set to 256k, the same weights as `qwen3.5:9b`. A model comparison therefore needs another family (R5).
- **Menu budget is per round:** the menu pre-check budget limits work inside one review round only. The number of rounds per design is set by the separate per-design budgets, which stay configurable and may be raised for complicated schematics (R3.4).
- **Labels come from raters:** the reference circuits and their checks exist, but whether a drawing is readable has to come from independent raters (R6). The owner and ChatGPT do the ratings through a rating page.

**Owner decision, 2026-11-14:** for the v10 baseline (`review_baseline_v10_2026-11-14_run1`), ChatGPT's ratings are used as the ratings ("Just go with ChatGPT's rating"). The two-rater protocol of R6.4 is waived for that baseline. Its 5 good and 10 defective drawings fall short of the §4 coverage, so results on it are PILOT.

**Still to be provided:** the hand check of the injected-label sample, structured labels for the older historical cases, and a third adjudicator for consequential disagreements, if one is available.

## 6. Out of scope here

- **Electrical design review (review P2.2):** for example op-amp bias compensation, regulator dropout, or loading on the divider-based VREF. This is a separate pass with its own requirements. The reviewer may note such concerns as text, but must not request topology changes during a layout review.
- **Protected code:** changes to the protected M2 composer or observers. Placement changes stay in pivot-side steps.
- **PCB, footprints and fabrication.**
