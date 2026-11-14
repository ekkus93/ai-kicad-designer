# Independent engineering review: AI KiCad Designer reviewer-applied edits

**Prepared:** 2026-11-13  
**Repository:** `ekkus93/ai-kicad-designer`, `mcp` branch  
**Primary index:** [docs/pivot/REVIEWER_APPLIED_EDITS.md](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/docs/pivot/REVIEWER_APPLIED_EDITS.md)  
**Scope:** The document's historical Oct 25–31 experiments; detailed before/after inspection of representative cases across distinct circuit families, plus sampled saved `assessment.json`, `result.json`, and KiCad-exported `netlist.xml` records. This is not a claim of having manually inspected every rendered candidate in all 65 cases.

## Executive findings

1. **Strong foundation:** A reviewer can request constrained edits; the editor records candidate revisions and review history; electrical-equivalence, KiCad ERC, and geometric checks independently assess results. Valid cases include an RC filter with an initially disconnected input wire that is restored by `regenerate_schematic`.
2. **Major quality gap:** The system often optimizes *passing the rail-continuity rubric*, not *readability*. Several accepted candidates have much longer power-net wiring and more bends, visibly degrading the drawing. Requiring a continuous drawn rail in all circumstances is a poor default when local named KiCad power/net symbols would communicate the same connection much more clearly.
3. **P0 safety bug:** In `review_loop_corpus_2026-10-27_qwen35_256k_run1/noninverting_gain`, candidate 004 follows a `move_symbols(U1, dx=-1.27 mm)` review action. It incorrectly merges REF and VMINUS, placing both terminals of C2 on the same net. Candidate 003 was electrically equivalent; candidate 004 fails electrical equivalence and KiCad ERC (three violations). Detection succeeded, and the bad candidate was **not** accepted; the editor nonetheless needs transactional, connectivity-preserving edits and immediate rollback.
4. **Control-loop failure:** Invalid/unchanged tool proposals and infeasible rails get repeated. The reviewer needs a clear machine-readable description of feasible actions and explicit avoidance of repeated failures.
5. **Completion is overstated by labels:** `ACCEPTED_FOR_REVIEW` means that the configured checks passed, **not** human engineering sign-off or PCB readiness. Sampled `result.json` files say `human_electrical_review: PENDING` and `locked_host_qualification: false`.
6. **Model attribution:** The historical index includes `qwen3.5:9b` and custom aliases such as `qwen35-32k:latest` and `qwen35-256k:latest`. Do not attribute all 65 cases to one fixed 9B configuration without the individual `result.json` model/digest evidence.

## Historical index statistics

| Result | Cases | Rate |
| --- | ---: | ---: |
| `ACCEPTED_FOR_REVIEW` | 19 | 29.2% |
| `NO_PROGRESS` | 37 | 56.9% |
| `LIMIT_REACHED` | 8 | 12.3% |
| `TOOL_ERROR` | 1 | 1.5% |
| **Total** | **65** | **100%** |

The 19 accepted entries include repeated runs on the same benchmark circuit families and are **not** 19 independent designs. The index explicitly says no edits were applied after October 31 as of its writing. These statistics are not a measured success rate of the most recent 9B system.

## Representative before/after measurements

Measurements below are from stored candidate `assessment.json` layout records, not estimates from pixel images.

| Circuit | Candidate 000 wires (mm) | Inspected later candidate wires (mm) | Wire bends before→after | Saved outcome | Human-quality judgment |
| --- | ---: | ---: | ---: | --- | --- |
| 555 LED flasher | 429.26 | 558.80 | 15→20 | Accepted (002) | Added long VCC/REF paths; a mixed or negative readability change |
| 555 astable timer | 411.48 | 537.21 | 20→23 | Accepted (003) | Rail check fixed, excessive perimeter wiring remains |
| Dual buffer | 452.12 | 527.05 | 16→29 | Accepted (007) | Rail and field checks fixed, physical layout noticeably busier |
| L7805 regulator | 160.02 | 219.71 | 6→9 | Accepted (002) | Function intact, but rectangular VIN/REF detours unnecessary |
| RC filter + op-amp buffer | 547.37 | 880.11 | 21→29 | Accepted (004) | Severe visual regression: perimeter supply routing |
| Inverting-gain amplifier | 725.17 | 725.17 | 26→26 | Accepted (003) | Valid field-owner fix, but **no** routing improvement |
| Sallen–Key filter | 557.53 | Not reliably available from failing last layout | 16→not available | Limit reached (007) | Useful local power symbols, but four validation checks still fail |

