# Reviewer loop spec: open questions

**Date:** 2026-11-14. Branch `mcp`.
**About:** questions raised by a review of the draft spec `docs/pivot/REVIEWER_LOOP_SPEC.md` and its tasks P6-011g to P6-011l in `docs/MCP_ARCHITECTURE_TODO.md`. They need the owner's answers before implementation starts.
**Written for:** the owner and an outside reviewer (ChatGPT). It is meant to make sense without the repository open.

## Background

The project generates KiCad schematics automatically. A **review loop** then improves each drawing:
1. Render the drawing (PNG, and optionally the SVG source or a text description).
2. Run independent checks: KiCad ERC, netlist equivalence against the intended circuit, and readability checks such as text placement, rail presentation, page balance and wire detours.
3. Send the drawing to a local LLM reviewer (`qwen35-256k` through Ollama). It accepts the drawing, or requests up to 4 typed edits: `move_field`, `move_symbols`, `connect_rail`, `use_power_symbols`, `regenerate_schematic`.
4. Apply the edits and go back to step 1.

Each *brief* (v1–v9) is a versioned JSON file that decides which checks and layout rules apply, so earlier runs stay reproducible.

**What went wrong, from the outside review of 65 historical cases:**
- Since 9 November, the reviewer has accepted every corpus drawing on its first look. None of its edits reached an accepted drawing.
- In October its applied edits often made drawings worse: longer wires, more bends, wires routed around the page edge.
- In one case (noninverting_gain), a move merged two nets, and the broken drawing became the loop's current drawing.
- In the 13 November blind qualification (check verdicts withheld), it rejected good and defective drawings at about the same rate.

**Already fixed (commit `ccf9e5cc`):**
- An edit that breaks ERC, netlist equivalence or KiCad's own load/plot, or that changes nothing, is rolled back, and the model is told why.
- Asking again for an edit already refused on the same drawing ends the run with `NO_PROGRESS`.

**The draft spec adds six requirements:**
- **R1:** separate status levels instead of one "accepted" verdict.
- **R2:** before/after quality measures for each edit.
- **R3:** a menu of edits pre-checked as feasible, chosen by ID.
- **R4:** structured refusal messages.
- **R5:** a default reviewer configuration.
- **R6:** a new labelled benchmark.

## Questions

### Status levels (R1)

**1. Are the status level names right, and should `QUALITY_NOT_WORSE` gate acceptance?**
The spec proposes these levels, each `PASS`, `FAIL` or `PENDING`:
- `NATIVE_VALID`
- `ELECTRICALLY_EQUIVALENT`
- `PRESENTATION_PASS`
- `QUALITY_NOT_WORSE`
- `MODEL_ACCEPTED`
- `DESIGN_REQUIREMENTS_CHECKED`
- `HUMAN_REVIEWED`

Today `ACCEPTED_FOR_REVIEW` means "all checks passed and the model said yes".
- *Option A:* `QUALITY_NOT_WORSE` is only reported.
- *Option B:* a run can't be `ACCEPTED_FOR_REVIEW` unless the final drawing is no worse than the starting one.

*Leaning:* report only, until the R2 tolerances have been tested on real runs.

