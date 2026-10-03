# M2h2 development status — INCOMPLETE

The governing requirements are in `docs/M2_GENERALIZATION_REMEDIATION_SPEC.md`.
Development probes and their expectations remain frozen in `development/`.
Historical blind evidence is unchanged. Do not interpret the evidence below as
final qualification of the current worktree.

## Current implementation slice — 2026-10-02

Source `465248ba47fe0d124ecd7997f2cdf898095b1d35` adds terminal-backed external signal-source precedence
when a net has signal inputs and no internal signal producer or reference/supply
role. It preserves incomparable siblings. Measured shelf ordering places the
source interface band before its consumers; partial beam placement retains its
core expansion schedule and checks the exact source inequality when both ends
are assigned. External interfaces do not create a new functional-fragment local
span obligation. No fixed gate, ERC rule, observer, frozen probe, or historical
evidence was changed.

Coverage evidence validation now rejects fewer than five distinct run links,
empty/repeated links, and non-full source SHAs. Interaction results record source,
runner, and lock hashes. Qualification tools emit per-case evidence summaries.

At this source, hosted contract job `110976476137` and static job `110976476016`
in run `37048718582` pass. Locked complete pytest and V6-3/DP2 regressions remain
pending. Five-run interactions `37048500822` and 56-positive qualification
`37048500798` target `260e33c`; the intervening source change is qualification
report formatting only. The source-precedence fix is not yet reconciled as a
real-tool pass. The old baseline below is historical after these behavior changes.

## Previous source baseline — 2026-10-02

At source `563de7bbd79cf232cdb3a16069a5e6f2dd93405a`, exact-head fast-validation run
`36891578571` completed successfully. Locked self-hosted job `110468241407`
verified KiCad 10.0.6 executable/library hashes and the locked platform,
passed all 225 pytest tests, and passed both V6-3 and DP2 one-run regressions.
The regression harness verifies independent electrical observation, zero ERC,
serialized-scene identity, one reference component, and the unchanged 250 mm
canonical reference limit; DP2 also verifies two NE5532 packages, nine reference
terminals, and no external reference connector. Artifact `11176333918` preserves
the generated reports. This supersedes the historical missing-AppDir blocker.

Hosted static and contract jobs also passed. Final qualification and interaction
work remain incomplete: final jobs at this head were skipped, and the previous
interaction run `36861301231` failed. No old five-run candidate or provisional
interaction evidence is promoted to final-source PASS. The interaction runner
hash freeze must be refreshed after all behavior changes.

Evidence summary: `finalization_checks/baseline_563de7b_ci.json`.

## Current implementation and checks

The worktree implements generic internal-reference producer selection and
gateway distribution, alternative conductor trees with canonical-union length
pruning, bounded structural placement alternatives, typed conflicts and repairs,
reservation allocation witnesses, net/component proofs, and a serialized-scene
digest. These mechanisms still need the full falsification and qualification
specified by the remediation document.

Current-source unit coverage now includes the structural route lower-bound role
matrix and the remaining typed repair categories represented by the current
repair model: reservation, collision, route/envelope growth, net connectivity,
and dangling endpoint/island conflicts. Additional structural-routing evidence
covers global-route channel capacity rejection, meaningful structural-diversity
reporting in composition evidence, and failure-exit preservation of candidate
decisions plus exact typed failure witnesses. The obligation certificate is now
covered by a focused current-source witness export audit for unique ownership,
complete semantic-obligation inventory, terminal inventory, complete required
net-graph witnesses, gateway witnesses, placement witnesses, page spread,
reservation/collision legality, canonical conductor lengths, certified-scene
digests, and stale-certificate emission rejection. This is contract evidence
only, not final real-tool qualification.

A fast GitHub Actions workflow exists at
`.github/workflows/m2h2-fast-validation.yml` to produce exact-head hosted Ruff,
format, `git diff --check`, scoped whitespace, M2h2 contract pytest, and locked
self-hosted full-pytest evidence. The locked self-hosted job also runs
`tools/run_m2h2_current_regressions.py`, which produces one-run V6-3 and DP2
current-source regression evidence and uploads it as
`m2h2-current-regressions-${{ github.sha }}`. The hosted static job now also runs
`tools/run_m2h2_structural_audit.py`, a structural anti-overfitting audit for
active M2 production-module control flow. The audit flags benchmark-specific
literals and literal net/refdes dispatch in active production modules; final
source still requires exact-head CI evidence before this can be reconciled as a
completed final audit gate.

