# M2h2 Finalization Specification — 2026-09-27

## 1. Purpose

This document defines the execution plan for completing **M2h2** from the current repository state described by `docs/M2H2_HANDOFF_2026-09-27.md` and `fixtures/m2h2/STATUS.md`.

This is not a new schematic-layout architecture. The governing technical contract remains `docs/M2_GENERALIZATION_REMEDIATION_SPEC.md`. The purpose of this finalization plan is narrower:

> Turn the current partially implemented M2h2 state into a fully falsified, interaction-covered, reproducibly qualified, evidence-complete **M2h2 PASS** on one stabilized final source tree.

Current one-run evidence already shows V6-3 and DP2 can pass the locked KiCad 10.0.6 flow at the present implementation. The remaining work is contract completion/falsification, structural and routing closure, interaction coverage, final-source qualification, reproducibility, render inspection, audits, and evidence reconciliation.

## 2. Authority

Use these documents in this order:

1. `docs/M2_GENERALIZATION_REMEDIATION_SPEC.md` — governing technical requirements and M2h2 completion criteria.
2. `docs/M2H2_FINALIZATION_SPEC_2026-09-27.md` — execution sequence and closure rules.
3. `docs/M2H2_FINALIZATION_TODO_2026-09-27.md` — canonical executable checklist and source of completion truth.
4. `docs/M2H2_HANDOFF_2026-09-27.md` — continuation state and verified current evidence.
5. `fixtures/m2h2/STATUS.md` — material working status.

If this finalization document conflicts with a hard technical requirement in the governing remediation specification, the governing remediation specification wins.

## 3. Hard boundaries

M2h2 finalization must preserve all of the following:

- M2h2 only. Do not begin M3.
- Do not create, reserve, author, or run corpus.v7.
- Do not introduce CP-SAT.
- Do not alter the hard 210 × 140 mm spread/page gate.
- Do not alter the 80 mm local-path gate.
- Do not alter the 60 mm support/locality gate where applicable.
- Do not alter the 250 mm canonical conductor-length gate.
- Do not weaken ERC or independent emitted-artifact observation.
- Do not add benchmark-specific geometry based on fixture IDs, design IDs, topology hashes, exact inventories, refdes, or literal net names.
- Preserve DP1–DP4 topology and frozen expectations.
- Preserve all historical blind/evaluation evidence.
- Ignore `.local/`.
- Do not inspect or use `research/legacy_openclaw/`.
- Use locked KiCad **10.0.6** for real-tool qualification.
- Work directly on `master`; no per-task branch/PR churn.
- Use the authenticated local GitHub CLI/API and this project's self-hosted runner for GitHub/repository/CI operations. The ChatGPT-only Ralph Bridge is not part of the computer-side workflow.

## 4. Current baseline

At the handoff source state:

- fresh one-run V6-3 passes locked KiCad 10.0.6, independent electrical observation, zero ERC, serialized-scene verification, and canonical VREF union **234.95 mm**;
- fresh one-run DP2 passes the same gates with no external VREF connector, two NE5532 packages, one connected VREF component, nine physical reference terminals, and canonical VREF union **247.65 mm**;
- complete pytest passes **195 tests**;
- scoped Ruff lint/format, `git diff --check`, and scoped whitespace checks pass;
- historical protection audit passes for 7,221 tracked files;
- active M2 literal anti-overfitting scan reports no findings and no CP-SAT;
- `qualification_candidate4` proves the earlier implementation could qualify 56/56 positives over five runs, but its source hashes are stale and it is not final-source evidence;
- preserved I1–I6 evidence is substantial, but the frozen interaction coverage ledger still has zero formally covered cells because final-source class/invariant reconciliation is incomplete.

These facts are starting evidence, not final qualification.

## 5. Execution phases

### Phase A — baseline and evidence integrity

Before behavior changes:

1. Reload the governing spec, this finalization spec, the TODO, handoff, and current status from `master`.
2. Record current `master` SHA and relevant source hashes in a fresh finalization evidence root.
3. Verify historical evidence protection hashes.
4. Verify DP1–DP4 frozen manifests and the interaction coverage plan have not changed.
5. Run the fast current-source baseline needed to establish a trustworthy starting point.
6. Record that older qualification candidates are provisional/non-final when source hashes differ.

Do not spend time on the full five-run final qualification in this phase.

### Phase B — obligation-complete pre-emission contract closure

