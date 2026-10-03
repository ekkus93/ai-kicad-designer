# M2h2 Finalization TODO — 2026-09-27

**Status:** ACTIVE / INCOMPLETE

Canonical executable checklist for the M2h2 Ralph Loop.

Governing documents:

- `docs/M2_GENERALIZATION_REMEDIATION_SPEC.md`
- `docs/M2H2_FINALIZATION_SPEC_2026-09-27.md`
- `docs/M2H2_HANDOFF_2026-09-27.md`
- `fixtures/m2h2/STATUS.md`

A checkbox may be checked only from current-source evidence. Older qualification candidates, one-run evidence where five runs are required, requested/planned coverage labels, parse/generation success, or internal-only metrics without required real KiCad evidence are not sufficient.

## 0. Boundaries and baseline

- [x] Confirm M2h2-only scope: no M3, no corpus.v7, no CP-SAT. Evidence: finalization spec + handoff baseline.
- [x] Confirm unchanged hard gates: 210 × 140 mm spread, 80 mm local path, 60 mm support/locality where applicable, 250 mm canonical conductor length. Evidence: governing/finalization specs.
- [x] Confirm `.local/` is ignored and `research/legacy_openclaw/` is not inspected/used. Evidence: Ralph finalization operating contract.
- [x] Confirm Ralph Bridge is used for all GitHub/repository/CI state and writes. Evidence: Ralph Bridge v0.2.2 exact-head master commits.
- [x] Confirm direct `master` workflow with no per-task branch/PR churn. Evidence: direct master CAS commits; no task branch/PR created.
- [x] Record current `master` SHA and relevant source hashes in a fresh finalization evidence root. Evidence: `fixtures/m2h2/finalization_checks/baseline_28213224.json`.
- [x] Verify historical blind/evaluation evidence integrity before behavior changes. Evidence: baseline records 7,221 protected files and aggregate SHA-256 `f1dcfc89822b37c6c376f844adf6a43295ffd716ad64921f44d687dfb880200e`.
- [x] Verify frozen DP1–DP4 manifest/topology and interaction coverage plan are unchanged. Evidence: baseline frozen-input hashes.
- [x] Record `qualification_candidate4` as provisional/non-final because source hashes are stale. Evidence: baseline + handoff/status.

## 1. Current-source baseline

- [x] Run current fast complete pytest baseline. Evidence: `fixtures/m2h2/finalization_checks/stabilization_f161672f_ci.json`, source `f161672f761559e0e8ae7294f1c4df39fa24bebb`, run `37127192673`, locked job `111214831140`, 271 passed in 145.14s.
- [x] Run scoped Ruff lint. Evidence: `fixtures/m2h2/finalization_checks/stabilization_f161672f_ci.json`, static job `111214830860`.
- [x] Run scoped Ruff format check. Evidence: same exact-source static job.
- [x] Run `git diff --check` / applicable whitespace checks. Evidence: same static and locked jobs.
- [x] Confirm fresh V6-3 one-run real-tool regression. Evidence: `fixtures/m2h2/finalization_checks/stabilization_f161672f_ci.json`, accepted V6-3 build; complete signature archived in artifact `11275239169`.
  - [x] locked KiCad 10.0.6; evidence: locked regression runner reports no version errors.
  - [x] independent electrical observation; evidence: accepted regression validates electrical status and diagnostics.
  - [x] zero unexpected ERC; evidence: accepted regression validates independent ERC report.
  - [x] serialized-scene verification; evidence: accepted regression validates obligation certificate.
  - [x] canonical VREF <= 250 mm; evidence: accepted regression validates single canonical VREF graph and unchanged length gate.
- [x] Confirm fresh DP2 one-run real-tool regression. Evidence: `fixtures/m2h2/finalization_checks/stabilization_f161672f_ci.json`, accepted DP2 build; complete signature archived in artifact `11275239169`.
  - [x] no external VREF connector; evidence: regression explicitly validates reference connector inventory.
  - [x] two NE5532 packages; evidence: regression validates exact package count.
  - [x] all required reference consumers connected; evidence: regression requires one canonical reference component and nine terminals.
  - [x] independent electrical observation; evidence: accepted electrical status with no diagnostics.
  - [x] zero unexpected ERC; evidence: accepted independent ERC report.
  - [x] canonical VREF <= 250 mm; evidence: accepted canonical reference graph/length checks.

## 2. Obligation-complete certificate audit and implementation

- [x] Exactly one geometry owner per symbol occurrence is certified. Evidence: `tests/test_m2h2_repair_matrix.py::test_obligation_certificate_exports_pre_emission_invariant_witnesses` verifies unique certificate geometry owners match emitted ownership evidence.
- [x] Complete physical terminal accounting is certified. Evidence: `tests/test_m2h2_repair_matrix.py::test_obligation_certificate_exports_pre_emission_invariant_witnesses` verifies terminal inventory count matches the net-graph terminal witnesses.
- [x] Every semantic obligation is represented in the certificate. Evidence: `tests/test_m2h2_repair_matrix.py::test_certificate_exports_complete_semantic_obligation_inventory` proves the certificate directly exports current `SemanticPlan` ports, edges, constraints, precedence, physical terminals, presentation nets, and local-span obligations with exact ID/terminal correspondence.
- [x] Exact gateway-to-real-pin witness exists for every required routed terminal. Evidence: `tests/test_m2h2_repair_matrix.py::test_obligation_certificate_exports_pre_emission_invariant_witnesses` verifies every exported gateway witness is proved and terminal-backed.
- [x] Every required net has one complete canonical geometric conductor graph. Evidence: `tests/test_m2h2_repair_matrix.py::test_certificate_covers_required_net_graphs_and_placement_obligations` proves every semantic presentation net has an exported graph witness and every explicit-geometry net is one component.
- [x] Disconnected same-net islands are rejected before successful emission. Evidence: `tests/test_m2h2_contracts.py::test_disconnected_internal_islands_reject_matching_net_strings` and `tests/test_m2h2_contracts.py::test_explicit_net_rejects_label_join_and_unattached_leaf`.
- [x] Unintended dangling route endpoints are rejected before successful emission. Evidence: `tests/test_m2h2_contracts.py::test_bypassed_internal_gateway_tip_is_a_dangling_endpoint` and `tests/test_m2h2_contracts.py::test_explicit_net_rejects_label_join_and_unattached_leaf`.
- [x] Junction degree and unrelated crossing semantics are certified. Evidence: `tests/test_m2h2_contracts.py::test_junction_and_unrelated_crossing_are_not_metadata_shortcuts`.
- [x] Every signal precedence inequality survives shelf/variant/translation/repack/compaction. Evidence: `tests/test_m2h2_repair_matrix.py::test_certificate_covers_required_net_graphs_and_placement_obligations` verifies pre-emission placement witnesses are exported for all current-source precedence obligations, and `tests/test_m2h2_contracts.py::test_exact_locality_boundary_and_precedence_inequality` covers the hard negative.
- [x] 80 mm local-path limits are certified pre-emission. Evidence: `tests/test_m2h2_repair_matrix.py::test_certificate_covers_required_net_graphs_and_placement_obligations` verifies pre-emission local-span witness accounting, and `tests/test_m2h2_contracts.py::test_exact_locality_boundary_and_precedence_inequality` covers exact boundary and over-bound rejection.
- [x] 60 mm support/locality limits are certified pre-emission where applicable. Evidence: `tests/test_m2h2_contracts.py::test_support_span_exact_boundary` covers exact boundary and over-bound rejection.
- [x] 210 × 140 mm spread/page limits are certified pre-emission. Evidence: `tests/test_m2h2_repair_matrix.py::test_obligation_certificate_exports_pre_emission_invariant_witnesses` verifies the certificate final content envelope is within unchanged gates.
- [x] Reservation/body/text/corridor collision legality is certified pre-emission. Evidence: `tests/test_m2h2_repair_matrix.py::test_obligation_certificate_exports_pre_emission_invariant_witnesses` verifies reservation containment/allocation and no unallocated growth; `test_route_corridor_capacity_is_checked_before_candidate_acceptance` covers channel capacity rejection.
- [x] 250 mm canonical conductor-length limits are certified pre-emission. Evidence: `tests/test_m2h2_repair_matrix.py::test_obligation_certificate_exports_pre_emission_invariant_witnesses` verifies every exported canonical length is <= 250,000,000 nm.
- [x] Certified-scene digest matches the exact serialized in-memory scene. Evidence: `tests/test_m2h2_repair_matrix.py::test_obligation_certificate_exports_pre_emission_invariant_witnesses` verifies certificate geometry/input digests match the certified scene digests.
- [x] Failed certificate prevents successful `.kicad_sch` emission. Evidence: `tests/test_m2h2_repair_matrix.py::test_failed_certificate_prevents_successful_schematic_emission` mutates the certified scene after proof and verifies emission aborts before output creation.

