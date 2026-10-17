# I6 `text_long_branch_2` native-render inspection

- Qualified behavior source: `ee4c37a711b1107085acaed5e58bf3e7ae78bd50`
- Qualification: accepted and reproducible ×5 in I6 group of Final Interactions run `39014637051`.
- Renderer: locked KiCad 10.0.6 native SVG.
- Reviewer: Codex engineering inspection; not user approval.
- SVG: `interactions/i6/text_long_branch_2/run1/renders/schematic/M2h2I6TextLongBranch2.svg`
- SHA-256: `805a24fb9895a742f4d852a33be9acc3842bf834959b3043d61175c1fe4bc1e3`

The long resistor value and connector text remain visible in a simple left-to-right two-resistor path. The secondary output branches from the first stage and the primary output sits on the right; the common-return branch is drawn below the signal row. The long value stays readable without overlapping wires or neighboring labels. The circuit occupies a modest horizontal strip of the A4 page, appropriate for review against its complexity band.

Independent observed values: 140.97 × 64.77 mm content envelope, 22.3721% page utilization, 24.13 mm motif fragmentation, 370.84 mm wire length, seven observed bends, 4.23 mm observed text/wire clearance, zero wire-through-text events, unrelated-wire crossings, or body overlaps.

This single native render does not establish long-field targeted acceptance, complete I6 visual inspection, the 90-case comparative gates, or final M2h2 completion.