Exact-head fast-validation run `36635167816` passed hosted static validation,
the structural anti-overfitting audit, hosted M2h2 contract pytest, hosted
format/diff/whitespace checks, and hosted Git diff checks at
`1697c64a8626d864fbfba39a40fde0c251818bdd`. Its locked self-hosted job
`109633910738` remained queued for 24 hours with zero observed steps and was
then cancelled by GitHub Actions on 2026-09-30. It produced no locked-runner log
and no current-regression artifact, so complete pytest, V6-3, DP2, interaction,
and final qualification evidence remained incomplete at that head. Ralph-approved
rerun attempts for the cancelled job/run were rejected by the bridge/GitHub API,
and the `m2h2-fast-validation` and `pytest` local-validation profiles were not
available through Ralph for this repository.

After a new self-hosted runner was provisioned, exact-head run `36824529633` at
`d4bda73f8485dc36df1cae4505a7ecd127d44b67` started the locked-runner job and
failed at `Pytest` because the runner platform did not match the old toolchain
lock. Diagnostic commit `c284f03f8fbde2f229111ac76a530b68e1faeccf` showed the
new runner platform is `Linux-6.8.0-87-generic-x86_64-with-glibc2.35`, CPU model
`12th Gen Intel(R) Core(TM) i7-12700K`; commit
`47789b8c3ace5094f71c56ebedf2bb48a45e0dba` updated only that platform identity
in `fixtures/m1a/toolchain.lock.json`, preserving the KiCad 10.0.6 executable
and library hashes. Run `36825923164` then got past the platform gate but failed
at `Pytest` with `KiCad library identity mismatch: sharun`. Diagnostic commit
`7c2dfecda645a5059272821ded42f8e10c4f7710` added an identity report; run
`36826093092` showed all locked `/tmp/AppDir` paths were absent on the runner
before pytest: `/tmp/AppDir/AppRun`, `/tmp/AppDir/shared/bin/kicad-cli`,
`/tmp/AppDir/sharun`, and the locked KiCad libraries all reported
`exists: false`. Therefore the new self-hosted runner can execute jobs, but the
required locked KiCad 10.0.6 AppDir is not provisioned at `/tmp/AppDir`, and no
current-source full pytest, V6-3, DP2, interaction, or final qualification
evidence exists yet on that runner.

The earlier exact-head fast-validation run `36601055914` passed hosted static
validation and hosted M2h2 contract pytest at
`5b134602edf25a1f6460aeece9496f1e839c8037`; its locked self-hosted job remained
queued, so complete pytest, V6-3, DP2, interaction, and final qualification
evidence were still incomplete at that head.

At the current source state, fresh one-run builds in `development_checks/`
passed locked KiCad 10.0.6, independent electrical observation, zero ERC, and
serialized-scene verification:

| Case | Evidence | Canonical VREF | Graph |
|---|---|---:|---|
| V6-3 | `v6-3_final_handoff_run1/` | 234.95 mm | one component |
| DP2 | `dp2_final_handoff_run1/` | 247.65 mm | one component, nine terminals |

Both are under the unchanged 250 mm gate. DP2 has no external VREF connector;
the shared internally produced reference reaches both packages, parked units,
and passive/support consumers. The route report records a `producer_centered`
strategy for both cases. These are single builds, not final five-build evidence.

Interaction coverage infrastructure now has a refreshed runner/tool hash freeze at
`fixtures/m2h2/finalization_checks/interaction_runner_hashes_eef2698.json` for
exact source head `eef2698ac55827592657cb34991c0859bdc8a4e5`. It supersedes the
older `interaction_runner_hashes_fe7335d.json` freeze after the runner gained
coverage-evidence and semantic-impossibility validators and the validation
workflow gained concurrency control. The freeze is infrastructure identity only:
it marks no interaction cell covered and does not replace five-run locked-KiCad
qualification. Any listed behavior-affecting input change invalidates it.

Interaction coverage ledger validation now rejects covered cells without
structured locked real-tool evidence and rejects impossible/unsupported cells
without a semantic impossibility witness. Evidence roots:
`fixtures/m2h2/finalization_checks/semantic_impossibility_witness_validator_8cb5d4a.json`,
`fixtures/m2h2/finalization_checks/interaction_coverage_evidence_validators_9cb6e74.json`,
and
`fixtures/m2h2/finalization_checks/coverage_ledger_no_parse_only_guard_b4d36ce.json`.
These validators pass in current-source hosted M2h2 contract pytest; they do not
mark any I1–I6 cell covered and do not replace locked real-tool qualification.

