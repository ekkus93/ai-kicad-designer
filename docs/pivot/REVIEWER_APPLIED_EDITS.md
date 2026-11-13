# Applied reviewer edits: index for review

Every review-loop case in which an edit requested by the model reviewer was applied, producing a new drawing. They all date from 2026-10-25 to 2026-10-31; since then the reviewer has not had an edit applied (rejected, no change, or accepted unchanged).

For each case: the run, the outcome, and each round's request. 'applied → candidate NNN' means the editor applied the edit and NNN is the new drawing; 'rejected' means the editor refused it, and the reason follows. Links open KiCad's SVG render of each drawing on GitHub; candidate 000 is the drawing before any edit. Full model replies are in each case's `reviews/NNN.json`.

65 cases, 19 ending with an accepted edited drawing.

## review_loop_555_v3_2026-10-27_qwen35_256k_run1 / reference_555_led_flasher_v8
- **Outcome:** NO_PROGRESS — model repeated an invalid review: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-27_qwen35_256k_run1/reference_555_led_flasher_v8/candidates/000/renders/schematic/Reference555LedFlasher.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-27_qwen35_256k_run1/reference_555_led_flasher_v8/candidates/002/renders/schematic/Reference555LedFlasher.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-27_qwen35_256k_run1/reference_555_led_flasher_v8/candidates/003/renders/schematic/Reference555LedFlasher.svg)
  - round 0: connect_rail(net=VCC) — rejected: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this revision; request use_power_symbols for VCC to draw it with power symbols
    - issue: rail_presentation: The VCC and REF nets are not visually presented as continuous rails or marked with power symbols at each separated terminal group. Terminals for VCC (R1.1, R3.1, J1.1, U1.4, U1.8) and REF (C2.2, J3.1, 
    - issue: action_plan_01_connect_rail_VCC
  - round 1: use_power_symbols(net=VCC) — applied → candidate 002
    - issue: rail_presentation: FAIL - asserted power-net wire groups are neither joined nor marked by a matching power symbol
  - round 2: connect_rail(net=REF) — applied → candidate 003
    - issue: rail_presentation: The REF net terminals (C2.2, J3.1, U1.1, C1.2) are not visually joined to a common rail nor marked by a matching power symbol.
    - issue: rail_presentation: The VCC net terminals (R1.1, R3.1, J1.1, U1.4, U1.8) are not visually joined to a common rail nor marked by a matching power symbol.
  - round 3: connect_rail(net=VCC) — rejected: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this revision; request use_power_symbols for VCC to draw it with power symbols
    - issue: visible_rail_continuity: The VCC net has multiple disconnected terminal groups (R1, R3, J1, U1 pins 4/8) that are not joined by a continuous wire trunk or power symbols as required by the visual rubric.
    - issue: label_association: Several fields (e.g., C2 REF, R2 REF, U1 REF) have negative owner_advantage_mm values, indicating they are visually closer to neighboring symbols than their own owning symbol, violating clear associati

## review_loop_555_v3_2026-10-27_qwen35_256k_run1 / timer_astable
- **Outcome:** NO_PROGRESS — model repeated an invalid review: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-27_qwen35_256k_run1/timer_astable/candidates/000/renders/schematic/TimerAstable.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-27_qwen35_256k_run1/timer_astable/candidates/001/renders/schematic/TimerAstable.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-27_qwen35_256k_run1/timer_astable/candidates/003/renders/schematic/TimerAstable.svg)
  - round 0: connect_rail(net=REF) — applied → candidate 001
    - issue: rail_presentation: The REF and VCC nets have terminals that are neither joined by a continuous wire trunk nor marked by a matching power symbol.
    - issue: label_association: Fields for U1, C2, R2, J2, J3, J1, C1 show negative owner_advantage_mm values, indicating they are visually closer to neighboring symbols than their own anchors.
  - round 1: connect_rail(net=VCC) — rejected: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this revision; request use_power_symbols for VCC to draw it with power symbols
    - issue: rail_presentation: VCC net terminals (R1.1, J1.1, U1.4, U1.8) are not joined by a continuous rail nor marked by power symbols
  - round 2: use_power_symbols(net=VCC) — applied → candidate 003
    - issue: rail_presentation: VCC net terminals are not visually joined or marked by power symbols
  - round 3: connect_rail(net=VCC) — rejected: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this revision; request use_power_symbols for VCC to draw it with power symbols
    - issue: visible_rail_continuity: The VCC net has disconnected terminal groups (R1, J1, U1 pins 4/8) that lack a continuous native wire path or matching power symbols.
    - issue: rail_presentation: The VCC rail is not presented with explicit wiring or power symbols for all separated terminal groups.

## review_loop_555_v3_2026-10-31_qwen35_32k_run1 / reference_555_led_flasher_v8
- **Outcome:** ACCEPTED_FOR_REVIEW — accepted `candidates/002/project/Reference555LedFlasher.kicad_sch`
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run1/reference_555_led_flasher_v8/candidates/000/renders/schematic/Reference555LedFlasher.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run1/reference_555_led_flasher_v8/candidates/001/renders/schematic/Reference555LedFlasher.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run1/reference_555_led_flasher_v8/candidates/002/renders/schematic/Reference555LedFlasher.svg)
  - round 0: connect_rail(net=VCC, replace_existing=True) — applied → candidate 001
    - issue: rail_presentation: FAIL - The VCC and REF power rails are not visually continuous. Terminals for R1, R3, J1 (VCC) and C1, C2, J3, U1 pins 1 (REF) are in separate wire groups that are neither joined by a common wire nor m
    - issue: rail_presentation: FAIL - Power symbols are missing or not correctly associated with the rail terminals. The schematic relies on text labels ('VCC', 'REF') near components but lacks the explicit power symbols (ground gly
  - round 1: connect_rail(net=REF, replace_existing=True) — applied → candidate 002
    - issue: rail_presentation: The REF net is visually fragmented into three separate wire groups that are neither joined nor marked by a matching power symbol. Terminals C2.2, J3.1/U1.1, and C1.2 each form isolated groups.
    - issue: action_type_01_connect_rail
  - round 2: accepted

## review_loop_555_v3_2026-10-31_qwen35_32k_run1 / timer_astable
- **Outcome:** ACCEPTED_FOR_REVIEW — accepted `candidates/003/project/TimerAstable.kicad_sch`
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run1/timer_astable/candidates/000/renders/schematic/TimerAstable.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run1/timer_astable/candidates/002/renders/schematic/TimerAstable.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run1/timer_astable/candidates/003/renders/schematic/TimerAstable.svg)
  - round 0: (no action) — rejected: model response exceeded its output token limit
  - round 1: connect_rail(net=REF, replace_existing=True) — applied → candidate 002
    - issue: rail_presentation: The REF and VCC rails are not visually presented as continuous groups. Terminals for these nets are separated by wires that do not form a single visible trunk, nor are they marked by power symbols (gro
    - issue: action_plan_10.0.6
  - round 2: connect_rail(net=VCC, replace_existing=True) — applied → candidate 003
    - issue: rail_presentation: The VCC rail is not visually continuous; terminals R1.1, J1.1, U1.4, and U1.8 are in separate wire groups without a shared trunk or matching power symbol.
    - issue: action_required: connect_rail with net=VCC to join all VCC terminals into a single visible rail group.
  - round 3: accepted

## review_loop_555_v3_2026-10-31_qwen35_32k_run2 / reference_555_led_flasher_v8
- **Outcome:** ACCEPTED_FOR_REVIEW — accepted `candidates/002/project/Reference555LedFlasher.kicad_sch`
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run2/reference_555_led_flasher_v8/candidates/000/renders/schematic/Reference555LedFlasher.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run2/reference_555_led_flasher_v8/candidates/001/renders/schematic/Reference555LedFlasher.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run2/reference_555_led_flasher_v8/candidates/002/renders/schematic/Reference555LedFlasher.svg)
  - round 0: connect_rail(net=VCC, replace_existing=True) — applied → candidate 001
    - issue: rail_presentation: The asserted VCC and REF rails are not visually joined by continuous wires nor marked by matching power symbols at their terminals. Specifically, terminals R1.1, R3.1, J1.1, U1.4, U1.8 (VCC) and C2.2, 
    - issue: action_plan_01_connect_rail_VCC
  - round 1: connect_rail(net=REF, replace_existing=True) — applied → candidate 002
    - issue: rail_presentation: The REF net is visually fragmented into three disconnected wire groups that are neither joined nor marked by a matching power symbol. Terminals C2.2, J3.1/U1.1, and C1.2 form separate islands.
    - issue: action_plan_01_connect_rail_ref
  - round 2: connect_rail(net=REF, replace_existing=True) — rejected: connect_rail wired what it could of REF, but marking the unreachable groups failed: use_power_symbols made no change; REF already uses power symbols and none of them touches another drawing item
    - issue: The REF net is visually disconnected: terminals at C2, J3, and U1 are not joined by a continuous wire trunk nor marked by a matching power symbol.
    - issue: The VCC net is visually disconnected: terminals at R1, R3, J1, and U1 are not joined by a continuous wire trunk nor marked by a matching power symbol.
  - round 3: accepted

## review_loop_555_v3_2026-10-31_qwen35_32k_run2 / timer_astable
- **Outcome:** ACCEPTED_FOR_REVIEW — accepted `candidates/002/project/TimerAstable.kicad_sch`
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run2/timer_astable/candidates/000/renders/schematic/TimerAstable.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run2/timer_astable/candidates/001/renders/schematic/TimerAstable.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run2/timer_astable/candidates/002/renders/schematic/TimerAstable.svg)
  - round 0: connect_rail(net=REF, replace_existing=True) — applied → candidate 001
    - issue: rail_presentation: The REF and VCC rails are not visually presented as continuous wires or marked by power symbols at their terminals. Specifically, terminals C2.2, J3.1, U1.1, C1.2 for REF and R1.1, J1.1, U1.4, U1.8 for
    - issue: action_required: connect_rail
  - round 1: connect_rail(net=VCC, replace_existing=True) — applied → candidate 002
    - issue: rail_presentation: The VCC rail is not visually continuous; terminals R1.1, J1.1, U1.4, and U1.8 are in separate wire groups without a shared trunk or matching power symbol.
    - issue: action_plan_01_connect_rail_VCC
  - round 2: accepted

## review_loop_555_v3_2026-10-31_qwen35_32k_run3 / reference_555_led_flasher_v8
- **Outcome:** ACCEPTED_FOR_REVIEW — accepted `candidates/002/project/Reference555LedFlasher.kicad_sch`
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run3/reference_555_led_flasher_v8/candidates/000/renders/schematic/Reference555LedFlasher.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run3/reference_555_led_flasher_v8/candidates/001/renders/schematic/Reference555LedFlasher.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run3/reference_555_led_flasher_v8/candidates/002/renders/schematic/Reference555LedFlasher.svg)
  - round 0: connect_rail(net=VCC, replace_existing=True) — applied → candidate 001
    - issue: rail_presentation: FAIL - Asserted power nets (VCC, REF) have terminals that are neither joined by continuous wires nor marked by matching power symbols.
    - issue: diagnostics: The editor reports wire groups for VCC and REF nets are disconnected from the main rail trunk or lack explicit power symbol markers at their endpoints.
  - round 1: connect_rail(net=REF, replace_existing=True) — applied → candidate 002
    - issue: rail_presentation: The REF net is not visually presented as a continuous rail. Terminals C2.2, J3.1/U1.1, and C1.2 are in separate wire groups that are neither joined nor marked by a matching power symbol.
    - issue: action_type_01
  - round 2: accepted

## review_loop_555_v3_2026-10-31_qwen35_32k_run3 / timer_astable_gnd
- **Outcome:** ACCEPTED_FOR_REVIEW — accepted `candidates/002/project/TimerAstable.kicad_sch`
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run3/timer_astable_gnd/candidates/000/renders/schematic/TimerAstable.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run3/timer_astable_gnd/candidates/001/renders/schematic/TimerAstable.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_555_v3_2026-10-31_qwen35_32k_run3/timer_astable_gnd/candidates/002/renders/schematic/TimerAstable.svg)
  - round 0: connect_rail(net=VCC, replace_existing=True) — applied → candidate 001
    - issue: rail_presentation: FAIL - The VCC and GND rails are not visually presented as continuous or marked by power symbols. Terminals for nets 'VCC' (R1.1, J1.1, U1.4, U1.8) and 'GND' (C2.2, J3.1, U1.1, C1.2) are in separate wi
    - issue: action_required: connect_rail - Connect the VCC rail by wiring terminals R1.1, J1.1, U1.4, and U1.8 into a single continuous group, then mark it with a VCC power symbol. Set replace_existing=true to reroute existing long
  - round 1: connect_rail(net=GND, replace_existing=True) — applied → candidate 002
    - issue: rail_presentation: FAIL - GND and VCC rails are not visually joined or marked by power symbols as required
  - round 2: accepted

## review_loop_corpus_2026-10-26_qwen_run1 / dual_buffer
- **Outcome:** NO_PROGRESS — model repeated an invalid review: 1 validation error for SchematicReview
actions.0.move_symbols
  Value error, move_symbols made no change; choose nonzero movem
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/dual_buffer/candidates/000/renders/schematic/DualBufferM2b.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/dual_buffer/candidates/001/renders/schematic/DualBufferM2b.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/dual_buffer/candidates/003/renders/schematic/DualBufferM2b.svg), [004](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/dual_buffer/candidates/004/renders/schematic/DualBufferM2b.svg)
  - round 0: connect_rail(net=VPLUS) — applied → candidate 001
    - issue: visible_rail_continuity: no continuous visible wire path between VPLUS terminals (U1 pin 8 and J1 pin 3)
    - issue: visible_rail_continuity: no continuous visible wire path between VMINUS terminals (U1 pin 4 and J1 pin 4)
  - round 1: connect_rail(net=VMINUS) — rejected: no obstacle-free native wire route joins the remaining VMINUS wire groups. Repeating connect_rail for VMINUS will fail again on this revision; first request move_symbols for one of ['C2', 'J1', 'U1'] 
    - issue: visible_rail_continuity: The VMINUS net lacks a continuous visible wire path between terminals U1:4 and J1:4.
    - issue: field_owner_association: Fields for U1 (unit 3) are visually closer to C2 than to their own symbol, violating the owner-association heuristic.
  - round 2: move_symbols(references=['C2'], dx_mm=0.0, dy_mm=-1.27) — applied → candidate 003
    - issue: visible_rail_continuity: no continuous native wire path between VMINUS terminals (U1 pin 4 and J1 pin 4)
    - issue: field_owner_association: U1 unit 3 fields are closer to C2 than to their own symbol
  - round 3: connect_rail(net=VMINUS) — applied → candidate 004
    - issue: visible_rail_continuity: The VMINUS net lacks a continuous visible wire path between terminals U1:4 and J1:4.
    - issue: field_owner_association: Fields for reference U1 (unit 3) are closer to C2 than to their own symbol, violating the owner-association heuristic.
  - round 4: (no action) — rejected: 1 validation error for SchematicReview