Audit and complete the pre-emission certificate against every requirement in `M2_GENERALIZATION_REMEDIATION_SPEC.md`.

Before successful `.kicad_sch` emission, the exact immutable candidate must prove at least:

- exactly one geometry owner per symbol occurrence;
- complete physical terminal accounting;
- every semantic obligation accounted for;
- exact gateway-to-real-pin witnesses for every required routed terminal;
- one complete canonical same-net conductor graph for each required net;
- no disconnected same-net islands;
- no unintended dangling route endpoints;
- correct junction-degree and crossing semantics;
- all signal precedence inequalities;
- 80 mm local-path bounds;
- 60 mm support/locality bounds where applicable;
- 210 × 140 mm page/spread feasibility;
- body/text/reservation/corridor legality;
- 250 mm canonical conductor-length bounds;
- exact serialized-scene identity matching the certified scene.

A failed certificate must prevent successful schematic emission.

The independent post-emission observer remains authoritative and must not consume the generator certificate as proof.

Required falsification includes independently authored graph traversal/oracle cases, tiny exhaustive placement enumeration for bounded synthetic layouts, exact-boundary tests, off-pin/stale-gateway mutations, disconnected-island mutations, split/unsplit conductor metamorphics, label-only protected-path negatives, unauthorized crossing/junction negatives, late serialization mutations, and set-order/refdes/net-name metamorphics.

### Phase C — structural search, routing, and typed repair closure

Finish the generic behavior required by the governing specification:

- conductor alternatives represent genuinely different legal trees/topologies;
- lower bounds remain sound for signal, power, reference, support, and shared control/distributive nets;
- internal generated references do not require fake external connectors;
- corridor/reservation capacity is checked before route acceptance;
- typed conflicts cover detour/canonical length, local span, signal order, blocked gateway/access, reservation/collision, envelope growth, and disconnected-net/island conditions represented by the repair model;
- repair dispatch uses typed state, not parsed human-readable diagnostic strings;
- every repair produces a genuinely changed candidate state;
- repeated/no-op states are deduplicated and do not masquerade as new exploration;
- budget counters never silently reset;
- evidence records meaningful structural/variant diversity, exact attempts, and best rejected candidate/failure witness.

V6-3 and DP2 must remain green under unchanged gates.

### Phase D — interaction coverage I1–I6

For every required I1–I6 cell and selected triple:

1. run final-source qualification;
2. verify exact terminal/package/unit/pin identity;
3. verify expected electrical partitions;
4. require zero unexpected ERC violations;
5. verify layout/path/signal-order/locality bounds;
6. verify required reference/supply distribution;
7. record actual structural/band class;
8. link real-tool evidence;
9. mark a cell covered only when all expected invariants pass.

For I3, validate actual band classes, not requested labels. Structural alternatives count only when the final-source real layout demonstrates the intended class.

If a cell is semantically impossible, record a genuine semantic impossibility witness. An implementation/layout failure is not an impossibility witness.

The final coverage ledger must show complete required coverage for each row and selected triple; do not hide a missing row behind one aggregate percentage.

### Phase E — source stabilization

Before final qualification:

1. finish all behavior-affecting implementation/test changes;
2. run the complete active test/lint/format/check suite;
3. record final source hashes;
4. create a new final qualification candidate root;
5. treat any later behavior-affecting source change as invalidating affected final qualification evidence.

### Phase F — final-source qualification and reproducibility

Run a fresh final qualification against the stabilized source. Do not overwrite candidate4 or historical roots.

Required base qualification includes:

- all **56 positive** M2h2 cases defined by the governing program;
- five clean builds per positive;
- historical invalid V3-8 as a negative;
- required interaction/stress cases and final structural alternatives needed to close the interaction coverage ledger.

For every required positive, use locked KiCad 10.0.6 and require:

- compiler-owned project bytes as governed;
- exact physical package/unit/pin identity;
- fresh independent electrical partitions;
- zero unexpected ERC violations;
- local variant choices;
- canonical conductor trees;
- obligation certificates;
- structural candidate/repair decisions;
- complete layout metrics;
- normalized SVG geometry/text;
- normalized reports/manifests using only existing documented path/time/title normalization.

Do not normalize away variant choices, candidate/repair differences, conductor-tree differences, or failed-proof differences.

Any behavior-affecting source change during this phase requires a fresh final qualification candidate.

