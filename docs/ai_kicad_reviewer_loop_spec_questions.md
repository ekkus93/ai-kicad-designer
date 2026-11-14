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
