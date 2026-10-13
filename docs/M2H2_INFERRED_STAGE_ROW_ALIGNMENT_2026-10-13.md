# M2h2 generic inferred-stage row-alignment remediation — 2026-10-13

Status: investigation only; no visual acceptance claimed.

The current `src/ai_kicad/m2_composition_candidate_rank.py` computes
`sequential_stage_row_drift` only when both stage blocks explicitly expose
`signal_in` and `signal_out` port roles. The same ranking code already derives
signal relations from authored edges, precedence and inferred passive-terminal
flow. Consequently a uniquely directed one-to-one passive chain may be omitted
from the row-alignment preference even though its semantic order is known.

Proposed generic correction: permit inferred one-to-one intermediate stages
with exactly one incoming and one outgoing signal neighbor; keep interfaces,
fanout, convergence and single-ended cells exempt. Add deterministic precedence,
renaming, declaration-order, and fanout tests. This is a placement-ranking
hypothesis, not proof of the independent comparative visual criteria.

Latest qualified source: `f909475058724c190dce26a66e0943866d72f62f`.
Independent 90-case audit run 38344818593 still fails five frozen criteria;
normalized 137-case render inventory run 38344818965 passes. Re-run locked
KiCad 10.0.6 qualification and independent comparative audit after any
behavior-affecting implementation; leave canonical sections 15–21 open.
