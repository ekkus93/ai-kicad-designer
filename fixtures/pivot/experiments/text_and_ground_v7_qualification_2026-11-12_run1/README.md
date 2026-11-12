# Brief v7 gates on the reviewer qualification cases (2026-11-12)

`tools/pivot/qualify_review_v3.py --prepare-only` was run at `62d0bc5c`. It re-assessed the 61 cases of `review_qualification_v3_2026-11-12_qwen35_256k_run1` with `fixtures/pivot/schematic_review_brief_v7.json`. No model review was run. The host was Linux with KiCad 10.0.6 via `/tmp/AppDir/AppRun`, which is not the locked qualification host. The gates are described in `text_and_ground_v7_2026-11-12_run1`.

**Problem:** three defects were measured only indirectly up to brief v6:
- `inverting_gain__r1_r2_text_misplaced`: R2's "R2 10k" sits 8 mm above its resistor, beyond the wire to U1A's + input, and is not nearer any other part.
- `inverting_gain__sideways_ground`: C2's REF ground points sideways with room below.
- The accepted inverting_gain drawing: U1C's label sits 17–19 mm from its pin column, slightly nearer C2. Brief v6 exempted it.

**Results:**

| group | cases | fail `field_wire_separation` | fail `ground_symbol_direction` | fail `field_nearest_owner` |
|---|---|---|---|---|
| known_good | 15 | 0 | 0 | 1 |
| historical | 14 | 4 | 3 | 5 |
| injected | 32 | 4 | 0 | 22 |

- **R2's text:** `field_wire_separation` fails it, in `inverting_gain__r1_r2_text_misplaced` and in the older `inverting_gain__wire_across_power_unit`, which has the same text. Also caught: U1C's text beyond another net's wire in `inverting_gain__long_ref_wire_and_loop` and `rc_to_buffer__wire_across_power_unit`.
- **Sideways ground:** `ground_symbol_direction` fails C2's REF in `inverting_gain__sideways_ground`, both REF grounds in `inverting_gain__r1_r2_text_misplaced`, and the REF ground in `noninverting_gain__wire_across_power_unit`.
- **Accepted sideways grounds** pass: those on op-amp + inputs would point into their own pin, and those in both timer drawings collide when pointed down.
- **U1C's label:** `field_nearest_owner` now fails the accepted inverting_gain drawing, its off-balance copy, `inverting_gain__vminus_by_pin_name` and `rc_to_buffer__wire_across_power_unit`. That is the intended change: these cases re-assess drawings made before v7. The v7 compiler places U1C's label beside its pins, and the regenerated drawing passes (`text_and_ground_v7_2026-11-12_run1`).
- **Earlier checks:** no other earlier check result differs from `field_ownership_v6_2026-11-12_run1`.
- **Still passing:** every defect case fails at least one gate except the 4 injected off-balance pages, which fail only `page_balance`.

**Not measured:** a part's own wiring that loops between it and its text, as J1's pin-1 wire does over J1 in linear_regulator and sallen_key, and C2's top wire in dual_rail_reference. These pass by design, because the text still reads as that part's. The loops themselves are a wiring question.