actions.0.move_symbols
  Value error, move_symbols made no change; choose nonzero movement [type=value_error, input_value={'operation': 'move_symbo... 'dx_mm': 0
  - round 5: move_symbols(references=['U1'], dx_mm=-12.7, dy_mm=0.0) — rejected: no obstacle-free native wire route joins the remaining rerouted moved-symbol net groups
    - issue: field_owner_association: U1 unit 3 Reference and Value fields are closer to C2 than to their own symbol (owner_advantage < 5.08 mm)
  - round 6: (no action) — rejected: 1 validation error for SchematicReview
actions.0.move_symbols
  Value error, move_symbols made no change; choose nonzero movement [type=value_error, input_value={'operation': 'move_symbo... 'dx_mm': 0

## review_loop_corpus_2026-10-26_qwen_run1 / dual_rail_reference
- **Outcome:** NO_PROGRESS — model repeated an invalid review: no obstacle-free native wire route joins the remaining VMINUS wire groups. Repeating connect_rail for VMINUS will fail again o
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/dual_rail_reference/candidates/000/renders/schematic/DualRailReference.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/dual_rail_reference/candidates/001/renders/schematic/DualRailReference.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/dual_rail_reference/candidates/003/renders/schematic/DualRailReference.svg)
  - round 0: connect_rail(net=VPLUS) — applied → candidate 001
    - issue: visible_rail_continuity: FAIL - Power nets VPLUS and VMINUS lack continuous visible wire paths between terminals.
    - issue: field_owner_association: FAIL - Fields for U1 unit 3 are closer to C2 than their owning symbol.
  - round 1: connect_rail(net=VMINUS) — rejected: no obstacle-free native wire route joins the remaining VMINUS wire groups. Repeating connect_rail for VMINUS will fail again on this revision; first request move_symbols for one of ['C2', 'J1', 'R2', 
    - issue: visible_rail_continuity: The VMINUS net lacks a continuous visible wire path between terminals U1:4, J1:4, and R2:2.
    - issue: field_owner_association: Fields for U1 unit 3 (Reference/Value) are visually closer to C2 than to their own symbol, violating the owner-association heuristic.
  - round 2: move_symbols(references=['C2'], dx_mm=12.7, dy_mm=0.0) — applied → candidate 003
    - issue: visible_rail_continuity: FAIL - No continuous visible wire path for net VMINUS between terminals U1-4, J1-4, and R2-2.
    - issue: field_owner_association: FAIL - Fields for U1 (unit 3) are visually closer to C2 than to their own symbol, violating the 5.08 mm owner-advantage heuristic.
  - round 3: connect_rail(net=VMINUS) — rejected: no obstacle-free native wire route joins the remaining VMINUS wire groups. Repeating connect_rail for VMINUS will fail again on this revision; first request move_symbols for one of ['C2', 'J1', 'R2', 
    - issue: visible_rail_continuity: The VMINUS net lacks a continuous visible wire path between terminals U1-4, J1-4, and R2-2. The native editor shows gaps in the rail geometry for this net.
    - issue: visible_rail_continuity: The VPLUS net lacks a continuous visible wire path between terminals U1-8, J1-3, C1-1, and R1-1. The native editor shows gaps in the rail geometry for this net.

## review_loop_corpus_2026-10-26_qwen_run1 / inverting_gain
- **Outcome:** NO_PROGRESS — model repeated an invalid review: move_symbols references not found: ['3', 'unit']
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/inverting_gain/candidates/000/renders/schematic/InvertingGain.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/inverting_gain/candidates/001/renders/schematic/InvertingGain.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/inverting_gain/candidates/002/renders/schematic/InvertingGain.svg)
  - round 0: connect_rail(net=VPLUS) — applied → candidate 001
    - issue: visible_rail_continuity: The VPLUS and VMINUS nets lack continuous visible wire paths between their terminals (U1 pins 8/4 and J1 pins 3/4).
    - issue: field_owner_association: Fields for U1 unit 3 are visually closer to neighboring symbols (R1, C2) than to their own symbol, violating the owner-association heuristic.
  - round 1: move_symbols(references=['U1'], dx_mm=0.0, dy_mm=-2.54) — applied → candidate 002
    - issue: field_owner_association: U1 unit 3 Reference field is closer to R1 than its own symbol (owner_advantage_mm: 8.88 < 5.08)
    - issue: field_owner_association: U1 unit 3 Value field is closer to C2 than its own symbol (owner_advantage_mm: 5.48 < 5.08)
  - round 2: move_symbols(references=['U1', 'unit', '3'], dx_mm=0.0, dy_mm=2.54) — rejected: move_symbols references not found: ['3', 'unit']
    - issue: field_owner_association: U1 unit 3 Reference/Value fields are too close to R1 (owner_advantage < 5.08mm)
    - issue: visible_rail_continuity: Power rails for VPLUS, VMINUS, and REF lack explicit continuous wire trunks connecting all terminals
  - round 3: move_symbols(references=['U1', 'unit', '3'], dx_mm=0.0, dy_mm=2.54) — rejected: move_symbols references not found: ['3', 'unit']
    - issue: field_owner_association: U1 unit 3 Reference/Value fields are too close to R1 (owner_advantage < 5.08mm)
    - issue: visible_rail_continuity: Power rails for VPLUS, VMINUS, and REF lack explicit continuous wire trunks connecting all terminals

## review_loop_corpus_2026-10-26_qwen_run1 / linear_regulator
- **Outcome:** NO_PROGRESS — model repeated an invalid review: stale model review: base_revision does not match image revision
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/linear_regulator/candidates/000/renders/schematic/LinearRegulator.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/linear_regulator/candidates/001/renders/schematic/LinearRegulator.svg)
  - round 0: connect_rail(net=VIN) — applied → candidate 001
    - issue: visible_rail_continuity: The schematic lacks explicit wire paths connecting terminals on the same net (VIN, REF). While electrically equivalent, the visual representation relies on implicit connections or label-only join
    - issue: action_plan_01_connect_rail_VIN
  - round 1: connect_rail(net=REF) — rejected: stale model review: base_revision does not match image revision
    - issue: visible_rail_continuity: The 'REF' net lacks a continuous visible wire path between terminals C1-2, C2-2, J3-1, and U1-2. The schematic relies on implicit connections or label-only joins which violates the visual rubric 
    - issue: action_plan_summary
  - round 2: connect_rail(net=REF) — rejected: stale model review: base_revision does not match image revision
    - issue: visible_rail_continuity

## review_loop_corpus_2026-10-26_qwen_run1 / noninverting_gain
- **Outcome:** NO_PROGRESS — model repeated an invalid review: 1 validation error for SchematicReview
actions.0.move_symbols
  Value error, move_symbols made no change; choose nonzero movem
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/noninverting_gain/candidates/000/renders/schematic/NoninvertingGain.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/noninverting_gain/candidates/001/renders/schematic/NoninvertingGain.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/noninverting_gain/candidates/002/renders/schematic/NoninvertingGain.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/noninverting_gain/candidates/003/renders/schematic/NoninvertingGain.svg), [005](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/noninverting_gain/candidates/005/renders/schematic/NoninvertingGain.svg)
  - round 0: connect_rail(net=VPLUS) — applied → candidate 001
    - issue: visible_rail_continuity: No continuous wire path exists between terminals for nets VPLUS, VMINUS, and REF. The schematic relies on implicit connections or label-only joins which fail the visual rubric.
    - issue: field_owner_association: Fields for U1 (unit 3) are closer to C2 than to their own symbol, violating the owner-association heuristic.
  - round 1: connect_rail(net=VMINUS) — applied → candidate 002
    - issue: visible_rail_continuity: No continuous visible wire path exists between terminals for nets VMINUS and REF as listed in diagnostics.
    - issue: field_owner_association: Fields for U1 unit 3 are closer to C2 than to their own symbol, violating the 5.08 mm owner-advantage heuristic.
  - round 2: connect_rail(net=REF) — applied → candidate 003
    - issue: visible_rail_continuity: The REF net lacks a continuous visible wire path between terminals (U1, C2, C1, J1, R2).
    - issue: field_owner_association: Fields for U1 unit 3 are closer to C2 than their own symbol, violating the 5.08 mm owner-advantage heuristic.
  - round 3: (no action) — rejected: 1 validation error for SchematicReview
actions.0.move_symbols
  Value error, move_symbols made no change; choose nonzero movement [type=value_error, input_value={'operation': 'move_symbo... 'dx_mm': 0
  - round 4: move_symbols(references=['U1'], dx_mm=0.0, dy_mm=1.27) — applied → candidate 005
    - issue: field_owner_association: FAIL - Reference and Value fields for U1 unit 3 are closer to C2 than to their own symbol, violating the 5.08 mm owner-advantage heuristic.
  - round 5: (no action) — rejected: 1 validation error for SchematicReview
actions.0.move_symbols
  Value error, move_symbols made no change; choose nonzero movement [type=value_error, input_value={'operation': 'move_symbo... 'dx_mm': 0

## review_loop_corpus_2026-10-26_qwen_run1 / rc_to_buffer
- **Outcome:** ACCEPTED_FOR_REVIEW — accepted `candidates/004/project/RcToBuffer.kicad_sch`
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/rc_to_buffer/candidates/000/renders/schematic/RcToBuffer.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/rc_to_buffer/candidates/001/renders/schematic/RcToBuffer.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/rc_to_buffer/candidates/003/renders/schematic/RcToBuffer.svg), [004](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/rc_to_buffer/candidates/004/renders/schematic/RcToBuffer.svg)
  - round 0: connect_rail(net=VPLUS) — applied → candidate 001
    - issue: visible_rail_continuity: The VPLUS and VMINUS nets lack continuous visible wire paths between terminals U1, J1, C1/C2.
    - issue: field_owner_association: Fields for U1 (unit 3) are closer to C2 than their own symbol, violating the owner-association heuristic.
  - round 1: connect_rail(net=VMINUS) — rejected: no obstacle-free native wire route joins the remaining VMINUS wire groups. Repeating connect_rail for VMINUS will fail again on this revision; first request move_symbols for one of ['C2', 'J1', 'U1'] 
    - issue: visible_rail_continuity: The VMINUS net lacks a continuous visible wire path between terminals U1:4 and J1:4.
    - issue: field_owner_association: Fields for U1 unit 3 are visually closer to C2 than to their own symbol, violating the owner-advantage heuristic.
  - round 2: move_symbols(references=['C2'], dx_mm=0.0, dy_mm=1.27) — applied → candidate 003
    - issue: visible_rail_continuity: FAIL - No continuous visible wire path between VMINUS terminals (U1 pin 4, J1 pin 4)
    - issue: field_owner_association: FAIL - Fields for U1 unit 3 are closer to C2 than their owner symbol
  - round 3: connect_rail(net=VMINUS) — applied → candidate 004
    - issue: visible_rail_continuity: The VMINUS net lacks a continuous visible wire path between terminals U1:4 and J1:4. The connection appears to rely on implicit routing or is visually broken, failing the visual rubric for explic
    - issue: label_association: Field #FLG02 (PWR_FLAG) is associated with the VMINUS net but its placement relative to the symbol bodies suggests a potential ambiguity in human association that requires verification against the stri
  - round 4: accepted

## review_loop_corpus_2026-10-26_qwen_run1 / sallen_key
- **Outcome:** NO_PROGRESS — model repeated an invalid review: no obstacle-free native wire route joins the remaining VPLUS wire groups. Repeating connect_rail for VPLUS will fail again on 
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/sallen_key/candidates/000/renders/schematic/SallenKey.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/sallen_key/candidates/002/renders/schematic/SallenKey.svg)
  - round 0: connect_rail(net=VPLUS) — rejected: no obstacle-free native wire route joins the remaining VPLUS wire groups. Repeating connect_rail for VPLUS will fail again on this revision; first request move_symbols for one of ['C1', 'J1', 'U1'] by
    - issue: visible_rail_continuity: Power nets VPLUS, VMINUS, and REF lack continuous visible wire paths between terminals.
    - issue: field_owner_association: Fields for U1 (unit 3) are closer to C2 than to their own symbol, violating the 5.08 mm owner-advantage heuristic.
  - round 1: move_symbols(references=['C1'], dx_mm=0.0, dy_mm=1.27) — applied → candidate 002
    - issue: visible_rail_continuity: FAIL - No continuous visible wire path for VPLUS, VMINUS, and REF nets between terminals.
    - issue: field_owner_association: FAIL - Fields for U1 (unit 3) are closer to C2 than to their own symbol.
  - round 2: connect_rail(net=VPLUS) — rejected: no obstacle-free native wire route joins the remaining VPLUS wire groups. Repeating connect_rail for VPLUS will fail again on this revision; first request move_symbols for one of ['C1', 'J1', 'U1'] by
    - issue: visible_rail_continuity: Power nets VPLUS, VMINUS, and REF lack continuous visible wire paths between terminals.
    - issue: field_owner_association: Fields for U1 (unit 3) are closer to C2 than to their own symbol, violating the 5.08 mm owner-advantage heuristic.

## review_loop_corpus_2026-10-26_qwen_run1 / timer_astable
- **Outcome:** NO_PROGRESS — model repeated an invalid review: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/timer_astable/candidates/000/renders/schematic/TimerAstable.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/timer_astable/candidates/001/renders/schematic/TimerAstable.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/timer_astable/candidates/003/renders/schematic/TimerAstable.svg)
  - round 0: connect_rail(net=REF) — applied → candidate 001
    - issue: visible_rail_continuity: The visible wire paths for nets REF and VCC are discontinuous between terminals, failing the visual rubric despite electrical equivalence.
    - issue: label_association: Some fields (e.g., U1 Value) have negative owner_advantage_mm, indicating they are visually closer to neighboring symbols than their own, which may impair human association.
  - round 1: connect_rail(net=VCC) — rejected: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this revision; first request move_symbols for one of ['J1', 'R1', 'U1'] by a g
    - issue: visible_rail_continuity: FAIL - The VCC net lacks a continuous visible wire path between terminals R1, J1, and U1. The schematic relies on label-only joins or apparent gaps rather than explicit native wires.
    - issue: action_plan_summary
  - round 2: move_symbols(references=['J1'], dx_mm=0.0, dy_mm=1.27) — applied → candidate 003
    - issue: visible_rail_continuity: FAIL - No continuous visible wire path exists for the VCC net between terminals R1-1, J1-1, U1-4, and U1-8. The native editor reports no obstacle-free route.
    - issue: label_association: QUALIFIED - All component references and values are legible and clearly associated with their symbols within the 25.4 mm locality limit.
  - round 3: connect_rail(net=VCC) — rejected: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this revision; first request move_symbols for one of ['J1', 'R1', 'U1'] by a g
    - issue: visible_rail_continuity: FAIL - The VCC net lacks a continuous visible wire path between terminals R1, J1, and U1. The schematic relies on label-only joins or apparent gaps rather than explicit native wires.
    - issue: label_association: QUALIFIED - All component references and values are legible and clearly associated with their symbols within the 25.4 mm locality limit.

## review_loop_corpus_2026-10-27_qwen35_256k_run1 / dual_buffer
- **Outcome:** NO_PROGRESS — model repeated an invalid review: move_symbols references not found: ['U1A', 'U1B']
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/dual_buffer/candidates/000/renders/schematic/DualBufferM2b.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/dual_buffer/candidates/001/renders/schematic/DualBufferM2b.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/dual_buffer/candidates/003/renders/schematic/DualBufferM2b.svg)
  - round 0: connect_rail(net=VPLUS) — applied → candidate 001
    - issue: visible_rail_continuity: no continuous visible wire path between VPLUS terminals (U1 pin 8, J1 pin 3)
    - issue: visible_rail_continuity: no continuous visible wire path between VMINUS terminals (U1 pin 4, J1 pin 4)
  - round 1: connect_rail(net=VMINUS) — rejected: no obstacle-free native wire route joins the remaining VMINUS wire groups. Repeating connect_rail for VMINUS will fail again on this revision; first request move_symbols for one of ['C2', 'J1', 'U1'] 
    - issue: visible_rail_continuity: VMINUS net lacks continuous wire path between U1 pin 4 and J1 pin 4
    - issue: field_owner_association: U1 unit 3 fields are visually closer to C2 than their own symbol
  - round 2: move_symbols(references=['C2'], dx_mm=12.7, dy_mm=0.0) — applied → candidate 003
    - issue: visible_rail_continuity: no continuous native wire path between same-net terminals for net VMINUS (from U1 pin 4 to J1 pin 4)
    - issue: field_owner_association: fields for reference U1 unit 3 are closer to C2 than their own symbol, violating the 5.08 mm owner-advantage heuristic
  - round 3: move_symbols(references=['U1A', 'U1B'], dx_mm=0.0, dy_mm=2.54) — rejected: move_symbols references not found: ['U1A', 'U1B']
    - issue: observed wire through text
  - round 4: move_symbols(references=['U1A', 'U1B'], dx_mm=0.0, dy_mm=2.54) — rejected: move_symbols references not found: ['U1A', 'U1B']
    - issue: observed wire through text

## review_loop_corpus_2026-10-27_qwen35_256k_run1 / dual_rail_reference
- **Outcome:** NO_PROGRESS — model repeated an invalid review: no obstacle-free native wire route joins the remaining VMINUS wire groups. Repeating connect_rail for VMINUS will fail again o
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/dual_rail_reference/candidates/000/renders/schematic/DualRailReference.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/dual_rail_reference/candidates/001/renders/schematic/DualRailReference.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/dual_rail_reference/candidates/002/renders/schematic/DualRailReference.svg)
  - round 0: connect_rail(net=VPLUS) — applied → candidate 001
    - issue: visible_rail_continuity: FAIL - Power nets VPLUS and VMINUS lack continuous visible wire paths between terminals (U1, J1, R1, R2).
    - issue: field_owner_association: FAIL - Fields for U1 unit 3 are closer to C2 than their owning symbol edges.
  - round 1: move_symbols(references=['U1'], dx_mm=0.0, dy_mm=-5.08) — applied → candidate 002
    - issue: field_owner_association: U1 unit 3 Reference and Value fields are closer to C2 than to their own symbol (owner_advantage < 5.08 mm)
    - issue: visible_rail_continuity: No continuous wire path exists between VMINUS terminals on U1, J1, R2, and C2
  - round 2: connect_rail(net=VMINUS) — rejected: no obstacle-free native wire route joins the remaining VMINUS wire groups. Repeating connect_rail for VMINUS will fail again on this revision; first request move_symbols for one of ['C2', 'J1', 'R2', 
    - issue: visible_rail_continuity: VMINUS net lacks continuous wire path between U1 pin 4 and J1 pin 4; also lacks continuous wire path between U1 pin 4 and R2 pin 2
  - round 3: (no action) — rejected: 1 validation error for SchematicReview
actions.0.move_symbols
  Value error, move_symbols made no change; choose nonzero movement [type=value_error, input_value={'operation': 'move_symbo..._mm': 0.0, 
  - round 4: connect_rail(net=VMINUS) — rejected: no obstacle-free native wire route joins the remaining VMINUS wire groups. Repeating connect_rail for VMINUS will fail again on this revision; first request move_symbols for one of ['C2', 'J1', 'R2', 
    - issue: visible_rail_continuity: VMINUS net lacks continuous wire path between U1 pin 4 and J1 pin 4; also missing path between U1 pin 4 and R2 pin 2

## review_loop_corpus_2026-10-27_qwen35_256k_run1 / inverting_gain
- **Outcome:** NO_PROGRESS — model repeated an invalid review: move_symbols references not found: ['3', 'unit']
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/inverting_gain/candidates/000/renders/schematic/InvertingGain.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/inverting_gain/candidates/001/renders/schematic/InvertingGain.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/inverting_gain/candidates/002/renders/schematic/InvertingGain.svg)
  - round 0: connect_rail(net=VPLUS) — applied → candidate 001
    - issue: visible_rail_continuity: The VPLUS and VMINUS nets lack continuous visible wire paths between their terminals (U1 pins 8/4 to J1 pins 3/4). Netlist equivalence does not satisfy the visual rubric.
    - issue: field_owner_association: Fields for U1 unit 3 (Reference and Value) are closer to neighboring symbols (R1, C2) than to their own symbol, violating the 5.08 mm owner-advantage heuristic.
  - round 1: move_symbols(references=['U1'], dx_mm=0.0, dy_mm=-2.54) — applied → candidate 002
    - issue: field_owner_association: U1 unit 3 Reference field is closer to R1 than its own symbol edge (owner_advantage_mm: 8.88 < 5.08 limit)
    - issue: field_owner_association: U1 unit 3 Value field is closer to C2 than its own symbol edge (owner_advantage_mm: 5.48 < 5.08 limit)
  - round 2: move_symbols(references=['U1', 'unit', '3'], dx_mm=0.0, dy_mm=-2.54) — rejected: move_symbols references not found: ['3', 'unit']
    - issue: field_owner_association: U1 unit 3 Reference and Value fields are too close to R1 (owner_advantage < 5.08 mm)
    - issue: visible_rail_continuity: Power rails for VPLUS/VMINUS rely on labels without explicit wire trunks in the lower-left quadrant
  - round 3: move_symbols(references=['U1', 'unit', '3'], dx_mm=0.0, dy_mm=2.54) — rejected: move_symbols references not found: ['3', 'unit']
    - issue: field_owner_association: U1 unit 3 Reference/Value fields are too close to R1 (owner_advantage < 5.08mm)
    - issue: visible_rail_continuity: Power rails for VPLUS/VMINUS rely on labels without explicit wire trunks in the lower-left quadrant

## review_loop_corpus_2026-10-27_qwen35_256k_run1 / linear_regulator
- **Outcome:** ACCEPTED_FOR_REVIEW — accepted `candidates/002/project/LinearRegulator.kicad_sch`
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/linear_regulator/candidates/000/renders/schematic/LinearRegulator.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/linear_regulator/candidates/001/renders/schematic/LinearRegulator.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/linear_regulator/candidates/002/renders/schematic/LinearRegulator.svg)
  - round 0: connect_rail(net=REF) — applied → candidate 001
    - issue: visible_rail_continuity: The visible wire path for the 'REF' net is broken between terminals (C1, C2, J3, U1). The visible wire path for the 'VIN' net is broken between terminals (C1, J1, U1).
  - round 1: connect_rail(net=VIN) — applied → candidate 002
    - issue: asserted power-net terminals lack a continuous visible wire path: [{'net': 'VIN', 'from_terminal': ['C1', '1'], 'to_terminal': ['J1', '1'], 'reason': 'no continuous native wire path between same-net terminals'}]
  - round 2: accepted

## review_loop_corpus_2026-10-27_qwen35_256k_run1 / noninverting_gain
- **Outcome:** NO_PROGRESS — model repeated an invalid review: 1 validation error for SchematicReview
actions.0.move_symbols
  Value error, move_symbols made no change; choose nonzero movem
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/noninverting_gain/candidates/000/renders/schematic/NoninvertingGain.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/noninverting_gain/candidates/001/renders/schematic/NoninvertingGain.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/noninverting_gain/candidates/002/renders/schematic/NoninvertingGain.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/noninverting_gain/candidates/003/renders/schematic/NoninvertingGain.svg), [004](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/noninverting_gain/candidates/004/renders/schematic/NoninvertingGain.svg)
  - round 0: connect_rail(net=VPLUS) — applied → candidate 001
    - issue: visible_rail_continuity: asserted power-net terminals lack a continuous visible wire path for nets VPLUS, VMINUS, and REF.
    - issue: field_owner_association: fields for U1 unit 3 are closer to C2 than their owning symbol, violating the 5.08 mm owner-advantage heuristic.
  - round 1: connect_rail(net=VMINUS) — applied → candidate 002
    - issue: visible_rail_continuity: no continuous native wire path between same-net terminals for VMINUS and REF nets
    - issue: field_owner_association: fields for U1 unit 3 are closer to C2 than their owning symbol
  - round 2: connect_rail(net=REF) — applied → candidate 003
    - issue: visible_rail_continuity: The REF net lacks a continuous visible wire path between terminals U1-5, C2-1, C1-2, J1-5, and R2-2. The schematic relies on implicit connections or label-only joins which fail the visual rubric.
    - issue: field_owner_association: Fields for U1 (unit 3) are too close to C2, violating the 5.08 mm owner-advantage heuristic.
  - round 3: move_symbols(references=['U1'], dx_mm=-1.27, dy_mm=0.0) — applied → candidate 004
    - issue: field_owner_association: U1 unit 3 Reference and Value fields are too close to C2, violating the 5.08 mm owner-advantage heuristic.
  - round 4: (no action) — rejected: 1 validation error for SchematicReview
actions.0.move_symbols
  Value error, move_symbols made no change; choose nonzero movement [type=value_error, input_value={'operation': 'move_symbo..._mm': 0.0, 
  - round 5: (no action) — rejected: 1 validation error for SchematicReview
actions.0.move_symbols
  Value error, move_symbols made no change; choose nonzero movement [type=value_error, input_value={'operation': 'move_symbo..._mm': 0.0, 

## review_loop_corpus_2026-10-27_qwen35_256k_run1 / rc_to_buffer
- **Outcome:** NO_PROGRESS — model repeated an invalid review: no obstacle-free native wire route joins the remaining rerouted moved-symbol net groups
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/rc_to_buffer/candidates/000/renders/schematic/RcToBuffer.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/rc_to_buffer/candidates/001/renders/schematic/RcToBuffer.svg)
  - round 0: connect_rail(net=VPLUS) — applied → candidate 001
    - issue: visible_rail_continuity: The VPLUS and VMINUS nets lack continuous visible wire paths between their terminals (U1 pins 8/4 and J1 pins 3/4). The schematic relies on implicit connections or label-only joins which violates
    - issue: field_owner_association: Fields for U1 unit 3 (Reference 'U1' and Value 'NE5532') are visually closer to C2 than to their own symbol, failing the owner-advantage heuristic.
  - round 1: move_symbols(references=['U1'], dx_mm=0.0, dy_mm=-25.4) — rejected: no obstacle-free native wire route joins the remaining rerouted moved-symbol net groups
    - issue: field_owner_association: U1 unit 3 Reference/Value fields are closer to C2 than their own symbol (owner_advantage < 5.08 mm)
    - issue: visible_rail_continuity: No continuous wire path exists between VMINUS terminals (U1 pin 4 and J1 pin 4)
  - round 2: move_symbols(references=['U1'], dx_mm=0.0, dy_mm=-25.4) — rejected: no obstacle-free native wire route joins the remaining rerouted moved-symbol net groups
    - issue: field_owner_association: U1 unit 3 Reference/Value fields are closer to C2 than their own symbol (owner_advantage < 5.08 mm)
    - issue: visible_rail_continuity: No continuous wire path exists between VMINUS terminals (U1 pin 4 and J1 pin 4)

## review_loop_corpus_2026-10-27_qwen35_256k_run1 / reference_555_led_flasher_v8
- **Outcome:** NO_PROGRESS — model repeated an invalid review: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/reference_555_led_flasher_v8/candidates/000/renders/schematic/Reference555LedFlasher.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/reference_555_led_flasher_v8/candidates/001/renders/schematic/Reference555LedFlasher.svg)
  - round 0: connect_rail(net=REF) — applied → candidate 001
    - issue: visible_rail_continuity: The schematic lacks explicit wire paths connecting terminals on the same net (REF and VCC). While electrically equivalent, the visual representation relies on implicit connections or label-only j
    - issue: label_association: Several fields show negative owner_advantage_mm values (e.g., C2 Reference has -11.52 mm), indicating they are visually closer to neighboring symbols than their own. This violates the clear association
  - round 1: connect_rail(net=VCC) — rejected: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this revision; first request move_symbols for one of ['J1', 'R1', 'R3', 'U1'] 
    - issue: visible_rail_continuity: FAIL - The VCC net lacks a continuous visible wire path between terminals R1, R3, J1, U1(4), and U1(8). The schematic relies on implicit connections or label-only joins which violates the visual 
    - issue: label_association: PASS - All component references and values are legible and clearly associated with their symbols.
  - round 2: (no action) — rejected: 1 validation error for SchematicReview
actions.0.move_symbols
  Value error, move_symbols made no change; choose nonzero movement [type=value_error, input_value={'operation': 'move_symbo..._mm': 0.0, 
  - round 3: connect_rail(net=VCC) — rejected: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this revision; first request move_symbols for one of ['J1', 'R1', 'R3', 'U1'] 
    - issue: visible_rail_continuity: VCC net lacks continuous visible wire path between terminals R1, R3, J1, U1 pins 4/8

## review_loop_corpus_2026-10-27_qwen35_256k_run1 / timer_astable
- **Outcome:** NO_PROGRESS — model repeated an invalid review: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/timer_astable/candidates/000/renders/schematic/TimerAstable.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/timer_astable/candidates/001/renders/schematic/TimerAstable.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_2026-10-27_qwen35_256k_run1/timer_astable/candidates/003/renders/schematic/TimerAstable.svg)
  - round 0: connect_rail(net=REF) — applied → candidate 001
    - issue: visible_rail_continuity: The visible wire paths for nets 'REF' and 'VCC' are discontinuous. Terminals on the same net (e.g., C2-2, J3-1, U1-1) lack a continuous native wire path between them.
    - issue: label_association: While fields pass distance checks, the visual association of power rails is ambiguous due to missing explicit wires, relying solely on labels which fails the visual rubric for 'visible_local_rails'.
  - round 1: connect_rail(net=VCC) — rejected: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this revision; first request move_symbols for one of ['J1', 'R1', 'U1'] by a g
    - issue: visible_rail_continuity: The VCC net lacks a continuous visible wire path between terminals R1-1, J1-1, U1-4, and U1-8. The schematic relies on label-only association for power distribution without explicit wiring geomet
    - issue: action_required: connect_rail
  - round 2: move_symbols(references=['J1'], dx_mm=0.0, dy_mm=12.7) — applied → candidate 003
    - issue: asserted power-net terminals lack a continuous visible wire path: [{'net': 'VCC', 'from_terminal': ['R1', '1'], 'to_terminal': ['J1', '1'], 'reason': 'no continuous native wire path between same-net terminals'}, {'net': 
    - issue: actions_needed_to_resolve_issues_before_next_review_step_or_acceptance_requesting_connect_rail_for_VCC_after_move_symbols_for_J1_by_127_mm_upward_offset_into_open_space_then_connect_rail_again
  - round 3: connect_rail(net=VCC) — rejected: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this revision; first request move_symbols for one of ['J1', 'R1', 'U1'] by a g
    - issue: visible_rail_continuity: VCC net lacks continuous visible wire path between terminals R1, J1, and U1

## review_loop_corpus_v3_2026-10-27_qwen35_256k_run1 / dual_rail_reference
- **Outcome:** NO_PROGRESS — model repeated an invalid review: no obstacle-free native wire route joins the remaining VMINUS wire groups. Repeating connect_rail for VMINUS will fail again o
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/dual_rail_reference/candidates/000/renders/schematic/DualRailReference.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/dual_rail_reference/candidates/001/renders/schematic/DualRailReference.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/dual_rail_reference/candidates/002/renders/schematic/DualRailReference.svg), [004](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/dual_rail_reference/candidates/004/renders/schematic/DualRailReference.svg)
  - round 0: connect_rail(net=VPLUS) — applied → candidate 001
    - issue: rail_presentation: VPLUS and VMINUS rails are not visually continuous or marked with power symbols at separated terminal groups.
    - issue: field_owner_association: Fields for U1 unit 3 (Reference/Value) are closer to C2 than to their own symbol, violating the 5.08 mm owner-advantage heuristic.
  - round 1: move_symbols(references=['U1'], dx_mm=0.0, dy_mm=-2.54) — applied → candidate 002
    - issue: field_owner_association: U1.3 Reference and Value fields are closer to C2 than to their own symbol (owner_advantage < 5.08 mm)
    - issue: rail_presentation: VMINUS net terminals are not visually joined or marked by a power symbol
  - round 2: connect_rail(net=VMINUS) — rejected: no obstacle-free native wire route joins the remaining VMINUS wire groups. Repeating connect_rail for VMINUS will fail again on this revision; first request move_symbols for one of ['C2', 'J1', 'R2', 
    - issue: visible_rail_continuity: FAIL - The VMINUS rail is visually fragmented into disconnected wire groups that are neither joined nor marked by a power symbol.
    - issue: rail_presentation: FAIL - Terminals on the VMINUS net (U1.4, C2.2, J1.4, R2.2) do not form a continuous visual rail or terminate at a matching power symbol.
  - round 3: move_symbols(references=['C2'], dx_mm=0.0, dy_mm=1.27) — applied → candidate 004
    - issue: visible_rail_continuity: VMINUS net terminals (C2.2, U1.4), (J1.4), and (R2.2) are in disconnected wire groups without a matching power symbol or continuous rail path.
    - issue: label_association: Field owner-association for C1/C2 references is marginal; ensure clear visual proximity to symbols.
  - round 4: connect_rail(net=VMINUS) — rejected: no obstacle-free native wire route joins the remaining VMINUS wire groups. Repeating connect_rail for VMINUS will fail again on this revision; first request move_symbols for one of ['C2', 'J1', 'R2', 
    - issue: rail_presentation: VMINUS net terminals (C2.2, U1.4), (J1.4), and (R2.2) are neither joined by a continuous wire nor marked by a VMINUS power symbol.

## review_loop_corpus_v3_2026-10-27_qwen35_256k_run1 / inverting_gain
- **Outcome:** TOOL_ERROR — timed out
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/inverting_gain/candidates/000/renders/schematic/InvertingGain.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/inverting_gain/candidates/001/renders/schematic/InvertingGain.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/inverting_gain/candidates/003/renders/schematic/InvertingGain.svg)
  - round 0: connect_rail(net=VPLUS) — applied → candidate 001
    - issue: rail_presentation: VPLUS and VMINUS rails are not visually continuous or marked with power symbols at separated terminal groups.
    - issue: field_owner_association: Fields for U1 unit 3 (Reference and Value) are too close to neighboring components R1 and C2, violating the 5.08 mm owner-advantage heuristic.
  - round 1: move_symbols(references=['U1'], dx_mm=0.0, dy_mm=-5.08) — rejected: no obstacle-free native wire route joins the remaining rerouted moved-symbol net groups
    - issue: field_owner_association: U1 unit 3 Reference field is closer to R1 (9.31 mm) than its own symbol edge (18.19 mm), violating the 5.08 mm owner-advantage limit.
    - issue: field_owner_association: U1 unit 3 Value field is closer to C2 (9.15 mm) than its own symbol edge (14.63 mm), violating the 5.08 mm owner-advantage limit.
  - round 2: move_symbols(references=['U1'], dx_mm=0.0, dy_mm=-2.54) — applied → candidate 003
    - issue: field_owner_association: U1 unit 3 Reference field is closer to R1 than its own symbol (owner_advantage_mm: 8.88 < 5.08)
    - issue: field_owner_association: U1 unit 3 Value field is closer to C2 than its own symbol (owner_advantage_mm: 5.48 < 5.08)

## review_loop_corpus_v3_2026-10-27_qwen35_256k_run1 / linear_regulator
- **Outcome:** ACCEPTED_FOR_REVIEW — accepted `candidates/002/project/LinearRegulator.kicad_sch`
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/linear_regulator/candidates/000/renders/schematic/LinearRegulator.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/linear_regulator/candidates/001/renders/schematic/LinearRegulator.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/linear_regulator/candidates/002/renders/schematic/LinearRegulator.svg)
  - round 0: connect_rail(net=REF) — applied → candidate 001
    - issue: rail_presentation: The REF and VIN nets have disconnected terminal groups that are neither joined by a continuous wire nor marked with a matching power symbol.
    - issue: visual_rail_continuity: Wires for the REF net (connecting C1, C2, J3, U1) and the VIN net (connecting C1, J1, U1) appear fragmented or lack explicit rail presentation as required by the review brief.
  - round 1: connect_rail(net=VIN) — applied → candidate 002
    - issue: rail_presentation: The VIN net terminals (C1.1, U1.1) and (J1.1) are not visually joined to a common rail nor marked by a matching power symbol.
    - issue: rail_presentation: The VOUT net terminals (J2.1, C2.1) and (U1.3) are not visually joined to a common rail nor marked by a matching power symbol.
  - round 2: accepted

## review_loop_corpus_v3_2026-10-27_qwen35_256k_run1 / noninverting_gain
- **Outcome:** NO_PROGRESS — model repeated an invalid review: 1 validation error for SchematicReview
actions.0.move_symbols
  Value error, move_symbols made no change; choose nonzero movem
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/noninverting_gain/candidates/000/renders/schematic/NoninvertingGain.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/noninverting_gain/candidates/001/renders/schematic/NoninvertingGain.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/noninverting_gain/candidates/003/renders/schematic/NoninvertingGain.svg)
  - round 0: connect_rail(net=REF) — applied → candidate 001
    - issue: rail_presentation: The REF, VMINUS, and VPLUS nets have disconnected terminal groups that are neither joined by continuous wires nor marked with power symbols.
    - issue: field_owner_association: Fields for U1 unit 3 (Reference and Value) are visually closer to C2 than to their own symbol, violating the owner-association heuristic.
  - round 1: (no action) — rejected: 1 validation error for SchematicReview
actions.0.move_symbols
  Value error, move_symbols made no change; choose nonzero movement [type=value_error, input_value={'operation': 'move_symbo...dx_mm': 0, 
  - round 2: move_symbols(references=['U1'], dx_mm=0.0, dy_mm=2.54) — applied → candidate 003
    - issue: field_owner_association: U1 unit 3 Reference/Value fields are closer to C2 than to their own symbol (owner_advantage < 5.08 mm)
    - issue: rail_presentation: VPLUS and VMINUS nets have disconnected wire groups without power symbols
  - round 3: (no action) — rejected: 1 validation error for SchematicReview
actions.0.move_symbols
  Value error, move_symbols made no change; choose nonzero movement [type=value_error, input_value={'operation': 'move_symbo...dx_mm': 0, 

## review_loop_corpus_v3_2026-10-27_qwen35_256k_run1 / rc_to_buffer
- **Outcome:** NO_PROGRESS — model repeated an invalid review: connect_rail made no change; VPLUS terminals are already wire-joined
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/rc_to_buffer/candidates/000/renders/schematic/RcToBuffer.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/rc_to_buffer/candidates/001/renders/schematic/RcToBuffer.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/rc_to_buffer/candidates/003/renders/schematic/RcToBuffer.svg), [004](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/rc_to_buffer/candidates/004/renders/schematic/RcToBuffer.svg)
  - round 0: connect_rail(net=VPLUS) — applied → candidate 001
    - issue: rail_presentation: VPLUS and VMINUS rails are not visually continuous or marked with power symbols at separated terminal groups.
    - issue: field_owner_association: Fields for U1 unit 3 (Reference/Value) are closer to C2 than to their own symbol, violating the 5.08 mm owner-advantage heuristic.
  - round 1: (no action) — rejected: 1 validation error for SchematicReview
actions.0.move_symbols
  Value error, move_symbols made no change; choose nonzero movement [type=value_error, input_value={'operation': 'move_symbo..._mm': 0.0, 
  - round 2: move_symbols(references=['U1'], dx_mm=0.0, dy_mm=1.27) — applied → candidate 003
    - issue: field_owner_association: U1.3 Reference/Value fields are closer to C2 than their own symbol (owner_advantage < 5.08 mm)
    - issue: rail_presentation: VMINUS net terminals (U1.4, J1.4, C2.2) are not visibly joined by a continuous rail nor marked by a power symbol
  - round 3: move_symbols(references=['U1'], dx_mm=0.0, dy_mm=-5.08) — applied → candidate 004
    - issue: field_owner_association: U1.3 Reference/Value fields are closer to C2 than their own symbol (owner_advantage < 5.08 mm)
    - issue: rail_presentation: VMINUS net terminals (U1.4, J1.4, C2.2) are not visibly joined by a continuous wire nor marked by a power symbol
  - round 4: connect_rail(net=VPLUS) — rejected: connect_rail made no change; VPLUS terminals are already wire-joined
    - issue: Unconnected wire endpoint at (1.2446, 0.6731) mm on net VPLUS
    - issue: Unconnected wire endpoint at (1.2573, 0.7747) mm on net VMINUS
  - round 5: connect_rail(net=VPLUS) — rejected: connect_rail made no change; VPLUS terminals are already wire-joined
    - issue: Unconnected wire endpoint at (1.2446, 0.6731) mm on net VPLUS
    - issue: Unconnected wire endpoint at (1.2573, 0.7747) mm on net VMINUS

## review_loop_corpus_v3_2026-10-27_qwen35_256k_run1 / reference_555_led_flasher_v8
- **Outcome:** NO_PROGRESS — model repeated an invalid review: use_power_symbols made no change; VCC has no rail wiring or labels
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/reference_555_led_flasher_v8/candidates/000/renders/schematic/Reference555LedFlasher.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/reference_555_led_flasher_v8/candidates/001/renders/schematic/Reference555LedFlasher.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/reference_555_led_flasher_v8/candidates/002/renders/schematic/Reference555LedFlasher.svg)
  - round 0: connect_rail(net=REF) — applied → candidate 001
    - issue: rail_presentation: The REF and VCC nets are not visually presented as continuous rails or marked with power symbols at each terminal group. Terminals for C2, J3, U1 (REF) and R1, R3, J1, U1 (VCC) are disconnected in the 
    - issue: label_association: Fields for components like C2, R2, D1, R3, J2, J3, J1, U1 show negative owner_advantage_mm values, indicating they are not visually closest to their owning symbols compared to neighbors.
  - round 1: use_power_symbols(net=VCC) — applied → candidate 002
    - issue: rail_presentation: VCC net terminals (R1.1, R3.1, J1.1, U1.4, U1.8) are not visually joined to a common rail nor marked by power symbols
  - round 2: use_power_symbols(net=VCC) — rejected: use_power_symbols made no change; VCC has no rail wiring or labels
    - issue: power_symbol_clearance: power symbol #PWR01 touches wire segment at 52.07mm x, 35.56-88.90mm y
  - round 3: use_power_symbols(net=VCC) — rejected: use_power_symbols made no change; VCC has no rail wiring or labels
    - issue: power_symbol_clearance: FAIL - power symbol #FLG01 touches wire segment (52.07, 35.56) -> (52.07, 88.90)
    - issue: rail_presentation: FAIL - VCC net terminals lack continuous native wire path or matching power symbols

## review_loop_corpus_v3_2026-10-27_qwen35_256k_run1 / sallen_key
- **Outcome:** NO_PROGRESS — model repeated an invalid review: no obstacle-free native wire route joins the remaining REF wire groups. Repeating connect_rail for REF will fail again on this
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/sallen_key/candidates/000/renders/schematic/SallenKey.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/sallen_key/candidates/002/renders/schematic/SallenKey.svg)
  - round 0: connect_rail(net=REF) — rejected: no obstacle-free native wire route joins the remaining REF wire groups. Repeating connect_rail for REF will fail again on this revision; first request move_symbols for one of ['C1', 'C2', 'C3', 'J1', 
    - issue: rail_presentation: The REF, VMINUS, and VPLUS nets are not visually joined by continuous wires nor marked by power symbols at their separated terminal groups.
    - issue: field_owner_association: Fields for U1 unit 3 (Reference/Value) are too close to C2 fields, violating the 5.08 mm owner-advantage heuristic.
  - round 1: move_symbols(references=['C1', 'C2', 'C3'], dx_mm=0.0, dy_mm=1.27) — applied → candidate 002
    - issue: rail_presentation: FAIL - Power rails (REF, VPLUS, VMINUS) are not visually continuous or marked with power symbols.
    - issue: field_owner_association: FAIL - Fields for U1.3 Reference and Value are too close to C2 fields.
  - round 2: connect_rail(net=REF) — rejected: no obstacle-free native wire route joins the remaining REF wire groups. Repeating connect_rail for REF will fail again on this revision; first request move_symbols for one of ['C1', 'C2', 'C3', 'J1', 
    - issue: rail_presentation: The REF, VPLUS, and VMINUS nets are electrically correct but visually disconnected. Terminals for these nets are neither joined by continuous wires nor marked by matching power symbols.
    - issue: label_association: Power rail terminals (e.g., U1.5, C1.2, J1.5) lack clear visual association with a shared rail or power symbol, violating the visible_local_rails criterion.

## review_loop_corpus_v3_2026-10-27_qwen35_256k_run1 / timer_astable
- **Outcome:** NO_PROGRESS — model repeated an invalid review: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/timer_astable/candidates/000/renders/schematic/TimerAstable.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run1/timer_astable/candidates/001/renders/schematic/TimerAstable.svg)
  - round 0: connect_rail(net=REF) — applied → candidate 001
    - issue: rail_presentation: The REF and VCC nets have disconnected terminal groups that are neither joined by continuous wires nor marked with power symbols.
    - issue: label_association: Fields for U1, C2, R2, J2, J3, J1, and C1 show negative owner_advantage_mm values, indicating they are visually closer to neighboring symbols than their own anchors.
  - round 1: connect_rail(net=VCC) — rejected: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this revision; first request move_symbols for one of ['J1', 'R1', 'U1'] by a g
    - issue: rail_presentation: VCC net terminals (R1.1, J1.1, U1.4, U1.8) are not visually joined to a common rail nor marked by power symbols
  - round 2: (no action) — rejected: 1 validation error for SchematicReview
actions.0.move_symbols
  Value error, move_symbols made no change; choose nonzero movement [type=value_error, input_value={'operation': 'move_symbo... 'dx_mm': 0
  - round 3: connect_rail(net=VCC) — rejected: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this revision; first request move_symbols for one of ['J1', 'R1', 'U1'] by a g
    - issue: rail_presentation: VCC net terminals (R1.1, J1.1, U1.4, U1.8) are not joined by a continuous rail nor marked by power symbols

## review_loop_corpus_v3_2026-10-27_qwen35_256k_run2 / dual_buffer
- **Outcome:** ACCEPTED_FOR_REVIEW — accepted `candidates/007/project/DualBufferM2b.kicad_sch`
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/dual_buffer/candidates/000/renders/schematic/DualBufferM2b.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/dual_buffer/candidates/001/renders/schematic/DualBufferM2b.svg), [004](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/dual_buffer/candidates/004/renders/schematic/DualBufferM2b.svg), [006](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/dual_buffer/candidates/006/renders/schematic/DualBufferM2b.svg), [007](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/dual_buffer/candidates/007/renders/schematic/DualBufferM2b.svg)
  - round 0: connect_rail(net=VPLUS) — applied → candidate 001
    - issue: rail_presentation: VPLUS and VMINUS rails are not visually continuous or marked with power symbols at separated terminal groups.
    - issue: field_owner_association: Fields for U1 unit 3 (Reference/Value) are too close to C2 fields, violating the 5.08 mm owner-advantage heuristic.
  - round 1: (no action) — rejected: 1 validation error for SchematicReview
actions.0.move_symbols
  Value error, move_symbols made no change; choose nonzero movement [type=value_error, input_value={'operation': 'move_symbo...dx_mm': 0, 
  - round 2: connect_rail(net=VMINUS) — rejected: no obstacle-free native wire route joins the remaining VMINUS wire groups. Repeating connect_rail for VMINUS will fail again on this revision; request use_power_symbols for VMINUS to draw it with powe
    - issue: rail_presentation: VMINUS net terminals (C2.2, U1.4, J1.4) are not joined by a continuous wire nor marked by a power symbol.
    - issue: field_owner_association: Fields for U1 unit 3 (Reference and Value) are too close to C2 fields, violating the 5.08 mm owner-advantage heuristic.
  - round 3: use_power_symbols(net=VMINUS) — applied → candidate 004
    - issue: rail_presentation: VMINUS net terminals are not joined by a continuous wire nor marked by a power symbol.
    - issue: field_owner_association: Fields for U1 unit 3 (Reference and Value) are too close to C2 fields, violating the 5.08 mm owner-advantage heuristic.
  - round 4: (no action) — rejected: 1 validation error for SchematicReview
actions.0.move_symbols
  Value error, move_symbols made no change; choose nonzero movement [type=value_error, input_value={'operation': 'move_symbo... 'dx_mm': 0
  - round 5: move_symbols(references=['U1'], dx_mm=12.7, dy_mm=0.0) — applied → candidate 006
    - issue: field_owner_association: U1 unit 3 fields are too close to C2 fields (owner_advantage < 5.08 mm)
  - round 6: connect_rail(net=VMINUS) — applied → candidate 007
    - issue: The VMINUS net has disconnected terminal groups: U1 pin 4, C2 pin 2, and J1 pin 4 are not visibly connected by a continuous wire or power symbol.
    - issue: The VPLUS net has disconnected terminal groups: U1 pin 8, C1 pin 1, and J1 pin 3 are not visibly connected by a continuous wire or power symbol.
  - round 7: accepted

## review_loop_corpus_v3_2026-10-27_qwen35_256k_run2 / dual_rail_reference
- **Outcome:** NO_PROGRESS — model repeated an invalid review: no obstacle-free native wire route joins the remaining VMINUS wire groups. Repeating connect_rail for VMINUS will fail again o
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/dual_rail_reference/candidates/000/renders/schematic/DualRailReference.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/dual_rail_reference/candidates/001/renders/schematic/DualRailReference.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/dual_rail_reference/candidates/002/renders/schematic/DualRailReference.svg), [004](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/dual_rail_reference/candidates/004/renders/schematic/DualRailReference.svg)
  - round 0: connect_rail(net=VPLUS) — applied → candidate 001
    - issue: rail_presentation: VPLUS and VMINUS rails are not visually continuous or marked with power symbols at separated terminal groups.
    - issue: field_owner_association: Fields for U1 unit 3 (Reference/Value) are closer to C2 than to their own symbol, violating the 5.08 mm owner-advantage heuristic.
  - round 1: move_symbols(references=['U1'], dx_mm=0.0, dy_mm=-2.54) — applied → candidate 002
    - issue: field_owner_association: U1.3 Reference/Value fields are too close to C2 (owner_advantage < 5.08 mm)
    - issue: rail_presentation: VMINUS net terminals are not visually joined or marked with a power symbol
  - round 2: connect_rail(net=VMINUS) — rejected: no obstacle-free native wire route joins the remaining VMINUS wire groups. Repeating connect_rail for VMINUS will fail again on this revision; request use_power_symbols for VMINUS to draw it with powe
    - issue: visible_rail_continuity: FAIL - The VMINUS rail is fragmented into disconnected wire groups without a continuous path or matching power symbol.
    - issue: rail_presentation: FAIL - Terminals on the VMINUS net are not visibly connected to a shared rail trunk nor marked by a VMINUS power symbol.
  - round 3: use_power_symbols(net=VMINUS) — applied → candidate 004
    - issue: visible_rail_continuity: FAIL - VMINUS net terminals are not visually connected by a continuous rail or marked by power symbols
  - round 4: connect_rail(net=VMINUS) — rejected: no obstacle-free native wire route joins the remaining VMINUS wire groups. Repeating connect_rail for VMINUS will fail again on this revision; request use_power_symbols for VMINUS to draw it with powe
    - issue: The VMINUS net has disconnected terminal groups: terminals at U1 pin 4, C2 pin 2, J1 pin 4, and R2 pin 2 are not visibly connected by a continuous wire or power symbol.
    - issue: The VPLUS net similarly shows disconnected terminal groups that lack explicit rail wiring or power symbols.

## review_loop_corpus_v3_2026-10-27_qwen35_256k_run2 / inverting_gain
- **Outcome:** NO_PROGRESS — model repeated an invalid review: no obstacle-free native wire route joins the remaining rerouted moved-symbol net groups
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/inverting_gain/candidates/000/renders/schematic/InvertingGain.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/inverting_gain/candidates/001/renders/schematic/InvertingGain.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/inverting_gain/candidates/002/renders/schematic/InvertingGain.svg)
  - round 0: connect_rail(net=VPLUS) — applied → candidate 001
    - issue: rail_presentation: VPLUS and VMINUS rails are not visually continuous or marked with power symbols at separated terminal groups.
    - issue: field_owner_association: Fields for U1 unit 3 (Reference/Value) are too close to neighboring components R1 and C2, violating the 5.08 mm owner-advantage heuristic.
  - round 1: move_symbols(references=['U1'], dx_mm=0.0, dy_mm=-2.54) — applied → candidate 002
    - issue: field_owner_association: U1 unit 3 Reference field is closer to R1 than its own symbol (owner_advantage_mm: 8.88 < 5.08)
    - issue: field_owner_association: U1 unit 3 Value field is closer to C2 than its own symbol (owner_advantage_mm: 5.48 < 5.08)
  - round 2: move_symbols(references=['U1'], dx_mm=0.0, dy_mm=-2.54) — rejected: no obstacle-free native wire route joins the remaining rerouted moved-symbol net groups
    - issue: field_owner_association: U1 unit 3 Reference and Value fields are too close to R1 (owner_advantage_mm < 5.08)
    - issue: visible_local_rails: REF net terminals lack explicit power symbols or continuous rail wiring
  - round 3: move_symbols(references=['U1'], dx_mm=0.0, dy_mm=-2.54) — rejected: no obstacle-free native wire route joins the remaining rerouted moved-symbol net groups
    - issue: field_owner_association: U1 unit 3 Reference/Value fields are too close to R1 (owner_advantage < 5.08mm)
    - issue: visible_local_rails: REF net terminals lack explicit power symbols or continuous rail wiring

## review_loop_corpus_v3_2026-10-27_qwen35_256k_run2 / linear_regulator
- **Outcome:** ACCEPTED_FOR_REVIEW — accepted `candidates/002/project/LinearRegulator.kicad_sch`
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/linear_regulator/candidates/000/renders/schematic/LinearRegulator.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/linear_regulator/candidates/001/renders/schematic/LinearRegulator.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/linear_regulator/candidates/002/renders/schematic/LinearRegulator.svg)
  - round 0: connect_rail(net=REF) — applied → candidate 001
    - issue: rail_presentation: The REF and VIN nets have disconnected terminal groups that are neither joined by a continuous wire nor marked with a matching power symbol.
    - issue: rail_presentation: Power symbols for the REF and VIN rails are missing or not visually associated with their respective terminals.
  - round 1: connect_rail(net=VIN) — applied → candidate 002
    - issue: rail_presentation: The VIN net terminals (C1.1, U1.1, J1.1) are not visually joined to a common rail nor marked by a matching power symbol.
    - issue: rail_presentation: The VOUT net terminals (J2.1, C2.1, U1.3) are not visually joined to a common rail nor marked by a matching power symbol.
  - round 2: accepted

## review_loop_corpus_v3_2026-10-27_qwen35_256k_run2 / noninverting_gain
- **Outcome:** NO_PROGRESS — model repeated an invalid review: move_symbols references not found: ['3', 'unit']
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/noninverting_gain/candidates/000/renders/schematic/NoninvertingGain.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/noninverting_gain/candidates/001/renders/schematic/NoninvertingGain.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/noninverting_gain/candidates/002/renders/schematic/NoninvertingGain.svg)
  - round 0: connect_rail(net=REF) — applied → candidate 001
    - issue: rail_presentation: FAIL - Power nets (REF, VPLUS, VMINUS) are not visually connected via continuous wires or power symbols.
    - issue: field_owner_association: FAIL - Fields for U1 unit 3 are too close to C2 fields, violating the 5.08 mm owner-advantage heuristic.
  - round 1: use_power_symbols(net=VPLUS) — applied → candidate 002
    - issue: rail_presentation: VPLUS and VMINUS rails are not visibly continuous or marked with power symbols at separated terminal groups.
    - issue: field_owner_association: Fields for U1 unit 3 (Reference/Value) are visually closer to C2 than to their own symbol, violating the 5.08 mm owner-advantage heuristic.
  - round 2: move_symbols(references=['U1', 'unit', '3'], dx_mm=0.0, dy_mm=2.54) — rejected: move_symbols references not found: ['3', 'unit']
    - issue: field_owner_association: U1.3 Reference/Value fields are too close to C2 (owner_advantage_mm > 5.08)
    - issue: rail_presentation: VMINUS net terminals are not visibly connected to a shared rail or marked by a power symbol
  - round 3: move_symbols(references=['U1', 'unit', '3'], dx_mm=12.7, dy_mm=0.0) — rejected: move_symbols references not found: ['3', 'unit']
    - issue: field_owner_association: U1.3 Reference/Value fields are too close to C2 (owner_advantage < 5.08 mm)
    - issue: rail_presentation: VMINUS net terminals are not visually joined or marked by a power symbol

## review_loop_corpus_v3_2026-10-27_qwen35_256k_run2 / rc_to_buffer
- **Outcome:** NO_PROGRESS — model repeated an invalid review: connect_rail made no change; REF terminals are already wire-joined
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/rc_to_buffer/candidates/000/renders/schematic/RcToBuffer.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/rc_to_buffer/candidates/001/renders/schematic/RcToBuffer.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/rc_to_buffer/candidates/002/renders/schematic/RcToBuffer.svg)
  - round 0: connect_rail(net=VPLUS) — applied → candidate 001
    - issue: rail_presentation: VPLUS and VMINUS rails are not visually continuous or marked with power symbols at separated terminal groups.
    - issue: field_owner_association: Fields for U1 unit 3 (Reference/Value) are closer to C2 than to their own symbol, violating the 5.08 mm owner-advantage heuristic.
  - round 1: move_symbols(references=['U1'], dx_mm=0.0, dy_mm=-5.08) — applied → candidate 002
    - issue: field_owner_association: U1 unit 3 Reference and Value fields are closer to C2 than to their own symbol (owner_advantage < 5.08 mm)
    - issue: rail_presentation: VMINUS net terminals (U1.4, C2.2, J1.4) are not joined by a continuous wire nor marked by a power symbol
  - round 2: connect_rail(net=REF) — rejected: connect_rail made no change; REF terminals are already wire-joined
    - issue: Unconnected wire endpoint at J1 pin 5 (REF net) and U1B pin 5 (REF net)
    - issue: Power rail VPLUS/VMINUS/REF not visually continuous with power symbols or shared rails
  - round 3: connect_rail(net=REF) — rejected: connect_rail made no change; REF terminals are already wire-joined
    - issue: Unconnected wire endpoint at J1 pin 5 (REF net) visually stranded near connector body.
    - issue: Power rail REF lacks explicit power symbol at terminal groups; relies on text labels only.

## review_loop_corpus_v3_2026-10-27_qwen35_256k_run2 / reference_555_led_flasher_v8
- **Outcome:** LIMIT_REACHED — review budget exhausted before edit and re-review
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/reference_555_led_flasher_v8/candidates/000/renders/schematic/Reference555LedFlasher.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/reference_555_led_flasher_v8/candidates/001/renders/schematic/Reference555LedFlasher.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/reference_555_led_flasher_v8/candidates/002/renders/schematic/Reference555LedFlasher.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/reference_555_led_flasher_v8/candidates/003/renders/schematic/Reference555LedFlasher.svg), [004](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/reference_555_led_flasher_v8/candidates/004/renders/schematic/Reference555LedFlasher.svg), [005](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/reference_555_led_flasher_v8/candidates/005/renders/schematic/Reference555LedFlasher.svg), [006](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/reference_555_led_flasher_v8/candidates/006/renders/schematic/Reference555LedFlasher.svg), [007](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/reference_555_led_flasher_v8/candidates/007/renders/schematic/Reference555LedFlasher.svg)
  - round 0: connect_rail(net=REF) — applied → candidate 001
    - issue: rail_presentation: The REF and VCC nets are not visually presented as continuous rails or marked with power symbols at each separated terminal group. Terminals for C2, J3, U1 (REF) and R1, R3, J1, U1 (VCC) are disconnect
    - issue: action_plan_01_connect_rail_ref
  - round 1: use_power_symbols(net=VCC) — applied → candidate 002
    - issue: rail_presentation: VCC net terminals are not visually joined or marked by power symbols
  - round 2: use_power_symbols(net=VCC) — applied → candidate 003
    - issue: power_symbol_clearance: #PWR01 (VCC) touches wire 52.070000 35.560000 -> 52.070000 88.900000
  - round 3: use_power_symbols(net=VCC) — applied → candidate 004
    - issue: power_symbol_clearance: #PWR01 (VCC) touches wire 52.070000 35.560000 -> 52.070000 88.900000
  - round 4: use_power_symbols(net=VCC) — applied → candidate 005
    - issue: power_symbol_clearance: power symbol #PWR01 on net VCC touches wire segment (52.07, 35.56) -> (52.07, 88.90)
  - round 5: use_power_symbols(net=VCC) — applied → candidate 006
    - issue: power_symbol_clearance: #PWR01 (VCC) touches wire 52.070000 35.560000 -> 52.070000 88.900000
  - round 6: use_power_symbols(net=VCC) — applied → candidate 007
    - issue: power_symbol_clearance: #PWR01 (VCC) touches wire 52.070000 35.560000 -> 52.070000 88.900000
  - round 7: use_power_symbols(net=VCC) — not applied
    - issue: power_symbol_clearance: #PWR01 (VCC) touches wire 52.070000 35.560000 -> 52.070000 88.900000

## review_loop_corpus_v3_2026-10-27_qwen35_256k_run2 / sallen_key
- **Outcome:** LIMIT_REACHED — wall-clock or model-token budget exhausted
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/sallen_key/candidates/000/renders/schematic/SallenKey.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/sallen_key/candidates/002/renders/schematic/SallenKey.svg), [004](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/sallen_key/candidates/004/renders/schematic/SallenKey.svg), [006](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/sallen_key/candidates/006/renders/schematic/SallenKey.svg), [007](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/sallen_key/candidates/007/renders/schematic/SallenKey.svg)
  - round 0: connect_rail(net=REF) — rejected: no obstacle-free native wire route joins the remaining REF wire groups. Repeating connect_rail for REF will fail again on this revision; request use_power_symbols for REF to draw it with power symbols
    - issue: rail_presentation: The REF, VMINUS, and VPLUS nets have terminals that are neither joined by a continuous wire nor marked by a matching power symbol.
    - issue: field_owner_association: Fields for U1 unit 3 (Reference and Value) are closer to C2 than to their own symbol, violating the owner-advantage heuristic.
  - round 1: use_power_symbols(net=REF) — applied → candidate 002
    - issue: rail_presentation: FAIL - Power nets (REF, VMINUS, VPLUS) are not visually connected via continuous wires or power symbols.
    - issue: field_owner_association: FAIL - Fields for U1.3 Reference and Value are too close to C2 fields.
  - round 2: connect_rail(net=VPLUS) — rejected: no obstacle-free native wire route joins the remaining VPLUS wire groups. Repeating connect_rail for VPLUS will fail again on this revision; request use_power_symbols for VPLUS to draw it with power s
    - issue: rail_presentation: VPLUS and VMINUS rails are not visually continuous or marked with power symbols at separated terminal groups.
    - issue: field_owner_association: Fields for U1 unit 3 (Reference/Value) are closer to C2 than to their own symbol, violating the 5.08 mm owner-advantage heuristic.
  - round 3: use_power_symbols(net=VPLUS) — applied → candidate 004
    - issue: rail_presentation: VPLUS and VMINUS rails are not visually continuous or marked with power symbols.
    - issue: field_owner_association: Fields for U1 unit 3 (Reference/Value) are too close to C2 fields, violating the 5.08 mm owner-advantage heuristic.
  - round 4: connect_rail(net=VMINUS) — rejected: no obstacle-free native wire route joins the remaining VMINUS wire groups. Repeating connect_rail for VMINUS will fail again on this revision; request use_power_symbols for VMINUS to draw it with powe
    - issue: rail_presentation: VMINUS net terminals (C2.2, U1.4) and (J1.4) are not joined by a continuous wire nor marked by a power symbol.
    - issue: rail_presentation: VPLUS net terminals (U1.8, J1.3) are not joined by a continuous wire nor marked by a power symbol.
  - round 5: use_power_symbols(net=VMINUS) — applied → candidate 006
    - issue: rail_presentation: FAIL - VMINUS net terminals are not joined or marked by power symbols.
    - issue: power_symbol_clearance: FAIL - Power symbol #PWR07 touches a wire segment.
  - round 6: use_power_symbols(net=VPLUS) — applied → candidate 007
    - issue: power_symbol_clearance: #PWR07 (VPLUS) touches wire 25.400000 33.020000 -> 25.400000 66.040000
    - issue: power_symbol_clearance: #PWR09 (VMINUS) touches #FLG02 and wire 25.400000 33.020000 -> 25.400000 66.040000
  - round 7: move_symbols(references=['U1'], dx_mm=2.54, dy_mm=0.0) — not applied
    - issue: field_owner_association: U1 unit 3 Reference/Value fields are closer to C2 than their own symbol (owner_advantage < 5.08 mm)
    - issue: power_symbol_clearance: #PWR09 (VMINUS) and #PWR07 (VPLUS) touch wires or labels

## review_loop_corpus_v3_2026-10-27_qwen35_256k_run2 / timer_astable
- **Outcome:** NO_PROGRESS — model repeated an invalid review: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/timer_astable/candidates/000/renders/schematic/TimerAstable.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/timer_astable/candidates/001/renders/schematic/TimerAstable.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-27_qwen35_256k_run2/timer_astable/candidates/003/renders/schematic/TimerAstable.svg)
  - round 0: connect_rail(net=REF) — applied → candidate 001
    - issue: rail_presentation: The REF and VCC nets have terminals that are neither joined by a continuous wire trunk nor marked by a matching power symbol.
    - issue: label_association: Fields for J3, J1, U1, C2, R2, J2 are visually stranded or ambiguous relative to their owning symbols.
  - round 1: connect_rail(net=VCC) — rejected: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this revision; request use_power_symbols for VCC to draw it with power symbols
    - issue: rail_presentation: VCC net terminals (R1.1, J1.1, U1.4, U1.8) are not joined by a continuous rail nor marked by power symbols
  - round 2: use_power_symbols(net=VCC) — applied → candidate 003
    - issue: rail_presentation: FAIL - VCC net terminals are not visually joined or marked by power symbols
  - round 3: connect_rail(net=VCC) — rejected: no obstacle-free native wire route joins the remaining VCC wire groups. Repeating connect_rail for VCC will fail again on this revision; request use_power_symbols for VCC to draw it with power symbols
    - issue: visible_rail_continuity: The VCC net has terminals at R1, J1, U1(4), and U1(8). The image shows these are not connected by a single continuous wire or power symbol; they appear as separate segments. This violates the req
    - issue: label_association: Several fields (e.g., J2, U1) show negative owner_advantage_mm values in the diagnostics, indicating their labels are not visually closest to their owning symbols compared to neighboring references. Th

## review_loop_corpus_v3_2026-10-31_qwen35_32k_run1 / inverting_gain
- **Outcome:** ACCEPTED_FOR_REVIEW — accepted `candidates/003/project/InvertingGain.kicad_sch`
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-31_qwen35_32k_run1/inverting_gain/candidates/000/renders/schematic/InvertingGain.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-31_qwen35_32k_run1/inverting_gain/candidates/001/renders/schematic/InvertingGain.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-31_qwen35_32k_run1/inverting_gain/candidates/003/renders/schematic/InvertingGain.svg)
  - round 0: move_field(reference=U1, field=Reference, x_mm=91.44, y_mm=66.04) — applied → candidate 001
    - issue: field_owner_association: U1 unit 3 Reference field is closer to R1 (9.31 mm) than its own symbol edge (18.19 mm), failing the 5.08 mm owner-advantage limit.
    - issue: field_owner_association: U1 unit 3 Value field is closer to C2 (9.15 mm) than its own symbol edge (14.63 mm), failing the 5.08 mm owner-advantage limit.
  - round 1: move_field(reference=U1, field=Value, x_mm=100.33, y_mm=68.74) — rejected: move_field for U1.Value made no change; choose a different position
    - issue: field_owner_association: The 'Value' field for U1 unit 3 (NE5532) is visually closer to C2's reference label than its own symbol, violating the owner-advantage heuristic.
  - round 2: move_field(reference=U1, field=Value, x_mm=91.44, y_mm=68.74) — applied → candidate 003
    - issue: field_owner_association: U1 unit 3 Value field is visually closer to C2 than its owner (owner_advantage_mm: 5.48 < 5.08 limit)
  - round 3: accepted

## review_loop_corpus_v3_2026-10-31_qwen35_32k_run1 / sallen_key
- **Outcome:** NO_PROGRESS — model repeated an invalid review: no clear position for a VPLUS power symbol at ['J1.3']; wiring of ['OUT', 'VMINUS'] and nearby drawing items block it; if OUT,
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-31_qwen35_32k_run1/sallen_key/candidates/000/renders/schematic/SallenKey.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-31_qwen35_32k_run1/sallen_key/candidates/001/renders/schematic/SallenKey.svg)
  - round 0: connect_rail(net=REF, replace_existing=True) — applied → candidate 001
    - issue: rail_presentation: The asserted power nets (REF, VPLUS, VMINUS) are electrically equivalent but visually disconnected. Terminals for each net are in separate wire groups that are neither joined by a continuous wire nor m
    - issue: field_owner_association: Fields for U1 unit 3 (Reference and Value) are too close to C2, violating the owner-advantage heuristic.
  - round 1: connect_rail(net=VPLUS, replace_existing=True) — rejected: connect_rail wired what it could of VPLUS, but marking the unreachable groups failed: no clear position for a VPLUS power symbol at ['J1.3']; wiring of ['OUT', 'VMINUS'] and nearby drawing items block
    - issue: rail_presentation: The VPLUS, VMINUS, and REF nets are not visually joined by continuous wires nor marked by power symbols at their separated terminal groups.
    - issue: field_owner_association: Fields for U1 unit 3 (Reference and Value) are closer to C2 than to their own symbol, violating the owner-advantage heuristic.
  - round 2: use_power_symbols(net=VPLUS) — rejected: no clear position for a VPLUS power symbol at ['J1.3']; wiring of ['OUT', 'VMINUS'] and nearby drawing items block it; if OUT, VMINUS is an asserted rail, request use_power_symbols for it first so its
    - issue: rail_presentation: FAIL - VPLUS and VMINUS rails are not visually joined or marked by power symbols at all terminals.
    - issue: field_owner_association: FAIL - Fields for U1 unit 3 are too close to C2 fields, violating the 5.08 mm owner-advantage heuristic.
  - round 3: use_power_symbols(net=VPLUS) — rejected: no clear position for a VPLUS power symbol at ['J1.3']; wiring of ['OUT', 'VMINUS'] and nearby drawing items block it; if OUT, VMINUS is an asserted rail, request use_power_symbols for it first so its
    - issue: rail_presentation: FAIL - VPLUS and VMINUS rails are not visually joined or marked by power symbols at all terminals.
    - issue: field_owner_association: FAIL - Fields for U1 unit 3 are too close to C2 fields, violating the 5.08 mm owner-advantage heuristic.

## review_loop_corpus_v3_2026-10-31_qwen35_32k_run2 / led_reverse_supply
- **Outcome:** NO_PROGRESS — model repeated an invalid review: move_field for J1.Value made no change; choose a different position
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-31_qwen35_32k_run2/led_reverse_supply/candidates/000/renders/schematic/LedReverseSupply.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-31_qwen35_32k_run2/led_reverse_supply/candidates/002/renders/schematic/LedReverseSupply.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-31_qwen35_32k_run2/led_reverse_supply/candidates/003/renders/schematic/LedReverseSupply.svg)
  - round 0: connect_rail(net=VNEG, replace_existing=True) — rejected: add_wire_path, connect_rail and use_power_symbols are limited to explicitly asserted power nets; valid nets are []
    - issue: observed content outside A4 margin
  - round 1: move_field(reference=J1, field=Reference, x_mm=39.37, y_mm=27.725) — applied → candidate 002
    - issue: observed content outside A4 margin
  - round 2: move_field(reference=J1, field=Value, x_mm=45.37, y_mm=27.725) — applied → candidate 003
    - issue: field_association: J1 Reference and Value fields are overlapping or too close, violating field_separation == 0 requirement
  - round 3: move_field(reference=J1, field=Value, x_mm=45.37, y_mm=27.725) — rejected: move_field for J1.Value made no change; choose a different position
    - issue: field_separation: overlapping reference/value fields for J1
  - round 4: move_field(reference=J1, field=Value, x_mm=45.37, y_mm=27.725) — rejected: move_field for J1.Value made no change; choose a different position
    - issue: field_separation: Overlapping fields for J1 (Reference/Value) violate field separation rules

## review_loop_corpus_v3_2026-10-31_qwen35_32k_run2 / sallen_key
- **Outcome:** NO_PROGRESS — model repeated an invalid review: no clear position for a VPLUS power symbol at ['J1.3']; wiring of ['OUT', 'VMINUS'] and nearby drawing items block it; if OUT,
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-31_qwen35_32k_run2/sallen_key/candidates/000/renders/schematic/SallenKey.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/review_loop_corpus_v3_2026-10-31_qwen35_32k_run2/sallen_key/candidates/001/renders/schematic/SallenKey.svg)
  - round 0: connect_rail(net=REF, replace_existing=True) — applied → candidate 001
    - issue: rail_presentation: The asserted power nets (REF, VPLUS, VMINUS) are electrically equivalent but visually disconnected. Terminals for each net are in separate wire groups that are neither joined by continuous wires nor ma
    - issue: label_association: Power rail terminals lack clear visual association with their respective rails due to missing connecting wires or power symbols.
  - round 1: connect_rail(net=VPLUS, replace_existing=True) — rejected: connect_rail wired what it could of VPLUS, but marking the unreachable groups failed: no clear position for a VPLUS power symbol at ['J1.3']; wiring of ['OUT', 'VMINUS'] and nearby drawing items block
    - issue: rail_presentation: FAIL - The VPLUS and VMINUS rails are not visually continuous. Terminals for U1 (pins 8, 4), C1/C2, and J1 are in separate wire groups that are neither joined by a common wire nor marked by a matching 
    - issue: visual_readability: WARN - Power rail connections rely on implicit netlist equivalence rather than explicit visual wiring or symbols, which violates the visual rubric for 'visible_local_rails'.
  - round 2: use_power_symbols(net=VPLUS) — rejected: no clear position for a VPLUS power symbol at ['J1.3']; wiring of ['OUT', 'VMINUS'] and nearby drawing items block it; if OUT, VMINUS is an asserted rail, request use_power_symbols for it first so its
    - issue: rail_presentation: FAIL - The VPLUS and VMINUS rails are not correctly presented. Terminals for these nets (e.g., J1.3, J1.4, U1.8, U1.4) are in separate wire groups that are neither joined by a continuous wire nor marke
    - issue: diagnostics: The diagnostics confirm that wire groups for VPLUS and VMINUS nets lack the required connection to the rest of their rail or a marking power symbol.
  - round 3: use_power_symbols(net=VPLUS) — rejected: no clear position for a VPLUS power symbol at ['J1.3']; wiring of ['OUT', 'VMINUS'] and nearby drawing items block it; if OUT, VMINUS is an asserted rail, request use_power_symbols for it first so its
    - issue: rail_presentation: FAIL - The VPLUS and VMINUS rails are not visually continuous or marked by power symbols at all terminals. Specifically, the wire groups for VPLUS (connecting J1.3, C1.1, U1.8) and VMINUS (connecting J
    - issue: visual_readability: The layout of power rails is confusing because the wires for VPLUS and VMINUS do not form a single continuous visual path to their respective power symbols, violating the rail_presentation requirement

## schematic_review_loop_2026-10-25_run1 / rc_corrupted
- **Outcome:** ACCEPTED_FOR_REVIEW — accepted `candidates/001/project/DevstralV4RcLowpass1kHz.kicad_sch`
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/rc_corrupted/candidates/000/renders/schematic/corrupted_rc.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/rc_corrupted/candidates/001/renders/schematic/DevstralV4RcLowpass1kHz.svg)
  - round 0: regenerate_schematic() — applied → candidate 001
    - issue: Pin not connected: J1 Pin 1
    - issue: Pin not connected: R1 Pin 1
  - round 1: accepted

## schematic_review_loop_2026-10-25_run1 / rc_corrupted_v2
- **Outcome:** ACCEPTED_FOR_REVIEW — accepted `candidates/001/project/DevstralV4RcLowpass1kHz.kicad_sch`
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/rc_corrupted_v2/candidates/000/renders/schematic/corrupted_rc.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/rc_corrupted_v2/candidates/001/renders/schematic/DevstralV4RcLowpass1kHz.svg)
  - round 0: regenerate_schematic() — applied → candidate 001
    - issue: Pin not connected: J1 Pin 1
    - issue: Pin not connected: R1 Pin 1
  - round 1: accepted

## schematic_review_loop_2026-10-25_run1 / rc_final
- **Outcome:** ACCEPTED_FOR_REVIEW — accepted `candidates/001/project/DevstralV4RcLowpass1kHz.kicad_sch`
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/rc_final/candidates/000/renders/schematic/corrupted_rc.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/rc_final/candidates/001/renders/schematic/DevstralV4RcLowpass1kHz.svg)
  - round 0: regenerate_schematic() — applied → candidate 001
    - issue: Pin not connected: J1 Pin 1
    - issue: Pin not connected: R1 Pin 1
  - round 1: accepted