## 3. Generic falsification matrix

### 3.1 Independent graph/connectivity oracle

- [x] Add/finish independently authored canonical-conductor graph oracle. Evidence: `tests/test_m2h2_contracts.py::reference_components` and graph falsifications.
- [x] Split and unsplit equivalent conductor graphs compare equal. Evidence: `tests/test_m2g2.py::test_unsplit_t_graph_is_subdivision_order_and_direction_invariant`.
- [x] Disconnected same-net islands fail. Evidence: `test_disconnected_internal_islands_reject_matching_net_strings`.
- [x] Label-only protected continuity fails. Evidence: `test_explicit_net_rejects_label_join_and_unattached_leaf` plus M2g2 negative controls.
- [x] Unauthorized geometric crossing does not create connectivity. Evidence: `test_junction_and_unrelated_crossing_are_not_metadata_shortcuts`.
- [x] Missing/invalid T or four-way junction topology fails. Evidence: `test_junction_and_unrelated_crossing_are_not_metadata_shortcuts`.
- [x] Extra unintended dangling endpoint fails. Evidence: `test_bypassed_internal_gateway_tip_is_a_dangling_endpoint` and `test_explicit_net_rejects_label_join_and_unattached_leaf`.
- [x] Duplicate/foreign-owned conductor interval negative is covered. Evidence: `test_global_branch_reuses_certified_same_net_local_interval_once`.

### 3.2 Gateway/pin proof

- [x] Exact gateway-to-pin attachment passes after legal translation. Evidence: `test_exact_pin_and_all_gateway_witnesses`; final-candidate translated gateway proof added in `m2_compose.py`.
- [x] One-grid-unit off-pin endpoint fails. Evidence: gateway witness falsification in `test_exact_pin_and_all_gateway_witnesses`.
- [x] Stale transformed gateway fails. Evidence: `test_exact_pin_and_all_gateway_witnesses`.
- [x] Wrong physical pin identity fails. Evidence: existing M2g2 typed identity/gateway witness tests plus exact final-candidate terminal proof.
- [x] Removed local escape segment fails. Evidence: local gateway witness keeps `require_escape=True`; stale/removed escape negative test.
- [x] Legal conductor subdivision/translation preserves proof. Evidence: translated gateway witness + split/unsplit metamorphic graph tests.

### 3.3 Tiny exhaustive placement oracle

- [x] Implement bounded exhaustive synthetic placement oracle/enumeration. Evidence: `test_tiny_exhaustive_two_band_reference_preserves_structural_classes` independently enumerates the finite synthetic two-band model.
- [x] Planner accepts when exhaustive oracle finds a legal arrangement. Evidence: the tiny exhaustive test compares feasible `side`/`stack` classes with `_partial_beam_candidates` and requires equality.
- [x] Planner reports bounded infeasibility when no legal arrangement exists. Evidence: exact spread boundary falsification requires `PACK_BUDGET_EXHAUSTED` for the independently infeasible over-bound synthetic placements.
- [x] Precedence/non-overlap/locality outcomes are compared independently of planner implementation. Evidence: tiny exhaustive rectangle enumeration plus independent exact precedence/locality boundary tests in `tests/test_m2h2_contracts.py`.

### 3.4 Exact-boundary tests

- [x] 80 mm local path exact boundary passes. Evidence: `test_exact_locality_boundary_and_precedence_inequality`.
- [x] 80 mm plus one coordinate unit fails. Evidence: same test.
- [x] 60 mm support/locality exact boundary passes where applicable. Evidence: `test_support_span_exact_boundary`.
- [x] 60 mm plus one coordinate unit fails where applicable. Evidence: same test.
- [x] 210 × 140 mm exact spread boundary passes when otherwise legal. Evidence: `test_exact_content_spread_boundaries_are_hard_and_inclusive`.
- [x] Above 210 mm or 140 mm fails. Evidence: same test.
- [x] 250 mm canonical conductor exact boundary passes. Evidence: `test_canonical_conductor_length_exact_boundary_passes_and_above_fails`.
- [x] Above 250 mm fails. Evidence: same test plus lower-bound pruning test.

### 3.5 Metamorphic/serialization tests

- [x] Set-like IR ordering does not alter governed decisions/output. Evidence: `tests/test_m2d1.py::test_set_permutation_and_refdes_renaming_preserve_compiler_geometry`.
- [x] Legal refdes renaming does not alter semantic geometry except legitimate text-envelope effects. Evidence: M2d1 metamorphic test.
- [x] Net-name renaming does not alter role-based routing decisions. Evidence: `test_internal_reference_net_rename_preserves_geometry_and_search_decisions`.
- [x] Equivalent segment subdivision does not alter observed connectivity. Evidence: M2g2 split/unsplit T-graph tests.
- [x] Late coordinate/text/wire mutation after certification invalidates serialized-scene verification. Evidence: `test_certified_scene_rejects_mutation_and_serialized_endpoint_change` and asset/design mutation test.

## 4. Structural search and routing closure

- [x] Conductor alternatives are genuinely different tree/topology structures. Evidence: `tests/test_m2h2_contracts.py::test_distribution_enumerates_distinct_trunk_topologies` verifies four distinct producer-centered/perimeter/side trunk signatures.
- [x] Canonical lower bounds are sound for signal nets. Evidence: `tests/test_m2h2_repair_matrix.py::test_canonical_length_lower_bound_applies_to_every_m2h2_route_role[signal-signal-signal_out-signal_in-signal]`.
- [x] Canonical lower bounds are sound for power nets. Evidence: `tests/test_m2h2_repair_matrix.py::test_canonical_length_lower_bound_applies_to_every_m2h2_route_role[power-power-power_out-power_in-distributive]`.
- [x] Canonical lower bounds are sound for reference/internal-reference nets. Evidence: `tests/test_m2h2_repair_matrix.py::test_canonical_length_lower_bound_applies_to_every_m2h2_route_role[reference-None-reference-reference-distributive]`.
- [x] Canonical lower bounds are sound for support/shared-control/distributive nets. Evidence: `tests/test_m2h2_repair_matrix.py::test_canonical_length_lower_bound_applies_to_every_m2h2_route_role` covers branch, support, shared-control and distributive explicit-geometry cases.
- [x] Corridor/reservation capacity is checked before route acceptance. Evidence: `tests/test_m2h2_repair_matrix.py::test_route_corridor_capacity_is_checked_before_candidate_acceptance` proves global-route channel capacity accepts one route wire and rejects duplicate occupancy before candidate acceptance.
- [x] Best rejected candidate and exact failure witness are preserved on every failure exit. Evidence: `tests/test_m2h2_repair_matrix.py::test_failure_exit_preserves_candidate_decisions_and_exact_failure_witness` forces every candidate to reject with a typed canonical-length conflict and verifies candidate decisions, failed metric, layout attempts, failure class, net, actual, and limit are preserved.
- [x] Evidence reports meaningful structural/variant diversity, not raw attempt count only. Evidence: `tests/test_m2h2_repair_matrix.py::test_composition_evidence_reports_structural_diversity_not_raw_attempt_count` verifies seed structures, placement classes, proved structures, and proved-candidate structures in `compose_with_evidence`.
- [ ] V6-3 remains <= 250 mm canonical VREF without gate change or label shortcut. Evidence: `fixtures/m2h2/finalization_checks/stabilization_1273d6af_ci.json`, fresh locked accepted regression.
- [x] DP2 internal VREF remains connectorless, fully distributed, and <= 250 mm. Evidence: `fixtures/m2h2/finalization_checks/stabilization_1273d6af_ci.json`, fresh locked accepted regression.

