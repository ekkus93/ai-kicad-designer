# M2h2 Human-Readable Schematic Composition TODO — 2026-10-07

**Status:** IN PROGRESS / INCOMPLETE

Canonical executable checklist for the post-M2h2 human-readable schematic composition remediation.

Source-level reconciliation checkpoint: current implementation/observer/oracle evidence has been reconciled through the source state immediately preceding this TODO update. Fresh locked-KiCad qualification, native-render inspection, comparative closure, and final PASS remain open and authoritative.

Governing documents:

- `docs/M2_GENERALIZATION_REMEDIATION_SPEC.md`
- `docs/M2H2_FINALIZATION_SPEC_2026-09-27.md`
- `docs/M2H2_HUMAN_READABLE_SCHEMATIC_COMPOSITION_SPEC_2026-10-07.md`
- `fixtures/m2h2/STATUS.md`

Historical M2h2 PASS remains valid as the completed electrical/correctness baseline. This checklist adds a stricter human-readable composition gate; it must not rewrite or weaken historical PASS evidence.

A checkbox may be checked only from current-source evidence. “Implemented,” parse/generation success, a lower aggregate aesthetic score, one attractive screenshot, internal generator metrics, or stale pre-change renders are not sufficient evidence.

## 0. Scope, authority, and preservation

- [x] Confirm this is additive M2h2 composition hardening, not M3.
- [x] Confirm no corpus.v7 work.
- [x] Confirm no CP-SAT.
- [x] Confirm unchanged 210 × 140 mm spread gate.
- [x] Confirm unchanged 80 mm local-path gate.
- [x] Confirm unchanged 60 mm support/locality gate where applicable.
- [x] Confirm unchanged 250 mm canonical conductor-length gate.
- [x] Confirm ERC and independent emitted-artifact observation remain authoritative.
- [x] Confirm DP1–DP4 topology/frozen expectations remain unchanged (all eight authored input/expectation Git blobs match historical production source `79a36b17`; see `fixtures/m2h2/human_composition_baseline_2026-10-08/dp_frozen_inputs_audit_2026-10-08.json`).
- [x] Confirm all historical blind/evaluation and M2h2 finalization evidence is preserved.
  - Exact-head preservation audit: `docs/M2H2_COMPOSITION_PRESERVATION_AUDIT_2026-10-08.md`. Historical evidence unchanged since frozen baseline `4d892285` (complete 107-path Ralph Bridge comparison, zero protected evidence changes); no current-source qualification credit is implied.
- [x] Confirm `.local/` remains ignored.
- [x] Confirm `research/legacy_openclaw/` is not inspected or used.
- [x] Confirm locked KiCad 10.0.6 remains the governed real-tool version.
- [x] Confirm all GitHub/repository/CI reads and writes use Ralph Bridge.
- [x] Confirm direct-`master` exact-head compare-and-swap workflow.

## 1. Baseline freeze and composition characterization

- [x] Record current `master` SHA and hashes of behavior-affecting M2 placement/routing/composition modules.
  - Baseline snapshot `c57f91d8253933abf319e4c116e176bdc334ac81` with 50 distinct M2 Python source Git blob SHA-1 identities in `fixtures/m2h2/human_composition_baseline_2026-10-08/m2_source_git_blob_checkpoint_2026-10-08.json`. This is a prequalification baseline for the listed M2 modules, NOT a final source freeze; final SHA-256 source hash closure remains unchecked in section 16.
- [x] Record historical M2h2 final PASS authority without modifying it.
- [x] Preserve/hash the final native-render archive used as the composition baseline.
  - `fixtures/m2h2/human_composition_baseline_2026-10-08/native_render_archive_manifest_42ab8452.json` records the preserved ten-part archive and its individual part SHA-256 and Git blob SHA-1 digests; the immutable archive contains 90 SVGs with independently verified SHA-256s and a sorted case inventory digest `759f49bf715da357d70f4fb4ae5513594328acb3ba8612031866ac6788a21fe0`. All ten archived files are present on current `master`. This preserves historical baseline evidence only, not current-source native render acceptance.
