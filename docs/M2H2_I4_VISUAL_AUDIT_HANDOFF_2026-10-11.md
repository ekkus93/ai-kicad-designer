# M2H2 comparative audit and I4 render inspection handoff — 2026-10-11

Qualified source: `6a15e01ed248d467d98d9e01794789917b218885`.

The exact-source [comparative audit 38153545158](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38153545158) **FAILED** six unchanged criteria: baseline hard defects cleared, individual hard defects never worsen, functional fragmentation nonworsening, routing aesthetics nonworsening, repeated-structure tolerance, and I4-specific improvement. Its 90-case historical comparison reported interface-side violations 77→53 and stage-order inversions 1→0, but fragmentation 14743.4342→14759.9463 mm, U-detours 691→845, and branch inconsistency 1529.08→1717.04 mm.

For `i4__b2_mixed`, observer hard defects fell from four to zero and page edge bias cleared, but fragmentation rose 73.6602→99.0602 mm, detours 2→6, and branch inconsistency 21.59→29.21 mm. Other new hard regressions include `base__v4-7` (interface-side), `base__m2f2-two_signal_chains_shared_rail` (local label disconnect), and `structural__a0_interleaved` (interface-side). None is waived.

The [native-render inventory 38153545170](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38153545170) passed: 137 cases and 685 SVGs, with identical normalized geometry hashes in all five runs of every case. Raw hashes vary from volatile SVG content. Visual inspection and comparative acceptance remain OPEN.

This commit requests the preserved native SVG for `i4__b2_mixed` for independent engineering inspection; the authoritative TODO remains INCOMPLETE.