## 5. Typed repair closure

- [x] Typed detour/canonical-length conflict produces a genuinely changed candidate. Evidence: `test_typed_repairs_use_structured_conflict_fields_and_change_state`.
- [x] Typed local-span conflict produces a genuinely changed candidate. Evidence: same test.
- [x] Typed signal-order conflict produces a genuinely changed candidate. Evidence: same test.
- [x] Typed blocked-gateway/access conflict produces a genuinely changed candidate. Evidence: same test.
- [x] Typed reservation/collision conflict produces a genuinely changed candidate. Evidence: `tests/test_m2h2_repair_matrix.py::test_typed_growth_repairs_use_conflict_fields_for_remaining_categories` covers `reservation_violation` and `collision_violation` typed conflicts without parsing diagnostics.
- [x] Typed route/envelope-growth conflict produces a genuinely changed candidate. Evidence: `tests/test_m2h2_contracts.py::test_typed_repairs_use_structured_conflict_fields_and_change_state` and `tests/test_m2h2_repair_matrix.py::test_typed_growth_repairs_use_conflict_fields_for_remaining_categories` verify one-pitch envelope growth with changed candidate state.
- [x] Typed disconnected-net/island conflict is handled where represented by the current repair model. Evidence: `tests/test_m2h2_repair_matrix.py::test_typed_growth_repairs_use_conflict_fields_for_remaining_categories` covers `net_connectivity` and `dangling_endpoint` typed conflicts using structured `net`/gateway fields.
- [x] Repair dispatch does not parse human-readable error strings. Evidence: structured-field repair test deliberately replaces exception diagnostics with unparseable text before repair.
- [x] No-op/repeated candidate states are deduplicated. Evidence: `compose_with_evidence` rejects unchanged repairs and globally records `(fragment variant, delta, route_retry)` state digests as `repeat_state_skipped`.
- [x] No-op states do not consume budget as new structural exploration. Evidence: `complete_attempts` increments only after no-op/repeat-state rejection in `compose_with_evidence`.
- [x] Candidate/repair budget counters never silently reset. Evidence: one monotonic `complete_attempts` counter spans all seeds/rounds and is preserved in success/failure evidence.
- [x] Exact attempted-state diversity is recorded in evidence. Evidence: `layout_attempts`, `structural_search.attempted_structure_count`, per-seed structural signatures, and exact complete-attempt budget are emitted.

## 6. Interaction coverage I1–I6 — final source

### 6.1 Coverage infrastructure

- [x] Freeze final-source interaction runner/tool hashes. Evidence: `fixtures/m2h2/finalization_checks/final_source_f161672f.json`, 19 production modules, four qualification runners and three locks; no cell qualification credit. Current-source revalidation: complete 271-test baseline `37127192673`, locked job `111214831140`, evidence `fixtures/m2h2/finalization_checks/stabilization_f161672f_ci.json`.
- [x] Coverage result records actual observed structural class, not requested factor labels only. Evidence: `tools/run_m2h2_i1.py::observed_structural_class` derives the selected seed/round, placement class, and proved structure from composition evidence and records only a five-run-stable observed class; `tests/test_m2h2_interaction_runner.py::test_observed_structural_class_uses_selected_run_evidence_not_requested_label` passed in exact-head GitHub Actions run `36517979598`, job `M2h2 contract pytest on hosted runner` (`109244434910`) at `0e6f29f42f8772af20f7ba1eae3929a93c37d162`. Current-source revalidation: complete 271-test baseline `37127192673`, locked job `111214831140`, evidence `fixtures/m2h2/finalization_checks/stabilization_f161672f_ci.json`.
- [x] Every covered cell links to real-tool qualification evidence. Evidence: `tools/run_m2h2_i1.py::validate_coverage_ledger_evidence` requires every covered cell to include `real_tool_qualification_evidence` with schema `m2h2.real-tool-evidence.1`, locked KiCad 10.0.6, exact source head, qualification root/results path, case ID, and nonempty run paths; `tests/test_m2h2_interaction_runner.py::test_current_coverage_ledger_has_no_invalid_evidence_records` and `tests/test_m2h2_interaction_runner.py::test_covered_cells_require_real_tool_evidence_not_parse_or_generation_only` passed in exact-head GitHub Actions run `36560904459`, job `M2h2 contract pytest on hosted runner` (`109381262073`) at `239c7d4afe86f78f955f6524b8aeb050a5b5a0bd`. Current-source revalidation: complete 271-test baseline `37127192673`, locked job `111214831140`, evidence `fixtures/m2h2/finalization_checks/stabilization_f161672f_ci.json`.
- [x] Impossible cells require semantic impossibility witnesses, not layout failures. Evidence: `tools/run_m2h2_i1.py::validate_coverage_ledger_impossibilities` requires unsupported cells to include a semantic witness with schema `m2h2.semantic-impossibility.1`, kind `semantic_impossibility`, semantic source, and proof text while rejecting layout/build/routing/tool failure keys; `tests/test_m2h2_interaction_runner.py::test_unsupported_cells_require_semantic_impossibility_not_layout_failure` passed in exact-head GitHub Actions run `36560904459`, job `M2h2 contract pytest on hosted runner` (`109381262073`) at `239c7d4afe86f78f955f6524b8aeb050a5b5a0bd`. Current-source revalidation: complete 271-test baseline `37127192673`, locked job `111214831140`, evidence `fixtures/m2h2/finalization_checks/stabilization_f161672f_ci.json`.

- [x] Reject one-run, repeated-run, empty-run-link, and non-SHA coverage records. Evidence: `tests/test_m2h2_interaction_runner.py::test_real_tool_coverage_rejects_incomplete_or_repeated_runs` (five parameterized negatives), current-source hosted contract job `110976476137`, run `37048718582` at `465248ba47fe0d124ecd7997f2cdf898095b1d35`. Current-source revalidation: complete 271-test baseline `37127192673`, locked job `111214831140`, evidence `fixtures/m2h2/finalization_checks/stabilization_f161672f_ci.json`.

### 6.2 I1

- [x] Qualify every required I1 cell on final source. Evidence: `fixtures/m2h2/finalization_checks/interaction_585a4f7c_ci.json`, current 72×5 locked KiCad evidence.
- [x] Qualify selected I1 triple(s). Evidence: `fixtures/m2h2/finalization_checks/interaction_585a4f7c_ci.json`, current 72×5 locked KiCad evidence.
- [ ] Verify terminal/electrical/ERC/layout/path/order invariants.
- [ ] Reconcile I1 covered cells in `development/interaction_coverage.json`.

### 6.3 I2

- [x] Qualify every required I2 cell on final source. Evidence: `fixtures/m2h2/finalization_checks/interaction_585a4f7c_ci.json`, current 72×5 locked KiCad evidence.
- [ ] Qualify selected I2 triple(s).
- [ ] Verify internal-reference/parked/shunt-return obligations.
- [ ] Reconcile I2 covered cells.

### 6.4 I3

