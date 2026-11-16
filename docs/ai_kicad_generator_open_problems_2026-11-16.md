# Generator layout: open problems (2026-11-16)

**Branch:** `mcp`. **Brief:** v11, the generator layout steps of spec R7 (`docs/pivot/REVIEWER_LOOP_SPEC.md`).
**Task:** P6-011p, "supply and return blocks" (`docs/MCP_ARCHITECTURE_TODO.md`).
**Latest corpus run:** `fixtures/pivot/experiments/supply_blocks_v11_2026-11-16_run3` at commit `60a741d5`. All 15 corpus designs pass every independent check (KiCad ERC, netlist equivalence, observed layout, the brief's readability checks). The pivot test suite passes: 613 passed, 1 deselected.

This document describes what is still wrong, what was tried, and the options. It asks the reader to decide how to proceed.

## How the generator works (briefly)

1. **Compile:** a protected compiler (the M2 composer, which must not be changed) produces a native KiCad schematic from the intended circuit (parts and nets).
2. **Pivot-side steps:** under brief v11, steps then adjust the layout, in this order:
   1. connector orientation and flow (R7.1)
   2. label cleanup
   3. rail planner: rails are drawn with local power symbols
   4. power flags
   5. block moves (R7.2): the LED branch beside its driving pin, a second connector pass, parked op-amp units beside their active sibling, and the return connector beside the supply connector
   6. supply blocks (R7.4): bypass and decoupling capacitors beside their pins, and power-symbol re-aiming
   7. field text placement
   8. page centring
3. **Validation:** every step change is validated before it is kept:
   - the protected layout observer
   - pure-geometry field checks
   - a full scratch assessment with KiCad ERC and netlist equivalence; no check that passed before may fail
4. **Finished-drawing check:** the finished drawing is assessed in full again. If anything fails, the blamed move is excluded and the drawing is regenerated.
5. **No hand-tuning:** none of this uses design-specific coordinates or per-design rules.

## The 555 LED flasher today

- **Drawing:** https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/supply_blocks_v11_2026-11-16_run3/reference_555_led_flasher_v8/review-images/drawing.png
- **Full page:** https://github.com/ekkus93/ai-kicad-designer/blob/mcp/fixtures/pivot/experiments/supply_blocks_v11_2026-11-16_run3/reference_555_led_flasher_v8/review-images/page.png

ChatGPT's latest review (2026-11-16) rated it about 8.3/10:
- Wiring is 53 % shorter and bends 56 % fewer than the 14 November baseline, with connectivity unchanged.
- The remaining points were C2's orientation, J1 and J3 not grouped, duplicate VCC symbols, a complicated REF connection near J3, an active-low LED (now reported as a design-review flag), and the missing 100 nF supply decoupling (already reported as a flag, not added).

## Open problem 1: C2's wire runs alongside pin 8's VCC arrow

**What it looks like:**
- C2 (10 nF, the control-pin bypass) stands 6.35 mm straight above CONT (pin 5) on a direct vertical wire.
- C2 is turned so its CONT pin faces down onto pin 5. Its REF symbol therefore sits on a 5.08 mm stub to the left of C2's top pin.
- On the NE555D symbol, pins 5 and 8 are 2.54 mm apart on the top edge, and pin 8 has a VCC arrow pointing up from it.
- C2's wire therefore runs parallel to pin 8 and its VCC arrow at 2.54 mm for several millimetres, which is the review's "harder to distinguish visually".

**What was tried:**
1. Ranking every valid spot near pin 5, preferring:
   1. at least 5.08 mm from other nets' pins, symbols and wires
   2. then no stub on the return symbol
   3. then nearness
2. The candidate spots included ones up to four grid steps to either side.
3. Result: no change, and 555 compile time rose from about 75–150 s to 300–410 s. The change was reverted.

**Why it failed:**
- A minimum-clearance rule cannot be met, because any wire leaving pin 5 starts 2.54 mm from pin 8.
- The real objection is a long parallel run beside another net. That needs a rule on the length of side-by-side runs at a small gap, not a minimum gap. It also needs routes that leave pin 5 and turn away from pin 8 quickly, which the current straight-out spots do not produce.

**Options:**
- **A.** Measure "side-by-side length within one grid step of another net" and prefer spots that keep it short. For example, C2 up and to the left of pin 5, with the wire turning left after one grid step.
- **B.** Accept the current placement. It is direct, short and conventional enough, and every check passes.

## Open problem 2: J3 (Return) is not grouped with J1 (Supply) on the flasher

**What it looks like:** J1 is at the top left, beside R1's VCC symbol. J3 is at the bottom, below C1. ChatGPT asked for them as one power-entry interface.

**Background:**
- A return connector is moved, as a unit with its power symbols, flags and private wires, to sit beside the supply connector.
- This already works on the regulator and on both timer_astable variants. There, J3's wiring is private (only its own REF symbol and power flag).

**What was tried on the flasher:**
1. **First failure:** every candidate position under J1 was refused because J1's text then read as J3's. Fix: the move may now re-place the neighbour's (J1's) text as well. This change is kept.
2. **Second failure:** with that fixed, every candidate breaks connectivity (ERC and netlist equivalence fail). On the flasher, J3's pin is joined by wire to C1's REF pin and a power flag, not only to a private REF symbol. Moving J3 means rerouting that shared REF wire, and the reroutes fail.

