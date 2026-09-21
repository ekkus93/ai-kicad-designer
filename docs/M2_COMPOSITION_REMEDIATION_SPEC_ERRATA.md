# M2 composition remediation specification erratum

Status: accepted M2e1a qualification-contract correction, 2026-09-21.

## Scope

This erratum corrects only the M2e1 handoff and completion requirements in
sections 9.4 and 9.5 of
[M2_COMPOSITION_REMEDIATION_SPEC.md](M2_COMPOSITION_REMEDIATION_SPEC.md). It does
not change the architecture, the Circuit IR, the schematic power policy, KiCad
pin electrical types, ERC severity, or any historical corpus artifact.

## Contradictory historical input

Historical `fixtures/m2blind_v3/ir/V3-8.json` has SHA-256
`4e0c1f1634a23870b5e50990da49e7f1696113f9544587677c8346a520ffdf1a`.
It declares all of the following simultaneously:

- external connector `J1` and regulator pin 1 `IN` on `VIN`;
- regulator pin 3 `OUT` and timer supply consumers on `VCC`;
- power stage input `VIN` and output `VCC`; and
- authored PWR_FLAG `flag.supply` / `#FLG01` on `VCC`.

The locked KiCad 10.0.6 assets resolve L7805 `IN` as `Power input`, L7805
`OUT` as `Power output`, connector contacts as passive, and PWR_FLAG as `Power
output`. Each of the five preserved M2e1 builds therefore reports the same two
real-tool errors, visible in
`fixtures/m2e1/qualification/v3-8/run1.failed/reports/erc.json` through
`run5.failed`:

1. `power_pin_not_driven`: L7805 `U1` pin 1 `IN` on `VIN` has no Power-output
   source.
2. `pin_to_pin`: PWR_FLAG `#FLG01` on `VCC` is a Power output connected to
   L7805 `U1` pin 3 `OUT`, also a Power output.

The first failed run independently reconstructed the expected terminal
partition exactly, and its composition evidence records the generic power
dependency from the regulator output to the timer plus the timer-output LED
branch. The failure is thus the authored source assertion, not composition or
connectivity. No geometry can preserve that exact assertion and also produce
zero ERC errors. Section 9.4's demand that all eight v3 inputs pass unchanged,
and section 9.5's corresponding completion bullet, are impossible for this
input under the governing power policy.

## Corrected qualification rule

Replace those requirements with this rule:

- Valid historical regression inputs must pass unchanged.
- A historical input proven invalid by independent real-tool evidence remains
  byte-for-byte preserved and classified as negative evidence; its historical
  blind and qualification results are not relabeled.
- The same requested topology must be represented by a corrected development
  fixture consistent with the governing IR and power policy, and that fixture
  must pass every electrical, ERC, layout, and reproducibility gate.

For V3-8, the corrected development fixture moves the authored external-source
assertion from the regulator-generated output rail to the genuine external
input rail. It does not alter topology, parts, terminals, relationships, return
assertion, pin types, ERC rules, or compiler behavior.

## Non-relaxation

The compiler must reject contradictory source assertions before final
acceptance using resolved terminal electrical roles and interface/power-stage
semantics. It must not infer from net spelling, silently move or insert a
PWR_FLAG, suppress either ERC violation, or repair user IR. Cases that the
narrow profile cannot prove safely are rejected explicitly.