A previous full pytest suite passed **195 tests** after an earlier routing
change. The current-master baseline above supersedes the missing-AppDir state:
225 tests and both locked one-run regressions now pass. Historical protection
audit passed for 7,221 tracked files with matching HEAD/worktree digests. The
active-module literal anti-overfitting scan passed and found no CP-SAT dependency
or implementation; the structural anti-overfitting audit is implemented and
passes in hosted validation, but final-source audit reconciliation still requires
completion of the locked baseline and final qualification gates.

## Provisional qualification evidence

`qualification_candidate4/results.json` records 56/56 positives across five
clean real KiCad builds each, plus the invalid V3-8 negative. It includes all 42
prior positives, V6-1–V6-8, DP1–DP4, and the DP1/DP3 long-field derivatives.
Its compiler source hashes differ from the current worktree for `m2_compose`,
`m2_geometry`, `m2_pack`, and `m2_route`; it cannot qualify the current source.

The preserved interaction results include five-build passes for I1's nine pair
cells plus its powered selected triple, I2's nine cells, I3's thirteen electrical
cases, I4's nine cells, I5's nine cells, and I6's 21 cells. I3's default
placement matches only six of twelve planned band classes. Six further
five-build real KiCad structural alternatives under `interaction_alternatives/`
demonstrate additional band classes, but those runs also predate later source
changes. `development/interaction_coverage.json` remains at zero formally
covered cells because actual final class and all invariants have not yet been
recorded for every cell. Planned cells must never be marked covered by parsing
or generation alone.

## Remaining completion work

1. Keep the locked KiCad 10.0.6 identity verified for every qualification run;
   the current-master full pytest and one-run baseline now pass.
2. Reconfirm V6-3 and DP2 at the final source state with locked KiCad 10.0.6 and
   unchanged gates.
3. Validate every I1–I6 cell and selected triple against actual electrical,
   routing, path, layout, band-class, and real-tool invariants at the final source
   state. Update the frozen coverage ledger with evidence links and genuine
   semantic impossibility witnesses only where applicable.
4. After source stabilization, run a new five-clean-build qualification for all
   56 positives and required interaction/stress cases using locked KiCad 10.0.6.
   Confirm deterministic project bytes, net partitions, ERC, variant and route
   decisions, obligation proofs, layout metrics, and normalized SVG geometry.
5. Inspect the new rendered sheets, report worst metrics and structural/variant
   coverage, rerun complete pytest/lint/format/whitespace/historical audits, and
   perform literal plus structural anti-overfitting review. Record agent
   inspection as such; human approval is not available from this worktree.

No corpus.v7, M3 work, gate change, or CP-SAT was introduced. M2h2 is not PASS.

## Fresh final-source qualification — 2026-10-02

Production source `260e33c` passes 56/56 positives over five clean builds each (run `37048500798`, locked job `110975750982`), and 72 I1–I6 cases over five builds each (run `37048500822`). Artifact audit `37050923509` confirms exact production/lock hashes against master `728478b`. Current full pytest, hosted contracts, lint/format, structural audit, and V6-3/DP2 one-run regressions pass in run `37049738355`. See `finalization_checks/qualification_260e33c_ci.json`.

M2h2 remains **INCOMPLETE**: six actual I3 structural classes need fresh qualification; required triples, render inspection, coverage ledger and final audits need reconciliation. The alternate runner now searches/certifies from scratch per build, verifies frozen expectations independently, binds provenance, and records its eight-seed/32-slot bounded search. Older one-scene/five-emission alternatives remain historical evidence only.

## Required-field render defect — 2026-10-02

Detailed engineering/agent inspection of fresh source `260e33c` renders found timer reference/value overlap with the nearby control-capacitor body/reference label. See `finalization_checks/render_inspection_260e33c.json`. Wire-only text checks missed it. Generic local slot selection now considers transformed bodies, net labels and other required fields; the independent emitted-byte observer rejects nonpassive required-field/body/label overlaps, with authored negative controls. This behavior change invalidates final-source claims from `260e33c`; fresh tests and qualification are required. Five I3 alternate classes passed x5 in `37051640945`, while the remaining 3+ interleaved case lacked a generated class candidate. Generic peer separation and minimum-multiple-band selection preserve that failure and retry under the same hard gates/budgets.

