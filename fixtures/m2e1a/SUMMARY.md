# M2e1a qualification summary

Status: **PASS**

Git base: `7a29f21c` (`M2e1`). The exact final working-tree state is reported by
`git status --short` at handoff; all M2e1a changes are intentionally
uncommitted.

## Resolution

M2e1's instance-based composition implementation was successful. Its initial
completion criterion was blocked by a proven-invalid historical benchmark
input, not by the composer. The original BLOCKED result remains unchanged at
`fixtures/m2e1/SUMMARY.md`.

Historical V3-8 asserts its external supply on the wrong side of its L7805:
`J1` and the regulator Power-input pin are on `VIN`, while `flag.supply` is on
the regulator-generated `VCC` net. Real KiCad 10.0.6 consequently reports both
an undriven Power-input on `VIN` and a Power-output/PWR_FLAG Power-output
conflict on `VCC`. The five original failed runs and the historical blind result
remain preserved and are not relabeled.

[The specification erratum](../../docs/M2_COMPOSITION_REMEDIATION_SPEC_ERRATA.md)
corrects sections 9.4/9.5 only: valid historical cases pass unchanged; proven
invalid cases remain negative evidence; and a corrected equivalent must pass
all gates. It does not relax ERC or change architecture.

## Input-contract correction

The `m2b.1` validator now evaluates authored PWR_FLAG claims against actual
resolved asset-pin electrical types and declared power-stage/interface
semantics. It:

- rejects an authored PWR_FLAG on a net containing a resolved Power-output
  terminal;
- requires an explicit PWR_FLAG when a power-stage input is represented only
  by passive external-interface connectivity and Power-input consumers; and
- explicitly rejects cases whose external-source status cannot be proved by
  the narrow profile.

The rule contains no case ID, refdes, or net-name dispatch. Tests prove that an
external-input flag is accepted, an output-net flag is rejected, input data is
not mutated or repaired, arbitrary net renaming does not change the result,
missing evidence is rejected, and ambiguous interface evidence is rejected.
The compiler does not relocate or insert a flag. No ERC rule, pin electrical
type, or composition geometry was changed.

## Corrected equivalent

`ir/regulator_timer_led_corrected.json` has SHA-256
`137d44ec7d6df8b6a1217896dd9118541404654d7a63a6e975a7393d9c4a4b09`.
A direct diff from historical V3-8 changes exactly one value:
`flag.supply.net` from `VCC` to `VIN`. It retains the regulator input/output
support capacitors, timer timing ladder and control bypass, timer-output
current-limited LED branch, external interfaces, return assertion, all terminal
memberships, and every semantic relationship.

Five fresh builds through pinned KiCad 10.0.6 all pass and have identical
compiler-owned schematic/project bytes, independently observed electrical
partitions, normalized SVG, composition evidence, ERC, complete layout metric
vector, and manifest checks. The generic composition trace retains the
`power_stage.regulator` → `timer.timer` power edge on `VCC` and the
`timer.timer` → `passive.indicator.series` branch edge on `OUT`.

Corrected-fixture results:

- independent expected/observed electrical partitions: exact, no diagnostics;
- ERC: zero violations;
- SVG: generated in every run;
- layout hard gates: all pass, with zero body overlaps, wire/body or wire/text
  collisions, unrelated crossings/pin contacts, endpoint mismatches, flow or
  stage-order reversals, and unrouted pins;
- observed content: 175.26 mm × 100.33 mm, page utilization 0.430844;
- observed local/support span: 34.29 mm; minimum text/wire clearance: 1.69 mm;
- five-run reproducibility: pass.

Full artifacts and the complete metric vector are in
`qualification/corrected-regulator-timer-led/`; normalized cross-run evidence
is in `qualification/results.json`.

## Regression qualification

Because validator source changed, M2e1a regenerated all accepted cases rather
than reusing earlier five-run evidence:

| Set | Result |
|---|---:|
| Valid corpus.v2 regressions | 8/8 pass; five-run reproducible |
| Valid corpus.v3 regressions (V3-1 through V3-7) | 7/7 pass; five-run reproducible |
| Original M2e1 development probes | 3/3 pass; five-run reproducible |
| Corrected V3-8-equivalent development fixture | 1/1 pass; five-run reproducible |
| Total accepted cases/builds | 19/19 cases; 95/95 builds |

Historical V3-8 is classified as `invalid_authored_power`. Its pre-layout
validation record contains both `POWER_ASSERTION_DRIVER_CONFLICT` and
`POWER_SOURCE_ASSERTION_REQUIRED`, and records that no compiler repair or
layout was attempted.

## Preservation and gates

Historical V3-8 remains byte-for-byte unchanged at SHA-256
`4e0c1f1634a23870b5e50990da49e7f1696113f9544587677c8346a520ffdf1a`.
The preserved original failed-run tree digest is
`594ed83b7340b5562255fd344f2684d17a070a0633c4777e943f7d273bcc2ac7`.
`qualification/results.json` also records hashes for corpus.v3, its automated
results and summary, and the initial M2e1 summary. Git reports no changes under
those protected paths.

Complete regression and mutation tests pass: `136 passed`. Ruff lint, Ruff
format check, and `git diff --check` also pass. `HASHES.sha256` records the
corrected input, result/validation records, preserved evidence, and lock
digests. No corpus.v4 or M3 work was created or started.