- [x] Add a new human-composition baseline evidence root.
- [x] Define a versioned composition metric schema before behavior changes.
- [x] Evaluate current final M2h2 renders using the initial independent observer.
- [x] Produce a ranked per-case defect inventory.
  - Exact-head baseline characterization evidence: `tools/analyze_m2h2_historical_composition.py` hash-verifies all 90 preserved final M2h2 native SVGs, reconstructs authored semantics independently of production scores, emits per-case interface/page/routing witnesses plus a deterministic defect-oriented `ranked_case_ids` inventory, and explicitly claims no current-source qualification. `tests/test_m2h2_historical_composition_analysis.py::test_full_historical_report_is_complete_ranked_and_archetype_covered` requires all 90 cases, unique one-to-one ranking, and zero missing/ambiguous semantic occurrences. Exact source `97542c4cd1ca1a6e46afb050cf6bac5a23540c0b`: Fast Validation run `38012665368`, locked-runner full pytest step PASS; all governed regression/build steps 7-10 also PASS. The workflow conclusion is failure solely because artifact upload hit storage quota; hosted jobs failed before exposing steps/logs. Historical SVG geometry-only screening remains supplementary evidence, not final qualification.
- [x] Record `i4__b2_mixed` as a falsification seed.
  - [x] output interfaces on visually inappropriate frontier are detected;
  - [x] detached interface-to-owning-stage relationships are detected;
  - [x] weak page utilization/edge bias is detected;
  - [x] awkward branch/detour geometry is measured;
  - [x] local label-mediated visual disconnection is measured where applicable.
    - The generic falsification-seed test on exact source `97542c4cd1ca1a6e46afb050cf6bac5a23540c0b` requires both `OUTPUT_1`/`OUTPUT_2` right-frontier violations, >60 mm owner detachments, edge bias, at least one U-shaped detour, nonzero sibling-branch geometry inconsistency, and an `INPUT` local label-mediated disconnect; locked-runner pytest PASS in run `38012665368`.
- [x] Identify at least one baseline example for each applicable archetype:
  - [x] linear chain;
  - [x] branch/fanout;
  - [x] feedback;
  - [x] repeated channels;
  - [x] shared rail;
  - [x] internal reference;
  - [x] multi-output;
  - [x] long-field text;
  - [x] structural multi-band/one-band;
  - [x] mixed interaction.
  - `build_report()["archetype_examples"]` records exact case IDs from generic semantic/native geometry features. The exact-head corpus test requires keys for linear, branch/fanout, feedback, repeated channels, shared rail, internal reference, multi-output, long-field text, structural multi-band, structural one-band, and mixed interaction, and requires every selected example to be a member of the hash-verified 90-case ranked inventory. Locked-runner pytest PASS: `97542c4cd1ca1a6e46afb050cf6bac5a23540c0b`, run `38012665368`.
- [x] Confirm baseline failures do not alter historical M2h2 PASS status.

## 2. Independent semantic-flow observer

- [x] Implement independently authored semantic-flow graph reconstruction.
- [x] Distinguish signal, support, power, reference, return, and interface roles.
- [x] Derive directed primary-flow precedence independently of generator placement state.
- [x] Preserve sibling incomparability where topology does not order siblings.
- [x] Handle feedback cycles without incorrectly ordering feedback as forward flow.
- [x] Handle external terminal-backed signal sources.
- [x] Handle multiple final outputs.
- [x] Emit exact witnesses for stage-order violations.
- [x] Emit cumulative primary-flow reversal distance.
- [x] Add authored positive controls.
- [x] Add authored negative controls.
- [x] Add split/unsplit conductor metamorphic tests.
- [x] Add refdes/net rename metamorphic tests.
- [x] Add insertion/set-order metamorphic tests.

## 3. Functional-block and visual-ownership observer

- [x] Independently derive functional blocks from semantics/connectivity.
- [x] Derive visual ownership for feedback/support/package-local structures.
- [x] Derive shared ownership for supply/reference infrastructure.
- [x] Report functional-block dispersion.
- [x] Report functional-block fragmentation.
- [x] Report support-to-owner distance.
- [x] Report interface-to-owning-stage distance.
- [x] Report feedback-loop span and unrelated-block intrusion.
- [x] Add negative mutation: isolate one support component.
- [x] Add negative mutation: move feedback network away from owner.
- [x] Add negative mutation: detach output interface from final producer.
- [x] Verify observer does not consume production layout scores as proof.

