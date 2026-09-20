# M2a dual op-amp qualification

The locked KiCad 10.0.6 `Amplifier_Operational:NE5532` asset inherits
`LM2904`. Its actual units are A (1 output, 2 negative input, 3 positive
input), B (5 positive input, 6 negative input, 7 output), and C (4 V-, 8 V+).
The eight physical contacts belong to one component, U1. There are no hidden,
stacked, or repeated physical pins in this asset. The inherited symbol geometry
and NE5532 child properties are resolved from the two hashed source files.

`dual_buffer.json` is the bounded M2a Circuit IR profile. U1A is a buffer with
an explicit wired output-to-negative-input feedback loop. U1B is intentionally
parked as a follower with its positive input on REF and a local wired feedback
loop. U1C is the separate package power unit. C1 spans VPLUS to REF and C2
spans REF to VMINUS. J1 is the external five-contact interface. Three
`PWR_FLAG` instances assert the externally supplied rails and reference for
ERC; they are virtual schematic assertions, not physical components or XML
netlist components. That distinction is checked in the observer.

The emitted symbol occurrences, embedded definitions, actual pin numbers,
unit inventory, local flag connections, and real KiCad XML net memberships are
observed independently of the constructive scene. The comparator alone reads
the expected IR. Hidden/stacked pins and unsupported future Circuit IR fields
are rejected explicitly.

Build with the pinned toolchain:

```sh
PYTHONPATH=src .venv/bin/python -m ai_kicad build fixtures/m2a/dual_buffer.json \
  --target schematic \
  --assets-lock fixtures/m2a/assets.lock.json \
  --toolchain-lock fixtures/m1a/toolchain.lock.json \
  --policy-lock fixtures/m1a/policy.lock.json \
  --out /tmp/m2a-build
```

A non-ASCII output basename is supported through an ASCII staging basename under
the locked C locale. A non-ASCII output parent path remains an explicit
unsupported case for this profile.

The qualification snapshot in `qualification/` contains the rendered SVG and
the measured electrical/layout/ERC reports from a fresh KiCad 10.0.6 build.
The full generated project and raw KiCad output are at `/tmp/m2a-qualified-final` in
the qualification environment. The real-tool mutation tests are in
`tests/test_m2a.py`: required power unit removed, amplifier B removed, A's
positive/negative pin numbers swapped, one physical pin number changed, unit B
reassigned to another package, and one actual input wire detached. The
expected IR stays fixed in every mutation.

M2a still rejects hidden/stacked pins, alternate units, hierarchy, buses,
PCB work, other active-device assets, and general analog placement. The
layout is a parameterized constructive buffer/support motif. It does not
qualify operating limits, amplifier stability, manufacturing, or the wider M2
corpus.
