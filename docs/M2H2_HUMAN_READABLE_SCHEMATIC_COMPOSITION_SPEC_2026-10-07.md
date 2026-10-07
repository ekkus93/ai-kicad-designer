# M2h2 Human-Readable Schematic Composition Specification — 2026-10-07

## 1. Purpose

M2h2 has already demonstrated that the current generator can produce electrically valid, independently observed, reproducible KiCad schematics under the governing geometry, routing, locality, ERC, and anti-overfitting constraints.

That result is necessary but not sufficient for human-readable schematic composition.

The motivating defect is visible in final-pass artifacts such as `i4__b2_mixed`: the emitted schematic is electrically correct and collision-free, yet it still exhibits weak engineering composition. Inputs, outputs, branch structure, page use, whitespace, connector placement, support structure, and visual flow do not consistently read like a schematic deliberately composed by a competent engineer.

This remediation therefore adds a stricter presentation-quality objective:

> Produce schematics whose **electrical meaning is visually legible from placement and routing**, not merely recoverable from labels and connectivity.

The target is not artistic styling. The target is conventional, compact, predictable engineering communication: a reader should be able to identify signal entry, signal progression, branching, feedback, support circuitry, supply/reference structure, and final outputs quickly and with minimal tracing effort.

This work is an additive post-M2h2 hardening phase. It does **not** revoke or rewrite the historical M2h2 PASS evidence. Instead it establishes an additional composition-quality acceptance contract that must preserve every existing M2h2 invariant.

## 2. Authority and relationship to existing M2h2 requirements

Use these documents in this order:

1. `docs/M2_GENERALIZATION_REMEDIATION_SPEC.md` — governing M2 technical requirements and hard invariants.
2. `docs/M2H2_FINALIZATION_SPEC_2026-09-27.md` — completed M2h2 execution and qualification contract.
3. `docs/M2H2_HUMAN_READABLE_SCHEMATIC_COMPOSITION_SPEC_2026-10-07.md` — this additive composition-quality contract.
4. `docs/M2H2_HUMAN_READABLE_SCHEMATIC_COMPOSITION_TODO_2026-10-07.md` — canonical executable checklist for this remediation.
5. `fixtures/m2h2/STATUS.md` — material status and historical finalization evidence.

If this specification conflicts with a hard requirement in the governing remediation specification or the completed M2h2 finalization contract, the existing hard requirement wins.

The existing M2h2 PASS remains valid as an electrical/correctness milestone. This remediation defines a new, stricter acceptance state: **M2h2 human-readable composition PASS**.

## 3. Problem statement

A schematic can pass all existing M2h2 gates and still be visually poor.

Examples of unacceptable composition include:

- placing an input connector on the left but placing its corresponding output connectors on the same side while the actual output stages are on the right;
- using remote net labels to bridge visually related circuitry when direct local placement would be clearer;
- placing a small circuit into a tiny patch of a large sheet without any complexity-based reason;
- leaving large accidental voids or rectangular routing detours that dominate the drawing;
- scattering support parts away from the stage or package they support;
- arranging repeated channels with inconsistent rows, columns, orientation, or spacing;
- placing supply/reference infrastructure so that it competes visually with the primary signal path;
- allowing feedback loops, branches, fanout, or shared rails to be electrically correct but visually ambiguous;
- using inconsistent value/reference-field orientation or alignment;
- satisfying absolute path-length limits while still choosing obviously inferior, bend-heavy, visually indirect routes.

The final-pass `i4__b2_mixed` artifact is an explicit **falsification seed** because it demonstrates several of these defects simultaneously. It must not become a benchmark-specific special case. The implementation may not inspect or dispatch on that case name, fixture identity, refdes inventory, literal net names, or exact topology hash.

## 4. Hard boundaries

This remediation must preserve all completed M2h2 guarantees.

- M2h2 scope only. Do not begin M3.
- Do not create or use corpus.v7.
- Do not introduce CP-SAT.
- Preserve the 210 × 140 mm spread gate.
- Preserve the 80 mm local-path gate.
- Preserve the 60 mm support/locality gate where applicable.
- Preserve the 250 mm canonical conductor-length gate.
- Do not weaken ERC.
- Do not weaken independent emitted-artifact observation.
- Preserve DP1–DP4 topology and all frozen expectations.
- Preserve all historical blind/evaluation evidence.
- Do not modify or overwrite historical qualification roots.
- Ignore `.local/`.
- Do not inspect or use `research/legacy_openclaw/`.
- Use locked KiCad 10.0.6 for governed real-tool qualification.
- Do not add fixture-specific, case-specific, refdes-specific, literal-net-specific, exact-inventory-specific, or topology-hash-specific layout logic.
- Do not accept a visual improvement that regresses electrical correctness, package/unit/pin identity, canonical graph correctness, routing legality, locality, page spread, required-field readability, or reproducibility.

