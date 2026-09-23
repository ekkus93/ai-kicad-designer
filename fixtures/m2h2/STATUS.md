# M2h2 development status — BLOCKED

This is partial development evidence, not a qualified M2h2 result. The four
fixed probes, two required long-field derivatives, expected terminal inventories,
electrical partitions and path obligations were frozen before layout tuning in
`development/`. The deterministic I1–I6 interaction covering set is frozen there
too. Its covered-cell list remains empty: none of the planned cells has passed
its complete invariants. Historical fixture and document integrity hashes still
match the frozen record.

The implementation derives terminal-backed signal precedence independently of
branch edge kind, checks placed terminal inequalities and selected local spans
before routing, checks every local gateway witness, enumerates whole-net wire
components, and requires explicit routing of internally generated references
without connector edges. It preserves composition attempts and available metrics
when a later real build fails. A typed producer is now selected for internally
generated reference routing, and the bounded seed order includes more variant
assignments. These contracts remain partial: the immutable obligation-complete
certificate, serialized-scene boundary, full typed repair model, distributive
trunk alternatives, structural coverage ledger, and full generic test matrix are
still missing.

## Preserved one-run development builds

| Case | Preserved evidence | Result at time of build |
|---|---|---|
| V6-1 | `qualification/v6_1/run2` | Real KiCad/independent observer pass |
| V6-2 | `qualification/v6_2/run1` | Real KiCad/independent observer pass |
| V6-3 | `qualification/v6_3/run1.failed` | Failure preserved; still fails current composition on VREF >250 mm |
| V6-4 | `qualification/v6_4/run2` | Real KiCad/independent observer pass |
| V6-5 | `qualification/v6_5/run2` | Real KiCad/independent observer pass |
| V6-6 | `qualification/v6_6/run2` | Real KiCad/independent observer pass |
| V6-7 | `qualification/v6_7/run2` | Real KiCad/independent observer pass |
| V6-8 | `qualification/v6_8/run2` | Real KiCad/independent observer pass |
| DP1, DP1 long fields | `qualification/dp1*/run1` | Real KiCad/independent observer pass |
| DP2 | not_evaluated | Current composition cannot attach a package reference gateway |
| DP3, DP3 long fields | `qualification/dp3*/run1` | Real KiCad/independent observer pass |
| DP4 | `qualification/dp4/run1` | Real KiCad/independent observer pass |

Those passing builds predate the latest source edits and do not qualify the
current worktree. Failed attempt directories were retained. The current
composition reproduces V6-3's hard VREF length failure and DP2's blocked VREF
gateway even after producer selection and variant-beam changes.

The full historical/new pytest suite passed at 178 tests before the final beam
ordering edit; the affected M2g2/M2f2/M2h2 tests then passed at 42 tests. Ruff
lint and format checks pass on changed Python files. No 42-case M2g2 five-run
qualification, all-positive five-run repeat, complete interaction execution,
full render inspection, or human blind gate has been performed. The locked real
KiCad version for preserved builds is 10.0.6. No corpus.v7, M3 work, or CP-SAT
was introduced.
