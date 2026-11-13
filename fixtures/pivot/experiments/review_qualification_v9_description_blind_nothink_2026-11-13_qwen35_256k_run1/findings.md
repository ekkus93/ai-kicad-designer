# Reviewer qualification: text description, blind, reasoning off

Each case: what is known about the drawing, then the reviewer's decision, issues (its own words) and requested edit.

## historical (14)

### dual_buffer__wire_across_power_unit — revise
- **Known defect:** a ground wire runs across U1C between V+ and V-, over its pin names
- Issue: Power rail VPLUS presentation failure. The terminal group at U1C (pin 8) and C1 is separated from the main rail trunk by a long detour via J1 and back, creating an ambiguous visual path. Furthermore, the power flag #FLG01 is placed on the wire segment between J1 and U1C/C1 but points UP towards the component body instead of pointing away from the rail source or clearly indicating the rail entry. This violates the 'supply arrows point up except at connectors' rule when entering a connector, but here it creates confusion about whether the flag marks the rail or just a local node. The rail is not cleanly presented as a single logical entity.
- Issue: Power rail VMINUS presentation failure. Similar to VPLUS, the terminal group at U1C (pin 4) and C2 is separated. The power flag #FLG02 is placed on the wire segment pointing LEFT towards the edge of the page, which is acceptable for a return rail, but the routing creates a 'U' shape that visually merges with the REF net path near J1, reducing clarity.
- Issue: Power rail REF presentation failure. The terminal group at U1C (pin 5) and C2/C1 is separated. The power flag #FLG03 is placed on the wire pointing DOWN. While ground glyphs should point down, this flag is named 'PWR_FLAG' and acts as a supply arrow for the reference rail in this context (or a generic flag). Its placement on a long detour wire makes it hard to associate with the specific terminal group it represents.
- Issue: Label association risk. The label 'U1C' is placed at (74.30, 30.74), which is very close to the body of C1 (body y range 43.69..45.21) and J1. While the distance check passes (>5.08mm), the visual proximity in the dense left-hand column (J1, C1, C2, flags) risks misassociation for a human reader scanning vertically.
- Issue: Wire clutter on net REF. The net REF has 13 segments and forms a large loop connecting U1C, C1, C2, J1, and U1A/B. This long, winding path obscures the direct connection between the amplifier's reference pin (U1.5) and the capacitor tops (C1.2, C2.1), making the circuit topology harder to follow than necessary.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### inverting_gain__wire_across_power_unit — INVALID
- **Known defect:** a ground wire runs across U1C between V+ and V-, over its pin names
- **Reviewer:** no usable answer (model response exceeded its output token limit)

### noninverting_gain__wire_across_power_unit — revise
- **Known defect:** a ground wire runs across U1C between V+ and V-, over its pin names
- rail_presentation: The VPLUS rail is visually split into two disconnected groups. Group 1 (J1.3, C1.1) connects to a power flag at (62.23, 91.44). Group 2 (U1C.8) connects to a wire segment that loops around but does not connect to the main VPLUS trunk or a matching power symbol in a continuous path. The terminal U1C.8 at (109.22, 90.17) is isolated from the visible rail continuity.
- rail_presentation: The VMINUS rail has a similar issue. The terminal U1C.4 at (109.22, 105.41) connects to a wire that loops but fails to join the main VMINUS trunk connected to J1.4 and C2.2 in a single continuous visual path.
- power_symbol_clearance: The power flag for VPLUS at (64.77, 96.52) points down onto the wire segment connecting J1.3 and C1.1, but its position is crowded by the nearby connector pin labels and the start of the loop to U1C.
- power_symbol_clearance: The power flag for VMINUS at (60.96, 93.98) points left into a wire segment that is part of the VMINUS rail, but its placement is too close to the connector body and pin labels, risking visual clutter.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### rc_to_buffer__wire_across_power_unit — INVALID
- **Known defect:** a ground wire runs across U1C between V+ and V-, over its pin names
- **Reviewer:** no usable answer (model response exceeded its output token limit)

### sallen_key__wire_across_power_unit — revise
- **Known defect:** a ground wire runs across U1C between V+ and V-, over its pin names
- rail_presentation: The VPLUS rail is visually disconnected at U1C.8 (pin 8). The terminal inventory lists U1C as a bodyless unit with pin 8 at (198.12, 66.04) on net VPLUS. However, the wire geometry for VPLUS shows a segment from (198.12, 66.04) to (198.12, 69.85), but no continuous path connects this terminal to the main VPLUS trunk or a power symbol. The rail is split into two groups: one connecting J1.3 and C1.1, and another connecting U1C.8 and U1B.8 (if present) or floating. This violates the requirement that every terminal of an asserted REF/VCC rail must be visibly connected to that rail via wire or a matching power symbol.
- power_symbol_clearance: The power flag #FLG01 at (186.69, 69.85) is placed on pin C1.1, which is part of the VPLUS rail. However, the flag's text box and glyph are too close to the C1 symbol body and value label, potentially causing visual clutter or overlap issues that affect readability.
- power_symbol_direction: The ground glyph for REF at (214.63, 69.85) is pointing right instead of down. According to the review brief, ground glyphs should point down unless constrained by pin geometry or other items. This orientation is inconsistent with standard practice and may confuse readers.
- field_owner_association: The reference/value labels for U1C (U1C Reference at 198.75, 59.95 and U1C Value at 198.75, 62.65) are associated with a bodyless unit. While the measurements show they are within acceptable distances, the lack of a visible body makes it harder to visually associate these labels with their respective pins, especially for U1C.4 and U1C.8 which are critical for power rail continuity.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### inverting_gain__r1_r2_text_misplaced — revise
- **Known defect:** R2 10k sits above U1A's input wire and R1 100k sits under U1A's output, nearer the op-amp than their resistors; C1's REF ground symbol sits sideways
- Issue: Power rail VPLUS presentation failure. The terminal group at U1C (pin 8) and C1 is separated from the main trunk by a long detour via J1, but the power flag #FLG01 is placed on pin C1.1 pointing up, which is acceptable, however the rail route for VPLUS has a significant detour (212.09 mm total length) involving a vertical run to y=87.63 and back down. While electrically correct, the visual grouping is cluttered. More critically, the power flag #FLG02 on VMINUS is at (25.40, 40.64) pointing down, but the rail VMINUS has a complex path including a segment from (82.55, 86.36) to (105.41, 86.36). The power symbol clearance is not violated, but the routing is inefficient.
- Issue: Power rail VMINUS presentation failure. Similar to VPLUS, the rail has a long detour. The power flag #FLG02 is on J1.4 pointing down. The terminal U1C (pin 4) is connected via a long wire. The layout does not follow the 'rail pins on top and return below' heuristic strictly for the decoupling caps relative to the op-amp body in a clean mirrored fashion due to the connector placement.
- Issue: Power rail REF presentation optimization. The ground glyphs are present, but the routing between C1.2, C2.1, J1.5, U1.3, and U1.5 is fragmented with multiple segments. A cleaner route would group these terminals more directly.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### inverting_gain__sideways_ground — revise
- **Known defect:** C2's REF ground symbol points sideways (left) instead of down
- rail_presentation: net VPLUS terminal U1.8 (82.55, 71.12) is not visibly joined to a common wire trunk or a matching power symbol; it connects only via text label 'VPLUS' at (26.67, 38.10).
- rail_presentation: net VMINUS terminal U1.4 (82.55, 86.36) is not visibly joined to a common wire trunk or a matching power symbol; it connects only via text label 'VMINUS' at (25.40, 40.64).
- power_symbol_clearance: power symbol #FLG01 at (72.39, 74.93) touches pin C1.1 and its value box; clearance fails.
- power_symbol_direction: supply arrow for VPLUS at (72.39, 74.93) points up but is placed on a wire that does not form a continuous rail trunk to the amplifier's positive supply pin U1.8.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### inverting_gain__long_supply_loops — revise
- **Known defect:** VPLUS and VMINUS run from J1 down the left edge and along the bottom to U1C
- Issue 1: Power rail VPLUS presentation failure. The terminal group at U1C (pin 8) and C1 is separated from the main trunk by a long detour via J1.3, but the power flag #FLG01 is placed on pin C1.1 without a clear visual connection to the main rail wire in the drawing description's wire list for VPLUS. The wire list shows a segment (72.39, 74.93) -> (82.55, 74.93) connecting C1.1 to U1C, but the power flag #FLG01 is at (72.39, 74.93). This placement is acceptable if it marks the rail entry, but the wire geometry for VPLUS shows a complex path that may not visually group all terminals clearly without a continuous trunk or explicit power symbol on each separated group. However, the primary issue is the lack of a clear visual grouping for the VPLUS rail where U1C and C1 are involved, as the wire segments do not form a simple orthogonal trunk.
- Issue 2: Power rail VMINUS presentation failure. Similar to VPLUS, the terminal group at U1C (pin 4) and C2 is separated. The power flag #FLG02 is placed on J1.4, but the wire geometry for VMINUS shows a complex path that may not visually group all terminals clearly.
- Issue 3: Power rail REF presentation failure. The ground glyph at (40.64, 45.72) is on a wire segment, but the wire list for REF shows multiple segments that do not form a simple trunk. The ground glyph at (99.06, 82.55) is on pin C1.2, which is acceptable, but the overall visual grouping of the REF rail is compromised by the complex wire paths.
- Issue 4: Label association for U1C. The reference 'U1C' and value 'NE5532' are placed at (83.19, 66.30) and (83.19, 69.00), respectively, but the component body is drawn without a body (only pin stubs). The labels are within the field_locality limit (<= 25.4 mm) and field_owner_association limit (<= 5.08 mm), but the visual association may be weak due to the lack of a body.
- Issue 5: Wire routing for net OUT. The wire segments for net OUT show a path from U1.1 to J1.2 and R1.2, but the coordinates suggest a non-orthogonal or complex path that may not align with KiCad's 1.27 mm connection grid. Specifically, the segment (99.06, 41.91) -> (107.95, 41.91) has a length of 8.89 mm, which is not a multiple of 1.27 mm.
- Issue 6: Wire routing for net PARK. The wire segments for net PARK show a path from U1.6 to U1.7, but the coordinates suggest a non-orthogonal or complex path that may not align with KiCad's 1.27 mm connection grid. Specifically, the segment (124.46, 44.45) -> (130.81, 44.45) has a length of 6.35 mm, which is not a multiple of 1.27 mm.
- Issue 7: Wire routing for net SUM. The wire segments for net SUM show a path from R2.2 to R1.1 and U1.2, but the coordinates suggest a non-orthogonal or complex path that may not align with KiCad's 1.27 mm connection grid. Specifically, the segment (72.39, 44.45) -> (77.47, 44.45) has a length of 5.08 mm, which is not a multiple of 1.27 mm.
- Issue 8: Wire routing for net VMINUS. The wire segments for net VMINUS show a complex path that may not align with KiCad's 1.27 mm connection grid. Specifically, the segment (26.67, 40.64) -> (30.48, 40.64) has a length of 3.81 mm, which is not a multiple of 1.27 mm.
- Issue 9: Wire routing for net VPLUS. The wire segments for net VPLUS show a complex path that may not align with KiCad's 1.27 mm connection grid. Specifically, the segment (26.67, 38.10) -> (30.48, 38.10) has a length of 3.81 mm, which is not a multiple of 1.27 mm.
- Issue 10: Wire routing for net REF. The wire segments for net REF show a complex path that may not align with KiCad's 1.27 mm connection grid. Specifically, the segment (29.21, 43.18) -> (30.48, 43.18) has a length of 1.27 mm, which is acceptable, but other segments may not be.
- Issue 11: Power symbol clearance for #FLG01. The power flag #FLG01 is placed at (72.39, 74.93), which is on pin C1.1. However, the wire list for VPLUS shows a segment (72.39, 74.93) -> (82.55, 74.93), which may cause the power symbol to touch another drawing item.
- Issue 12: Power symbol clearance for #FLG02. The power flag #FLG02 is placed at (25.40, 40.64), which is on a wire. However, the wire list for VMINUS shows a segment (25.40, 40.64) -> (26.67, 40.64), which may cause the power symbol to touch another drawing item.
- Issue 13: Power symbol clearance for #FLG03. The power flag #FLG03 is placed at (29.21, 43.18), which is on a wire. However, the wire list for REF shows a segment (29.21, 43.18) -> (30.48, 43.18), which may cause the power symbol to touch another drawing item.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### inverting_gain__long_ref_wire_and_loop — revise
- **Known defect:** a long REF wire from J1 to U1A's + input, and C2's ground wired by a loop over U1C close under its NE5532 text
- rail_presentation: net VMINUS terminal U1.4 (82.55, 86.36) has a power symbol pointing left instead of up/down; flag at (24.13, 40.64) points down on a return rail.
- power_symbol_clearance: REF ground glyph at (40.64, 45.72) and VMINUS supply arrow at (24.13, 40.64) are positioned on wires where they should be adjacent to terminals or connectors; VPLUS arrow at (82.55, 71.12) points right into the component body.
- label_association: U1C Reference/Value fields are >5.08 mm from their own unit's drawing and nearer another part's drawing.
- *Requested edit:* `{"operation": "move_field", "reference": "U1C", "unit": 3, "field": "Reference", "x_mm": 82.55, "y_mm": 64.395, "angle": 0}`