## 4. Interface-side and signal-flow composition

- [x] Add generic semantic frontier model for external interfaces.
- [x] Prefer directed inputs on left frontier.
- [x] Prefer directed outputs on right frontier.
- [x] Place power-input interfaces with supply infrastructure rather than primary signal flow.
- [x] Exempt genuinely bidirectional/undirected interfaces using semantic evidence, not names.
- [x] Add deterministic penalties for unjustified interface-side violations.
- [x] Add deterministic penalties for primary stage-order inversions.
- [x] Add deterministic penalties for primary-flow backtracking distance.
- [x] Preserve valid incomparable sibling ordering freedom.
- [x] Add targeted regression for `i4__b2_mixed`.
  - Exact-head source `fec1a3f0c6ac54d7ce278c7b64a23f964abce8d4`: `tools/run_m2h2_current_regressions.py` includes the original mixed-branch design, with a lock/version check, independent electrical/ERC and serialized-scene verification, and independent human-composition observation. `tests/test_m2h2_current_regressions.py` prevents accidental loss of coverage. Locked KiCad 10.0.6 one-build case accepted (fast-validation run `37970772914`; `655 passed` in full pytest; all three CI jobs PASS). This checks inclusion and the single-run source regression only, **not** section 15's native-render aesthetic acceptance or section 17's five-run final qualification.
- [x] Add a renamed/permuted equivalent of the same semantic archetype to prove generic behavior.
- [x] Add negative mutation: final output connector moved to input frontier.
- [x] Verify no case/fixture/refdes/literal-net dispatch is introduced.

## 5. Functional grouping and locality composition

- [x] Add generic intra-block cohesion objective.
- [x] Add generic inter-block separation objective.
- [x] Keep local feedback structures with their owner.
- [x] Keep package-local support with its owner where hard constraints permit.
- [x] Preserve shared infrastructure as explicitly shared rather than arbitrarily attaching it to one block.
- [x] Prefer natural electrical ordering of passive series chains.
- [x] Prevent isolated stage members connected only through distant labels when a legal local arrangement exists.
  - Current-source exact-head evidence: `src/ai_kicad/m2_pack.py::_local_signal_proximity_candidates` searches direction-preserving adjacent vertical corridors when the aligned local slot is obstructed, while retaining measured hard-placement gates and bounded deterministic search. `tests/test_m2_composition_signal_locality.py` covers blocked-corridor recovery and semantic-order invariance. On exact source `fca44525387837ef869a891d9b0fcbab68e52518`, Fast Validation run `38005894006` completed full pytest plus locked-KiCad 10.0.6 V6-3/DP2, connector-label/selected-triple five-run, whole-band five-run, and fresh regression-build steps successfully; the workflow failure is solely the later artifact-upload quota failure and does not invalidate those completed steps. Native-render/final qualification remains open.
- [x] Record exact grouping penalties in candidate evidence.
- [x] Preserve existing 60 mm support/locality hard requirements.
- [x] Add small synthetic exhaustive grouping cases.
- [x] Add dominated-candidate oracle checks.

## 6. Branch, fanout, and feedback readability

- [x] Model branch points explicitly in composition evidence.
- [x] Prefer visually identifiable branch origins.
  - Production `m2_composition_candidate_rank._branch_readability_penalty` now groups ordinary signal and explicit branch fanout by semantic source/net, deduplicates targets, and penalizes off-center origins, uneven sibling depth, and backwards branches. Authored controls in `tests/test_m2_composition_candidate_rank.py` cover centered vs detached origins, signal-edge equivalence, renames/permutations, and unrelated-net exclusions; hosted contract and static checks passed for source `74f5d59b4f62b1e55dd46e078431e07dd02ee419`. Native render acceptance remains separately unchecked.