- [x] Qualify every required I3 electrical/path case on final source. Evidence: `fixtures/m2h2/finalization_checks/interaction_585a4f7c_ci.json`, current 72×5 locked KiCad evidence.
- [ ] Qualify all required actual shelf/band structural classes.
- [x] Re-run required structural alternatives on final source. Evidence: `fixtures/m2h2/finalization_checks/structural_585a4f7c_ci_inspection.json`, all nine cases ×5, source f161672f / producer 585a4f7c; actual class records and native SHA-verified agent review.
- [x] Qualify selected I3 triple(s). Evidence: `fixtures/m2h2/finalization_checks/interaction_585a4f7c_ci.json`, current 72×5 locked KiCad evidence.
- [ ] Reconcile I3 covered cells from actual class evidence.

### 6.5 I4

- [x] Qualify every required I4 cell on final source. Evidence: `fixtures/m2h2/finalization_checks/interaction_585a4f7c_ci.json`, current 72×5 locked KiCad evidence.
- [x] Qualify selected I4 triple(s). Evidence: `fixtures/m2h2/finalization_checks/interaction_585a4f7c_ci.json`, current 72×5 locked KiCad evidence.
- [ ] Verify unequal-consumer/cross-fragment/sibling-order invariants.
- [ ] Reconcile I4 covered cells.

### 6.6 I5

- [x] Qualify every required I5 cell on final source. Evidence: `fixtures/m2h2/finalization_checks/interaction_585a4f7c_ci.json`, current 72×5 locked KiCad evidence.
- [x] Qualify selected I5 triple(s). Evidence: `fixtures/m2h2/finalization_checks/interaction_585a4f7c_ci.json`, current 72×5 locked KiCad evidence.
- [ ] Verify 3+ gateway distribution/multiple-shelf/restricted-entry invariants.
- [ ] Reconcile I5 covered cells.

### 6.7 I6

- [x] Qualify every required I6 shared-package/reference cell on final source. Evidence: `fixtures/m2h2/finalization_checks/interaction_585a4f7c_ci.json`, current 72×5 locked KiCad evidence.
- [x] Qualify required text-stress × support-count cells. Evidence: `fixtures/m2h2/finalization_checks/interaction_585a4f7c_ci.json`, current 72×5 locked KiCad evidence.
- [x] Qualify required text-stress × branch-degree cells. Evidence: `fixtures/m2h2/finalization_checks/interaction_585a4f7c_ci.json`, current 72×5 locked KiCad evidence.
- [ ] Reconcile I6 covered cells.

### 6.8 Coverage completion

- [ ] Every required I1–I6 cell is covered or has a valid semantic impossibility witness.
- [ ] Every selected triple is covered or has a valid semantic impossibility witness.
- [ ] Coverage ledger contains no cell marked complete from parse/generation success alone.

## 7. Source stabilization

- [x] Finish the identified behavior-affecting repair. Evidence: `fixtures/m2h2/finalization_checks/source_review_f161672f.json`, current complete tests and locked regressions. Reopen on any fresh qualification/native falsification.
- [x] Complete pytest passes. Evidence: `fixtures/m2h2/finalization_checks/stabilization_f161672f_ci.json`, exact source `f161672f761559e0e8ae7294f1c4df39fa24bebb`, 271 passed.
- [x] Scoped Ruff lint passes. Evidence: same exact-source static job `111214830860`.
- [x] Scoped Ruff format check passes. Evidence: same exact-source static job.
- [x] `git diff --check` passes. Evidence: same static and locked jobs.
- [ ] Applicable whitespace/link checks passes. Scoped whitespace passes; final evidence-link audit remains required.
- [x] Record stabilized final source hashes. Evidence: `fixtures/m2h2/finalization_checks/final_source_f161672f.json`, all 19 production modules, four qualification runners and three locks.
- [ ] Create fresh qualification root tied to exact stabilized source. Trigger requests separate exact producer-SHA roots for all 56 positives, 72 interactions and nine structural cases. Verify actual workflow roots before closing.
- [ ] Confirm no behavior-affecting source changes after final qualification starts.

## 8. Final-source 56-positive qualification

Prior machine evidence, invalidated for final-source qualification by the required-field readability fix: successful locked KiCad job `110975750982`, run `37048500798`, source `260e33c`; 56/56 accepted and five-run reproducible. Artifact ID `11246541158` contains all fresh projects/XML/ERC/SVG/reports. Audit run `37050923509` confirms production source and lock hashes equal current master. See `fixtures/m2h2/finalization_checks/qualification_260e33c_ci.json`.

- [ ] Run all 56 required positives.
- [ ] Run five clean builds per positive.
- [ ] Locked KiCad 10.0.6 used for every build.
- [ ] Fresh XML/electrical export produced.
- [ ] Exact independent package/unit/pin identity passes.
- [ ] Exact independent electrical partitions pass.
- [ ] Zero unexpected ERC violations.
- [ ] Layout/path/reservation/certificate gates pass.
- [ ] Compiler-owned project bytes reproduce as governed.
- [ ] Local variant choices reproduce.
- [ ] Canonical conductor trees reproduce.
- [ ] Obligation certificates reproduce.
- [ ] Structural candidate/repair decisions reproduce.
- [ ] Complete metric vectors reproduce.
- [ ] Normalized SVG geometry/text reproduces.
- [ ] Normalized reports/manifests reproduce under only documented normalization.
- [ ] Historical invalid V3-8 remains correctly rejected. The fresh run rejects it; reconcile exact failure codes before closing this item.

## 9. Final interaction/stress qualification

- [x] Run required final-source interaction qualification roots for I1–I6. Evidence: `fixtures/m2h2/finalization_checks/interaction_585a4f7c_ci.json`, current 72×5 locked KiCad evidence.
- [ ] Run required selected triples.
- [x] Run required final-source structural alternatives. Evidence: `fixtures/m2h2/finalization_checks/interaction_585a4f7c_ci.json`, current 72×5 locked KiCad evidence and `fixtures/m2h2/finalization_checks/structural_585a4f7c_ci_inspection.json`.
- [x] Run required long-field/stress derivatives. Evidence: `fixtures/m2h2/finalization_checks/interaction_585a4f7c_ci.json`, current 72×5 locked KiCad evidence.
- [ ] Five-run reproducibility passes for every governed interaction/stress case.
- [x] No interaction/stress evidence relies solely on pre-final-source runs. Evidence: `fixtures/m2h2/finalization_checks/interaction_585a4f7c_ci.json`, current 72×5 locked KiCad evidence.

## 10. Engineering inspection

- [ ] Inspect fresh final renders for signal ordering.
- [ ] Inspect feedback/timing clarity.
- [ ] Inspect reference distinction.
- [ ] Inspect package/support association.
- [ ] Inspect fanout traceability.
- [ ] Inspect required reference/value/text readability.
- [ ] Record reviewer/method as engineering/agent inspection, not human approval.
- [ ] Record worst observed metrics and any rejected candidate of interest.

## 11. Final audits

- [ ] Complete pytest passes on final source.
- [ ] Scoped Ruff lint passes.
- [ ] Scoped Ruff format check passes.
- [ ] `git diff --check` passes.
- [ ] Scoped whitespace checks pass.
- [ ] Applicable link checks pass.
- [ ] Historical evidence hash audit passes.
- [ ] Literal anti-overfitting scan passes.
- [ ] Structural anti-overfitting review of active conditionals/dispatch passes.
- [ ] No CP-SAT dependency or implementation exists.
- [ ] Report terminal/component coverage.
- [ ] Report local/global tree lengths.
- [ ] Report structural/variant diversity.
- [ ] Report exact attempt/repair budgets.
- [ ] Report best rejected candidates/failure witnesses.
- [ ] Report prediction-versus-observation deltas.

## 12. Reconciliation and PASS