### inverting_gain__decoupling_detour — revise
- **Known defect:** C2's VMINUS wire leaves U1C pin 4, runs right under C2 and back up to C2's top pin (40.64 mm); C2's REF symbol sits 1.27 mm above that wire
- Issue 1: Power rail VPLUS presentation failure. The terminal at U1C pin 8 (VPLUS) has a supply arrow pointing right, which violates the Layout (v8) requirement that 'supply arrows point up except at connectors'. Additionally, the power symbol clearance is compromised as the symbol touches the body of U1C.
- Issue 2: Power rail VMINUS presentation failure. The terminal at J1 pin 4 (VMINUS) has a supply arrow pointing left. While sideways arrows are allowed for ground glyphs in limitations, the Layout brief specifies 'supply arrows point up'. A left-pointing arrow on a vertical wire segment is non-standard and reduces readability.
- Issue 3: Power rail REF presentation failure. The power symbol at C1 pin 2 (REF) has a ground glyph pointing down. While this is standard for ground, the text label 'REF' is positioned such that it overlaps with the nearest other part U1C (distance 17.77 mm to value box), which is within the 25.4 mm locality limit but risks visual crowding if components move.
- Issue 4: Label association risk for C1. The reference 'C1' is 6.72 mm from its body, and the value '100n' is 5.57 mm from its body. While within limits, these distances are on the higher end of acceptable ranges (<= 5.08 mm owner-association heuristic), potentially reducing legibility if zoomed out.
- Issue 5: Label association risk for C2. The reference 'C2' is 6.09 mm from its body, and the value '100n' is 4.95 mm from its body. Similar to Issue 4, these distances are close to the owner-association limit.
- Issue 6: Label association risk for R1. The reference 'R1' is 3.97 mm from its body, and the value '100k' is 1.27 mm from its body. The value is at the minimum grid alignment distance, which is acceptable but leaves no margin for error.
- Issue 7: Label association risk for R2. The reference 'R2' is 3.97 mm from its body, and the value '10k' is 1.27 mm from its body. Similar to Issue 6.
- Issue 8: Label association risk for U1A. The reference 'U1A' is 4.23 mm from its body, and the value 'NE5532' is 1.53 mm from its body. The value is very close to the body.
- Issue 9: Label association risk for U1B. The reference 'U1B' is 4.23 mm from its body, and the value 'NE5532' is 1.53 mm from its body. Similar to Issue 8.
- Issue 10: Label association risk for U1C. The reference 'U1C' is 5.24 mm from its body, and the value 'NE5532' is 2.54 mm from its body. The reference is close to the 5.08 mm owner-association limit.
- Issue 11: Label association risk for J1. The reference 'J1' is 3.97 mm from its body, and the value 'Conn_01x05' is 1.27 mm from its body. Similar to Issue 6.
- Issue 12: Page composition balance issue. The drawing centre offset is <= 0.25, but the layout of power symbols and flags near the left edge (J1, VMINUS, VPLUS) creates an asymmetrical visual weight compared to the right side (U1B, PARK).
- *Requested edit:* `{"operation": "move_field", "reference": "#FLG01", "unit": 1, "field": "Reference", "x_mm": 26.67, "y_mm": 40.64, "angle": 0}`

### inverting_gain__vminus_by_pin_name — revise
- **Known defect:** the VMINUS rail name sits about 1 mm right of U1C's V- pin name
- rail_presentation: net VPLUS has a terminal group (U1.8, C1.1) connected by wire but the power symbol at U1.8 points right instead of up; this violates the Layout(v8) rule that supply arrows point up except at connectors.
- power_symbol_clearance: power symbol #FLG01 at (72.39, 74.93) touches pin C1.1 and its own text box is within 5.08 mm of U1C's drawing, risking overlap with nearby labels.
- label_association: label "U1C" at (96.40, 77.39) is 11.78 mm from its body; while within the 25.4 mm locality limit, it is visually distant and may be ambiguous for quick reading compared to labels closer to their bodies.
- *Requested edit:* `{"operation": "move_field", "reference": "#FLG01", "unit": 1, "field": "Reference", "x_mm": 72.39, "y_mm": 74.93, "angle": 0}`

### inverting_gain__vminus_above_c2_text — revise
- **Known defect:** the VMINUS rail name sits about 1 mm above C2's C2 / 100n text
- rail_presentation: net VPLUS terminal U1.8 (pin 8) has a power symbol but the rail wire from J1.3 to U1.8 is broken; the segment (82.55, 74.93)->(82.55, 71.12) exists but the connection at U1.8 pin 8 is not visually joined to the trunk in a continuous manner per owner-readability.v9 expectations for straight decoupling paths.
- rail_presentation: net VMINUS terminal U1.4 (pin 4) has a power symbol but the rail wire from J1.4 to U1.4 is broken; the segment (82.55, 86.36)->(87.63, 86.36) exists but the connection at U1.4 pin 4 is not visually joined to the trunk in a continuous manner per owner-readability.v9 expectations for straight decoupling paths.
- power_symbol_clearance: power symbol #FLG01 at (72.39, 74.93) touches C1 body; move_field required.
- power_symbol_clearance: power symbol #FLG02 at (26.67, 40.64) is too close to J1 body and wire runs; move_field required.
- power_symbol_clearance: power symbol #FLG03 at (29.21, 43.18) is too close to J1 body and wire runs; move_field required.
- *Requested edit:* `{"operation": "move_field", "reference": "#FLG01", "unit": 1, "field": "Reference", "x_mm": 75.0, "y_mm": 74.93, "angle": 0}`

### timer_astable__vcc_arrows_into_text — revise
- **Known defect:** R1's VCC arrow points down into R1's 10k; the RST VCC arrow points sideways
- rail_presentation: net VCC has terminals at J1.1, R1.1, U1.4, U1.8 but no single continuous wire trunk or shared power symbol; each terminal group ends at a separate supply arrow pointing in different directions (up/down/left) without joining to a common rail glyph.
- power_symbol_clearance: VCC supply arrow at (97.79, 36.83) points down into the body of R1 (pin 1 at 101.60, 36.83), violating clearance; VCC arrow at (125.73, 50.80) points left into U1 body.
- power_symbol_direction: REF ground glyph at (135.89, 68.58) on pin U1.1 points right instead of down, and VCC arrows point inconsistently (up/down/left) rather than consistently up for supply rails.
- label_association: field "REF" at (49.53, 41.99) is visually closest to J3 but the glyph is on a wire segment near J3; field "VCC" at (76.20, 27.86) is far from its own pin stub and closer to J1 body than the intended rail trunk.
- *Requested edit:* `{"operation": "connect_rail", "net": "VCC", "replace_existing": true}`

### reference_555_led_flasher_v8__vcc_arrow_at_ref_text — INVALID
- **Known defect:** the RST VCC arrow points at C2's REF text; C1's REF crowds J1's Supply text
- **Reviewer:** no usable answer (model response exceeded its output token limit)

## injected (32)

### rc_lowpass__detached_value — accept
- **Known defect:** detached_value

### rc_lowpass__overlapping_fields — revise
- **Known defect:** overlapping_fields
- Issue: Field '10n' (C1 Value) is located at (69.85, 36.07), which is 27.08 mm from C1's body and only 3.97 mm from R1. This violates the field_owner_association limit of <= 5.08 mm and creates ambiguity between C1 and R1.
- Issue: Field 'R1' (R1 Reference) is located at (69.85, 36.07), overlapping exactly with the location of the '10n' field for C1 in the provided description (though coordinates differ slightly in text vs box, the proximity to C1 is 27.08 mm). The description states 'R1' field is 3.97 mm from R1's body but 27.08 mm from C1. However, the '10n' field for C1 is also at (69.85, 36.07) in the text list, creating a direct overlap or extreme proximity issue where one component's value is visually associated with another component's reference.
- Correction on Issue 2 based on strict coordinate reading: The '10n' field for C1 is at (69.85, 36.07). The 'R1' reference field is also listed at (69.85, 36.07). This is a direct overlap of two fields at the exact same coordinates, which is physically impossible in a standard drawing but indicates a data error or severe collision. Even if treated as adjacent, the distance between C1's body and its own '10n' value is 27.08 mm, far exceeding the 5.08 mm owner_association limit.
- Issue: Field 'J3' (J3 Reference) is at (35.56, 43.44). Its nearest other part is J1 at 7.03 mm. While this passes the 25.4 mm locality check, the vertical separation between J1 and J3 connectors is small, potentially causing visual crowding if labels are not perfectly aligned, though currently acceptable.
- *Requested edit:* `{"operation": "move_field", "reference": "C1", "unit": 1, "field": "Value", "x_mm": 78.74, "y_mm": 65.0, "angle": 0}`

### rc_lowpass__distant_reference — revise
- **Known defect:** distant_reference
- Issue: R1 Reference label 'R1' is visually stranded and ambiguous.
- Description: The reference label 'R1' for the resistor is located at (30.48, 30.48). Its nearest other part is J1 at only 2.96 mm. This violates the `field_owner_association` heuristic (<= 5.08 mm) and creates a visual ambiguity where the label appears closer to connector J1 than to its own component body R1, which is rotated 90 degrees and located far away.
- Action: move_field
- Parameters: {"field": "Reference", "reference": "R1", "unit": 1, "from_x_mm": 30.48, "from_y_mm": 30.48, "to_x_mm": 67.31, "to_y_mm": 40.89}
- *Requested edit:* `{"operation": "move_field", "reference": "R1", "unit": 1, "field": "Reference", "x_mm": 67.31, "y_mm": 40.89, "angle": 0}`

### rc_lowpass__off_balance_page — accept
- **Known defect:** off_balance_page

### led_series__detached_value — revise
- **Known defect:** detached_value
- rail_presentation: Net REF is visually disconnected from any power symbol. The net connects D1.1 and J2.1, but no ground glyph or supply arrow is present to assert the rail name 'REF'. This violates the requirement that every terminal of an asserted rail must join a visible common wire trunk or end at a matching power symbol.
- rail_presentation: Net VPLUS lacks a supply arrow. The net connects J1.1 and R1.1, but no supply arrow is present to assert the rail name 'VPLUS'. This violates the requirement that every terminal of an asserted rail must join a visible common wire trunk or end at a matching power symbol.
- power_symbol_direction: No power symbols are present to verify direction, but given the missing symbols, the layout cannot be confirmed as compliant with supply arrows pointing up or ground glyphs pointing down. The absence of these symbols constitutes a presentation failure for asserted rails.
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": false}`

### led_series__overlapping_fields — revise
- **Known defect:** overlapping_fields
- Issue: Rail Presentation Failure for net REF.
- Description: The intended circuit defines a 'REF' rail connecting D1.1 and J2.1. However, the schematic drawing shows no visible wire connecting these two terminals directly or via a common trunk. Instead, the connection relies on a complex path of segments that visually zig-zag (e.g., moving horizontally then vertically) rather than forming a clean, continuous rail as per the 'Layout (v8)' brief which expects straight wiring to supply pins where possible. Furthermore, there are no power symbols (ground glyphs) present to mark this return rail, violating the requirement that separated terminal groups must touch a power symbol or join a visible common wire trunk.
- Location: Between D1 pin 1 (83.82, 60.96) and J2 pin 1 (54.61, 66.04).
- Action: connect_rail
- Parameters: {"net": "REF", "set_from_ref": "D1", "set_from_pin": "1", "set_to_ref": "J2", "set_to_pin": "1", "set_replace_existing": true}
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": true}`