## schematic_review_loop_2026-10-25_run1 / rc_labels_locked
- **Outcome:** ACCEPTED_FOR_REVIEW — accepted `candidates/004/project/distant_value_rc.kicad_sch`
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/rc_labels_locked/candidates/000/renders/schematic/distant_value_rc.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/rc_labels_locked/candidates/001/renders/schematic/distant_value_rc.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/rc_labels_locked/candidates/003/renders/schematic/distant_value_rc.svg), [004](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/rc_labels_locked/candidates/004/renders/schematic/distant_value_rc.svg)
  - round 0: move_field(reference=C1, field=Value, x_mm=89.0, y_mm=62.5) — applied → candidate 001
    - issue: The 'Value' field for component C1 is located at (150.0, 100.0), which is 77.369106 mm away from the component symbol. This exceeds the acceptable proximity limit and violates the field_locality check.
  - round 1: move_field(reference=C1:1.Value, field=Value, x_mm=95.0, y_mm=62.5) — rejected: move_field must identify one existing reference/unit
    - issue: Field collision: C1's Reference and Value fields overlap at coordinates (88.9, 62.23) and (89.0, 62.5). The Value field '15n' is visually obscured or too close to the Reference field 'C1', violating clear association.
  - round 2: move_field(reference=C1, field=Value, x_mm=92.0, y_mm=62.5) — applied → candidate 003
    - issue: Field collision: C1's Reference and Value fields are overlapping or too close, violating field separation best practices.
  - round 3: move_field(reference=C1, field=Value, x_mm=95.0, y_mm=62.5) — applied → candidate 004
    - issue: Field collision: C1's Reference and Value fields overlap or are too close, violating field separation best practices.
  - round 4: accepted