- [x] Prefer consistent sibling-branch geometry.
- [ ] Penalize unnecessary branch crossings/detours.
  - Source-level partial implementation: generic fanout candidate ranking penalizes unrelated obstacles intersecting both shortest Manhattan elbows, deduplicates mixed signal/branch edges, and excludes owned support/package members. Four authored tests PASS with hosted static and contract checks at `dec2b79937deedaa7c4587227c78e5698a3f2798`, run `37907563890`. This is a placement/corridor proxy, **not** emitted-wire crossing or detour evidence; retain unchecked pending current-source locked-KiCad routing observation.
- [x] Keep branch outputs attributable to source.
- [x] Model forward-path versus feedback-path roles.
- [x] Prefer compact feedback loops around owning stage.
- [ ] Penalize feedback routes through unrelated functional blocks.
  - Source-level partial implementation at `19303f27a71861fd4b3070a88268b38c862d4f50`: conservative two-shortest-elbow placement proxy in `m2_composition_candidate_rank._feedback_corridor_intrusions`, with seven authored tests, including reversed direction and protected support relatives. This **does not** measure actual emitted routing; leave unchecked until current-source native route evidence supports it.
- [x] Add branch/fanout positive and negative oracle cases.
- [x] Add feedback positive and negative oracle cases.
- [x] Add passive two-level fanout regression.
- [x] Add amplifier/filter feedback regression.

## 7. Power and reference composition

- [x] Add shared-rail/reference visual-coherence metrics.
- [x] Report supply/reference infrastructure dispersion.
- [x] Keep internal reference producer/support visually coherent.
- [x] Keep package-local decoupling/support local where semantics permit.
- [x] Prevent supply/reference infrastructure from dominating primary signal rows.
- [x] Preserve no-fake-external-reference behavior.
- [x] Add two-signal-chains/shared-rail regression.
- [x] Add V6-3 internal-reference regression.
- [x] Add multi-consumer supply/reference regression.
- [x] Add dual-regulator/mixed-load regression.
- [x] Verify all existing canonical graph and conductor-length gates remain unchanged.

## 8. Repeated-structure composition

- [x] Detect repeated semantic channels/stages generically.
- [x] Report row alignment variance.
- [x] Report column alignment variance.
- [x] Report corresponding-symbol displacement variance.
- [x] Report orientation variance.
- [x] Report pitch variance.
- [x] Prefer a consistent repeated-channel visual grammar.
- [x] Keep equivalent channel order deterministic.
- [x] Add declaration-order permutation tests.
- [x] Add mirrored naming/refdes metamorphic tests.
- [x] Add three-amplifier one-band regression.
- [x] Add multi-band/repeated-channel regression.
- [ ] Freeze repeated-structure acceptance tolerances from general corpus evidence.

## 9. Page utilization and whitespace

- [x] Report content bounding-box width.
- [x] Report content bounding-box height.
- [x] Report content bounding-box area.
- [x] Report occupied-area ratio against 210 × 140 mm composition envelope.
- [x] Report content-centroid offset / edge bias.
- [x] Report horizontal whitespace imbalance.
- [x] Report vertical whitespace imbalance.
- [x] Report largest accidental internal empty corridor/void.
- [x] Define semantic complexity bands using block count, visible symbol count, and semantic edge count.
- [x] Exempt genuinely tiny probes from minimum utilization while still checking needless dispersion.
- [x] Freeze small/medium/dense complexity-aware utilization tolerances before final qualification.
- [x] Add negative mutation: shift a non-tiny circuit into a tiny upper-left patch.
- [x] Add negative mutation: introduce a large avoidable internal void.
- [x] Verify compactness pressure never violates hard spread/locality/readability gates.

## 10. Alignment, grid, and field composition

- [x] Add meaningful alignment-line detection.
- [x] Prefer common baseline/centerline for sequential active stages where practical.
- [x] Prefer role-consistent passive alignment.
  - Source-level semantic terminal-role alignment for local reference/shunt legs is implemented in `m2_composition_candidate_rank._passive_reference_axis_alignment_penalty`, including explicit exemptions for ambiguous/shared ownership. Three authored controls verify axis preference, refdes/port-order invariance, and shared-leg exclusions. Exact source `f1e9392efec0569c05e5a89f1446fa82bbc25f19`, hosted contract and complete static PASS in run `37908086300`. Native-render acceptance remains unchecked.