Do **not** use reduced wire length as a hard gate by itself. More wire can be appropriate when it clarifies important signal topology. However, increases this large accompanied by long perimeter routes are strong evidence that the current review reward is misaligned with engineering drafting quality.

## Case-level observations and reproducible links

### 1. Reference 555 LED flasher — partial success
- [Before drawing (000)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run1/reference_555_led_flasher_v8/candidates/000/review-images/drawing.png)
- [Accepted drawing (002)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run1/reference_555_led_flasher_v8/candidates/002/review-images/drawing.png)
- Good: recognizable NE555 timing ladder R1/R2/C1, control bypass C2, LED plus current limit; verified electrical equivalence, ERC and explicit VCC/REF representation.
- Bad: long VCC and REF trunks across the sheet, oversized rectangular wire paths, increased bends and wiring. The 10 nF control-pin bypass should not be confused with a local 100 nF VCC-to-REF supply bypass; check whether the application design requires the latter.
- Fix: local power symbols; minimize detour length; organize the 555, timing ladder, LED branch and supply connector into logical blocks; verify RESET pin 4 and CONT pin 5 connections independently.

### 2. 555 astable timer — partial success
- [Before (000)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run1/timer_astable/candidates/000/review-images/drawing.png)
- [Accepted (003)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run1/timer_astable/candidates/003/review-images/drawing.png)
- Good: main astable structure preserved and rail checks pass.
- Bad: unwieldy top VCC/REF routes; wire density near 555 pins; increased bends and length. Output connector is distant and wired via a long perimeter route.
- Fix: local symbols for VCC/REF, keep timing nodes visually local, group pin 5 capacitor near pin 5, make OUT a short labeled net to J2.

### 3. Dual buffer (in fact one active buffer and one parked follower in intended spec) — poor final aesthetics
- [Before (000)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/dual_buffer/candidates/000/review-images/drawing.png)
- [Accepted (007)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/dual_buffer/candidates/007/review-images/drawing.png)
- Good: negative feedback is obvious for both op-amp units; intended netlist matches observed; editor resolves field and rail checks.
- Bad: large top wire from power/reference region to U1B, dense routing around J1 and U1C, perimeter VMINUS wire and 29 bends; output is visually isolated from connector.
- Fix: use separate signal/power groupings; label REF at parked amplifier locally; arrange C1/C2 beside U1C; do not route rails around entire drawing to satisfy an overly strict visible-continuity check.

### 4. L7805 linear regulator — valid circuit structure, mediocre editing
- [Before (000)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/linear_regulator/candidates/000/review-images/drawing.png)
- [Accepted (002)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/linear_regulator/candidates/002/review-images/drawing.png)
- Good: L7805 with 330 nF input, 100 nF output, clear IN/OUT connections; recorded netlist and ERC pass.
- Bad: needlessly long VIN looping at J1 and REF rail beneath both capacitors; awkward connector distribution.
- Fix: VIN left → L7805 → VOUT right; input/output capacitors below their nets with local REF symbols. Verify voltage headroom, load current, thermal power and manufacturer-specific capacitor recommendations separately from layout.

### 5. RC-to-op-amp buffer — one of the largest regressions
- [Before (000)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/rc_to_buffer/candidates/000/review-images/drawing.png)
- [Accepted (004)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/rc_to_buffer/candidates/004/review-images/drawing.png)
- Good: recognizable R1/C3 low-pass network feeding U1A buffer; electrical checks pass.
- Bad: massive rectangular VPLUS/VMINUS routes surround the schematic; wiring grows 547→880 mm; system optimizes visible rail wires at the expense of presentation.
- Fix: use matching supply symbols at J1 and U1C; a local REF symbol at C3 and U1B; separate analog signal flow from power distribution. Should be a **negative regression fixture**: final quality score must not improve just because all rail continuity checks pass.