## schematic_review_loop_2026-10-25_run1 / rc_visual_gated
- **Outcome:** ACCEPTED_FOR_REVIEW — accepted `candidates/001/project/distant_value_rc.kicad_sch`
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/rc_visual_gated/candidates/000/renders/schematic/distant_value_rc.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/rc_visual_gated/candidates/001/renders/schematic/distant_value_rc.svg)
  - round 0: move_field(reference=C1, field=Value, x_mm=95.0, y_mm=65.0) — applied → candidate 001
    - issue: The 'Value' field for component C1 is located at (150.0, 100.0), which is 77.369106 mm away from the component symbol. This exceeds the acceptable proximity limit and violates the field_locality check.
  - round 1: accepted

## schematic_review_loop_2026-10-25_run1 / rc_wiring_locked
- **Outcome:** ACCEPTED_FOR_REVIEW — accepted `candidates/001/project/DevstralV4RcLowpass1kHz.kicad_sch`
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/rc_wiring_locked/candidates/000/renders/schematic/corrupted_rc.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/rc_wiring_locked/candidates/001/renders/schematic/DevstralV4RcLowpass1kHz.svg)
  - round 0: regenerate_schematic() — applied → candidate 001
    - issue: ERC returned 4 violations (Pin not connected, Unconnected wire endpoint)
    - issue: real KiCad connectivity differs from intended circuit
  - round 1: accepted

