# M2h2 current-source comparative audit diagnostics — 2026-10-12

Independent audit: workflow run 38234136700, qualified source `b3c320b404e4210c0879866ba22eb6efb730693f`, **FAIL**. All 90 historical cases were matched. Six acceptance gates still fail: baseline hard defects cleared; individual hard defects never worsen; fragmentation nonworsening; routing aesthetics nonworsening; repeated-structure alignment within frozen tolerance; and `i4__b2_mixed` improvement.

Historical to fresh: stage inversions 1 to 0; interface-side violations 77 to 53; functional fragmentation 14743.4342 to 14759.9463 mm; edge-biased cases 64 to 55; U-detours 691 to 841; branch inconsistency 1529.08 to 1699.26 mm. The previous source-matched audit (38222075080) reported the same totals: the bounded frontier-retention change has not demonstrated an improvement in selected final layouts.

Examples requiring generic remediation: `base__v4-7` gained an interface-side violation; `base__m2f2-two_signal_chains_shared_rail` gained a local-label disconnect; `base__v6-5` gained a local-label disconnect; `structural__a0_interleaved` gained an interface-side violation. A plausible next generic investigation is whether the frontier candidate generator prioritizes large row misalignment over an interface on the wrong semantic side. This is a hypothesis, not a proven fix. Native inspection of the falsification seed remains mandatory.

No historical PASS, frozen thresholds, or sections 15–21 acceptance criteria are changed by this checkpoint. The original authoritative TODO remains INCOMPLETE.
