# Reviewer qualification baseline, brief v3 (2026-11-12)

`tools/pivot/qualify_review_v3.py` at `65bda258` ran this on a Linux host that is not the locked qualification host. It used KiCad 10.0.6 via `/tmp/AppDir/AppRun`, with all six locked file hashes matching. The model was `qwen35-256k:latest` with a 262144-token context, a 2048-token output cap, temperature 0 and seed 20261025, given brief v3 and the review loop's own system prompt.

**Question:** does the model review catch readability defects that the independent checks miss, without rejecting good drawings? This is P6-011b. It is a baseline: no reviewer change has been made yet.

**Cases:** 61 drawings, each re-assessed with today's checks. `summary.json` lists every case with its source, defect, check results and image hashes.
- **known_good (15):** the accepted drawings from `review_loop_corpus_v3_2026-11-12_qwen35_256k_run1`. Expected decision: accept.
- **historical (14):** drawings that the owner or an outside review found defective after the model had accepted them, or that an evidence folder produced. Each names the folder of the fix that followed. 9 of the 14 still pass every check today, so only the image review can catch them. The other 5 now fail `power_symbol_clearance`. The case where U1C's text sits beside its pins is left out, because the owner approved both positions.
- **injected (32):** detached value, overlapping fields, distant reference and off-balance page, each on 8 known-good drawings. 5 pass every check: led_series's detached value, and the off-balance pages of led_series, sallen_key, timer_astable and the 555.

**Modes:** `full` sends the normal assessment, as the loop does. `image_only` sends the check names but withholds their results and the diagnostics.

**Results, full mode:**

| group | cases | pass all checks | model rejects | loop would accept |
|---|---|---|---|---|
| known_good | 15 | 15 | 4 | 11 |
| historical | 14 | 9 | 6 | 8 |
| injected | 32 | 5 | 28 | 4 |

- **False rejections:** all 4 known-good rejections are op-amp drawings: dual_buffer, dual_rail_reference, inverting_gain and sallen_key. Each says the rails are not visibly connected or rely on text labels.
- **Cause of those rejections:** under brief v3 the report still carries the protected wire-only observer's `layout.observed_power_rail_wire_path_witnesses`. For a drawing with power symbols, that list says "no continuous native wire path between same-net terminals" for every rail, while `rail_presentation` passes with no witnesses. inverting_gain and sallen_key quote it directly. Seven full-mode replies cite those witnesses.
- **False acceptances reproduced:** of the 9 historical defects that pass every check, the model accepted 8. It rejected the ninth, `inverting_gain__long_ref_wire_and_loop`, only for the false rail claim. No full-mode rejection of a machine-silent defect names the defect. Accepted defects:
  - the ground wire across U1C's pin names (4 designs)
  - R1/R2 text by the wrong part
  - the sideways ground symbol
  - the long VPLUS/VMINUS loops
  - R1's VCC arrow pointing into "10k"
- **Machine-silent injected defects:** the model accepted 4 of 5. It rejected sallen_key's off-balance page, again only for the rail claim.
- **Caught by the checks:** every rejection of a defect a check catches repeats that check's failure. The image adds nothing there.

**Results, image_only mode:**
- **No discrimination:** the model rejects 13 of 15 known-good drawings. 1 reply was invalid, a `move_symbols` with zero offset; 6 were invalid across all groups.
- **Recurring false claims:**
  - U1A/U1B/U1C are three separate components rather than units of one NE5532
  - a rail terminal is disconnected or "relies on text labels"
  - an all-wire rail lacks a power symbol
- **Cue matches are noise:** `names_defect` matches 6 of the 9 machine-silent historical defects, but on reading the issues none of them names the actual defect. The U1C cue matches the multi-unit complaint, and the timer_astable match claims VCC is disconnected at pin 4.

**Conclusions:**
1. With machine results, the reviewer adds no detection beyond the checks on this set. It accepted 8 of 9 historical and 4 of 5 injected defects that the checks miss.
2. Its known-good false rejections come mainly from the stale wire-only witnesses in the report, which is a pivot-side defect that can be fixed.
3. Without machine results, the model does not tell good drawings from bad, matching the brief-v2 finding of 2026-10-26.

P6-011b stays open. Next: drop or relabel the wire-only witnesses under brief v3, rerun this case set, then decide how readability defects like these 9 can be measured.
