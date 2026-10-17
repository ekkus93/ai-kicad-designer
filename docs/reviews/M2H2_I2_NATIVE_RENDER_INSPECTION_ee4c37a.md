# I2 interaction native-render inspection

- Qualified behavior source: `ee4c37a711b1107085acaed5e58bf3e7ae78bd50`
- Exact-source I2 Qualification: run [39014637051](https://github.com/ekkus93/ai-kicad-designer/actions/runs/39014637051), 9/9 cases accepted and reproducible across five builds.
- Locked renderer: KiCad 10.0.6
- Reviewer: Codex engineering inspection; not user approval.
- Scope: two representative I2 renders (`external_2`, `internal_2`). This is a partial inspection and does not complete section 18.

## `external_2` — external-bias branch

Inspected `interactions/i2/external_2/run1/renders/schematic/M2h2I2External2.svg`, SHA-256 `d63ba04d60825e9c15d3505259a95d9d350ccd7f45f2810299f6d319d4d7e142`.

The signal enters at J1 from the left, traverses the resistor ladder, and reaches output connectors J3/J4 on the right. The two outputs remain distinguishable. C1/C2 are visible shunt branches, and the external-bias rail is drawn below them. The content is a shallow upper-page strip with broad unused page area; review page use against the frozen complexity-banded baseline. Independent observed values: 180.34 × 45.72 mm content envelope, 20.2025% page utilization, 24.13 mm motif fragmentation, 10 bends, 414.02 mm wire length, zero ERC violations, unrelated-wire crossings, symbol-body overlaps, wires through bodies or text.

## `internal_2` — internal/reference support

Inspected `interactions/i2/internal_2/run1/renders/schematic/M2h2I2Internal2.svg`, SHA-256 `56227b53c0ae9220d73d994dd98a68b2f09e1491a6679788b2e0335e0811b5ce`.

The input enters from the left, and two serial resistor/capacitor stages are traceable across the page. The VPLUS/VMINUS support branch is grouped on the right and the output connectors are on the right. The large upper loop and output2 branch are recognizable, though visual grouping between the two outputs is less direct than a straight channel layout. Page use is moderate but leaves broad unused sheet space. Independent observed values: 158.75 × 82.55 mm content envelope, 32.1098% page utilization, 24.13 mm motif fragmentation, 12 bends, 407.67 mm wire length, zero ERC violations, unrelated-wire crossings, body overlaps, wires through bodies or text.

## Review boundary

These two accepted I2 renders are visually traceable and have no observed electrical/ERC or geometry hard defects. Page use and output grouping remain under review. This partial I2 inspection does not establish complete interaction-family inspection, final native-render inventory, or comparative acceptance.