- [ ] Reconcile `fixtures/m2h2/STATUS.md` to final current-source evidence.
- [ ] Reconcile every completed TODO item with exact evidence references.
- [ ] Confirm all generic obligation/certificate completion criteria are satisfied.
- [ ] Confirm all I1–I6 coverage criteria are satisfied.
- [ ] Confirm 56-positive five-run final-source qualification is PASS.
- [ ] Confirm all required interaction/stress final qualification is PASS.
- [ ] Confirm historical V3-8 remains rejected.
- [ ] Confirm all reproducibility gates are PASS.
- [ ] Confirm engineering inspection has no unresolved hard defect.
- [ ] Confirm all final audits are PASS.
- [ ] Declare **M2h2 PASS** in `fixtures/m2h2/STATUS.md`.
- [ ] Mark this TODO **COMPLETE / PASS**.

After PASS, stop. Do not create corpus.v7 and do not begin M3.

### Render-inspection follow-up — 2026-10-02

`fixtures/m2h2/finalization_checks/render_inspection_260e33c.json` records the actual agent inspection and a hard timer reference/value overlap missed by the wire-only slot/observer checks. The body/label/field-aware slot fix and independent emitted-byte rejection are behavior-affecting. Source `260e33c` and structural source `df917d0` remain preserved machine evidence, but cannot close final-source qualification gates after this fix. Fresh complete tests and qualification are required. Five alternate I3 classes passed five fresh searches at `df917d0` (run `37051640945`); the 3+ interleaved case remains a layout development failure, not semantic impossibility.

### Bounded selection follow-up — 2026-10-02

The source audit found `compose_with_evidence` stopped after two proved structural classes and before considering the remaining retained seeds. The selection loop now accounts for every seed's four slots, considers an alternative routing slot after an initial proof, keeps global deduplication/counters, records non-needed repair slots, and ranks all proved candidates. `test_quality_selection_finishes_all_retained_seed_slots` independently asserts complete slot accounting, deterministic score selection, and the unchanged 32-complete-attempt ceiling. Qualification must be rerun after this behavior change. The stricter required-field geometry checks are preserved; 32 bounded nearby/fallback text slots provide compact alternatives after the shared-reference regression at `634d529`.

### Stabilized-source qualification — 2026-10-02

Source `beb50458a1ba3b35667534954d2f01e0f40152ba` passes 241 complete tests, scoped lint/format/whitespace, fresh V6-3/DP2 regressions, and six alternate I3 classes with five independent real-tool builds each (`37053544406`, job `110992550174`, artifact `11247344029`). Final base and interaction qualification are now started on identical production source in a new exact-head root. Coverage, final inspection, and final audits remain unchecked until their fresh evidence is reconciled.

### Final evidence audit implementation — 2026-10-02

`tools/run_m2h2_final_artifact_audit.py` checks the complete production-module/lock inventory, interaction and structural runner identities, exact V3-8 authored rejection, five-run evidence, actual placement classes, emitted-pin terminal bounds/path diagnostics, independent local/global conductor accounting, budgets/selection/rejected candidates, prediction/observation deltas, and fresh-render/report transfers. `tests/test_m2h2_final_audit.py` independently falsifies overlapping/reversed/subdivided conductor accounting, unsplit T path distance, disconnected-island reachability, and nonorthogonal inputs. These audit/report-only changes preserve production hashes frozen in `final_source_beb50458.json`; final gates remain open pending actual fresh artifact execution and inspection.

The final audit also checks scoped documentation links, structural control-flow literals, dependency exclusion, and emitted-pin source-to-consumer diagnostics. Structural-render transfer uses exact successful run `37053544406`; render acceptance remains pending agent inspection, rather than being inferred from transfer or qualification success.

### Net-label readability follow-up — 2026-10-02

Close-up inspection of fresh source `beb50458` I3 renders transferred in run `37067694162` found duplicated timer supply text and reset labels on pin/body text. The final-source base run `37066444590` passed 56/56 x5 (artifact `11252733877`, zip SHA-256 `15a1d768ffb9fe91a678c6e6a8b94cf449c93934422c904bac757a21cb90267b`) but remains preserved, non-final machine evidence after the label correction. `m2_fragments` now accounts for the actual left-justified label footprint, gives left escapes full label clearance, removes redundant source/gateway labels, and places reset labels on explicit measured stubs. The independent observer rejects label/body and label/label overlaps, with emitted-byte synthetic negatives in `tests/test_m2h2_label_geometry.py`. Fresh complete tests and affected real-tool qualification are required; engineering inspection remains incomplete.

Exact render hashes, six-case review observations, and hard-defect witnesses are preserved in `fixtures/m2h2/finalization_checks/render_inspection_beb50458.json`. The three-amplifier alternative is explicitly one active-core band and two bands when parked/package support is included, matching the pre-existing core-band alternative protocol; these counts must never be hidden or relabeled.

Label clearance is conditional on actual label emission. Explicit internal-reference gateways retain their original escape lengths; measured text clearance must not add conductor length to unlabeled routed gateways.

### Label readability regression repair — 2026-10-02

Exact-head run `37068659936` at `eaf4cd6` preserved eight full-suite failures and one hosted structural-contract failure. Place left-bottom net labels in bounded measured slots with explicit stubs; retain independent label/body and label/label rejection after electrical/path diagnostic checks. Broaden measured row compaction to legal gaps and stagger offsets without changing the eight-seed/32-attempt bound. Current-source tests and all fresh qualification remain required; no completion checkbox is promoted from these implementation changes.

Run `37069847886` at `8b6f258` rejects the generic label-stub prototype: LED anode escapes point inward, and moving their labels adds body-crossing conductors. Keep the independent readability gate and fix the local LED anode escape outward instead. Search measured structural compaction/stagger proposals across the retained packing baselines, keeping the same final candidate budget. Preserve the failed evidence; qualification remains open.

Run `37070201875` at `64de43d` passes the hosted structural contracts; locked full-suite qualification still rejects V4-7 VCC routing. Field-slot construction was reserving symmetric label rectangles inconsistent with the left-bottom emitted geometry. Use the same measured label extents as independent observation while retaining required field clearance. Fresh full tests and qualification are still required.

Run `37070465631` preserves the same two failures (244/246 tests pass). Net routing now admits already owned same-net local wire conductors for canonical attachment, rather than treating them as foreign obstacles; unrelated wires, bodies, pins, text and protected paths retain their checks. Add measured seed diagnostics to the structural-class regression. Acceptance still requires complete conductor proofs, independent artifact checks and locked KiCad; qualification is open.

Measured diagnostics from `37070806754` identify a parked function in the needed active-row slot. Add a bounded atomic active/parked placement exchange into the vacated cell, followed by complete placement constraints and routing proofs. Remove the ineffective same-net obstacle experiment; retain V4-7 gateway diagnostics for the unresolved route. No gate or completion evidence is changed.

Run `37071209807` preserves both failures. Compaction must repair the complete active row: a baseline sibling's external-source inequality can invalidate every isolated move. Add a bounded atomic active-row transaction and relocate parked blockers into vacated cells, with all geometry/terminal constraints rechecked. Timer supply escapes now follow their physical upward pin exit; preserve a local supply label only when no gateway label replaces it. Reset-label escape uses the full text width on grid without an unnecessary extra pitch. Fresh tests, length proofs, actual render inspection and all qualification remain open.

### Restabilized source — 2026-10-03

Source `8675431f76594fd51c591180f0bba85ece942c9f` passes 246 complete tests, hosted contracts, scoped lint/format/whitespace and both locked KiCad 10.0.6 current-source regressions in run `37071729309`. See `stabilization_8675431f_ci.json` and the complete production/runner/lock freeze `final_source_8675431f.json`. Start new base, I1–I6 and six-class structural roots on this identical production source. Transfer actual structural renders automatically after a successful five-run structural job. All coverage, fresh qualification, render inspection and final audits remain open.

Fresh qualification head `ada198a39b6fc8f652793f9444393276619f7984` passes full fast validation (`37089782363`). The audit workflow now targets exact base run `37089782367`, I1–I6 run `37089782393` and structural run `37089782376`, all new roots on frozen production source `8675431f`. These jobs are pending/running; the audit is not dispatched and no qualification checkbox is completed until actual accepted evidence is reconciled.

