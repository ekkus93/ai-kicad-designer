# M2e1 implementation qualification summary

Status: **BLOCKED**

Git base: `8c5c48802fdf9ea5406a44fdcc4228514a1b5a72` with the uncommitted M2e1
changes listed by `git status --short` in `qualification/results.json`.

The implementation now uses independent semantic-instance recognition, exact
occurrence ownership, local fragment construction, measured-envelope packing,
typed inter-fragment dependencies, and deterministic route trees. The former
single-core build path is no longer used. Compatibility calls in `m2b.py`
delegate to the common composer. No CP-SAT or whole-design/pairwise dispatch was
introduced.

## Qualification result

Five clean builds were run for every known v2/v3 regression and each new
development probe. Successful runs require exact compiler project bytes,
independently observed electrical equivalence, zero ERC violations, all layout
gates, normalized SVG equality, complete metric-vector equality, and matching
composition evidence.

| Set | Result |
|---|---:|
| Known corpus.v2 regressions | 8/8 pass; all five-run reproducible |
| Known corpus.v3 regressions | 7/8 pass; all outcomes five-run reproducible |
| New development probes | 3/3 pass; all five-run reproducible |
| Total | 18/19 accepted |

The only rejection is V3-8. Every clean run reaches real KiCad 10.0.6 and
returns the same two ERC errors:

1. `power_pin_not_driven`: regulator U1 pin 1 (`IN`) on `VIN` has no power
   source assertion.
2. `pin_to_pin`: `#FLG01`, a power-output PWR_FLAG explicitly authored on
   `VCC`, is connected to regulator U1 pin 3 (`OUT`), also a power output.

This is an input-contract contradiction, not a remaining composition failure.
The frozen V3-8 IR declares `flag.supply` on the regulator **output** `VCC`,
while its `power_stage` relation declares the external input as `VIN`. With the
locked L7805 and PWR_FLAG electrical pin types, no geometry can both preserve
that exact assertion/net identity and produce zero ERC violations. Moving the
flag to `VIN`, changing the IR, suppressing ERC rules, weakening the observer,
or changing locked asset electrical types are all explicitly forbidden by the
task. The five failed builds and raw ERC reports are retained under
`qualification/v3-8/`.

The fresh XML and emitted schematic from the first failed run were also passed
through the independent electrical observer after the staged build stopped:
the expected and observed terminal partitions compare exactly. Thus V3-8's
remaining rejection is specifically the two real-KiCad ERC violations, not an
electrical-partition or composition mismatch.

## Gates and metrics

- Complete pytest: `130 passed`.
- Ruff lint over `src`, `tests`, and `tools`: pass.
- Ruff format check over `src`, `tests`, and `tools`: pass.
- `git diff --check`: pass.
- KiCad: locked 10.0.6 AppImage; toolchain lock SHA-256
  `30402012777b0557801dfc5f7d8fbcecfbb4037da6a09e8b5df6eeb699481a9c`.
- Assets lock SHA-256:
  `e657a0b87be86eedb22105bf160ccbdadfe87c232977617a71aee16e3d7445b8`.
- Policy lock SHA-256:
  `b51e4e0f6c62b868ddf1642949e5073b971ff3fe108b0f62d73466d3a6e82e48`.

Worst values among accepted five-run sheets:

- observed content: 205.74 mm wide, 104.14 mm high;
- feedback span: 15.24 mm;
- local wire span: 49.53 mm;
- support locality: 34.29 mm;
- page utilization: 0.52498;
- minimum observed text/wire clearance: 1.65 mm.

## Engineering render inspection

The first clean render of each new development probe was inspected at full
sheet scale in addition to the automated geometry gates:

- `amplifier_to_sallen_key`: both NE5532 functional units are visibly distinct,
  each local feedback/filter structure remains attached to its unit, the signal
  path is traceable from the non-inverting stage into the Sallen-Key stage, and
  the shared package power unit is isolated below the signal row.
- `regulator_parallel_rc`: the regulator input/output support capacitors remain
  local to the regulator, and the regulated output uses one visible fanout trunk
  with two distinct RC branch taps.
- `dual_timer_led`: the two timing/control groups remain distinct, each timer
  output terminates in its own resistor/LED branch, and the shared supply and
  reference domains do not imply a false signal-ordering edge.

No overlapping symbols, clipped content, severed local motif wiring, or
ambiguous branch ownership was observed in these renders. This inspection is
an engineering sanity check, not a substitute for the independent electrical,
ERC, layout, or reproducibility gates.

All 12 M2c1 tuning cases pass the complete regression suite. All historical
evidence directories (`fixtures/m2blind/`, `fixtures/m2blind_v3/`, and
`fixtures/m2d1/`) have no working-tree changes. Their original blind outcomes
are not rewritten or relabeled.

M2e1 cannot be marked PASS until the governing requirement resolves the V3-8
IR/ERC contradiction. No corpus.v4 or M3 work was started.
