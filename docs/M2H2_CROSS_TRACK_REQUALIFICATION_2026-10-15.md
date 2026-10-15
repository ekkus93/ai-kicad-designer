# Bounded interior cross-track requalification — 2026-10-15

Production routing and regression source: `48c58dd33298b042726be12a51308a035f3981bf`.

Generic, source-neutral routing now enumerates at most 32 additional obstacle-derived interior two-track escape candidates per connection. Existing route legality, prior-net crossing checks, page bounds, conductor length limits, eight-plan distribution budget, historical baselines, observer/oracle, and pinned KiCad toolchain are unchanged. New tests cover both orthogonal orders, bounded permutation-invariant candidate sets, and nondegenerate legs.

Exact-source [Fast Validation](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38731606600) PASSED all three jobs (hosted contracts, locked-runner complete pytest/current-source regressions, static/Ruff). [Locked toolchain diagnostic](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38731606484) PASSED.

This documentation-only descendant requests all three independent locked KiCad 10.0.6 five-run suites (56 base plus V3-8 negative, I1–I6, and nine structural classes) and the development composition probe against the exact qualification head. Passing fast gates is not evidence of native visual or frozen historical comparative acceptance. The latest independent comparison failed five criteria; sections 15–21 remain OPEN. Do not alter frozen thresholds, baseline, observer, or toolchain.