- [x] Align connectors with the signal rows they serve where practical.
- [x] Align local support structures rather than leaving arbitrary offsets.
  - Source-level alignment checkpoint: generic sequential signal and directed connector-row penalties in `src/ai_kicad/m2_composition_candidate_rank.py` and explicit support/package ownership axis penalty were exercised by authored positive, negative, fanout, feedback, and ordering controls in `tests/test_m2_composition_candidate_rank.py`. Hosted contract tests and complete static checks PASS on exact source `de219e0129d7814326517de1f71cb49c73ab0da5`, run `37906474016`. This supports the three checked source preferences only; locked KiCad 10.0.6, native route/render evidence, and final composition acceptance remain unchecked.
- [x] Preserve KiCad-compatible grid placement.
- [x] Make reference/value orientation consistent for comparable roles.
  - Generic symbol-relative reference/value field-slot consistency is now a late aesthetic tie-breaker in `m2_composition_candidate_rank._field_slot_consistency_penalty`. It compares matching functional kinds, terminal-role footprints and symbol rotations; exempts interfaces, different orientations, and missing text geometry; and never outranks routing or whitespace. Four authored controls cover preference, routing priority, renaming/declaration order, role/rotation exclusions and missing fields. Source `4a4c2d4742ddaa2ffa100caf87b5ef25f593281b`; hosted contract/static PASS in run `37909980631`. This source-level preference is not native-render field acceptance.
- [x] Preserve long-field alternate-slot behavior.
- [x] Preserve existing field/body/wire/label independent checks.
- [x] Add field-alignment metrics.
- [x] Add long-field regression cases.
- [x] Add negative mutation: repeated component with inconsistent field orientation.

## 11. Routing clarity and label discipline

- [x] Report route bend count.
- [x] Define normalized bend excess against a legal semantic-local baseline.
- [x] Report canonical routed length.
- [x] Define normalized routed-length excess against a legal semantic-local baseline.
- [x] Report unrelated wire crossings.
  - Independent observer refinement: count unique orthogonal intersection coordinates, invariant to wire serialization splits, reversals, and duplicates; preserve endpoint-on-interior unrelated-net conflict witnesses. Authored controls cover a split at the intersection and overlapping strokes. This is observer correctness, not a current-source native-render PASS.
- [x] Detect unnecessary U-shaped/rectangular detours.
- [x] Detect route excursions through unrelated blocks.
- [x] Report sibling-branch geometry inconsistency.
- [x] Detect label-mediated local disconnects.
- [x] Prefer direct visible local connectivity when legal and clearer.
- [x] Prefer labels for genuinely global/shared distribution when clearer.
  - Current-source routing evidence: `m2_route._optional_local_visible_edges` admits only unique two-fragment local signal-interface relations within the existing 80 mm locality bound and `route_between_fragments` adds a best-effort obstacle-checked conductor while preserving the 250 mm canonical-length gate. Distant, distributive/shared, ambiguous, power/reference, blocked, and over-length cases remain label/distribution governed. `tests/test_m2_terminal_interface_flow.py` covers both local visible routing and distant/distributive label retention. Exact source `97542c4cd1ca1a6e46afb050cf6bac5a23540c0b`, locked-runner full pytest PASS in run `38012665368`; final native-render acceptance remains open.
- [x] Ensure label discipline never creates electrical ambiguity.
- [x] Add direct-vs-label synthetic oracle cases.
- [x] Add detour negative mutations.
- [x] Freeze routing-aesthetic tolerances before final qualification.

## 12. Production search/objective integration

- [x] Encode the lexicographic objective hierarchy:
  - [x] electrical correctness;
  - [x] existing hard M2h2 invariants;
  - [x] semantic readability;
  - [x] routing clarity;
  - [x] compactness/whitespace;
  - [x] aesthetic tie-breakers.