## schematic_review_loop_2026-10-25_run1 / timer_generated
- **Outcome:** NO_PROGRESS — candidate repeats an earlier revision
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/timer_generated/candidates/000/renders/schematic/Reference555LedFlasher.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/timer_generated/candidates/001/renders/schematic/Reference555LedFlasher.svg)
  - round 0: regenerate_schematic() — applied → candidate 001
    - issue: ERC returned 3 violations

## schematic_review_qualification_2026-10-25_run1 / distant_value_rc
- **Outcome:** LIMIT_REACHED — wall-clock or model-token budget exhausted
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/distant_value_rc/candidates/000/renders/schematic/distant_value_rc.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/distant_value_rc/candidates/001/renders/schematic/distant_value_rc.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/distant_value_rc/candidates/002/renders/schematic/distant_value_rc.svg)
  - round 0: move_field(reference=C1, field=Value, x_mm=89.0, y_mm=62.0) — applied → candidate 001
    - issue: Field 'C1 Value' is too distant from its symbol (77.37 mm > 25.4 mm limit).
  - round 1: move_field(reference=C1, field=Value, x_mm=89.5, y_mm=62.0) — applied → candidate 002
    - issue: Field collision detected: C1 Reference and Value fields overlap (x=88.9/89.0, y=62.23/62.0).
  - round 2: move_field(reference=C1:1.Value, field=Value, x_mm=94.5, y_mm=62.0) — not applied
    - issue: Field collision detected between C1 Reference and Value labels at coordinates (88.9, 62.23) and (89.5, 62.0).