### led_series__distant_reference — revise
- **Known defect:** distant_reference
- Issue: R1 Reference label 'R1' is visually stranded and ambiguous. The label is located at (36.83, 30.48) with a gap of 44.57 mm from its own body (R1 pin column), while the nearest other part (J1) is only 20.19 mm away. This violates the `field_owner_association` heuristic (<= 5.08 mm) and creates a readability problem where the label does not clearly associate with its component.
- Issue: R1 Value label '1k' has a gap of 1.89 mm from its body, which is acceptable, but its nearest other part is D1 at 9.15 mm. While within limits, combined with the stranded reference label, it contributes to poor visual grouping for the resistor component.
- Issue: The REF net wiring exhibits excessive detouring and non-orthogonal routing segments that complicate reading flow. Specifically, the wire path from J2.1 to D1.1 involves multiple horizontal and vertical segments creating a 'staircase' pattern (e.g., (49.53, 66.04) -> (50.80, 66.04) -> (52.07, 66.04)). This violates the `Layout (v8)` requirement for 'wired straight to its supply pin' and creates visual clutter.
- Issue: The VPLUS net wiring also shows unnecessary detours. The path from J1.1 to R1.1 includes segments like (49.53, 29.21) -> (83.82, 29.21), which suggests a wide horizontal run that may not be necessary if the connector pins are closer or if routing can be optimized to avoid crossing potential future signal paths, though currently no other nets cross it. However, the presence of multiple segments indicates a lack of direct orthogonal routing.
- Issue: Power symbols are missing for the asserted rails (REF and VPLUS). According to `visible_local_rails`, every terminal of an asserted rail must be visibly connected by wire or a matching power symbol. Currently, there are no power symbols drawn for REF or VPLUS, relying solely on text labels which is insufficient per the brief ('Repeated same-name net labels alone are not accepted').
- Issue: The page composition lacks clear functional grouping due to the scattered placement of the R1 component and its labels far from the main vertical signal path (D1-R1-J2). The R1 reference label is isolated on the left side, breaking the visual flow.
- Issue: Junction dots are missing at wire intersections or T-junctions where wires meet components or other wires. For example, at (83.82, 66.04) where the vertical REF wire meets the horizontal segment from J2, a junction dot should be present to clarify connectivity, though KiCad often implies this; however, the brief mentions 'Junction Dots: none' in the description, suggesting they might be expected or that their absence contributes to ambiguity if not clearly resolved by geometry.
- *Requested edit:* `{"operation": "move_field", "reference": "R1", "unit": 1, "field": "Reference", "x_mm": 83.82, "y_mm": 45.0, "angle": 90}`

