# MCP handoff: power-symbol rails and the 555

**Date:** 2026-10-27 (second handoff of the day; continues [`MCP_HANDOFF_2026-10-27.md`](MCP_HANDOFF_2026-10-27.md))

**Branch:** `mcp`. This handoff covers commits `5ed00db2` through `5330ca4c`, plus the commit that adds this file.

Governing documents remain [`MCP_ARCHITECTURE_SPEC.md`](MCP_ARCHITECTURE_SPEC.md) and [`MCP_ARCHITECTURE_TODO.md`](MCP_ARCHITECTURE_TODO.md). **The TODO checkboxes and notes were not updated in this session.** The new evidence below has not yet been recorded against P6-011b–f, because no human readability or electrical review has been done.

## Summary

The reference 555 could not be drawn under the old rail rule, and that was a geometry fact, not a model weakness. Under review brief v2:
- every terminal of VCC and REF must be joined by drawn wire;
- the protected M2 layout observer forbids wires of different nets crossing.

On the NE555D symbol, the pins run 5, 8, 3, 1, 2, 6, 7, 4 around the outline. Any VCC wire joining pins 8 and 4 forms a closed loop with the body, and that loop separates CONT (pin 5, with C2's REF pin) from GND (pin 1). So no placement, spacing or routing can satisfy both rules. Experiments confirmed it: channel widening and full rail rip-up both failed.

The owner chose to allow conventional power symbols for rails. This was implemented as **review brief v3**:
- A rail may be joined by wire, or each separately drawn terminal group may carry a matching power symbol: a ground glyph for REF/GND, a supply arrow otherwise.
- Label-only joins are still rejected.
- Brief v2 is unchanged.

**Result:** the editor can now produce 555 schematics that pass every independent check (KiCad ERC, netlist equivalence, layout, rail presentation and power-symbol clearance). However, the local vision model (Qwen 3.5) has not yet accepted one.

## What was built this session

- **Context size control** (`5ed00db2`). The review service and corpus driver take `--context-tokens`. Earlier runs always used `num_ctx` = 16384, even with long-context models, because the reviewer sends `num_ctx` explicitly and that overrides the Modelfile. Each review uses about 10–20K tokens.
- **`use_power_symbols` edit and brief v3** (`03aa4b4e` and later fixes):
  - `src/ai_kicad/pivot/power_symbols.py` holds placement, the label view, the `rail_presentation` and `power_symbol_clearance` checks, and the locked-symbol loader.
  - The power symbols are KiCad 10.0.6's own `power:VCC` and `power:GND`, copied byte-for-byte to `fixtures/pivot/power_symbols/` with a sha256 manifest.
  - The brief is `fixtures/pivot/schematic_review_brief_v3.json`, with schema `fixtures/pivot/schematic_review_brief.v3.schema.json` and model `SchematicReviewBriefV3`. The review service turns on the power-symbol policy only for a v3 brief, and the engine rejects `use_power_symbols` without it.
- **How the edit works:**
  - It removes the rail's labels and its terminal-to-terminal wiring.
  - It keeps the shortest wire from each PWR_FLAG to its connector, and from each declared decoupling capacitor to the supply pin it serves. The protected observer requires the latter.
  - It places one symbol per wire group. Short stubs of 1–4 grid steps are allowed. Ground glyphs point up, and supply arrows down, only as a last resort.
  - Each candidate position is checked for geometric clearance against parts, fields, labels, visible pin numbers and other nets' wires. It is also checked by running the protected M2 layout observer on the label view, using the current revision's KiCad netlist (connectivity is unchanged by the edit).
  - Repeating the edit re-places only that rail's crowded symbols.
  - If no clear position exists, the edit is refused, naming the nets whose wiring blocks it.
- **How checking works with power symbols.** KiCad ERC and the netlist run on the real schematic; KiCad leaves `#PWR` symbols out of the netlist. The protected M2 observers (netlist comparison, layout, field checks) cannot read power symbols, so they inspect a *label view* in which each power symbol becomes a same-named local label at its connection point.
- **Feedback text.** Under v3, a blocked `connect_rail` now points the model at `use_power_symbols`. The prompt says to repeat it when `power_symbol_clearance` fails.
- **Harnesses:**
  - `tools/pivot/run_rail_repair_corpus.py --power-symbols` tries wiring, then power symbols, then the move search, and finally an all-power-symbols plan. One design's initial-assessment failure no longer aborts the whole run.
  - `tools/pivot/run_review_loop_corpus.py` gains `--context-tokens`, `--model-timeout`, `--designs`, and resolves relative `--review-brief` paths.
- **Tests:** `tests/pivot/test_power_symbols.py` has 18 tests. `tests/pivot/test_schematic_group_edits.py` adds an assertion for the v3 blocked-route message. The new tests that cover bug fixes were checked to fail without the fix.

## Evidence (all under `fixtures/pivot/experiments/`)

| Run | Commit | Result |
|---|---|---|
| `review_loop_corpus_2026-10-27_qwen35_256k_run1` (brief v2, `qwen35-256k:latest`, 262144 context) | `5ed00db2` | 6/14 accepted; the earlier `qwen3.5:9b` 16K run accepted 5/14. Gains: `led_reverse_supply` and `linear_regulator`. Loss: `rc_to_buffer`. |
| `rail_repair_corpus_v3_2026-10-27_run1` | `03aa4b4e` | Aborted when a parallel KiCad export failed. KiCad logged "Invalid lock file /tmp/org.kicad.kicad/instances" (an instance-lock race under `--jobs 4`). |
| `rail_repair_corpus_v3_2026-10-27_run2` | `03aa4b4e` | `dual_buffer` rerun alone; assessment succeeded. |
| `rail_repair_corpus_v3_2026-10-27_run3` | `05a9cafb` | Found that decoupling wires were being removed and that label positions conflicted with the observer. |
| `rail_repair_corpus_v3_2026-10-27_run4` (`--jobs 1`) | `c1c77832` | **All asserted rails resolved on 8/9 designs, including `timer_astable` and the reference 555 v8.** Sallen-Key still has VMINUS unresolved. |
| `review_loop_corpus_v3_2026-10-27_qwen35_256k_run1` (brief v3) | `c1c77832` | 5/14 accepted. The driver crashed after all designs (relative brief path); `summary.json` was rebuilt from per-design results and is marked `reconstructed_after_driver_crash`. |
| `review_loop_corpus_v3_2026-10-27_qwen35_256k_run2` (brief v3, 600 s model timeout) | `c606d7b5` | 6/14 accepted, including `dual_buffer`, fixed by the model with `use_power_symbols`. |
| `review_loop_555_v3_2026-10-27_qwen35_256k_run1` (both 555s) | `95e63161` | 0/2 accepted, but **both reached a candidate passing every independent check** (`candidates/003`). The model rejected both, citing `visible_rail_continuity`, a check brief v3 does not use. |

For rail-repair runs, each candidate's schematic and `assessment.json` are committed, plus the full final candidate per design and every `result.json`/`summary.json`. Other intermediate files remain on local disk only. Review-loop runs are committed in full, except gitignored `.kicad_prl` files. Everything is first-run evidence on this Linux host, not the locked qualification host.

## Open issues and next steps

1. **Reviewer prompt still assumes brief v2's rail rule** (`src/ai_kicad/pivot/schematic_review.py`, the long rail paragraph in the system prompt). Under v3 the model keeps citing `visible_rail_continuity` and asking to wire VCC.
   - Recommended next step: make the rail paragraph depend on the active brief or on the checks present. Under v3, mention only `rail_presentation`, `power_symbol_clearance` and `use_power_symbols`.
   - Then rerun the 555s, for example: `run_review_loop_corpus.py --designs timer_astable reference_555_led_flasher_v8 --review-brief fixtures/pivot/schematic_review_brief_v3.json --model qwen35-256k:latest --context-tokens 262144 --model-timeout 600`, about 25 minutes. A smaller context (`qwen35-32k`) should be much faster, since 262K runs mostly on the CPU of the 16 GB GPU host.
2. **No human review yet.** The passing 555 candidates (`review_loop_555_v3_.../*/candidates/003/review-images/`) and the rail-repair run4 finals need owner readability review. Visual issues noted so far:
   - VCC arrows sometimes point sideways or sit on short stubs.
   - The timer_astable passing candidate has R1's VCC arrow pointing down.
   - REF wiring added by `connect_rail` can be long.
   - VMINUS/VPLUS both use the supply-arrow glyph; there is no negative-rail glyph.
3. **`field_owner_association` fails on compiler output for every op-amp design.** U1C's reference sits closer to a capacitor than to its own unit. It needs a `move_field` edit, or the model's acceptance will stay blocked.
4. **Sallen-Key** still has VMINUS unresolved in rail-repair run4.
5. **Model behaviour failures** seen in the logs:
   - It requested `connect_rail` on non-asserted `LOCAL_REF` (`led_reverse_supply`).
   - It requested `move_symbols` with unit references such as `U1A` or `3`, which aren't valid references.
   - It repeated rejected edits until `NO_PROGRESS`.

   Error messages could suggest valid references and nets.
6. **Documentation:** `docs/pivot/SCHEMATIC_REVIEW_LOOP.md` does not yet describe brief v3, `use_power_symbols` or the label view.
7. **TODO bookkeeping:** record the runs above as `Evidence:`/`Note:` sub-bullets under P6-011b–f in `docs/MCP_ARCHITECTURE_TODO.md`, without checking any item until human review exists.
8. **Unchanged blockers from the earlier handoff:** P0-013/X-001 (no self-hosted runner), P4-009, P5-001–P5-004, P6-002, P6-005 and P6-006. The page-composition criterion (P6-011b) still needs an owner decision.

## Workspace notes

- **Python environment.** Use `.venv/bin/python`. The editable install imports `src/` from the main checkout, so set `PYTHONPATH=src` when testing in a git worktree.
- **Formatting.** Run `ruff format` only on files you changed. Several pivot files (`controller.py`, `backend.py`, `direct_backend.py`, `native.py`, `requirements.py`, `revisions.py`) are not formatter-clean at HEAD.
- **Parallel KiCad.** Run KiCad-heavy corpus jobs with `--jobs 1` to avoid the KiCad instance-lock race seen in rail-repair run1.
- **Long runs and source hashes.** Long corpus runs hash source files when they finish. Don't edit the working tree while one is running; use a separate worktree.
- **Test baseline.** `python -m pytest -q tests/pivot`: 195 passed, 11 failed. All 11 failures are hard-coded desktop KiCad/ngspice paths (`/home/phil/...`) in `test_direct_backend.py` and the ngspice test. Ruff check is clean.
- **Untracked files left in place.**
  - `.claude/`, `.serena/`, `CLAUDE.md` and `AGENTS.md`. `CLAUDE.md` imports `AGENTS.md` and documents host paths and test scope.
  - The preserved untracked `fixtures/m2h2/*` evidence.
  - Captured home/config files under older `fixtures/pivot/experiments/konnect_*` runs.
  - The partial `rail_repair_corpus_2026-10-26_run2`/`_run3` data.

  Do not use `git add -A` here.
