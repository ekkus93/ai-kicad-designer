# Reviewer qualification: SVG text plus PNGs, blind, reasoning off (2026-11-13)

Run of `tools/pivot/qualify_review_v3.py` at `068ad16f` with brief v9, `qwen35-256k:latest` (digest `b528609af3c0`), and these settings (owner request):
- `--svg --with-images`: the plotted SVG's source as text, plus both PNG renders (the 1800×1272 full page and the 1600×1200 close-up)
- reasoning off
- 2048-token output cap
- `--modes image_only`: check verdicts withheld; the prompt says so

The 61 cases are the same as `review_qualification_v9_description_blind_nothink_2026-11-13_qwen35_256k_run1`. `summary.json` has the scores and `findings.md` has every case with the reviewer's own words.

| group | cases | INVALID | rejected | accepted |
|---|---|---|---|---|
| historical | 14 | 0 | 13 | 1 |
| injected | 32 | 3 | 26 | 3 |
| known-good | 15 | 0 | 13 | 2 |

**Compared with the description run:**
- **Fewer INVALID:** 3 against 10.
- **Similar rejection rates.**
- **More false rail claims on known-good drawings:** 6 against 0.
- **Fewer defect-cue matches on injected cases:** 3 against 14.

The same caveat applies: the cue matching overstates `names_defect`. By hand, most reviews again lead with rails "not correctly presented" when they are presented by matching power symbols, and real hits on the known defect are rare. The reviewer rejects good and defective drawings at about the same rate.
