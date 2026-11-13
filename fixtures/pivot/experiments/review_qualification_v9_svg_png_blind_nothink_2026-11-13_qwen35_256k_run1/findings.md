# Reviewer qualification: SVG text + PNGs, blind, reasoning off

Each case: what is known about the drawing, then the reviewer's decision, issues (its own words) and requested edit.

## historical (14)

### dual_buffer__wire_across_power_unit — revise
- **Known defect:** a ground wire runs across U1C between V+ and V-, over its pin names
- Issue 1: Rail VPLUS presentation failure. The net VPLUS has terminals at J1 pin 3, C1 pin 1, and U1C pin 8. In the drawing, the wire from J1 pin 3 to C1 pin 1 is visible, but the terminal group containing U1C pin 8 is not visibly joined to this trunk by a wire; instead, it appears isolated or connected only via text labels. This violates rail_presentation which requires every separated group to touch a power symbol or be wired to a shared trunk.
- Issue 2: Rail VMINUS presentation failure. The net VMINUS has terminals at J1 pin 4, C2 pin 2, and U1C pin 4. The wire from J1 pin 4 to C2 pin 2 is visible, but the terminal group containing U1C pin 4 is not visibly joined to this trunk by a wire; it appears isolated or connected only via text labels. This violates rail_presentation.
- Issue 3: Rail REF presentation failure. The net REF has terminals at J1 pin 5, C1 pin 2, and U1C pin 5. The wire from J1 pin 5 to C1 pin 2 is visible, but the terminal group containing U1C pin 5 is not visibly joined to this trunk by a wire; it appears isolated or connected only via text labels. This violates rail_presentation.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### inverting_gain__wire_across_power_unit — revise
- **Known defect:** a ground wire runs across U1C between V+ and V-, over its pin names
- rail_presentation: The REF rail is not correctly presented. Terminal U1C pin 2 (REF) is connected to C1, but the wire path from C1's top plate to the main REF trunk is interrupted by a gap near J1 pin 5 and U1C pin 4. The intended circuit requires all REF terminals to be visibly joined or marked with a power symbol. Currently, the connection between the C1/C2 decoupling network and the main REF rail appears broken in the drawing.
- rail_presentation: The VMINUS rail is not correctly presented. Terminal U1C pin 4 (VMINUS) connects to C2, but the wire path from C2's bottom plate to the main VMINUS trunk is interrupted near J1 pin 4 and U1C pin 8. The connection between the decoupling capacitors and the main VMINUS rail is visually broken.
- rail_presentation: The power symbols for REF (U1C pin 2) and VMINUS (U1C pin 4) are not properly connected to their respective rails due to the broken wire paths described above. This violates the rail_presentation requirement that every terminal of an asserted rail must be visibly connected to that rail.
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": true}`

### noninverting_gain__wire_across_power_unit — revise
- **Known defect:** a ground wire runs across U1C between V+ and V-, over its pin names
- rail_presentation: The VPLUS rail is not correctly presented. Terminal U1C pin 8 (V+) at x=109.22, y=90.17 is connected to C1 pin 1 but lacks a visible power symbol or continuous wire trunk joining it to the other VPLUS terminals (J1 pin 3 and U1A pin 8). The rail appears fragmented with no shared wire path.
- rail_presentation: The VMINUS rail is not correctly presented. Terminal U1C pin 4 (V-) at x=109.22, y=105.41 is connected to C2 pin 2 but lacks a visible power symbol or continuous wire trunk joining it to the other VMINUS terminals (J1 pin 4 and U1A pin 2). The rail appears fragmented with no shared wire path.
- rail_presentation: The REF rail is not correctly presented. Terminal R2 pin 2 at x=144.78, y=124.46 is connected to the ground symbol but lacks a visible power symbol or continuous wire trunk joining it to the other REF terminals (J1 pin 5 and U1A pin 5). The rail appears fragmented with no shared wire path.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### rc_to_buffer__wire_across_power_unit — accept
- **Known defect:** a ground wire runs across U1C between V+ and V-, over its pin names

### sallen_key__wire_across_power_unit — revise
- **Known defect:** a ground wire runs across U1C between V+ and V-, over its pin names
- rail_presentation: The VPLUS rail is not correctly presented. Terminal U1C pin 8 (VPLUS) at x=198.12, y=66.04 is connected to a power symbol #FLG01, but the wire from U1C pin 8 to #FLG01 crosses under the body of component C1 without a visible T-junction marker or clear routing path in the SVG paths. Additionally, the rail segment connecting U1C pin 8 to #FLG01 appears to be interrupted by the geometry of C1's symbol body.
- rail_presentation: The VMINUS rail is not correctly presented. Terminal U1C pin 4 (VMINUS) at x=198.12, y=81.28 is connected to a power symbol #FLG02, but the wire path from U1C pin 4 to #FLG02 crosses under the body of component C3 without a visible T-junction marker or clear routing path in the SVG paths.
- rail_presentation: The REF rail is not correctly presented. Terminal J1 pin 5 (REF) at x=58.42, y=43.18 is connected to a power symbol #FLG03, but the wire path from J1 pin 5 to #FLG03 crosses under the body of component C1 without a visible T-junction marker or clear routing path in the SVG paths.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### inverting_gain__r1_r2_text_misplaced — revise
- **Known defect:** R2 10k sits above U1A's input wire and R1 100k sits under U1A's output, nearer the op-amp than their resistors; C1's REF ground symbol sits sideways
- rail_presentation: The REF rail is not correctly presented. Terminal U1C pin 3 (REF) and terminal C1 pin 2 (REF) are connected to the main REF net, but they are not visibly joined by a continuous wire trunk or marked by a matching power symbol on their own separate group. Instead, they rely on text labels which is insufficient per the brief.
- rail_presentation: The VMINUS rail is not correctly presented. Terminal U1C pin 4 (VMINUS) and terminal C2 pin 2 (VMINUS) are connected to the main VMINUS net, but they are not visibly joined by a continuous wire trunk or marked by a matching power symbol on their own separate group.
- rail_presentation: The VPLUS rail is not correctly presented. Terminal U1C pin 8 (VPLUS) and terminal C1 pin 1 (VPLUS) are connected to the main VPLUS net, but they are not visibly joined by a continuous wire trunk or marked by a matching power symbol on their own separate group.
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": true}`