### Fresh qualification failure — 2026-10-03

Fresh frozen-source interaction run `37089782393` at `ada198a39b6fc8f652793f9444393276619f7984` preserves five repeated body/pin build failures for `i3/three_amplifier_one_band`, `i5/c2_s3plus` and `i5/c3_s1_2`. All other interaction cases pass five runs, but the required matrix remains INCOMPLETE. Artifact `11262462251` (zip SHA-256 `909e8ef577b78c8bf242254413e64bbf15747ca96223ba6f27ee53006866ff78`) preserves all successful and failed evidence. Extract exact geometry witnesses and repair the implementation under unchanged gates; ordinary qualification failures are not semantic impossibility. No final checkbox is promoted.

The exact independent failures are `observed net label overlaps body/label: OUTPUT_1, J5`, `PASSIVE_1_OUT, J4`, and `PASSIVE_1_OUT, J6`; electrical observation passes in all three. Preserved-failure inspection run `37090552267`, job `111109782308`, transfers their authored failure reports. Gateway label placement now extends an actual emitted-label escape on grid until its left-bottom footprint clears every owned physical body, bounded to 32 local steps. No label is moved off its conductor and no observer/gate is weakened. Three physical connector-access regression controls and targeted five-run real-tool checks precede fresh full qualification. This behavior change invalidates qualification head `ada198a` as final evidence; preserve its outcomes.

Preserved base qualification `37089782367` accepts 51/56 positives x5 and rejects V3-8 correctly. It retains failures for V5-3 precedence, V6-5 label/LED body overlap, V6-6 local OUT_B/REF crossing, V6-8 blocked VCC routing, and DP4 VCC lower-bound overflow. Artifact `11261579497` (zip SHA-256 `d9bffadde5dd8e1cb59e4aef1f41e4992a15d0028388d35a50bc2e5bf0ec2b9b`) and all historical inputs remain unchanged. Structural run `37089782376` fails a0_interleaved on OUTPUT_2/J4 label overlap while the other five alternatives pass. Probe these known regressions with bounded current-source composition on a hosted runner before repeating full locked qualification; composition-only evidence cannot close any qualification gate.

### Structural regression repair — 2026-10-03

`fixtures/m2h2/finalization_checks/structural_regression_repair_2026-10-03.json` binds all 19 production hashes and composition-only witnesses for the five preserved base failures. Five dedicated regression tests pass locally in 46.76 seconds; scoped lint/format pass. Package backfill now accounts for the source's actual row and refuses occupied cells. External connector precedence can translate a complete staged group atomically. Generated supplies with typed internal producers gain measured compact distribution candidates and the existing shared-tree planner. Timer control support is placed on the other side of the supply exit while preserving its terminal identities and support span. DP4's proved candidate uses 227.33 mm of canonical VCC conductor under the unchanged 250 mm gate. The eight-seed/32-attempt bounds, protected-path-first priority and all observation gates remain unchanged. These are composition-only repair witnesses, not final qualification. Locked full pytest, seven current-source regressions, targeted connector-label x5 and all fresh final qualifications remain required; no completion checkbox is promoted.

Locked run `37093175818` at `7ebfe8b3d10fb90532aa1e20277618b399886fb9` passes full pytest, V6-3/DP2 and all three connector-label x5 regressions. New V5-3, V6-5, V6-6 and DP4 real-tool builds pass; V6-8 composes but locked KiCad reports one ERC violation. Preserve artifact `11263777233` (zip SHA-256 `db8c431d9515caf716c76a0bea9deb8de7b147cd8e1ad64613a33a552bcba02b`) and inspect its authored ERC report. ERC remains a hard failure, not a semantic impossibility or user blocker; fresh full qualification stays open.

### Power endpoint and snapped package-backfill repair (2026-10-03)

Development repair evidence: `fixtures/m2h2/finalization_checks/power_endpoint_and_grid_backfill_repair_2026-10-03.json`. The preserved V6-8 ERC endpoint failure is not waived. Typed power endpoints now carry actual conductor labels, shared power trees preserve the existing label-island policy, and package backfill reserves a grid pitch before measured atomic precedence repair. Six bounded composition regressions pass locally (98.11 s); Ruff check and format pass. Fast locked validation now includes the shared-rail case. This is composition-only evidence; final qualification, interaction, render, and reconciliation boxes remain unchecked pending fresh locked KiCad 10.0.6 evidence.

Compatibility follow-up: `fixtures/m2h2/finalization_checks/shared_tree_guard_compatibility_2026-10-03.json` preserves exact CI `37094713425` (253 pass, two failures), limits the shared-tree endpoint guard to its intended net class, and restores actual measured-size packing provenance. Both failing contracts now pass locally (12.31 s). The prior development composition sweep passed all 56 positives; no final qualification credit is claimed. Complete pytest and locked builds must pass on the corrected source.

### Restabilized power/packing source — 2026-10-03

Production head `1397637d0fe51e5dfcf46038ec34d9a65e910173` passes complete locked validation `37094984816`: 255 pytest tests in 132.09 s, static checks and hosted contracts; fresh V6-3/DP2 one-run checks; three connector-label cases with five actual builds each; and all six qualification-regression one-run builds. Evidence: `fixtures/m2h2/finalization_checks/stabilization_1397637d_ci.json`. The exact-source composition matrix passes all 56 positives (`fixtures/m2h2/finalization_checks/composition_matrix_1397637d.json`), without final qualification credit. Production/runners/locks are frozen in `fixtures/m2h2/finalization_checks/final_source_1397637d.json`. Fresh 56 x5 plus negative, I1-I6 x5, and six structural alternatives x5 are started against this identical source. All qualification, coverage, render, final audit, and PASS reconciliation criteria remain open.

### Tall-core selected-triple routing repair — 2026-10-03

The uploaded master snapshot matches all 19 frozen production modules. Its local 72-case interaction composition sweep finds I3 `selected_triple` blocked on `TIMER_A_OUT` (30/32 complete attempts); the other 71 cases compose. Generic timer output alternatives now retain outward exits, excluding an inward left-facing output that folds into the owned terminal corridor. Seven targeted composition tests pass in 73.36 s and all 56 positive cases compose on the changed source; these provide no final qualification credit. The fast locked workflow adds the selected triple's five real-tool builds. Prior source `1397637d` / candidate `47d4978c` is superseded; its baseline, 56 x5 qualification and six x5 structural evidence remain historical. Source-stabilization/freeze boxes are reopened pending new exact-source baseline evidence. Explicitly superseded qualification runs release the locked runner; report-only pushes do not interrupt qualification. See `fixtures/m2h2/finalization_checks/outward_timer_output_repair_2026-10-03.json`.

### Outward-access source freeze — 2026-10-03

Source `2575ee20fba0ca24cc6edf50e0ae038b9aa8153c` passes 256 tests (137.77 s), static/hosted checks, V6-3/DP2, all four targeted five-run cases including the tall-core/shared-package/long-text triple, and six fresh qualification regression builds in run `37096621691`. Exact evidence: `stabilization_2575ee20_ci.json`, `final_source_2575ee20.json`, `source_review_2575ee20.json`. All 56 positive and 72 interaction compositions pass; composition-only sweeps provide no final qualification credit. Fresh base/negative, I1-I6 and structural x5 suites are now started on these identical production hashes; coverage, final renders, audits and PASS remain open.

### Native locked-font render falsification — 2026-10-03

