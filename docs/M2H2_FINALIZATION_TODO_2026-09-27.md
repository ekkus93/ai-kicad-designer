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

- [ ] Run current fast complete pytest baseline.
- [x] Run scoped Ruff lint. Evidence: GitHub Actions `M2h2 Fast Validation` run `36478515556`, job `static lint / format / diff-check` (`109118128135`), exact head `8ac13a665aef36bfb4241289be7a1d34fc4c568b`, step `Ruff lint`.
- [x] Run scoped Ruff format check. Evidence: GitHub Actions `M2h2 Fast Validation` run `36478515556`, job `static lint / format / diff-check` (`109118128135`), exact head `8ac13a665aef36bfb4241289be7a1d34fc4c568b`, steps `Ruff format check m2_compose`, `Ruff format check src remainder`, `Ruff format check test_m2h2_repair_matrix`, `Contracts format diff lines 1-200` through `801-900`, `Ruff format check key M2 tests`, `Ruff format check remaining tests`, and `Ruff format check tools`.
- [x] Run `git diff --check` / applicable whitespace checks. Evidence: GitHub Actions `M2h2 Fast Validation` run `36478515556`, job `static lint / format / diff-check` (`109118128135`), exact head `8ac13a665aef36bfb4241289be7a1d34fc4c568b`, steps `Git diff check` and `Scoped trailing-whitespace check`.
- [ ] Confirm fresh V6-3 one-run real-tool regression:
  - [ ] locked KiCad 10.0.6;
  - [ ] independent electrical observation;
  - [ ] zero unexpected ERC;
  - [ ] serialized-scene verification;
  - [ ] canonical VREF <= 250 mm.
- [ ] Confirm fresh DP2 one-run real-tool regression:
  - [ ] no external VREF connector;
  - [ ] two NE5532 packages;
  - [ ] all required reference consumers connected;
  - [ ] independent electrical observation;
  - [ ] zero unexpected ERC;
  - [ ] canonical VREF <= 250 mm.

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
- [ ] V6-3 remains <= 250 mm canonical VREF without gate change or label shortcut.
- [ ] DP2 internal VREF remains connectorless, fully distributed, and <= 250 mm.

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

- [x] Freeze final-source interaction runner/tool hashes. Evidence: `fixtures/m2h2/finalization_checks/interaction_runner_hashes_f64f31c.json` records exact head `f64f31c149ca33db4c9ad1c81ad14fa14010a7c9`, interaction runner/generator/tool Git blob hashes, frozen manifest/coverage-plan blobs, active source module blobs, and validation workflow blobs. This is a current-source hash freeze only; it does not mark any coverage cell complete and must be replaced if listed behavior-affecting inputs change before final interaction qualification.
- [ ] Coverage result records actual observed structural class, not requested factor labels only.
- [ ] Every covered cell links to real-tool qualification evidence.
- [ ] Impossible cells require semantic impossibility witnesses, not layout failures.

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
- [ ] Historical invalid V3-8 remains correctly rejected.

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
