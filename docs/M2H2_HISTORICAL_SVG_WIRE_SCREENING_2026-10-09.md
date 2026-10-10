# Historical native SVG wire-geometry screening (2026-10-09)

A local, hash-verified screening pass decoded all 90 historical native KiCad SVGs from the preserved ten-part archive (qualification SHA `42ab8452fca16592ead8f628b17980a9d34794b7`). It counted physical green-wire strokes after coalescing split, overlapping, reversed, and duplicate strokes; measured route ink length, bounding-box dimensions, bends, and visible endpoint-on-wire branches. These measurements exclude sheet frames, symbols, fields, and labels.

For `i4__b2_mixed` (SVG SHA-256 `9deab519039a207aa8de93508cc538c3c4c404ca9f6da3d17eab40a4d80f371e`), wire-ink bounds are 93.98 × 52.07 mm, total unique visible wire length 177.8 mm, five orthogonal bends, and three endpoint-on-wire branches. Its wire-only bounding-box area is 16.6447% of the 210 × 140 mm reference envelope. This is historical geometry evidence, **not** current-source qualification or a visual PASS.

The full analyzer and seven authored tests passed locally, but their repository commit was blocked by the GitHub-write tool safety gate. The source and report must be committed and qualified before any TODO checkbox can be reconciled from this work. Wire-only ranking cannot establish unrelated-net crossings, semantic owner detachment, or label-mediated disconnection; those require independent semantic observation and native engineering inspection.
