# Reviewer qualification: text description, blind, reasoning off (2026-11-13)

Run of `tools/pivot/qualify_review_v3.py` at `8fbab156` with brief v9, `qwen35-256k:latest` (digest `b528609af3c0`), and these settings:
- `--description`: a plain-text description of the drawing instead of images, from `src/ai_kicad/pivot/schematic_description.py`
- reasoning off
- 2048-token output cap
- `--modes image_only`: check verdicts withheld; the prompt says so

The cases are the harness's 61: 15 "known-good" drawings from `review_loop_corpus_v3_2026-11-12_qwen35_256k_run1`, 14 historical defects found by the owner or an outside review, and 32 injected defects. `summary.json` has the scores and `findings.md` has every case with the reviewer's own words.

| group | cases | INVALID | rejected | accepted |
|---|---|---|---|---|
| historical | 14 | 3 | 11 | 0 |
| injected | 32 | 6 | 24 | 2 |
| known-good | 15 | 1 | 13 | 1 |

**Reading the results:**
- **The `names_defect` score (10 of 14 historical) overstates it.** Its cue patterns match generic words such as "U1C", "V+", "long" and "REF", which nearly every review contains.
- **Hand reading of the 14 historical cases:**
  - Most reviews lead with the same complaint about every drawing: rails "not visibly joined by a continuous wire trunk or … matching power symbol". That is mostly false; the drawings use matching power symbols.
  - Genuine hits are rare. The clearest is timer_astable: "VCC supply arrow at (97.79, 36.83) points down into the body of R1", which is the known defect, correctly located.
- **Known-good drawings:** these predate the v8/v9 layout rules, so some rejections are legitimate under brief v9, for example inverting_gain's U1C label 19.4 mm from its pins. Others are not.
- **INVALID:** all 10 hit the 2048-token output cap.
- **Overall:** the reviewer now rejects almost every drawing instead of accepting almost every one. It does not yet tell good drawings from bad.
