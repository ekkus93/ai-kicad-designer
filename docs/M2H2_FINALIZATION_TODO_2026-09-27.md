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

- [ ] Confirm M2h2-only scope: no M3, no corpus.v7, no CP-SAT.
- [ ] Confirm unchanged hard gates: 210 × 140 mm spread, 80 mm local path, 60 mm support/locality where applicable, 250 mm canonical conductor length.
- [ ] Confirm `.local/` is ignored and `research/legacy_openclaw/` is not inspected/used.
- [ ] Confirm Ralph Bridge is used for all GitHub/repository/CI state and writes.
- [ ] Confirm direct `master` workflow with no per-task branch/PR churn.
- [ ] Record current `master` SHA and relevant source hashes in a fresh finalization evidence root.
- [ ] Verify historical blind/evaluation evidence integrity before behavior changes.
- [ ] Verify frozen DP1–DP4 manifest/topology and interaction coverage plan are unchanged.
- [ ] Record `qualification_candidate4` as provisional/non-final because source hashes are stale.

## 1. Current-source baseline

- [ ] Run current fast complete pytest baseline.
- [ ] Run scoped Ruff lint.
- [ ] Run scoped Ruff format check.
- [ ] Run `git diff --check` / applicable whitespace checks.
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

- [ ] Exactly one geometry owner per symbol occurrence is certified.
- [ ] Complete physical terminal accounting is certified.
- [ ] Every semantic obligation is represented in the certificate.
- [ ] Exact gateway-to-real-pin witness exists for every required routed terminal.
- [ ] Every required net has one complete canonical geometric conductor graph.
- [ ] Disconnected same-net islands are rejected before successful emission.
- [ ] Unintended dangling route endpoints are rejected before successful emission.
- [ ] Junction degree and unrelated crossing semantics are certified.
- [ ] Every signal precedence inequality survives shelf/variant/translation/repack/compaction.
- [ ] 80 mm local-path limits are certified pre-emission.
- [ ] 60 mm support/locality limits are certified pre-emission where applicable.
- [ ] 210 × 140 mm spread/page limits are certified pre-emission.
- [ ] Reservation/body/text/corridor collision legality is certified pre-emission.
- [ ] 250 mm canonical conductor-length limits are certified pre-emission.
- [ ] Certified-scene digest matches the exact serialized in-memory scene.
- [ ] Failed certificate prevents successful `.kicad_sch` emission.

## 3. Generic falsification matrix

### 3.1 Independent graph/connectivity oracle

- [ ] Add/finish independently authored canonical-conductor graph oracle.
- [ ] Split and unsplit equivalent conductor graphs compare equal.
- [ ] Disconnected same-net islands fail.
- [ ] Label-only protected continuity fails.
- [ ] Unauthorized geometric crossing does not create connectivity.
- [ ] Missing/invalid T or four-way junction topology fails.
- [ ] Extra unintended dangling endpoint fails.
- [ ] Duplicate/foreign-owned conductor interval negative is covered.

### 3.2 Gateway/pin proof

- [ ] Exact gateway-to-pin attachment passes after legal translation.
- [ ] One-grid-unit off-pin endpoint fails.
- [ ] Stale transformed gateway fails.
- [ ] Wrong physical pin identity fails.
- [ ] Removed local escape segment fails.
- [ ] Legal conductor subdivision/translation preserves proof.

### 3.3 Tiny exhaustive placement oracle

- [ ] Implement bounded exhaustive synthetic placement oracle/enumeration.
- [ ] Planner accepts when exhaustive oracle finds a legal arrangement.
- [ ] Planner reports bounded infeasibility when no legal arrangement exists.
- [ ] Precedence/non-overlap/locality outcomes are compared independently of planner implementation.

### 3.4 Exact-boundary tests

- [ ] 80 mm local path exact boundary passes.
- [ ] 80 mm plus one coordinate unit fails.
- [ ] 60 mm support/locality exact boundary passes where applicable.
- [ ] 60 mm plus one coordinate unit fails where applicable.
- [ ] 210 × 140 mm exact spread boundary passes when otherwise legal.
- [ ] Above 210 mm or 140 mm fails.
- [ ] 250 mm canonical conductor exact boundary passes.
- [ ] Above 250 mm fails.

### 3.5 Metamorphic/serialization tests

- [ ] Set-like IR ordering does not alter governed decisions/output.
- [ ] Legal refdes renaming does not alter semantic geometry except legitimate text-envelope effects.
- [ ] Net-name renaming does not alter role-based routing decisions.
- [ ] Equivalent segment subdivision does not alter observed connectivity.
- [ ] Late coordinate/text/wire mutation after certification invalidates serialized-scene verification.

## 4. Structural search and routing closure

- [ ] Conductor alternatives are genuinely different tree/topology structures.
- [ ] Canonical lower bounds are sound for signal nets.
- [ ] Canonical lower bounds are sound for power nets.
- [ ] Canonical lower bounds are sound for reference/internal-reference nets.
- [ ] Canonical lower bounds are sound for support/shared-control/distributive nets.
- [ ] Corridor/reservation capacity is checked before route acceptance.
- [ ] Best rejected candidate and exact failure witness are preserved on every failure exit.
- [ ] Evidence reports meaningful structural/variant diversity, not raw attempt count only.
- [ ] V6-3 remains <= 250 mm canonical VREF without gate change or label shortcut.
- [ ] DP2 internal VREF remains connectorless, fully distributed, and <= 250 mm.

## 5. Typed repair closure

- [ ] Typed detour/canonical-length conflict produces a genuinely changed candidate.
- [ ] Typed local-span conflict produces a genuinely changed candidate.
- [ ] Typed signal-order conflict produces a genuinely changed candidate.
- [ ] Typed blocked-gateway/access conflict produces a genuinely changed candidate.
- [ ] Typed reservation/collision conflict produces a genuinely changed candidate.
- [ ] Typed route/envelope-growth conflict produces a genuinely changed candidate.
- [ ] Typed disconnected-net/island conflict is handled where represented by the current repair model.
- [ ] Repair dispatch does not parse human-readable error strings.
- [ ] No-op/repeated candidate states are deduplicated.
- [ ] No-op states do not consume budget as new structural exploration.
- [ ] Candidate/repair budget counters never silently reset.
- [ ] Exact attempted-state diversity is recorded in evidence.

## 6. Interaction coverage I1–I6 — final source

### 6.1 Coverage infrastructure

- [ ] Freeze final-source interaction runner/tool hashes.
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
- [ ] Applicable whitespace/link checks pass.
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
