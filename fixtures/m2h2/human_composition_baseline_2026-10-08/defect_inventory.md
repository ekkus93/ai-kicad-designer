# Initial native-render defect inventory (partial)

Historical M2h2 PASS remains unchanged. Frozen production SHA:
`79a36b173c6c82a68cbe575cc1d666c55d2296b3`.
Native qualification SHA: `42ab8452fca16592ead8f628b17980a9d34794b7`.

The ten preserved `final_native_42ab8452/partNN.json` archives contain
90 native SVGs with SHA-256 records. The sorted (case, svg_sha256)
inventory has SHA-256
`759f49bf715da357d70f4fb4ae5513594328acb3ba8612031866ac6788a21fe0`.

The `i4__b2_mixed` native SVG in part08 has verified SHA-256
`9deab519039a207aa8de93508cc538c3c4c404ca9f6da3d17eab40a4d80f371e`.
Both output connector labels begin at x=75.6 pt, whereas the matching
signal net labels begin at x=342.0 pt: a 266.4 pt (approximately 94 mm)
horizontal visual separation. Output interfaces are on the input side
rather than associated with the final producer. The layout also occupies
a small upper-left region; utilization and detour gates require independent
quantitative evaluation.

This is a falsification seed, not case-specific production logic or final
qualification. Other archetypes and all-case metrics remain open.
