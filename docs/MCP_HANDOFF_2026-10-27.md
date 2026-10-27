# MCP project handoff

**Date:** 2026-10-27

**Branch:** `mcp`
**Workspace at handoff:** current branch includes the 14 commits after `origin/mcp` as of `d5aed8b6` (`Record P6-011f complete review loops across the vetted corpus`), plus this handoff commit. The branch was pushed after creating this document.

## Project state

Continue from [`MCP_ARCHITECTURE_SPEC.md`](MCP_ARCHITECTURE_SPEC.md) and [`MCP_ARCHITECTURE_TODO.md`](MCP_ARCHITECTURE_TODO.md). The MCP pivot has advanced well beyond the 2026-10-22 desktop handoff: image review is integrated into the `SCHEMATIC` controller phase, and the branch now includes `connect_rail`, constrained `move_symbols`, and corpus review/repair runners. The `mcp` branch is the authorized development branch.

The broad P6-011 objective is **not complete**. Its current state is:

- **P6-011a complete:** versioned owner review brief and criteria.
- **P6-011b open:** the 2026-10-26 visual qualification covered 20 cases across 8 circuits with Qwen 3.5 9B and Devstral Small 2 24B. Image-only reviews rejected all five clean cases for both models. Full reviews still falsely accepted two off-balance pages because page balance has no qualified independent measure. An owner-selected composition criterion and independent human readability review remain outstanding. See `fixtures/pivot/evidence/P6-011b-visual-qualification-2026-10-26.json`.
- **P6-011c marked complete in the TODO:** `connect_rail` and `move_symbols` passed native, ERC, equivalence, and layout checks on 6 of 8 asserted-rail circuits. The reference 555 and Sallen-Key still have unroutable rail cases. Some successful routes are long or crowd connector labels; independent readability assessment remains outstanding. See `fixtures/pivot/evidence/P6-011c-group-edits-corpus-2026-10-26.json`.
- **P6-011d open:** Qwen and Devstral stopping/recovery probes retain failures without false acceptance, but no model recovered the reference 555 to acceptance; regression/truncation breadth is incomplete. See `fixtures/pivot/evidence/P6-011d-recovery-and-stopping-2026-10-26.json`.
- **P6-011e open:** `review_schematic` is integrated in the SCHEMATIC phase and FOOTPRINTS is gated on current-revision evidence. The demo correctly fails closed; no accepted review has unlocked FOOTPRINTS on a correctly bound revision. See `fixtures/pivot/evidence/P6-011e-schematic-phase-integration-2026-10-26.json`.
- **P6-011f open:** the Qwen corpus runner covered 13 M2b designs plus the reference 555 v8. Five of 14 reached joint acceptance; nine stopped without false acceptance. The reference 555 VCC rail remains unroutable. There is no independent readability assessment. See `fixtures/pivot/evidence/P6-011f-review-loop-corpus-2026-10-26.json`.

Other unchecked TODO items are P0-013, P4-009, P5-001 through P5-004, P6-002, P6-005, P6-006, and X-001. Important owner/human decisions include the Panasonic capacitor supplier/lifecycle and C1 body-model treatment (P6-002), review of the assembly drawing and independent Gerber/rotation validation (P6-005), human electrical review and the corrected held-out 555 run (P6-006), and visual/readability criteria for P6-011b/f. P5 manufacturing, delivery, and physical testing require their own explicit approvals.

## Latest implementation and evidence

The 14 local commits after the prior remote tip include the complete-corpus review driver, SCHEMATIC-phase integration, revision binding, rail repair/group movement, image-only qualification, and recorded corpus results. The most recent commit is `d5aed8b6`; the changes are on `mcp` and were pushed with this handoff.

The committed P6-011c group-edit evidence is in `fixtures/pivot/experiments/rail_repair_corpus_2026-10-26_run1/` plus the retained subset of `_run3/`. The P6-011f corpus run is `fixtures/pivot/experiments/review_loop_corpus_2026-10-26_qwen_run1/`. Read the TODO notes before repeating long model runs; several iterations already consumed substantial local model time and are retained.

## Workspace preservation

The tracked working tree was clean before creating this handoff. The workspace also contains many untracked artifacts from earlier investigations and experiment reruns, including `.claude/`, `.serena/`, `AGENTS.md`, `CLAUDE.md`, extensive `fixtures/m2h2/` material, captured home/config files under `fixtures/pivot/experiments/`, and partial rail-repair corpus run data. These were deliberately not staged with this handoff. In particular, the untracked portions of `rail_repair_corpus_2026-10-26_run2/` and `_run3/` are large; preserve them locally and inspect their manifests/status before deciding whether any belong in a later evidence commit. Do not use `git add -A` on this checkout.

## Toolchain and verification

Use Python 3.12 and the repository development environment. The repository commands are in `AGENTS.md`: `python -m pytest -q`, `python -m ruff check src/ai_kicad tests tools`, and `python -m ruff format --check src/ai_kicad tests tools`. The 2026-10-26 TODO evidence reports 176 pivot tests passing and 11 failures caused by KiCad/ngspice absolute paths from another machine. That count predates the latest review-loop corpus commits; rerun tests on the intended self-hosted desktop and verify the locked KiCad 10.0.6 and ngspice paths before drawing a current regression conclusion. Do not upgrade KiCad or weaken frozen evidence thresholds.

## Suggested next work

1. Review the exact failed 555 candidates and `P6-011f` loop records. Solve the VCC route obstruction without fixture-specific coordinates, and rerun independent KiCad/layout/net-partition gates.
2. Assess the successful 6/8 rail-repair renders for route length, connector-label crowding, and owner readability. Keep human review distinct from model acceptance.
3. Ask the owner to choose a measurable page-composition threshold for the false-acceptance cases before changing the brief or acceptance gates.
4. Continue the uncompleted P6-011d/e/f corpus and integration qualification only after preserving the current requests, failed candidates, and diagnostics.
5. Work through the remaining TODO items in dependency order; retain the manufacturing and physical-inspection approvals as separate owner decisions.