## schematic_review_qualification_2026-10-25_run1 / rails_gate_v2_recovery
- **Outcome:** NO_PROGRESS — candidate repeats an earlier revision
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/rails_gate_v2_recovery/candidates/000/renders/schematic/timer_label_join_candidate.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/rails_gate_v2_recovery/candidates/001/renders/schematic/Reference555LedFlasher.svg)
  - round 0: regenerate_schematic() — applied → candidate 001
    - issue: visible_rail_continuity: FAIL - Power nets (VCC, REF) lack continuous visible wire paths between terminals; rely on labels only.
    - issue: label_association: PASS - All component references and values are legible and associated with their symbols.

## schematic_review_qualification_2026-10-25_run1 / rails_wire_edit_probe
- **Outcome:** NO_PROGRESS — candidate repeats an earlier revision
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/rails_wire_edit_probe/candidates/000/renders/schematic/timer_label_join_candidate.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/rails_wire_edit_probe/candidates/001/renders/schematic/Reference555LedFlasher.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/rails_wire_edit_probe/candidates/002/renders/schematic/Reference555LedFlasher.svg)
  - round 0: regenerate_schematic(); translate_sheet(dx_mm=0.0, dy_mm=0.0) — applied → candidate 001
    - issue: visible_rail_continuity: FAIL - No continuous visible wire paths exist between terminals for nets 'REF' and 'VCC'. The schematic relies on implicit net connections rather than explicit wiring, which violates the visual r
    - issue: label_association: PASS - All component references and values are legible and associated with their symbols.
  - round 1: regenerate_schematic(); translate_sheet(dx_mm=0.0, dy_mm=0.0) — applied → candidate 002
    - issue: visible_rail_continuity: FAIL - No continuous visible wire paths exist between terminals for nets 'REF' and 'VCC'. The schematic relies on implicit net connections rather than explicit wiring, which violates the visual r
    - issue: label_association: PASS - All component references and values are legible and associated with their symbols.

