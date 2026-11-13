# Reviewer qualification (stopped after 23 of 61): text description, blind, reasoning on

Each case: what is known about the drawing, then the reviewer's decision, issues (its own words) and requested edit.

## historical (8)

### dual_buffer__wire_across_power_unit — INVALID
- **Known defect:** a ground wire runs across U1C between V+ and V-, over its pin names
- **Reviewer:** no usable answer (length)

### inverting_gain__wire_across_power_unit — INVALID
- **Known defect:** a ground wire runs across U1C between V+ and V-, over its pin names
- **Reviewer:** no usable answer (length)

### noninverting_gain__wire_across_power_unit — INVALID
- **Known defect:** a ground wire runs across U1C between V+ and V-, over its pin names
- **Reviewer:** no usable answer (length)

### rc_to_buffer__wire_across_power_unit — INVALID
- **Known defect:** a ground wire runs across U1C between V+ and V-, over its pin names
- **Reviewer:** no usable answer (length)

### sallen_key__wire_across_power_unit — accept
- **Known defect:** a ground wire runs across U1C between V+ and V-, over its pin names

### inverting_gain__r1_r2_text_misplaced — INVALID
- **Known defect:** R2 10k sits above U1A's input wire and R1 100k sits under U1A's output, nearer the op-amp than their resistors; C1's REF ground symbol sits sideways
- **Reviewer:** no usable answer (length)

### inverting_gain__sideways_ground — INVALID
- **Known defect:** C2's REF ground symbol points sideways (left) instead of down
- **Reviewer:** no usable answer (length)

### inverting_gain__long_supply_loops — INVALID
- **Known defect:** VPLUS and VMINUS run from J1 down the left edge and along the bottom to U1C
- **Reviewer:** no usable answer (length)

## known-good (15)

### dual_buffer__known_good — needs_help
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- C1 Reference label distance (8.55 mm) exceeds field_owner_association limit (5.08 mm).
- C1 Value label distance (5.85 mm) exceeds field_owner_association limit (5.08 mm).
- U1C bodyless unit clearance violated: wires run along pin-name column at x=73.66.

### dual_rail_reference__known_good — accept
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)

### inverting_gain__known_good — INVALID
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- **Reviewer:** no usable answer (length)

### led_long_text__known_good — accept
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)

### led_reverse_supply__known_good — INVALID
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- **Reviewer:** no usable answer (length)

### led_series__known_good — accept
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)

### linear_regulator__known_good — INVALID
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- **Reviewer:** no usable answer (length)

### noninverting_gain__known_good — INVALID
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- **Reviewer:** no usable answer (length)

### rc_highpass__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- rail_route_detour for net REF exceeds limit 1.15 (ratio 1.49). Wire detours excessively to x=25.4, y=80.01.
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": false}`

### rc_lowpass__known_good — accept
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)

### rc_to_buffer__known_good — INVALID
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- **Reviewer:** no usable answer (length)

### reference_555_led_flasher_v8__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- field_owner_association: D1 Reference gap 5.25 mm > 5.08 mm limit
- field_owner_association: U1 Reference gap 6.18 mm > 5.08 mm limit
- page_balance: Drawing center offset > 0.25 from usable frame centre
- *Requested edit:* `{"operation": "regenerate_schematic"}`

### sallen_key__known_good — INVALID
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- **Reviewer:** no usable answer (length)

### timer_astable__known_good — accept
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)

### timer_astable_gnd__known_good — INVALID
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- **Reviewer:** no usable answer (length)