## 5. Objective hierarchy

The placer/router must optimize lexicographically in this order:

1. **Electrical correctness and semantic topology.**
2. **Existing M2h2 hard geometry, locality, routing, ERC, and artifact-observation invariants.**
3. **Human semantic readability.**
4. **Routing clarity and visual traceability.**
5. **Compactness and whitespace quality.**
6. **Aesthetic tie-breakers.**

A lower-ranked objective may never be improved by violating a higher-ranked one.

In particular:

- a prettier layout with an ERC defect is a failure;
- a more compact layout that breaks local support constraints is a failure;
- a shorter wire that reverses semantic signal order is a failure;
- a layout with a better aggregate score but an obvious connector-side or stage-flow violation is a failure.

No single weighted “beauty score” is sufficient for acceptance. The system must expose individual semantic metrics and hard anti-pathology gates.

## 6. Composition model

### 6.1 Semantic flow graph

Build an implementation-independent directed semantic-flow graph from the authored design semantics and independently observable terminal roles.

Nodes represent functional stages or interfaces, not individual drawing coordinates.

Edges represent meaningful signal progression, including:

- external input to first consuming stage;
- stage output to downstream stage;
- branch/fanout source to consumers;
- amplifier output to feedback network and return terminal;
- regulator/reference producer to consumers;
- shared rail distribution;
- explicit final-stage output to external output interface.

Power, reference, return, support, and signal roles must remain distinguishable.

The generator may use its own internal representation, but final acceptance must be checked by an independently authored observer that does not trust generator placement scores.

### 6.2 Functional blocks

A functional block is a semantically related set such as:

- input interface;
- amplifier stage;
- filter stage;
- feedback network;
- timing network;
- regulator/reference producer;
- package support/decoupling;
- branch/fanout cluster;
- output interface;
- repeated channel.

Blocks are discovered from semantics and connectivity. They must not be inferred from fixture names.

### 6.3 Visual ownership

Every support or secondary structure must have an owning semantic block or explicit shared role.

Examples:

- an amplifier feedback resistor belongs visually to that amplifier stage;
- a local decoupling capacitor belongs to its package/supply context;
- a shared reference producer belongs to shared infrastructure, not arbitrarily to the nearest stage;
- an output connector belongs to the terminal stage whose externally visible signal it exposes.

This ownership drives grouping and locality preferences but may not override hard routing feasibility.

## 7. Required composition principles

### 7.1 Primary signal flow

For designs with a directed primary signal path:

- external inputs should preferentially occupy the left visual frontier;
- final external outputs should preferentially occupy the right visual frontier;
- intermediate stages should progress monotonically left-to-right unless a real semantic dependency requires otherwise;
- vertical arrangement may encode parallel channels, branches, or support structure;
- arbitrary backtracking of the main signal path is disfavored and must be justified by a higher-priority hard constraint.

The observer must report semantic stage-order inversions and primary-flow reversal distance.

### 7.2 Interface placement

External interfaces must visually correspond to their role.

- input connectors should be near the first consumer they feed;
- output connectors should be near the final producer whose signal they expose;
- power-input connectors should be grouped with supply infrastructure rather than mixed into the signal-flow row;
- bidirectional or ambiguous interfaces are exempt from left/right polarity rules only when their semantics genuinely lack a direction;
- an output connector on the input side of the drawing requires an explicit semantic/constraint justification in evidence.

Remote net labels must not be used as a substitute for sensible interface placement when a legal local arrangement exists.

### 7.3 Stage grouping

Components forming one functional stage should read as one visual unit.

Required properties:

- low intra-block dispersion;
- clear separation from unrelated neighboring blocks;
- feedback/support parts close to their owning active device;
- natural local ordering of series/passive chains;
- no isolated stage member placed across the sheet merely because labels preserve connectivity.

### 7.4 Branch and fanout readability

When a signal branches:

- the branch point should be visually identifiable;
- sibling branches should separate cleanly;
- parallel branches should use consistent geometry where practical;
- fanout should not create unnecessary crossings or long detours;
- branch outputs should remain attributable to the source without relying on distant labels.

### 7.5 Feedback readability

Feedback structures must visually communicate feedback.

- feedback parts should remain near the owning amplifier/comparator/control stage;
- the feedback path should not be visually confused with forward signal flow;
- the loop should avoid crossing unrelated blocks;
- local feedback should not be routed around the page solely to satisfy generic packing.

### 7.6 Power and reference composition

Power/reference infrastructure must be visually coherent but subordinate to primary signal flow.

- shared rails should form recognizable infrastructure rather than scattered disconnected visual fragments;
- internal reference producers should be grouped with their support network and distribution origin;
- per-package support should remain local to the package where semantics permit;
- parked package units and required power pins must remain understandable without dominating the signal diagram;
- reference and supply nets must remain visually distinguishable from ordinary signal nets.

### 7.7 Repeated structures

Repeated channels/stages should use consistent visual grammar.

Measure and minimize:

- row/column alignment variance;
- orientation variance;
- pitch variance;
- corresponding-component displacement variance;
- inconsistent branch geometry;
- arbitrary permutation of otherwise equivalent channels.

Equivalent repeated structures should look intentionally repeated.

### 7.8 Alignment and grid discipline

The layout should prefer a small number of meaningful alignment lines.

- active stages in one flow should share a baseline/centerline where practical;
- repeated passives should align by role;
- connector pins/interfaces should align with the signal rows they serve;
- support structures should align locally rather than float at arbitrary offsets;
- use KiCad-compatible grid positions throughout.

Alignment is a preference after hard legality, not a reason to force overlaps or violate locality.

### 7.9 Page utilization and whitespace

The 210 × 140 mm gate is a maximum envelope, not a target size.

The system must avoid pathological under-utilization and accidental empty space.

The independent observer must report at least:

- content bounding-box width/height/area;
- occupied-area ratio against the allowed 210 × 140 mm composition envelope;
- horizontal and vertical whitespace imbalance;
- largest internal empty corridor/void attributable to placement rather than intentional block separation;
- distance from content centroid to composition-envelope centroid;
- edge bias.

Acceptance thresholds must be **complexity-aware**. A three-symbol probe must not be forced to fill the page, while a multi-stage circuit may not occupy a tiny upper-left patch without justification.

Before final implementation qualification, freeze complexity bands using semantic block count, visible symbol count, and edge count. At minimum:

- tiny cases are exempt from minimum utilization gates but still checked for edge bias and needless dispersion;
- small/medium cases must meet a frozen minimum utilization or compactness bound;
- dense cases must demonstrate balanced use of available space without violating the 210 × 140 mm maximum.

Thresholds must be frozen from general corpus statistics and independent engineering inspection, not tuned per fixture.

### 7.10 Text and required fields

Human-readable composition includes field placement.

- references and values must use consistent orientation for comparable component roles;
- fields should align with their owning symbol and neighboring repeated structure;
- long fields must not force excessive block spacing when a legal alternate field slot/orientation exists;
- required fields must remain clear of bodies, wires, labels, borders, and unrelated fields under the existing independent observer;
- field placement must remain deterministic.

### 7.11 Routing aesthetics

Existing routing limits remain hard ceilings. This remediation adds preference for clearer routes below those ceilings.

Measure and minimize, after legality:

- avoidable bend count;
- avoidable wire length relative to a legal semantic-local baseline;
- unrelated wire crossings;
- visually unnecessary U-shaped or rectangular detours;
- route excursions through unrelated blocks;
- inconsistent sibling-branch geometry;
- label-mediated visual discontinuity where direct routing is reasonably local and legal.

Do not reduce bend count by obscuring topology or collapsing semantically important branch structure.

### 7.12 Net-label discipline

Net labels are valid schematic tools, but they should not conceal local semantic relationships.

Prefer direct visible connectivity when:

- producer and consumer are in the same local functional region;
- direct routing is legal and does not create a worse crossing/collision;
- the direct path clarifies stage flow.

Prefer labels when:

- the net is genuinely global/shared;
- a direct wire would cross unrelated functional regions;
- repeated distribution would otherwise dominate the sheet;
- supply/reference semantics are clearer as named infrastructure.

