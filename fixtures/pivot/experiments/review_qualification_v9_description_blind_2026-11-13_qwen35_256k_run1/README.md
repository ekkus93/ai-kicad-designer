# Reviewer qualification, stopped early: text description, blind, reasoning on (2026-11-13)

Run of `tools/pivot/qualify_review_v3.py` at `8fbab156` with brief v9, `qwen35-256k:latest` (digest `b528609af3c0`), and these settings:
- `--description`: a plain-text description of the drawing instead of images
- `--think`: reasoning on
- 16384-token output cap
- `--modes image_only`: check verdicts withheld; the prompt says so

**Stopped by the owner after 23 of the 61 cases** (15 known-good, 8 historical) because most reviews produced no answer. The harness writes `summary.json` only at the end, so there is none. `findings.md` lists every reviewed case from the saved review records; case groups and known defects come from the completed sibling run `review_qualification_v9_description_blind_nothink_2026-11-13_qwen35_256k_run1`.

**Result:** 14 of 23 reviews are INVALID. The reasoning repeated the same few lines, for example "If I move it to x=86.36? That's +17.66mm", until it hit the 16,384-token output cap, so no answer came back. Of the nine that answered: 6 accepts, 2 revises and 1 needs_help.

Reasoning on with this model is not usable: it loops, and each review takes about 3 minutes.
