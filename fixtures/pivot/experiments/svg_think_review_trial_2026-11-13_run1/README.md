# Reviewer trial: SVG source as text, reasoning on (2026-11-13)

One design, inverting_gain, under brief v9, reviewed by `qwen35-256k:latest` (digest `b528609af3c0`) with the new reviewer options:
- `svg_source=True`: the plotted SVG's source is sent as text (`schematic_svg` in the handoff) instead of PNG images.
- `think=True`: reasoning on, with a 16384-token output cap and a 262144-token context.

It ran from the working tree committed with this README, through `NativeSchematicReviewService` directly, with output in a scratch folder copied here. This is not a corpus run.

**Why:** in every corpus run the reviewer accepted on first review and no edit it requested ever reached an accepted drawing. Its reasoning was switched off (`think: false`, 2048-token cap), and it saw 1600×1200 PNGs. The owner asked for reasoning on and for the model to read the SVG as text.

**Result:** `ACCEPTED_FOR_REVIEW` on the first review, with no issues and no actions. The review took 92 s, with 101,395 prompt tokens (mostly the SVG) and 4,315 output tokens. The full reasoning is in `reviews/000.json` (`response.message.thinking`). It shows:
- **It could not find the power symbols.** It repeated "I don't see explicit ground/arrow glyphs in the SVG path data". KiCad's SVG draws them as unlabelled `<path>` coordinates.
- **It deferred to the checks when unsure.** For example: "the rail_presentation check passed… I should trust it unless visual inspection contradicts it".
- **It misread the layout.** It took C1 and C2 for U1A/U1B parts rather than U1C's decoupling, and said the flags' "#FLG" names are visible text.
- **It raised no readability point** of the kind the owner and an outside review found.

**Conclusion:** text input makes labels and their positions readable, but raw SVG geometry does not tell this model what is drawn. With the check verdicts in front of it, it accepts. The next steps are a structured description of the drawing, withholding the check verdicts until after its review, and scoring it on the qualification cases.