**Options:**
- **A.** When a return connector's wiring is shared with a part's return pin, cut the shared wire. Mark both pins (J3 and C1) with their own local REF symbols, then move J3. This is what the rail planner does elsewhere. It is a general change to how the block move treats rail nets.
- **B.** Accept J3 where it is. It is short-wired to C1 and correct, just not beside J1.

## Open problem 3: smaller items still open under P6-011p

- **Sideways VPLUS arrows:** in the op-amp power blocks of dual_buffer, noninverting_gain and sallen_key (B14). Turning them up collides with nearby items. Return symbols that were sideways were fixed with a short stub, but for VPLUS every tried stub also collided.
- **dual_rail_reference (B12):** its capacitors C1 and C2 run from VPLUS and VMINUS to the VREF midpoint, not to a return rail. The decoupling rule only recognises capacitors to a return, so it does not treat these as decoupling.
- **Not yet measured:** whether B01, B02 and B07 (rated good) are no worse than in the v10 baseline. Not hard, just not done.
- **Duplicate VCC symbols:** at J1 and R1 on the flasher. This belongs to the next task (P6-011q, drawing conventions, redundant-symbol cleanup), not P6-011p.

## Costs to keep in mind

- **Compile time:** each change is validated with a full KiCad scratch assessment (about 1–3 s each). The 555 flasher now takes about 150 s to compile under v11; the op-amp designs take 40–130 s. Approaches that search many candidates multiply this.
- **Protected code:** the protected compiler and observers cannot be changed. All layout work is in pivot-side steps after compilation.
- **Reproducibility:** briefs v1–v10 must keep their drawings byte-for-byte, so every change is behind brief v11.

## What needs deciding

For each item, accept as a known gap, or pursue with the option named:

1. **C2 alongside pin 8:** pursue option A (side-by-side-length rule), or accept?
2. **J3 on the flasher:** pursue option A (cut shared return wiring and mark both pins locally), or accept?
3. **Sideways VPLUS arrows, and dual_rail_reference's midpoint capacitors:** pursue, or accept?
4. **Next steps:** once P6-011p is settled, the plan is:
   1. P6-011q (drawing conventions, including the duplicate VCC symbols and jog cleanup)
   2. P6-011s (regenerate and re-rate the v11 baseline)
   3. P6-011u and P6-011v (offer the generator's moves as menu entries Qwen can choose)

   Is that the right order?
