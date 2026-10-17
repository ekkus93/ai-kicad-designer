# I3 native-render inspections

- Qualified behavior source: `ee4c37a711b1107085acaed5e58bf3e7ae78bd50`
- Qualification: I3 **14/14 cases accepted and reproducible ×5**, final interaction run `39014637051`; locked runner and KiCad 10.0.6. The exact-source result file is `fixtures/m2h2/interaction_final_ee4c37a711b1107085acaed5e58bf3e7ae78bd50/i3/results.json`.
- Scope: Run 1 SVG inspected for each of the 14 I3 cases; this is engineering review evidence, not aesthetic acceptance.
- Case: `a0_interleaved`
- Run: 1 of 5; all five runs are accepted and reproducible in exact-source I3 progress evidence.
- Renderer: locked KiCad 10.0.6 native SVG.
- Reviewer: Codex engineering inspection; not user approval.
- SVG: `interactions/i3/a0_interleaved/run1/renders/schematic/M2h2I3A0Interleaved.svg`
- SHA-256: `94e8dcf5a592ae20f3996f89fc04a53f51e0907e72c463ceb4faa52a01d418ae`

The signal input enters at the left and the resistor chain advances left-to-right. Three shunt capacitors are visible as vertical branches. J3 and J4 outputs are placed below their respective branch rows; J5 carries the final path at the right. This makes the three output roles distinguishable, though the first two connectors sit below the page's main signal row and the content occupies only the upper-left portion of the sheet. Treat page use and connector association as concerns for the independent complexity-banded review. Independent observed values: 189.23 × 78.74 mm content envelope, 36.5083% page utilization, 24.13 mm motif fragmentation, six bends, 370.84 mm wire length, zero ERC violations, flow reversals, unrelated-wire crossings, body overlaps, wires through bodies or text.

## `a0_multiple`

Inspected `interactions/i3/a0_multiple/run1/renders/schematic/M2h2I3A0Multiple.svg`, SHA-256 `fa8123237bdf030ebfab78214a3435e8f01b5810e5efc08857470a72b1875294`. The three-resistor/capacitor chain reads left-to-right. J4 is on the final right-side output; J3 branches from an earlier node and is visibly routed below the row. The shared return uses a long lower wire, and the sheet remains mostly empty. Independent observed values: 143.51 × 66.04 mm content envelope, 23.2218% page utilization, 24.13 mm motif fragmentation, seven bends, 365.76 mm wire length; zero ERC violations, flow reversals, crossings, body overlaps, wires through bodies or text.

## `a0_one`

Inspected `interactions/i3/a0_one/run1/renders/schematic/M2h2I3A0One.svg`, SHA-256 `3aa2b288d8f83f17bb272b3cec53bda6df43a353eea27fc6c35f4858c51e6637`. The simple J1-to-R1-to-J3 signal path is clear, and C1 drops vertically to the return net; J2 is the common-return connector. The arrangement is legible but uses very little of the A4 page, which must be judged within its tiny complexity band. Independent observed values: 96.52 × 46.99 mm content envelope, 11.1130% page utilization, 24.13 mm motif fragmentation, five bends, 130.81 mm wire length; zero ERC violations, flow reversals, crossings, body overlaps, wires through bodies or text.

The three a0 render inspections do not establish complete I3 visual inspection, final native-render inventory, or comparative acceptance.

## `a1_multiple`

Inspected `interactions/i3/a1_multiple/run1/renders/schematic/M2h2I3A1Multiple.svg`, SHA-256 `fdf6cb9504929f00529cff6625060ece72778c9af08555eb0d29e4c1494a4f8d`. The 555 timer loop and three resistor/capacitor stages are recognizable, and the channel output is on the right. The circuit is clustered in the upper-left part of the A4 sheet, with most of the page unused; this is a material page-use concern for the case's complexity. Independent observed values: 165.10 × 72.39 mm, 29.2841% page utilization, 34.29 mm motif fragmentation, 472.44 mm wire length, 15 observed bends; zero ERC violations, flow reversals, crossings, body overlaps, wires through bodies or text.

