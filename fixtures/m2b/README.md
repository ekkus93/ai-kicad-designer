# M2c1 semantic layout tuning qualification

M2c1 qualifies all 12 **tuning** cases in `corpus.v1.json`. The corpus bytes
remain frozen at SHA-256
`64a0bcd7c20c6275806d3912e7320af3dd3a9124b0b84ec5c7456cb19f9256b3`.
The `expected_unsupported` fields record the original M2b freeze and are not
rewritten. **corpus.v1 is a development protocol, not the final blind M2
benchmark:** M2b already exercised its `led_long_text` holdout. The remaining
holdout fixtures have not been implemented or used for tuning. A later task
must create a fresh corpus.v2 before a final held-out evaluation. This report
does not claim the full M2 exit criterion or blinded human readability.

Every row below has a checked `qualification/<id>/` project, fresh KiCad
10.0.6 XML/ERC/SVG, an independently observed physical-pin/electrical
comparison, and an observed layout report. `E` is exact electrical partition
comparison; `L` is the independent layout hard gate. `Wire/bend` gives wire mm
and orthogonal bend count. `Local/support` is the largest motif and declared
support distance in mm. `BBox` is the occupied content width × height in mm;
`Util` is its fraction of the usable A4 drawing rectangle. `Text` is the
minimum observed wire-to-required-text clearance in mm. All rows use the
asset/tool/policy hashes listed below.

| Tuning case | State | E | ERC | L | Wire/bend | Local/support | BBox | Util | Text | Locks |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---|
| `led_series` | pass | pass | 0 | pass | 91.44 / 0 | 30.48 / 0 | 116.84 × 10.16 | .029 | 9.18 | A/T/P |
| `led_reverse_supply` | pass | pass | 0 | pass | 91.44 / 0 | 30.48 / 0 | 116.84 × 10.16 | .029 | 6.77 | A/T/P |
| `rc_lowpass` | pass | pass | 0 | pass | 186.69 / 2 | 58.42 / 0 | 121.92 × 60.96 | .182 | 9.18 | A/T/P |
| `rc_highpass` | pass | pass | 0 | pass | 186.69 / 2 | 58.42 / 0 | 121.92 × 60.96 | .182 | 9.18 | A/T/P |
| `dual_buffer` | pass | pass | 0 | pass | 267.97 / 11 | 27.94 / 27.94 | 196.85 × 96.52 | .466 | 2.32 | A/T/P |
| `noninverting_gain` | pass | pass | 0 | pass | 274.32 / 11 | 27.94 / 27.94 | 196.85 × 96.52 | .466 | 2.32 | A/T/P |
| `inverting_gain` | pass | pass | 0 | pass | 287.02 / 11 | 27.94 / 27.94 | 196.85 × 96.52 | .466 | 2.32 | A/T/P |
| `rc_to_buffer` | pass | pass | 0 | pass | 320.04 / 12 | 31.75 / 27.94 | 196.85 × 99.06 | .478 | 2.32 | A/T/P |
| `dual_rail_reference` | pass | pass | 0 | pass | 331.47 / 12 | 27.94 / 27.94 | 196.85 × 96.52 | .466 | 1.69 | A/T/P |
| `sallen_key` | pass | pass | 0 | pass | 459.74 / 15 | 31.75 / 27.94 | 196.85 × 123.19 | .594 | 2.32 | A/T/P |
| `linear_regulator` | pass | pass | 0 | pass | 342.90 / 3 | 46.99 / 46.99 | 139.70 × 62.23 | .213 | 6.77 | A/T/P |
| `timer_astable` | pass | pass | 0 | pass | 514.35 / 11 | 26.67 / 26.67 | 135.89 × 95.25 | .317 | 6.77 | A/T/P |

The shared hash tuple for every row is A (M2b assets), T (KiCad toolchain),
and P (drafting policy). The inherited M2a asset lock is also included:

| Lock | SHA-256 |
|---|---|
| M2b assets | `e657a0b87be86eedb22105bf160ccbdadfe87c232977617a71aee16e3d7445b8` |
| M2a assets | `45c0116edb502793f16f756cf54a1d6c273f93a7f475207c5da4a2a720297516` |
| KiCad toolchain | `30402012777b0557801dfc5f7d8fbcecfbb4037da6a09e8b5df6eeb699481a9c` |
| Drafting policy | `b51e4e0f6c62b868ddf1642949e5073b971ff3fe108b0f62d73466d3a6e82e48` |

