# M2h2 development status — INCOMPLETE

**M2h2 PASS — final current-source evidence reconciled, 2026-10-03.**

Production source `79a36b173c6c82a68cbe575cc1d666c55d2296b3` and qualification producer `42ab8452fca16592ead8f628b17980a9d34794b7` pass all finalization requirements. Final ledger head `d4e493b2a99a010a5763288e45ab1bdcc07769c9` passes run `37144876230`: 283 tests, hosted contracts, lint/format/diff/whitespace/structural checks and locked KiCad 10.0.6 regressions. Fresh base 56×5 (`37132185217`), interaction 72×5 (`37132185171`), structural nine×5 (`37132185186`) and independent audit (`37143838789`) pass. All 69 required interaction cells and five selected triples have current-source five-run evidence, including actual final-source I3 band classes. All 90 SHA-verified native renders pass engineering agent inspection with no unresolved hard defect; this is not human approval. Historical invalid V3-8 remains rejected with both authored power-precondition diagnostics.

Exact closure authority: `fixtures/m2h2/finalization_checks/final_closure_42ab8452.json`. Detailed metrics, canonical local/global lengths, terminal/component coverage, structural/variant decisions, exact budgets, rejected witnesses and prediction/observation deltas are preserved in `final_artifact_reconciliation_42ab8452.json`, its four case-diagnostic files, and the SHA-verified full audit archive. Native SVG archive and review are preserved beside them. V6-3 canonical VREF is 196.85 mm; DP2 is 247.65 mm. Every canonical net remains within 250 mm; all other hard gates and ERC/independent observation remain unchanged. All 7,221 historical protected files retain aggregate SHA `f1dcfc89822b37c6c376f844adf6a43295ffd716ad64921f44d687dfb880200e`. Frozen coverage planning vectors and DP1–DP4 topology remain unchanged. Prior falsified candidates remain preserved without final credit.

The canonical TODO is COMPLETE / PASS. Stop after M2h2; no M3 or corpus.v7 is begun.

### Preserved historical working status


The governing requirements are in `docs/M2_GENERALIZATION_REMEDIATION_SPEC.md`.
Development probes and their expectations remain frozen in `development/`.
Historical blind evidence is unchanged. Do not interpret the evidence below as
final qualification of the current worktree.

## Native long-field falsification — 2026-10-03

M2h2 remains **INCOMPLETE**. Producer `585a4f7c96b185c3a4e9db73fa13960388ea411b` completed 56×5 base, 72×5 interaction, structural9×5 and independent machine audit, but native I6 long-field inspection found long rotated resistor values overlapping their bodies/references. The preserved candidate is falsified for final readability. The production repair adds measured long-passive text clearance, explicit field orientation, and independent long-passive body checks. Relevant TODO checks are reopened; all final-source qualification and render gates must be repeated. Exact native evidence: `finalization_checks/long_passive_field_falsification_585a4f7c.json`; complete archives: `final_native_585a4f7c/` and `final_audit_585a4f7c/`. No hard gate, topology, ERC requirement, or historical evidence is weakened.

## Historical implementation slice — 2026-10-02

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

## Native-render hard defect — 2026-10-03

M2h2 remains **INCOMPLETE**. Producer `84b21bc399e2239cd796bb9ec4f09a989f8ce808` passes the 56-positive x5, 72-interaction x5, six-structural x5 and original V3-8 negative machine suites on identical source `2575ee20`. The completed artifact audit verifies machine evidence and historical integrity, but actual native DP3 long-field inspection falsifies label readability: `REQUIRED_NET_LABEL20` and `A_OUT` run together. The native SVG is preserved at `fixtures/m2h2/finalization_checks/native_render_defect_dp3_long_fields_84b21bc3.svg`, with exact references in `fixtures/m2h2/finalization_checks/render_falsification_84b21bc3_2026-10-03.json`. Source stabilization is reopened; these qualifications are preserved pre-repair evidence and cannot count as final-source completion after the required font repair. The unchanged 210x140, 80, 60 and 250 mm gates, ERC, independent observation, frozen topology, and historical evidence remain mandatory. Actual I3 class reconciliation and complete fresh render inspection also remain open.

## Native-font repair source stabilized — 2026-10-03

