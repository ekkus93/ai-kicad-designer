# Claude Code Handoff — 2026-10-16

## Project and Current Focus

This repository is `ai-kicad-designer`, a Python 3.12 package for generating and qualifying KiCad schematics. The active larger effort is tracked in [`M2H2_HUMAN_READABLE_SCHEMATIC_COMPOSITION_TODO_2026-10-07.md`](M2H2_HUMAN_READABLE_SCHEMATIC_COMPOSITION_TODO_2026-10-07.md). It is **in progress, not accepted as complete**. The TODO records extensive open qualification and visual inspection requirements; read its latest status banner and sections 15–21 before changing production behavior. Do not change frozen baselines, observers, tolerances, or acceptance gates merely to make a check pass.

The immediate human-review thread concerns the I4/B2 mixed routing example. The latest work is on branch `review/m2h2-routing-visual-review-2026-10-15`, commit `c1bc5256` (`Clear output one from return wiring`), pushed to `origin`. It changes the generic output-frontier placement in `src/ai_kicad/m2_pack.py` and refreshes the review schematic and SVG. **This branch is not merged into `master`.** Check it out to inspect or continue this routing work; the handoff itself is being committed separately to `master`.

## Latest I4/B2 Review State

Open [`docs/reviews/m2h2-routing-review-2026-10-15/README.md`](reviews/m2h2-routing-review-2026-10-15/README.md) and the files under `i4-b2-mixed/`. Output 1 was staggered along the outer frontier to clear the return wiring. In the latest locked KiCad 10.0.6 build, measured canonical lengths were INPUT 57.15 mm, OUTPUT_1 60.96 mm, OUTPUT_2 53.34 mm, and RETURN 203.20 mm (RETURN was 236.22 mm in the prior review). ERC, unrouted-pin, body/text intrusion, and unrelated-crossing counts were zero. Ruff lint/format and `git diff --check` passed for this revision. Full five-run qualification and the 90-case comparative audit were **not** run for it. The user has not yet reviewed this newest render.

The route-selection issue was that connector enclosure avoidance outranked route length. Fully aligning outputs exceeded the RETURN length cap; staggered frontier placement cleared Output 1 and shortened RETURN. Ask for the user's visual feedback before treating this individual review as closed.

## Next Work

1. Get the user's review of the latest I4/B2 SVG and address any remaining visual defects with general placement/routing rules.
2. Continue the open TODO work, starting with its latest exact-source qualification status; existing historical comparison has documented failed frozen criteria, and native-render engineering inspection remains open.
3. For behavior changes, run the prescribed locked KiCad suites, full pytest/Ruff checks, comparative baseline audit, and native-render inspection from the exact source revision. Preserve evidence and failures; do not claim broad acceptance from a single-case build.

## Working Notes

Use Python 3.12, with `python -m pytest -q`, `python -m ruff check src/ai_kicad tests tools`, and `python -m ruff format --check src/ai_kicad tests tools` for standard checks. Governed schematic qualification requires the pinned KiCad 10.0.6 toolchain; see `fixtures/m1a/toolchain.lock.json` and the relevant `tools/` workflows. The local machine has an available GPU and Ollama, and KiCad is available through the locked AppImage launcher at `/tmp/AppDir/AppRun` in this environment. No Ralph Bridge was used; the user explicitly asked not to use it.