### 6. Inverting gain — valid narrow improvement
- [Before (000)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-31_qwen35_32k_run1/inverting_gain/candidates/000/review-images/drawing.png)
- [Accepted (003)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-31_qwen35_32k_run1/inverting_gain/candidates/003/review-images/drawing.png)
- Good: U1C reference/value field repositioning resolves its ownership check, no electrical changes.
- Bad: schematic power-rail and REF perimeter wiring remains sprawling and the intended gain stage is not as clean as later Nov 11–13 benchmarks; 725.17 mm unchanged.
- Fix: count this as `LABEL_FIX_ACCEPTED`, not `SCHEMATIC_LAYOUT_OPTIMIZED`; run a separate power-layout pass using local symbols and topology-aware blocks.

### 7. Sallen–Key filter — useful progress, not accepted
- [Before (000)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/sallen_key/candidates/000/review-images/drawing.png)
- [Last inspected (007)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/sallen_key/candidates/007/review-images/drawing.png)
- Good: signal network R1/R2, C3/C4, U1A is recognizable; using local symbols improves part of rail organization.
- Bad: `observed_layout`, `rail_presentation`, `power_symbol_clearance`, and `field_owner_association` fail. Diagnostics cite VPLUS label overlapping J1 pin number, and power symbols touching other objects. Limits reached without acceptance.
- Fix: reserve connection-symbol space near connector pins; explicitly prohibit pin-number and label collisions; use candidate layout feasibility checks before requesting a power-symbol insertion; keep filter topology grouping stable.

### 8. Noninverting gain — **P0 connectivity regression**
- [Before (000)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/noninverting_gain/candidates/000/review-images/drawing.png)
- [Candidate 003 (electrically valid)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/noninverting_gain/candidates/003/review-images/drawing.png)
- [Candidate 004 (electrically broken)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/noninverting_gain/candidates/004/review-images/drawing.png)
- What happened: `move_symbols(references=['U1'], dx_mm=-1.27, dy_mm=0)` generated candidate 004. It merges the `REF` and `VMINUS` nets. J1.4, J1.5, U1.4, U1.5 and **both C2 pins** share one electrical net. The saved ERC reports three violations: power-output/power-output connection, `REF` + `VMINUS` combined, and unconnected wire endpoint. Candidate 000–003 had PASS electrical equivalence; 004 fails.
- Correct safeguard already present: independent ERC/electrical-equivalence checks detect the fault, and the run does not accept candidate 004.
- Required change: edit transaction with post-edit native netlist pin-partition equivalence **before a candidate is made active**; reject and revert any mismatch. Add exact regression test `003 → move U1 −1.27 mm → reject/rollback`.

### 9. Dual-rail reference — engineering ambiguity beyond mere wires
- [Before (000)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/dual_rail_reference/candidates/000/review-images/drawing.png)
- [Last (004)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/dual_rail_reference/candidates/004/review-images/drawing.png)
- Good: intended divider (R1=R2=10k) is visible and VPLUS/VMINUS rails are identifiable. Last candidate's stored electrical equivalence and ERC pass, though run is `NO_PROGRESS` due to blocked operations.
- Bad: middle reference node is taken straight from a resistor divider. U1B is explicitly specified as a **parked follower** whose output pin 7 is connected only to its own inverting input, not to J1.5/VREF. Thus **VREF is not an op-amp-buffered low-impedance virtual ground**. If it is expected to drive significant return current, the analog design is unsuitable; the midpoint will shift with load. This is an application-dependent design concern, not an error in the target netlist checker.
- Fix: clarify the intent. If low-impedance virtual ground required, use an appropriately designed midpoint buffer with output drive/current limits and suitable stability checks, rather than silently assuming a 10k/10k divider suffices. Reviewer should flag this only as design requirement review, not perform unrequested topology changes.

### 10. LED reverse-supply — label correction gets stuck
- [Before (000)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-31_qwen35_32k_run2/led_reverse_supply/candidates/000/review-images/drawing.png)
- [Last (003)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-31_qwen35_32k_run2/led_reverse_supply/candidates/003/review-images/drawing.png)
- The simple series LED/resistor to a negative supply is easy to recognize. The editor moves J1's reference/value, but puts `J1` directly against `Reference` visually; `field_separation: FAIL` explicitly identifies `J1:1.Reference` overlapping `J1:1.Value`. The reviewer then **repeats the exact same no-op move** instead of choosing a different placement.
- Fix: automatic field placement from obstacle-aware anchor candidates, with overlap evaluation, a no-op cache, and rejection of repeated `(revision, operation, parameters)` combinations.

