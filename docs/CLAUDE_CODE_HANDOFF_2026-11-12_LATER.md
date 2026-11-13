# Handoff: P6-011b / P6-011f schematic readability (2026-11-12, later session)

Picks up from `docs/CLAUDE_CODE_HANDOFF_2026-11-12.md`. Branch `mcp`, pushed to `origin/mcp`. Last commit: `5a81f7b8`. Working tree is clean except `.serena/` (not ours) and one untracked failed run (see below).

## Ground rules (carry over)

- Never add a `Co-Authored-By` trailer. A global commit-msg hook rejects it. Use concise imperative subjects.
- Never `git add -A`. Add paths explicitly.
- Do not modify protected M2h2 source, tests or fixtures (non-pivot `src/ai_kicad/m2*`). Never touch or commit the untracked `fixtures/m2h2/*` folders.
- KiCad SVG and `.dat` files are hash-verified byte-exact. Do not reformat them.
- Do not modify `fixtures/m2b/timer_astable.json`.
- Do not weaken acceptance checks to make a drawing pass.
- Do not edit source while a corpus run or regeneration is running.
- Do not commit captured home/config folders (`fixtures/pivot/experiments/*/home/`). KiCad `config/` folders are fine.
- No PCB fabrication orders without owner approval.
- Do not restart Ollama yourself.
- `review_loop_corpus_v7_2026-11-12_qwen35_256k_run1` (TOOL_ERROR run, reviewer model missing): leave it untracked. Do not commit or delete it.
- Experiment folders are write-once, created via `tools/pivot/experiment_paths.create_experiment_dir`.
- Task checkboxes are checked only with real-tool evidence. P6-011f and P6-011b stay unchecked.

## Owner decisions in force

- U1C's label stays beside its pins. Under v7 it is placed beside the pin column, on either side.
- VPLUS on pin 8 may point sideways.
- PWR_FLAG diamonds stay where they are.
- Repeated same-name net labels are not acceptable for rails.
- Decoupling pairs must keep an explicit wire.
- Reviewer: `qwen35-256k:latest`, 262144 context, 2048 output (digest `b528609af3c0`).
- Rail detours: ratio 1.15 plus a minimum detour of 7.62 mm (option 1).
- Centre the drawing on the page, gated by `page_balance` (option A, brief v5).
- Text by the wrong part fails `field_nearest_owner`, with a 5.08 mm margin.
- Sideways ground fails when it could point down. Supply arrows may point sideways.
- Power-unit text is placed beside its pins on either side (brief v7).

## Where things are

Brief history (each is a Pydantic model with a JSON schema, in `src/ai_kicad/pivot/schematic_review_brief.py`):

| brief | adds | commit |
|---|---|---|
| v3 | power symbols for rails | earlier |
| v4 | bodyless-unit clearance, rail detour, power-symbol direction | `65286870` |
| v5 | centring and `page_balance` | `3dc5252c` |
| v6 | `field_nearest_owner` | `3b22ea61` |
| v7 | `field_wire_separation`, `ground_symbol_direction`, power-unit text beside pins | `62d0bc5c` |

Corpus runs (15 designs, all accepted on first review, no rejected replies):

| run | brief | commit | notes |
|---|---|---|---|
| `review_loop_corpus_v4_2026-11-12_qwen35_256k_run1` | v4 | `2107b0e4` | |
| `review_loop_corpus_v5_2026-11-12_qwen35_256k_run1` | v5 | `7c8e2348` | centred drawings |
| `review_loop_corpus_v7_2026-11-12_qwen35_256k_run2` | v7 | `5a81f7b8` | inverting_gain's U1C label moved; others identical to v5 |
| `review_loop_corpus_v7_2026-11-12_qwen35_256k_run1` | v7 | not committed | TOOL_ERROR: reviewer model had been removed from Ollama. Untracked, do not use. |

Qualification (no model review, KiCad check of 61 cases):
- `readability_gates_v4_2026-11-12_run1`
- `field_ownership_v6_2026-11-12_run1`
- `text_and_ground_v7_qualification_2026-11-12_run1`

Drawing evidence:
- `page_centring_2026-11-12_run1` (v5)
- `text_and_ground_v7_2026-11-12_run1` (v7)

Every qualification defect fails at least one gate, except four injected off-balance pages, which fail only `page_balance`. Under v7 all 15 accepted drawings pass every check.

Test state at `a2c7d198` / `5a81f7b8`: `tests/pivot` with `AI_KICAD_APPRUN=/tmp/AppDir/AppRun` gives 437 passed, 11 failed. The 11 failures are the known environment ones: `test_direct_backend.py` (10, desktop KiCad CLI paths) and `test_engineering.py::test_real_ngspice_transient_matches_analytical_limit` (desktop ngspice path).

## Environment notes

- `/tmp` is cleared on reboot. After a reboot, redo the KiCad AppDir provisioning (see memory `kicad-appdir-provisioning`). Downloaded tar SHA256 `c05fa676…` matches the mirror. `--appimage-extract` writes `squashfs-root`; move it to `/tmp/AppDir` (a bare `mv` into an existing path made a symlink loop once).
- Ollama models live under `/usr/share/ollama/.ollama/models`. The store was empty after the reboot until the owner restored `qwen35-256k`. Check `curl localhost:11434/api/tags` before any run.
- `scratchpad` helpers (`compare_run.py`, `regen7.py`, `evidence_v7.py`, etc.) may be gone. They are not needed to reproduce results; the commands are in the README files.

## Open items

1. **Option C / minimum fill (owner chose option a: fail a drawing that is too small).** Not implemented. Blocking decision: the threshold, and what happens to a failing drawing.
   - Measured frame use (bounding-box area) of the 15 accepted v7 drawings: led_series 4.1%, led_long_text 5.7%, led_reverse_supply 6.0%, rc_lowpass and rc_highpass 10.7%, linear_regulator 12.2%, dual_buffer 12.9%, reference_555_led_flasher_v8 14.5%, and 22–39% for the other eight.
   - A 15% threshold would fail seven accepted drawings. A failing drawing needs either a compiler layout change (spread the parts) or a smaller sheet size. The engine currently has only A4.
   - Ask the owner: which threshold, and rework (compiler) or smaller sheet.

2. **Own-wiring loops (owner chose option a: add a gate).** Not implemented. Proposed definition: a wire of the part's own net that runs between the part's label and its body. Examples: J1's pin-1 wire looping over the connector in `linear_regulator` and `sallen_key`, and C2's top wire in `dual_rail_reference`. Check the definition against the 15 accepted drawings before any compiler change. Adding it is a new gate, so it means a v8 brief and a qualification run.

3. **Human readability and electrical review.** Still needed. P6-011b cannot be checked without it. The model review adds no independent check: its comments are generic, and every accepted drawing is accepted on first pass.

4. **Model review of later changes.** Any change to the compiler or a gate needs a new corpus run. Use a new `_runN` folder.

## Suggested next steps

1. Get the owner's threshold and rework-or-smaller-sheet decision for option C.
2. Implement the own-wiring loop gate as a v8 brief. Check it on the accepted drawings first.
3. Rerun the qualification and the corpus under the new brief, and record evidence in new write-once folders.
4. Schedule the human readability review. Do not check P6-011b until it is done.