## `a1_one`

Inspected `interactions/i3/a1_one/run1/renders/schematic/M2h2I3A1One.svg`, SHA-256 `436d1c81c9292ef5fbd4a6bc8fbc5ace481f4f7e054996230bf903830b15ef05`. The 555 timer, timing network, and right-side output read coherently; positive and negative supply connectors sit to the left of the circuit. The drawing occupies only the upper-left portion of the A4 sheet. Independent observed values: 121.92 × 69.85 mm, 20.8664% page utilization, 34.29 mm motif fragmentation, 241.30 mm wire length, eight observed bends; zero ERC violations, flow reversals, crossings, body overlaps, wires through bodies or text.

## `a2_interleaved`

Inspected `interactions/i3/a2_interleaved/run1/renders/schematic/M2h2I3A2Interleaved.svg`, SHA-256 `f671d6bdc7f70236d8498b5196de28fb4bc9dd7ee2d1e58c9881a5720b7cc378`. The two 555 channels form clear stacked rows, with their timing networks and output stages legible; supply and output interfaces sit on the right. The sheet is substantially better filled than the smaller I3 examples. Some outputs rely on matching net labels between the main circuit and right-side connectors, which should be assessed in the broader visual comparison. Independent observed values: 186.69 × 137.16 mm, 62.7415% page utilization, 29.21 mm motif fragmentation, 629.92 mm wire length, 21 observed bends; zero ERC violations, flow reversals, crossings, body overlaps, wires through bodies or text.

## `a2_multiple`

Inspected `interactions/i3/a2_multiple/run1/renders/schematic/M2h2I3A2Multiple.svg`, SHA-256 `e2cddd29110b54f95b758d46644ede7bb25f484945d4159a0b95a4878c6778e8`. The two timer channels are clearly separated into rows, with readable timing networks. The top channel has a visible rightward output path; the lower channel's output connector is separated from its producer by a net label, and much of the lower-right sheet remains unused. Independent observed values: 187.96 × 111.76 mm, 51.4705% page utilization, 29.21 mm motif fragmentation, 684.53 mm wire length, 23 observed bends; zero ERC violations, flow reversals, crossings, body overlaps, wires through bodies or text.

## `a2_one`

Inspected `interactions/i3/a2_one/run1/renders/schematic/M2h2I3A2One.svg`, SHA-256 `03567a036aa61dee7753837c6d3f45b668295f59c8447d3d4253c7f78ce86c2c`. The two timer channels are arranged side by side with consistent timing networks. Channel 2 exits directly to the right; channel 1 uses a long downward wire to its connector below the channels, so its output attribution is less immediate. The drawing uses more of the sheet than the smaller cases, though the bottom and right regions remain mostly empty. Independent observed values: 198.12 × 85.09 mm, 41.3060% page utilization, 34.29 mm motif fragmentation, 502.92 mm wire length, 16 observed bends; zero ERC violations, flow reversals, crossings, body overlaps, wires through bodies or text.

## `a3_interleaved`

Inspected `interactions/i3/a3_interleaved/run1/renders/schematic/M2h2I3A3Interleaved.svg`, SHA-256 `609e10672bc55e27225d4bdb35428650783e82c129cf88c4bb4ecd9b449e8e24`. All three 555 channel blocks and their local timing components are visible. The blocks occupy an asymmetric two-above/one-below arrangement; output connectors are grouped on the right, with channel association carried partly by labels. The arrangement is readable but less regular than a consistent three-channel grid. Independent observed values: 163.83 × 127.00 mm, 50.9805% page utilization, 29.21 mm motif fragmentation, 763.27 mm wire length, 32 observed bends; zero ERC violations, flow reversals, crossings, body overlaps, wires through bodies or text.

## `a3_multiple`

