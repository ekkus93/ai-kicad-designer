# M2h2 native-render inspection checkpoint — 2026-10-10

Status: PARTIAL / FAILED visual acceptance. This is engineering inspection, not user approval or final qualification.

Qualification source: `ea154c78b8f0ca7348159d3d068fc62d8630f337`.
Case: `i4__b2_mixed`, native KiCad 10.0.6 SVG from run 1.
SVG SHA-256: `df4efc81132e37d3c5727581f7652b625ac88d8dfec33dfbf2efcdc63d179005`.
Preview PNG SHA-256: `71590f14eb9399ea16e7ac530ed747dfebbafa250b76685d61aee0d765bdfc55`.
Ralph Bridge inspection transfer: workflow run `38083028721`, job `114303678066`, 58 PNG chunks.

The visual shows J1 signal input at left, R1/R2 progression along the upper row, and J3/J4 output interfaces to the right. C1/C2 return legs use matching RETURN labels. However, the circuit is packed into the upper part of the A4 sheet with extensive unused lower-page whitespace. R3 forms a conspicuous rectangular lower branch returning upward to J4, weakening branch attribution and output ownership. This render fails page-balance and route-readability inspection; it must not be marked accepted.

A generic remedy should preserve source-agnostic hard electrical and placement constraints while exploring better page centering and output-owner row alignment. A fresh native render and full comparative audit are required after any production change. The other 136 qualified cases are not visually inspected by this record.