### led_series__off_balance_page — revise
- **Known defect:** off_balance_page
- Issue: Missing Power Symbols for Asserted Rails.
- Description: The intended circuit defines three nets (VPLUS, REF, MID). According to the review brief and `visible_local_rails` criteria, every terminal of an asserted rail must be visibly connected to a shared wire trunk or end at a matching power symbol. Currently, there are no power symbols drawn for VPLUS, REF, or MID. The wires exist but terminate without explicit power symbols naming the rails.
- Location: Entire schematic page (nets VPLUS, REF, MID).
- Severity: Critical (fails `rail_presentation` and `visible_local_rails`).
- Action: Request `use_power_symbols` for nets VPLUS, REF, and MID to draw the whole rail with appropriate power symbols (supply arrows for VPLUS/MID, ground glyph for REF if treated as return, or supply arrows if all are supplies; based on 'Input'/'Return' values, VPLUS is likely a positive supply, REF is likely GND/return, MID is intermediate. However, without explicit power assertions in the netlist provided in `intended_circuit`, we must assume standard KiCad behavior where nets need symbols if they are power rails. The brief says 'asserted power rails'. Since `power_assertions` is empty in `intended_circuit`, but the review brief implies checking for them, and the current state has none, this is a presentation failure.
- Correction Logic: The `use_power_symbols` action will place symbols on the existing wire groups. For VPLUS (Input), an arrow pointing up or to the side. For REF (Return from J2), a ground glyph. For MID, if it's just a node between R1 and D1, it might not need a symbol unless asserted as a rail. However, the `visible_local_rails` check requires symbols for *asserted* rails. Given the component values ('Input', 'Return'), VPLUS and REF are likely power rails. MID is an intermediate net. I will request symbols for VPLUS and REF.
- Refined Action: Request `use_power_symbols` for net VPLUS and net REF.
- *Requested edit:* `{"operation": "use_power_symbols", "net": "VPLUS"}`

### linear_regulator__detached_value — revise
- **Known defect:** detached_value
- Issue: Power flag #FLG01 (VIN) is pointing left instead of up. The brief requires supply arrows/flags to point up except at connectors. Position: (74.93, 41.91). Action: Rotate or re-place the power symbol to point upwards.
- Issue: Power flag #FLG02 (REF) is pointing down but is placed on a wire segment rather than directly adjacent to the terminal it represents, and its position (48.26, 34.29) is disconnected from the main REF rail trunk which runs horizontally at y=68.58 and vertically at x=110.49. The brief requires every terminal of an asserted rail to be visibly connected to that rail via a shared wire or a matching power symbol on each separately drawn group. This flag appears stranded or misaligned with the main REF net topology. Position: (48.26, 34.29). Action: Remove this stray flag and ensure the REF rail is presented with a single continuous wire trunk or appropriate power symbols at distinct entry points.
- Issue: The VOUT net has two separate wire groups (one to J2, one to C2/U1) but lacks a power symbol for the VOUT rail. While not strictly forbidden if wired continuously, the brief suggests power flags sit where rails enter connectors or on their own wires. However, the primary issue is the lack of visual continuity or explicit marking for the VOUT rail's separate branches if they are not joined by a visible trunk. Currently, J2 and C2/U1 are separated. Action: Connect the VOUT wire from U1.3 to J2.1 directly to form a continuous trunk, or add a power symbol if separation is intentional but needs marking. Given the brief's preference for straight wiring to supply pins, connecting them is preferred.
- Issue: The REF net has a complex routing with multiple segments and junctions that might be visually cluttered. Specifically, the wire from U1.2 goes up to (110.49, 68.58) then right to C2.2 and left to C1.2. This is electrically correct but could be simplified. However, without a clear visual defect like overlap or illegibility, this might pass. But the stray flag #FLG02 at (48.26, 34.29) is definitely an issue as it doesn't connect to the main REF rail trunk.
- Issue: The VOUT net label at (127.00, 41.91) is very close to the C2 component and wire. Check for overlap or crowding. Position: (127.00, 41.91). Action: Move the VOUT label if it overlaps or is too close to other elements.
- *Requested edit:* `{"operation": "move_field", "reference": "#FLG01", "unit": 1, "field": "Value", "x_mm": 74.93, "y_mm": 41.91, "angle": 0}`

### linear_regulator__overlapping_fields — revise
- **Known defect:** overlapping_fields
- rail_presentation: The REF net is split into two disconnected visual groups. Group 1 (J3, U1) has a ground glyph at (52.07, 38.10). Group 2 (C1, C2) has a ground glyph at (97.79, 68.58). However, the wire connecting these groups ((97.79, 68.58)->(123.19, 68.58)) is part of the rail but lacks a clear visual trunk or explicit connection marker between the U1 ground pin and the C1/C2 capacitors in the upper region, creating ambiguity about whether the top capacitors are truly tied to the same REF potential as the bottom section without relying solely on netlist equivalence. Specifically, the wire segment (97.79, 68.58) -> (123.19, 68.58) connects C1 and C2, but the path from U1 to this trunk is via (110.49, 49.53)->(111.76, 49.53)->(111.76, 68.58). The visual flow from the regulator's GND pin to the capacitor bank is interrupted by a T-junction at (111.76, 49.53) which might be visually cluttered or ambiguous depending on rendering, but more critically, the layout does not strictly follow the 'mirrored across' or straight-to-supply pin aesthetic for the REF rail relative to the VIN/VOUT rails which are cleaner.
- power_symbol_clearance: The ground glyph at (97.79, 68.58) is placed directly on pin C1.2. While technically allowed, placing a power symbol exactly on a component pin can sometimes obscure the pin number or value if they overlap in rendering. The glyph at (52.07, 38.10) is on a wire segment, which is acceptable but less ideal than being adjacent to a terminal for clarity.
- label_association: The label "REF" at (52.07, 41.99) is associated with the glyph at (52.07, 38.10). The label "REF" at (97.79, 72.47) is associated with the glyph at (97.79, 68.58). However, there are no explicit labels for the VIN or VOUT rails in the vicinity of their main trunks except for the net labels "VIN" and "VOUT" which are present. The issue is that the REF rail has two distinct ground symbols, implying a split presentation that might confuse a reader expecting a single continuous rail representation unless the wiring is very explicit. The brief suggests power flags sit where rails enter connectors or on their own wires; here we have ground glyphs. This is acceptable for return rails, but the separation of the REF net into two groups with separate symbols needs to be visually unified or justified by a clear trunk.
- page_composition: The drawing has functional groups (input, regulator, output), but the REF rail's wiring creates a somewhat complex path (U1 -> T-junction -> horizontal wire -> C1/C2). This could be simplified. The VIN and VOUT rails are cleaner. The overall balance is acceptable, but the REF rail complexity detracts from the 'clear reading flow' ideal.
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": true}`

### linear_regulator__distant_reference — revise
- **Known defect:** distant_reference
- Issue 1: Power flag #FLG01 (VIN) is placed at (48.26, 34.29) pointing down, but the VIN rail enters from J1 at (78.74, 41.91). The flag is disconnected from the main VIN wire trunk and points into empty space rather than marking the rail entry point near J1 or U1.
- Issue 2: Power flag #FLG02 (REF) is placed at (74.93, 41.91) pointing left, but the REF rail is a return path with ground glyphs already present at J3 and C1/C2. This flag is misplaced on a wire segment between J3 and U1, not aligned with the rail entry through a connector as per Layout (v8) rules.
- Issue 3: The VIN net label "VIN" at (74.93, 41.91) overlaps with power flag #FLG01's position, causing visual clutter and ambiguity in identifying the rail entry point.
- Issue 4: The REF net label "REF" is missing from the schematic description but implied by power symbols; however, the placement of ground glyphs at (52.07, 38.10) and (97.79, 68.58) does not form a continuous visual trunk for the REF rail as required by visible_local_rails criteria.
- *Requested edit:* `{"operation": "move_field", "reference": "#FLG01", "unit": 1, "field": "Reference", "x_mm": 78.74, "y_mm": 39.37, "angle": 0}`

### linear_regulator__off_balance_page — revise
- **Known defect:** off_balance_page
- Issue: Power flag #FLG01 (VIN) is positioned at (209.55, 38.10) pointing left. According to Layout (v8), power flags should sit where rails enter through a connector if there is room, otherwise on their own wires. The current placement on the wire segment between J1 and U1 is acceptable for 'otherwise', but the orientation 'pointing left' violates the standard convention where flags typically point towards the load or supply direction (often down or right in horizontal layouts) unless constrained. More critically, the flag at (209.55, 38.10) is very close to the net label 'VIN' at (209.55, 38.10). The field inventory shows the Reference text '#FLG01' centered at (209.55, 38.10) and the Net Label 'VIN' also at (209.55, 38.10). This indicates a severe overlap or collision between the power flag's reference label and the net label.
- Issue: Power flag #FLG02 (REF) is positioned at (182.88, 30.48) pointing down. The field inventory shows its Reference text '#FLG02' centered at (182.88, 30.48). This location is adjacent to connector J3's body (x 190.50..193.04). While not overlapping the body directly, the proximity combined with the pointing direction needs verification against clearance rules. However, the primary issue is the overlap at #FLG01.
- Issue: Net label 'VIN' and Power flag #FLG01 share the exact center coordinate (209.55, 38.10). This causes visual ambiguity where the net name and the power symbol reference are indistinguishable or overlapping.
- *Requested edit:* `{"operation": "move_field", "reference": "#FLG01", "unit": 1, "field": "Reference", "x_mm": 209.55, "y_mm": 38.1, "angle": 0}`

### inverting_gain__detached_value — revise
- **Known defect:** detached_value
- Issue 1: Label Association Failure (C1 Value). The value label "100n" for component C1 is located at (146.05, 44.45), which is 69.07 mm from its own body and coincides with the nearest other part U1B. This violates the `field_owner_association` limit of <= 5.08 mm and creates a severe readability problem where the value appears to belong to a different component or is visually stranded.
- Issue 2: Label Association Failure (U1C Reference). The reference label "U1C" is located at (104.02, 77.39), which is 19.40 mm from its own body (a bodyless unit) and 12.29 mm from part C2. This exceeds the `field_owner_association` limit of <= 5.08 mm.
- Issue 3: Label Association Failure (U1C Value). The value label "NE5532" for component U1C is located at (104.02, 80.09), which is 17.64 mm from its own body and 10.53 mm from part C2. This exceeds the `field_owner_association` limit of <= 5.08 mm.
- Issue 4: Power Rail Presentation Failure (VMINUS). The VMINUS rail has terminals at J1.4, U1C.4, and C2.2. The terminal group at C2.2/U1C.4 is connected via a wire to a supply arrow at (87.63, 83.82) pointing right. However, the terminal group at J1.4 is connected to a supply arrow at (24.13, 40.64) pointing left. While electrically valid, the visual presentation of the VMINUS rail is fragmented with arrows pointing in opposite directions across the page, and the text labels are distant from their respective connection points, potentially confusing the reading flow.
- Issue 5: Power Rail Presentation Failure (VPLUS). The VPLUS rail has terminals at J1.3, U1C.8, and C1.1. The terminal group at C1.1 is connected to a supply arrow at (26.67, 38.10) pointing left. The terminal group at U1C.8 is connected to a supply arrow at (82.55, 71.12) pointing right. Similar to VMINUS, the rail is visually split with arrows pointing in opposite directions.
- Issue 6: Power Symbol Clearance Failure (#FLG01). The power flag #FLG01 is located at (72.39, 74.93) on pin C1.1. Its value text "PWR_FLAG" is centered at (72.39, 77.63). This places the flag very close to the component body and potentially overlapping with the component's own reference/value fields or nearby wiring, violating `power_symbol_clearance`.
- Issue 7: Power Symbol Clearance Failure (#FLG02). The power flag #FLG02 is located at (26.67, 40.64) on a wire for VMINUS. Its value text "PWR_FLAG" is centered at (26.67, 43.34). This placement is close to the wire and other drawing items.
- Issue 8: Power Symbol Clearance Failure (#FLG03). The power flag #FLG03 is located at (29.21, 43.18) on a wire for REF. Its value text "PWR_FLAG" is centered at (29.21, 45.88). This placement is close to the wire and other drawing items.
- *Requested edit:* `{"operation": "move_field", "reference": "C1", "unit": 1, "field": "Value", "x_mm": 72.39, "y_mm": 74.93, "angle": 0}`

### inverting_gain__overlapping_fields — revise
- **Known defect:** overlapping_fields
- C1 Value label "100n" at (138.43, 31.75) is misplaced; it belongs to C1 but is located near U1B instead of C1's body.
- U1C Reference label "U1C" at (104.02, 77.39) is too far from its body and visually ambiguous.
- VMINUS supply arrow at (24.13, 40.64) points left instead of up/down as required for a return rail entry.
- VPLUS supply arrow at (26.67, 38.10) points left instead of up/down as required for a supply rail entry.
- REF ground glyph at (80.01, 39.37) is placed on a wire segment rather than directly on the terminal or a dedicated stub.
- *Requested edit:* `{"operation": "move_field", "reference": "C1", "unit": 1, "field": "Value", "x_mm": 62.23, "y_mm": 76.2, "angle": 0}`

### inverting_gain__distant_reference — revise
- **Known defect:** distant_reference
- field_owner_association: The reference/value labels for U1A (U1, NE5532) are located at x=167.64/91.44 and x=138.43/138.43 respectively, which are visually distant from their respective symbol bodies (U1A body x 86.36..96.52; U1B body x 133.35..143.51). The label 'U1A' is 69.14 mm from its own body, and 'U1B' is 4.23 mm from its own body but the text 'NE5532' for U1B is centered at x=138.43 while the body ends at x=143.51, creating a potential association ambiguity given the mirrored layout intent. Specifically, the reference 'U1A' and value 'NE5532' for unit 1 are placed far to the right (x~90-170), while the actual symbol body for U1A is at x~86-96. This violates the visual association heuristic where labels should be close to their own unit's drawing.
- field_owner_association: The reference/value labels for U1C (U1, NE5532) are located at x=104.02/104.02, which is 19.40 mm from its own body (body x 82.55..82.55). This distance exceeds the recommended proximity for clear association, especially since U1C is drawn without a body and relies on pin stubs; the label should be closer to the pin column.
- power_symbol_direction: The VMINUS supply arrow at (24.13, 40.64) points left instead of up or towards its rail entry point as expected for a supply rail entering from a connector or power source. Similarly, the VPLUS supply arrow at (26.67, 38.10) points left, which may not align with the intended flow direction from the connector J1.
- power_symbol_direction: The VMINUS supply arrow at (87.63, 83.82) points right, which is acceptable if it connects to a rail entering from the right, but given the layout of C2 and U1C, the direction should be consistent with the rail's entry point.
- power_symbol_direction: The VPLUS supply arrow at (82.55, 71.12) points right, which is acceptable if it connects to a rail entering from the left, but consistency with other power symbols should be maintained.
- *Requested edit:* `{"operation": "move_field", "reference": "U1A", "unit": 1, "field": "Reference", "x_mm": 92.0, "y_mm": 34.5, "angle": 0}`

### inverting_gain__off_balance_page — INVALID
- **Known defect:** off_balance_page
- **Reviewer:** no usable answer (model response exceeded its output token limit)

### sallen_key__detached_value — revise
- **Known defect:** detached_value
- Issue 1: Power rail VPLUS presentation failure. The terminal at U1 pin 8 (VPLUS) has a supply arrow pointing left, which is acceptable, but the wire segment from C1.1 to U1.8 runs horizontally across the page. While electrically correct, the horizontal run for a top-rail power net often obscures signal paths or creates visual clutter if not routed vertically to a common trunk. However, the primary failure is the VMINUS rail.
- Issue 2: Power rail VMINUS presentation failure. The terminal at U1 pin 4 (VMINUS) has a supply arrow pointing right. The wire segment from C2.2 to U1.4 runs horizontally. More critically, the power symbol at J1.4 points left, and the symbol at U1.4 points right. This creates a 'V' shape or divergent flow visually. The rail_presentation check fails because the separate groups (J1 side and U1/C2 side) are not joined by a single visible wire trunk in a clear manner; they rely on the netlist connection which is invisible to the human eye without tracing long wires.
- Issue 3: Power symbol clearance failure for #FLG01. The power flag at (186.69, 69.85) on pin C1.1 points up. Its text box and glyph are very close to the body of C1 and potentially other nearby labels. Specifically, the value '100n' for C1 is at y=76.20, and the flag is at y=69.85. The gap is small. While not overlapping, the upward pointing arrow on a bottom rail (REF) or top rail (VPLUS/VMINUS) can be confusing if it points into another component's area. Here, #FLG01 is on VPLUS but points up, which is correct for VPLUS, but its proximity to C1's body and value needs verification against the 5.08mm owner-advantage heuristic. The nearest other part is U1C at 20.31mm (for the flag text), which passes. However, the visual clarity of the rail entry is compromised by the lack of a clear vertical trunk.
- Issue 4: Power symbol clearance failure for #FLG02. The power flag at (52.07, 40.64) on VMINUS points down. This is correct for a return rail. However, it is located near J1. The nearest other part is R1 at 35.18mm (for the flag text), which passes. But the visual grouping of the VMINUS rail is fragmented.
- Issue 5: Power symbol clearance failure for #FLG03. The power flag at (54.61, 43.18) on REF points down. This is correct for a reference ground. It is located near J1. The nearest other part is R1 at 35.18mm (for the flag text), which passes. However, the visual grouping of the REF rail is fragmented.
- Issue 6: Rail route detour for net OUT. The wire segments for net OUT are convoluted, with multiple segments and a total length of 128.27 mm. This suggests a poor routing strategy that could be improved by using a more direct path or a common trunk.
- Issue 7: Rail route detour for net INTERMEDIATE. The wire segments for net INTERMEDIATE are convoluted, with multiple segments and a total length of 86.36 mm. This suggests a poor routing strategy that could be improved by using a more direct path or a common trunk.
- Issue 8: Rail route detour for net PARK. The wire segments for net PARK are convoluted, with multiple segments and a total length of 71.12 mm. This suggests a poor routing strategy that could be improved by using a more direct path or a common trunk.
- *Requested edit:* `{"operation": "connect_rail", "net": "VMINUS", "replace_existing": true}`

### sallen_key__overlapping_fields — INVALID
- **Known defect:** overlapping_fields
- **Reviewer:** no usable answer (model response exceeded its output token limit)

### sallen_key__distant_reference — revise
- **Known defect:** distant_reference
- Issue 1: Power rail VPLUS presentation failure. The terminal at U1C pin 8 (VPLUS) is drawn without a body, and the power symbol is an arrow pointing left on the wire segment connecting to J1.3. According to Layout (v8), supply arrows should point up except at connectors. Furthermore, the arrow points away from the main circuit block towards the edge, which is acceptable only if it's a connector entry, but here it seems to be an internal rail termination. The symbol orientation and placement need correction to align with standard presentation where the arrow indicates the source direction clearly relative to the component.
- Issue 2: Power rail VMINUS presentation failure. Similar to VPLUS, the power symbol at U1C pin 4 (VMINUS) has an arrow pointing right on the wire segment connecting to J1.4. The arrow points away from the main circuit block. While this might be acceptable for a connector entry, the orientation should ideally point towards the supply source or follow the rail direction consistently. Additionally, the symbol at C2 pin 2 (VMINUS) has an arrow pointing left, which is inconsistent with the expected downward or upward orientation for ground/supply rails unless it's specifically marking a return path from a connector.
- Issue 3: Power rail REF presentation failure. The power symbols for the REF net are ground glyphs. One glyph at C2 pin 1 points left, which is not the standard downward orientation for a ground symbol on a return rail. This inconsistency in symbol orientation can lead to confusion about the rail's function and direction.
- Issue 4: Label association and readability. The label "U1C" is centered at (198.75, 59.31) with a gap of 5.88 mm from its own body. While this passes the field_owner_association limit of 5.08 mm, it is close to the limit and might be considered crowded given the proximity to other components like C1 (nearest at 10.03 mm). The label "NE5532" for U1C is centered at (198.75, 62.02) with a gap of 3.17 mm from its body, which is within limits but could be improved for better readability.
- Issue 5: Wire routing and junction clarity. The wire segments for the OUT net show a complex routing with multiple segments and junctions. Specifically, the segment from (148.59, 68.58) to (157.48, 68.58) and subsequent segments create a path that might be visually cluttered. The junction at (157.48, 68.58) connects multiple wires, but the routing could be simplified to improve clarity.
- Issue 6: Power symbol clearance. The power symbols for VPLUS and VMINUS on the U1C component are placed on pin stubs of a bodyless unit. The clearance check might be borderline if the symbols are too close to other drawing items, although the current measurements suggest they are within acceptable limits. However, the orientation of these symbols is inconsistent with standard practices.
- Issue 7: Rail route detour. The rail routes for VPLUS and VMINUS show some detours, particularly around the U1C component. The ratio of wire length to rectilinear spanning tree should be kept low to avoid unnecessary complexity. The current routing might introduce slight detours that could be optimized.
- Issue 8: Junction dot visibility. The junction dots at (83.82, 66.04), (116.84, 66.04), and (157.48, 68.58) are present but might not be sufficiently prominent or clearly marked in the drawing, potentially leading to ambiguity about where wires connect.
- Issue 9: Net label placement. The net labels "OUT" at (54.61, 35.56) and (163.83, 68.58) are placed on wires but might not be optimally positioned for readability. They should be placed in areas with sufficient clearance from other text and symbols.
- Issue 10: Overall page composition. The drawing has a balanced functional grouping, but there is some crowding around the U1C component and its associated power symbols. The unused space could be better utilized to improve the overall layout and readability.
- *Requested edit:* `{"operation": "move_field", "reference": "U1C", "unit": 3, "field": "Reference", "x_mm": 198.755, "y_mm": 59.315, "angle": 0}`

### sallen_key__off_balance_page — revise
- **Known defect:** off_balance_page
- Issue 1: Power rail VPLUS presentation failure. Terminal U1C pin 8 (VPLUS) has a supply arrow pointing left, but the rail connection from J1.3 to U1C is routed via a long detour through C1 and U1A pins that are not visually joined by a continuous wire trunk in the description's segment list for VPLUS. The VPLUS net segments listed only join J1.3 and U1.8, leaving U1C pin 8 disconnected from the visible rail trunk despite being electrically equivalent. This violates rail_presentation.
- Issue 2: Power rail VMINUS presentation failure. Terminal U1C pin 4 (VMINUS) has a supply arrow pointing right, but the rail connection from J1.4 to U1C is routed via C2 and U1A pins that are not visually joined by a continuous wire trunk in the description's segment list for VMINUS. The VMINUS net segments listed only join J1.4 and U1.4, leaving U1C pin 4 disconnected from the visible rail trunk despite being electrically equivalent. This violates rail_presentation.
- Issue 3: Power symbol clearance failure for REF ground glyph at (261.62, 69.85). The glyph points left on pin C2.1, but its text box is centered at (256.56, 69.85), which may overlap or be too close to the body of U1C (nearest other part) given the tight layout around x=245-260 mm. This risks power_symbol_clearance violation.
- Issue 4: Power symbol direction failure for VMINUS supply arrow at (97.79, 40.64). The arrow points left on a wire segment, but the brief requires supply arrows to point up except at connectors. Since this is not a connector terminal, pointing left is non-compliant.
- Issue 5: Power symbol direction failure for VPLUS supply arrow at (245.11, 66.04). The arrow points left on pin U1C, but the brief requires supply arrows to point up except at connectors. Since this is not a connector terminal, pointing left is non-compliant.
- *Requested edit:* `{"operation": "connect_rail", "net": "VPLUS", "replace_existing": true}`

### dual_rail_reference__detached_value — revise
- **Known defect:** detached_value
- Issue: Power rail VMINUS presentation failure. The netlist defines terminals at U1.4, C2.2, J1.4, R2.2. The drawing shows a power symbol (supply arrow) at U1.4 and one at R2.2, but the terminal group at J1.4/C2.2 is connected via a wire that terminates in a power flag (#FLG02) rather than a matching supply arrow or ground glyph naming 'VMINUS'. According to `rail_presentation`, separated groups must touch a power symbol naming that rail. The current use of a flag for the main rail connection violates the requirement for a named power symbol (supply arrow/ground glyph) on each separately wired terminal group.
- Issue: Power rail VPLUS presentation failure. Similar to VMINUS, the terminal group at J1.3/C1.1 is connected via a wire terminating in a power flag (#FLG01). The `rail_presentation` check requires a matching power symbol (supply arrow) naming 'VPLUS' on each separated group. The presence of flags instead of supply arrows for the main rail connections fails this criterion.
- Issue: Power symbol direction violation. The specification states `power_symbol_direction == 0`, meaning supply arrows must point up (or away from the rail entry at connectors). In the drawing, all power symbols (supply arrows) are drawn pointing left on wires or pins. This violates the orientation rule for supply arrows which should point towards the source (up) or be placed appropriately relative to the connector entry.
- Issue: Power symbol clearance violation. The power flags (#FLG01, #FLG02) and supply arrows are placed directly on wires/pins without sufficient clearance from other drawing items in some contexts, though the primary failure is the type of symbol used (flag vs arrow/glyph). However, the instruction `use_power_symbols` suggests re-placing symbols that touch other items. The current placement of flags on active rail lines creates ambiguity and fails the `power_symbol_clearance` check if interpreted strictly against 'other drawing items' including the wire segments they sit on.
- Issue: Label association for C1 Value. The value '100n' for C1 is located at (168.91, 54.61), which is 63.99 mm from C1's body. While this passes the `field_locality` limit of 25.4 mm? No, 63.99 > 25.4. Wait, re-reading: `field_locality <= 25.4 mm`. The measurement says 63.99 mm. This is a violation of `field_locality`. The label is too far from its own body.
- Issue: Label association for C1 Reference. The reference 'C1' is at (90.17, 57.15), 6.72 mm from body. This passes `field_locality` (<=25.4) and `field_owner_association` (<=5.08)? No, 6.72 > 5.08. This violates `field_owner_association`. The reference is not clearly associated with its own unit within the 5.08 mm heuristic limit.
- *Requested edit:* `{"operation": "use_power_symbols", "net": "VMINUS"}`

### dual_rail_reference__overlapping_fields — revise
- **Known defect:** overlapping_fields
- C1 Value label "100n" is misplaced at (161.29, 41.91), which is 56.37 mm from its own body and visually associated with U1A instead of C1.
- C2 Value label "100n" is misplaced at (137.80, 59.85), which is only 4.95 mm from its own body but the coordinate suggests a potential overlap or misalignment issue given the description of nearest other part U1A at 15.86 mm.
- U1C Reference label "U1C" is misplaced at (112.39, 45.34), which is 5.88 mm from its own body and visually associated with C1 instead of U1C.
- U1C Value label "NE5532" is misplaced at (112.39, 48.05), which is 3.17 mm from its own body and visually associated with C1 instead of U1C.
- VMINUS supply arrow at (24.13, 40.64) points left on a wire, which may not align with the expected direction for power symbols in this context.
- VPLUS supply arrow at (26.67, 38.10) points left on a wire, which may not align with the expected direction for power symbols in this context.
- *Requested edit:* `{"operation": "move_field", "reference": "C1", "unit": 1, "field": "Value", "x_mm": 90.17, "y_mm": 57.15, "angle": 0}`

### dual_rail_reference__distant_reference — revise
- **Known defect:** distant_reference
- Issue: Power rail VMINUS presentation failure at terminal U1.4.
- Description: The power symbol for VMINUS is placed on pin U1.4 pointing left, but the rail wire runs vertically from U1.4 to C2.2 and then horizontally to J1.4. A power symbol pointing left on a vertical segment where the rail continues vertically violates the 'rail_presentation' requirement that symbols mark separated groups or ends of rails. The symbol should be removed or reoriented if it implies a termination, but given the wire continues, the symbol placement is misleading for a continuous rail.
- Action: connect_rail
- Parameters: {"net": "VMINUS", "from_ref": "U1", "from_pin": "4", "to_ref": "J1", "to_pin": "4", "set_replace_existing": true}
- Issue: Power rail VPLUS presentation failure at terminal U1.8.
- Description: Similar to VMINUS, the power symbol for VPLUS is on pin U1.8 pointing left, while the rail wire runs vertically from U1.8 to C1.1 and then horizontally to J1.3. The symbol placement on a vertical segment with continuing horizontal wiring is inconsistent with clear rail presentation.
- Action: connect_rail
- Parameters: {"net": "VPLUS", "from_ref": "U1", "from_pin": "8", "to_ref": "J1", "to_pin": "3", "set_replace_existing": true}
- Issue: Power symbol clearance failure for #FLG01.
- Description: The power flag #FLG01 is located at (100.33, 55.88) on pin C1.1 pointing up. Its text box and glyph are in close proximity to the capacitor body and potentially other fields. While not explicitly overlapping another symbol's body in the provided data, the placement on a vertical wire segment with a horizontal continuation (implied by the netlist structure of VPLUS connecting U1.8, C1.1, J1.3) suggests it might be interrupting the visual flow or placed where a supply arrow would normally be if not for the flag. However, the primary issue is that flags are typically used at connectors or specific entry points. Here, it's on an internal node of a rail formed by U1, C1, J1. The brief states 'power flags sit where their rails enter through a connector... otherwise on their own wires'. This placement is acceptable if it marks the entry, but the orientation (pointing up) on a vertical wire segment needs to ensure it doesn't obscure the connection point or conflict with the 'supply arrow' convention for internal nodes. Given the strict review brief, we must ensure flags don't crowd parts. The nearest part is C1 body at ~0mm (on pin), but the flag is *on* the pin. This is acceptable per KiCad rules, but let's check if it touches other fields. The data says 'nearest other part R1 at 26.12 mm' for U1B ref, but for #FLG01, nearest is C1 body (0mm). The issue is likely the visual clutter or incorrect usage of a flag vs arrow on an internal rail node. However, the prompt says 'Asserted power rails are checked by rail_presentation; there is no visible_rail_continuity check'. The failure is likely 'rail_presentation' because the symbol is on a wire segment that isn't a terminal end in the visual sense of a separate group, or it's just redundant. But wait, the netlist shows U1.8, C1.1, J1.3 are all on VPLUS. The flag is on C1.1. This is an internal node. Flags should generally not be used for internal nodes unless marking a specific entry point like a connector. Here J1 is the connector. So the flag on C1.1 is likely incorrect usage or unnecessary clutter.
- Action: use_power_symbols
- Parameters: {"net": "VPLUS", "target_symbol_refdes": ["#FLG01"]}
- Issue: Power symbol clearance failure for #FLG02.
- Description: The power flag #FLG02 is at (25.40, 40.64) on a wire segment of VMINUS. This is an internal node between J1.4 and the other VMINUS terminals. Similar to #FLG01, using a flag here instead of a supply arrow or simply omitting it for an internal rail node is questionable. The brief says 'power flags sit where their rails enter through a connector... otherwise on their own wires'. This implies they can be on wires, but typically only at entry points (connectors). J1 is the connector. Placing a flag on the wire segment away from the connector might be considered poor presentation or incorrect usage.
- Action: use_power_symbols
- Parameters: {"net": "VMINUS", "target_symbol_refdes": ["#FLG02"]}
- Issue: Label association for U1C Reference.
- Description: The reference 'U1C' is at (112.39, 45.34) with a gap of 5.88 mm to its own body (which is drawn without a body, only pin stubs). The nearest other part is C1 at 12.73 mm. While the gap is within the 25.4 mm limit, the fact that it's on a 'bodyless' unit and the label is somewhat distant might be acceptable, but let's check the owner-association limit of 5.08 mm. The gap is 5.88 mm which is > 5.08 mm. This violates 'Measurement field_owner_association: <= 5.08 mm'.
- Action: move_field
- Parameters: {"field_refdes": "U1C", "field_type": "Reference", "from_x_mm": 112.39, "from_y_mm": 45.34, "to_x_mm": 107.12, "to_y_mm": 45.34}
- Issue: Label association for U1C Value.
- Description: The value 'NE5532' for U1C is at (112.39, 48.05) with a gap of 3.17 mm to its own body. This is within the 5.08 mm limit. However, the reference label issue above needs fixing first. After moving the reference, the value should be checked relative to the new position or kept close. Assuming we move the reference closer, the value might need adjustment too, but typically they stay together. The instruction says 'move_field' for absolute coordinates. I will move both if needed, but the issue is specifically on the Reference label exceeding 5.08mm.
- Action: move_field
- Parameters: {"field_refdes": "U1C", "field_type": "Value", "from_x_mm": 112.39, "from_y_mm": 48.05, "to_x_mm": 107.12, "to_y_mm": 48.05}
- *Requested edit:* `{"operation": "connect_rail", "net": "VMINUS", "replace_existing": true}`

### dual_rail_reference__off_balance_page — INVALID
- **Known defect:** off_balance_page
- **Reviewer:** no usable answer (model response exceeded its output token limit)

### timer_astable__detached_value — INVALID
- **Known defect:** detached_value
- **Reviewer:** no usable answer (model response exceeded its output token limit)

### timer_astable__overlapping_fields — revise
- **Known defect:** overlapping_fields
- Issue 1: Power rail VCC presentation failure. The netlist shows terminals at J1.1, R1.1, U1.4, U1.8 on net VCC. However, the wire geometry for VCC is fragmented into three separate groups (J1->R1, U1.4->U1.8, and isolated segments) without a continuous trunk or shared rail symbol connecting them visually. This violates `rail_presentation`. Action: connect_rail with net=VCC to join these groups.
- Issue 2: Power rail REF presentation failure. Terminals at J3.1, C1.2, C2.2, U1.1 are on net REF. The drawing shows isolated ground glyphs and short wires but no continuous visual trunk connecting all terminals. Specifically, the segment from J3 to C2 is missing a direct wire path in the visible geometry (only indirect via other nets or gaps). This violates `rail_presentation`. Action: connect_rail with net=REF.
- Issue 3: Power symbol clearance failure for REF. The ground glyph at U1.1 (135.89, 68.58) points right and its text box overlaps the nearest other part U1's body/value area by approximately 5 mm, violating `power_symbol_clearance`. Action: use_power_symbols with net=REF to reposition symbols away from U1.
- Issue 4: Power symbol clearance failure for VCC. The supply arrow at R1.1 (101.60, 36.83) points up but its text box is within 3 mm of C2's value field (123.86, 40.80), which is acceptable per clearance rules, but the arrow itself touches the wire segment from J1 to R1, potentially causing visual crowding near the connector J1. However, the primary issue is that the VCC rail segments are not visually unified. Action: connect_rail with net=VCC first.
- Issue 5: Label association failure for C1 Value. The field "10u" (C1 Value) is centered at (151.13, 45.72), which is 45.55 mm from C1's body and 5.67 mm from U1. This exceeds the `field_locality` limit of 25.4 mm for independent_gate qualification and creates ambiguity in association. Action: move_field with coordinates (107.35, 77.47) to align closer to C1's body.
- Issue 6: Label association failure for U1 Reference. The field "U1" is centered at (151.13, 45.72), 6.18 mm from its body but 29.55 mm from C2. While within `field_owner_association` limit of 5.08 mm for its own unit, the placement near U1's body is acceptable, but the value field "NE555D" at (151.13, 48.42) is only 3.77 mm from the body, which is tight but acceptable. However, the overall layout lacks balanced functional grouping for the timer circuit, with components clustered on the right side. Action: regenerate_schematic to improve page balance and signal flow.
- Issue 7: Wire separation failure for DISCH net. The wire segments for DISCH (joining R1.2, R2.1, U1.7) include a segment from (101.60, 49.53) to (115.57, 49.53) that runs horizontally near C2's body, potentially causing visual confusion with the CONT net wires nearby. This violates `field_wire_separation` if interpreted strictly as any wire of another net crossing the straight line to the unit's drawing. Action: regenerate_schematic to optimize routing.
- Issue 8: Page composition imbalance. The drawing center is offset due to clustering of components (U1, C2, R1, R2) on the right and left sides with gaps at top/bottom, leading to a `page_balance` offset >0.25 fraction. Action: regenerate_schematic to redistribute components for better balance.
- *Requested edit:* `{"operation": "connect_rail", "net": "VCC", "replace_existing": true}`

### timer_astable__distant_reference — INVALID
- **Known defect:** distant_reference
- **Reviewer:** no usable answer (model response exceeded its output token limit)

### timer_astable__off_balance_page — revise
- **Known defect:** off_balance_page
- Issue 1: Power rail VCC presentation failure. The netlist shows terminals at J1.1, R1.1, U1.4, U1.8 on net VCC. However, the wire geometry for VCC is fragmented into three separate groups (J1->R1, U1.4->U1.8, and isolated segments) without a continuous trunk or shared rail symbol connecting them visually. This violates `rail_presentation`. Action: connect_rail with net=VCC to route a single orthogonal wire group joining all VCC terminals.
- Issue 2: Power rail REF presentation failure. Terminals at J3.1, C1.2, C2.2, U1.1 are on net REF. The drawing shows isolated ground glyphs and short wires that do not form a continuous visual trunk for the return rail. Specifically, the segment from J3 to C1 is disconnected from the rest of the REF network in the wire list. Action: connect_rail with net=REF.
- Issue 3: Power symbol clearance failure for U1 pin 1 (GND/REF). The ground glyph at (236.20, 68.58) has its text box overlapping or too close to the NE555D body and potentially other nearby labels like 'NE555D' or pin stubs, violating `power_symbol_clearance`. Action: use_power_symbols for net=REF to re-place symbols with adequate clearance.
- Issue 4: Power symbol direction violation for U1 pin 1. The ground glyph at (236.20, 68.58) points right instead of down, violating `power_symbol_direction` which requires ground glyphs to point down unless constrained by geometry. Action: use_power_symbols for net=REF.
- Issue 5: Power symbol direction violation for U1 pin 4 and 8 (VCC). The supply arrows at (220.98, 46.91) and (233.68, 40.56) point up, which is correct, but the arrow at (171.45, 27.86) points up while the wire runs downward from J1 to R1, creating a visual inconsistency in flow direction relative to the connector orientation. While technically allowed if pointing into the pin, the brief prefers arrows pointing up except at connectors; here J1 is a connector, so the arrow should ideally be on the wire segment entering the connector or aligned with the supply flow. However, the primary issue is the fragmented rail. Action: connect_rail will resolve this.
- Issue 6: Label association risk for C2. The reference 'C2' at (219.11, 38.10) and value '10n' at (219.11, 40.80) are close to U1's body (nearest part distance 11.85 mm and 9.15 mm respectively). While within the 25.4 mm locality limit, the proximity to U1 might cause visual ambiguity in dense layouts. Action: move_field for C2 Reference and Value to increase separation from U1 by at least 5.08 mm if possible, or ensure clear visual grouping.
- Issue 7: Label association risk for R1. The reference 'R1' at (202.79, 38.10) is 7.13 mm from C2 and 11.70 mm from J1. This is acceptable per the 5.08 mm owner-advantage heuristic, but the value '10k' is only 6.64 mm from C2. Ensure no visual overlap in detail view. Action: monitor during regenerate_schematic if needed.
- Issue 8: Wire routing inefficiency for net OUT. The wire path for OUT has 9 segments and a length of 105.41 mm, with significant detours (e.g., from U1.3 to J2). The rectilinear spanning tree would be shorter. Action: connect_rail with net=OUT to optimize routing.
- Issue 9: Wire routing inefficiency for net TIMING. The wire path has 7 segments and a length of 57.15 mm, with detours around U1 pins. Action: connect_rail with net=TIMING to optimize routing.
- *Requested edit:* `{"operation": "connect_rail", "net": "VCC", "replace_existing": true}`

### reference_555_led_flasher_v8__detached_value — INVALID
- **Known defect:** detached_value
- **Reviewer:** no usable answer (model response exceeded its output token limit)

### reference_555_led_flasher_v8__overlapping_fields — revise
- **Known defect:** overlapping_fields
- Issue 1: Label Association Failure (C1 Value). The value field '10u' for component C1 is located at (104.14, 46.99), which is 45.55 mm from its own body and only 5.67 mm from the unrelated component U1. This violates the `field_owner_association` limit of <= 5.08 mm and creates visual ambiguity where the value appears attached to the wrong part.
- Issue 2: Label Association Failure (C1 Reference). The reference field 'C1' is located at (60.36, 78.74), which is 2.31 mm from its body but visually stranded far from the actual capacitor symbol body (x 52.58..56.64). While within distance limits, the layout separates the label from the component it describes, violating `field_owner_association` best practices for readability.
- Issue 3: Rail Presentation Failure (VCC Net). The VCC net is fragmented into three disconnected wire groups: one joining R1/R3, one joining J1, and one joining U1. These groups are not joined by a continuous visible wire trunk nor do they all terminate at a single shared power symbol. Specifically, the group ending at J1 (Supply) has a VCC arrow pointing up at (44.45, 92.71), but the other VCC terminals lack a unified rail presentation.
- Issue 4: Rail Presentation Failure (REF Net). The REF net is fragmented into three disconnected wire groups: one joining C1/J3, one joining C2/U1, and one isolated at J3. These groups are not joined by a continuous visible wire trunk nor do they all terminate at a single shared power symbol.
- Issue 5: Power Symbol Direction Violation (VCC). The VCC supply arrow at (44.45, 92.71) points up, which is correct for a supply rail, but the presence of multiple disconnected groups with arrows pointing in different directions or lacking connection violates the `rail_presentation` requirement that every terminal group must touch a matching power symbol on a shared rail structure.
- Issue 6: Power Symbol Direction Violation (REF). The REF ground glyph at (71.12, 92.71) points down, which is correct for a return rail, but the fragmentation of the net means this symbol does not represent a unified rail as required by `rail_presentation`.
- Issue 7: Page Composition Failure. The drawing exhibits fragmented motifs and confusing crossings due to the disconnected VCC and REF rails. The layout requires zooming to understand the main organization of the power distribution, violating the `page_composition` requirement for clear reading flow and balanced functional grouping.
- *Requested edit:* `{"operation": "move_field", "reference": "C1", "unit": 2, "field": "Value", "x_mm": 54.61, "y_mm": 80.52, "angle": 0}`

### reference_555_led_flasher_v8__distant_reference — revise
- **Known defect:** distant_reference
- Issue 1: Power rail VCC presentation failure. The netlist shows terminals at J1 (Supply), R1, R3, U1 pins 4/8. However, the wire geometry for VCC is fragmented into three separate groups with no continuous trunk connecting them to a single power symbol or shared rail. Specifically, the group joining J1 and R1/R3 is disconnected from the group at U1. This violates `rail_presentation` which requires every separated terminal group to touch a matching power symbol or join a visible common wire trunk. The current layout has long runs blocking connections without a unified rail presentation.
- Issue 2: Power rail REF presentation failure. Similar to VCC, the REF net is fragmented. Terminals at J3, C1, U1, and C2 are not joined by a continuous visible wire trunk or properly marked with power symbols in a way that satisfies `rail_presentation`. The ground glyphs are present but the wiring does not form a coherent rail structure connecting all terminals visibly.
- Issue 3: Power symbol clearance failure for VCC. The VCC supply arrow at (44.45, 92.71) is placed on a wire segment that appears to be part of a fragmented rail. While it points up as required, the surrounding geometry suggests potential crowding or improper placement relative to the disconnected terminal groups, failing `power_symbol_clearance` if interpreted conservatively regarding glyph proximity to other items in a fragmented rail context.
- Issue 4: Power symbol clearance failure for REF. The ground glyph at (50.80, 85.09) on pin C1.2 is part of a fragmented REF rail. Its placement may be considered touching or too close to the body of C1 or other nearby elements in a way that violates `power_symbol_clearance` when the rail itself is not properly presented.
- Issue 5: Label association risk for U1. The reference label "U1" is centered at (124.46, 30.48), which is 26.50 mm from its own body box (x 123.02..125.90). While this exceeds the typical 25.4 mm locality limit mentioned in limitations as a catch for specific defects, it is visually distant and may be considered stranded or ambiguous if the user expects labels closer to components. However, given the component's position at the top right, this might be acceptable layout-wise but warrants inspection for human legibility.
- Issue 6: Wire routing inefficiency for OUT net. The OUT net has 13 segments totaling 201.93 mm, indicating a highly convoluted path with multiple detours. This violates `rail_route_detour` principles which discourage excessive length relative to the rectilinear spanning tree. The path winds around other components unnecessarily.
- Issue 7: Junction dot ambiguity. There are junction dots listed at coordinates like (24.13, 73.66) and (54.61, 50.80). While these may be valid T-junctions, their presence without explicit visual markers in the description could lead to ambiguity if not clearly drawn as such in the actual image, potentially confusing readers about where nets split or join.
- *Requested edit:* `{"operation": "connect_rail", "net": "VCC", "replace_existing": true}`

### reference_555_led_flasher_v8__off_balance_page — revise
- **Known defect:** off_balance_page
- Issue 1: Power rail VCC presentation failure. The netlist shows terminals at J1 (Supply), R1, R3, U1 pins 4/8. However, the wire geometry for VCC is fragmented into three separate groups with no continuous trunk connecting them to a single power symbol or shared rail. Specifically, the segment joining J1.1 and U1.8 is missing; instead, there are isolated segments: one group joins R1/R3, another joins J1 alone, and another joins U1.8 alone. This violates `rail_presentation` (every separated group must touch a power symbol naming that rail) and `visible_local_rails`. The editor should wire every group it can route to form a continuous VCC trunk.
- Issue 2: Power rail REF presentation failure. The netlist shows terminals at C1, C2, J3, U1 pin 1. The wire geometry shows isolated segments: one joins J3 alone, another joins C1 alone. There is no continuous trunk connecting these to a shared ground glyph or power symbol. This violates `rail_presentation` and `visible_local_rails`. The editor should wire every group it can route to form a continuous REF trunk.
- Issue 3: Power symbol clearance failure for VCC. The VCC supply arrow at (241.30, 45.72) is placed on a wire segment that does not connect to the main VCC rail trunk (which joins R1/R3). This creates an isolated power symbol group that fails `rail_presentation`. Additionally, the VCC supply arrow at (228.60, 52.07) is on a wire segment joining U1.4 but not connected to the main trunk. These isolated symbols fail `power_symbol_clearance` as they do not join a visible common wire trunk.
- Issue 4: Power symbol clearance failure for REF. The REF ground glyph at (200.66, 85.09) is on a wire segment joining C1 alone, not connected to the main REF rail trunk (which joins J3 and U1). This isolated symbol fails `power_symbol_clearance` as it does not join a visible common wire trunk.
- Issue 5: Power symbol direction violation for VCC. The VCC supply arrow at (241.30, 45.72) points up, which is correct per brief, but its placement on an isolated segment violates `rail_presentation`. Similarly, the VCC supply arrow at (228.60, 52.07) points up correctly but is isolated. The issue is not direction but isolation.
- Issue 6: Power symbol direction violation for REF. The REF ground glyph at (200.66, 85.09) points down, which is correct per brief, but its placement on an isolated segment violates `rail_presentation`. Similarly, the REF ground glyph at (220.98, 92.71) points down correctly but is isolated.
- Issue 7: Power symbol direction violation for VCC. The VCC supply arrow at (194.31, 92.71) points up, which is correct per brief, but its placement on an isolated segment violates `rail_presentation`. Similarly, the VCC supply arrow at (204.47, 38.10) points up correctly but is isolated.
- Issue 8: Power symbol direction violation for REF. The REF ground glyph at (220.98, 45.72) points down, which is correct per brief, but its placement on an isolated segment violates `rail_presentation`. Similarly, the REF ground glyph at (238.76, 69.85) points down correctly but is isolated.
- Issue 9: Power symbol direction violation for VCC. The VCC supply arrow at (194.31, 92.71) points up, which is correct per brief, but its placement on an isolated segment violates `rail_presentation`. Similarly, the VCC supply arrow at (204.47, 38.10) points up correctly but is isolated.
- Issue 10: Power symbol direction violation for REF. The REF ground glyph at (200.66, 85.09) points down, which is correct per brief, but its placement on an isolated segment violates `rail_presentation`. Similarly, the REF ground glyph at (220.98, 92.71) points down correctly but is isolated.
- *Requested edit:* `{"operation": "connect_rail", "net": "VCC", "replace_existing": true}`

## known-good (15)

### dual_buffer__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- Issue: Power rail VMINUS presentation failure. The terminal at U1C pin 4 (73.66, 52.07) has a supply arrow pointing right into the component body, and the terminal at J1 pin 4 (33.02, 40.64) connects to a flag pointing down but lacks a clear rail wire trunk connecting these groups visibly. The netlist shows connectivity, but the visual grouping fails the 'rail_presentation' check because the separate groups are not joined by a visible common wire trunk or clearly marked power symbols in a consistent orientation.
- Issue: Power rail VPLUS presentation failure. Similar to VMINUS, the terminal at U1C pin 8 (73.66, 36.83) has an arrow pointing right into the body. The terminal at J1 pin 3 (33.02, 38.10) connects to a flag pointing left. These groups are not visually joined by a continuous wire trunk.
- Issue: Power rail REF presentation failure. The ground glyph at C2 pin 1 (90.17, 40.64) points left instead of down, and the glyph at U1C pin 5 (implied via wire) points down but is separated from the main trunk by a long detour. The visual continuity of the REF rail is broken.
- Issue: Label association for U1C. The reference 'U1C' is placed at (74.30, 30.11), which is 5.88 mm from its own body (drawn without a body). While within the 25.4 mm limit, the label is visually distant from the pin stubs at y=36.83 and y=52.07, potentially causing ambiguity for human readers regarding which unit it refers to, especially since U1A and U1B share the same reference text 'U1'.
- *Requested edit:* `{"operation": "connect_rail", "net": "VMINUS", "replace_existing": true}`

### dual_rail_reference__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- Issue: Power rail VMINUS presentation failure at terminal U1.4.
- Description: The power symbol for VMINUS is placed on pin U1.4 pointing left (away from the component body and towards the connector area), which violates the Layout (v8) requirement that supply arrows point up except at connectors, and generally points away from the rail entry. Furthermore, the rail route detour ratio exceeds 1.15 due to the long vertical wire segment required to connect U1.4 to the main VMINUS trunk before turning left.
- Action: connect_rail
- Parameters: {"net": "VMINUS", "set_from_ref": "U1", "set_from_pin": "4", "set_to_ref": "J1", "set_to_pin": "4", "set_replace_existing": true}
- Issue: Power rail VPLUS presentation failure at terminal U1.8.
- Description: Similar to VMINUS, the power symbol for VPLUS is placed on pin U1.8 pointing left. This creates an awkward routing where the wire must travel vertically from the top of the component before turning left, increasing the detour ratio and violating the preferred orientation where supply arrows point up or towards the rail entry.
- Action: connect_rail
- Parameters: {"net": "VPLUS", "set_from_ref": "U1", "set_from_pin": "8", "set_to_ref": "J1", "set_to_pin": "3", "set_replace_existing": true}
- Issue: Power rail VREF presentation failure at terminal U1.5.
- Description: The power symbol for VREF is placed on pin U1.5 pointing left. While VREF is a reference net, the layout brief suggests consistent power flag/symbol placement where possible. The current placement forces a long vertical wire segment upwards from the component body before turning left to join the main trunk, resulting in a suboptimal detour ratio.
- Action: connect_rail
- Parameters: {"net": "VREF", "set_from_ref": "U1", "set_from_pin": "5", "set_to_ref": "J1", "set_to_pin": "5", "set_replace_existing": true}
- *Requested edit:* `{"operation": "connect_rail", "net": "VMINUS", "replace_existing": true}`

### inverting_gain__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- field_owner_association: The label "U1C" (Reference) at (104.02, 77.39) is 19.40 mm from its own body box (x 101.95..106.09, y 76.54..78.24). This exceeds the 5.08 mm owner-advantage limit and risks visual disassociation.
- field_owner_association: The label "NE5532" (Value) for U1C at (104.02, 80.09) is 17.64 mm from its own body box. This exceeds the 5.08 mm owner-advantage limit.
- field_owner_association: The label "U1C" (Reference) at (104.02, 77.39) is 12.29 mm from the nearest other part (C2). While not overlapping, the large gap combined with the distance from its own body creates a readability risk.
- field_owner_association: The label "NE5532" (Value) for U1C at (104.02, 80.09) is 10.53 mm from the nearest other part (C2).
- power_symbol_clearance: The VPLUS supply arrow at (82.55, 71.12) points right into the body of U1C (which has no drawn body but occupies that space logically) and its text "VPLUS" is centered at (88.82, 71.12), which is very close to the U1C reference label area.
- power_symbol_clearance: The VMINUS supply arrow at (87.63, 83.82) points right into the vicinity of C2's body and its text "VMINUS" is centered at (94.44, 83.82), which is close to C2's value label.
- power_symbol_direction: The VPLUS supply arrow at (82.55, 71.12) points right instead of up (standard for supply rails entering from top/connectors).
- power_symbol_direction: The VMINUS supply arrow at (87.63, 83.82) points right instead of down (standard for return rails).
- rail_presentation: The VPLUS rail group is split between J1.3 and U1.8. The wire segment from J1.3 to U1.8 passes near C1. The power symbol at U1.8 points right, which is non-standard and potentially confusing.
- rail_presentation: The VMINUS rail group is split between J1.4 and U1.4/C2.2. The wire segment from J1.4 to U1.4 passes near C2. The power symbol at U1.4 points right, which is non-standard.
- *Requested edit:* `{"operation": "move_field", "reference": "U1C", "unit": 3, "field": "Reference", "x_mm": 104.02, "y_mm": 77.39, "angle": 0}`

### led_long_text__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- Issue: D24 Reference label 'D24' is visually stranded and ambiguous.
- Location: (71.17, 54.61)
- Reasoning: The label is positioned 9.72 mm from the component body and 10.99 mm from the nearest other part (R123). While it passes the 25.4 mm locality limit, the large gap combined with the 90-degree rotation makes visual association difficult without zooming. The label appears to float rather than being clearly anchored to the LED symbol.
- Action: move_field
- Parameters: {"field": "D24 Reference", "from_x_mm": 71.168243, "from_y_mm": 54.61, "to_x_mm": 59.0, "to_y_mm": 57.0, "angle": 90}
- *Requested edit:* `{"operation": "move_field", "reference": "D24", "unit": 1, "field": "Reference", "x_mm": 59.0, "y_mm": 57.0, "angle": 90}`

### led_reverse_supply__known_good — INVALID
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- **Reviewer:** no usable answer (model response exceeded its output token limit)

### led_series__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- rail_presentation: net REF has a long detour (49.53 mm) with multiple segments and waypoints that do not form a clean orthogonal trunk; this violates the visual rubric for clear signal flow and crowding.
- power_symbol_clearance: no power symbols are present on nets REF or VPLUS, which is required by visible_local_rails for asserted rails when terminals are separated; the current wiring alone is insufficient for rail presentation compliance.
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": true}`

### linear_regulator__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- rail_presentation: net REF has a terminal group at J3.1 (52.07, 34.29) connected to a ground glyph at (52.07, 38.10), but the main rail trunk connecting C1.2 and C2.2 runs along y=68.58. The terminal U1.2 at (110.49, 49.53) connects to this trunk via a vertical wire segment (110.49, 49.53)->(111.76, 49.53) which is off-grid (delta x=1.27mm but the start y=49.53 is not on the 1.27 grid relative to the trunk at 68.58? Actually 68.58-49.53=19.05, which is 15*1.27. The issue is the wire segment (110.49, 49.53)->(111.76, 49.53) creates a T-junction that is not aligned with the main vertical trunk at x=111.76. The main trunk is at x=111.76 from (111.76, 68.58) to (111.76, 49.53)? No, the wire list says (110.49, 49.53)->(111.76, 49.53). This implies a horizontal segment from the pin to the trunk. However, the trunk is defined by segments (97.79, 68.58)->(123.19, 68.58) and (111.76, 68.58)->(110.49, 68.58). There is no vertical segment connecting the U1 pin to the trunk in the wire list. The wire list has (110.49, 49.53)->(111.76, 49.53) and then (111.76, 68.58)->(110.49, 68.58). This means the connection from U1.2 to the main REF rail is missing a vertical segment. The wire list shows (110.49, 49.53)->(111.76, 49.53) and then (111.76, 68.58)->(110.49, 68.58). This implies a gap between y=49.53 and y=68.58 at x=111.76 is not wired. The terminal U1.2 is at (110.49, 49.53). The wire starts at (110.49, 49.53) and goes to (111.76, 49.53). Then there is a segment from (111.76, 68.58) to (110.49, 68.58). There is no wire connecting (111.76, 49.53) to (111.76, 68.58). This breaks the rail continuity for the U1.2 terminal.
- power_symbol_clearance: The power flag #FLG01 at (74.93, 41.91) points left and is on a wire segment of net VIN. The wire segment from (76.20, 41.91) to (78.74, 41.91) passes near the flag. The flag is at (74.93, 41.91). The wire segment (74.93, 41.91)->(76.20, 41.91) starts exactly at the flag's connection point. This is acceptable. However, the power flag #FLG02 at (48.26, 34.29) points down and is on a wire segment of net REF. The wire segment from (48.26, 34.29) to (49.53, 34.29) starts exactly at the flag's connection point. This is acceptable.
- label_association: The label "VIN" at (74.93, 41.91) is associated with the power flag #FLG01 and the wire segment starting there. However, the label "VOUT" appears twice: once at (26.67, 44.45) and once at (127.00, 41.91). The label at (26.67, 44.45) is near the wire segment ending at J2.1. The label at (127.00, 41.91) is near the wire segment connecting C2.1 and U1.3. Both are acceptable.
- page_composition: The drawing has a balanced layout with clear functional grouping. The power unit U1 is centrally located with decoupling capacitors C1 and C2 mirrored across it. The connectors J1, J2, and J3 are placed at the appropriate locations for supply input, regulated output, and return. The page has enough space to follow the circuit without crowding.
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": true}`

### noninverting_gain__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- Issue: Power rail VPLUS presentation failure at U1C (U1A in intended circuit) pin 8.
- Description: The power symbol for VPLUS is placed on the pin stub of U1C (unit 3). According to the review brief, supply arrows should point up. Currently, the arrow points right. Furthermore, the text 'VPLUS' is centered at (115.49, 90.17), which places it very close to the top edge of the component body and potentially overlapping with the reference/value area if the body were drawn, though here it is on a stub. More critically, the arrow direction violates the 'supply arrows point up' rule for non-connector entries.
- Action: move_field
- Parameters: {"field": "#FLG01", "from_ref": "U1C", "from_pin": "8", "to_ref": "U1C", "to_pin": "8", "offset_x_mm": 0.0, "offset_y_mm": -2.54}
- Reasoning: Move the VPLUS power symbol text and glyph upwards by 2.54mm to ensure the arrow points up (from the connection point towards the top of the page) and clears any potential overlap with the component body definition area.
- *Requested edit:* `{"operation": "move_field", "reference": "#FLG01", "unit": 1, "field": "Value", "x_mm": 97.79, "y_mm": 96.68, "angle": 0}`

### rc_highpass__known_good — accept
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)

### rc_lowpass__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- Issue: Rail Presentation Failure for Net REF.
- Description: The 'REF' net connects J3.1 and C1.2. According to the review brief (Layout v8), power unit decoupling capacitors should be mirrored with rail pins on top and return below, wired straight to supply pins. Furthermore, visible_local_rails requires every terminal of an asserted REF/VCC rail to be visibly connected via wire or a matching power symbol. Currently, the REF net has no power symbols (ground glyphs) at its terminals (J3.1 or C1.2). The wires form a long detour (100.33 mm total length vs rectilinear span of ~48mm), violating the rail_route_detour limit (< 7.62mm extra length allowed, here excess is >20mm). The layout does not show the capacitor mirrored across a power unit or wired straight to a supply pin as required by the intended circuit profile 'm2b.1' for this topology.
- Action: connect_rail
- Parameters: {"net": "REF", "set_replace_existing": true}
- Reasoning: The existing long runs block clear presentation and lack power symbols. Replacing the rail route will allow the editor to wire groups straight to supply pins and place appropriate ground glyphs at J3.1 and C1.2, satisfying visible_local_rails and rail_presentation checks.
- *Requested edit:* `{"operation": "connect_rail", "net": "REF", "replace_existing": true}`

### rc_to_buffer__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- Issue 1: Power rail VMINUS presentation failure. The terminal at U1C pin 4 (VMINUS) is drawn without a body, and the wire connecting it to J1.4 passes through the pin-name column of this bodyless unit. This violates `bodyless_unit_clearance`. Additionally, the power symbol for VMINUS at U1C points right instead of down/up as required by `power_symbol_direction` and `ground_symbol_direction` conventions for a return rail.
- Issue 2: Power rail VPLUS presentation failure. The power symbol at C1 pin 1 points left instead of up (supply arrow convention), violating `power_symbol_direction`. The terminal at U1C pin 8 also has a power symbol pointing left instead of up.
- Issue 3: Power rail REF presentation failure. The power symbol at C2 pin 1 points left instead of down/up, violating `power_symbol_direction` and `ground_symbol_direction`.
- Issue 4: Label association risk for U1C. The reference/value fields for U1C are placed with a gap of 5.88 mm to its own body (which is drawn without a body, only pin stubs). While this passes the 25.4 mm locality limit, the visual association between the text and the pin stubs may be ambiguous due to the lack of a visible body box.
- Issue 5: Wire routing inefficiency for net OUT. The wire segments for net OUT show a detour pattern that suggests unnecessary complexity compared to a direct orthogonal path, potentially affecting readability.
- *Requested edit:* `{"operation": "move_field", "reference": "U1C", "unit": 3, "field": "Reference", "x_mm": 126.365, "y_mm": 59.315, "angle": 0}`

### reference_555_led_flasher_v8__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- Issue 1: Power rail VCC presentation failure. The netlist shows terminals at J1 (Supply), R1, R3, U1 pins 4/8. However, the wire geometry for VCC is fragmented into three separate groups with no continuous trunk connecting them to a single power symbol or shared rail. Specifically, the group joining J1 and R1/R3 is disconnected from the group at U1. This violates `rail_presentation` which requires every separated terminal group to touch a matching power symbol or join a visible common wire trunk. The existing long runs block connections between the supply entry (J1) and the timer chip (U1).
- Issue 2: Power rail REF presentation failure. Similar to VCC, the REF net has terminals at J3, C1, U1, C2. The wire geometry shows separate segments for J3->C1 and C1->U1/C2, but they are not joined by a continuous trunk or properly marked with a single ground glyph for the entire return path as required by `rail_presentation`. The ground glyphs are present on individual pins/wires but do not form a coherent rail presentation where separated groups are clearly part of the same return path.
- Issue 3: Power symbol clearance failure. The power symbols for VCC and REF are placed on wires or pins, but their text boxes (e.g., "VCC" at (44.45, 88.82) and "REF" at (71.12, 96.60)) are in close proximity to component bodies and other labels. Specifically, the VCC symbol at (44.45, 92.71) is near J1's body and C1's value text, potentially violating `power_symbol_clearance` which requires zero overlap with other drawing items.
- Issue 4: Power symbol direction inconsistency. The supply arrow for VCC at (44.45, 92.71) points up, which is correct per the brief (supply arrows point up except at connectors). However, the ground glyphs for REF are pointing down, which is also correct. But the placement of these symbols on fragmented wires suggests a need to re-route the rails to consolidate them and place power symbols appropriately.
- Issue 5: Label association risk. The label "Supply" at (59.69, 94.06) for J1 is close to C1's value text at (60.36, 81.44). While the distance check passes (>25.4 mm), the visual flow from J1 to its power symbol might be ambiguous if the rail is not clearly presented.
- Issue 6: Wire routing inefficiency. The VCC net has a long run from (29.21, 38.10) to (54.61, 38.10) and then to J1 at (48.26, 92.71), which is a detour. The TIMING net also has complex routing with multiple segments that could be simplified by re-routing the rail.
- Issue 7: Junction dot ambiguity. There are junction dots at (24.13, 73.66), (29.21, 38.10), etc., but without a clear rail presentation, it's hard to visually confirm that these are part of the same net or distinct nets.
- Issue 8: Component placement crowding. The components C1, C2, R1, R2 are clustered in the center-left area, which might cause visual crowding and make it harder to follow the signal flow from VCC to GND (REF).
- Issue 9: Missing power symbols for consolidated rails. Instead of having multiple power symbols scattered across the schematic, there should be a single power symbol for each rail (VCC and REF) placed where the rail enters through a connector or at a strategic point, with all terminals connected via continuous wires to that symbol.
- Issue 10: Rail route detour violation. The VCC net has a detour ratio exceeding 1.15 due to the fragmented routing and long runs that block other connections. This violates `rail_route_detour` which limits detours to <= 1.15 ratio.
- *Requested edit:* `{"operation": "connect_rail", "net": "VCC", "replace_existing": true}`

### sallen_key__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- power_symbol_clearance: Power symbol #FLG01 at (186.69, 72.55) touches component C1's value text box.
- power_symbol_clearance: Power symbol #FLG03 at (54.61, 45.88) is too close to connector J1's body and pin labels.
- power_symbol_direction: Supply arrow for VPLUS at (198.12, 66.04) points left instead of up.
- power_symbol_direction: Supply arrow for VMINUS at (198.12, 81.28) points right instead of down.
- power_symbol_direction: Ground glyph for REF at (186.69, 77.47) points down but is placed on a pin stub rather than a wire trunk, violating the 'rail pins on top' layout rule for decoupling caps.
- power_symbol_direction: Ground glyph for REF at (214.63, 69.85) points left instead of down.
- page_composition: Drawing centre offset exceeds 0.25 frame half-width due to large unused space on the right side and bottom.
- *Requested edit:* `{"operation": "move_field", "reference": "#FLG01", "unit": 1, "field": "Reference", "x_mm": 186.69, "y_mm": 72.55, "angle": 0}`

### timer_astable__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- Issue: Rail VCC presentation failure. The netlist defines a single 'VCC' rail connecting J1, R1, U1.4, and U1.8. However, the schematic description shows two disconnected wire groups for 'net VCC': one group (6.35 mm) joining J1.1 and another group (2.54 mm) joining U1.4, plus a separate segment for U1.8. These are not joined by continuous wires to form a single visible trunk as required by the Layout (v8) brief ('rail pins on top... wired straight'). The rail is fragmented visually.
- Issue: Rail REF presentation failure. Similar to VCC, the 'REF' net has terminals at J3, C2, U1, and C1. The wire segments listed for 'net REF' only join J3.1 to C2.2 (via a path through 49.53, 38.10). There is no visible wire connecting this group to the terminal at U1.1 or C1.2. The rail is visually partitioned.
- Issue: Power symbol clearance failure for REF. The ground glyph for REF at (135.89, 68.58) on pin U1.1 points 'right'. While sideways pointing is allowed if it doesn't touch other items, the text box for this symbol ('REF' centred at 140.95, 68.58) is very close to the body of U1 (x range 128.27..143.51). The glyph points into the pin stub area or risks overlapping the component body depending on exact rendering, violating the conservative clearance check implied by 'power_symbol_clearance == 0' requirement.
- Issue: Power symbol direction for REF at U1.1. The brief states ground glyphs should point down unless pointing sideways is necessary to avoid touching items. Here, pointing right towards the component body (U1) is poor practice and likely causes a clearance violation.
- *Requested edit:* `{"operation": "connect_rail", "net": "VCC", "replace_existing": true}`

### timer_astable_gnd__known_good — revise
- **Known defect:** none recorded (v3-era drawing; predates the v8/v9 layout rules)
- Issue 1: Power rail VCC presentation failure. The net 'VCC' is split into three disconnected wire groups (J1, U1.4, U1.8) with no visible common trunk or shared power symbol connecting them. This violates the `rail_presentation` criterion which requires every terminal of an asserted rail to be visibly connected via a shared wire or a matching power symbol.
- Issue 2: Power rail GND presentation failure. The net 'GND' is split into three disconnected wire groups (J3, C1, C2) with no visible common trunk. While they share the same net name, the visual continuity is broken, failing `rail_presentation`.
- Issue 3: Power symbol clearance violation for GND at U1. The ground glyph at (135.89, 68.58) points right instead of down. Per `power_symbol_direction`, supply arrows must point up and ground glyphs must point down unless constrained by geometry. Pointing sideways is only allowed if it doesn't touch other items; here it risks collision with U1's body or nearby text.
- Issue 4: Power symbol clearance violation for VCC at J1. The supply arrow at (76.20, 31.75) points up but is placed on a short stub that does not clearly join the main rail trunk visually. It appears stranded rather than part of a continuous rail.
- Issue 5: Power symbol clearance violation for VCC at U1.4 and U1.8. The arrows point up from pins that are not connected to a common wire trunk, creating visual ambiguity about whether these are separate rails or part of the main VCC rail.
- *Requested edit:* `{"operation": "connect_rail", "net": "VCC", "replace_existing": true}`

