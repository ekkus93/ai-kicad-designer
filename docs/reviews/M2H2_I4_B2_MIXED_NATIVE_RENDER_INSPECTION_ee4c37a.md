# I4 `b2_mixed` native-render inspection

- Qualified behavior source: `ee4c37a711b1107085acaed5e58bf3e7ae78bd50`
- Qualification: accepted and reproducible ×5 in I4 group of Final Interactions run `39014637051`.
- Renderer: locked KiCad 10.0.6 native SVG.
- Reviewer: Codex engineering inspection; not user approval.
- SVG: `interactions/i4/b2_mixed/run1/renders/schematic/M2h2I4B2Mixed.svg`
- SHA-256: `9206b5505390fe4fd43f1c6f5963ca2d0de597e387d56aeda75656165687af35`

The input enters on the left and the resistor/capacitor signal path advances left-to-right. The branch for output 2 rises to a separate upper rail and output 1 remains on the primary row; both output connectors are on the right. The relationship between the branch and its source remains visible, with no label-only disconnection. The drawing is legible, but occupies only the upper-left part of the A4 sheet. Evaluate that low page use against the frozen complexity band and corpus comparison rather than treating this single case as acceptance.

Independent observed values: 137.16 × 64.77 mm content envelope, 21.7675% page utilization, 24.13 mm motif fragmentation, 364.49 mm wire length, seven observed bends; zero ERC violations, flow reversals, interface enclosures, missing output routes, unrelated-wire crossings, body overlaps, wires through bodies or text.

This single native render does not establish targeted-composition acceptance, full interaction visual acceptance, the 90-case comparative gates, or final M2h2 completion.
