# M2h2 human-composition baseline render candidates

This is a **historical-baseline navigation aid**, not a current-source
qualification result, visual inspection, or closure record.

The preserved locked-KiCad native-render archive contains 90 SVG case renders,
under `fixtures/m2h2/finalization_checks/final_native_42ab8452/`
(parts 01–10). Its source-bound inventory and part hashes are recorded in
`fixtures/m2h2/human_composition_baseline_2026-10-08/native_render_archive_manifest_42ab8452.json`.
The archive belongs to historical qualification head
`42ab8452fca16592ead8f628b17980a9d34794b7`.

## Provisional archetype inspection targets

The following **case IDs were found in the archived render records**. Their
assignment is a selection hypothesis from the case family/design name, not
a finding from visual inspection. The independent observer and an engineering
render inspection must confirm each classification and record measured defects
before section 1 of the composition TODO can be checked.

| Archetype | Archived case ID | Part |
| --- | --- | ---: |
| Linear chain | `base__m2e1-amplifier_to_sallen_key` | 03 |
| Branch/fanout | `base__passive_two_level_fanout` | 04 |
| Feedback | `base__m2e1-amplifier_to_sallen_key` | 03 |
| Repeated channels | `i3__three_amplifier_one_band` | 08 |
| Shared rail | `base__m2f2-two_signal_chains_shared_rail` | 03 |
| Internal reference | `base__v6-3` | 05 |
| Multi-output | `base__timer_split_filtered_gain_indicator` | 04 |
| Long-field text | `i6__text_long_branch_1` | 09 |
| Structural one-band | `structural__three_amplifier_one_band` | 10 |
| Structural multi-band | `structural__a0_multiple` | 09 |
| Mixed interaction | `i4__b2_mixed` | 08 |

## Required follow-through

For each target, recover the SVG from its verified archive part, inspect
the native rendered geometry, and associate its independent semantic-flow,
ownership, interface, whitespace, and routing observations with the exact
render hash. Record per-case defects and exact witnesses, including the
`i4__b2_mixed` frontier, stage ownership, page bias, detours, and label-mediated
local disconnects. Rank hard defects before aesthetic preferences. Add
alternative examples where the selected case does not actually instantiate
the proposed archetype.

**Do not mark baseline characterization, targeted acceptance, five-run
qualification, or final closure PASS from this navigation aid.** Historical
electrical PASS remains untouched.

## Verified local extraction for engineering inspection

Run from the repository root:

```bash
python tools/extract_m2h2_baseline_renders.py \
  --output-dir /tmp/m2h2-historical-renders \
  --case i4__b2_mixed
```

Omit `--case` to extract and hash-check all 90 historical native SVGs. The
extractor verifies each original archive-part SHA-256 and each decompressed
SVG SHA-256, rejects unsafe case identifiers, and emits a deterministic
`index.json` with archive provenance and native canvas metadata. Archived
case names are *navigation identifiers only*, never production dispatch.
It deliberately does **not** assert a recovered visual defect, observer
metric, aesthetic PASS, or current-source native KiCad qualification; those
require independent geometry/semantic observation and engineering inspection.