All 56 positives x5, 72 interaction cases x5, six structural alternatives x5, and the original V3-8 negative pass machine qualification for producer `84b21bc399e2239cd796bb9ec4f09a989f8ce808`, with unchanged production source `2575ee20`. Artifact audit `37106385552` verifies their complete machine evidence and all 7,221 protected historical files. This does not close final qualification: actual native DP3 long-field inspection finds `REQUIRED_NET_LABEL20` running into `A_OUT` with a nominal 0.0821 mm text overlap. The former 0.89 mm-per-character label bounds miss the locked stroke font width. Exact native evidence is archived in `fixtures/m2h2/finalization_checks/native_render_defect_dp3_long_fields_84b21bc3.svg`; audit/run/artifact references and the witnessed text coordinates are in `fixtures/m2h2/finalization_checks/render_falsification_84b21bc3_2026-10-03.json`. Only six base cases were visually inspected before finding this hard defect. Source stabilization and the final-source hash freeze are reopened. Correct font measurement, repair ensuing ordinary layout failures, and repeat all required fresh qualifications and render inspection before checking any final completion item. I3 active-count 2 / one-band and actual-interleaving classes also require explicit observed evidence; one active-core band in the three-amplifier alternative must not be described as one total non-interface band.

### Locked-stroke font repair — 2026-10-03

`fixtures/m2h2/finalization_checks/font_metrics_repair_2026-10-03.json` binds the repaired source and test hashes. Glyph-based label bounds contain all 5,397 actual native locked-font samples; the independent emitted-byte observer now rejects the authored wide-glyph collision controls. Expanded package geometry is retained alongside a balanced compact alternative within eight local variants; compact passive support and typed distribution repair retain all fixed gates and complete-attempt budgets. Targeted V6-3, DP2 and V6-8 compositions pass; scoped lint/format pass. Full matrices and exact-head locked validation are required before source stabilization. Composition, calibration and unit evidence do not count as fresh final-source KiCad x5 qualification. Baseline, source freeze and final qualification/render/audit gates remain open.

### Bounded independent oracle and complete composition — 2026-10-03

All 56 positives and 72 interaction compositions pass on production `7b788e58a6a5e21f286b4a25d643e0727da1944e`. The new cell-walk regression initially attempted nanometre-sized cells and exhausted resources; coordinate compression preserves conductor contacts and bounds its independent enumeration. The corrected regression passes in 12.30 s. `fixtures/m2h2/finalization_checks/bounded_oracle_and_composition_7b788e58.json` records all composition witnesses and the failed CI attempt. The structural protocol now requires eight distinct named alternatives, including actual two-active-core one-band and interleaved cases. These pure proofs supply no real-tool qualification credit. Complete exact-source pytest and locked regressions must rerun; all final qualification, coverage, render, audit and PASS gates remain open.

## Font repair source stabilization — 2026-10-03

Production `7b788e58a6a5e21f286b4a25d643e0727da1944e` passes complete locked validation `37109142099` at test/protocol head `f18b02d586e9575a0a3a86f2e347812570803a04`: 261 tests, hosted 67 contracts, lint/format/whitespace/diff, fresh V6-3/DP2 one-run regressions, four targeted cases x5 and six fresh real-tool regression builds. Evidence: `stabilization_7b788e58_ci.json`, `source_review_7b788e58.json`, `final_source_7b788e58.json`. All 56 positive and 72 interaction compositions pass, without final qualification credit. Fresh base/negative, all I1–I6 and eight structural five-run suites are requested on identical production. Actual class coverage, complete fresh native render inspection, final audits and PASS remain open.

## Visible pin-number native-render falsification — 2026-10-03

Fresh eight-case structural qualification `37109849527` passes x5 on production `7b788e58`, producer `7c475adc941596a5113f9076270a58cb64429306`; artifact `11270055020` preserves all evidence. Native structural render audit `37109981436`, job `111165824948`, transfers eight SHA-verified SVGs. Agent inspection of four structural renders identifies a hard readability defect: connector `INPUT`, `RETURN` and output aliases overlap visible pin number `1`. In `a0_interleaved`, native `INPUT` spans x=25.4000..31.1066 mm at y=107.6007 while pin `1` spans x=30.40865..31.82135 at y=107.5944. Actual glyphs overlap, producing the appearance `INPUT1`; body-only label clearance does not detect pin text. Preserve `native_render_defect_pin_number_7c475adc.svg` and `pin_number_render_falsification_7c475adc.json`. Source stabilization is reopened. The generic embedded-pin text clearance repair must pass complete tests and all required fresh qualifications before final-source completion. No final checkbox or planned class is promoted from this run.

### Bounded visible-number clearance repair

`fixtures/m2h2/finalization_checks/pin_number_clearance_repair_2026-10-03.json` binds all current source hashes and the preserved native falsification. The finite measured pin-number clearance and independent emitted-byte rejection pass 30 focused tests in 95.78s, including V6-8, DP4 and the prospective V4-7 gate. A broad square prototype caused width regressions; unconstrained bends caused multi-port net contacts, which were rejected and corrected. The final bounded alternatives preserve straight outward escapes for multiple ports and use an orthogonal single-port escape when needed. Full exact-source locked validation and all fresh final qualifications remain required. No final completion checkbox is promoted.

## Actual whole-band I3 closure implementation — 2026-10-03

The generic narrow timer escape and measured all-cell row now prove frozen `a3_one` with three active timers and **one all-noninterface band**, 205.707343 x 139.28 mm, within unchanged gates. All 56 positive and 72 interaction compositions, nine bounded structural searches, 28 focused tests and 56 contract/audit tests pass locally. Exact development records and source hashes: `fixtures/m2h2/finalization_checks/i3_whole_band_development_2026-10-03.json`. These are development proofs, not final real-tool qualification. The previous pin-repair head's locked CI passed 263 tests and all regression builds, but its static job failed formatting; repository 100-column formatting is corrected here. New source baseline and all final qualification/coverage/render/audit checkboxes remain open. Required structural qualification, render transfer and final artifact audits now require nine distinct cases, including `a3_one --bands 1` without the core-only flag. Preserved three-amplifier core-only evidence cannot close the whole-band cell.

## Local-construction ceiling falsification and repair — 2026-10-03

Exact instrumentation on frozen DP2 found 33 and 35 local proposals for package support cells, above the governing 32-proposal ceiling. A shared per-fragment ledger now counts accepted and rejected body/support/access proposals, stops before proposal 33 and exposes budget-uncovered and retention-uncovered classes. Failure before packing preserves its rejection ledger and earlier completed fragments. Exact development evidence: `fixtures/m2h2/finalization_checks/local_construction_budget_2026-10-03.json`. Original current-master regressions for I1 `d2_b3`, `d3_b3` and I3 selected triple are restored after snapshot restoration omitted them. All original assertions remain intact.

- [x] Confirm local-construction proposals never exceed 32 per fragment, including rejected proposals, and exact budget/retention-uncovered classes are recorded on current source. Evidence: `fixtures/m2h2/finalization_checks/stabilization_1273d6af_ci.json`, complete 270-test baseline including both local-construction budget/failure-ledger regressions.

Predecessor baseline `37113559365` passes all jobs and five actual whole-band builds, but cannot close final-source gates after this budget/evidence behavior change. Fresh source baseline and qualification remain required; no stale or local-only evidence is promoted.

## Native power-source glyph clearance — 2026-10-03

Current-source baseline `37114227421` on `354efedab75f7af017019d41d1eefa59e6d27d99` passes all jobs: locked job `111177784156` has 266 passing tests, V6-3/DP2 real-tool regressions, target five-run regressions and five actual whole-band `a3_one` builds; hosted `111177784262` and static `111177784266` pass. This baseline confirms the shared local-construction ceiling and restored original regression inventory, but is superseded for final-source qualification by the glyph-clearance behavior change below.

Actual native inspection of preserved `fixtures/m2h2/interaction_alternatives/a3_one_three_amplifier_candidate1/run1/renders/schematic/M2h2I3ThreeAmplifierOneBand.svg` finds the PWR_FLAG diamond over the first letter of VPLUS. The source marker was placed at the same label anchor with a symmetric one-pitch planner box; the locked glyph extends two pitches above its electrical pin. This is historical native falsification evidence, not current qualification credit.