## schematic_review_qualification_2026-10-25_run1 / rails_wire_edit_probe_v4
- **Outcome:** NO_PROGRESS — model repeated an invalid review: add_wire_path endpoint (104.14, 49.69) is not a terminal on net VCC; valid terminals are []
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/rails_wire_edit_probe_v4/candidates/000/renders/schematic/timer_label_join_candidate.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/rails_wire_edit_probe_v4/candidates/001/renders/schematic/timer_label_join_candidate.svg)
  - round 0: add_wire_path(net=REF); add_wire_path(net=VCC) — applied → candidate 001
    - issue: visible_rail_continuity: FAIL - No continuous visible wire paths exist between terminals of the same net (VCC and REF). The schematic relies on implicit connections or label-only joins which violates the visual rubric fo
    - issue: label_association: PASS - All component references and values are legible and associated with their symbols within acceptable distances.
  - round 1: add_wire_path(net=VCC); add_wire_path(net=REF); move_field(reference=REF, field=Reference, x_mm=71.12, y_mm=38.1) — rejected: add_wire_path endpoint (104.14, 49.69) is not a terminal on net VCC; valid terminals are []
    - issue: visible_rail_continuity: The VCC net is visually fragmented; the wire from U1 pin 8 to R3 and J1 does not form a continuous trunk with the branch to R1/C2. The wire from U1 pin 4 to R1/C2 also lacks a clear shared rail s
    - issue: visible_rail_continuity: The REF net has ambiguous routing near C1 and J1; the connection between C1, J1, and U1 pins 1/5 appears disjointed in the visual representation.
  - round 2: regenerate_schematic(); add_wire_path(net=VCC) — rejected: add_wire_path endpoint (104.14, 49.69) is not a terminal on net VCC; valid terminals are []
    - issue: visible_rail_continuity: The VCC net is not visually continuous; the wire from U1 pin 8 to J1 and R3 appears broken or misrouted relative to the intended circuit partition.
    - issue: electrical_equivalence: ERC violations indicate that pins of type Power output are connected, which contradicts the intended circuit where VCC should connect specific terminals without shorting distinct power outputs.

## schematic_review_qualification_2026-10-25_run1 / rails_wire_edit_probe_v5
- **Outcome:** LIMIT_REACHED — review budget exhausted before edit and re-review
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/rails_wire_edit_probe_v5/candidates/000/renders/schematic/timer_label_join_candidate.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/rails_wire_edit_probe_v5/candidates/002/renders/schematic/timer_label_join_candidate.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/rails_wire_edit_probe_v5/candidates/003/renders/schematic/timer_label_join_candidate.svg)
  - round 0: add_wire_path(net=REF); add_wire_path(net=VCC); add_wire_path(net=VCC) — rejected: add_wire_path endpoint (54.61, 92.71) is not a terminal on net REF; valid terminals are [(54.61, 85.09), (71.12, 45.72), (74.93, 92.71), (88.9, 69.85)]
    - issue: visible_rail_continuity: FAIL - No continuous visible wire paths exist between terminals on the same net (VCC and REF nets are fragmented).
  - round 1: add_wire_path(net=VCC); add_wire_path(net=REF) — applied → candidate 002
    - issue: visible_rail_continuity: FAIL - No continuous visible wire path exists between terminals on the same net (VCC and REF). The schematic relies on implicit connections or label-only joins which violates the visual rubric fo
    - issue: label_association: PASS - All component references and values are legible and associated with their symbols within acceptable distance limits.
  - round 2: add_wire_path(net=VCC); add_wire_path(net=REF) — applied → candidate 003
    - issue: visible_rail_continuity: The VCC net is visually split into two distinct horizontal rails (one for the LED branch, one for the 555 supply) that do not connect to a single continuous trunk. This violates the visible rail 
    - issue: electrical_equivalence: The ERC report indicates 'Both REF and VCC are attached to the same items; REF will be used in the netlist'. While this is an electrical warning, the visual layout fails the presentation brief bec
  - round 3: add_wire_path(net=VCC); add_wire_path(net=REF); move_field(reference=C2, field=Reference, x_mm=81.28, y_mm=39.37); move_field(reference=R2, field=Reference, x_mm=64.77, y_mm=57.15) — not applied
    - issue: visible_rail_continuity: The VCC net has a visible gap between the top-left 'VCC' label and the main horizontal rail; the wire path is not explicitly continuous in the image.
    - issue: visible_rail_continuity: The REF net shows ambiguous junctions where multiple wires meet without clear orthogonal elbow points, violating the explicit rail continuity requirement.

