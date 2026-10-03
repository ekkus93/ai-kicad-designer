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

- [x] Run current fast complete pytest baseline. Evidence: `fixtures/m2h2/finalization_checks/stabilization_8675431f_ci.json`: exact source `8675431f76594fd51c591180f0bba85ece942c9f`, run `37071729309`, locked job `111052498258`, 246 passed in 99.94s.
- [x] Run scoped Ruff lint. Evidence: exact-head `M2h2 Fast Validation` run `37071729309`, static job `111052498198`, source `8675431f76594fd51c591180f0bba85ece942c9f`, Ruff lint.
- [x] Run scoped Ruff format check. Evidence: exact-head `M2h2 Fast Validation` run `37071729309`, static job `111052498198`, source `8675431f76594fd51c591180f0bba85ece942c9f`, Ruff format.
- [x] Run `git diff --check` / applicable whitespace checks. Evidence: exact-head `M2h2 Fast Validation` run `37071729309`, static job `111052498198`, source `8675431f76594fd51c591180f0bba85ece942c9f`, Git diff check and scoped whitespace.
- [x] Confirm fresh V6-3 one-run real-tool regression. Evidence: `fixtures/m2h2/finalization_checks/stabilization_8675431f_ci.json`, fresh locked regression job `111052498258`.
  - [x] locked KiCad 10.0.6;
  - [x] independent electrical observation;
  - [x] zero unexpected ERC;
  - [x] serialized-scene verification;
  - [x] canonical VREF <= 250 mm.
- [x] Confirm fresh DP2 one-run real-tool regression. Evidence: `fixtures/m2h2/finalization_checks/stabilization_8675431f_ci.json`, fresh locked regression job `111052498258`.
  - [x] no external VREF connector;
  - [x] two NE5532 packages;
  - [x] all required reference consumers connected;
  - [x] independent electrical observation;
  - [x] zero unexpected ERC;
  - [x] canonical VREF <= 250 mm.

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
- [x] V6-3 remains <= 250 mm canonical VREF without gate change or label shortcut. Evidence: `fixtures/m2h2/finalization_checks/stabilization_8675431f_ci.json`, fresh locked regression job `111052498258`.
- [x] DP2 internal VREF remains connectorless, fully distributed, and <= 250 mm. Evidence: `fixtures/m2h2/finalization_checks/stabilization_8675431f_ci.json`, fresh locked regression job `111052498258`.

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

- [ ] Freeze final-source interaction runner/tool hashes. Evidence: `fixtures/m2h2/finalization_checks/interaction_runner_hashes_fe7335d.json` freezes the current interaction runner, qualification/structural-alternative runners, frozen manifest/coverage ledger, probe generator, active composition/routing inputs, and validation workflow at exact head `fe7335d56284babad26dd531bb7229607fa1213a`; any listed behavior-affecting change invalidates the freeze. The cited freeze is stale after later source/runner changes; refresh at stabilization.
- [x] Coverage result records actual observed structural class, not requested factor labels only. Evidence: `tools/run_m2h2_i1.py::observed_structural_class` derives the selected seed/round, placement class, and proved structure from composition evidence and records only a five-run-stable observed class; `tests/test_m2h2_interaction_runner.py::test_observed_structural_class_uses_selected_run_evidence_not_requested_label` passed in exact-head GitHub Actions run `36517979598`, job `M2h2 contract pytest on hosted runner` (`109244434910`) at `0e6f29f42f8772af20f7ba1eae3929a93c37d162`.
- [x] Every covered cell links to real-tool qualification evidence. Evidence: `tools/run_m2h2_i1.py::validate_coverage_ledger_evidence` requires every covered cell to include `real_tool_qualification_evidence` with schema `m2h2.real-tool-evidence.1`, locked KiCad 10.0.6, exact source head, qualification root/results path, case ID, and nonempty run paths; `tests/test_m2h2_interaction_runner.py::test_current_coverage_ledger_has_no_invalid_evidence_records` and `tests/test_m2h2_interaction_runner.py::test_covered_cells_require_real_tool_evidence_not_parse_or_generation_only` passed in exact-head GitHub Actions run `36560904459`, job `M2h2 contract pytest on hosted runner` (`109381262073`) at `239c7d4afe86f78f955f6524b8aeb050a5b5a0bd`.
- [x] Impossible cells require semantic impossibility witnesses, not layout failures. Evidence: `tools/run_m2h2_i1.py::validate_coverage_ledger_impossibilities` requires unsupported cells to include a semantic witness with schema `m2h2.semantic-impossibility.1`, kind `semantic_impossibility`, semantic source, and proof text while rejecting layout/build/routing/tool failure keys; `tests/test_m2h2_interaction_runner.py::test_unsupported_cells_require_semantic_impossibility_not_layout_failure` passed in exact-head GitHub Actions run `36560904459`, job `M2h2 contract pytest on hosted runner` (`109381262073`) at `239c7d4afe86f78f955f6524b8aeb050a5b5a0bd`.