The observer must report a “label-mediated local disconnect” when two locally related blocks are separated visually only by a label despite a legal local composition alternative.

## 8. Independent composition observer

Add an independently authored post-emission composition observer.

It must consume:

- authored semantic design information;
- emitted KiCad schematic/project artifacts;
- native/normalized KiCad render geometry where needed;
- independently recovered symbol/terminal/connectivity facts.

It must **not** use generator-internal placement scores, candidate ranks, or self-declared aesthetic success as proof.

Required reported metrics include at least:

- primary stage-order inversion count;
- cumulative primary-flow reversal distance;
- input-side violations;
- output-side violations;
- interface-to-owning-stage distance;
- functional-block dispersion;
- functional-block fragmentation count;
- support-to-owner distance;
- feedback-loop span and unrelated-block intrusion;
- repeated-structure alignment/orientation/pitch variance;
- content width/height/area and utilization;
- whitespace/edge-bias metrics;
- bend count and normalized bend excess;
- routed length and normalized length excess;
- unrelated crossing count;
- local label-mediated disconnect count;
- required-field alignment/clearance metrics;
- supply/reference infrastructure dispersion.

The observer must record exact semantic witnesses for every violation, not only aggregate counts.

## 9. Independent oracles and falsification

### 9.1 Tiny exhaustive placement oracle

For bounded synthetic layouts, independently enumerate all legal placements on a reduced grid and compute the lexicographic composition objective.

Use this to falsify:

- stage ordering;
- connector side semantics;
- grouping penalties;
- repeated-structure alignment;
- compactness/whitespace scoring;
- routing-aesthetic lower bounds where tractable.

The production placer need not match the oracle’s exact coordinates. It must not select a candidate dominated by another legal candidate under the governed lexicographic objective unless the production search budget legitimately excludes that candidate and records the witness.

### 9.2 Graph-order oracle

Independently derive semantic partial orders and validate that visual order respects them.

Include:

- linear chains;
- siblings that must remain incomparable;
- branch/fanout;
- feedback cycles where only the forward path is ordered;
- power/reference edges excluded from signal precedence;
- external terminal-backed sources;
- multiple outputs.

### 9.3 Metamorphic falsification

The composition must remain semantically stable under:

- refdes renaming;
- literal net renaming;
- insertion-order changes;
- set/dictionary ordering changes;
- equivalent wire segmentation;
- equivalent symbol UUID regeneration where supported;
- mirrored naming of repeated channels;
- permutation of independent repeated-channel declaration order.

These transformations may change exact coordinates only when tie-breaking permits equivalent solutions. They must not change semantic side assignment, block grouping, stage order, or relative composition quality.

### 9.4 Negative mutation tests

Independently mutate emitted scenes/artifacts to introduce:

- an output connector moved to the input frontier;
- stage-order inversion;
- isolated support part;
- separated feedback network;
- excessive empty gap;
- misaligned repeated channel;
- avoidable local label disconnect;
- needless detour;
- field/body or field/wire readability regression.

The observer must reject the mutations.

## 10. Baseline characterization

Before changing behavior:

1. preserve current M2h2 PASS evidence;
2. record current master/source hashes;
3. evaluate the final M2h2 native-render archive with the new composition observer;
4. produce a ranked defect inventory;
5. explicitly include `i4__b2_mixed` as one observed defect example;
6. identify additional failure archetypes from the corpus without turning them into fixture-specific rules;
7. freeze the composition metric schema before final qualification.

The baseline is expected to fail the new composition standard. That does not invalidate historical M2h2 PASS.

## 11. Qualification archetypes

The remediation must cover, at minimum:

- simple linear signal chains;
- multi-stage amplifier/filter chains;
- branch/fanout;
- feedback amplifier/control loops;
- repeated parallel channels;
- multiple outputs;
- shared power rails;
- internal references;
- multi-consumer supply/reference distribution;
- dual-regulator/mixed-load structures;
- passive two-level fanout;
- timers/control structures;
- one-band and multi-band structural cases;
- long-field text cases;
- package-shared units;
- mixed interaction cases combining several of the above.

`i4__b2_mixed`, the two-signal-chains/shared-rail case, V6-3, the three-amplifier structural case, passive fanout, and long-field cases should be retained as named **regression evidence**, but no production branch may depend on those names.

## 12. Search and objective requirements

The production layout search must expose composition decisions in evidence.

Required behavior:

