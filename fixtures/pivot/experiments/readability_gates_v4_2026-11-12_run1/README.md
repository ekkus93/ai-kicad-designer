# Brief v4 readability gates on the qualification cases (2026-11-12)

`tools/pivot/qualify_review_v3.py --prepare-only` at `65286870` built and assessed the 61 cases of `review_qualification_v3_2026-11-12_qwen35_256k_run1`, using `fixtures/pivot/schematic_review_brief_v4.json`. No model review was run. The host was Linux with KiCad 10.0.6 via `/tmp/AppDir/AppRun`, which is not the locked qualification host.

**Problem:** with machine results available, the model review accepted all 9 historical defects that pass every brief-v3 check (`review_qualification_v3_2026-11-12_qwen35_256k_run2`).

**Change (owner-approved, 2026-11-12):** brief v4 is brief v3 plus three independent gates (`src/ai_kicad/pivot/readability_checks.py`):

| gate | criterion | fails when |
|---|---|---|
| `bodyless_unit_clearance` | page_composition | a wire crosses, or runs along, the pin-name column of a unit drawn without a body (U1C) |
| `rail_route_detour` | visible_local_rails | a rail wire group is more than 1.15× the rectilinear spanning tree of the terminals and power symbols it joins, **and** more than 7.62 mm longer |
| `power_symbol_direction` | visible_local_rails | a supply arrow points down or a ground glyph points up; sideways is allowed |

- **Why a minimum detour:** a ratio alone does not separate good drawings from defects. Short stubs to a power symbol in accepted drawings reach 2.0–2.5×, but only 3.81 mm longer. Real defects measure 1.10–2.35× over 12.7–122 mm.
- **Why sideways is allowed:** VPLUS on pin 8 points sideways by owner decision, and 6 accepted grounds are sideways where there is no room below.

**Results** (every brief-v3 check result is unchanged):

| group | cases | fail a v3 check | fail a new v4 gate |
|---|---|---|---|
| known_good | 15 | 0 | 0 |
| historical | 14 | 5 | 11 |
| injected | 32 | 27 | 0 |

- **Historical defects:** all 9 that passed every v3 check now fail a v4 gate.
  - wire across U1C (4 designs): `bodyless_unit_clearance` and `rail_route_detour`
  - long VPLUS/VMINUS loops, and the long REF wire with the loop over U1C: `rail_route_detour`
  - R1's VCC arrow pointing down into "10k": `power_symbol_direction`
  - R1/R2 text by the wrong part, and C2's sideways ground: `rail_route_detour`, but only because those drawings also have long rails. Their own defects are not measured.
- **Injected defects:** the 5 that pass every check (four off-balance pages, and led_series's detached value) still pass. Page composition still has no owner-chosen measurable criterion.

`summary.json` lists each case's check results and image hashes. `tests/pivot/test_readability_checks.py` pins these outcomes on the retained case drawings.