Inspected `interactions/i3/a3_multiple/run1/renders/schematic/M2h2I3A3Multiple.svg`, SHA-256 `d98c238decff4e2516bf999bd5fb2e27eb1f71a2900ffda03fe6a6e3121ce43a`. The three timer channels are electrically legible, but their placement is scattered as one upper-left channel and two lower channels with substantial whitespace between groups. The output connectors are split between the upper and right regions, and channel 2 uses a label-mediated connection. The repeated-channel visual grammar is uneven. Independent observed values: 175.26 × 137.16 mm, 58.9002% page utilization, 29.21 mm motif fragmentation, 665.48 mm wire length, 25 observed bends; zero ERC violations, flow reversals, crossings, body overlaps, wires through bodies or text.

## `a3_one`

Inspected `interactions/i3/a3_one/run1/renders/schematic/M2h2I3A3One.svg`, SHA-256 `88e0705b4d2ceba2e1bc6369608dac75b8a84e6bada644390d6f0c8c8c661472`. Two timer channels form a consistent upper row while the third occupies the lower-left region; each channel retains a recognizable local timing network. The three outputs are split across bottom and right-side interfaces, with one output routed downward. The overall composition remains asymmetric but is clear at this density. Independent observed values: 198.12 × 137.16 mm, 66.5829% page utilization, 29.21 mm motif fragmentation, 629.92 mm wire length, 22 observed bends; zero ERC violations, flow reversals, crossings, body overlaps, wires through bodies or text.

## `a1_interleaved`

Inspected `interactions/i3/a1_interleaved/run1/renders/schematic/M2h2I3A1Interleaved.svg`, SHA-256 `0e9d8382a5815c8f15fa677981bc3776685bd7bd81b6bbed54651d5d0fd5b659`. The 555 timer feeds a left-to-right two-stage resistor/capacitor path; the primary output and auxiliary output occupy distinct points on the right. Branches are traceable, although the long lower return and upper-right routing leave a broad, sparse arrangement. Independent observed values: 172.72 × 72.39 mm, 30.6357% page utilization, 34.29 mm motif fragmentation, 671.83 mm wire length, 21 observed bends; zero ERC violations, flow reversals, crossings, body overlaps, wires through bodies or text.

## `selected_triple`

Inspected `interactions/i3/selected_triple/run1/renders/schematic/M2h2I3SelectedTriple.svg`, SHA-256 `867fb2ba05a66cafdebfdd931a65941708fe904cf7818d4a13e388607feae284`. The two timer channels read as stacked signal stages; a dual op-amp package and reference support occupy the right/lower regions. The package's U3C unit and decoupling components sit well above U3B, visually separating package-local support. Several long net labels link outputs to distant connectors near the lower-left, making those interface associations less immediate. Independent observed values: 181.61 × 135.89 mm, 60.4692% page utilization, 29.21 mm motif fragmentation, 829.31 mm wire length, 35 observed bends; zero ERC violations, flow reversals, crossings, body overlaps, wires through bodies or text.

## `three_amplifier_one_band`

Inspected `interactions/i3/three_amplifier_one_band/run1/renders/schematic/M2h2I3ThreeAmplifierOneBand.svg`, SHA-256 `8c1fa49971a385bc0cea982305ccdc8ec6c91afea60d4de2c9d34d893d677e75`. Three amplifier signal stages align across a single horizontal band, with inputs and outputs clearly ordered. Shared/reference support units sit above the row and remain understandable, though the extra package/reference circuitry makes the upper band denser than the main signal row. The drawing leaves substantial space below. Independent observed values: 160.02 × 77.47 mm, 30.3749% page utilization, 20.32 mm motif fragmentation, 665.48 mm wire length, 32 observed bends; zero ERC violations, flow reversals, crossings, body overlaps, wires through bodies or text.

All 14 I3 cases are now accepted and reproducible ×5. These 14 inspected native renders do not establish final 137-case native-render inventory or comparative acceptance.