The generic repair uses the actual locked PWR_FLAG body, finite existing same-net contacts and 0/180-degree orientations. It moves no electrical contact off its existing conductor, adds no wires and changes no route budget. Actual source-glyph extents are reserved. Independent emitted-byte layout observation now includes source bodies and rejects their collisions with labels, required fields and other bodies. `tests/test_m2h2_source_marker.py` includes measured orientation and an independent embedded-glyph collision negative. Exact evidence: `fixtures/m2h2/finalization_checks/source_marker_clearance_2026-10-03.json`.

Fresh complete baseline, full final-source qualification, native render inspection, coverage and audits remain required. No final checkbox is promoted from this development slice.

### Preserve electrical negative-control diagnostics

Baseline `37123582246` on `bdcbde14` passes static/hosted checks and 266 full tests, with two diagnostic-order regressions: preserved electrical negatives encountered a historical source-marker readability defect first. All historical files and negative assertions remain unchanged. Mandatory source-glyph/label rejection is reordered after electrical motif checks and before final label checks/return. The native negative now reads actual historical schematic/XML bytes. Four focused tests pass. Exact witness: `fixtures/m2h2/finalization_checks/source_marker_diagnostic_order_2026-10-03.json`. All 56 positive, 72 interaction and nine structural development compositions pass. Fresh complete baseline remains required.

## Current source stabilization and fresh qualification trigger — 2026-10-03

Exact head `94e8b4bc45242a1e834a1ae1a123d0717a589a6c` passes all jobs of `37123857550`: 268 tests, V6-3/DP2, four targeted five-run cases, five true whole-band `a3_one` builds and six additional locked regressions. Artifact `11274093988`, ZIP SHA-256 `0affa2d491efd471d15e5db76ce748fd68fb5767229077bd89875e3b2d718d15`, preserves exact evidence. `final_source_94e8b4bc.json` freezes all 19 production hashes, four runner hashes and three locks. The trigger commit changes reports only and requests the complete final-source qualification suite. All full qualification, actual coverage, reproducibility, native inspection and final audit gates remain open.

## Source-glyph attached-wire falsification — 2026-10-03

The full source `94e8b4bc` baseline passes 268 tests and locked regressions, and fresh structural run `37124244387` qualifies all nine cases x5 on producer `f2628c9c7b5b26060774d883a2e9de23402d2392`. These are preserved machine evidence and are superseded by this additional repair.

Exact DP2 source geometry places `flag.1` at (109.22,110.49) mm with a 180-degree source glyph extending to y=113.03 mm, while the attached vertical wire continues to (109.22,114.30) mm. The wire passes through the diamond. A source-attached wire was exempted by the ordinary component-pin endpoint body rule. The generic placement now rejects all wire intersections with the measured source glyph interior, uses finite existing same-net canonical vertices when label/gateway contacts do not clear, and adds no wires or conductor length. Independent emitted-byte source-glyph wire rejection runs after electrical diagnostic gates and has no endpoint exemption. The historical electrical negatives remain unchanged. Exact witness: `fixtures/m2h2/finalization_checks/source_glyph_wire_clearance_2026-10-03.json`.

Source stabilization and all affected final-source qualification gates are reopened. Supersede ongoing prior-source qualifications; no old five-run or native-render result is promoted for the new source.

## Wire-clear stabilized source and qualification trigger — 2026-10-03

Exact source `1273d6af219475db5fc804d487d06e8fb6fa8c69` passes all jobs of `37124948961`: 270 tests in 146.58s, fresh V6-3/DP2, targeted five-run cases, five actual whole-band builds and six additional locked regressions. Artifact `11275495312`, ZIP SHA-256 `04d34307cd8446c37d1dd82d469cb00481befc9147b0e414983935f68d8eeea1`, preserves complete evidence. The source and runner freeze is `final_source_1273d6af.json`. The report-only trigger requests fresh final qualification of all 56 positives x5, 72 interactions x5 and nine structural alternatives x5. All final qualification, actual coverage, reproducibility, native render inspection and audit gates remain open.

### Final audit input and stress-render preparation

The report-only audit workflow now points to current producer `5c7640a8d9a505a733f009f7a2c7cd1d6c2012b0`: base `37125376461`, interactions `37125376457`, structural `37125376451`. These runs remain pending; download and audit must not execute until all succeed. Native render transfer additionally includes all six I6 long-text branch/support stress cases for actual readability inspection. This changes audit/report presentation only; all 19 production source hashes and four qualification-runner hashes remain frozen in `final_source_1273d6af.json`. No final checkbox is promoted.


## Fresh interaction result — frozen source 1273d6af

Run `37125376457`, job `111209500807`, completed successfully on qualification producer `5c7640a8d9a505a733f009f7a2c7cd1d6c2012b0`: all 72 cases accepted and reproducible across five distinct fresh builds (360 builds). Exact case/run references, measured selected structures, artifact ID and ZIP digest are recorded in `fixtures/m2h2/finalization_checks/interaction_5c7640a8_ci.json`. This is current-source locked-KiCad evidence. Coverage closure still requires the final independent artifact audit and actual I3 band classification; render inspection and remaining base/structural qualification are pending. No pending gate is checked from CI success alone.


## Native worksheet-border falsification — 2026-10-03

The source-1273 structural `a3_one` native SVG, obtained through run `37126310097` from successful five-run qualification `37125376451`, places `C5.Value=10u` across the locked KiCad worksheet title-block border. Exact native bytes and measured coordinates are preserved in `fixtures/m2h2/finalization_checks/worksheet_native_falsification_2026-10-03.json` and its referenced SVG. Engineering inspection therefore falsifies the prior candidate despite accepted/reproducible machine results. Current-source baseline/freeze, qualification and inspection gates are reopened.

The repair preserves the original packing origin for unaffected layouts and translates only measured worksheet-colliding complete packings upward by a finite grid displacement. Composer and independent emitted-symbol observer reject worksheet overlap, including rotated passive fields and wires. No topology, spread, path, length, ERC or evidence gate is weakened. Fresh locked-KiCad qualification remains mandatory.


## Worksheet-clear source freeze and fresh qualification — 2026-10-03

Production source `f161672f761559e0e8ae7294f1c4df39fa24bebb` is stabilized: 271 complete locked-runner tests passed in 145.14s in run `37127192673`; static job `111214830860`, hosted contract job `111214831072`, locked job `111214831140` all succeeded. Locked real V6-3/DP2, four targeted ×5 probes, true whole-layout `a3_one` ×5, and additional regressions passed. Exact current evidence: `fixtures/m2h2/finalization_checks/stabilization_f161672f_ci.json`; all 19 source hashes, four runners and three locks: `fixtures/m2h2/finalization_checks/final_source_f161672f.json`; generic source review: `fixtures/m2h2/finalization_checks/source_review_f161672f.json`.

Fresh 56-positive, 72-interaction and nine-structural five-run qualification is requested under separate roots tied to the new producer head. Older 5c7640a8 candidate success is historical falsification evidence, not final-source completion evidence. Native inspection must verify the repaired C5/title-block separation and all remaining engineering gates.


### Fresh structural qualification and native worksheet review

`fixtures/m2h2/finalization_checks/structural_585a4f7c_ci_inspection.json` records successful run `37127602956`: all nine actual structural alternatives × five fresh locked-KiCad builds, plus exact native SVG SHA-256 verification and engineering/agent inspection of every structural scene. Actual new `a3_one` C5 value is clear of the worksheet border; all-noninterface one-band evidence remains distinct from core-only three-amplifier evidence. Full base/interaction coverage, remaining renders and final independent audit are still pending.

Final audit workflow inputs are repointed to the live producer `585a4f7c96b185c3a4e9db73fa13960388ea411b`, base run `37127602948`, interaction run `37127602933`, structural run `37127602956`. The final audit will be triggered only after all three succeed; no pending evidence gate is closed by preparation.