- [x] Ensure no weighted aggregate can trade away a higher-priority invariant.
- [x] Add candidate metrics for interface placement.
- [x] Add candidate metrics for stage ordering.
- [x] Add candidate metrics for grouping.
- [x] Add candidate metrics for repeated structures.
- [x] Add candidate metrics for whitespace/utilization.
- [x] Add candidate metrics for routing clarity.
- [x] Search meaningful interface-frontier alternatives.
- [x] Search meaningful semantic block-order alternatives.
- [x] Search meaningful repeated-channel row/column alternatives.
  - Current-source 28428470c8d4bd4672e8fe94fe24ac6577be8bbe: generic bounded row and column generation plus explicit final eight-seed retention and deduplication, with regression coverage; hosted static and contract PASS in run 37835474849. This establishes source implementation only; native KiCad qualification and render acceptance remain open.
- [x] Search meaningful support-placement alternatives.
- [x] Search meaningful field-slot alternatives.
  - Current-source `eff40b3e4f6d4bf0e34e28cbf106ab65095a8550`: independent measured text-slot variants, bounded field-kind variant proposals, explicit final eight-seed retention, and dedicated generic regressions. Hosted static/contract validation PASS in run `37840687842`; native KiCad qualification remains open because the self-hosted runner lacks pinned `/tmp/AppDir` files.
- [x] Search meaningful branch/route alternatives where already bounded.
  - Bounded `m2_pack._branch_fanout_repack_candidates` searches a source-centered fanout and sibling-depth alignment, checks all candidates through `_measured_repack` hard placement/terminal constraints, and protects both legal variants from the final eight-seed retention cap. Five authored controls cover centering, sibling-depth correction, net rename/declaration permutation, retention, and unrelated-net exemption; these are included in hosted contract CI. Source `d4752e40855d64e15fcc0f383b480b4375d5f20c`; hosted contract/static PASS in run `37911027488`. Actual emitted-wire route clarity and native KiCad qualification remain unchecked in sections 6, 11, 15–21.
- [x] Preserve exact attempt/budget counters.
- [x] Deduplicate repeated states.
- [x] Preserve best rejected candidate and full metric vector.
- [x] Make all tie-breakers deterministic.
- [x] Keep search bounded; no unbounded combinatorial expansion.

## 13. Tiny exhaustive placement and graph oracles

- [x] Implement independent tiny-grid exhaustive placement oracle.
- [x] Cover connector-side semantics.
- [x] Cover linear stage order.
- [x] Cover incomparable siblings.
- [x] Cover grouping.
- [x] Cover repeated alignment.
- [x] Cover whitespace/compactness.
- [x] Cover branch geometry where tractable.
- [x] Compare production result against non-dominated legal oracle candidates.
- [x] Require evidence when bounded production search legitimately misses oracle optimum.
  - `m2_tiny_grid_composition_oracle.verify_tiny_search_budget_witness` and `m2_tiny_grid_oracle_miss_evidence.require_bounded_search_miss_evidence` reject an unexplained dominated candidate, disclose candidate/attempt budgets and unvisited optimum witnesses, and reject hidden better attempted candidates. Authored positive/negative/boundary controls in `test_m2_tiny_grid_composition_oracle.py` and `test_m2_tiny_grid_oracle_miss_evidence.py` passed (34 tests in local source-level validation on 2026-10-08). This source-level reconciliation does not imply locked KiCad qualification.
- [x] Implement independent graph-order oracle.
- [x] Falsify signal vs power/reference precedence separation.
- [x] Add exact-boundary tests for each frozen composition tolerance.
- [x] Add off-by-one-grid tests around each boundary.

## 14. Anti-overfitting and metamorphic audits

- [x] Extend literal anti-overfitting audit for composition production modules.
- [x] Extend structural anti-overfitting audit for composition production modules.
- [x] Reject fixture/case-ID control flow.
- [x] Reject qualification-group control flow.
- [x] Reject literal benchmark net-name control flow.
- [x] Reject refdes-specific control flow.
- [x] Reject exact-inventory special cases.
- [x] Reject topology-hash special cases.
- [x] Reject per-case coordinate maps.
- [x] Reject precomputed target-image dimensions/coordinates.
- [x] Scan data tables as well as obvious conditional branches.
- [x] Pass refdes-renaming metamorphics.
- [x] Pass net-renaming metamorphics.
- [x] Pass insertion-order metamorphics.
- [x] Pass equivalent-wire-segmentation metamorphics.
- [x] Pass repeated-channel declaration-order metamorphics.

