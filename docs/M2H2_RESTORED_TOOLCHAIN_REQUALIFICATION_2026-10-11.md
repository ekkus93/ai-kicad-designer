# M2H2 restored locked-KiCad exact-head qualification — 2026-10-11

**Status: QUALIFICATION REQUESTED; COMPARATIVE VISUAL PASS NOT ESTABLISHED.**

The user's reinstated `/tmp/AppDir` contains original KiCad 10.0.6 and all six SHA-256 hashes still match `fixtures/m1a/toolchain.lock.json`. Ralph Bridge independently confirms that [locked toolchain diagnostic 38135180694](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38135180694) passed against `074ba09c93419b935e680d7578c54179459c3ee2`. The FUSE mount failure concerns launching the standalone AppImage and is not a waiver of the locked extracted AppDir identity.

The current behavior-affecting code includes the generic candidate-priority and low-bend routing-rank changes. On source `074ba09c93419b935e680d7578c54179459c3ee2`, locked-runner and hosted Fast Validation jobs passed but Ruff static formatting failed for two regression tests. Formatting-only commit `17c770881cdbb85859ac8d3fc728e7fe7a28931a` fixes those tests; full Fast Validation must still be verified.

This document launches unchanged-threshold, exact-HEAD locked KiCad 10.0.6 requalification of base 56×5 plus V3-8, I1–I6 interaction ×5, and nine structural classes ×5. It is a reporting-only descendant of the actual behavior-affecting source. Preserve separately keyed evidence for this exact commit; do not overwrite previous accepted or failed cases. Only after all three workflows pass should the independent source-matched comparative artifact audit and native-render inspection be treated as valid final-candidate evidence.

The original corpus comparison still has six failing visual-acceptance gates. The governing `docs/M2H2_HUMAN_READABLE_SCHEMATIC_COMPOSITION_TODO_2026-10-07.md` stays INCOMPLETE until every acceptance criterion is met; no unchecked boxes are waived here.