### Phase G — engineering inspection, audits, and closure

After final-source machine qualification passes:

1. inspect fresh final renders for signal ordering, timing/feedback clarity, reference distinction, package/support association, fanout traceability, and required-field readability;
2. explicitly record this as engineering/agent inspection, not human approval;
3. report worst observed metrics, component/terminal coverage, local/global tree lengths, structural/variant diversity, exact budgets, best rejected candidates, and prediction-versus-observation deltas;
4. run complete pytest;
5. run scoped Ruff lint and format checks;
6. run `git diff --check` and scoped whitespace checks;
7. run applicable link checks;
8. run historical evidence integrity audit;
9. run literal and structural anti-overfitting audits;
10. confirm CP-SAT remains absent;
11. reconcile `fixtures/m2h2/STATUS.md` and the canonical TODO from actual final evidence.

Only after every governing completion criterion is satisfied may the status be **M2h2 PASS**.

## 6. Ralph Loop operating contract

At the start of every Ralph run:

1. reload from current `master`:
   - `docs/M2_GENERALIZATION_REMEDIATION_SPEC.md`;
   - `docs/M2H2_FINALIZATION_SPEC_2026-09-27.md`;
   - `docs/M2H2_FINALIZATION_TODO_2026-09-27.md`;
   - `docs/M2H2_HANDOFF_2026-09-27.md`;
   - `fixtures/m2h2/STATUS.md`;
2. inspect current master SHA/state with local Git and inspect relevant CI through the authenticated GitHub CLI/API; confirm the project's self-hosted runner and locked KiCad toolchain are available;
3. select the earliest actionable unchecked TODO item while advancing independent qualification/audit work concurrently when safe;
4. prefer completing/fixing existing M2h2 work over duplicating it.

Do not stop merely because of a test failure, lint/format failure, packing/routing failure, interaction-cell failure, qualification failure, CI still running, bounded CI polling timeout, safe compare-and-swap race, implementation bug, or stale provisional evidence. Diagnose, fix, rerun, and continue.

A valid user blocker exists only for unavailable credentials/authorization, unavailable required hardware/toolchain that cannot be provisioned under current authority, a destructive/external action requiring user approval, or concrete evidence that the governing specification is contradictory/impossible without violating another hard invariant.

After each coherent completion slice:

- reconcile TODO checkboxes only from current-source evidence;
- add exact evidence references;
- update `fixtures/m2h2/STATUS.md` only for material status changes;
- commit coherent code/tests/evidence/TODO reconciliation directly to `master` using exact-head compare-and-swap semantics and the authenticated local GitHub workflow.

## 7. Evidence roots

Never overwrite historical/provisional roots.

Use fresh finalization/final qualification roots beneath `fixtures/m2h2/`, for example:

- `fixtures/m2h2/finalization_checks/`
- `fixtures/m2h2/interaction_qualification_*_final_candidateN/`
- `fixtures/m2h2/qualification_final_candidateN/`

Every final evidence root must record:

- exact Git/source hashes;
- toolchain/asset/policy hashes;
- exact command/profile identity;
- run counts;
- normalization contract;
- per-case outcomes;
- attempts/budgets/failure witnesses where applicable.

## 8. Definition of M2h2 PASS

M2h2 is PASS only when all of the following are true on one stabilized final source state:

1. all generic obligation/certificate requirements are implemented and falsified;
2. independent graph and tiny placement oracles pass positive and negative tests;
3. structural search/routing/typed repair requirements are implemented and tested;
4. V6-3 and DP2 remain green with unchanged gates;
5. every required I1–I6 cell and selected triple is evidence-backed covered or has a valid semantic impossibility witness;
6. the required final-source 56-positive five-run qualification passes;
7. historical V3-8 remains correctly rejected;
8. all required interaction/stress/final structural-alternative qualification passes;
9. five-run reproducibility passes for all governed outputs/evidence;
10. final renders receive required engineering inspection with no unresolved hard defect;
11. complete pytest/lint/format/diff/whitespace/link audits pass as applicable;
12. historical evidence integrity passes;
13. literal and structural anti-overfitting audits pass;
14. CP-SAT remains absent;
15. `fixtures/m2h2/STATUS.md` is reconciled to final evidence;
16. `docs/M2H2_FINALIZATION_TODO_2026-09-27.md` is fully checked with evidence references.

After PASS, stop. Do not create corpus.v7 and do not begin M3.