The tool lock identifies `/tmp/AppDir/AppRun` and its `kicad-cli` binary as
KiCad **10.0.6**, with executable SHA-256 values
`5587d7de2c45df07c3de73f4679dba77f73020a30d8e8a651a0779ceb08d86de`
and `1108ea3589e75aa274adad754275709da326f89614a9c6ce6fc456a430ef1a4b`.
The controlled configuration uses C locale and UTC. Manifests record the
design, lock, corpus and artifact hashes separately.

## Physical assets and relationships

The new standard symbols are from the official KiCad symbols repository tag
`10.0.6`, commit `7800d91437ce44e2ed0928f2ad31a287457b8a68`. The
locked `Regulator_Linear:L7805` file has SHA-256
`914752c784fe6cec8995789f16ea83c34f0c78cc35cf14583a4eb1b65d9ed499`;
its pins are **1 IN, 2 GND, 3 OUT**. The locked `Timer:NE555D` file has SHA-256
`40b6f3455dea99ec9308e5a0eaffc20c41e6affed2e3647c306bda7d92c49242`;
its pins are **1 GND, 2 TRIG, 3 OUT, 4 reset, 5 CONT, 6 THRES, 7 DISCH, 8 VCC**.
KiCad 10 common-unit pins 1 and 8 are included in the timer's physical
occurrence inventory. The comparator checks observed embedded pin names and
numbers independently of intended relationships; deliberate regulator and
timer name swaps fail.

The `m2b.1` IR adds `power_stage`, `timer`, `timing_ladder`, `bridge`, and
`reference_divider` relations. Both RC filters use the same series/shunt
composition with reversed passive roles. The LED variant changes the declared
source and return nets while preserving anode-to-cathode physical polarity.
`dual_rail_reference` uses an explicit two-resistor midpoint named `VREF`,
distinct from `VPLUS` and `VMINUS`; it is not asserted as an external source.
Sallen-Key shares the op-amp occurrence across input, feedback, bridge,
power and bypass relations. Its two series resistors, shunt capacitor, output
bridge capacitor and direct negative-feedback wire are visible in the SVG.
The regulator uses the physical IN/GND/OUT roles and two rail-specific bypass
relations. The timer uses the locked THRES/TRIG/DISCH roles, a vertical R-R-C
timing ladder, reset tied to supply, and a local control bypass.

Placement remains deterministic construction without CP-SAT or random search.
The active power/support group moved closer to the amplifier: occupied width
fell from 219.7 to 196.85 mm for the pre-existing active families. Text slots
account for horizontal and vertical passives. Observed gates now require
physical wire paths for local series, shunt, polarity, feedback, bridge,
decoupling, divider and timing relations; they check stage order, support
locality, page spread, and text visibility independently of total wire length.
Counterexamples cover label-only motifs, reversed order, detached feedback,
remote decoupling, page-scale spreading, hidden/missing text and a crossing
with shorter total wire length.

Two clean builds per tuning case compare compiler-owned project bytes,
electrical reports, complete layout metric vectors and KiCad SVG after only
the established nonsemantic `<title>` normalization. The previous M1, M2a
and M2b suites remain regression gates. All 12 checked SVGs were inspected at
full-sheet scale; the RC and LED drawings remain small because their topology
is linear and simple. The longest drawing is the timer at 514.35 mm of total
wire; Sallen-Key has the most bends (15), and the regulator has the largest
support span (46.99 mm). No hard defect is waived by these measurements.

Build a case with the locked environment:

```sh
PYTHONPATH=src .venv/bin/python -m ai_kicad build fixtures/m2b/timer_astable.json \
  --target schematic \
  --assets-lock fixtures/m2b/assets.lock.json \
  --toolchain-lock fixtures/m1a/toolchain.lock.json \
  --policy-lock fixtures/m1a/policy.lock.json \
  --out /tmp/m2c1-timer-example
```

Hierarchy, buses, PCB work, negative regulator assets, switching control and
the remaining corpus.v1 holdouts remain unsupported. `led_long_text` stays an
M2b regression only; its development use disqualifies corpus.v1 as a final
blind benchmark.
