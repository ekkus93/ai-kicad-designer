# M2h2 development status — INCOMPLETE

The governing requirements are in `docs/M2_GENERALIZATION_REMEDIATION_SPEC.md`.
Development probes and their expectations remain frozen in `development/`.
Historical blind evidence is unchanged. Do not interpret the evidence below as
final qualification of the current worktree.

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
`.github/workflows/m2h2-fast-validation.yml` to produce exact-head pytest,
Ruff lint, Ruff format, and `git diff --check` evidence. The hosted static job in
run `36513428860` passed Ruff lint, Ruff format for `src`, M2 contract tests,
`tools`, `git diff --check`, and scoped trailing-whitespace checks for exact head
`5a2b8e72267beb7dda870d2e0b6af971248b5eb7`. The hosted M2h2 contract pytest
subset in the same run also passed for that exact head. A full hosted pytest run
is not a valid substitute for locked evidence because the KiCad platform/CPU
identity guard rejects the hosted runner. The locked self-hosted full pytest job
for exact head `5a2b8e72267beb7dda870d2e0b6af971248b5eb7` remains queued, so
complete pytest, V6-3, DP2, interaction, and final qualification evidence are not
complete.

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
`fixtures/m2h2/finalization_checks/interaction_runner_hashes_fe7335d.json` for
exact head `fe7335d56284babad26dd531bb7229607fa1213a`, after the runner was changed
to record observed structural classes from composition evidence. The freeze is
infrastructure identity only: it marks no interaction cell covered and does not
replace five-run locked-KiCad qualification. Any listed behavior-affecting input
change invalidates it.

A previous full pytest suite passed **195 tests** after the latest routing
change. Current-source hosted static evidence and hosted M2h2 contract pytest now
pass at exact head `5a2b8e72267beb7dda870d2e0b6af971248b5eb7`; exact-head full
pytest is still awaiting the locked runner. Historical protection audit passed
for 7,221 tracked files with matching HEAD/worktree digests. The active-module
literal anti-overfitting scan passed and found no CP-SAT dependency or
implementation.

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

1. Complete the current-source fast-validation workflow by getting the locked
   self-hosted full pytest job to run, then reconcile that baseline check only
   after exact-head evidence exists.
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
   perform a structural anti-overfitting review. Record agent inspection as such;
   human approval is not available from this worktree.

No corpus.v7, M3 work, gate change, or CP-SAT was introduced. M2h2 is not PASS.