M2h2 remains **INCOMPLETE**. Production `7b788e58a6a5e21f286b4a25d643e0727da1944e` passes locked validation `37109142099` at stabilization/test head `f18b02d586e9575a0a3a86f2e347812570803a04`: 261 complete tests, 67 hosted contracts, scoped static checks, fresh V6-3/DP2 one-run regressions, four targeted cases x5 and six additional real-tool regressions. Conservative locked-font label envelopes, generic bounded package/passive alternatives and typed distribution repair preserve all gates and independent ERC/artifact observation. See `finalization_checks/stabilization_7b788e58_ci.json`, `source_review_7b788e58.json` and `final_source_7b788e58.json`. Fresh complete base 56 x5 plus original V3-8 negative, 72 interaction x5 and eight observed structural alternatives x5 are requested. Preserved pre-repair qualifications are non-final; actual coverage, native render inspection and final audits remain required.

## Visible pin-number readability defect — 2026-10-03

M2h2 remains **INCOMPLETE**. Fresh eight structural alternatives qualify x5 on production `7b788e58` in run `37109849527`, artifact `11270055020`; native render transfer `37109981436` passes. Actual agent inspection of four renders finds connector aliases overlapping their visible pin number (`INPUT` visually becomes `INPUT1`). Exact SVG and coordinates are preserved in `finalization_checks/native_render_defect_pin_number_7c475adc.svg` and `pin_number_render_falsification_7c475adc.json`. This is a new hard readability defect, requiring generic local label clearance and independent emitted-byte rejection from actual visible pin definitions. Source stabilization is reopened; pre-repair qualification is preserved and non-final after behavior changes. Fixed gates, electrical topology, ERC and historical evidence remain unchanged.

## Actual whole-band I3 closure implemented — 2026-10-03

M2h2 remains **INCOMPLETE**. The generic narrow timer output escape plus bounded measured all-cell row proves three active timers in one actual non-interface band at 205.707343 x 139.28 mm. Development composition passes 56/56 positives and 72/72 interactions; all nine required structural classes prove within eight seeds / 32 attempts. Focused tests pass 28 and contract/audit tests pass 56. See `finalization_checks/i3_whole_band_development_2026-10-03.json`. Previous pin-number repair CI passes locked 263 tests and real-tool regressions; its formatting failure is corrected using repository Ruff configuration. Fresh locked baseline now includes five builds of the actual whole-band case. Final-source full qualification, native render inspection, coverage reconciliation and audits are still required; no local proof or historical qualification is promoted as PASS.

## Local proposal accounting corrected — 2026-10-03

M2h2 remains **INCOMPLETE**. Exact DP2 instrumentation falsified the 32-local-proposal ceiling (33/35 package proposals). Shared accounting now enforces 32 including rejections and reports untried/retention-truncated classes, preserving pre-packing failure evidence. Three newer regression entries omitted during snapshot restoration are restored unchanged. The bounded implementation passes development 56-positive / 72-interaction compositions and all nine structural searches; 32 restored focused regression tests pass. Predecessor locked baseline `37113559365` passes all jobs, including five actual three-timer whole-band builds, but final source stabilization is reopened for the accounting change. See `finalization_checks/local_construction_budget_2026-10-03.json`. Fresh complete baseline and final qualification/render/coverage/audits remain mandatory.

### Native source-marker readability repair — 2026-10-03

Baseline `37114227421` on `354efeda` succeeds with 266 tests and all locked regressions, including five actual three-timer whole-band builds. A separate actual native inspection exposes the power-source diamond overlapping VPLUS. The measured finite contact/orientation repair and independent emitted-byte source-body rejection reopen source stabilization and qualification. Historical native evidence is preserved; M2h2 remains **INCOMPLETE**, pending fresh final-source qualification and renders. Details: `fixtures/m2h2/finalization_checks/source_marker_clearance_2026-10-03.json`.

### Stabilized source after source-marker repair — 2026-10-03

Source `94e8b4bc45242a1e834a1ae1a123d0717a589a6c` is frozen in `fixtures/m2h2/finalization_checks/final_source_94e8b4bc.json`. Complete baseline `37123857550` passes all jobs: 268 tests and all locked KiCad 10.0.6 regression builds, including five actual whole-band three-timer builds. Artifact `11274093988` preserves the evidence. A report-only commit requests fresh 56-positive x5, 72-interaction x5 and nine structural x5 qualification. Coverage reconciliation, full normalized reproducibility, native render inspection and audits remain pending. M2h2 remains **INCOMPLETE**.