Source-level checkpoint: `cdcfd445be09712f8a12d30068d3a23509cb7684`, fast-validation run `37829859944` (hosted contract pytest and static checks PASS; locked KiCad job queued). New functionality and authored regressions support the checked implementation items; no native-render or final-source PASS is claimed.

## 15. Targeted composition regression suite

- [ ] `i4__b2_mixed` reads left-to-right with output interfaces associated with final outputs.
- [ ] `i4__b2_mixed` no longer exhibits pathological upper-left page packing for its complexity.
- [ ] `i4__b2_mixed` branch geometry has no avoidable dominant empty rectangle/detour.
- [ ] two-signal-chains/shared-rail remains electrically correct and becomes visually coherent.
- [ ] V6-3 remains electrically correct and its internal reference/support reads coherently.
- [ ] three-amplifier one-band remains electrically correct and repeated stages align consistently.
- [ ] passive two-level fanout remains traceable.
- [ ] amplifier-to-filter chain has obvious forward flow.
- [ ] feedback cases show local recognizable feedback.
- [ ] multi-output cases place final interfaces near final producers.
- [ ] long-field cases retain readability without unnecessary dispersion.
- [ ] timer/control cases retain readable control/feedback structure.
- [ ] package-shared cases retain package/support association.
- [ ] mixed interaction cases do not collapse into label-only disconnected visual islands.
- [ ] all targeted regressions pass native KiCad 10.0.6 generation/inspection.

## 16. Source stabilization

- [ ] Finish all behavior-affecting composition implementation changes.
- [ ] Run complete pytest.
- [ ] Run scoped Ruff lint.
- [ ] Run scoped Ruff format check.
- [ ] Run `git diff --check`.
- [ ] Run scoped whitespace checks.
- [ ] Run applicable link checks.
- [ ] Run historical preservation audit.
- [ ] Run literal anti-overfitting audit.
- [ ] Run structural anti-overfitting audit.
- [ ] Confirm CP-SAT remains absent.
- [ ] Run current-source V6-3 real-tool regression.
- [ ] Run current-source DP2 real-tool regression.
- [ ] Record final behavior-affecting source hashes.
- [ ] Freeze composition observer/oracle schema and hashes.
- [ ] Create fresh final human-composition qualification root.
- [ ] Declare later behavior-affecting source changes qualification-invalidating.

## 17. Fresh locked-KiCad qualification

- [ ] Run all 56 positive M2h2 base cases ×5 from stabilized final source.
- [ ] Require locked KiCad 10.0.6 for all governed runs.
- [ ] Require exact package/unit/pin identity.
- [ ] Require independent electrical partitions.
- [ ] Require zero unexpected ERC violations.
- [ ] Require serialized-scene verification.
- [ ] Require existing spread/locality/conductor-length gates.
- [ ] Require independent composition-observer pass.
- [ ] Require frozen composition metrics/tolerances.
- [ ] Require deterministic composition class across runs.
- [ ] Require deterministic metric vector after documented normalization.
- [ ] Confirm historical V3-8 remains rejected.
- [ ] Run all required I1–I6 interaction cases ×5.
- [ ] Run all required structural classes ×5.
- [ ] Run targeted composition regressions ×5 where reproducibility applies.
- [ ] Preserve all failures and best-candidate witnesses; do not overwrite evidence.

## 18. Native-render engineering inspection