### inverting_gain__sideways_ground — revise
- **Known defect:** C2's REF ground symbol points sideways (left) instead of down
- rail_presentation: The REF rail is not correctly presented. Terminal U1C pin 2 (REF) is connected to C1, but the wire path from C1 to the main REF trunk is visually ambiguous and potentially disconnected in the SVG data. Specifically, the wire segment M72.3900 74.9300 L72.3900 73.6600 suggests a connection to C1's negative terminal, but the path to the main REF net (which includes J1 pin 5 and U1 pins 3/5) is not clearly continuous in the provided SVG paths. The intended circuit requires all REF terminals to be visibly connected via wires or power symbols.
- rail_presentation: The VMINUS rail has a similar issue. Terminal U1C pin 4 (VMINUS) connects to C2, but the wire path from C2 to the main VMINUS trunk (J1 pin 4 and U1 pin 4) is not clearly continuous in the SVG data. The wire segment M99.0600 82.5500 L97.7900 82.5500 suggests a connection to C2's negative terminal, but the path to the main VMINUS net is ambiguous.
- rail_presentation: The power symbols for REF and VMINUS are present (#FLG03 at (29.21, 43.18) and #FLG02 at (26.67, 40.64)), but their connection to the respective rail terminals is not visually clear in the SVG paths. The power symbols should be clearly joined to their rail terminals by wires or be part of a continuous rail group.
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": true}`

### inverting_gain__long_supply_loops — revise
- **Known defect:** VPLUS and VMINUS run from J1 down the left edge and along the bottom to U1C
- rail_presentation: The REF rail is not correctly presented. Terminal U1C pin 2 (VMINUS) and terminal C1 pin 2 (REF) are connected to the same net, but the wire path between them is visually ambiguous and does not clearly join a shared trunk or power symbol as required by the brief. Specifically, the wire from C1 pin 2 to U1C pin 2 appears to cross under other wires without clear junction markers, violating the rail_presentation criterion that every terminal must visibly connect to a shared rail or matching power symbol.
- rail_presentation: The VMINUS rail is not correctly presented. Terminal J1 pin 4 and terminal C2 pin 2 are connected via a wire path that loops around U1C without clear junction markers, making the connection visually ambiguous. This violates the requirement that branch junctions be visibly unambiguous.
- label_association: The label 'REF' at (102.75, 85.09) is associated with C2 pin 1, but its proximity to U1C pin 3 (also labeled REF) creates ambiguity about which terminal it belongs to, violating the field_owner_association criterion of <= 5.08 mm.
- page_composition: The drawing center is offset from the usable frame center by more than 0.25 of the frame's half-width and half-height, as the circuit components are clustered in the upper-left quadrant, leaving excessive unused space on the right and bottom, violating the page_balance criterion.
- *Requested edit:* `{"operation": "move_field", "reference": "#FLG03", "unit": 1, "field": "Value", "x_mm": 29.21, "y_mm": 45.88, "angle": 0}`

### inverting_gain__long_ref_wire_and_loop — revise
- **Known defect:** a long REF wire from J1 to U1A's + input, and C2's ground wired by a loop over U1C close under its NE5532 text
- rail_presentation: The VPLUS rail is not correctly presented. Terminal U1C pin 8 (V+) at x=82.55, y=71.12 is connected to a power symbol '#FLG01' which names 'PWR_FLAG', not 'VPLUS'. The intended circuit requires this terminal to be marked with a power symbol naming 'VPLUS' or joined by wire to the main VPLUS trunk.
- rail_presentation: The VMINUS rail is not correctly presented. Terminal U1C pin 4 (V-) at x=82.55, y=86.36 is connected to a power symbol '#FLG02' which names 'PWR_FLAG', not 'VMINUS'. The intended circuit requires this terminal to be marked with a power symbol naming 'VMINUS' or joined by wire to the main VMINUS trunk.
- rail_presentation: The REF rail is not correctly presented. Terminal U1C pin 2 (REF) at x=72.39, y=82.55 is connected to a power symbol '#FLG03' which names 'PWR_FLAG', not 'REF'. The intended circuit requires this terminal to be marked with a power symbol naming 'REF' or joined by wire to the main REF trunk.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### inverting_gain__decoupling_detour — revise
- **Known defect:** C2's VMINUS wire leaves U1C pin 4, runs right under C2 and back up to C2's top pin (40.64 mm); C2's REF symbol sits 1.27 mm above that wire
- rail_presentation: The VPLUS rail is not correctly presented. Terminal U1C pin 8 (V+) at x=82.55, y=71.12 is connected to C1 pin 1 via a wire, but the intended circuit defines VPLUS as a net connecting U1 pin 8, C1 pin 1, and J1 pin 3. The drawing shows a wire from U1C pin 8 to C1 pin 1, but there is no visible connection or power symbol for the VPLUS rail at J1 pin 3 (x=33.02, y=38.1). The terminal inventory lists J1 pin 3 as part of the VPLUS net, but the SVG shows a wire from J1 pin 3 to VPLUS label text, not a continuous wire trunk or power symbol joining the rail groups. This violates the requirement that every terminal of an asserted REF/VCC rail must be visibly connected by wire or a matching power symbol.
- rail_presentation: The VMINUS rail is not correctly presented. Terminal U1C pin 4 (V-) at x=82.55, y=86.36 is connected to C2 pin 2 via a wire, but the intended circuit defines VMINUS as a net connecting U1 pin 4, C2 pin 2, and J1 pin 4. The drawing shows a wire from U1C pin 4 to C2 pin 2, but there is no visible connection or power symbol for the VMINUS rail at J1 pin 4 (x=33.02, y=40.64). The terminal inventory lists J1 pin 4 as part of the VMINUS net, but the SVG shows a wire from J1 pin 4 to VMINUS label text, not a continuous wire trunk or power symbol joining the rail groups. This violates the requirement that every terminal of an asserted REF/VCC rail must be visibly connected by wire or a matching power symbol.
- rail_presentation: The REF rail is not correctly presented. Terminal U1A pin 3 (+) at x=83.82, y=39.37 is connected to J1 pin 5 via a wire, but the intended circuit defines REF as a net connecting U1 pins 3 and 5, C1 pin 2, C2 pin 1, and J1 pin 5. The drawing shows a wire from U1A pin 3 to J1 pin 5, but there is no visible connection or power symbol for the REF rail at C1 pin 2 (x=72.39, y=82.55) or C2 pin 1 (x=99.06, y=74.93). The terminal inventory lists these pins as part of the REF net, but the SVG shows wires from these pins to REF label text, not a continuous wire trunk or power symbol joining the rail groups. This violates the requirement that every terminal of an asserted REF/VCC rail must be visibly connected by wire or a matching power symbol.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### inverting_gain__vminus_by_pin_name — revise
- **Known defect:** the VMINUS rail name sits about 1 mm right of U1C's V- pin name
- rail_presentation: The VPLUS rail is not correctly presented. Terminal U1C pin 8 (V+) at x=82.55, y=71.12 is connected to C1 pin 1 via a wire, but the wire does not extend to a power symbol naming VPLUS. Instead, the wire connects to J1 pin 3 which has a VPLUS label, but there is no continuous visible wire trunk joining all VPLUS terminals (U1C-8, C1-1, J1-3) in a single group without interruption or ambiguity. The rail appears fragmented visually.
- rail_presentation: The VMINUS rail is not correctly presented. Terminal U1C pin 4 (V-) at x=82.55, y=82.55 is connected to C2 pin 2 via a wire, but the wire does not extend to a power symbol naming VMINUS. Instead, the wire connects to J1 pin 4 which has a VMINUS label, but there is no continuous visible wire trunk joining all VMINUS terminals (U1C-4, C2-2, J1-4) in a single group without interruption or ambiguity. The rail appears fragmented visually.
- rail_presentation: The REF rail is not correctly presented. Terminal U1A pin 3 (+) at x=83.82, y=39.37 and U1A pin 5 (-) at x=130.81, y=39.37 are connected via a wire to J1 pin 5 which has a REF label, but there is no continuous visible wire trunk joining all REF terminals (U1A-3, U1A-5, C1-2, C2-1, J1-5) in a single group without interruption or ambiguity. The rail appears fragmented visually.
- rail_presentation: Power symbols for VPLUS, VMINUS, and REF are present but do not clearly name their respective rails in a way that satisfies the rail_presentation check. For example, the power symbol at J1 pin 5 is labeled 'REF', but it is not connected via a continuous wire to all other REF terminals, leading to ambiguity.
- rail_presentation: Power symbols for VPLUS and VMINUS are present but do not clearly name their respective rails in a way that satisfies the rail_presentation check. For example, the power symbol at J1 pin 3 is labeled 'VPLUS', but it is not connected via a continuous wire to all other VPLUS terminals, leading to ambiguity.
- rail_presentation: Power symbols for VMINUS and REF are present but do not clearly name their respective rails in a way that satisfies the rail_presentation check. For example, the power symbol at J1 pin 4 is labeled 'VMINUS', but it is not connected via a continuous wire to all other VMINUS terminals, leading to ambiguity.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### inverting_gain__vminus_above_c2_text — revise
- **Known defect:** the VMINUS rail name sits about 1 mm above C2's C2 / 100n text
- rail_presentation: The VPLUS rail is not correctly presented. Terminal U1C pin 8 (V+) at x=82.55, y=71.12 is connected to C1 pin 1 via a wire, but the wire does not extend to a power symbol or shared trunk for VPLUS. Instead, it connects directly to C1's top plate which is labeled VPLUS but lacks a continuous rail path to other VPLUS terminals like J1 pin 3 or U1A pin 8. The rail appears fragmented with no visible common trunk joining all VPLUS terminals.
- rail_presentation: The VMINUS rail is not correctly presented. Terminal U1C pin 4 (V-) at x=82.55, y=82.55 connects to C2 pin 2 via a wire, but the wire does not extend to a power symbol or shared trunk for VMINUS. It connects directly to C2's bottom plate labeled VMINUS but lacks continuity with other VMINUS terminals like J1 pin 4 or U1A pin 2.
- rail_presentation: The REF rail is not correctly presented. Multiple terminals (U1A pin 3, U1B pin 5, U1C pin 6, C1 pin 2, C2 pin 1, J1 pin 5) are labeled REF but are not joined by a visible common wire trunk or matching power symbol. Each terminal group is isolated without a shared rail path.
- rail_presentation: Power symbols for VPLUS, VMINUS, and REF are present but do not form continuous rails with other terminals of the same net. For example, #FLG01 (VPLUS) at x=72.39, y=74.93 is near U1C pin 8 but not connected via wire to other VPLUS terminals.
- rail_presentation: Power symbols for VMINUS (#FLG02) and REF (#FLG03) are similarly isolated without connecting wires to their respective net terminals.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### timer_astable__vcc_arrows_into_text — revise
- **Known defect:** R1's VCC arrow points down into R1's 10k; the RST VCC arrow points sideways
- rail_presentation: The VCC rail is visually disconnected at U1 pin 4 (RST). The wire from R1 connects to the TIMING net, but there is no visible wire connecting the top of R1 to U1 pin 4. The intended circuit requires a continuous path from J1 Supply through R1 to both the TIMING network and U1 pin 4.
- rail_presentation: The REF rail is visually disconnected at C2. The wire from C2 connects to the TIMING net, but there is no visible wire connecting the bottom of C2 to the main REF return path via J3 or U1 pin 1.
- label_association: The label 'VCC' near U1 pin 8 is positioned too close to the symbol body and overlaps with the pin number '8', reducing readability.
- *Requested edit:* `{"operation": "connect_rail", "net": "VCC", "replace_existing": true}`

### reference_555_led_flasher_v8__vcc_arrow_at_ref_text — revise
- **Known defect:** the RST VCC arrow points at C2's REF text; C1's REF crowds J1's Supply text
- rail_presentation: The VCC rail is not correctly presented. Terminal U1 pin 8 (VCC) at x=91.44, y=49.53 is connected to a power symbol via wire, but terminal U1 pin 4 (VCC) at x=78.74, y=54.61 is connected only by text label 'VCC' without a visible wire trunk or matching power symbol on its separate group. This violates the requirement that every terminal of an asserted VCC rail must be visibly connected to a shared rail or a matching power symbol.
- rail_presentation: The REF rail is not correctly presented. Terminal U1 pin 1 (REF) at x=88.9, y=69.85 is connected only by text label 'REF' without a visible wire trunk or matching power symbol on its separate group. This violates the requirement that every terminal of an asserted REF rail must be visibly connected to a shared rail or a matching power symbol.
- rail_presentation: The CONT rail is not correctly presented. Terminal C2 pin 1 (CONT) at x=71.12, y=38.1 is connected only by text label 'REF' (which is incorrect net labeling for this terminal based on intended circuit) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The DISCH rail is not correctly presented. Terminal R1 pin 2 (DISCH) at x=54.61, y=45.72 is connected only by text label 'VCC' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The TIMING rail is not correctly presented. Terminal R2 pin 2 (TIMING) at x=54.61, y=63.5 is connected only by text label 'REF' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The LED_A rail is not correctly presented. Terminal D1 pin 2 (LED_A) at x=29.21, y=60.96 is connected only by text label 'WP7113ID' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The OUT rail is not correctly presented. Terminal D1 pin 1 (OUT) at x=29.21, y=68.58 is connected only by text label 'WP7113ID' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The LED_A rail is not correctly presented. Terminal R3 pin 2 (LED_A) at x=29.21, y=53.34 is connected only by text label '1k' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The OUT rail is not correctly presented. Terminal J2 pin 1 (OUT) at x=29.21, y=87.63 is connected only by text label 'Pulse output' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The REF rail is not correctly presented. Terminal C1 pin 2 (REF) at x=54.61, y=85.09 is connected only by text label '10u' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The TIMING rail is not correctly presented. Terminal C1 pin 1 (TIMING) at x=54.61, y=77.47 is connected only by text label '10u' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The REF rail is not correctly presented. Terminal J3 pin 1 (REF) at x=74.93, y=92.71 is connected only by text label 'Return' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The VCC rail is not correctly presented. Terminal R3 pin 1 (VCC) at x=29.21, y=45.72 is connected only by text label '1k' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The VCC rail is not correctly presented. Terminal J1 pin 1 (VCC) at x=48.26, y=92.71 is connected only by text label 'Supply' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The CONT rail is not correctly presented. Terminal U1 pin 5 (CONT) at x=88.9, y=49.53 is connected only by text label 'NE555D' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The DISCH rail is not correctly presented. Terminal R2 pin 1 (DISCH) at x=54.61, y=55.88 is connected only by text label '47k' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The TIMING rail is not correctly presented. Terminal U1 pin 2 (TIMING) at x=78.74, y=64.77 is connected only by text label 'NE555D' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The TIMING rail is not correctly presented. Terminal U1 pin 6 (TIMING) at x=78.74, y=62.23 is connected only by text label 'NE555D' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The VCC rail is not correctly presented. Terminal C2 pin 2 (REF) at x=71.12, y=45.72 is connected only by text label '10n' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The VCC rail is not correctly presented. Terminal U1 pin 4 (VCC) at x=78.74, y=54.61 is connected only by text label 'NE555D' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The VCC rail is not correctly presented. Terminal U1 pin 8 (VCC) at x=91.44, y=49.53 is connected only by text label 'NE555D' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The REF rail is not correctly presented. Terminal U1 pin 1 (REF) at x=88.9, y=69.85 is connected only by text label 'NE555D' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The REF rail is not correctly presented. Terminal C2 pin 2 (REF) at x=71.12, y=45.72 is connected only by text label '10n' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The REF rail is not correctly presented. Terminal C1 pin 2 (REF) at x=54.61, y=85.09 is connected only by text label '10u' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- rail_presentation: The REF rail is not correctly presented. Terminal J3 pin 1 (REF) at x=74.93, y=92.71 is connected only by text label 'Return' (incorrect net labeling) and lacks a visible wire trunk or matching power symbol.
- *Requested edit:* `{"operation": "connect_rail", "net": "VCC", "replace_existing": true}`

## injected (32)

### rc_lowpass__detached_value — revise
- **Known defect:** detached_value
- Issue 1: The REF net (Return) is not visibly connected to a power symbol. The terminals for J3 and C1 are joined by wires, but the rail lacks a ground glyph or supply arrow as required by the visible_local_rails rubric.
- Issue 2: The layout of the return path (J3 to C1) forms a large loop that is not optimized for readability; the wire runs along the left edge and bottom, which could be improved by routing more directly if space permits, though this is minor compared to the missing power symbol.
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": true}`

### rc_lowpass__overlapping_fields — revise
- **Known defect:** overlapping_fields
- The resistor R1 has a visible value label '10k' but the intended circuit specifies 'R1' as the reference and '10k' as the value. The SVG shows 'R1' text rotated 90 degrees at (69.85, 36.71) and '10k' at (69.85, 39.41). However, the field inventory lists R1's reference text at (69.85, 36.074) with angle 90 and value text at (69.85, 38.774) with angle 90. The visual rendering matches the intended circuit values, but the label association for R1's reference 'R1' is present. No readability issue found for R1 labels.
- The capacitor C1 has a visible value label '10n' but the intended circuit specifies 'C1' as the reference and '10n' as the value. The SVG shows 'C1' text at (84.49, 62.87) and '10n' at (69.85, 36.71). Wait, the '10n' label is misplaced; it should be near C1 but is shown near R1 in the SVG description? Re-examining: The SVG has '10n' text at (69.85, 36.71) which is actually the value for C1? No, that position is near R1. The field inventory shows C1's value '10n' at (69.85, 36.074). This is a misplacement: the value '10n' for C1 is drawn at the same coordinates as R1's reference label in the SVG, causing overlap or confusion. The intended circuit has C1 with value '10n', but the SVG places '10n' near R1 instead of C1. This is a readability problem.
- The capacitor C1's reference label 'C1' is at (84.49, 62.87) which is correct, but its value '10n' is incorrectly placed at (69.85, 36.074) overlapping with R1's labels. This violates field_separation and owner_association criteria.
- The resistor R1's reference label 'R1' is at (69.85, 36.074) and value '10k' at (69.85, 38.774), which are correct for R1. However, the capacitor C1's value '10n' is also placed at (69.85, 36.074) in the SVG, causing a collision with R1's reference label. This is a critical readability issue.
- The page composition shows all components grouped in the top-left quadrant, which is acceptable for a simple circuit. No excessive unused space or crowding issues detected.
- No power rails (REF/VCC) are asserted in this circuit, so rail_presentation and power_symbol_clearance checks do not apply. The circuit uses connectors J1, J2, J3 without explicit power symbols, which is valid for signal nets only.
- *Requested edit:* `{"operation": "move_field", "reference": "C1", "unit": 1, "field": "Value", "x_mm": 84.49, "y_mm": 60.96, "angle": 0}`

### rc_lowpass__distant_reference — revise
- **Known defect:** distant_reference
- Issue 1: Missing Reference Label for Resistor R1. The resistor symbol (R1) has a value '10k' but lacks the reference designator 'R1'. This violates the label_association criterion where every required component reference must be legible.
- Issue 2: Missing Power Rail Presentation. The circuit contains nets IN, OUT, and REF, but there are no power symbols (supply arrows or ground glyphs) to present these rails as asserted power nets. According to visible_local_rails, terminals of an asserted rail must connect to a shared wire or a matching power symbol.
- Issue 3: Poor Page Composition Balance. The schematic content is heavily concentrated in the top-left quadrant (approx. x<100mm, y<80mm), leaving the majority of the A4 page empty. This violates page_composition's requirement for balanced functional grouping and clear reading flow without excessive unused space.
- *Requested edit:* `{"operation": "move_field", "reference": "R1", "unit": 1, "field": "Reference", "x_mm": 30.48, "y_mm": 30.48, "angle": 0}`

### rc_lowpass__off_balance_page — accept
- **Known defect:** off_balance_page

### led_series__detached_value — revise
- **Known defect:** detached_value
- Issue 1: Missing power symbols for asserted rails. The intended circuit defines nets 'VPLUS' and 'REF'. The schematic shows terminals for J1 (pin 1) and R1 (pin 1) on the VPLUS net, and D1 (pin 1) and J2 (pin 1) on the REF net. However, no power symbols (supply arrows or ground glyphs) are visible connected to these nets. According to the review brief, every terminal of an asserted rail must be visibly connected by wire or a matching power symbol. The current drawing relies solely on text labels ('Input', 'Return') which is insufficient for rail presentation.
- Issue 2: Rail continuity not visually presented. The wires connecting J1-R1-D1-J2 form a loop, but without explicit power symbols at the entry points (or along separate branches if they existed), the rails are not correctly presented per the 'visible_local_rails' criteria. The brief states that repeated same-name net labels alone are not accepted.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### led_series__overlapping_fields — revise
- **Known defect:** overlapping_fields
- Issue 1: Missing power symbols for asserted rails. The intended circuit defines nets VPLUS and REF as power rails, but the schematic lacks visible power symbols (supply arrows or ground glyphs) at the terminals of J1, R1, D1, and J2. This violates the rail_presentation criterion, which requires every terminal group to be joined by wire or marked by a matching power symbol.
- Issue 2: Missing decoupling capacitors. The review brief owner-readability.v9 specifies that a power unit's two decoupling capacitors should be mirrored across it. The current schematic contains only a resistor (R1) and an LED (D1), with no capacitors present to satisfy this layout requirement.
- *Requested edit:* `{"operation": "use_power_symbols", "net": "VPLUS"}`

### led_series__distant_reference — revise
- **Known defect:** distant_reference
- Issue 1: Missing power symbols for asserted rails. The intended circuit defines nets 'VPLUS' and 'REF', but the schematic lacks visible power symbols (supply arrows or ground glyphs) to terminate these rails at their disconnected terminal groups. This fails the 'visible_local_rails' criterion, specifically 'rail_presentation'.
- Issue 2: Label association ambiguity for R1. The reference 'R1' is located far from its resistor symbol, and while not strictly overlapping, it risks being visually stranded or ambiguous in a larger context, though currently within the 5.08 mm heuristic limit. However, given the sparse layout, moving it closer would improve owner-readability.
- Issue 3: Label association ambiguity for J1/J2. The value labels 'Input' and 'Return' are placed near their connectors but could be clearer if positioned more directly adjacent to the pin stubs or within a tighter field envelope relative to the symbol body.
- *Requested edit:* `{"operation": "move_field", "reference": "R1", "unit": 1, "field": "Reference", "x_mm": 83.0, "y_mm": 45.0, "angle": 0}`

### led_series__off_balance_page — revise
- **Known defect:** off_balance_page
- The REF net (return path) is visually disconnected. The wire from J2 pin 1 connects to a separate horizontal segment that does not join the vertical return path coming from D1. This violates the rail_presentation criterion which requires every terminal of an asserted rail to be visibly connected by continuous wires or a matching power symbol.
- The VPLUS net (supply path) is visually disconnected. The wire from J1 pin 1 connects to a separate horizontal segment that does not join the vertical supply path coming from R1. This violates the rail_presentation criterion.
- The intended circuit defines a series connection where current flows from J1, through R1, then D1, and returns via J2. The current drawing shows two distinct, unconnected wire segments for both the input and return rails, failing to present the asserted power rails correctly.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### linear_regulator__detached_value — revise
- **Known defect:** detached_value
- Issue 1: Rail presentation failure for net REF. The terminals at C1 (pin 2), C2 (pin 2), U1 (pin 2), and J3 (pin 1) are not visibly joined by a continuous wire trunk nor marked by matching power symbols. Specifically, the wire from U1 pin 2 to C1 pin 2 exists, but the connection to C2 and J3 is broken or missing in the visual representation, violating rail_presentation.
- Issue 2: Rail presentation failure for net VOUT. The terminals at J2 (pin 1), C2 (pin 1), and U1 (pin 3) are not visibly joined by a continuous wire trunk. The wire from U1 pin 3 to C2 pin 1 exists, but the connection to J2 is missing or broken.
- Issue 3: Rail presentation failure for net VIN. The terminals at J1 (pin 1), C1 (pin 1), and U1 (pin 1) are not visibly joined by a continuous wire trunk. The wire from J1 pin 1 to U1 pin 1 exists, but the connection to C1 is missing or broken.
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": true}`

### linear_regulator__overlapping_fields — revise
- **Known defect:** overlapping_fields
- rail_presentation: The REF rail is not correctly presented. Terminal U1:2 (GND) at (110.49, 49.53) connects to C1 and C2 but has no visible wire or power symbol joining it to the other REF terminals (J3:1, C1:2, C2:2). The netlist shows connectivity, but visually the rail is fragmented without a shared trunk or matching power symbols for each group.
- rail_presentation: Terminal J3:1 at (52.07, 34.29) is isolated with no wire connecting to the main REF rail formed by U1:2-C1-C2. It lacks a power symbol to mark it as part of the REF net visually.
- rail_presentation: Terminal C1:2 at (97.79, 68.58) and C2:2 at (123.19, 68.58) are connected by wire but neither has a power symbol; they rely on U1:2 which itself is disconnected from J3 visually.
- rail_presentation: Power symbols #FLG01 and #FLG02 are present but do not name the rails (REF/VIN). They should be replaced with proper power symbols naming 'REF' for ground and 'VIN' for input, or connected via wires to existing named symbols if available. Currently they appear as generic flags without rail names.
- rail_presentation: Supply arrows for VIN should point up; currently no supply arrow is visible on the VIN rail (J1-U1-C1). The rail relies solely on text labels which is insufficient per brief.
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": true}`

### linear_regulator__distant_reference — revise
- **Known defect:** distant_reference
- rail_presentation: The REF rail is not correctly presented. Terminal U1 pin 2 (REF) at x=110.49, y=49.53 is connected to C1 pin 2 and the GND pin of U1, but there is no visible wire connecting this group to a power symbol named 'REF'. The only REF power symbols are at J3 (x=52.07, y=34.29) and below C1/C2 (x=97.79, y=68.58). The terminal at U1 pin 2 is stranded from the rail presentation.
- rail_presentation: Terminal J3 pin 1 (REF) at x=52.07, y=34.29 has a power symbol nearby but the wire connection to the main REF rail trunk is missing or ambiguous in the SVG path data for the upper left section.
- page_composition: The drawing layout is unbalanced with significant empty space on the right side of the A4 page (x > 150mm), while all components are clustered in the top-left quadrant (x < 130mm). This violates the page_balance criterion which requires the drawing centre to be within 0.25 of the frame centre.
- *Requested edit:* `{"operation": "move_field", "reference": "U1", "unit": 1, "field": "Value", "x_mm": 110.49, "y_mm": 34.45, "angle": 0}`

### linear_regulator__off_balance_page — revise
- **Known defect:** off_balance_page
- rail_presentation: The REF rail is not correctly presented. Terminal U1 pin 2 (GND) at (245.11, 45.72) connects to C2 pin 2 and the GND symbol, but there is no visible wire connecting this group to the main REF rail trunk formed by J3, C1, and the other connections. The netlist shows all these as members of 'REF', but visually they are separated without a continuous wire path or a shared power symbol naming the rail for the entire group.
- rail_presentation: Terminal U1 pin 2 (GND) at (245.11, 45.72) is connected to C2 and a GND symbol, but this group is visually isolated from the main REF rail trunk (J3, C1). The rail is split into disconnected visual groups without a clear common wire or shared power symbol for the entire net.
- rail_presentation: Terminal U1 pin 2 (GND) at (245.11, 45.72) connects to C2 and a GND symbol, but this group is visually isolated from the main REF rail trunk (J3, C1). The rail is split into disconnected visual groups without a clear common wire or shared power symbol for the entire net.
- rail_presentation: Terminal U1 pin 2 (GND) at (245.11, 45.72) connects to C2 and a GND symbol, but this group is visually isolated from the main REF rail trunk (J3, C1). The rail is split into disconnected visual groups without a clear common wire or shared power symbol for the entire net.
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": true}`

### inverting_gain__detached_value — revise
- **Known defect:** detached_value
- Issue 1: Power rail VPLUS is not correctly presented. The terminal at U1C pin 8 (V+) is connected to a wire that goes to C1, but the power symbol for VPLUS is missing or incorrectly placed. The rail should be visibly connected to a supply arrow or ground glyph naming VPLUS.
- Issue 2: Power rail VMINUS is not correctly presented. The terminal at U1C pin 4 (V-) is connected to a wire that goes to C2, but the power symbol for VMINUS is missing or incorrectly placed. The rail should be visibly connected to a ground glyph naming VMINUS.
- Issue 3: Power rail REF is not correctly presented. The terminal at U1C pin 2 (REF) is connected to a wire that goes to C1, but the power symbol for REF is missing or incorrectly placed. The rail should be visibly connected to a ground glyph naming REF.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### inverting_gain__overlapping_fields — revise
- **Known defect:** overlapping_fields
- Issue 1: Rail 'REF' presentation failure. The intended circuit defines a common REF rail connecting terminals on U1A (pin 3), U1B (pin 5), C1 (pin 2), C2 (pin 1), and J1 (pin 5). In the drawing, the wire from U1A pin 3 to the central junction is present, but the wire from U1B pin 5 to that same junction is missing. Instead, a separate power symbol labeled 'REF' is placed at U1B's pin 5 location without being electrically joined to the main REF rail trunk via a wire. This violates the rail_presentation criterion which requires every terminal of an asserted rail to be visibly connected by continuous wires or a matching power symbol on each separately drawn group. The isolated 'REF' symbol at U1B is not part of a wired group touching a supply arrow for the REF net, nor is it joined to the main trunk.
- Issue 2: Rail 'VMINUS' presentation failure. The intended circuit defines a common VMINUS rail connecting terminals on U1A (pin 4), U1C (pin 4), C2 (pin 2), and J1 (pin 4). In the drawing, the wire from U1A pin 4 to the central junction is present, but the wire from U1C pin 4 to that same junction is missing. Instead, a separate power symbol labeled 'REF' (which should be 'VMINUS' based on netlist) is placed at U1C's pin 4 location without being electrically joined to the main VMINUS rail trunk via a wire. This violates the rail_presentation criterion.
- Issue 3: Rail 'VPLUS' presentation failure. The intended circuit defines a common VPLUS rail connecting terminals on U1A (pin 8), C1 (pin 1), and J1 (pin 3). In the drawing, the wire from U1A pin 8 to the central junction is present, but the wire from C1 pin 1 to that same junction is missing. Instead, a separate power symbol labeled 'VPLUS' is placed at C1's pin 1 location without being electrically joined to the main VPLUS rail trunk via a wire. This violates the rail_presentation criterion.
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": true}`

### inverting_gain__distant_reference — INVALID
- **Known defect:** distant_reference
- **Reviewer:** no usable answer (model response exceeded its output token limit)

### inverting_gain__off_balance_page — revise
- **Known defect:** off_balance_page
- rail_presentation: The VPLUS rail is not correctly presented. Terminal U1C pin 8 (V+) at x=189.23, y=72.39 is connected to C1 pin 1 via a wire, but the power symbol for VPLUS (#FLG01) is located at x=179.07, y=75.438 which is not directly connected to this terminal group by a continuous wire trunk or a matching power symbol on that specific separated group. The rail appears fragmented visually.
- rail_presentation: The VMINUS rail is not correctly presented. Terminal U1C pin 4 (V-) at x=189.23, y=80.01 is connected to C2 pin 2 via a wire, but the power symbol for VMINUS (#FLG02) is located at x=133.35, y=38.1 which is not directly connected to this terminal group by a continuous wire trunk or a matching power symbol on that specific separated group. The rail appears fragmented visually.
- rail_presentation: The REF rail is not correctly presented. Terminal U1C pin 2 (REF) at x=179.07, y=84.535 is connected to C1 pin 2 via a wire, but the power symbol for REF (#FLG03) is located at x=135.89, y=40.64 which is not directly connected to this terminal group by a continuous wire trunk or a matching power symbol on that specific separated group. The rail appears fragmented visually.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### sallen_key__detached_value — accept
- **Known defect:** detached_value

### sallen_key__overlapping_fields — revise
- **Known defect:** overlapping_fields
- issue_1: The REF rail is not correctly presented. Terminal U1A pin 5 (REF) at x=180.34, y=39.37 is connected to a wire that goes left to J1 pin 5, but the terminal U1B pin 6 (REF) at x=180.34, y=44.45 is isolated from the main REF rail by a separate wire loop that does not connect to the common trunk. The intended circuit defines all REF terminals as one net, but visually they are split into disconnected groups without a shared power symbol or continuous wire trunk.
- issue_2: Power symbol clearance fails for #FLG01 (REF flag) at x=186.69, y=69.85. The power symbol box touches the wire connecting U1A pin 5 to the REF rail, violating the clearance requirement that power-symbol glyph or value boxes must not touch another symbol, field, label, visible pin number or foreign wire.
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": true}`

### sallen_key__distant_reference — revise
- **Known defect:** distant_reference
- rail_presentation: The REF rail is not correctly presented. Terminal U1 pin 5 (REF) at x=180.34, y=39.37 is connected to a power symbol via wire, but terminal C2 pin 1 (REF) at x=220.99, y=71.12 is connected to a power symbol whose value text 'PWR_FLAG' is placed at x=220.99, y=73.82. However, the wire from U1 pin 5 goes down to a ground glyph at x=186.69, y=72.64 (which is actually connected to C1 pin 2), while the wire from C2 pin 1 goes left to a ground glyph at x=209.57, y=70.49 (connected to U1C pin 4). The intended circuit has all REF terminals joined by a common rail or matching power symbols. In the drawing, U1 pin 5 connects to a ground glyph, C2 pin 1 connects to a different ground glyph, and C1 pin 2 connects to yet another ground glyph. These are not visibly joined by a continuous wire trunk nor do they share a single clearly named power symbol in a way that satisfies rail_presentation for the entire net. Specifically, the group containing U1 pin 5, C1 pin 2, C3 pin 2, and J1 pin 5 is wired to one ground glyph, while the group containing U1C pin 4 and C2 pin 1 is wired to a separate ground glyph. This violates rail_presentation which requires every separately drawn terminal group of an asserted rail to touch a power symbol naming that rail, and all such groups must be visibly connected by wire or share the same rail identity. The drawing shows two disconnected REF rail segments.
- power_symbol_clearance: The power symbols for the REF rail (ground glyphs) are placed at x=186.69, y=72.64; x=209.57, y=70.49; and possibly others. These are not touching other drawing items, so clearance is acceptable. However, since rail_presentation fails due to disconnected groups, this issue is secondary.
- rail_route_detour: The REF rail has multiple disconnected segments with no long detours exceeding 7.62 mm, so this metric passes locally but the overall rail continuity fails.
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": true}`

### sallen_key__off_balance_page — accept
- **Known defect:** off_balance_page

### dual_rail_reference__detached_value — revise
- **Known defect:** detached_value
- rail_presentation: The VREF rail is not visibly connected to the amplifier U1C's pin 5 (VREF) via a wire or power symbol. Instead, it connects only through text labels 'VREF' at positions (90.17, 57.785), (168.91, 54.61), etc., which is insufficient per the review brief.
- rail_presentation: The VPLUS rail is not visibly connected to amplifier U1C's pin 8 (V+) via a wire or power symbol. It connects only through text labels 'VPLUS' at positions (105.49, 52.7), etc., which is insufficient per the review brief.
- rail_presentation: The VMINUS rail is not visibly connected to amplifier U1C's pin 4 (V-) via a wire or power symbol. It connects only through text labels 'VMINUS' at positions (104.95, 67.94), etc., which is insufficient per the review brief.
- *Requested edit:* `{"operation": "connect_rail", "net": "VREF", "replace_existing": true}`

### dual_rail_reference__overlapping_fields — revise
- **Known defect:** overlapping_fields
- rail_presentation: The VREF rail is not visibly connected to the amplifier U1C (pins 4, 8) or the capacitors C1/C2 in a way that satisfies the visual rubric. The intended circuit defines VREF as the midpoint between R1 and R2, but the SVG shows no wire connecting the junction of R1/R2 to the pins of U1C or the plates of C1/C2. Instead, separate wires connect R1 to VPLUS and R2 to VMINUS, leaving the central node (VREF) electrically isolated in the drawing.
- rail_presentation: The power symbols #FLG01 and #FLG02 are present but do not visually join the separated groups of the VPLUS and VMINUS rails as required. The SVG shows wires for VPLUS and VMINUS that terminate at component pins without a continuous wire trunk or a matching power symbol on each group.
- rail_presentation: Power symbols #FLG01 and #FLG02 are placed near the amplifier U1C but do not visually connect to the rail terminals. The SVG shows no glyph or arrow for these flags, violating the requirement that each separately wired part of a rail must end at a power symbol naming that rail.
- *Requested edit:* `{"operation": "connect_rail", "net": "VREF", "replace_existing": true}`

### dual_rail_reference__distant_reference — revise
- **Known defect:** distant_reference
- rail_presentation: The VREF rail is not visibly connected to the amplifier U1C (pins 8, 4) or capacitors C1/C2 in a way that satisfies the visual rubric. The intended circuit defines VREF as the midpoint between R1/R2, but the drawing shows U1C's power pins (8, 4) connected directly to VPLUS and VMINUS rails without an explicit connection to the VREF net formed by the resistor divider. This violates the requirement that every terminal of an asserted rail must be visibly connected to that rail or a matching power symbol.
- rail_presentation: The VREF rail is not visibly connected to the amplifier U1B (pin 5) or capacitors C2/C1 in a way that satisfies the visual rubric. The intended circuit defines VREF as the midpoint between R1/R2, but the drawing shows U1B's power pin (5) connected directly to the VMINUS rail without an explicit connection to the VREF net formed by the resistor divider. This violates the requirement that every terminal of an asserted rail must be visibly connected to that rail or a matching power symbol.
- rail_presentation: The VREF rail is not visibly connected to the amplifier U1A (pin 5) or capacitors C2/C1 in a way that satisfies the visual rubric. The intended circuit defines VREF as the midpoint between R1/R2, but the drawing shows U1A's power pin (5) connected directly to the VMINUS rail without an explicit connection to the VREF net formed by the resistor divider. This violates the requirement that every terminal of an asserted rail must be visibly connected to that rail or a matching power symbol.
- *Requested edit:* `{"operation": "connect_rail", "net": "VREF", "replace_existing": true}`

### dual_rail_reference__off_balance_page — revise
- **Known defect:** off_balance_page
- rail_presentation: The VREF rail is not visibly connected to the amplifier U1C (pins 4, 8) or capacitor C1/C2. Terminals for U1C pins 4 and 8 are present but lack visible wire connections to a common VREF trunk or power symbol.
- rail_presentation: The VMINUS rail is not visibly connected to amplifier U1C pin 4 or capacitor C2 pin 2. These terminals exist but are not joined by wires to the main VMINUS net.
- rail_presentation: The VPLUS rail is not visibly connected to amplifier U1C pin 8 or capacitor C1 pin 1. These terminals exist but lack wire connections to the main VPLUS trunk.
- *Requested edit:* `{"operation": "connect_rail", "net": "VREF", "replace_existing": true}`

### timer_astable__detached_value — revise
- **Known defect:** detached_value
- rail_presentation: The VCC rail is not correctly presented. Terminal U1 pin 4 (VCC) and terminal U1 pin 8 (VCC) are connected to the net, but they are not visibly joined by a continuous wire trunk or marked by a matching power symbol on their respective groups. Specifically, the wire from J1 Supply connects to R1, which then connects to C2 and U1 pin 4/8, but there is no explicit visual indication (like a supply arrow) at the points where the rail enters the connector or component pins as required by the layout brief for power units.
- rail_presentation: The REF rail is not correctly presented. Terminal J3 Return connects to C2 and U1 pin 1, but these terminals are not visibly joined by a continuous wire trunk or marked by a matching ground glyph on their respective groups. The wire from J3 goes to C2 and U1 pin 1, but there is no explicit visual indication (like a ground glyph) at the points where the rail enters the component pins as required by the layout brief for return rails.
- *Requested edit:* `{"operation": "connect_rail", "net": "VCC", "replace_existing": true}`

### timer_astable__overlapping_fields — revise
- **Known defect:** overlapping_fields
- rail_presentation: The VCC rail is visually disconnected at the output of U1 pin 3 (OUT). The wire from U1 pin 3 goes to J2, but there is no visible connection back to the main VCC rail or a power symbol. This violates the requirement that every terminal of an asserted VCC rail must be visibly connected to that rail.
- rail_presentation: The REF rail at U1 pin 1 (GND) has a wire going to J3, but the visual path is ambiguous and does not clearly show a continuous connection to the main REF rail or a power symbol.
- label_association: The label 'REF' near U1 pin 1 is visually close to the GND symbol but the connection path is not clearly visible, making it difficult to associate the label with its owning symbol.
- *Requested edit:* `{"operation": "connect_rail", "net": "VCC", "replace_existing": true}`

### timer_astable__distant_reference — revise
- **Known defect:** distant_reference
- rail_presentation: The VCC rail is visually disconnected at U1 pin 8. The wire from J1 (Supply) to U1 pin 8 is missing, leaving the power symbol at U1 pin 8 floating without a visible connection to the supply source.
- rail_presentation: The REF rail is visually disconnected at C2. The wire connecting C2 pin 2 to the main REF net trunk is missing, leaving the ground glyph at C2 isolated from the return path defined by J3 and U1 pin 1.
- *Requested edit:* `{"operation": "connect_rail", "net": "VCC", "replace_existing": true}`

### timer_astable__off_balance_page — revise
- **Known defect:** off_balance_page
- rail_presentation: The VCC rail is visually disconnected at U1 pin 8. The wire from J1 (Supply) to U1 pin 8 is missing, leaving the terminal floating despite the netlist equivalence.
- rail_presentation: The REF rail is visually disconnected at U1 pin 1. The wire connecting U1 pin 1 to the main REF trunk is missing, leaving the terminal floating.
- rail_presentation: The CONT rail is visually disconnected at C2 pin 1. The wire from C2 pin 1 to the main CONT trunk is missing, leaving the terminal floating.
- rail_presentation: The TIMING rail is visually disconnected at U1 pins 2 and 6. The wires connecting these pins to the main TIMING trunk are missing, leaving the terminals floating.
- rail_presentation: The DISCH rail is visually disconnected at R2 pin 1. The wire from R2 pin 1 to the main DISCH trunk is missing, leaving the terminal floating.
- *Requested edit:* `{"operation": "connect_rail", "net": "VCC", "replace_existing": true}`

### reference_555_led_flasher_v8__detached_value — INVALID
- **Known defect:** detached_value
- **Reviewer:** no usable answer (model response exceeded its output token limit)

### reference_555_led_flasher_v8__overlapping_fields — revise
- **Known defect:** overlapping_fields
- Issue 1: Rail Presentation Failure for VCC. The intended circuit defines a single 'VCC' net connecting J1, R1, R3, U1 pins 4 and 8. In the SVG, the wire segment from U1 pin 8 (x=91.44, y=49.53) to U1 pin 4 (x=78.74, y=54.61) is missing. The path data shows a connection from U1 pin 8 to the top rail trunk at x=91.44, but no wire connects this trunk to the VCC label or other components on that rail level in the vicinity of the timer's power pins. Specifically, the terminal inventory lists U1 pin 8 and U1 pin 4 as members of 'VCC', but the SVG paths do not show a continuous wire joining them or joining them to the main VCC supply line from J1/R1/R3. This violates the rail_presentation criterion that every terminal must be visibly connected by wire or a matching power symbol.
- Issue 2: Rail Presentation Failure for REF. The intended circuit defines a single 'REF' net connecting C2, J3, U1 pin 1, and C1. In the SVG, the wire segment from U1 pin 1 (x=88.9, y=69.85) to the main REF rail trunk is missing. The path data shows a connection from U1 pin 1 to the GND symbol at x=88.9, but no wire connects this trunk to the main REF supply line from J3/C2/C1 in the vicinity of the timer's reference pin. This violates the rail_presentation criterion that every terminal must be visibly connected by wire or a matching power symbol.
- Issue 3: Rail Presentation Failure for TIMING. The intended circuit defines a single 'TIMING' net connecting R2, U1 pins 2 and 6, and C1. In the SVG, the wire segment from U1 pin 2 (x=78.74, y=64.77) to U1 pin 6 (x=78.74, y=62.23) is missing. The path data shows a connection from U1 pin 2 to the TIMING rail trunk at x=78.74, but no wire connects this trunk to the main TIMING supply line from R2/C1 in the vicinity of the timer's timing pins. This violates the rail_presentation criterion that every terminal must be visibly connected by wire or a matching power symbol.
- *Requested edit:* `{"operation": "connect_rail", "net": "VCC", "replace_existing": true}`

### reference_555_led_flasher_v8__distant_reference — revise
- **Known defect:** distant_reference
- Issue 1: Rail Presentation Failure (VCC Net). The VCC rail is not correctly presented. While the power symbol at U1 pin 8 and R1 pin 1 are named 'VCC', the terminal at J1 (Supply) is connected to a net labeled 'VCC' but lacks a visible wire connection to the main VCC trunk or a matching power symbol on its own group in a way that satisfies `rail_presentation`. The SVG shows a path from J1's pin 1 to a connector body, but the visual continuity to the main supply rail is ambiguous without explicit wiring to the shared trunk or a dedicated power symbol for that specific branch. Specifically, the terminal at J1 (Supply) appears isolated from the main VCC distribution network in the drawing, failing the requirement that every terminal of an asserted REF/VCC rail must be visibly connected by wire or a matching power symbol.
- Issue 2: Rail Presentation Failure (REF Net). The REF rail is not correctly presented. The terminal at J3 (Return) is connected to a net labeled 'REF' but lacks a visible wire connection to the main REF trunk or a matching ground/power symbol on its own group in a way that satisfies `rail_presentation`. The SVG shows a path from J3's pin 1 to a connector body, but the visual continuity to the main return rail is ambiguous without explicit wiring to the shared trunk or a dedicated power symbol for that specific branch. Specifically, the terminal at J3 (Return) appears isolated from the main REF distribution network in the drawing, failing the requirement that every terminal of an asserted REF/VCC rail must be visibly connected by wire or a matching power symbol on its own group.
- *Requested edit:* `{"operation": "connect_rail", "net": "VCC", "replace_existing": true}`

### reference_555_led_flasher_v8__off_balance_page — INVALID
- **Known defect:** off_balance_page
- **Reviewer:** no usable answer (model response exceeded its output token limit)

## known-good (15)

### dual_buffer__known_good — accept
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)

### dual_rail_reference__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- rail_presentation: The VREF rail is not visibly connected to the amplifier U1C (pins 5, 8, 4) or the capacitors C1/C2 in a way that satisfies the visual rubric. The intended circuit defines VREF as the midpoint of R1/R2 and connects to pins 5, 8, 4 of U1C, pin 1/2 of C1/C2, and pin 5 of J1. In the SVG, there is no continuous wire from the R1/R2 junction to the amplifier supply pins or capacitor midpoints; instead, separate wires connect VPLUS and VMINUS rails directly to the amplifier power pins (8 and 4) without an explicit VREF connection path visible. This violates rail_presentation for the VREF net.
- rail_presentation: The VPLUS rail connects to J1 pin 3, R1 pin 1, C1 pin 1, and U1C pin 8, but the wire from R1 to C1/U1C is not continuous with a shared trunk; it appears as separate segments. Similarly, VMINUS connects to J1 pin 4, R2 pin 2, C2 pin 2, and U1C pin 4, but again lacks a unified visible trunk. This fragmentation fails rail_presentation.
- rail_presentation: Power symbols #FLG01 (VPLUS) and #FLG02 (VMINUS) are present but do not visually join the respective rail groups; they sit on separate wires without being part of a continuous rail presentation. This violates rail_presentation for both VPLUS and VMINUS nets.
- *Requested edit:* `{"operation": "connect_rail", "net": "VREF", "replace_existing": true}`

### inverting_gain__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- rail_presentation: The VPLUS rail is not correctly presented. Terminal U1C pin 8 (V+) at x=82.55, y=71.12 is connected to C1 pin 1 via a wire, but the net label 'VPLUS' is placed at x=88.82, y=71.76, which is visually distant from the terminal group and not clearly associated with it in the intended circuit context where U1C unit 3 (power) should have its positive supply marked or wired to a common VPLUS trunk. The existing wire from U1C pin 8 goes to C1, but there is no visible connection to a power symbol or a shared rail trunk that clearly names 'VPLUS' at the point of entry for the amplifier unit. This violates the requirement that every terminal of an asserted REF/VCC rail must be visibly connected to that rail by wire or a matching power symbol.
- rail_presentation: The VMINUS rail is not correctly presented. Terminal U1C pin 4 (V-) at x=82.55, y=86.36 is connected to C2 pin 2 via a wire, but the net label 'VMINUS' is placed at x=94.44, y=84.46, which is visually distant and not clearly associated with the terminal group. Similar to VPLUS, there is no visible connection to a power symbol or a shared rail trunk that clearly names 'VMINUS' at the point of entry for the amplifier unit.
- label_association: The net label 'VPLUS' at x=88.82, y=71.76 is not visually closest and clearly related to its owning symbol (U1C pin 8) or the terminal group it is meant to name. It appears stranded between the capacitor C1 and the amplifier U1C, failing the owner-association heuristic.
- label_association: The net label 'VMINUS' at x=94.44, y=84.46 is not visually closest and clearly related to its owning symbol (U1C pin 4) or the terminal group it is meant to name. It appears stranded between the capacitor C2 and the amplifier U1C, failing the owner-association heuristic.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### led_long_text__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- rail_presentation: The VPLUS rail (connecting J1 and R123) is visually disconnected. Terminal J1-1 at (27.94, 34.29) connects to a wire that loops back to itself without reaching R123-1 at (57.15, 41.91). The intended series path from VPLUS through R123 to MID is broken by this self-looping wire segment.
- rail_presentation: The REF rail (connecting D24 and J2) is visually disconnected. Terminal D24-1 at (57.15, 60.96) connects to a wire that loops back to itself without reaching J2-1 at (27.94, 66.04). The intended series path from MID through R123 to REF is broken by this self-looping wire segment.
- rail_presentation: The layout violates the owner-readability.v9 brief requirement for straight wiring between power unit terminals and their supply pins. Both rails exhibit unnecessary detours where wires loop back on themselves instead of connecting directly to the opposing terminal group.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### led_reverse_supply__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- rail_presentation: The VNEG rail (J2 pin 1 to D1 pin 1) is not visibly connected. J2 is at (62.23, 41.91) and D1 is at (83.82, 60.96). There are no wires drawn between them in the SVG paths.
- rail_presentation: The LOCAL_REF rail (J1 pin 1 to R1 pin 1) is not visibly connected. J1 is at (34.29, 34.29) and R1 is at (83.82, 41.91). No wire segment connects these points.
- page_composition: The drawing is heavily skewed to the top-left corner of the A4 sheet, leaving excessive unused space on the right and bottom, which violates the balanced functional grouping requirement.
- *Requested edit:* `{"operation": "connect_rail", "net": "VNEG", "replace_existing": true}`

### led_series__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- rail_presentation: The VPLUS rail (J1 pin 1 to R1 pin 1) and the REF rail (D1 pin 1 to J2 pin 1) are asserted in the intended circuit but lack visible power symbols or supply arrows at their terminals. Per the review brief, every terminal of an asserted rail must be visibly connected to a shared wire trunk or end at a matching power symbol. Currently, these rails terminate without explicit power symbols, failing the visual rubric for owner-readability.
- rail_presentation: The MID rail (R1 pin 2 to D1 pin 2) is also missing a power symbol at its termination points, which is required for asserted rails in this schematic context.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### linear_regulator__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- rail_presentation: The REF rail is not correctly presented. Terminal U1 pin 2 (GND) at (110.49, 49.53) connects to C1 and C2 but lacks a visible power symbol (ground glyph) on its own wire segment or shared trunk as required by the brief for separated groups. The rail ends at the junction of C1/C2/GND without a dedicated ground symbol marking that group's return path, violating rail_presentation.
- rail_presentation: Terminal J3 pin 1 (REF) at (52.07, 34.29) connects to a wire leading to a ground glyph but the glyph is not clearly associated with this specific terminal group in the drawing layout; the brief requires each separately wired part of the rail to end at a power symbol naming that rail.
- rail_presentation: Terminal J2 pin 1 (VOUT) at (30.48, 41.91) connects to U1 pin 3 but lacks a visible power symbol or supply arrow on its wire segment as required for the VOUT rail presentation.
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": true}`

### noninverting_gain__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- rail_presentation: The VPLUS rail is not correctly presented. Terminal U1C pin 8 (V+) at x=109.22, y=90.17 is connected to C1 pin 1 (V+) at x=97.79, y=93.98 via a wire, but the group containing these terminals does not touch a power symbol naming VPLUS. The only VPLUS-named terminal is J1 pin 3 at x=68.58, y=91.44, which connects to C1 pin 1 via a wire that passes near U1C pin 8 but the routing appears disjointed or missing a clear trunk to a power symbol for the U1C group.
- rail_presentation: The VMINUS rail is not correctly presented. Terminal U1C pin 4 (V-) at x=109.22, y=105.41 connects to C2 pin 2 (VMINUS) at x=125.73, y=101.6 via a wire, but this group lacks a power symbol naming VMINUS. The only VMINUS-named terminal is J1 pin 4 at x=68.58, y=93.98, which connects to C2 pin 2 via a wire that seems to bypass the U1C group without a clear shared trunk or power symbol for the U1C terminals.
- rail_presentation: The REF rail is not correctly presented. Terminal U1C pin 2 (REF) at x=97.79, y=93.98 connects to C1 pin 2 (REF) at x=97.79, y=101.6 via a wire, but this group lacks a power symbol naming REF. The only REF-named terminal is J1 pin 5 at x=68.58, y=96.52, which connects to C1 pin 2 via a wire that appears to create a disjointed path rather than a clear trunk with a power symbol for the U1C group.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### rc_highpass__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- Issue 1: The REF net (return path) is visually disconnected. Terminal J3-1 and R1-2 are not joined by a continuous wire trunk; instead, they form an open loop with no visible connection to the rest of the circuit's return path.
- Issue 2: The OUT net has a visual discontinuity between C1-2 and J2-1. While electrically connected via the netlist, the drawing shows a gap in the wire path that breaks the visual continuity required for rail_presentation compliance.
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": true}`

### rc_lowpass__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- Issue 1: The REF net (Return) is not visibly connected to a power symbol. The terminals for J3 and C1 are joined by wire, but the rail ends without a ground glyph or supply arrow as required by the visible_local_rails rubric.
- Issue 2: The layout of the return path (J3 to C1) creates a large loop that is visually inefficient and does not follow the 'wired straight' preference for decoupling capacitors described in the review brief.
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": true}`

### rc_to_buffer__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- rail_presentation: The VPLUS rail is not correctly presented. Terminal U1C pin 8 (VMINUS) is connected to a power symbol, but the intended circuit defines U1C pin 8 as part of the VPLUS rail. The drawing shows U1C pin 8 connected to a 'V-' label and a ground-like glyph, which contradicts the intended netlist where pin 8 is positive supply (VPLUS). This indicates a wiring or symbol orientation error for U1C.
- rail_presentation: The VMINUS rail is not correctly presented. Terminal U1C pin 4 is connected to a power symbol labeled 'VMINUS', but the drawing shows U1C pin 4 connected to a 'V+' label and a supply arrow, which contradicts the intended netlist where pin 4 is negative supply (VMINUS). This indicates a wiring or symbol orientation error for U1C.
- rail_presentation: The REF rail is not correctly presented. Terminal U1B pin 5 is connected to a power symbol labeled 'REF', but the drawing shows U1B pin 5 connected to a '+' label and a supply arrow, which contradicts the intended netlist where pin 5 is reference (REF). This indicates a wiring or symbol orientation error for U1B.
- rail_presentation: The REF rail is not correctly presented. Terminal U1B pin 6 is connected to a power symbol labeled 'REF', but the drawing shows U1B pin 6 connected to a '-' label and a ground-like glyph, which contradicts the intended netlist where pin 6 is reference (REF). This indicates a wiring or symbol orientation error for U1B.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### reference_555_led_flasher_v8__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- rail_presentation: The VCC rail is not correctly presented. Terminal U1 pin 8 (VCC) at x=91.44, y=49.53 is connected to a power symbol #FLG01 at x=44.45, y=92.71 via a long wire that crosses other nets and components, but the rail presentation check fails because the terminal U1 pin 8 is not visibly joined to a shared rail trunk or a matching power symbol on its own group in a way that satisfies the rail_presentation gate. The existing long run blocks other connections.
- rail_presentation: The REF rail is not correctly presented. Terminal C2 pin 2 (REF) at x=71.12, y=45.72 is connected to a power symbol #FLG02 at x=54.61, y=85.09 via a long wire that crosses other nets and components, but the rail presentation check fails because the terminal C2 pin 2 is not visibly joined to a shared rail trunk or a matching power symbol on its own group in a way that satisfies the rail_presentation gate. The existing long run blocks other connections.
- rail_presentation: The TIMING rail is not correctly presented. Terminal R2 pin 2 (TIMING) at x=54.61, y=63.5 is connected to a power symbol #FLG02 at x=54.61, y=85.09 via a long wire that crosses other nets and components, but the rail presentation check fails because the terminal R2 pin 2 is not visibly joined to a shared rail trunk or a matching power symbol on its own group in a way that satisfies the rail_presentation gate. The existing long run blocks other connections.
- rail_presentation: The OUT rail is not correctly presented. Terminal D1 pin 1 (OUT) at x=29.21, y=68.58 is connected to a power symbol #FLG02 at x=54.61, y=85.09 via a long wire that crosses other nets and components, but the rail presentation check fails because the terminal D1 pin 1 is not visibly joined to a shared rail trunk or a matching power symbol on its own group in a way that satisfies the rail_presentation gate. The existing long run blocks other connections.
- rail_presentation: The LED_A rail is not correctly presented. Terminal R3 pin 2 (LED_A) at x=29.21, y=53.34 is connected to a power symbol #FLG02 at x=54.61, y=85.09 via a long wire that crosses other nets and components, but the rail presentation check fails because the terminal R3 pin 2 is not visibly joined to a shared rail trunk or a matching power symbol on its own group in a way that satisfies the rail_presentation gate. The existing long run blocks other connections.
- rail_presentation: The DISCH rail is not correctly presented. Terminal R1 pin 2 (DISCH) at x=54.61, y=45.72 is connected to a power symbol #FLG02 at x=54.61, y=85.09 via a long wire that crosses other nets and components, but the rail presentation check fails because the terminal R1 pin 2 is not visibly joined to a shared rail trunk or a matching power symbol on its own group in a way that satisfies the rail_presentation gate. The existing long run blocks other connections.
- rail_presentation: The CONT rail is not correctly presented. Terminal C2 pin 1 (CONT) at x=71.12, y=38.1 is connected to a power symbol #FLG02 at x=54.61, y=85.09 via a long wire that crosses other nets and components, but the rail presentation check fails because the terminal C2 pin 1 is not visibly joined to a shared rail trunk or a matching power symbol on its own group in a way that satisfies the rail_presentation gate. The existing long run blocks other connections.
- *Requested edit:* `{"operation": "connect_rail", "net": "VCC", "replace_existing": true}`

### sallen_key__known_good — accept
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)

### timer_astable__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- Issue 1: Rail Presentation Failure (VCC Net). The VCC rail is not correctly presented. While the power symbol at J1 (#FLG01) and U1 pin 8 are present, the terminal at U1 pin 4 (RST) is connected to a 'VCC' label but lacks a visible wire connecting it to the main VCC trunk or a matching power symbol in its immediate group. The SVG shows a path from J1 to R1, then to C2 and U1 pin 8, but the connection to U1 pin 4 appears to rely on text association without a clear visual wire trunk or local power symbol as required by `rail_presentation`. Specifically, the terminal at (125.73, 53.34) for U1 pin 4 is labeled 'VCC' but does not visibly join the continuous wire group from J1/U1 pin 8/C2 pin 1 in a way that satisfies the grouping requirement without ambiguity.
- Issue 2: Rail Presentation Failure (REF Net). The REF rail has multiple disconnected groups. The terminal at U1 pin 1 (GND) is labeled 'REF' and connected to C1, but the terminal at J3 (Return) is physically separated and connected only via a wire that does not clearly join the main REF trunk in a visually unambiguous manner for all terminals. Specifically, the group containing J3 and U1 pin 1 appears isolated from the group containing C2 and C1 unless a long detour wire exists which is not clearly drawn as a single continuous path in the SVG data provided for that specific net partition.
- Issue 3: Power Symbol Clearance Failure (#FLG01). The power symbol #FLG01 at (72.39, 34.29) has its value 'PWR_FLAG' which might be considered a generic label, but the clearance check `power_symbol_clearance` requires that no glyph or value box touches another drawing item. The proximity of this symbol to J1 and the VCC rail path needs verification against the conservative glyph boxes defined in KiCad 10.0.6 library; if any part of the 'PWR_FLAG' text or glyph overlaps with the wire from J1 or the connector body, it fails.
- Issue 4: Power Symbol Clearance Failure (#FLG02). Similar to #FLG01, the power symbol #FLG02 at (45.72, 34.29) for the REF rail needs to ensure its glyph and 'PWR_FLAG' text do not touch other items like J3 or the wire leading to U1 pin 1.
- Issue 5: Rail Route Detour Exceeds Limit. The connection between the VCC supply (J1) and the timer's VCC pins (U1 pin 8, C2 pin 1) involves a path that may exceed the 7.62 mm detour limit if there are intermediate bends or if the direct rectilinear spanning tree is significantly longer than the drawn wire group. The SVG paths show some orthogonal routing which might accumulate length.
- Issue 6: Label Association Ambiguity. The label 'VCC' at (138.43, 41.1950) for U1 pin 8 and (125.73, 47.5450) for C2 pin 1 are close to the symbol bodies but need to be confirmed as visually closest to their own unit's drawing and not a neighboring symbol's drawing, especially given the density around the timer IC.
- Issue 7: Label Association Ambiguity (REF). The label 'REF' at (140.9489, 69.2149) for U1 pin 1 is rotated and positioned near the GND symbol; ensure it is clearly associated with U1 pin 1 and not confused with other REF labels like those at C1 or J3.
- Issue 8: Page Composition Balance. The drawing center might be offset if the timer IC and its surrounding components (R1, R2, C1, C2) are clustered on one side while connectors J1, J2, J3 are spread out, potentially causing an offset > 0.25 of the frame's half-width/half-height from the usable frame center.
- Issue 9: Visible Local Rails (REF). The terminal at U1 pin 1 is labeled 'REF' and connected to a GND symbol, but the visual continuity with other REF terminals (C1, J3) must be confirmed. If they are not joined by a visible common wire trunk or matching power symbols in separate groups, it fails `visible_local_rails`.
- *Requested edit:* `{"operation": "connect_rail", "net": "VCC", "replace_existing": true}`

### timer_astable_gnd__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- rail_presentation: The VCC rail is visually disconnected at U1 pin 4 (RST). The wire from the timing network node (U1 pin 2/6) does not connect to U1 pin 4. The intended circuit requires RST to be tied to VCC, but the drawing shows an open connection or a connection only via text labels without visible wiring.
- rail_presentation: The GND rail is visually disconnected at U1 pin 1 (GND). The wire from the timing network node (U1 pin 2/6) does not connect to U1 pin 1. The intended circuit requires GND to be tied to U1 pin 1, but the drawing shows an open connection or a connection only via text labels without visible wiring.
- *Requested edit:* `{"operation": "connect_rail", "net": "VCC", "replace_existing": true}`