**10. Which drawing do the status levels describe when a run doesn't accept?**
A run produces candidates 000 (the generated drawing), 001, 002 and so on. When the model never accepts, the levels could describe:
- the **best passing** candidate (all checks pass, model didn't accept)
- the **last current** candidate (where the loop stopped)
- candidate **000**

This changes what `QUALITY_NOT_WORSE` compares against.

*Leaning:* the last current candidate, with the best passing one reported separately, as it is today.

### Quality measures (R2)

**2. What tolerances should the quality measures use?**
The measures are:
- total wire length
- rail detour
- bends
- perimeter wires (long wires hugging the edge of the drawing)
- minimum text-to-wire clearance
- field ownership (whether a label is clearly nearest its own part)
- page balance
- power-symbol count

An edit is "worse" when a measure moves the wrong way by more than its tolerance. Suggested starting values:
- wire length: +5 %
- bends: +2
- text clearance: −0.635 mm (a quarter grid)
- perimeter wire: at least 50.8 mm long and within 2.54 mm of the drawing's bounding box

Sub-question: should the bounding box include text and fields, or only symbols and wires?

**8. Should R2's quality rollback be report-only for now?**
The spec says an edit that fixes no failing check but makes a measure worse is rolled back. The worry is that this blocks exactly what the reviewer is for: improvements no check measures. For example, moving a part to group a functional block more clearly can add wire without fixing any check.
- *Option A:* enforce the rollback now.
- *Option B:* report and label it only, and decide on enforcement once the R6 benchmark shows whether the measures agree with human judgment.

*Leaning:* B.

### Edit menu (R3)

**3. How many menu entries per issue class?**
The editor would offer pre-checked edits in four classes:
- field relocation
- symbol nudge
- rail-symbol placement
- rail reroute

More entries give the model more choice, but lengthen the prompt and cost more pre-checking time. *Suggested:* 3 per class.

**7. Should free-form edits stay allowed alongside the menu?**
- *Option A:* the model can pick a menu entry by ID or still invent its own edit, which goes through the same safety and quality checks.
- *Option B:* for a first qualification, menu choices only. This isolates whether the model chooses well among feasible edits.

*Leaning:* keep free-form edits, and record which kind each edit was, so the two can be compared.

**11. Should the menu offer improvements when every check already passes?**
As written, the menu covers "issues the editor can measure". After brief v9, most drawings pass every check, so the menu would usually be empty, and the reviewer would be back to guessing coordinates. The alternative is to also offer general improvements: tightening labels, re-aiming power symbols, nudging parts toward better grouping.

*Leaning:* yes, but rank them below fixes for failing checks.

**12. Is a time budget needed for pre-checking menu entries?**
Each entry is applied in a scratch copy and run through KiCad's netlist and ERC, about 1–3 s each. Four classes × 3 entries adds roughly 10–40 s per review before the model runs, and a full 15-design corpus already takes about an hour.
- *Option:* cap scratch KiCad runs per review, for example 12.
- *Option:* check connectivity geometrically first, and run KiCad only on the entries actually sent.

### Refusals (R4)

**16. Is a scripted replay of logged model replies acceptable evidence?**
One acceptance test uses an October run in which the reviewer repeated the same no-op `move_field` on connector J1 until the run ended. Reproducing it with the live model isn't possible, because the model and prompt have changed. The test would feed the logged replies through a scripted reviewer and check that the new loop refuses the repeat and offers an alternative.

*Leaning:* yes for the loop's behaviour. It says nothing about whether the model would recover.

### Default configuration (R5)

**13. Should the default reviewer be chosen by comparing several models?**
The proposed defaults come from one model, `qwen35-256k`:
- SVG source plus PNGs
- reasoning off (with reasoning on, it looped until the output cap on 14 of 23 cases)
- check verdicts withheld
- up to 4 edits

Also installed: `devstral-small-2:24b`, `qwen35-32k`, `qwen35-128k` and `qwythos-codex-q4`.
- *Option A:* keep `qwen35-256k`.
- *Option B:* qualify two or three models on the new benchmark and pick the best.

Option B costs a few hours of runs per model.

### Benchmark (R6)

**4. What result makes the reviewer "qualified"?**
An example bar:
- accepts at least 80 % of known-good drawings
- rejects at least 80 % of defective ones
- names the labelled defect in at least 50 % of rejections
- makes no false connectivity claims, such as saying a rail is unconnected when it is connected

The 13 November runs were far below this: they rejected good and bad drawings at similar rates, and often made false rail claims.

**5. Which hold-out circuits, and may they need new library or composer support?**
All current designs are 555 timers, op-amp stages, RC filters, LEDs and a regulator. Hold-out candidates:
- a transistor switch
- an LDO with enable
- a microcontroller decoupling block
- an instrumentation amplifier

Some may need symbols or layout rules the locked KiCad library or the protected composer don't support yet. Should hold-outs be limited to what the system can already draw, or is extending support acceptable as part of this work?

**6. Who rates the blind A/B comparisons, and how are disagreements settled?**
The benchmark compares the starting and final drawings of each run, blind, on six criteria:
- electrical correctness
- node traceability
- power-section clarity
- text association
- functional-block arrangement
- overall preference

Raters could be the owner, ChatGPT, or both. With two raters, one option is that the owner's rating wins, and disagreements are reported.

**14. May injected defect labels be generated automatically?**
The spec asks that every defect case carry a hand-written label: the part, the problem and its location. The 32 injected defects, such as a detached value or a shifted part, are made programmatically, so their labels can be written exactly from the injection parameters.
- Historical defects need hand-written labels.
- New-baseline defects need hand-written labels.
- Injected defects: *proposal:* generate their labels, and check a sample by hand.

**17. Does the A/B rating count as the independent readability assessment?**
Older tasks P6-011b and P6-011f can't be checked off without an "independent readability assessment", and no new task produces one explicitly. If the owner (or another person) does the R6 A/B ratings, should that count as the assessment? Or is a separate review of the final corpus drawings needed?

### Task structure and reproducibility

**9. Should all behaviour changes be switched on by a new brief v10?**
R2's rollback, R3's menu, R4's equivalence rule and R5's defaults all change how the loop behaves. The project's pattern is to put each behaviour change behind a new brief version, so v3–v9 runs still reproduce exactly. The spec doesn't say so explicitly.

*Proposal:* brief v10 turns them on. R1's reporting applies to every brief, because it changes no behaviour.

**15. Should the large tasks be split and reordered?**
- **P6-011i (menu)** covers four edit classes, scratch verification, `choose_edit`, and unit addressing. *Proposed split:*
  - i1: field relocation plus `choose_edit` (cheapest, most often needed)
  - i2: symbol nudges
  - i3: rail-symbol placement and reroutes
- **P6-011l (benchmark)** mixes owner work, automated work and new circuits. *Proposed split:*
  - l1: new baseline and labels
  - l2: label-based scoring
  - l3: loop and edit-quality metrics with rating records
  - l4: hold-out circuits
- **P6-011k (default profile)** has a circular dependency. The new baseline must be generated under some brief, but k defines that brief and depends on l. *Proposal:* k creates the brief/profile first, and its qualification moves into l.

## Answers for Claude — independent reviewer recommendations (2026-11-14)

These answers are proposed implementation decisions supplied by ChatGPT at the owner's request. They are **not** evidence that the owner has separately signed off on the benchmark labels, design-requirements review, or final acceptance of any schematic. They are intended to unblock implementation and to update the draft spec and TODO accordingly. Preserve the original questions above for traceability.

### Q1 — Status names and the QUALITY_NOT_WORSE gate

**Decision: keep the seven names, but make QUALITY_NOT_WORSE report-only for v10 qualification.** Clearly document their exact evidence and the distinction between a review-loop verdict and production readiness. NATIVE_VALID checks KiCad's load/export/plot; ELECTRICALLY_EQUIVALENT requires *both* native netlist equivalence and ERC; PRESENTATION_PASS covers only enabled deterministic checks; MODEL_ACCEPTED is the model's actual verdict; DESIGN_REQUIREMENTS_CHECKED and HUMAN_REVIEWED remain PENDING until independently supported. Missing or incomplete evidence is PENDING, not PASS.

Keep the legacy ACCEPTED_FOR_REVIEW status for compatibility, but do not imply it certifies design suitability, PCB readiness, human review, or measured improvement. QUALITY_NOT_WORSE should be recorded on every run, without initially gating that legacy status. Reconsider the gate only after Q4/Q6 calibration demonstrates that its tolerances predict blind human judgments. Hard electrical-safety gates already apply regardless of R2.

### Q2 — Numerical R2 tolerances and perimeter bounding box

Use these **initially advisory** thresholds; store both raw values and pass/worse flags, rather than collapsing them into a single opaque score:

| Measure | Tentative worse threshold | Caveats |
|---|---|---|
| Total wire length | Increase greater than **max(12.7 mm, 5% of previous value)** | Evaluate *in context*; a slightly longer local route can improve readability. |
| Asserted-rail detour | Excess grows by more than **max(5.08 mm, 10% of prior detour)** | First implement a numeric per-net excess and record witnesses/paths; do not use old binary PASS/FAIL as a distance. |
| Wire bends | **More than 2** additional bends | Count topology-aware non-collinear junctions consistently, not raw export segments. |
| Long perimeter wire | Any **new** qualifying perimeter path of at least **50.8 mm** within **2.54 mm** of the route envelope, or >25.4 mm additional total perimeter-path length | Record the path and endpoints; do not punish legitimate short edge connectors. |
| Minimum text-to-wire clearance | Decrease greater than **0.635 mm** | Any actual collision/overlap remains a hard failure regardless of tolerance. |
| Field ownership | Worst owning-symbol advantage degrades by more than **1.27 mm** | Normalize the sign convention explicitly (larger separation from non-owner should be better); any owner-association check failure remains a hard presentation failure. |
| Page balance | Center-offset fraction worsens by **>0.03** of page width or height | Also record occupied-area fraction; don't force tiny circuits to fill the page. |
| Power-symbol count | **No automatic count-only penalty** | Flag orphaned, ambiguous, redundant-on-one-terminal-group, or colliding symbols; per-net count changes are diagnostic, since replacing long wires may legitimately increase symbols. |

**Bounding boxes:** calculate a **symbol-core box** from component bodies, connector bodies, and pin anchors (exclude wires and text) for functional placement and grouping. Separately calculate a **routing envelope** from wire/power-symbol geometry (exclude field/text extents) for detecting perimeter-hugging routes. Record both. Do *not* base the perimeter rule solely on a box containing the very wires being penalized; that metric is easy to game and can misclassify a far-away perimeter path as normal. For each suspect path, additionally check whether it unnecessarily skirts the symbol-core box and whether a shorter feasible connection/symbol alternative exists. Define the exact geometric predicate with positive/negative fixture drawings before enabling any rollback.

The thresholds are starting hypotheses, not human-validated quality standards. Report every individual worsening, even if the composite quality score improves.

### Q3 — Menu size per issue class

**Start with up to 3 entries per relevant class**, ranked by expected issue resolution and measured cost. Also enforce **8 total menu entries** in a normal review to limit prompt noise and preprocessing cost. If fewer safe options exist, show fewer; do not invent fillers. Prioritize failing checks, then optional readability improvements. Deduplicate equivalent moves and show what each option fixes, its predicted R2 delta, and its exact target (reference plus unit).

### Q4 — Reviewer qualification bar

Set a **pre-registered first qualification bar**, evaluated on a *new, frozen, blind and independently labelled* set, not on previously seen examples:

- **Known-good acceptance:** at least **80%** of independently verified good drawings.
- **Defect detection:** reject or correctly flag at least **80%** of labelled defective drawings, with both aggregate and per-defect-class rates reported.
- **Defect naming:** identify the **correct component/net AND the substantive defect type** in at least **70%** of correctly rejected defect cases; vague rail/label language does not count.
- **Safety:** **zero** accepted/kept electrical connectivity regressions and zero knowingly accepted ERC/equivalence failures. Any such failure disqualifies the profile. Report confident false connectivity assertions separately; target **zero** on the qualification sample, rather than silently ignoring them.
- **Edit usefulness:** for at least **10 nontrivial edited A/B pairs**, among non-ties the post-edit drawing must be preferred in **at least 60%**, with no unreported serious regression.
- **Coverage:** aim for **at least 30 independently rated good** and **30 defective** cases spanning at least **six circuit families/defect classes**; report confidence intervals and run at least **three deterministic seeds** for model selection where practical. If sample counts fall short, label the result PILOT rather than QUALIFIED.

Freeze the bar *before* looking at model comparison scores. Track per-class misses so an overall average cannot hide a failure on rail, field, or connectivity defects. Requalification is required for material changes to the model digest, prompt, input modality, brief, or editor.

### Q5 — Hold-out circuits and library/composer changes

Use **a transistor low-side switch**, **an enable-controlled LDO**, **a microcontroller power/decoupling and reset block**, and **an instrumentation/differential amplifier** as contrasting hold-outs. Prioritize the first three for genuinely different layout motifs; the instrumentation amplifier is still partly an op-amp-family test. Include both power-symbol and signal-path challenges.

**Do not alter protected M2 composer/observer implementations merely to pass R6.** Build the main benchmark using currently supported circuit capabilities. If a hold-out needs new functionality, permit separately scoped *pivot-side* symbol/fixture/composer support, with explicit evidence and its own tests, before freezing the hold-out corpus. Keep such extension work out of the model qualification score until it is stable; publish the unsupported count rather than silently dropping difficult cases. Do not train/prompt-tune against the frozen hold-outs once they are locked.

### Q6 — Blind A/B raters and disagreements

Use **two independent ratings when possible: the owner and ChatGPT**, with order randomized, identities/candidate numbers hidden, and the original intended circuit supplied equally to both. Record a per-criterion rubric (0–4 scale or win/tie/loss with short supporting observations), raw scores, rationales, image hashes and rater identity/version. Neither rater sees the other's score beforehand.

Disagreements are **not silently overridden**. Require both independent ratings in the record, mark a disagreement, and adjudicate consequential disagreements in a third pass (ideally by an independent electronics engineer). The owner can make the final project/product judgment, but the reported benchmark should retain raw independent outcomes and show results both before and after adjudication. ChatGPT's opinion is a second review, **not** a substitute for measured KiCad correctness or required human electrical sign-off.

### Q7 — Free-form edits versus menu choices

**For the first controlled R3/R6 qualification, use menu-only editing.** That isolates whether the reviewer can choose good, feasible edits without failures due to invented coordinates. Keep free-form editing **available behind an explicit experimental flag/profile**, validated by the *same* transactional native-equivalence, ERC and geometry checks, and benchmark it separately. After obtaining a qualified menu-only baseline, compare menu-only, free-form-only, and hybrid modes on identical frozen cases. Do not pool their metrics.

### Q8 — Quality rollback enforcement

**Option B: report and label quality regressions first; do not automatically roll back on R2-only deterioration in v10.** The current heuristic would otherwise reject useful topology-aware regrouping when that improvement is not yet measured. Continue mandatory rollback for any native load/export/plot failure, ERC or equivalence regression, changed target circuit, or disallowed hard geometric collision.

Record whether a candidate (a) fixes a failing check, (b) introduces any R2 worsening, and (c) is preferred in the blind A/B. A fix that worsens a metric should carry LOCAL_FIX_ONLY (or an explicit quality-regression overlay), not an unqualified improvement. A check-neutral layout change that worsens a metric remains flagged, even if provisionally kept; promote R2 rollback to an enforceable policy only after R6 validates the metrics. **Update P6-011h's acceptance text** so it tests advisory labeling first and policy-enforced rollback in a separately enabled mode—not unconditional quality rollback on v10.

### Q9 — Brief v10 and reproducibility

**Yes.** Put behavior-changing review settings (R2 policy, R3 menu/menu-only mode, R4 refusal equivalence, R5 input/default configuration) behind an immutable **brief v10** or a versioned service profile explicitly referenced by v10. Keep briefs v1–v9 behaviorally reproducible. The new R1 status *reporting fields* may be emitted by all versions without altering their editing or model decisions, but do not retroactively rewrite historical result artifacts. Record the brief SHA, model digest, CLI options, toolchain and qualification corpus revision.

### Q10 — Which candidate's statuses describe an unaccepted run?

**Use the last safely committed current candidate for the top-level statuses**, whether accepted or not, matching the existing loop semantics. Also report candidate 000 and **best independently passing** candidate explicitly, with their own statuses, hashes and metrics. A rejected/rolled-back scratch candidate must never become current. If no later safe candidate exists, current is 000.

QUALITY_NOT_WORSE for the top-level current candidate always compares **current versus candidate 000** (not versus the last edit); per-edit R2 deltas compare against the immediately preceding safely committed candidate. Also compute *best-passing versus 000* separately. Do not substitute a better candidate in the top-level status without labeling which revision it describes.

### Q11 — Offer menu improvements when all checks pass?

**Yes, but only concrete, safe, measurable suggestions.** After all hard and presentation checks pass, offer up to **2 optional proposals** (within the overall menu cap) for grouping, eliminating a perimeter route, reducing clear wire detours or clarifying ownership/labels. Include their predicted deltas and avoid cosmetic churn. If no defensible improvement is found, leave the menu empty and allow acceptance; do not require the model to fabricate a flaw or coordinates. A reported image issue not covered by the editor should be logged for future rule development rather than treated as grounds for speculative unsafe edits.

### Q12 — Pre-check budget

**Yes.** Use an explicit budget: at most **12 cheap geometric proposals considered, 8 full native scratch validations, and roughly 20 seconds total** per review for generating the menu (configurable per host). Rank and prune cheaply first; fully verify *every displayed entry* via native KiCad ERC/netlist equivalence before offering it. Never describe a geometry-only candidate as “pre-checked feasible.” If the budget expires, emit the subset already verified plus a structured budget-exhausted reason. Cache assessments by immutable base-revision hash, action, and toolchain/brief version; invalidate on source changes. Record the time and number of KiCad invocations so the cap can be tuned empirically.

### Q13 — Compare models for R5 defaults?

**Option B: qualify multiple models.** Use the current qwen35-256k configuration as the **provisional baseline**, not the declared winner. Compare at least **two genuinely distinct model families/configurations** on the same frozen R6 cases—for example the existing Qwen3.5 9B profile and devstral-small-2:24b, optionally adding a Qwen context/window variant as an ablation. Verify actual model sizes/digests rather than assuming names denote different weights. Hold prompt, image inputs, reasoning mode (off for the baseline), sample conditions and edit policy constant, then report detection/naming quality, A/B improvement, latency, token use and memory requirements. Choose the smallest/fastest model that meets Q4's safety and quality bar; more context alone should not win. Do not change the default based only on historical October runs.

### Q14 — Automatically generated injected-defect labels?

**Yes** for deterministic synthetic injections, generated from their exact injection manifests (component reference/unit/pin, defect type, position, and original/intended revision). Require visual/native verification that the injection actually produced the alleged defect; an injection that makes no observable change is not a positive case. Hand-check a **stratified 20% sample, with at least 2 from each defect category** (or all if a category has fewer than 2) plus every ambiguous or failed probe. Historical and baseline defects must be independently written/verified, not inferred only from a programmatic mutation. Store label provenance so scorer reliability can be audited.

### Q15 — Split and reorder tasks?

**Yes.** Split P6-011i into **i1** field relocation/choose_edit, **i2** unit-safe symbol nudges, **i3** power symbols and rail reroutes. Split P6-011l into **l1** baseline and labels, **l2** label-based scoring, **l3** blind A/B ratings plus loop/edit metrics, **l4** hold-outs. Split P6-011k into **k1** creation of an immutable v10 profile and **k2** model/profile qualification (the latter can be done within l3/l4 to avoid duplicate requirements). A workable order is **g → h(reporting) → k1 → i1/i2/i3 → j → l1 → l2 → l3 → l4 → k2/final qualification**, with h's quality-enforcement mode deferred until l3 demonstrates calibration. Document each dependency as evidence-based, not a circular checkbox. Maintain the protected-component boundaries.

### Q16 — Scripted replay acceptable for refusals?

**Yes for testing the loop/controller contract**, including equivalence normalization, same-base-revision replay, structured reason codes, rollback, and alternative suggestions. Replay the October J1 move_field no-op and also wrong-unit, zero-length-route, and unsafe-net-merge cases. Pin exact prior revision hashes and expected responses so the test is deterministic. **No**, replay alone is not evidence that a *live model* will recover or choose a better operation; that needs separately measured live blind runs. Keep these two test claims distinct.

### Q17 — Does R6 A/B satisfy independent readability assessment?

**Yes, conditionally.** A blind, independently recorded R6 A/B assessment can count for P6-011b/P6-011f's **readability** evidence if it uses the defined rubric, covers multiple circuit families and final drawings (not just edited successes), includes at least **15 baseline examples plus 10 before/after pairs**, and preserves disagreements and concrete defect notes. It does **not** automatically satisfy the separate **human electrical review** or design-requirements verification; those remain PENDING until a qualified person reviews the underlying circuits and records evidence. Cross-link the actual rating dataset and protocol in the TODO before checking either task.

### Additional decisions to resolve the spec's non-question notes

1. **Outcome classes:** keep *primary effect* separate from *quality effect*. Prefer primary precedence **FUNCTIONAL_REPAIR > PRESENTATION_FIX > LAYOUT_CHANGE**, with LOCAL_FIX_ONLY/quality regression recorded as a secondary overlay when an otherwise helpful fix worsens R2. If the existing enum cannot represent two dimensions, add separate fields rather than hiding a functional repair behind LOCAL_FIX_ONLY. ROLLED_BACK is a disposition, not a kept-edit outcome.
2. **Batches:** validate *each* proposed edit on a scratch or staged revision; never expose a failed stage as current. For an explicitly dependent multi-action bundle, commit all-or-none against the same starting revision. For independent sequential actions, commit each safe edit individually and report per-edit and final net deltas. A batch never relaxes native/ERC/equivalence safety.
3. **Equivalent operations:** canonicalize action type, net, reference/unit, target field, coordinates and grid first. For coordinate operations, equivalence means same target and snapped movement/placement within **one 1.27 mm grid step per axis** (unless the applicable project grid differs, in which case use the recorded actual grid). For non-coordinate rail operations, compare canonical net, operation, scope and options; changes in meaningful parameters are not duplicates. Refusal-cache scope is the exact base-revision hash, not the whole run.
4. **Historical mapping:** rc_corrupted regeneration = FUNCTIONAL_REPAIR; inverting_gain power-unit field move = PRESENTATION_FIX; noninverting_gain unsafe 003→004 = ROLLED_BACK/connectivity (not a valid kept edit). October rail-continuity fixes can be PRESENTATION_FIX **with a measured quality-regression overlay** even when all configured checks later pass.
5. **Qualification evidence:** record negative results, unavailable hold-outs, both original and accepted candidate SHAs, objective checks, independent ratings and the model's raw action IDs. “Accepted” without native and rating evidence is not proof of a better engineering drawing.

**Requested follow-up for Claude:** reflect these decisions in the draft spec and TODO acceptance criteria before implementation, especially the intentional changes to R2 quality rollback, R3 menu-only first qualification, explicit candidate provenance, and the k/l dependency cycle. Do not mark implementation tasks complete merely because these recommendations have been documented.

## Other points from the review (no decision needed, for awareness)

- **Outcome class order:** when an edit's outcome classes compete, the spec says to use the "most significant" class without defining an order. The assumed order is functional repair > presentation fix > local fix only > layout change, with a separate `ROLLED_BACK` for refused edits. It also needs deciding whether a batch is classed per edit or as a whole.
- **Rail detour:** today the rail-detour check reports only pass/fail with examples, so R2 needs it extended to report a number.
- **Equivalent edits:** "within one grid step" needs defining per edit type. Rail edits have no coordinates, so for them "equivalent" means identical.
- **Batch rules:** batched edits already stop when any passing check breaks, which is stricter than R2's single-edit rule. The spec should say which rule batches follow.
- **Two tools for R6:** detection rates come from the single-review qualification harness (`tools/pivot/qualify_review_v3.py`); edit-quality metrics come from corpus loop runs (`tools/pivot/run_review_loop_corpus.py`).
- **Historical classification:** P6-011g's acceptance asks historical cases to "classify as in the outside review", but that review used different labels. It needs an explicit mapping, for example:
  - inverting_gain → presentation fix
  - rc_corrupted → functional repair
  - noninverting_gain 003→004 → rolled back for connectivity
