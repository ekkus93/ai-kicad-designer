# M2h2 bounded second interior corridor — implementation handoff (2026-10-14)

**Status: source change APPLIED and fast-qualified.** Initial source-write attempts were blocked, but the subsequent Ralph Bridge retry succeeded. After rectifying an omitted route-tree return and synchronizing the independent strategy-set contract and Ruff formatting, the final production/regression source `3fa6eafe8b97b95ff0787a2217dacab14b3d4b4c` passed all three [exact-head Fast Validation jobs (38652437889)](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38652437889) and the [locked KiCad 10.0.6 toolchain diagnostic (38652437837)](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38652437837). This is **not** full five-run qualification or independent composition acceptance.

## Exact inspected source

- Starting `master`: `c95421f4b638e71bbc264652b7caaa742e34f295`.
- Function: `_distribution_initial_trees` in `src/ai_kicad/m2_route.py`, approximately lines 465–615.
- Existing behavior: deterministic gateway-row median and obstacle-adjacent legal interior lanes are enumerated, but the loop stops at the **first** legally seed-connected lane. The planner then includes perimeter candidates, with a total eight-plan cap.
- Existing regression: `tests/test_m2_distribution_clear_lane.py` checks a blocked median, one clear lane at row 0, gateway permutation invariance, and the eight-plan cap.

## Minimal generic candidate-generation change to qualify

1. Within the `for y in ordered_lanes` loop, after appending a successfully legal `(strategy, conductors, trunk, expansions)` interior plan, replace unconditional termination with termination only after **two** legal interior plans have been collected. Keep all existing geometry, obstacle, seed-attachment, and length checks intact.
2. Retain the existing final eight-plan cap. Note that adding a second interior plan before exterior candidates can displace the final perimeter-side candidate when the budget is saturated; this is a deliberate search-budget tradeoff to evaluate, not proven to improve the corpus.
3. Update `test_blocked_median_selects_adjacent_legal_interior_lane` to assert two deterministic clear-lane candidates, with horizontal trunk rows 0 and `PITCH`, and retain all gateway-permutation and budget assertions.
4. Add an obstacle-controlled negative test if the full suite reveals a second corridor that is geometrically legal but electrically or visually undesirable. Do not special-case shared-rail fixture identifiers, relax observer thresholds, or increase the search budget.

## Qualification and falsification

- Run exact-head Fast Validation (complete pytest, Ruff/static checks, locked KiCad regressions) and pinned KiCad 10.0.6 toolchain diagnostic.
- If fast gates pass, trigger source-matched 56-base/V3-8-negative, I1–I6, and structural five-run qualification. Preserve failed witnesses.
- Only after three-suite success, run the independent frozen 90-case historical comparison and 137-case normalized native-render inventory, then inspect native renders case by case.
- Compare shared-rail label disconnects, U-detours, branch inconsistency, repeated-structure alignment, V6-3, V5-3, V4-7, and mixed I4 B2. Revert if per-case hard defects worsen or frozen comparative criteria do not improve.
- The last independent audit (run 38611663994) failed five frozen criteria; native inventory (38611663887) passed. Neither result is altered by this handoff.

**Next:** source-write access is working. Run the exact-head five-run base, interaction, and structural suites, then independent historical comparison/native-render inspection. Preserve the five unresolved frozen acceptance failures until the independent audit proves otherwise. Ralph Bridge remains the only GitHub/CI interface; no per-task branches or PRs.
