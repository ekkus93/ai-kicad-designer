# Brief v6 field nearest-owner gate on the qualification cases (2026-11-12)

`tools/pivot/qualify_review_v3.py --prepare-only` was run at `3b22ea61`. It built and assessed the 61 cases of `review_qualification_v3_2026-11-12_qwen35_256k_run1` using `fixtures/pivot/schematic_review_brief_v6.json`. No model review was run. The host was Linux with KiCad 10.0.6 via `/tmp/AppDir/AppRun`. It is not the locked qualification host.

**Problem:** two text-association defects passed every check up to brief v5:
- the historical `inverting_gain__r1_r2_text_misplaced`, where R1's "R1 100k" sits under U1A, nearer the op-amp than its resistor; it was caught only because the same drawing also has long rails
- the injected `led_series__detached_value`, where D1's "LED" is moved next to R1

The existing `field_owner_association` measures distance to symbol *anchors* with a 5.08 mm margin, so it misses text that sits nearer another part's drawing.

**Change (owner request, 2026-11-12):** brief v6 is brief v5 plus `field_nearest_owner`, under label_association (`fields_nearer_another_part` in `readability_checks.py`).
- **Measure:** for each visible reference or value, the gap from its text box to its own placed unit's drawing (body and pin stubs), and to every other part's drawing. Other units of the same part count as other parts. Power symbols are not parts.
- **Fails when:** another part is nearer than the field's own unit, **and** the field is more than 5.08 mm from its own unit.
- **Why the minimum:** in the accepted inverting_gain and noninverting_gain drawings, "R1" is 3.72 mm from its resistor and 2.91 mm from U1A, and it reads as R1's. The defects measured 5.34–8.04 mm (R1) and 6.93 mm (D1 "LED").
- **Exempt:** units drawn without a body (U1C). Their label stays beside the pin column by owner decision. In accepted inverting_gain it sits 17–19 mm from the pins, slightly nearer C2.

**Results** (no earlier check result changed):

| group | cases | fail a v4 check | fail `field_nearest_owner` | caught only by `field_nearest_owner` |
|---|---|---|---|---|
| known_good | 15 | 0 | 0 | 0 |
| historical | 14 | 14 | 3 | 0 |
| injected | 32 | 27 | 21 | 1 (`led_series__detached_value`) |

- Historical failures: `inverting_gain__r1_r2_text_misplaced` (R1 reference and value). Also `inverting_gain__wire_across_power_unit` and `noninverting_gain__wire_across_power_unit`, older drawings with the same R1 text placement.
- All 8 injected detached values fail. So do all 8 injected overlapping fields, where the moved value lands by another part, and 5 of 8 distant references.
- The 15 drawings of `review_loop_corpus_v5_2026-11-12_qwen35_256k_run1`, which are centred, also pass `field_nearest_owner` (`tests/pivot/test_readability_checks.py`).
- `page_balance` fails on 14 of 15 known-good cases here. That is expected: the harness re-assesses the v3/v4 accepted drawings, which predate v5 centring, and centring runs only when the compiler generates the drawing. The 4 injected off-balance pages are therefore the only cases that fail nothing but `page_balance`.

**Not measured:** R2's "R2 10k" in the same historical drawing sits 8.04 mm above U1A's input wire. That is far from its resistor but not nearer any other part, so it passes; the gate does not measure distance to wires. C2's sideways ground in `inverting_gain__sideways_ground` is still caught only through that drawing's long rails.

`summary.json` lists each case's check results and image hashes.