M2h2 remains **INCOMPLETE**. No gate, frozen topology, historical artifact or ERC rule was weakened.

## Bounded selection and compact field slots — 2026-10-02

All six measured I3 classes pass five fresh searches with locked KiCad and frozen independent expectations at `634d529` (run `37052922578`). That source still fails the shared-package internal-reference contract after required-field keepouts changed packing. Add bounded nearby field slots while preserving body/label/field clearance. The governing quality-selection audit also found an early two-proved-structures stop; remove it and account for every retained seed's four slots under the same eight-seed/32-attempt ceiling. See `finalization_checks/structural_634d529_ci.json` and the new full-slot selection test. Fresh tests and all final qualifications remain required; M2h2 is **INCOMPLETE**.

## Fresh label-inspection defect — 2026-10-02

M2h2 remains **INCOMPLETE**. Source `beb50458` passed 241 complete tests, six I3 alternatives x5, and all 56 base positives x5 at qualification head `4493c318`; exact base artifact is `11252733877`. Fresh I3 render close-ups (`37067694162`) exposed duplicate supply labels and reset-net text over the timer body. Those machine results cannot close final qualification after the label-layout/independent-observer correction. All historical roots and gates remain unchanged. Continue fresh tests, qualification, actual coverage, render inspection, and audits; this is an implementation defect, not a user blocker.

## Restabilized source — 2026-10-03

Source `8675431f76594fd51c591180f0bba85ece942c9f` passes all 246 tests and both locked KiCad 10.0.6 V6-3/DP2 regressions in run `37071729309`; static checks and hosted contracts also pass. Evidence: `finalization_checks/stabilization_8675431f_ci.json`. The render-driven label, timer-exit and complete-row placement fixes require fresh base 56 x5, I1–I6 x5 and actual structural-class qualification. New qualification roots are started against frozen identical production source; M2h2 remains **INCOMPLETE** pending coverage reconciliation, render inspection and final audits.

### Current finalization repair — 2026-10-03

M2h2 remains **INCOMPLETE**. Fresh `ada198a` interaction qualification finds three five-run label/body regressions, with exact reports preserved in artifact `11262462251` and inspection run `37090552267`. Measured on-conductor gateway label clearance and three targeted real-tool regressions are under current-source validation. Existing final qualification roots are preserved but non-final after this behavior change. The governing gates, electrical topology, frozen probes and historical evidence are unchanged.

### Power/packing source restabilized — 2026-10-03

M2h2 remains **INCOMPLETE**. Production `1397637d0fe51e5dfcf46038ec34d9a65e910173` passes full locked validation `37094984816`: 255 tests, all static/hosted checks, V6-3/DP2, three connector-label cases x5, and all six targeted real-tool regressions including V6-8 and the shared-rail case. The unconnected endpoint is resolved with actual scope-correct power labels and the snapped package-envelope overlap is repaired; ERC and independent observation remain enforced. See `finalization_checks/stabilization_1397637d_ci.json` and exact source freeze `finalization_checks/final_source_1397637d.json`. Fresh base, interaction and structural five-run qualification is required; historical failed candidates remain preserved and non-final.

### Tall-core interaction restabilization — 2026-10-03

M2h2 remains **INCOMPLETE**. Candidate `47d4978c` passes 56-positive x5 qualification and six structural alternatives x5, but its I3 selected-triple composition has an inward timer-output routing failure. The generic outward-access repair is under new locked validation; all prior candidate qualification is preserved and non-final after this production change. Source freeze and final qualification must be refreshed. Exact development evidence: `finalization_checks/outward_timer_output_repair_2026-10-03.json`.

### Outward-access source restabilized — 2026-10-03

M2h2 remains **INCOMPLETE**. Source `2575ee20fba0ca24cc6edf50e0ae038b9aa8153c` passes exact locked validation `37096621691`: 256 tests, static/hosted checks, V6-3/DP2, four targeted cases x5 including the tall-core selected triple, and six real-tool regressions. All 56 positive and 72 interaction composition probes also pass, without final qualification credit. Freeze and evidence: `finalization_checks/final_source_2575ee20.json`, `stabilization_2575ee20_ci.json`, `source_review_2575ee20.json`. Fresh complete five-run base/negative, interaction and structural roots are started on identical production source; actual coverage, final render inspection and audits remain required.