- candidate ranking follows the objective hierarchy in Section 5;
- semantic readability penalties are computed from generic roles/graphs;
- candidate comparison is deterministic;
- ties use stable generic tie-breakers;
- repair/search budgets do not silently reset;
- repeated candidate states are deduplicated;
- best rejected candidates preserve their composition metrics and rejection reason;
- the final candidate records a metric vector sufficient to explain why it beat alternatives.

The search must consider meaningful alternatives for at least:

- interface side/frontier assignment;
- semantic block ordering;
- repeated-channel row/column arrangement;
- support placement;
- field-slot choice;
- branch geometry;
- route topology where multiple legal trees exist.

Do not introduce unbounded combinatorial search.

## 13. Anti-overfitting requirements

Add structural and literal audits covering all production modules touched by this remediation.

Reject production control flow based on:

- fixture/case IDs;
- qualification group names;
- exact refdes strings;
- literal benchmark net names;
- exact component inventories;
- exact known topology hashes;
- expected image dimensions or precomputed coordinates for known tests;
- hardcoded coordinates derived from current final renders.

A generic semantic role such as “external output interface” is allowed. A condition such as “if case is i4__b2_mixed” is not.

The audit must also detect suspicious benchmark tables or per-case coordinate maps stored outside obvious control flow.

## 14. Acceptance gates

A case passes human-readable composition only when all applicable hard gates pass and no unresolved composition defect remains.

### 14.1 Existing correctness gates

Every governed case must continue to pass:

- locked KiCad 10.0.6 generation/opening/check flow;
- exact package/unit/pin identity;
- independent electrical partition observation;
- zero unexpected ERC violations;
- serialized-scene verification;
- existing route/locality/spread/conductor-length limits;
- required-field/body/wire/label clearance;
- historical preservation and anti-overfitting requirements.

### 14.2 Composition anti-pathology gates

The frozen observer must reject, where semantically applicable:

- primary stage-order inversion;
- unjustified input/output side reversal;
- detached local interface ownership;
- fragmented functional block;
- support placement outside governed ownership/locality expectation;
- visually misleading feedback placement;
- pathological page under-utilization for non-tiny cases;
- gross whitespace/edge bias;
- repeated-structure misalignment beyond frozen tolerance;
- avoidable local label disconnect above frozen tolerance;
- route detour/bend excess above frozen tolerance;
- unresolved text/value/reference alignment or readability defect.

### 14.3 Comparative improvement

For the baseline corpus:

- every previously identified hard composition defect must be fixed or have an evidence-backed semantic/hard-constraint justification;
- no previously good composition dimension may materially regress without a higher-priority justification;
- aggregate corpus metrics must improve in the expected direction, but aggregate improvement cannot hide an individual hard defect.

## 15. Native-render engineering inspection

Machine metrics are necessary but not sufficient.

After final-source qualification:

- generate native KiCad renders;
- inspect at least one representative final render for every distinct governed case;
- explicitly inspect all mixed/high-density, repeated-channel, feedback, shared-rail/reference, long-field, and structural cases;
- record inspection as engineering/agent inspection, not as user approval.

The rubric must answer, for every applicable case:

1. Is the primary signal entry obvious?
2. Is primary signal progression obvious without hunting through labels?
3. Are final outputs visually associated with final producing stages?
4. Are branches/fanout visually attributable to their source?
5. Is feedback visually recognizable as feedback?
6. Are power/reference structures coherent and subordinate?
7. Are support components clearly associated with owners?
8. Are repeated channels visually consistent?
9. Is the circuit compact without feeling cramped?
10. Is whitespace intentional rather than accidental?
11. Are labels/fields aligned and readable?
12. Are there any obvious “computer-generated” placement artifacts that the numeric gates missed?

Any obvious hard readability defect falsifies the candidate and requires correction plus fresh affected qualification.

## 16. Reproducibility

For every governed repeated qualification:

- five clean builds where the M2h2 finalization already requires five;
- deterministic semantic composition class;
- deterministic metric vector after documented normalization;
- deterministic project bytes where already governed;
- deterministic normalized native-render geometry;
- no run-to-run random connector-side, block-order, support-placement, or route-class drift.

If several layouts are intentionally equivalent, the implementation must still choose deterministically under stable tie-breakers.

## 17. Final qualification

After behavior-affecting source stabilization, run fresh current-source qualification.

At minimum:

- all existing 56 positive M2h2 base cases ×5;
- the historical V3-8 negative;
- all existing required I1–I6 interaction cases ×5;
- all required structural classes ×5;
- targeted composition regressions for the identified baseline defects;
- tiny-oracle and graph-oracle suites;
- metamorphic anti-overfitting suite;
- independent composition-observer suite;
- native-render inspection.

A behavior-affecting source change invalidates affected qualification evidence.

## 18. Evidence requirements

Use new roots beneath `fixtures/m2h2/` without overwriting historical evidence.

Recommended roots include:

- `fixtures/m2h2/human_composition_baseline_*/`;
- `fixtures/m2h2/human_composition_oracles_*/`;
- `fixtures/m2h2/human_composition_regressions_*/`;
- `fixtures/m2h2/human_composition_qualification_*/`;
- `fixtures/m2h2/human_composition_native_inspection_*/`.

Every final evidence root must record:

- exact source/head SHA;
- toolchain and locked KiCad identity;
- observer/schema version and hashes;
- exact case identity and semantic role inventory;
- candidate metric vectors;
- best rejected candidate metric vectors where applicable;
- exact run counts;
- per-case pass/fail;
- native render hashes;
- links to independent observer and oracle evidence.

## 19. Definition of human-readable composition PASS

M2h2 human-readable composition is PASS only when all of the following hold on one stabilized final source state:

1. existing M2h2 correctness PASS remains intact;
2. the independent composition observer is implemented and falsified;
3. semantic-flow and functional-block models are generic and independently checked;
4. tiny exhaustive placement and graph-order oracles pass;
5. baseline defects are catalogued with exact evidence;
6. input/output interface placement is semantically appropriate;
7. primary stage flow is visually ordered;
8. branches/fanout and feedback are visually intelligible;
9. support, power, and reference structures are coherently grouped;
10. repeated structures satisfy frozen alignment/consistency tolerances;
11. page utilization and whitespace satisfy frozen complexity-aware bounds;
12. routing-aesthetic metrics satisfy frozen tolerances without weakening existing limits;
13. label-mediated local disconnects satisfy frozen tolerances;
14. text/reference/value composition remains readable and consistent;
15. anti-overfitting and metamorphic audits pass;
16. all targeted composition regressions pass;
17. all 56 base positives ×5 pass under locked KiCad 10.0.6;
18. V3-8 remains correctly rejected;
19. all required I1–I6 interaction cases ×5 pass;
20. all required structural classes ×5 pass;
21. reproducibility passes;
22. all required native renders receive engineering inspection with no unresolved hard readability defect;
23. complete pytest/lint/format/diff/whitespace/link/historical audits pass as applicable;
24. the canonical human-readable composition TODO is fully checked with exact current-source evidence.

Only then may this remediation be marked **COMPLETE / PASS**.

## 20. Ralph Loop operating contract

At the start of every run:

1. reload current `master`;
2. reload:
   - `docs/M2_GENERALIZATION_REMEDIATION_SPEC.md`;
   - `docs/M2H2_FINALIZATION_SPEC_2026-09-27.md`;
   - this specification;
   - the canonical human-readable composition TODO;
   - `fixtures/m2h2/STATUS.md`;
3. inspect current master state and relevant CI through Ralph Bridge;
4. preserve existing M2h2 PASS authority;
5. select the highest-value actionable unchecked composition item;
6. prefer coherent vertical slices over one-checkbox commits;
7. advance independent observer/oracle/qualification work concurrently where safe.

Ordinary implementation bugs, test failures, lint/format failures, placement/search failures, visual-regression failures, CI still running, bounded polling timeouts, or safe compare-and-swap races are not user blockers.

A valid blocker exists only for unavailable credentials/authorization, unavailable required hardware/toolchain that cannot be provisioned under current authority, a destructive/external action requiring user approval, or a demonstrated contradiction with a higher-priority hard invariant.

After each coherent slice:

- update TODO checkboxes only from current-source evidence;
- add exact evidence references;
- update `fixtures/m2h2/STATUS.md` only when material remediation status changes;
- commit coherent code/tests/evidence/TODO reconciliation directly to `master` through Ralph Bridge using exact-head compare-and-swap semantics.

Do not finish merely to report progress. Finish only when every TODO item is checked with final-source evidence and human-readable composition is PASS, or a genuine blocker as defined above requires the user.