### Source-glyph wire clearance reopened — 2026-10-03

The `94e8b4bc` source baseline and `f2628c9c` qualification are superseded: exact DP2 geometry reveals a source-attached vertical wire through the rotated power-source diamond. Finite existing-conductor contact selection now requires measured wire clearance, and independent emitted-byte observation rejects wire entry into source glyphs without the component-pin endpoint exemption. No conductor or electrical topology is added or weakened. Details: `fixtures/m2h2/finalization_checks/source_glyph_wire_clearance_2026-10-03.json`. M2h2 remains **INCOMPLETE** pending new baseline and final-source evidence.

### Wire-clear source stabilized — 2026-10-03

`1273d6af219475db5fc804d487d06e8fb6fa8c69` passes complete baseline `37124948961`: 270 tests and every locked KiCad 10.0.6 regression, including five actual whole-band builds. Artifact `11275495312` preserves evidence. `final_source_1273d6af.json` freezes all 19 production hashes, four runner hashes and three locks. A report-only trigger requests fresh complete five-run base, interaction and nine-case structural qualification. No prior-source qualification is final credit; coverage, native inspection and final audits remain open. M2h2 remains **INCOMPLETE**.


### Current-source interaction qualification result (2026-10-03)

Frozen production source `1273d6af219475db5fc804d487d06e8fb6fa8c69`, producer `5c7640a8d9a505a733f009f7a2c7cd1d6c2012b0`: I1–I6 run `37125376457` passed all 72 cases × five fresh independent locked-KiCad 10.0.6 builds with reproducible results. See `fixtures/m2h2/finalization_checks/interaction_5c7640a8_ci.json`. M2h2 remains **INCOMPLETE** pending fresh base56/structural9 results, independent final artifact audit, measured coverage reconciliation and native render inspection.


### Native worksheet falsification and bounded page-placement repair (2026-10-03)

M2h2 remains **INCOMPLETE**. Actual source-1273 `a3_one` native render falsifies engineering inspection: the title-block top border crosses `C5.Value=10u`. See `fixtures/m2h2/finalization_checks/worksheet_native_falsification_2026-10-03.json`. Preserve successful interaction run `37125376457` and structural run `37125376451` as historical candidate evidence; neither qualifies the repaired final source. New generic finite page translation and independent worksheet collision gates require fresh baseline, all five-run qualification and inspection. No corpus.v7 or M3 work is started.


### Worksheet-clear stabilized source (2026-10-03)

Production `f161672f761559e0e8ae7294f1c4df39fa24bebb` passes current complete locked-runner baseline `37127192673`: 271 tests, source V6-3/DP2, targeted five-run probes, actual whole-layout one-band ×5 and additional real KiCad regressions. Source/runner/lock freeze and exact CI evidence are in `finalization_checks/final_source_f161672f.json`, `stabilization_f161672f_ci.json` and `source_review_f161672f.json`. Fresh full qualification is requested. M2h2 remains **INCOMPLETE** pending final-source five-run base/interaction/structural qualification, independent artifact audit, measured coverage reconciliation and native inspection.


### Fresh worksheet-clear structural result (2026-10-03)

All nine structural alternatives ×5 passed on frozen source f161672f / producer 585a4f7c in run `37127602956`. Exact native SVG digests and agent inspection in `finalization_checks/structural_585a4f7c_ci_inspection.json` confirm repaired C5/title-block clearance and readable current structural scenes. M2h2 remains **INCOMPLETE** pending base56 and I72 fresh qualification, independent final artifact audit, actual-cell reconciliation and remaining render inspection.


### Fresh source f161 interaction qualification — 2026-10-03

All 72 current-source interaction cases passed five fresh locked-KiCad 10.0.6 builds at producer `585a4f7c96b185c3a4e9db73fa13960388ea411b`, run `37127602933`, job `111216003619`. Exact case paths, reproducibility and artifact SHA are recorded in `fixtures/m2h2/finalization_checks/interaction_585a4f7c_ci.json`. This closes qualification of those cases, not actual I3 band-class coverage or the V6-3 internal-reference selected triple; final independent artifact audit and coverage reconciliation remain required. M2h2 remains **INCOMPLETE**.