- [ ] Generate final native KiCad renders from stabilized source.
- [ ] Archive hashes for every inspected render.
- [ ] Inspect at least one representative render for every distinct governed case.
- [ ] Explicitly inspect all mixed/high-density cases.
- [ ] Explicitly inspect all repeated-channel cases.
- [ ] Explicitly inspect all branch/fanout cases.
- [ ] Explicitly inspect all feedback cases.
- [ ] Explicitly inspect all shared-rail/reference cases.
- [ ] Explicitly inspect all long-field cases.
- [ ] Explicitly inspect all structural band-class cases.
- [ ] For every applicable inspected case, record:
  - [ ] primary signal entry is obvious;
  - [ ] primary signal progression is obvious;
  - [ ] final outputs are associated with final producers;
  - [ ] branch/fanout source attribution is obvious;
  - [ ] feedback is recognizable;
  - [ ] power/reference infrastructure is coherent/subordinate;
  - [ ] support ownership is obvious;
  - [ ] repeated structures are consistent;
  - [ ] compactness is appropriate;
  - [ ] whitespace is intentional;
  - [ ] fields/labels are aligned/readable;
  - [ ] no obvious unmodelled computer-generated layout defect remains.
- [ ] Record inspection as engineering/agent inspection, not user approval.
- [ ] Any hard visual defect falsifies the candidate and reopens affected qualification.

## 19. Comparative baseline closure

- [ ] Re-run composition observer over the original baseline corpus.
- [ ] Produce before/after per-case metric comparison.
- [ ] Show every baseline hard composition defect fixed or evidence-backed as unavoidable.
- [ ] Show `i4__b2_mixed` specifically improved without case-specific code.
- [ ] Show no material regression on previously strong cases.
- [ ] Show corpus-wide stage-order metrics improve or remain zero.
- [ ] Show corpus-wide interface-side metrics improve.
- [ ] Show functional-block fragmentation improves.
- [ ] Show page-utilization/edge-bias metrics improve for applicable complexity bands.
- [ ] Show routing-aesthetic metrics improve without violating hard routing gates.
- [ ] Show repeated-structure alignment improves or remains within frozen tolerance.
- [ ] Confirm aggregate metrics are not used to hide individual hard defects.

## 20. Final reproducibility and audit closure

- [ ] Verify five-run deterministic project bytes where already governed.
- [ ] Verify deterministic semantic composition class.
- [ ] Verify deterministic normalized native-render geometry.
- [ ] Verify deterministic observer metric vectors.
- [ ] Verify deterministic candidate/tie-break decisions.
- [ ] Run complete final pytest.
- [ ] Run final Ruff lint.
- [ ] Run final Ruff format check.
- [ ] Run final `git diff --check`.
- [ ] Run final whitespace checks.
- [ ] Run final link checks as applicable.
- [ ] Run final historical-preservation audit.
- [ ] Run final literal anti-overfitting audit.
- [ ] Run final structural anti-overfitting audit.
- [ ] Confirm CP-SAT absent.
- [ ] Reconfirm unchanged 210 × 140 / 80 / 60 / 250 mm hard gates.
- [ ] Reconfirm ERC/independent observer not weakened.
- [ ] Reconfirm DP1–DP4 and historical evidence unchanged.

## 21. Final reconciliation and PASS

- [ ] Create final closure record binding exact production source, qualification source, observer/oracle hashes, toolchain, and evidence roots.
- [ ] Record final base-case count and five-run outcomes.
- [ ] Record final interaction-case count and five-run outcomes.
- [ ] Record final structural-class count and five-run outcomes.
- [ ] Record final targeted-composition regression outcomes.
- [ ] Record worst composition metrics and exact witnesses.
- [ ] Record before/after baseline comparison.
- [ ] Record native-render inspection totals.
- [ ] Update `fixtures/m2h2/STATUS.md` only when final material status changes.
- [ ] Reconcile every checkbox in this TODO from exact current-source evidence.
- [ ] Confirm no unchecked item remains.
- [ ] Mark this TODO **COMPLETE / PASS**.
- [ ] Stop; do not create corpus.v7 and do not begin M3.

## Completion rule

Do not finish merely because placement “looks better,” a handful of screenshots look good, aggregate metrics improve, or the targeted `i4__b2_mixed` regression is repaired.

Completion requires:

- all existing M2h2 correctness guarantees preserved;
- generic semantic composition behavior;
- independent observer and oracle evidence;
- anti-overfitting/metamorphic evidence;
- full current-source locked-KiCad qualification;
- reproducibility;
- native-render engineering inspection;
- complete audits;
- every checkbox above checked with exact evidence.

Until then, status remains **INCOMPLETE**.
