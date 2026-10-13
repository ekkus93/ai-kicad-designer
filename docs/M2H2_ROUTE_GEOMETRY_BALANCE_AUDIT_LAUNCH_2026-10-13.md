# M2h2 route-geometry balance — frozen baseline audit launch (2026-10-13)

**Status: QUALIFIED ELECTRICAL/STRUCTURAL SOURCE, INDEPENDENT COMPARATIVE AND VISUAL ACCEPTANCE PENDING.**

## Provenance

The exact source under audit is `b8a69cc9b57750b2758ebf1b187fccd2ba443b7c` (documentation-only descendant of `4d64b42ed26b29638df39ca4ab2faec73299b75c`), whose generic routing-candidate ranking balances routed union length against bend count after the mandatory signal/side/ownership and route-backtracking tiers.

- [56 positive base cases ×5 and V3-8 negative: 38462094064](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38462094064) — **PASS**.
- [I1–I6 five-run interactions: 38462094056](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38462094056) — **PASS**.
- [Nine structural-class five-run cases: 38462094429](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38462094429) — **PASS**.
- [Locked KiCad toolchain: 38462094273](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38462094273) — **PASS**.
- [Fast Validation 38460169304](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38460169304) and [source-neutral development probe 38460169403](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38460169403) — **PASS** for the preceding same-behavior source `4d64b42e`.

The later `204721d119451bc7b66a98b86905ebb7aa9542f6` commit modifies only the bounded diagnostic report, its regression tests, and development probe coverage; the [expanded probe 38466268895](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38466268895) **PASSED**. These are not an alternate qualification root for the production layout.

Persisted exact-source native evidence: `$HOME/m2h2-evidence/b8a69cc9b57750b2758ebf1b187fccd2ba443b7c/`.

## Frozen independent acceptance

This commit triggers the existing 90-case historical comparative artifact audit and 137-case ×5 normalized SVG inventory against **exact** `b8a69cc9b57750b2758ebf1b187fccd2ba443b7c`. The native inventory also requests a single source-matched SVG-derived PNG preview for the known shared-rail failure witness `base__m2f2-two_signal_chains_shared_rail`. Preview images are engineering inspection aids only; the independent comparative observer remains authoritative. Reuse preserved qualification results without overwriting historical/failure evidence.

The preceding independent audit [38457583899](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38457583899) **FAILED five frozen criteria**. For the new route-balance source none of those failures is assumed fixed, and no existing tolerance, historical baseline, hard electrical/geometry requirement, or visual acceptance checkbox is changed by this launch. If the audit fails, diagnose per-case independent-hard, U-detour, repeated-stage, shared-rail and mixed-output geometry witnesses before further generic code changes.

Final TODO sections 15–21 remain open until full independent audit, case-by-case native engineering inspection, reproducibility, and final reconciliation demonstrate positive acceptance. Do not begin M3 or corpus.v7.
