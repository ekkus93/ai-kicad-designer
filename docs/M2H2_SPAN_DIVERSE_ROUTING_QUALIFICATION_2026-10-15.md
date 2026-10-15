# M2h2 span-diverse interior routing qualification — 2026-10-15

**Status: production fix implemented; qualification requested; frozen comparison still OPEN.**

Behavior source `9d4141ab95b051859312838b50b5730654907a51` replaces the coordinate-biased first-eight interior obstacle-track selection with deterministic quantile sampling across the entire endpoint span. For any track between endpoints, `abs(track-a) + abs(track-b)` is constant; the former tie-break therefore excluded far-side escape lanes in dense bands. The new selection retains both interior extremes, includes intervening lanes, and preserves the eight-track interior cap and nearest outside tracks. It changes no electrical, page, clearance, previous-net, canonical-length, candidate-search, observer, or frozen acceptance gate.

Four source-neutral regression tests cover dense tracks, endpoint reversal/insertion invariance, sparse/outside retention, far-side candidate generation, and negative coordinates. The implementation and formatting are on `master`, with no new branch or PR.

**Requested at this documentation-only descendant:** exact-source Fast Validation, pinned KiCad 10.0.6 identity, full 56-base×5/V3-8-negative qualification, I1–I6×5 interactions, nine structural classes×5, and generic development probe. A request is not a PASS. If all suites pass, perform an independent full 90-case historical comparison and 137-case×5 normalized native-render inventory bound to this exact source, then inspect the renders. The last completed independent comparison failed five frozen criteria; TODO sections 15–21 remain unchecked. Do not alter baselines, tolerances, oracle, toolchain, or acceptance checkboxes without evidence.
