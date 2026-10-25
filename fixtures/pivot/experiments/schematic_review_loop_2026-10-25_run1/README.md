# Native schematic / Ollama review loop demonstration

The final runs use source `df0f263604053ecbb1d6b915f1835bf412a5b819`,
KiCad 10.0.6 and local Qwen 3.5 9B with vision. Each model call receives the
complete page, a drawing close-up, the intended circuit and independent checks.
All edits and subsequent reviews below ran without manual repair between calls.

| Final run | Initial condition | Automatic behavior | Reviews |
|---|---|---|---:|
| [RC wiring](rc_wiring_locked/result.json) | Missing wire and overlapping J1 fields | Model requested regeneration; new native candidate passed checks and image review | 2 |
| [RC labels](rc_labels_locked/result.json) | C1 value stranded 77.37 mm from its symbol | Model requested field moves; overlap checks rejected placements and one invalid reference was rejected; subsequent corrections passed | 5 |
| [LED generation](led_locked/result.json) | Intended circuit only | Generated and independently checked native schematic, then model image review accepted it | 1 |
| [555 generation](timer_locked_libraries/result.json) | Intended 10-component reference circuit | Generated and checked native schematic with isolated locked libraries, then model image review accepted it | 1 |

The RC wiring demonstration intentionally removes a wire from a generated
schematic and overlays J1's reference/value. The separate label demonstration
intentionally moves only C1's value. Input bytes, defect descriptions and hashes
are retained under [inputs](inputs/). The model cannot modify the intended values
or connectivity; regeneration rebuilds from that intended circuit.

Before/after RC label close-ups:

- [Before](rc_labels_locked/candidates/000/review-images/drawing.png)
- [After](rc_labels_locked/candidates/004/review-images/drawing.png)

The RC label case is a real feedback loop: the first proposed move overlapped
the C1 reference, a later request used `C1:1.Value` as a reference and was rejected,
and another placement still overlapped. The controller returned those errors to
the model and accepted only the separately checked and re-reviewed final revision.

## What these results establish

The supported generation/check/render/review/edit/recheck loop executes end to end.
All six independent gates pass for the final four accepted candidates. Each final
model acceptance names the exact schematic SHA-256 and has no remaining issues or
actions. Reports, images, raw responses, token/time usage and intermediate rejected
candidates remain available. The pivot test suite passes **129/129**; Ruff and
format checks pass for the changed implementation and tests.

`ACCEPTED_FOR_REVIEW` is scoped software/model evidence. The intended circuit's
engineering validity, independent human electrical review, and locked-host
qualification are separate gates. The model's wording in raw responses is data,
not a manufacturing or electrical approval.

## Failures and limits retained

- `rc_visual_only`: the earlier model accepted the deliberately detached value
  despite a proximity brief when no locality gate existed. This is a **visual
  detection failure**. The generalized field-locality gate now prevents that
  particular geometric defect from passing, regardless of model approval.
- `rc_visual_thinking`: six responses hit the 4096-token output limit without an
  actionable JSON review. The budget stopped the run with no accepted artifact.
  The implementation now also stops repeated invalid replies sooner.
- `timer_generated`: the first 555 run stopped on repeated ERC library warnings.
  It was not accepted. Isolated registration of the exact locked symbol libraries
  fixes that backend configuration issue in `timer_locked_libraries`.
- `rc_corrupted`: an early prototype repaired the electrical defect, but its
  close-up included the page background. Later runs correct the crop.
- The final 555 render still uses several REF/VCC labels. Its model acceptance
  **does not establish that it meets the owner's earlier preference for continuous
  visible rails**. The current supported edits cannot generally reroute arbitrary
  symbol groups or join all local power/reference branches. Broader visual judgment
  and wiring-style remediation remain open work.

The model can request field placement, whole-sheet translation and regeneration.
It has no arbitrary file/shell access. The controller preserves every candidate,
rechecks each change, rejects stale artifacts, and stops on budgets, cycles,
unsupported requests or a request for help.

## Verification and reproduction

```bash
uv run python fixtures/pivot/experiments/schematic_review_loop_2026-10-25_run1/verify_evidence.py
```

This verifies run manifests, the exact source implementation blobs, image hashes,
test report and final native/review revision matches, then writes `summary.json`.
The run manifests record all native/tool/model artifacts. Use
`tools/pivot/review_schematic.py` with these retained inputs and a new output
directory to reproduce a run; see `docs/pivot/SCHEMATIC_REVIEW_LOOP.md` for arguments.
