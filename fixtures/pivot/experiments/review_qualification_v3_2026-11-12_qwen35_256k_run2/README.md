# Reviewer qualification after removing wire-only witnesses (2026-11-12)

This uses the same harness, cases, model, options and seed as `review_qualification_v3_2026-11-12_qwen35_256k_run1`. It ran at `63ed2a3f`, which stops sending the protected observer's `layout.observed_power_rail_wire_path_witnesses` to the reviewer under brief v3. For every rail joined by power symbols, those witnesses said "no continuous native wire path", while `rail_presentation` passed. The run used a Linux host with KiCad 10.0.6 via `/tmp/AppDir/AppRun`, which is not the locked qualification host.

**Same inputs:** every case's check results and image hashes match run1. Only the report sent to the model changed.

**Results, full mode (run1 → run2):**

| group | cases | pass all checks | model rejects | false rail claim | loop would accept |
|---|---|---|---|---|---|
| known_good | 15 | 15 | 4 → 0 | 3 → 0 | 11 → 15 |
| historical | 14 | 9 | 6 → 5 | 2 → 1 | 8 → 9 |
| injected | 32 | 5 | 28 → 27 | 2 → 0 | 4 → 5 |

- **Good drawings:** all 15 are now accepted. The false rail claim no longer appears on any of them in full mode.
- **Historical defects:** the model now accepts all 9 that pass every check. Run1's only rejection among them, `inverting_gain__long_ref_wire_and_loop`, came from the false rail claim, not from the defect, and is gone.
- **Injected defects:** the model accepts all 5 that pass every check. Run1 rejected sallen_key's off-balance page only for the rail claim.
- **Checked defects:** every rejection is of a drawing a check fails, and it repeats that check.
- **One false rail claim remains**, on `reference_555_led_flasher_v8__vcc_arrow_at_ref_text`, which fails `power_symbol_clearance` anyway.

**Results, image_only mode:** identical to run1, as expected, because that mode never sent the layout section. 13 of 15 good drawings are rejected.

**Conclusion:** removing the contradictory witnesses fixed every full-mode false rejection on this set. It also shows that, with machine results available, the model review catches none of the readability defects the checks miss. Its decisions follow the checks. Catching those defects needs measured checks; brief v4 is planned for that.