- [x] Reject one-run, repeated-run, empty-run-link, and non-SHA coverage records. Evidence: `tests/test_m2h2_interaction_runner.py::test_real_tool_coverage_rejects_incomplete_or_repeated_runs` (five parameterized negatives), current-source hosted contract job `110976476137`, run `37048718582` at `465248ba47fe0d124ecd7997f2cdf898095b1d35`.

### 6.2 I1

- [ ] Qualify every required I1 cell on final source.
- [ ] Qualify selected I1 triple(s).
- [ ] Verify terminal/electrical/ERC/layout/path/order invariants.
- [ ] Reconcile I1 covered cells in `development/interaction_coverage.json`.

### 6.3 I2

- [ ] Qualify every required I2 cell on final source.
- [ ] Qualify selected I2 triple(s).
- [ ] Verify internal-reference/parked/shunt-return obligations.
- [ ] Reconcile I2 covered cells.

### 6.4 I3

- [ ] Qualify every required I3 electrical/path case on final source.
- [ ] Qualify all required actual shelf/band structural classes.
- [ ] Re-run required structural alternatives on final source.
- [ ] Qualify selected I3 triple(s).
- [ ] Reconcile I3 covered cells from actual class evidence.

### 6.5 I4

- [ ] Qualify every required I4 cell on final source.
- [ ] Qualify selected I4 triple(s).
- [ ] Verify unequal-consumer/cross-fragment/sibling-order invariants.
- [ ] Reconcile I4 covered cells.

### 6.6 I5

- [ ] Qualify every required I5 cell on final source.
- [ ] Qualify selected I5 triple(s).
- [ ] Verify 3+ gateway distribution/multiple-shelf/restricted-entry invariants.
- [ ] Reconcile I5 covered cells.

### 6.7 I6

- [ ] Qualify every required I6 shared-package/reference cell on final source.
- [ ] Qualify required text-stress × support-count cells.
- [ ] Qualify required text-stress × branch-degree cells.
- [ ] Reconcile I6 covered cells.

### 6.8 Coverage completion

- [ ] Every required I1–I6 cell is covered or has a valid semantic impossibility witness.
- [ ] Every selected triple is covered or has a valid semantic impossibility witness.
- [ ] Coverage ledger contains no cell marked complete from parse/generation success alone.

## 7. Source stabilization

- [ ] Finish all behavior-affecting code/test changes.
- [ ] Complete pytest passes.
- [ ] Scoped Ruff lint passes.
- [ ] Scoped Ruff format check passes.
- [ ] `git diff --check` passes.
- [ ] Applicable whitespace/link checks passes.
- [ ] Record stabilized final source hashes.
- [ ] Create fresh `qualification_final_candidateN` root tied to exact stabilized source.
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

- [ ] Run required final-source interaction qualification roots for I1–I6.
- [ ] Run required selected triples.
- [ ] Run required final-source structural alternatives.
- [ ] Run required long-field/stress derivatives.
- [ ] Five-run reproducibility passes for every governed interaction/stress case.
- [ ] No interaction/stress evidence relies solely on pre-final-source runs.

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
