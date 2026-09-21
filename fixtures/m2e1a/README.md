# M2e1a power-assertion correction evidence

M2e1a resolves the qualification-contract contradiction recorded by the
preserved initial M2e1 result. The composition implementation is unchanged.

`ir/regulator_timer_led_corrected.json` is a development equivalent of
historical V3-8. A direct textual comparison has exactly one changed value:
`flag.supply.net` is `VIN` instead of `VCC`. Consequently the external
connector supplies the L7805 Power-input pin through a PWR_FLAG assertion, and
the regulator's real Power-output pin alone drives the generated `VCC` rail.
All components, terminal memberships, support capacitors, timer timing/control
network, timer-output resistor/LED branch, return assertion, relationships,
values, and refdes are retained.

The historical input and blind/M2e1 evidence remain untouched. The corrected
fixture is not corpus.v4 and is not blind evidence.

Qualification evidence is written under `qualification/`. Each accepted case
has five clean KiCad 10.0.6 builds. `results.json` compares compiler-owned
schematic/project bytes, independently observed electrical partitions, ERC,
complete layout metrics, composition evidence, normalized SVG, and manifest
checks. `validation/` records the generic pre-layout rejection of historical
V3-8 and preservation hashes.

