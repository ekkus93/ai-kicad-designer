# Structural native-render engineering inspection

- Qualified source: `ee4c37a711b1107085acaed5e58bf3e7ae78bd50`
- Evidence root: `/home/jovyan/m2h2-evidence/ee4c37a711b1107085acaed5e58bf3e7ae78bd50/structural/`
- Render origin: locked KiCad 10.0.6 SVGs from each `run1/renders/schematic/`
- Inspection: full-page engineering review of all nine required structural-class renders, using 2200-pixel-wide PNG previews rasterized from those SVGs with CairoSVG 2.7.1.
- Reviewer: Codex engineering inspection; this is not user approval.
- Scope: this is structural-class candidate inspection only. It does not establish section 18 final-source render closure or the complete 137-case inspection requirement.

## Findings

All nine selected class candidates satisfy their recorded class, five-run reproducibility, electrical/ERC, serialized-scene, and composition-observer checks. Their independent reports show zero body overlaps, wires through bodies or text, unrelated wire crossings, and ERC violations. The full-page review found no visible symbol-text collision or malformed electrical symbol. These are necessary observations, not aesthetic acceptance.

Page use remains a material concern for the sparsest candidates. In particular, `a0_interleaved`, `a0_multiple`, and `a1_interleaved` place content in the upper-left portion of an A4 page, leaving most of the sheet empty. Their content envelopes and center offsets are recorded below. `a1_interleaved` and `a2_interleaved` also put output connectors away from the corresponding producer row and rely on matching local labels to communicate the relationship. The connectors are electrically verified, but their visual association needs review against the final interaction renders. No frozen page-use threshold for these generated structural alternatives was applied here; the applicable frozen 90-case comparison remains authoritative.

These observations keep human-composition acceptance open. Do not check TODO section 18 or section 21 from this review alone. Revisit the low-utilization and label-separated cases in the complete exact-source render inventory and independent case comparison.

| Structural case | Content envelope (mm) | Utilization (observer ppm) | Centroid offset (mm) | Full-page inspection |
|---|---:|---:|---:|---|
| `a0_interleaved` | 85.90 × 75.78 | 221421 | −59.5, −27.9 | Very sparse and strongly upper-left; passive input/output connectors do not form an obvious left-to-right row. |
| `a0_multiple` | 110.03 × 63.08 | 236086 | −46.2, −36.8 | Very sparse and upper-left; resistor/capacitor branches are individually legible, but page balance is poor. |
| `a1_interleaved` | 105.78 × 79.59 | 286373 | −49.1, −26.0 | Timer and support are legible; output connector is separated from its producer by page position and label association; large upper-left bias. |
| `a1_multiple` | 137.42 × 103.72 | 484809 | −32.0, −16.4 | Timer and output branches read clearly; whitespace remains broad but less severe than the preceding cases. |
| `a2_interleaved` | 124.12 × 138.01 | 582669 | −40.4, 2.0 | Two timer channels are readable as a vertical sequence; output connectors sit on a separate lower row with label-mediated association. |
| `a2_one` | 134.59 × 122.77 | 562016 | −33.9, −6.9 | Two repeated channels are aligned horizontally and easy to compare; interface ports occupy a separate top row. |
| `a3_interleaved` | 206.51 × 134.20 | 942640 | 2.1, −1.2 | Three channels are electrically traceable across the interleaved layout; broad separation and lower-row output connectors make the channel grouping less immediate than the one-band version. |
| `a3_one` | 204.44 × 73.24 | 509285 | 1.0, −31.7 | Three repeated timer channels align consistently; output ports are on a common top row; substantial lower-page whitespace. |
| `three_amplifier_one_band` | 166.76 × 78.32 | 444239 | −19.1, −29.1 | Three active amplifier stages align on one row; package support/parked units are above; labels remain readable and the page is top-biased. |

## Render hashes

Hashes below identify the exact inspected native SVGs in this evidence root.

| Structural case | Relative SVG path | SHA-256 |
|---|---|---|
| `a0_interleaved` | `a0_interleaved/run1/renders/schematic/M2h2I3A0Interleaved.svg` | `96c7d7ac07586a25b31997d4005c8eb65f22e0e4b2eaa7541a11cbac3f479b66` |
| `a0_multiple` | `a0_multiple/run1/renders/schematic/M2h2I3A0Multiple.svg` | `af7fba77d1bb21228add7d7e42130fb1ef335454420f0029a78b9d56f9ffcd77` |
| `a1_interleaved` | `a1_interleaved/run1/renders/schematic/M2h2I3A1Interleaved.svg` | `53a5a91ad8d9a4cea762a437372b8dae84fdf2778ba76668164d1a6bddcfed5d` |
| `a1_multiple` | `a1_multiple/run1/renders/schematic/M2h2I3A1Multiple.svg` | `e4ce2271d6df0c7bfc78ab0e60ee63553d6d56e30ad2eca2e8bf4a73711e2e76` |
| `a2_interleaved` | `a2_interleaved/run1/renders/schematic/M2h2I3A2Interleaved.svg` | `627c1794c22703bdf26de9b4e977558ddb00555d7bd691c16de0b607a20aedd7` |
| `a2_one` | `a2_one/run1/renders/schematic/M2h2I3A2One.svg` | `d83790602766237df901d3188d09b8dbdb223069aa916feaedeab59d8a23367d` |
| `a3_interleaved` | `a3_interleaved/run1/renders/schematic/M2h2I3A3Interleaved.svg` | `4db8537bca073138fa19a41127fa5aa8df03e19060a48e959e38563a0b5180b7` |
| `a3_one` | `a3_one/run1/renders/schematic/M2h2I3A3One.svg` | `cc107f8d80204cbadd3e47732a020945707e98da0f5745d799d88823cad1c66b` |
| `three_amplifier_one_band` | `three_amplifier_one_band/run1/renders/schematic/M2h2I3ThreeAmplifierOneBand.svg` | `3d60549ccbb02d525ee73332a99568b9659afa075a6c123a8a99dce68672b8c7` |