### 11. Corrupted RC low-pass — genuine successful repair
- [Before (000)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/rc_corrupted/candidates/000/review-images/drawing.png)
- [After regeneration (001)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/rc_corrupted/candidates/001/review-images/drawing.png)
- Before: J1 input is visibly disconnected from R1. After `regenerate_schematic`, J1 connects to R1; output J2 follows R1/C1 node; return J3 ties to C1 lower terminal. Saved KiCad netlist, ERC and equivalence pass.
- Fix/retain: keep as positive **functional repair** fixture. Distinguish `REGENERATE_FROM_SPEC` from `LOCAL_EDIT`, and record whether the repair was made by the LLM versus deterministic regeneration.

### 12. RC field-association qualification — narrow success
- [Before (000)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/review_with_owner_gate_v2_recovered/candidates/000/review-images/drawing.png)
- [After (002)](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/review_with_owner_gate_v2_recovered/candidates/002/review-images/drawing.png)
- Model moves C1 value `15n` nearer its capacitor and receives acceptance; useful narrow field placement test. Retain explicit text distance, symbol ownership and spacing checks; do not interpret this as general circuit layout improvement.

## Major process recommendations, prioritized

### P0 — correctness / safety

**P0.1 Transactional, electrically invariant editing.** Each proposed change should execute in scratch state: source SHA/revision verification → apply → KiCad ERC and native netlist export → compare exact `(refdes,pin)` net partitions against intended design and baseline → graphical collision/clearance check → commit as active candidate **only if hard checks pass**. Reject and rollback otherwise. Keep invalid outputs in a quarantine/evidence directory. An edit that moves only text or symbols must not be permitted to change connectivity. Include the noninverting-gain 003→004 regression.

**P0.2 Separate schematic objective from visual representation.** Compare the native KiCad netlist, not merely model-provided labels or raster visual interpretation. Treat physical named labels and KiCad power symbols as legitimate electrical joins. Do not require globally continuous *visible* wires for every asserted supply net.

**P0.3 Preserve independent acceptance gates.** Expose separate statuses for: `NATIVE_VALID`, `ELECTRICALLY_EQUIVALENT`, `PRESENTATION_PASS`, `DESIGN_REQUIREMENTS_CHECKED`, `PCB_READY`, `HUMAN_REVIEWED`. `ACCEPTED_FOR_REVIEW` must not imply physical engineering approval. Record check suppressions/ignored ERC categories.

### P1 — reviewer/editor reliability

**P1.1 Supply structured feasible actions.** The editor should first compute nearby legal candidate placements/connection paths, endpoint IDs, valid net IDs, minimum clearances and explicit reasons a proposal cannot work. Qwen then selects among those candidates instead of inventing mm coordinates or moving whole multipart symbols blindly. Use canonical `(reference, unit)` IDs for multipart symbols; don't accept a malformed `references=['U1','unit','3']` list.

**P1.2 Replace wire-first rail continuity with net-symbol normalization.** Add operations such as `normalize_power_nets`, `place_local_power_symbol`, `compact_power_entry`, `place_decoupling_pair`, `reflow_functional_block`, `autoroute_region`, `relocate_field_safely`. Prefer local symbols unless there is a concise local bus that genuinely improves understanding. Power flags are electrical assertions used for ERC, not substitutes for visible net labels.

**P1.3 Add progress and repetition control.** Hash `(revision, failed_operation, parameters, diagnostic)` and refuse exact repeats. A failed path must produce a structured obstacle witness and suggestions: alternate symbols, small local shifts, block reflow, or a bounded fallback. Count repeated invalid calls separately from useful revisions. Do not accept a request that leaves drawing unchanged unless it is an explicit `accept` action.

**P1.4 Optimize a quality delta, not just passing checks.** Keep hard gates for ERC/netlist and collisions. For valid candidates, compare baseline and revised: total wire length, total *detour* length, bend count, long perimeter wire count, visible symbol-to-symbol congestion, component group locality, text-owner separation, page balance and readability. Penalize adding 61% wiring to fix a rail style check unless a human-calibrated quality score improves. Record before/after metrics in every result.

