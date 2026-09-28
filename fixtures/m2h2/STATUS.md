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
covers global-route channel capacity rejection and meaningful structural-diversity
reporting in composition evidence. This is contract evidence only, not final
real-tool qualification.

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

The full pytest suite passed **195 tests** after the latest routing change.
Ruff lint, Ruff format, `git diff --check`, and scoped trailing-whitespace checks
pass after formatting. Historical protection audit passed for 7,221 tracked files
with matching HEAD/worktree digests. The active-module literal anti-overfitting
scan passed and found no CP-SAT dependency or implementation.

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

1. Complete the spec's full generic falsification matrix, including independent
   graph and tiny exhaustive placement oracles, reservation and serialization
   mutations, and metamorphic tests.
2. Audit the obligation certificate, corridor allocation, routing bounds,
   structural search ledger, and repair decisions against every requirement in
   the specification. Fix any missing invariant before acceptance.
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
