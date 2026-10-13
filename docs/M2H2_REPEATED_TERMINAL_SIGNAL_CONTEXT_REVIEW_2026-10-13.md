# Terminal-inferred signal context in repeated-stage ranking — 2026-10-13

Status: **source correction implemented and exact-head Fast Validation passed; full visual acceptance unproven**.

Implementation: `bab8a5f033b5ada900389def1d3642c987a30ba8` updated
`_block_semantic_signature` to include the same deduplicated generic signal
relations as production flow ranking, including uniquely inferred passive
terminal connections. Added metamorphic regressions for unmatched/matched
output terminals, shared passive ambiguity, net renaming, declaration order,
and authored-plus-inferred equivalent edge annotations.

Qualification: [Fast Validation 38370298212](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38370298212)
**PASS, all three jobs**, and [locked toolchain 38370298298](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38370298298)
**PASS**. Full five-run current-source qualification and independent
native comparative audit were not executed by these checks. Historical
comparison still has five failed frozen visual acceptance criteria. This
review does not waive any visual gate or change historical evidence.

The current `src/ai_kicad/m2_composition_candidate_rank.py` derives
`_signal_relations(plan)` from authored signal/branch edges, precedence, and
`inferred_passive_interface_signal_relations(plan)`. But
`_block_semantic_signature(plan, block_id)`, used by
`_repeated_alignment_penalty`, builds incident context only from authored
edges and precedence. Therefore two otherwise identical signal-output cells,
one connected to a uniquely inferred passive output terminal and the other
unconnected, can be classified as repeated peers. This may impose an
unjustified alignment penalty.

Proposed generic correction: pass the already-computed signal relations to
`_block_semantic_signature` and add normalized `("out", "signal", target)`
and `("in", "signal", source)` incident links, deduplicating with the
existing incident-link set. Keep non-signal authored edge kinds unchanged.

Required regression: compare two identical filter cells with `signal_out`
ports on distinct nets, first with a uniquely attached passive interface,
second without an interface. They must not be treated as repeated peers.
Adding a matching passive interface to the second net must restore repeated
peer alignment, and equivalent authored signal/branch annotations must
not double-count it. Verify declaration-order and net-renaming invariance.

This is not a claim that the five frozen failed historical comparative
criteria are fixed. A behavior change requires exact-head Fast Validation,
locked KiCad 10.0.6 five-run base/V3-8, I1–I6 and structural qualification,
then independent 90-case comparison, native render inventory, and
engineering inspection. Do not change frozen tolerances or historical evidence.
