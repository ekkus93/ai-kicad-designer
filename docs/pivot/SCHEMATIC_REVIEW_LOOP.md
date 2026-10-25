# Automatic schematic image review

The schematic review loop generates a native KiCad schematic, checks its saved
electrical and geometric content, sends rendered images to a local vision model,
applies supported edits, and reviews the new revision again. No manual changes
are needed between these steps.

## Run

From the repository root, with local Ollama, the pinned KiCad 10.0.6 AppImage
extracted, `rsvg-convert`, and ImageMagick `convert` available:

```bash
PYTHONPATH=src:. uv run python tools/pivot/review_schematic.py \
  --design fixtures/m2b/rc_lowpass.json \
  --kicad-apprun /home/phil/Applications/kicad-10.0.6/AppDir/AppRun \
  --model qwen3.5:9b \
  --output /tmp/rc-schematic-review \
  --max-reviews 6
```

Add `--source /path/to/Existing.kicad_sch` to review and repair an existing
schematic against the intended circuit supplied by `--design`. Output must be a
new directory. Original source files are never overwritten. The intended circuit
uses the repository's supported M2b IR and locked symbol assets.

Use `--review-brief /path/to/readability-requirements.txt` to provide the user's
visual criteria, such as connecting nearby return terminals with visible wires
or keeping component labels close to their symbols. The brief is included in the
logged model instructions. When the independent gates already pass, the model
can still request supported visual edits to satisfy that brief.

The independent field-locality gate limits the distance between a visible field
envelope and its own symbol anchor to 25.4 mm by default. Change this explicit
readability constraint with `--max-field-distance-mm` when a design requires it.
It applies to every component and is separate from field overlap checks.

The default model call uses an explicit 16,384-token context, 2,048 output tokens,
temperature zero and thinking disabled. `--think` enables model thinking and
raises the output allowance to 4,096. The installed tag's digest, capabilities,
Ollama version and exact sampling settings are recorded. Vision capability is
required; schematic images are attached to the model request.

## Edit and acceptance contract

The model sees the whole page, a cropped drawing image, intended circuit,
independent ERC/connectivity/layout reports, reference/value field coordinates,
and the SHA-256 of the schematic it reviewed. It can request:

- `move_field`: position an existing Reference or Value field for a specific unit.
- `translate_sheet`: move the complete drawing, including symbols, wires and text.
- `regenerate_schematic`: rebuild placement and wiring from the intended circuit.
  This can repair missing parts, wrong serialized values, disconnected wires and
  layout corruption while retaining the intended electrical design.

Changes are applied to isolated native candidates. The loop reruns KiCad checks,
independent comparison, layout observation and image rendering before requesting
another review. The model cannot accept a revision with failing checks, unresolved
issues, pending edits, or a stale hash. It cannot change the intended circuit,
execute shell commands, or overwrite the input schematic.

`ACCEPTED_FOR_REVIEW` identifies a candidate that passed the independent checks
and was then accepted by the model after viewing its current images. This does
not establish electrical correctness of the intended circuit itself; that still
requires the project's calculation/simulation and human electrical review gates.

Other outcomes are `NEEDS_HELP`, `NO_PROGRESS`, `LIMIT_REACHED`, or `TOOL_ERROR`.
Review count, wall-clock and model-token budgets prevent endless iteration. A
repeated invalid reply also stops as `NO_PROGRESS`. A
subprocess/model request has its own timeout; budget checks run between operations
and prevent acceptance after the total budget has expired. Every candidate is
retained, including regressions. `best_passing_schematic` is an independently
passing fallback, while `accepted_schematic` is set only after joint acceptance.

## Evidence and scope

`result.json` records decisions, rejected replies, edits, stop reason, budgets,
and accepted/fallback paths. `reviews/` retains prompts, model responses, usage,
and hashes of the images sent. `candidates/` retains native files, page/detail
images, native-tool logs and independent reports. `manifest.json` records exact
source/implementation, toolchain and artifact hashes. Exit status is zero only
for `ACCEPTED_FOR_REVIEW`.

The initial scope is supported single-sheet M2b circuits. General symbol moves
with new routing, arbitrary circuit synthesis/part substitution, unsupported
native constructs and hierarchy stop for additional implementation or a human
decision. The loop is a direct native backend client; it does not use Ralph Bridge.

The v5 555 generation prompt was found to contain conflicting LED resistor
guidance. Its runs remain historical records with this limitation; the corrected
suite is `fixtures/pivot/heldout_topology_suite_v6_555.json`. That separate circuit
generation benchmark is not evidence that this schematic image loop converges.

Initial live probing found that Qwen could accept a visually detached value label
when only electrical/collision checks passed. That false acceptance is preserved
in the experiment evidence. The locality gate was added so this geometric defect
cannot be overridden by model approval. Model visual judgment alone remains
insufficient for certifying all aesthetic or readability concerns.
