# M2h2 comparative audit outcome — 2026-10-15

Exact qualified source `20ca22ccd0349f33cdbcd9bd32dda78af7b25d8c`: locked KiCad 10.0.6 base 56x5 (38723936637), I1–I6x5 (38723936522), and structural 9-class x5 (38723936553) PASS. Native render inventory (38729570231) PASS.

Independent historical comparison run 38729570577 FAILS five frozen criteria: baseline hard-defect closure, individual hard-defect nonworsening, routing aesthetics, repeated-structure tolerance, and mixed-case improvement. Historical to fresh: stage inversions 1→0; interface violations 77→48; fragmentation 14743.4342→14672.3162 mm; edge-biased cases 64→51; U-detours 691→842; branch inconsistency 1529.08→1725.93 mm.

Unresolved hard witnesses: shared-rail local-label disconnects 1→2; V4-7 and V6-3 interface-side violations 0→1; passive fanout local-label disconnects 1→2. Mixed I4 B2 still has page edge bias, U-detours 2→7, fragmentation 73.6602→99.0602 mm, and branch inconsistency 21.59→29.21 mm. Prioritize generic bounded routing, candidate generation, and repeated-structure improvements; do not alter frozen baselines, thresholds, observer, or toolchain. Native engineering inspection and TODO sections 15–21 remain OPEN. No visual PASS.
