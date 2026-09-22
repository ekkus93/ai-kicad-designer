# M2f2 — typed packing projection and parallel-consumer layout repair

**Final status: PASS**

## Root cause and repair

The proposed root cause was confirmed. `semantic_plan()` derived ordering from
`signal` edges only, while the frozen `_ordered_main()` independently rebuilt a
row graph from `signal`, `power`, and `branch`. In V4-7 this converted two
parallel regulator consumers into a false serial row. A second generic
contributor was confirmed: local fragment envelopes already include two pitches
of clearance on every side, but the global packer added another four-pitch gap,
preventing minimum-gap compaction.

The repaired packer now derives independent signal shelves from the signal-only
projection. Power fanout consumers form a deterministic parallel shelf aligned
with their producer; reference and support edges impose no stage order; package
power blocks use the same consumer-affinity mechanism; and branch loads try a
bounded beside-source candidate and a lower attachment band. Serial signal
chains remain topologically ordered left to right, and independent multi-stage
chains start separate shelves.

Measured fragment envelopes are packed against prospective 210 × 140 mm content
limits, not merely the wider A4 usable rectangle. The bound subtracts the fixed
two-pitch-per-side padding added by the fragment-envelope constructor, then
checks the actual grid-aligned placed-envelope union. The fixed candidate budget
is eight. Candidates compact to envelope-defined legal separation, translate to
a guarded page origin, and report measured bounds or witnessed spread conflicts.
The independent observed-layout evaluator and all thresholds are unchanged.

The inter-fragment router was adjusted only where the new arrangements exposed
generic tree issues: fanout uses one shared trunk rather than overlapping
source-to-tap segments, vertical power drops select the first grid track that
clears measured obstacles, and branch routes approach the target through its
declared side corridor.

No CP-SAT was introduced.

## New probes

- `regulator_three_consumers.json`: one positive L7805 feeds three independent
  consumers—two RC blocks and one series-output block. This uses two supported
  downstream block types and is not timer-specific.
- `two_signal_chains_shared_rail.json`: two independent two-stage op-amp signal
  chains share the same L7805-generated positive rail, with no signal connection
  between the chains. Each chain retains its own signal shelf.

Both pass exact independent electrical comparison, zero-violation ERC, all
unchanged layout gates, and five-build reproducibility.

## Qualification

The pinned external environment is KiCad 10.0.6 with toolchain lock
`30402012777b0557801dfc5f7d8fbcecfbb4037da6a09e8b5df6eeb699481a9c`.
Qualification accepted 29/29 cases across 69/69 builds:

| Set | Cases | Builds | Result |
|---|---:|---:|---|
| Known corpus.v2 | 8 | 8 | PASS |
| Valid corpus.v3 plus corrected V3-8 equivalent | 8 | 8 | PASS |
| Existing M2e1 probes | 3 | 3 | PASS |
| V4 known regressions | 8 | 40 | PASS, 5/5 reproducible each |
| New M2f2 probes | 2 | 10 | PASS, 5/5 reproducible each |

All eight V4 schematic outputs changed relative to their frozen V4 artifacts,
so all eight received the required five-clean-build qualification.

| V4 case | Electrical | ERC | Layout | Observed content | Reproducibility |
|---|---|---:|---|---:|---:|
| V4-1 | PASS | 0 | PASS | 199.39 × 85.09 mm | 5/5 |
| V4-2 | PASS | 0 | PASS | 194.31 × 91.44 mm | 5/5 |
| V4-3 | PASS | 0 | PASS | 189.23 × 87.63 mm | 5/5 |
| V4-4 | PASS | 0 | PASS | 175.26 × 54.61 mm | 5/5 |
| V4-5 | PASS | 0 | PASS | 189.23 × 91.44 mm | 5/5 |
| V4-6 | PASS | 0 | PASS | 194.31 × 78.74 mm | 5/5 |
| V4-7 | PASS | 0 | PASS | 172.72 × 133.35 mm | 5/5 |
| V4-8 | PASS | 0 | PASS | 140.97 × 85.09 mm | 5/5 |

Repaired V4-7 also records zero observed overlaps, wire/body or wire/text
collisions, unrelated crossings or pin contacts, endpoint mismatches, flow or
stage-order reversals; 34.29 mm maximum local/support span; 1.69 mm minimum
text/wire clearance; and 896.62 mm total observed wire length. Its first render
is `qualification/v4-7/run1/renders/schematic/V4RegulatedDualTimerSystem.svg`.

The three-consumer probe measures 198.12 × 97.79 mm; its render is
`qualification/probe-regulator_three_consumers/run1/renders/schematic/`
`M2f2RegulatorThreeConsumers.svg`. The two-chain probe measures
201.93 × 132.08 mm; its render is
`qualification/probe-two_signal_chains_shared_rail/run1/renders/schematic/`
`M2f2TwoSignalChainsSharedRail.svg`.

## Regression and audits

- Complete pytest: 147 passed in 81.93 seconds, including M1 observer/mutation,
  all M2 identity/composition tests, and the 12-case tuning parametrization.
- Active source/tests/new M2f2 tooling: Ruff lint and Ruff format check pass.
- `git diff --check` and hand-authored whitespace checks pass.
- Historical fixture roots `m2blind`, `m2blind_v3`, `m2blind_v4`, `m2d1`, and
  `m2e1`: no changed or untracked paths.
- Active source contains no V4 IDs, V4 design names, probe IDs, inventory hashes,
  refdes geometry dispatch, or family-pair layout functions.
- No corpus.v5, M3 work, or CP-SAT dependency was created.

The complete machine-readable record is `qualification/results.json`.

**M2f2 PASS**