**P1.5 Decompose review into passes.** Run one issue class at a time: electrical safety, rail/power representation, functional-block alignment, label placements, final page presentation. Have each pass return structured evidence and one supported change. Qwen3.5 9B is better used to select and rank *high-level edits* than to guess precise KiCad routes and coordinates. Consider forcing a deterministic rerender/validation pass before each follow-up review; bind responses to exact revision hash.

### P2 — quality and generalization

**P2.1 Functional topology-aware layout.** Define reusable motifs for 555 astable, op-amp buffer/inverting/non-inverting, active filter, regulator, divider/reference, power-entry, decoupling. These motifs should be generalized graph constraints rather than one-off XY coordinates for NE5532 or L7805. Maintain input→processing→output left-to-right, local feedback loops, local returns and decoupling groupings.

**P2.2 Separate analog engineering from drafting.** Add application requirements (supply voltage, common-mode range, expected load, waveform amplitude, noise/offset limits, temperature) and a separate design-review pass. Electrical equivalence only confirms the generated drawing matches the *specified graph*, which itself may be inappropriate. For 555 check supply bypass and RESET; for L7805 check dropout/thermal/capacitor guidance; for op-amps check operating rails and input bias; for a divider-based VREF check allowable loading and buffering requirements. No automatic topology modification during a visual-only edit.

**P2.3 Human-calibrated holdout benchmark.** Make a stable set with distinct topology families and multiple variants, not only repeated runs of 555/op-amp. Human reviewers blind-rate baseline and revised schematic for 1) electrical correctness, 2) node traceability, 3) power-section clarity, 4) text association, 5) natural functional-block arrangement, 6) overall preference. Report per-circuit and aggregate edit **quality win rate** plus connectivity regression rate, not just review-loop acceptance rate.

**P2.4 Versioned, reproducible reports.** Report commit SHA, source PNG SHA, model ID/digest/context size, tool/edit version, candidate IDs and diffs, detailed netlist before/after, ERC check suppressions, reason for each edit, validator outputs and elapsed time. The historical summary mixes experiments and aliases; report independent circuit families separately and control for deterministic regenerate-only baselines.

## Suggested acceptance criteria

- **Safety:** Zero accepted connectivity regressions. A proposed `move_symbols`, `move_field`, or `use_power_symbols` change that merges any previously distinct nets must be rejected and rolled back.
- **Correctness:** No accepted KiCad ERC errors (with any ignored categories explicitly disclosed). Verified matching pin-partition graph for every candidate proposed as valid.
- **Presentation:** No visible text/symbol/pin-number overlaps; explicit junction conventions; adequate label ownership; no long perimeter wire introduced solely to satisfy false rail-continuity assumptions.
- **Quality:** Accepted improvements must show positive human preference on holdout circuits; if a narrow issue is resolved but global aesthetics regress, report `LOCAL_FIX_ONLY` or reject as overall optimization.
- **Loop progress:** No repeat of an identical rejected/no-op action for the same revision. On infeasible routes offer a different *feasible* operation; return a structured blocker when none exists.
- **Traceability:** Every accepted edited candidate includes a before/after diff, separate check statuses, and unresolved engineering-design caveats.

## Proposed next engineering sprint for Claude

1. Reproduce `noninverting_gain` candidate 003→004 and harden `move_symbols` into a transactional operation. Put an automated regression in CI.
2. Replace the rail-continuity check's implicit preference for a single drawn wire trunk with equivalent local power-symbol validation. Test 555 flasher, dual buffer, and RC-to-buffer cases without increased perimeter wiring.
3. Fix field placement and no-op repeat handling using LED reverse-supply `J1` as a unit test.
4. Introduce before/after quality-delta reporting; distinguish functional repair (`rc_corrupted`) from label fix (`inverting_gain`) from layout optimization (all rails). Keep explicit `human_electrical_review: PENDING` until actually reviewed.
5. Run a blinded mini-benchmark of these distinct circuits under `qwen3.5:9b` at fixed digest/temperature/context and compare quality wins to deterministic editor-only baselines.

**Bottom line:** A small vision-capable LLM can usefully direct schematic repairs. The major opportunity is **not** a larger model or more free-form review prompts; it is safer edit transactions, clearer high-level operations, a better quality objective, and evaluation against actual engineering readability rather than only tool-check PASS counts.
