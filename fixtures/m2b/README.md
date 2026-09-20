# M2b semantic analog layout qualification

`corpus.v1.json` freezes the M2 protocol before layout tuning. It has 12 tuning
and 8 held-out circuits. Its byte SHA-256 is
`64a0bcd7c20c6275806d3912e7320af3dd3a9124b0b84ec5c7456cb19f9256b3`.
`corpus.v1.sha256` records the same digest. Membership and case metadata require
an explicit version bump and rationale to change. Cases marked
`expected_unsupported` remain in their original splits for later M2 work.

The checked M2b subset uses `m2b.1` Circuit IR. Components and nets carry
physical identities; relations supply series order, shunt/reference, polarity,
flow, amplifier function, negative feedback, power rails, and local decoupling.
The same constructive layout functions serve all supported cases. The active
stage keeps separate NE5532 units A/B/C as one physical package. Unit B is
intentionally biased as a follower. A feedback resistor can share the sense
node with a gain/reference leg or an input series resistor without acquiring
a second symbol occurrence.

| ID | Split | Electrical | ERC | SVG | Layout hard gates | Symbols | Wires | Labels | Bends | Wire mm |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|
| `led_series` | tuning | pass | 0 | pass | pass | 4 | 3 | 2 | 0 | 91.44 |
| `rc_lowpass` | tuning | pass | 0 | pass | pass | 5 | 6 | 3 | 2 | 186.69 |
| `dual_buffer` | tuning | pass | 0 | pass | pass | 9 | 26 | 12 | 11 | 267.97 |
| `noninverting_gain` | tuning | pass | 0 | pass | pass | 11 | 29 | 13 | 11 | 274.32 |
| `inverting_gain` | tuning | pass | 0 | pass | pass | 11 | 29 | 13 | 11 | 287.02 |
| `rc_to_buffer` | tuning | pass | 0 | pass | pass | 11 | 30 | 13 | 12 | 320.04 |
| `led_long_text` | holdout | pass | 0 | pass | pass | 4 | 3 | 2 | 0 | 91.44 |

The holdout case uses the existing LED/resistor relations with longer legal
reference and value strings. It has no case ID, reference, or component-list
branch in the compiler. Every result above came from the pinned KiCad 10.0.6
CLI. `qualification/<id>/` holds the generated project, fresh KiCad XML/ERC,
SVG, independent electrical comparison, layout metrics, and build manifest.
Each manifest records design, asset, toolchain, policy and corpus hashes plus
artifact hashes. Transient KiCad configuration files and `.kicad_prl` are not
checked evidence.

Build any case using the locked environment:

```sh
PYTHONPATH=src .venv/bin/python -m ai_kicad build fixtures/m2b/rc_lowpass.json \
  --target schematic \
  --assets-lock fixtures/m2b/assets.lock.json \
  --toolchain-lock fixtures/m1a/toolchain.lock.json \
  --policy-lock fixtures/m1a/policy.lock.json \
  --out /tmp/m2b-rc-example
```

The observer parses emitted embedded symbols and occurrences, then reads fresh
KiCad XML terminal partitions. It does not consume layout scene connectivity.
The layout gate reparses the artifact for body, wire, text, pin, crossing, and
margin checks. The `.gitattributes` exception is limited to raw KiCad-generated
qualification SVG whitespace; source and authored fixtures retain normal
whitespace checks.

M2b deliberately leaves the rest of the frozen corpus unsupported: high-pass
variants, Sallen-Key, regulators, timer, switching control, broad reference
networks, and additional composed/summing circuits. It does not claim the full
12/8 corpus or blinded-readability M2 exit. Deterministic construction passed
all seven cases without CP-SAT or random search.
