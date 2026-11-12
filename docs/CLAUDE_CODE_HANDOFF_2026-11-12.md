# Claude Code handoff, 2026-11-12

This file is for continuing work on another computer. Branch `mcp`, last pushed commit `8d2f86ea`. Everything below is committed and pushed. Nothing was left uncommitted except the long-standing untracked items listed under "Not in git".

## What this work is

P6-011f in `docs/MCP_ARCHITECTURE_TODO.md`: improve the readability of the schematics the native pipeline draws for the 15-design v3 review corpus. The owner reviews drawings (often with ChatGPT's opinion pasted in) and asks for specific layout fixes. Each fix is:

1. implemented
2. regenerated across all 15 designs and checked visually
3. recorded as a new write-once experiment folder
4. committed and pushed

Then the owner usually asks for a full model-review corpus run.

P6-011f stays **unchecked**: it still needs the independent readability assessment and the owner's human electrical review.

## State at handoff

Latest code: `8d2f86ea`. The latest full corpus run, `review_loop_corpus_v3_2026-11-11_qwen35_256k_run5` at `b414c4dd`, accepted 15/15. **No corpus run has been done on `8d2f86ea` yet**, so that is the natural next step if the owner asks to "run the full corpus".

Layout rules added 2026-11-09 to 11-12, in commit order (evidence folder in brackets):

| commit | change | evidence |
|---|---|---|
| `0b9049ab` | wires kept out of an op-amp power unit's pin column | `power_unit_column_2026-11-09_run1` |
| `2428c627` | horizontal two-pin parts' text centred above or below the body | `horizontal_field_text_2026-11-10_run1` |
| `2afc6702` | a connector-wired rail group is marked at the connector | `connector_rail_symbol_2026-11-10_run1` |
| `9a2a2d13` | ground symbols tried pointing down first; name may go beside the glyph | `upright_ground_symbol_2026-11-10_run1` |
| `3479ac9f` | power-unit text above its top pin (later superseded, see below) | `power_unit_text_above_2026-11-11_run1` |
| `a4d4a3ca` | supply rails: groups more than 25.4 mm apart get supply symbols instead of long wires | `supply_rail_symbols_2026-11-11_run1` |
| `cb479802` | same 25.4 mm cap for return rails (REF/GND) | `return_rail_symbols_2026-11-11_run1` |
| `570b27d4` | a decoupling capacitor whose wire detours is moved beside its pin | `decoupling_placement_2026-11-11_run1` |
| `b414c4dd` | rail names keep 1.27 mm clear of a power unit's pin-name column | `rail_name_pin_clearance_2026-11-11_run1` |
| `8d2f86ea` | power symbols keep 1.27 mm clear of part labels and of differently drawn rail names | `rail_name_part_text_clearance_2026-11-12_run1` |

Each folder's README explains the problem, the rule and the per-design results. The corpus runs between them are `review_loop_corpus_v3_2026-11-1{0,1}_qwen35_256k_run*`. `2026-11-11_run1` is a failed TOOL_ERROR run (ffmpeg missing) that was deliberately never committed. Leave it untracked; don't commit or delete it.

## Owner decisions to respect

- **U1C's label (op-amp power unit) stays beside the pins.** The owner first asked for it above pin 8. After the supply-symbol change, the independent owner-association measure reads text above pin 8 as VPLUS's, so the owner chose (a): beside. Don't move it back above.
- **VPLUS on pin 8 points sideways.** The spot above the power unit is reserved (`power_unit_text_spots`).
- **Leave the PWR_FLAG diamonds where they are.** ChatGPT has suggested grouping them at J1 twice; the owner hasn't approved that.
- **Repeated same-name net labels are not acceptable for rails** (brief v3 `visible_local_rails`). Power symbols are.
- **Decoupling pairs must keep an explicit wire.** The protected layout observer rejects a pair without one ("observed local motif lacks explicit wire path: decoupling"). Don't weaken that check.

## Known open issues and ideas (not started)

- **Reviewer false claims.** qwen35-256k repeatedly says the rails "rely on text labels only" on the symbol-heavy op-amp drawings: 4 of 5 in run5. The editor rejects the requested `connect_rail` and the next review accepts. This, plus four owner-found defects the model passed, is the case for **P6-011b** (qualify the reviewer on known-good and known-bad drawings). The previous accepted drawings in the evidence folders are ready-made negatives.
- **inverting_gain:** "U1C / NE5532" sits about 13 mm right of the pins after `8d2f86ea`, loosely attached. All checks pass.
- **Remaining tight text:** rc_to_buffer has a sparse page (utilization 0.24 against the 0.65 target). sallen_key and linear_regulator have 0.635 mm text-to-wire clearance.
- **Bigger idea:** a standard power/decoupling block layout (capacitors paired, rails above and below). Part placement comes from the protected M2 composer, so it would need a pivot-side placement step like `straighten_decoupling_text`.

## How to run things

- **Python:** use `.venv/bin/python` (3.12); system `python3` is 3.10. System python3 has PyMuPDF (`fitz`/`pymupdf`) for cropping SVGs.
- **KiCad:** the launcher is `/tmp/AppDir/AppRun` (KiCad 10.0.6 AppImage, locked in `fixtures/m1a/toolchain.lock.json`). **Check this path exists on the new computer**; this host is not the locked qualification host either.
- **Image review needs ffmpeg/ffprobe** (or rsvg-convert + ImageMagick). After a container restart here ffmpeg vanished. It was reinstalled with `sudo apt-get install ffmpeg=7:4.4.2-0ubuntu0.22.04.1`, the version recorded in earlier assessments.
- **Ollama model:** `qwen35-256k:latest` with the full 262144-token context. Don't restart Ollama yourself.
- **Full corpus** (one design run takes several minutes; all 15 about an hour). Only run it on committed code, because the run records the source commit:
  ```sh
  PYTHONPATH=src:. .venv/bin/python tools/pivot/run_review_loop_corpus.py \
    --experiment-id review_loop_corpus_v3_<YYYY-MM-DD>_qwen35_256k_run<N> \
    --kicad-apprun /tmp/AppDir/AppRun --model qwen35-256k:latest \
    --review-brief fixtures/pivot/schematic_review_brief_v3.json \
    --context-tokens 262144 --model-timeout 600
  ```
  `--experiment-id` is used verbatim, so include the date and `_runN`. Pick the next unused N. After the run:
  1. summarize `result.json` per design
  2. compare each accepted `.kicad_sch` (UUIDs stripped) with the latest evidence
  3. add a P6-011f progress note to `docs/MCP_ARCHITECTURE_TODO.md`
  4. commit `fixtures/pivot/experiments/<run>` with the TODO
  5. push
- **Regenerating designs without the model** (what each fix uses). A small script does it: for each name, build `NativeSchematicEngine(json.loads(<fixtures/m2b/NAME.json or fixtures/pivot/NAME/design.json>), Path("/tmp/AppDir/AppRun"), power_symbol_rails=True)`, then call `eng._compile(out_dir)` and `eng.assess(<project/*.kicad_sch>, out_dir/"assess")`. The `assess` directory must exist first. Check that all 9 checks pass:
  - native_tools
  - erc
  - electrical_equivalence
  - observed_layout
  - rail_presentation
  - power_symbol_clearance
  - field_separation
  - field_locality
  - field_owner_association

  Corpus design names are the 15 folders in any `review_loop_corpus_v3_*` run.
- **Evidence folders** are write-once. Create them with `tools.pivot.experiment_paths.create_experiment_dir(Path('.'), '<name>_<YYYY-MM-DD>_run<N>')`. Include for each changed design:
  - `project/*.kicad_sch`
  - `presentation.json` and `assessment.json`
  - `review-images/`
  - a before drawing or close-ups
  - a README in the house style used in recent folders
- **Tests:** `.venv/bin/python -m pytest -q tests/pivot` takes about 3 minutes. 11 failures are environmental and expected: 10 in `test_direct_backend.py` (desktop-only KiCad paths) and `test_engineering.py::test_real_ngspice_transient_matches_analytical_limit`. To skip them, add `--ignore tests/pivot/test_direct_backend.py --deselect tests/pivot/test_engineering.py::test_real_ngspice_transient_matches_analytical_limit`. Regression tests for this work are in:
  - `tests/pivot/test_bodyless_units.py`
  - `tests/pivot/test_connector_rail_symbol.py`
  - `tests/pivot/test_field_layout.py`
  - `tests/pivot/test_power_symbols.py`
- **Ruff:** format and check only the files you changed.

## Ground rules (from CLAUDE.md, AGENTS.md and owner instructions)

- **Commits:** never add a `Co-Authored-By` trailer; a global commit-msg hook rejects it. Use concise imperative subjects. Never `git add -A`; add paths explicitly. Pushing to `origin mcp` is allowed.
- **Protected M2h2 code and evidence:** don't modify protected M2h2 source, tests or fixtures (non-pivot `src/ai_kicad/m2*`, e.g. `m2_compose`, `m2b_observation.py`, `m2a_artifacts.py`). Never touch, clean or commit the untracked `fixtures/m2h2/*` folders.
- **Byte-exact evidence:** KiCad SVG and `.dat` files are hash-verified byte-exact. Don't reformat them.
- **Other fixtures:** don't modify `fixtures/m2b/timer_astable.json`.
- **Checks:** don't weaken acceptance checks to make a drawing pass.
- **During runs:** don't edit source while a corpus run or regeneration is running. A git worktree works for side changes.
- **Credentials:** don't commit captured home/config folders, such as the untracked `fixtures/pivot/experiments/*/home/` folders.
- **Fabrication:** no PCB fabrication orders without owner approval.

## Not in git (copy these by hand if you need them)

- **`CLAUDE.md` and `AGENTS.md`** at the repo root are **untracked**. Copy them to the new computer, or Claude Code there won't see the project instructions.
- **Claude Code memory** is in `~/.claude/projects/-home-jovyan-work-ai-kicad-designer/memory/` on this computer. It records the venv/KiCad paths, the no-Co-Authored-By rule, that `--experiment-id` is the full folder name, and that qwen35-256k is the review model. Everything important from it is repeated above.
- **The scratch helper scripts** (regenerate, crop) lived in a session scratchpad and are not kept. Recreate them from "How to run things".