## schematic_review_qualification_2026-10-25_run1 / rails_wire_edit_probe_v8
- **Outcome:** NO_PROGRESS — model repeated an invalid review: wire route has a zero-length segment
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/rails_wire_edit_probe_v8/candidates/000/renders/schematic/timer_label_join_candidate.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/rails_wire_edit_probe_v8/candidates/001/renders/schematic/timer_label_join_candidate.svg)
  - round 0: add_wire_path(net=REF, from_ref=C2, to_ref=J3) — applied → candidate 001
    - issue: visible_rail_continuity: FAIL - No continuous visible wire path exists between terminals on the same net (VCC and REF nets are fragmented).
  - round 1: add_wire_path(net=CONT, from_ref=U1, to_ref=C2) — rejected: add_wire_path is limited to nets with an explicit power assertion
    - issue: visible_rail_continuity: The wire connecting U1 pin 5 (CONT) to C2 pin 1 is not explicitly drawn as a continuous rail; it relies on label association which fails the visual rubric.
    - issue: visible_rail_continuity: The wire connecting U1 pin 1 (REF) to J3 and C2 pin 2 is fragmented or obscured by layout, failing the explicit conductor geometry check.
  - round 2: add_wire_path(net=VCC, from_ref=U1, to_ref=R3) — rejected: wire route has a zero-length segment
    - issue: visible_rail_continuity: The VCC net has a visible gap between the U1 pin 4 terminal and the main horizontal wire trunk; the connection relies on a label-only join which fails the visual rubric.
    - issue: observed_layout: Unrelated wires cross visually near the center of the schematic, creating potential confusion for signal flow tracing.
  - round 3: add_wire_path(net=REF, from_ref=J3, to_ref=U1) — rejected: wire route has a zero-length segment
    - issue: visible_rail_continuity: The wire connecting the 'REF' net to J3 (Return) and U1 pin 1 appears to have a visual gap or is not explicitly drawn as a continuous rail segment in the provided images, relying on label associa
    - issue: observed_layout: There is an observed unrelated wire crossing near the center of the schematic where the wire from R2/C1 junction crosses the wire connecting U1 pin 6 to U1 pin 2 without a clear dot indicating a junction

## schematic_review_qualification_2026-10-25_run1 / rails_wire_edit_probe_v9
- **Outcome:** NO_PROGRESS — model repeated an invalid review: add_wire_path is limited to explicitly asserted power nets; valid nets are ['REF', 'VCC']
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/rails_wire_edit_probe_v9/candidates/000/renders/schematic/timer_label_join_candidate.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/rails_wire_edit_probe_v9/candidates/001/renders/schematic/timer_label_join_candidate.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/rails_wire_edit_probe_v9/candidates/003/renders/schematic/timer_label_join_candidate.svg), [005](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/rails_wire_edit_probe_v9/candidates/005/renders/schematic/timer_label_join_candidate.svg)
  - round 0: add_wire_path(net=REF, from_ref=C2, to_ref=J3) — applied → candidate 001
    - issue: visible_rail_continuity: FAIL - No continuous visible wire path exists between terminals on the same net (VCC and REF nets are fragmented).
  - round 1: add_wire_path(net=CONT, from_ref=U1, to_ref=C2) — rejected: add_wire_path is limited to explicitly asserted power nets; valid nets are ['REF', 'VCC']
    - issue: visible_rail_continuity: The wire from U1 pin 5 (CONT) to C2 pin 1 is not explicitly drawn as a continuous rail; it relies on label association which fails the visual rubric.
    - issue: visible_rail_continuity: The wire from U1 pin 1 (REF) to J3 and C2 pin 2 is fragmented or obscured by layout, failing the explicit conductor geometry check.
  - round 2: add_wire_path(net=VCC, from_ref=U1, to_ref=R3) — applied → candidate 003
    - issue: visible_rail_continuity: The VCC net has a visible gap between the U1 pin 8 terminal and the main horizontal wire trunk, creating an ambiguous connection that violates the visual rubric for explicit rail continuity.
    - issue: observed_layout: Unrelated wires cross visually without clear junction indication in the upper-left quadrant, reducing readability.
  - round 3: add_wire_path(net=VCC, from_ref=U1, to_ref=R1) — rejected: wire route repeats waypoint (91.44, 49.53); omit points matching either named terminal
    - issue: visible_rail_continuity: FAIL - The VCC net has multiple disconnected wire segments and apparent gaps between terminals (e.g., U1 pin 8 to R1, U1 pin 4 to J1), failing the visual continuity requirement.
    - issue: native_tools: FAIL - ERC returned 6 violations related to endpoints off the connection grid, indicating poor wiring geometry.
  - round 4: add_wire_path(net=VCC, from_ref=U1, to_ref=U1) — applied → candidate 005
    - issue: visible_rail_continuity: FAIL - The VCC net has multiple disconnected wire segments and apparent gaps near U1 pins 4, 8, and the power rail trunk. ERC warnings confirm endpoints are off-grid.
    - issue: observed_layout: FAIL - Wire geometry is fragmented; explicit continuous rails are not visible for the VCC net despite electrical equivalence passing.
  - round 5: add_wire_path(net=VCC, from_ref=U1, to_ref=J1) — rejected: wire route repeats waypoint (78.74, 54.61); omit points matching either named terminal
    - issue: visible_rail_continuity: FAIL - The VCC net has multiple disconnected wire segments and apparent gaps near U1 pins 4, 8, and the power supply terminal J1. The visual continuity of the main power rail is broken.
    - issue: native_tools: FAIL - ERC returned 6 violations related to 'Symbol pin or wire end off connection grid', indicating misaligned endpoints that break explicit electrical connections.
  - round 6: add_wire_path(net=TIMING, from_ref=R2, to_ref=U1) — rejected: add_wire_path is limited to explicitly asserted power nets; valid nets are ['REF', 'VCC']
    - issue: visible_rail_continuity: FAIL - Wire geometry between terminals is ambiguous or non-continuous in the visual representation, failing the independent gate check.
    - issue: observed_layout: FAIL - ERC warnings indicate endpoints are off-grid, suggesting poor wire routing that affects visual continuity and readability.

## schematic_review_qualification_2026-10-25_run1 / review_with_owner_gate_v2_feedback
- **Outcome:** LIMIT_REACHED — wall-clock or model-token budget exhausted
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/review_with_owner_gate_v2_feedback/candidates/000/renders/schematic/wrong_association_rc_v2.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/review_with_owner_gate_v2_feedback/candidates/002/renders/schematic/wrong_association_rc_v2.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/review_with_owner_gate_v2_feedback/candidates/003/renders/schematic/wrong_association_rc_v2.svg)
  - round 0: move_field(reference=C1, field=Value, x_mm=99.0, y_mm=47.5) — rejected: move_field for C1.Value made no change; choose a different position
    - issue: C1 Value field is visually closer to J2 than its own symbol, violating owner-association heuristic
  - round 1: move_field(reference=C1, field=Value, x_mm=88.9, y_mm=62.23) — applied → candidate 002
    - issue: C1.Value field is visually closer to J2 than to C1, violating owner-association heuristic
  - round 2: move_field(reference=C1, field=Value, x_mm=95.0, y_mm=62.23) — applied → candidate 003
    - issue: Field overlap: C1 Reference and Value fields are overlapping (field_separation check failed).
  - round 3: accepted

## schematic_review_qualification_2026-10-25_run1 / review_with_owner_gate_v2_recovered
- **Outcome:** ACCEPTED_FOR_REVIEW — accepted `candidates/002/project/wrong_association_rc_v2.kicad_sch`
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/review_with_owner_gate_v2_recovered/candidates/000/renders/schematic/wrong_association_rc_v2.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/review_with_owner_gate_v2_recovered/candidates/002/renders/schematic/wrong_association_rc_v2.svg)
  - round 0: move_field(reference=C1, field=Value, x_mm=99.0, y_mm=47.5) — rejected: move_field for C1.Value made no change; choose a different position
    - issue: C1 Value field is visually closer to J2 than its own symbol, violating owner-association heuristic
  - round 1: move_field(reference=C1, field=Value, x_mm=88.9, y_mm=47.5) — applied → candidate 002
    - issue: C1.Value field is visually closer to J2 than to C1, violating the owner-association heuristic
  - round 2: accepted

## schematic_review_qualification_2026-10-25_run1 / review_with_owner_gate_v2_recovery
- **Outcome:** NO_PROGRESS — candidate repeats an earlier revision
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/review_with_owner_gate_v2_recovery/candidates/000/renders/schematic/wrong_association_rc_v2.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/review_with_owner_gate_v2_recovery/candidates/001/renders/schematic/wrong_association_rc_v2.svg)
  - round 0: move_field(reference=C1, field=Value, x_mm=99.0, y_mm=47.5) — applied → candidate 001
    - issue: C1 Value field is visually closer to J2 than its own symbol, violating owner-association heuristic

## schematic_review_qualification_2026-10-25_run1 / timer_labeled_rails
- **Outcome:** LIMIT_REACHED — wall-clock or model-token budget exhausted
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/timer_labeled_rails/candidates/000/renders/schematic/Reference555LedFlasher.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/schematic_review_qualification_2026-10-25_run1/timer_labeled_rails/candidates/001/renders/schematic/Reference555LedFlasher.svg)
  - round 0: regenerate_schematic() — applied → candidate 001
    - issue: observed unrelated wire crossing
  - round 1: accepted

## rails_obstacle_route_2026-10-25_run1 / (single case)
- **Outcome:** LIMIT_REACHED — wall-clock or model-token budget exhausted
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/rails_obstacle_route_2026-10-25_run1/candidates/000/renders/schematic/timer_label_join_candidate.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/rails_obstacle_route_2026-10-25_run1/candidates/001/renders/schematic/timer_label_join_candidate.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/rails_obstacle_route_2026-10-25_run1/candidates/002/renders/schematic/timer_label_join_candidate.svg)
  - round 0: add_wire_path(net=REF, from_ref=C2, to_ref=J3) — applied → candidate 001
    - issue: visible_rail_continuity: FAIL - No continuous visible wire path exists between terminals on the same net (REF and VCC). The schematic relies on implicit connections or label-only joins which violates the visual rubric fo
    - issue: label_association: PASS - All component references and values are legible and associated with their symbols within acceptable distances.
  - round 1: add_wire_path(net=VCC, from_ref=R1, to_ref=U1) — applied → candidate 002
    - issue: visible_rail_continuity: FAIL - No continuous visible wire path exists between terminals on the same net (VCC and REF nets are fragmented into label-only connections).
  - round 2: add_wire_path(net=VCC, from_ref=R1, to_ref=U1) — not applied
    - issue: visible_rail_continuity: The schematic lacks explicit wire paths connecting terminals on the same net (VCC and REF). The machine checks report 'no continuous native wire path' for multiple VCC and REF connections, indica
    - issue: visible_local_rails: Power nets (VCC, REF) rely on label-only joins or apparent gaps instead of continuous visible wires from relevant terminals to a shared rail. The diagnostics list specific terminal pairs (e.g., R1-1 

## rails_obstacle_route_resume_2026-10-25_run1 / (single case)
- **Outcome:** LIMIT_REACHED — wall-clock or model-token budget exhausted
- **Drawings:** [000](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/rails_obstacle_route_resume_2026-10-25_run1/candidates/000/renders/schematic/timer_label_join_candidate.svg), [001](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/rails_obstacle_route_resume_2026-10-25_run1/candidates/001/renders/schematic/timer_label_join_candidate.svg), [002](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/rails_obstacle_route_resume_2026-10-25_run1/candidates/002/renders/schematic/timer_label_join_candidate.svg), [003](https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/rails_obstacle_route_resume_2026-10-25_run1/candidates/003/renders/schematic/timer_label_join_candidate.svg)
  - round 0: add_wire_path(net=VCC, from_ref=R1, to_ref=R3) — applied → candidate 001
    - issue: visible_rail_continuity: The schematic lacks explicit wire paths connecting terminals on the same net (VCC and REF). The current layout relies on implicit connections or label-only joins, which fails the visual rubric fo
    - issue: action_plan_summary: Add explicit orthogonal wire paths to join all terminals on the same net (VCC and REF) into a single continuous visible rail. This will satisfy the visible_rail_continuity criterion while preserving 
  - round 1: add_wire_path(net=VCC, from_ref=R1, to_ref=J1) — applied → candidate 002
    - issue: visible_rail_continuity: The schematic lacks explicit wire paths connecting terminals on the same net (REF, VCC). The visual representation relies on implicit connections or label proximity rather than drawn wires, faili
  - round 2: add_wire_path(net=REF, from_ref=C2, to_ref=C1) — applied → candidate 003
    - issue: visible_rail_continuity: The 'REF' net lacks a continuous visible wire path between terminals C2 and C1. The 'VCC' net lacks a continuous visible wire path between terminals R1 and U1.
    - issue: action_required: Add explicit Manhattan wire segments to join the disconnected terminals for the 'REF' and 'VCC' nets.
  - round 3: add_wire_path(net=VCC, from_ref=J1, to_ref=R1) — rejected: add_wire_path duplicates existing wire geometry
    - issue: visible_rail_continuity: The VCC net has an excessive detour from J1 to R1, creating a visually cluttered and non-optimal routing path that violates the visible_local_rails rubric for clear signal flow.
    - issue: page_composition: The layout exhibits poor balance due to the long, winding wire segment connecting J1 (Supply) to R1, which disrupts the natural functional grouping of the power rail components.
  - round 4: add_wire_path(net=VCC, from_ref=J1, to_ref=U1) — rejected: wire route repeats waypoint (48.26, 92.71); omit points matching either named terminal
    - issue: visible_rail_continuity: The VCC net has an excessive detour from J1 to U1 pin 8, crossing the R1/C2 area unnecessarily. This violates the 'easy to follow' visual rubric for power rails.
    - issue: label_association: Field owner association is weak for C2 and R2; their labels are geometrically closer to neighboring components (U1, R1) than their own symbols in some metrics, though within limits. The layout feels cl
  - round 5: add_wire_path(net=VCC, from_ref=J1, to_ref=U1) — not applied
    - issue: visible_rail_continuity: The VCC net has an excessive detour from J1 to U1 pin 8, creating a visually cluttered and non-optimal routing path that violates the visible_local_rails rubric for clear signal flow.
    - issue: page_composition: The layout exhibits poor balance due to the long, winding wire segment connecting J1 (Supply) to U1, which disrupts the natural functional grouping of the power rail.

