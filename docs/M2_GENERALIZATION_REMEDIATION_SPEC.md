# M2 generalization remediation specification

Status: focused architectural review and Sol implementation handoff, 2026-09-23.
This document implements no remediation and creates no new corpus.

## 1. Decision and evidence boundary

**Verdict A: retain the existing architecture; strengthen and implement its
constraint, connectivity, variant, search, and acceptance contracts.** The
architecture is credible as a bounded schematic compiler, but the present
implementation is not qualified for general M2 composition. Passing 42 known
cases is regression evidence, not evidence of compositional completeness.

The missing executable abstraction is an **obligation-complete candidate**:
one immutable placement/presentation transaction with a total terminal and
relationship inventory, geometry witnesses, remaining constraint bounds, and
proof results. A collection of fragments, a semantic edge list, and a record
called a canonical tree do not establish that obligation completeness.

This is realization of existing requirements, not a new governing architecture:

- [SCHEMATIC_LAYOUT_SPEC](SCHEMATIC_LAYOUT_SPEC.md), sections 2, 5, 7, 9 and 11,
  already separates electrical/semantic/presentation graphs, requires semantic
  constraints, reconstruction of connectivity before serialization, bounded
  repair, and feasibility before scoring.
- [M2_COMPOSITION_REMEDIATION_SPEC](M2_COMPOSITION_REMEDIATION_SPEC.md), sections
  4–7, requires terminal-backed ports, propagation of order/span constraints,
  internal interfaces without connector prerequisites, and net-level routing.
- [M2_LAYOUT_ROBUSTNESS_REMEDIATION_SPEC](M2_LAYOUT_ROBUSTNESS_REMEDIATION_SPEC.md),
  sections 7–10, requires explicit cross-fragment obligations, meaningful
  aspect/support alternatives, a partial-placement beam, and selection among
  fully feasible candidates. M2g2 implements only parts of that handoff.
- [EVALUATION_PLAN](EVALUATION_PLAN.md), sections 3–5 and 8, retains independent
  emitted-artifact authority and mutation tests.

No existing governing document or threshold needs amendment. This document
makes the next implementation milestone, **M2h2 — obligation-complete bounded
composition**, concrete. It supersedes neither historical outcomes nor blind
qualification requirements. No M3, hierarchy, new asset families, PCB routing,
product redesign, or corpus.v7 is in scope.

### Evidence and reproducibility of this review

Primary evidence is the [V6 summary](../fixtures/m2blind_v6/SUMMARY.md),
[automated results](../fixtures/m2blind_v6/automated_results.json), all preserved
files under `fixtures/m2blind_v6/runs/V6-{2,3,4,6,8}/run1.failed/`, and their IRs.
The failure directories' JSON, schematic/library S-expressions, XML and SVG
structures were read/parsed, including raw CLI and configuration evidence.
V6-4 preserves only failure/attempt reports; V6-8 additionally preserves failed
composition evidence. Neither preserves an emitted schematic. Absence of a
layout report must not be interpreted as absence of layout computation.

The reviewed workspace HEAD is `3b6341cbb32ae354d17ece46f787c9ffd7545630`.
All 18 source hashes recorded in
[M2g2 qualification](../fixtures/m2g2/qualification/results.json) match current
source, including all modules used below. V6's frozen implementation commit is
`59b44e368345f0a24b3c98c07e9c1a6548a166de`; its freeze evidence remained unchanged.
Read-only in-memory reconstruction used the matching current modules to inspect
V6-4 local shapes/packing units and V6-8 routes. These are diagnostic calculations,
not new KiCad runs, accepted alternatives, or retroactive qualification.

The source audit follows these active boundaries (function names identify the
reviewed implementation even if later edits move line numbers):

| Boundary | Source/functions |
|---|---|
| Typed semantics and ownership | [m2_semantics.py](../src/ai_kicad/m2_semantics.py): `semantic_plan`, `_amp_block` |
| Local construction/certificates | [m2_fragments.py](../src/ai_kicad/m2_fragments.py): `_finish`, family constructors, `_access_alternatives`, `fragment_variants` |
| Measured placement | [m2_pack.py](../src/ai_kicad/m2_pack.py): `_place`, `_signal_chains`, `_make_units`, `_pack_shelves`, `pack_fragment_candidates` |
| Bounded repair and acceptance | [m2_compose.py](../src/ai_kicad/m2_compose.py): `_assemble_candidate`, `compose_with_evidence`, both repack helpers |
| Routes and conductor graphs | [m2_route.py](../src/ai_kicad/m2_route.py): `_connect`, `route_between_fragments`; [m2_geometry.py](../src/ai_kicad/m2_geometry.py): `Gateway.validate`, `canonical_conductor_tree`, `conductor_reachable` |
| Preflight and independent gates | [m2b.py](../src/ai_kicad/m2b.py): `Draft.point`, `measure`, `check_observed_layout` |
| Serialization/observation/build | [m2a.py](../src/ai_kicad/m2a.py): `emit`, `observe`; [m2b_build.py](../src/ai_kicad/m2b_build.py): `build` |

The review also inspected relevant M2g2 tests/probe construction, older IR
relationship inventories for probe novelty, and the four requested governing
specifications. It did not inspect `.local/`, `research/legacy_openclaw/`, or
recursively inspect `examples/`. SVG structural inspection is not human visual
approval. No historical evaluator was rerun and no historical evidence changed.

## 2. Why 42/42 failed to predict 3/8

The historical blind progression is 2/8, 3/8, 7/8, 4/8, followed by 42/42
known/development qualification and 3/8 fresh V6 acceptance. These are different
samples and evaluation roles, not a monotonic learning curve. The 42 comprise
32 prior-corpus positives (including the corrected V3-8), five M2e1/M2f2 probes,
three new M2g2 base probes and two stress derivatives. The invalid original V3-8
remains a negative. Five repeats demonstrate stability, not five independent
compositional examples.

The suite contains substantial interaction testing, but no measured interaction
coverage. It is inaccurate to say it tests every constraint only in isolation.
It tests selected interactions close to known failures; it does not establish
closure under substituting a local motif or adding another semantic relation.

| Fresh interaction | Nearby known coverage | Assumption left unfalsified |
|---|---|---|
| Passive intermediate between timer and active successor | Timer/filter, timer/buffer, M2g2 timer/high-pass/inverting/indicator | A branch target can be removed from the signal packing graph without losing its outgoing precedence. |
| Internal generated reference shared by filter, output shunt and parked unit | Reference amplifiers; Sallen-Key plus output RC | Net naming/local gateway validity implies global electrical connectivity even without an external reference connector. |
| Two tall timer chains plus shared mixed amplifier package | Dual timers; parallel op-amps; two independent chains | Combining individually measured fragments with four shelf recipes gives meaningful placement coverage. |
| Parallel non-inverting and inverting consumers of one high-pass | V5-7 high-pass feeding parallel functions | A topology-preserving local substitution will preserve cross-fragment distance bounds. |
| Regulated timer/buffer plus dual output branches | Regulated timer branches; timer/buffer; mixed regulator loads | Greedy fewest-bend tree attachment and access-only repair control whole-net conductor length. |

This resembles a bounded catalog of constructive local layouts with a thin
composition heuristic, not machine learning of complete circuits. Cartesian
combinations of locally valid variants need not be feasible: they compete for
height, reference access, package affinity and routing corridors. M2g2's beam
mostly changes port escape choices in a baseline assignment; it is not the
specified partial-placement search over those joint constraints.

Specific tests in [test_m2g2.py](../tests/test_m2g2.py) explain the blind spots:

- `test_fanout_order_preserves_only_real_precedence` supplies `signal` edges
  directly and checks envelope origins. It bypasses actual passive-target
  classification and never checks terminal precedence through a branch target.
- `test_multiple_support_types_expose_bounded_local_substitutions` checks 2–8
  variants and common occurrence keys, not independent body/support/aspect
  dimensions. Seven equal-sized timer variants satisfy it.
- `test_typed_identity_ownership_and_gateway_witnesses_are_exact` checks witness
  net identities and obligation owners, not global connected-component coverage.
  The detached/label-only graph tests are useful, but are not a total-net proof.
- Synthetic route/obstacle and envelope tests validate individual predicates;
  they do not force the composer to reject an internally accepted layout for
  stage order or cross-fragment span before emission.
- The bounded-failure test injects `ROUTE_BLOCKED: net=N`. It never supplies
  `NET_DETOUR_OVERFLOW` in its actual different format, so repair dispatch failure
  remains invisible.
- [make_m2g2_probes.py](../tools/make_m2g2_probes.py) creates three base topologies,
  plus long-text and unit-exchange derivatives. Nonempty frozen path expectations
  and five successful builds do not cover unrepresented interaction cells.

[Engineering inspection](../fixtures/m2g2/engineering_inspection.json) records
`completed_agent_visual` on seven renders. It supports observations about those
renders; it is neither independent human milestone approval nor evidence about
all possible compositions. There is no evidence of V6 contamination or unstable
frozen inputs. The failure is primarily coverage and implementation, not a
compromised blind protocol.

## 3. Root causes by failure

### 3.1 V6-2: semantic precedence disappears before packing

The [composition](../fixtures/m2blind_v6/runs/V6-2/run1.failed/reports/composition.json)
contains `timer.timer -> passive.timer_filter.series` as `branch`, then
`passive.timer_filter.series -> function.amp.a` as `signal` on FILTERED.
`m2_semantics.semantic_plan` classifies a signal edge as `branch` whenever its
target ID starts with `passive.`. `_signal_chains` in `m2_pack` then excludes
*all branch targets* from its nodes, including this intermediate RC. The RC's
outgoing signal relation no longer participates in chain construction.

The first side-affinity packing passes at 203.525 × 101.18 mm. Its actual filter
output is (189.23, 41.91) mm and amplifier input is (34.29, 39.37) mm. The observer
correctly rejects the 154.94 mm x reversal. Their Manhattan separation is also
157.48 mm; fixing only order would not discharge all this candidate's obligations.

This is **A: a missing packing constraint**, exposed by branch handling and
independent placement. Shelf ordering amplifies the omission; this is not a
licensed relaxation on separate shelves. Local pin orientation is valid.
`_place` transforms anchors, escape polylines and reservations consistently;
there is no evidence of a later emitter translation/repack causing the reversal.
The observer's series-to-amplifier rule agrees with the authored relation and
real pins. Electrical equivalence cannot detect spatial reversal.

Branch incidence and precedence must be independent properties. A fork creates
one precedence edge to each ordered child, never an artificial edge between
siblings; an intermediate child retains all its downstream constraints.

### 3.2 V6-3: exact pin attachment, but disconnected reference islands

The [ERC report](../fixtures/m2blind_v6/runs/V6-3/run1.failed/reports/erc.json)
records seven violations. The exported XML contains VREF only at C1.2, C2.1,
R1.2 and R2.1, plus singleton unconnected nets for C3.2, C5.2 and U3.5.
This is a real emitted electrical defect.

Crucially, the emitted wires **do end exactly on those three actual pins**:

| Pin | Actual pin (mm) | Preserved stub and outer endpoint (mm) |
|---|---|---|
| C3.2 | (86.36, 90.17) | via (86.36, 96.52) to (86.36, 97.79) |
| C5.2 | (129.54, 139.70) | via (129.54, 146.05) to (129.54, 149.86) |
| U3.5 | (153.67, 110.49) | via (147.32, 110.49) to (146.05, 110.49) |

These are floating one-terminal islands, not coordinate near-misses. KiCad's
`pin_not_connected` description does not establish a geometric pin-to-wire gap.
Do not read the unusually scaled ERC position values as the schematic's physical
coordinates; the table is reconstructed from embedded symbols and wire bytes.

The causal chain is explicit:

1. `_finish` in `m2_fragments` places labels only when the port net is local-only
   or includes a connector. VREF here spans fragments and has no connector.
2. Sallen-Key and output-RC reference stubs therefore receive no VREF label.
   The parked unit's VREF input stub also receives no label.
3. `route_between_fragments` groups only `signal`, `power`, and `branch` edges.
   It excludes reference edges and does not derive completeness from the full
   terminal inventory. The parked VREF input lacks a driving signal edge too.
4. `canonical_conductor_tree` splits/deduplicates segments but does not require
   one connected component. Its one VREF record contains four wire components.
   Net strings group segments in memory; they do not electrically join them.
5. `_finish` verifies reachability from **any** gateway witness, not all required
   terminals/islands. `measure` checks membership in wire endpoints **or labels**,
   not connection to the intended net. All three floating stubs satisfy it.
6. `m2a.emit` faithfully serializes the canonical segments. It does not clip,
   normalize away, or move these stubs. KiCad detects their isolation.

The missing contract is total physical-terminal coverage by an explicit
presentation connectivity plan, including internal reference nets and all local
islands. Fixing endpoint equality alone would leave this exact defect intact.
No observed evidence implicates stale translations, grid quantization, segment
clipping, emitter normalization, or variant-dependent route staleness in V6-3.
Those remain required mutation controls, not substitute diagnoses. Ownership
normalization also did not cause this failure: the disconnected intervals were
already separate before canonicalization.

### 3.3 V6-4: weak dimensions, not 32 independent packings

The [failure trace](../fixtures/m2blind_v6/runs/V6-4/run1.failed/reports/failure.json)
has 32 failed packing proposals, only **six distinct content dimension pairs**,
and only two heights: 149.44 and 147.75 mm. These dimensions alone are not a full
geometry-equivalence proof, but they demonstrate how little size diversity was
explored. The best exceeds 140 mm by 7.75 mm. There were no complete routed
attempts, although the diagnostic misleadingly says `candidates=32/8`.

Matching-source reconstruction shows both timer families have seven variants,
all with packing dimensions **69.85 × 74.51 mm**. `_timer_fragment` fixes the
ladder above/below the timer and the control cell at fixed offsets; access
alternatives change gateways, not that arrangement. The two chain units are
approximately 113.985 × 74.51 and 114.05 × 74.51 mm. `_pack_shelves` puts later
serial units on another shelf; two such row widths also exceed 210 mm if simply
placed side by side. One-pitch channel gaps are not the dominant waste.

Side/lower affinity builds an interface column 76.2 mm high, raising one shelf;
flat interfaces reduce the result to 147.75 mm but cannot remove the two tall
timer rows. Package power is a 55.88 × 22.44 mm cell and cannot backfill a narrower
amplifier rank using the current width test. It is not demonstrated to require a
new full shelf: backfill beside existing rows is available. Blaming only package
power or text margins is therefore unsupported.

Required missing decisions are a compact timer ladder/support form, measured
upper/lower/lateral support arrangements, and fragment-level interleaving of
independent chains while preserving each precedence edge. Reservation arithmetic
may be improved where duplicate clearance is proved, but reducing margins by
8 mm without such proof is prohibited. No alternative passing V6-4 layout was
certified in this review; failure of these recipes is not page infeasibility.

### 3.4 V6-6: recorded path bounds never constrain placement

The [failure](../fixtures/m2blind_v6/runs/V6-6/run1.failed/reports/failure.json)
reports `ordered series` and `series/amplifier`, each 88.9 mm. These are two
obligation descriptions of the same high-pass-output to inverting-input-resistor
endpoint pair: (48.26, 41.91) to (76.20, 102.87) mm. They are not necessarily two
independent long routes. The observer correctly resolves the inverting input
resistor instead of using its reference-biased plus pin.

DAG rank placement stacks the unequal amplifier variants vertically; the chosen
inverting variant is `.v1`. Neither `_make_units` nor candidate acceptance
propagates that terminal-pair bound. `ProtectedPath.maximum_span=80_000_000` and
`PathObligation.maximum_span` exist, but their presence is not an executable
cross-fragment check. `_assemble_candidate` calls `measure`, which does not
implement these final locality gates. The composer stops at its first internal
pass and does not try another seed after the independent rejection.

The 80 mm metric is **endpoint Manhattan span with explicit reachability required
separately**, not the length traveled along a wire. It can be evaluated exactly
as soon as both fragments are placed, before any routing or KiCad invocation.

### 3.5 V6-8: distributive routing, objective and failed feedback

The [attempt trace](../fixtures/m2blind_v6/runs/V6-8/run1.failed/reports/layout_attempts.json)
ends at 381 mm. It also records 266.70 mm (seed 0 retry) and **260.35 mm** (seed 6
retry), the best preserved VCC result. All remain above 250 mm. BUFFERED also
exceeds 250 mm in some attempts; this is not exclusively a power-net issue.

The router uses the same incremental tree attachment for signal and power,
with a route-class ordering difference. It tries direct tracks before visibility
search and ranks attachments by bends before added length. It plans no shared
rail corridor jointly with consumer clusters. The regulator can sit far to the
right of a timer and package consumer, behind already routed signal obstacles.

Matching-source reconstruction explains the lengths (canonical conductor union,
local and global intervals charged once):

| Attempt | VCC local conductor | VCC global conductor | Total |
|---|---:|---:|---:|
| seed 0 initial | 46.99 mm | 336.55 mm | 383.54 mm |
| seed 0 retry | 46.99 mm | 219.71 mm | 266.70 mm |
| seed 6 retry | 46.99 mm | 213.36 mm | 260.35 mm |
| seed 7 final route mode | 74.93 mm | 306.07 mm | 381.00 mm |

For seed 0, gateway coordinates are regulator (170.18, 38.10), timer
(69.85, 57.15), and package (50.80, 110.49) mm. The initial global tree traverses
x=25.40 and y=29.21 mm before returning toward consumers. The retry is markedly
shorter with the same placement. The final seed's local length is worse too.
The engine therefore needs whole-net length budgeting and consumer-aware
placement, not simply a larger routing iteration count.

Repair is additionally broken for this conflict class: `_substitution_repack`
and `_reservation_growth_repack` parse `net=...`, but the exception is
`NET_DETOUR_OVERFLOW: [('VCC', ...)] threshold=...`. All eight round-2 entries
are `repeat_state_skipped`; all growth objects are null. Round 3 changes route
retry mode without the reported reservation growth. There are 32 recorded slots,
24 actual assembly attempts, and only 16 distinct recorded conflict strings.
Fix typed conflict propagation before interpreting the budget as useful search.

### Root-cause classification

| Category requested | Verdict |
|---|---|
| Architecture/spec deficiency | No governing rewrite needed; existing contracts already require the missing obligations. Implementation-level candidate/presentation contracts need to become enforceable. |
| Implementation not realizing architecture | Demonstrated: branch precedence loss, unconsumed path bounds, absent complete-net proof, first internal-pass selection, omitted partial-placement search. |
| Search-space coverage | Demonstrated: few shelf recipes, equivalent size outcomes, skipped detour repair. No evidence that simply extending the same schedule would solve V6. |
| Local-variant expressiveness | Demonstrated for timer size/support; other families expose fewer structural dimensions than the prior specification requires. |
| Candidate selection/objective | Demonstrated: no final-hard-gate feasibility screen for order/span; bends precede whole-net length feasibility; first-pass early exit. |
| Constraint propagation | Demonstrated across passive branch boundaries, shared package affinity and cross-fragment local paths. |
| Routing/emission correctness | V6-3 is a presentation connectivity/routing completeness defect faithfully serialized by the emitter; no demonstrated coordinate serialization defect. |
| Evaluation/threshold defect | No false rejection demonstrated for these five cases. The initial V6 harness count-field bug was corrected separately without changing artifacts or gates. |
| Benchmark/capability envelope | Known-suite selection lacks interaction coverage; valid fresh compositions still count as failures. Bounded failure does not establish that they exceed the declared page/capability envelope. |

## 4. Executable obligation and candidate contracts

Use ordinary immutable records in the existing module boundaries. Do not build a
new workflow framework. Semantic obligations are derived before choosing local
geometry and survive all variant, shelf, route and repair decisions.

| Record | Required content |
|---|---|
| Terminal inventory | Physical terminal ID, occurrence/unit, locked pin-definition identity, net, required/intentional-NC state, geometry owner. |
| Precedence | Origin relationship IDs, resolved source/target terminal or functional boundary, axis, strict minimum separation, scope. Separate from branch incidence. |
| Local relationship | Origin IDs, exact terminal pair(s), explicit-wire requirement, endpoint span limit, support/feedback subtype and component transitions. |
| Presentation net | All physical terminals and local connected islands, signal/distributive role from semantics, explicit global obligations, allowed labeled islands and scope/budget. No net-spelling dispatch. |
| Variant certificate | Geometry digest, exact pin transforms, island membership, all terminal-to-gateway witnesses, local paths/spans, occupied and reserved geometry, structural/access signature. |
| Candidate | Variant assignment, transforms, structural decisions, planned shared corridors, net plan, propagated bounds, route graphs and proof results bound to one digest. |
| Conflict | Enum class, obligation/net IDs, owners/ports, offending geometry, actual/limit/lower-bound values, responsible state decisions, permissible repair classes. No parsing English exception strings. |

Every accepted relationship must map to obligations or an explicit unsupported
reason. Ownership covers occurrences; it never substitutes for terminal coverage.
Generate terminal obligations even where no signal edge exists. In particular,
parked inputs, package rails, references and interfaces cannot disappear because
they are absent from the signal DAG. Unknown ambiguity stops planning; no
inferred electrical direction for passive/reference distribution is permitted.

### Gate classification and timing

| Gate | Current prospective representation | Required treatment |
|---|---|---|
| Stage order | Partial signal-rank construction; no total terminal-order acceptance check | Hard placement constraint; propagate partial-placement lower bounds; exact check after every transform and before emission. Never just ranking. |
| Local span / support / feedback | Metadata plus local constructive geometry; incomplete global enforcement | Hard actual-pin placement bounds; admissible partial-domain bounds; exact final geometric check plus explicit path feasibility. |
| 250 mm conductor length | Hard canonical-length rejection after routing | Safe lower bound during placement and each attachment; prune provably impossible partial trees; full post-route hard test. Among possible trees rank length/headroom as routing feasibility guidance. |
| 210 × 140 mm content / page | Packing bounds and assembled content checks exist | Hard placement/content checks, lower bounds for unplaced items, exact prospective historical point extent and full occupied-page containment after routing. |
| Net topology/connectivity | Canonicalization, owner checks and gateway checks, but no total-net component proof | Hard local certificate and post-route graph/partition proof covering every terminal and permitted label join. |
| Wire endpoint attachment | `measure` endpoint-or-label set check | Hard exact pin/gateway incidence and degree/endpoint-intent test; no coordinate snapping or unnamed dangling island. |
| Collision/reservation legality | Local reservations and segment checks; containment may be satisfied by any reservation | Hard owner/net/capacity-aware allocation before routing and complete-scene post-route proof. Post-hoc reservation around each new wire is not prospective capacity proof. |

An admissible lower bound can reject only if it exceeds the hard limit. A
heuristic distance/congestion estimate may rank, but must never be labeled an
infeasibility proof. Do not use a Manhattan MST as a lower bound on a Steiner
network: shared branches can be shorter. Bounding-box width plus height is a
safe lower bound for an explicitly connected rectilinear terminal set. For
multiple preconnected islands, use a conservative bound on additional length
(e.g. maximum of individual distances to the existing union), not a sum that
double-counts shared future branches. The current tree union length is itself a
lower bound only while that tree is fixed; rerouting can remove its detours.

## 5. Stage-order and local-distance propagation

For every declared signal precedence `u -> v`, resolve the actual output-side
terminal of u and input-side terminal of v. Compound filter boundaries follow
verified local paths; an inverting input is its series input terminal, not plus.
Preserve intra-fragment relationship obligations as well as fragment edges.

For left-to-right M2 precedence, require
`X(owner(u)) + local_x(u, variant) + epsilon <=
 X(owner(v)) + local_x(v, variant)`.
Here epsilon is one integer coordinate unit (1 nm) for the existing strict
comparison; legal grid origins and occupied separation usually imply a larger
gap. It is not permission to violate clearance. Every branch child with declared
signal direction obeys this inequality; incomparable siblings have no invented
mutual precedence. Feedback, supplies and reference distribution are excluded
from signal order only, never from connectivity.

Shelf assignment does not reset x precedence. A common whole-scene translation
preserves differences; any individual shift, compaction, variant replacement or
repack must re-evaluate all incident constraints using new local pin offsets.
Reject cycles/incompatible inequalities with origin witnesses. No visual
row-reading exception may waive the existing observer's x-order rule.

For each required local pair `(a,b)`, enforce
`abs(xa-xb) + abs(ya-yb) <= bound` on exact physical endpoints. Use 80 mm for
current local fragmentation obligations, 60 mm for consumer support, and retain
the separately defined existing feedback limits (including the observed 45 mm
gate and applicable local construction limits). Do not reinterpret these as
wire-length thresholds. Explicit conductor reachability is a separate proof.

Propagate coordinate domains after each assignment: intersect predecessor and
successor x ranges, then intersect each endpoint domain with the counterpart's
Manhattan-distance diamond, accounting for chosen or remaining variant offsets.
If the minimum possible endpoint distance over remaining domains exceeds the
bound, prune. A bounding-box domain relaxation is acceptable and conservative;
once both variants/positions are chosen, evaluate the exact inequality.

Feedback/filter/timing paths internal to a variant are locally certified.
Cross-fragment series/amplifier and reference/support obligations remain in the
global planner. Shared-package affinity can rank package placement but cannot
override a real decoupling terminal bound or create a false serial edge. Keep
one relationship inventory with multiple named consumers, not an unconsumed
`maximum_span` field in each fragment.

## 6. Terminal, gateway, conductor and emission proof

The invariant is stronger than either terminal-name equality or endpoint presence:
**every required routed terminal has a continuous geometric conductor ending
exactly on its resolved actual pin and reaching its assigned gateway/island;
every island is connected to the intended net under the declared presentation
plan.** Every gateway terminal witness must be proved, not merely one witness.
If witnesses occupy different islands, expose separate gateway/island records.

The proof chain is:

1. Resolve physical terminal to one occurrence and exact asset pin endpoint.
2. Construct its local conductor and actual geometric island. Assign island IDs
   by connectivity, not `fragment_id:net_name` alone.
3. Prove each terminal-to-gateway path from wire geometry; label equality supplies
   no edge in an explicit path. Account separately for intentional NC and any
   policy-permitted direct label-at-pin presentation.
4. Transform pins, wires, labels, gateways, windows and reservations together.
   Rebuild witnesses after variant change. No route cache survives a changed
   geometry digest without revalidation.
5. Attach global routes to declared transformed gateways/windows, checking exact
   net, island, approach and ownership. A route touching the end of an escape
   polyline is insufficient unless the escape is present and pin-reachable.
6. Build one canonical **graph** per required net, with geometric connected
   components reported explicitly. Split at real endpoint contacts, pins, legal
   taps and junctions; do not connect unrelated crossings or infer connections
   from metadata. Validate interval ownership and preserve all required contacts.
7. For explicitly distributed nets require one geometric component covering all
   assigned terminals. Where existing policy permits labeled islands, record
   every island and exact scope-correct label contact, and prove the net's
   electrical graph connected after those authorized joins. Protected paths
   still require one wire-connected component. One graph may contain several
   justified wire islands; calling it a tree must not hide disconnected geometry.
8. Classify every degree-one conductor endpoint: actual required pin, approved
   attached label/source terminal, or explicitly intentional presentation end.
   Reject unaccounted stubs, unnamed one-terminal islands and missing branches.
   Reject unintended cycles/redundant loops; normalize only with topology proof.
9. Compare reconstructed electrical partitions with the complete expected
   terminal inventory, including extra terminals and shorts. Labels are governed
   by actual scope and contact, not by the net assigned to a wire in memory.
10. Freeze the certified scene. Before writing `.kicad_sch`, produce serialized
    content in memory and independently parse its embedded pin definitions,
    symbol transforms, wires, junctions and labels. Exact coordinates, terminal
    coverage and partitions must agree with the certificate. Serialization must
    be a pure encoding operation with no last-minute geometry choices.

Use integer nanometers throughout; preserve off-grid pin tracks exactly, even
where origins use the qualified pitch. No tolerance may turn a near-miss into
contact. Test grid rounding, stale gateways, ownership overlap, deleted escape
segments and changed pin definitions independently. V6-3 specifically needs
steps 6–9, even though steps 1–5 largely worked for its isolated stubs.

## 7. Distributive-net routing model

Power, internal references and shared control distribution have consumer sets,
not serial stage order. Derive their role from terminal/relationship semantics.
Do not special-case `VCC`, `VREF`, regulator/timer pairs or net degree alone.
Keep signal branches supported by the same graph machinery, with their own
protected precedence/locality obligations.

Plan distribution before global routing:

1. Collect all terminal-backed local islands, including those with no semantic
   signal/power edge. Preserve existing allowed presentation choices explicitly;
   internal shared references default to connected explicit distribution.
2. Cluster gateways by candidate shelf/support band and compatible approach side.
   Enumerate four structural strategies: horizontal shared trunk above consumers,
   horizontal trunk below, vertical side trunk, and producer-centered tree.
   A no-producer reference uses the most constrained gateway, then stable ID,
   solely as a geometric seed.
3. Reserve the trunk and shelf-local tap corridors during placement. For each
   strategy retain the two nearest legal track placements using exact gateway
   tracks/obstacle boundaries: at most eight plans per net. Track legality uses
   the same body/text/pin/protected-route and capacity rules as signal routing.
4. Generate deterministic branches at gateway projections and legal Hanan-style
   intersections. Connect shelf clusters to the shared trunk and local consumers
   to taps, charging shared intervals once. Reuse fixed local trees only at
   certified access windows. No internal motif conductor may be rewritten.
5. Use the existing sparse visibility connector for blocked branch segments,
   retaining its ceilings of 32 taps, eight tracks per side, and 4,096 expansions
   per tested tap. Add a sheet-wide counter so nested trials cannot reset limits.
6. Reject any plan whose fixed local conductor union plus safe global lower bound
   already exceeds 250 mm. During attachment track total union length and the
   conservative remaining demand. Among hard-feasible distribution plans rank
   total union length, worst terminal-to-trunk distance, bends, occupied growth,
   then canonical geometry. Do not prefer a fewer-bend route already over budget.
7. Return a typed blockage/length conflict naming the consumers, limiting
   corridors and local/global length breakdown. Feed consumer spread or unusable
   supply-entry sides back to placement/variant selection. Report the best
   failed candidate as well as the final attempt.

Each complete routing attempt chooses one bounded strategy assignment for all
nets from a beam of at most eight partial assignments; each extension evaluates
at most eight plans. These are routing states inside the same attempt, not new
unbudgeted full-sheet searches. For G nets and K(n) required gateway islands
on net n, cap plan extensions at 64*G and tap-search expansions at
`64 * sum(max(1, K(n)-1)) * 32 * 4096` per complete attempt, with the same
counters carried through all trial plans. These conservative operation ceilings
are not runtime promises; a safety watchdog aborts the attempt, never chooses
a partial winner. Reserve scarce corridors before routing but
retain protected-path-first route priority. Shared corridors must be available
to their intended net when it is routed. Do not route supplies first merely
because they have more terminals or add labels as an overflow escape hatch.

This is schematic trunk-and-tap planning, not a generic PCB router or a claim of
optimal Steiner routing. It should also improve shared control/reference nets
and signal fanout length budgeting, not just the V6-8 power net.

## 8. Local variants: meaningful completeness and pruning

Retain at most eight certified variants per fragment. Local constructors receive
only their owned semantic neighborhood, exact assets, constraints and policy;
they must not inspect unrelated connector presence to decide connectivity.
Global presentation planning assigns any permitted boundary labels separately.

| Family | Actually represented now | Required reusable structural alternatives |
|---|---|---|
| Amplifier / Sallen-Key | Feedback above/below; several one-port escape alternatives | Preserve these; support/reference side and compact/expanded corridor forms when legal, with full pin/path revalidation. |
| Timer | Fixed vertical ladder/control placement; altered port escape direction | Compact measured ladder versus expanded form; control/support cell above/below/lateral; supply entry and branch exit independently usable. Preserve ladder order. |
| Regulator | Fixed support geometry; gateway direction changes | Input/output support bands above/below or lateral; continued supply output corridor; compact width/height alternatives. |
| Package power / divider | Reference-side alternate and port escapes | Compact wide/tall support cell, separate positive/negative entry sides, divider access; global placement adjacent to either owning consumer band. |
| RC / series / LED | Fixed body arrangement for each kind; altered escapes | Permitted series axis, shunt/return side, branch exit; compact/expanded measured spacing. Preserve actual polarity and declared progression. |
| Interface | Fixed occurrence placement, escape alternatives | Finite field/access arrangements; global input/output/perimeter versus shared interface band placement. No synthetic connector. |

The prior robustness spec already requests most of these. Gateway direction
changes are useful but do not count as support relocation or aspect alternatives.
Local compact forms derive minimum distances from bodies, text, pin conductors,
protected corridors and policy separation; they are not percentage-scaled versions
of existing coordinates. Add only locally meaningful combinations, not a product
of every side flag. At most 32 local construction proposals per fragment; log
rejection reasons and retain at most eight.

Dominance is conditional on an identical occurrence/terminal inventory,
obligation topology, island policy, and compatible ordered port/access signature.
Variant A can discard B only if A has no larger width/height, no worse required
local spans or wire length, and at least the same feasible access windows and
approach capacity after canonical alignment. Different gateway offsets or obstacle
patterns generally make variants incomparable; smaller area alone proves nothing.
Retain one representative per structural signature first, then nondominated
aspect/access representatives, with deterministic IDs as final ties. Record any
budget-truncated nondominated class as **uncovered**, not dominated or impossible.

For next-milestone timer/package tests, require at least two distinct normalized
body/support arrangements with measured aspect differences where constraints
permit them. Escape-only variations cannot satisfy that test. A family need not
expose all nominal sides where actual pins or semantics make them illegal.

## 9. Deterministic hierarchical search and coverage

Replace the eight preselected whole-sheet variant dictionaries crossed with four
shelf recipes with the partial-placement beam already specified by M2g2's handoff.
Do not increase the eight-seed / three-repair / 32-complete-attempt ceilings.

1. **Structural assignment.** Use the complete precedence DAG, local-path groups,
   package affinities and distribution demands. Grow placements in stable
   topological order (most constrained access, envelope size, then ID for ties).
   Treat independent chains as separable fragments with retained constraints,
   not rigid full-width row rectangles. Four extension classes are aligned
   successor/peer, independent shelf/backfill, upper affinity band, lower affinity
   band. Within a class choose the minimum legal origin from propagated bounds.
   Sibling vertical order, package attachment and interface band are explicit
   state decisions, not consequences of alphabetical sorting alone.
2. **Variant assignment.** At each extension consider up to eight nondominated
   local variants. Intersect port/order/distance domains and reservation capacity
   before keeping the extension. Beam width is eight, at most `8*8*4*N` extension
   evaluations for N fragments per placement pass. Do not merge states solely by
   bounding dimensions; future port feasibility matters.
3. **Coarse placement and corridors.** Allocate distribution strategy/corridor
   demand, propagate precedence and locality again, and reject size/capacity lower
   bounds. Keep eight seeds with distinct structural signatures where available.
   Within each signature rank unresolved demand, maximum dimension utilization,
   predicted net-length headroom, area, then canonical state. These estimates
   never waive hard constraints or count as proofs.
4. **Route feasibility.** Route all net/island obligations under section 7 and the
   existing local/global obstacle rules. Reconstruct conductor graphs; evaluate
   every prospective hard gate. Failed candidates retain complete conflicts.
5. **Compact/repack.** Two fixed passes, x then y, minimize origins subject to
   selected separation inequalities, order, locality and corridor allocation.
   Regenerate all global routing after movement. A changed local variant is
   rebuilt/certified in full. Recheck every incident constraint after each move.
6. **Quality selection.** Finish the bounded schedule and rank only fully proved
   candidates by the governing feasibility-first quality tuple, ending in a
   canonical geometry digest. Emit/check in that deterministic order. No first
   internal-pass early return before known hard checks or remaining ranked
   candidates have been considered.

Each seed has four globally accounted slots: initial route, alternative routing
strategy/tracks, conflict-directed variant or structural substitution, and final
witnessed reservation adjustment/repack. A locality/order conflict goes directly
to structural repair rather than wasting a reroute that cannot change endpoints.
A detour conflict can change distribution plan, consumer cluster position or
entry-side variant; reservation growth is appropriate only for a witnessed
capacity/blockage deficit. Growth never means blindly making a too-long tree
larger. Fix reservations monotonically within a repair lineage after genuine
growth. Share one attempt ledger across repacking calls; no recursive budget reset.

Globally deduplicate canonical states across seeds and repairs. Record a skipped
slot separately from a complete layout attempt; it still consumes that seed's
slot, preserving the 32-slot ceiling. Record partial expansions, route expansions,
local proposals, proof checks and KiCad invocations separately. A post-emission
rejection may use an unused slot for that seed, but cannot create a 33rd attempt.
If no slot remains, try another already-proved candidate or fail explicitly.
A wall watchdog only aborts; elapsed time must never select a winner.

Typed route feedback must distinguish: inaccessible gateway (side/variant),
blocked corridor (capacity/separation), conductor-length lower-bound overflow
(consumer spread/trunk), actual routed detour (routing choice), local span
(relative placement), or terminal/island coverage defect (construction/planning
contract). Impossible geometry certificates are programming failures, not reasons
to silently omit obligations and continue searching.

### Search coverage report

Report coverage over decisions, not just attempts:

- Available/tried/pruned/uncovered structural signatures: shelf membership,
  sibling order, support side, local compact/expanded family, interface band,
  package placement and distribution-trunk strategy.
- Distinct normalized local body/support shapes, port access signatures, complete
  placements and routed graph signatures; strip variant ordinal/name differences.
- For every prune, its dominating state or hard bound with obligation IDs.
  Distinguish budget truncation from infeasibility.
- Conflict class eliminated by each actual repair, best failed metric vector,
  selected feasible vector, and remaining nondominated classes at exhaustion.
- Coverage denominator is the finite alternatives declared by this grammar,
  not all possible planar layouts. Report structural coverage and geometry
  equivalence separately; equal dimensions do not imply equal routing behavior.

At least one tiny exhaustive reference enumerator in tests (up to four synthetic
fragments, two variants, two bands) must independently enumerate legal states.
Compare the beam's retained classes and rejection bounds to it. Do not require
optimality or global completeness from a width-eight beam. Require that a known
hard-invalid candidate cannot be emitted while a generated proved candidate
passes, and that every discarded feasible class has an honest coverage reason.

## 10. CP-SAT decision

**Do not introduce CP-SAT in M2h2.** Unlike the preceding V5 review, V6-4 is direct
evidence of a placement/variant expressiveness bottleneck. Its natural eventual
model is indeed discrete variants, shelves and rectangle origins subject to
precedence, locality, reservations, spread and non-overlap. But the current search
has not implemented those constraints or the specified hierarchical alternatives,
and all timer variants retain the same tall body layout. A solver over that weak
inventory would not manufacture the missing compact construction. V6-2/3/6 also
have correctness/propagation defects that no placement optimizer should mask.

The constructive approach is sufficient for the **next bounded implementation
experiment**, not proven sufficient for every M2 input. Implement the executable
contracts and structural coverage first. Make its small constraint problem
exportable: per-fragment variant domain with exact terminal offsets, candidate
shelf/support assignments, integer origins, occupied/reserved rectangles,
precedence inequalities, Manhattan locality bounds and fixed page/spread limits.
Routing and local motif construction remain outside this placement problem.

Reconsider a solver only if the corrected coverage report repeatedly exhausts
legal structural alternatives and a generic independent feasible placement
witness or exhaustive small-model comparison shows that pruning/assignment is
the remaining bottleneck. Missing local variants, disconnected islands or failed
route heuristics are not that evidence. Freeze any later constructive-versus-solver
comparison before tuning, using the same variants, constraints, route budgets and
gates. Existing governing solver ceilings remain applicable then. Solver adoption,
version/settings and deterministic qualification would require a separate bounded
placement-only milestone; no optional solver fallback is left for Sol to invent
inside M2h2.

## 11. Quality thresholds and capability claims

Retain **210 × 140 mm spread, 80 mm local span, and 250 mm per-net canonical
conductor union length**, with the existing feedback/support/text/page gates.
Do not enlarge A4, shrink fields, permit unrelated crossings, or use continuity
labels to evade these failures.

These limits operationalize compact one-sheet grouping, nearby protected
relationships and restrained wiring. The governing evaluation plan treats
historical good examples as qualitative structural evidence, not calibrated
universal numerical optima. This review did not remeasure excluded examples and
does not claim these numbers are scientifically optimal. Known successful
qualification and V6-1/5/7 demonstrate achievable values in relevant compositions;
V6-7 passes with observed content 199.39 × 124.46 mm. The failures do not prove
that valid alternative geometry must exceed the thresholds.

The name “detour” is imprecise: 250 mm currently caps total canonical net wire
length, not excess over a lower bound or the longest source-to-consumer path.
Consumer count legitimately affects total tree length. Retain the current hard
cap for this frozen capability envelope; additionally report consumer/island
count, total union length, terminal bounding-box lower bound and routed-to-bound
ratio (undefined when the bound is zero), and worst explicit source-to-consumer
path. These are explanatory diagnostics, not replacement gates. In particular,
V6-8 does not demonstrate metric invalidity: the same placement admits much
shorter routing modes, and a hard-cap-feasible layout has not been disproved.

Any future capability/metric revision needs preregistered semantic definitions,
reviewed diagrams at fixed text/page scale, anti-gaming controls and a new protocol.
A raw larger number after V6 is not such a revision. Do not retroactively exclude
these supported cases from the denominator or claim infeasibility from exhausted
heuristics. Full M2 qualification still requires the prescribed blind and human
review gates; M2h2 is development remediation only.

## 12. Pre-emission and independent post-emission authority

Before writing any `.kicad_sch`, require a certificate containing the following
results bound to the exact candidate/asset/policy digest:

1. Exactly one geometry owner per resolved symbol occurrence; no duplicate or
   missing physical terminal, unit, source assertion or intentional NC state.
2. Every semantic relationship has all its obligations accounted for. All
   required local paths have exact endpoints, explicit reachability, valid
   component transitions and passing span/feedback/support bounds.
3. Every signal precedence inequality holds, including branches and paths crossing
   shelves. Local polarity, timing ladder and functional orientation gates pass.
4. Every placed packing envelope lies within page bounds; occupied body/text/pin
   geometry and planned corridors meet ownership, clearance and capacity rules.
   No body/text/reservation collision or unsupported exception exists.
5. Every global route attachment coincides exactly with a real transformed
   gateway or permitted tap; every required gateway witness reaches its actual
   pin through preserved local conductor geometry.
6. Every required net has one canonical graph with all terminals, geometric
   components and authorized label joins enumerated. Partitions equal the IR;
   no unintended cross-net contact or unmatched island exists.
7. Every wire endpoint has a semantic attachment/intent; junctions match actual
   branch degree and unrelated crossings never create electrical union.
8. Canonical length/detour gates, final occupied envelope/page gates and exact
   historical point-extent spread gates pass. New geometry cannot obtain an
   allocation merely by creating its own post-hoc reservation.
9. Serialized-in-memory geometry and independently resolved pin endpoints match
   the certified scene. The certificate becomes invalid on any mutation.

The emitter accepts only a certified immutable candidate. On failure, preserve
nonrelease diagnostics and the failed proof, never a successful project. Keep
proof errors separate from invalid electrical input, missing capabilities,
budget exhaustion and proven infeasibility within a stated model.

Acceptance remains:

`generator precondition proof AND independent emitted-artifact verification`.

After writing the candidate, run real locked KiCad **10.0.6**, fresh XML export,
zero-violation ERC, independent identity/partition comparison, actual geometry
and path/layout checks, and real SVG rendering. The post-emission observer derives
pins from embedded definitions and exported membership, and obligations from the
accepted design, never from the generator certificate. A certificate cannot waive
an independent failure. Preserve every observed metric and witness even when an
earlier gate fails; unevaluated checks are explicitly `not_evaluated`.

Basic integer geometry helpers may be shared, as today, but test total connectivity
with an independently authored reference graph traversal and hand-authored
mutations. A shared canonicalizer bug must not let the planner and observer
certify each other. Keep original T-branch/subdivision positives and all negative
controls. Never weaken KiCad ERC or turn the V6-3 singleton nets into allowed
exceptions.

Preserve attempt evidence on post-emission failure. In V6-2/3/6,
`composition.json` retains actual attempt counts while the standalone failure
`layout_attempts.json` is empty and its budget says zero; build error handling
must not replace a completed ledger with absent exception attributes.

## 13. Finite interaction-coverage development protocol

Before layout implementation, author the probe manifests, independent expected
partitions/obligations and coverage table. Freeze them as development inputs.
They are intentionally visible; they are not a new blind corpus. Do not tune
probe topology after a failure. Track topology ancestry and renamed/field-width
variants as the same base design.

Use this finite factor vocabulary; values count semantic objects, not refdes:

| Factor | Levels for coverage |
|---|---|
| Serial depth | 1, 2, 3+ ordered functional/passive stages |
| Parallel breadth | 1, 2, 3+ incomparable consumers |
| Active-core count | 0, 1, 2, 3+ timer/regulator/active amplifier functions |
| Shared package count | 0, 1, 2+ multi-function packages |
| Shared supply consumers | 1, 2, 3+ functional/support groups |
| Signal branch degree | 1, 2, 3+ |
| Reference dependency | External reference; internal generated reference; distinct reference domains |
| Support count | 0, 1–2, 3+ consumer-associated cells |
| Protected paths | Local only; cross-fragment; mixed local/cross-fragment |
| Distributive consumers | 1, 2, 3+ required gateway islands |
| Shelves/bands | One; multiple; multiple with legal backfill/interleaving |
| Text stress | Nominal; 24-character value plus 20-character required label |

Cover all legal level pairs within each mandatory interaction row below, using
small synthetic fragments where electrical circuit authorship is unnecessary.
Cross-row combinations are not implied to be covered. Selected three-way rows
require all listed levels' legal triples. Record unsupported/impossible factor
combinations with a semantic reason before execution, never because layout failed.

| Coverage row | Interaction to exhaust |
|---|---|
| I1 | Serial depth × branch degree; selected triple: passive intermediate × active successor × multiple bands |
| I2 | Reference dependency × distributive consumers; selected triple: internal reference × parked input × shunt return |
| I3 | Active-core count × shelves/bands; selected triple: two tall independent cores × shared package × long text |
| I4 | Parallel breadth × protected-path class; selected triple: unequal consumer shapes × cross-fragment bound × sibling vertical order |
| I5 | Shared supply consumers × support count; selected triple: 3+ gateway distribution × multiple shelves × restricted supply entry |
| I6 | Shared package count × reference dependency; plus text stress × support count and text stress × branch degree |

Generate a deterministic covering set for these finite rows by lexicographically
choosing the next legal factor assignment covering the most uncovered required
cells, tie-breaking by the factor vector. Freeze the resulting finite case list
before geometry tuning. No random or unlimited fuzz loop is a completion gate.
Report covered/required cells for each row and the selected triple cells; do not
report one aggregate percentage that hides a missing row. Generic graph tests
cover combinatorics; at least the four real circuits below validate end-to-end
meaning. Add real probes if an interaction is represented only by unrealistic
synthetic geometry. A passing cell needs all its expected invariants, not merely
successful generation.

Required boundary/mutation dimensions apply across this matrix: exact/below/above
80 mm and spread limits; detour feasibility under alternate trunk selection;
connector present/absent on a shared reference; both legal pin-unit allocations;
set-array permutations; reflected/translated synthetic envelopes; extra
independent consumer; and changed sibling ordering. Keep unsupported transforms
negative rather than treating every reflection as a legal schematic variant.

### Four new required real development probes

These are design requirements for M2h2, not IRs authored by this review. Use the
existing qualified assets and relationship vocabulary. Keep all source assertions
and unused-unit biasing explicit. Freeze exact terminal inventories and expected
paths before running the layout. Comparison with v2–v6 relationship inventories
shows these are new combinations; the implementation session must confirm
non-isomorphism/ancestry against the full known IRs before freezing them.

| ID | Fixed composition | Interaction and independent expectations |
|---|---|---|
| DP1 | Passive root RC feeds three RC siblings; one sibling feeds a further series/LED load, with three external branch outputs and common return. No active part. | Depth 3+, breadth/degree 3+, mixed explicit local/cross-fragment paths. Every ordered edge remains forward; all shunts stay local; siblings need no mutual x order. Add the stated long-field stress derivative. Distinct from M2g2's two-sibling passive fanout. |
| DP2 | Two NE5532 packages, one active function per package (buffer and inverting gain), each other function explicitly parked; one authored divider generates a shared internal reference for both packages' bias/reference consumers. No connector on that reference. Separate input/output interfaces. | Package count 2, internal reference, parked inputs and support islands. Explicit reference distribution must reach every required island; all six package occurrences and exact pins accounted for. Adding a reference connector in a metamorphic derivative may not change functional local geometry or rescue missing connectivity. No Sallen-Key/output-RC template. |
| DP3 | Two independent astable timers on one external supply, each feeding its own RC output filter; separate timing/discharge/control/output nets, two output connectors and common return. | Two tall repeated cores, depth 2, shared distribution and multiple bands. Requires real compact/support alternatives, no full-chain rigid-row assumption. Long-field stress on one output; both ladders remain ordered and support paths remain explicit. Distinct from prior dual-timer LED/mixed-load and dual-timer/amplifier designs. |
| DP4 | One qualified regulator supplies two independent timers; one timer output fans out to two distinct RC filters, the other drives one LED branch. No amplifier package. | Three active cores, shared supply/support, signal degree 2, multiple consumer clusters and restricted exits. Supply tree plus local support must meet 250 mm; output branches meet precedence/locality. Distinct from V4's unloaded regulated dual timers and V5/V6 single-timer branch compositions. |

These four are the minimum, not four substitutes for the coverage table. Their
size is a stress on the existing single-sheet envelope, not authorization to
waive it. A failing probe remains a development failure with preserved evidence;
if the milestone cannot satisfy the fixed probes, report incomplete rather than
simplifying them or claiming a newly narrowed capability after the fact.

## 14. Exact next Sol milestone and generic tests

Implement **M2h2 — obligation-complete bounded composition** in one fresh Sol
session, sequenced by contracts rather than V6 case IDs:

1. Freeze new probe/coverage expectations and historical integrity hashes. Add
   generic failing tests of total-net completeness and terminal-based constraints.
2. In `m2_semantics` derive complete precedence, local-path and presentation-net
   obligations; replace exclusive edge-kind assumptions and connector-dependent
   completeness with independent typed properties.
3. In `m2_geometry` / `m2_fragments` certify actual local islands and every
   terminal witness, measured meaningful variants and all local bounds.
4. In `m2_pack` implement bounded partial placement, constraint propagation,
   structural coverage and compaction; in `m2_route` implement distribution plans
   and whole-net length feasibility with typed conflict feedback.
5. In `m2_compose` maintain the shared budget ledger, proof-complete immutable
   candidates, global deduplication and feasible-candidate ranking. In `m2a.emit`
   enforce the certified-scene boundary and in-memory serialization check.
6. In `m2b`/observation retain independent authority and add missing total-graph
   diagnostics; in `m2b_build` preserve proof/attempt/observed evidence on every
   exit. Then run the whole qualification and anti-overfitting audit.

Module factoring is allowed; the specified responsibilities and contracts are
not optional. No case-specific layout dispatch, solver, additional page sizes,
new symbol families or hidden alternate historical renderer is permitted.

Required generic tests, authored independently of V6 coordinates/topologies:

| Test group | Required falsification |
|---|---|
| Precedence | Real semantic planning of an active→passive→active path plus a sibling, through alternate shelves/variants and repack. Assert exact terminal inequalities; a reversal with perfect electrical partitions must fail before emission. |
| Internal net completeness | Shared internal reference with multiple islands and no connector; a parked input and passive return. Removing a branch or approved label must fail total coverage even when every pin has a stub and every gateway net string is correct. |
| Gateway proof | Multi-witness gateway with only one witness reachable, off-pin by one grid unit, stale transformed escape, removed local segment, and wrong physical pin definition. All rejected; legal subdivision and translation pass. |
| Canonical graph | Disconnected same-net segments, missing T/four-way junctions, unauthorized crossing, duplicate/foreign-owned interval, label-only protected path and extra dangling endpoint. Separate independently authored graph oracle and real KiCad mutations. |
| Locality | Unequal parallel consumer envelopes; exact 80 mm passes, 80 mm plus one coordinate unit fails. Force alternative sibling/band choice without changing semantics; analogous 60 mm support and existing feedback boundaries. |
| Packing diversity | Two tall synthetic chains where legal interleaving/compact variants fit and row stacking fails. Exhaustive tiny reference enumeration distinguishes structural classes. Seven identical-size escape variants do not count as aspect coverage. |
| Distribution | Producer with three restricted-access consumer clusters; fewer-bend long tree loses to a hard-feasible trunk. Charge local and shared global intervals exactly once. Repeat with net renamed and a reference/control role. |
| Repair dispatch | Feed real typed detour, span, order, blocked-gateway and growth conflicts. Assert the intended structural/variant change, no string parsing, no false growth claim, no budget reset and no silently skipped eligible repair. |
| Selection | Candidate A passes collision/spread but fails a known order/span gate; candidate B passes all proofs. A cannot be emitted. Independent rejection of B can try the next proved candidate within the same ledger. |
| Reservations/emission | Late text/source/route growth, occupied-but-unallocated channel and serialization endpoint change invalidate certification. No `.kicad_sch` is written from a failed certificate. |
| Metamorphic/anti-overfitting | Set permutations preserve exact decisions; ID/refdes/net renaming preserves semantic gates; supported unit exchange preserves physical identity and obligations; unrelated consumer additions leave normalized local certificates unchanged. Text-width changes can change geometry. |
| Evidence | Fail before packing, during route, at proof, and after KiCad; preserve all prior attempts, all available metrics and honest `not_evaluated` fields. Repeated states have separate counters. |

### Qualification and completion criteria

Require all of the following; any missing item leaves M2h2 incomplete:

- All 42 M2g2 positives, all eight V6 cases now explicitly **known regressions**,
  the four new base probes and their required stress derivatives pass unchanged
  numerical gates, exact independent electrical identity and zero ERC violations.
  Retain original invalid V3-8 as a negative and all established M1/M2 tuning,
  observer, identity and mutation tests. Do not overwrite their evidence.
- Every positive, including stress derivatives, has **five clean builds** in new
  directories with real locked KiCad **10.0.6**, fresh XML/ERC/SVG, identical
  compiler-owned project bytes, canonical geometry, obligation/certificate and
  candidate/repair decisions, complete metrics and normalized report signatures.
  Normalize only existing documented path/date/title fields; report runtime
  separately. Do not normalize variant choices or failed proof differences away.
- All mandatory interaction rows/triples have complete recorded coverage or
  preregistered semantic impossibility witnesses. Generic proofs have negative
  controls and the tiny independent exhaustive placement/graph checks pass.
- Source-level anti-overfitting review finds no design IDs, filenames, refdes,
  net spelling, topology hashes, exact inventory dispatch or named family-pair
  handlers in geometry decisions. Inspect structural conditionals, not only
  literal matches. New probes are frozen before tuning and remain unchanged.
- Report per-case maximum metrics, local/global tree lengths, component coverage,
  variant diversity, structural coverage, best rejected candidates, exact budget
  counters and prediction-versus-observation differences. No claimed repair may
  be a null operation hidden behind a round label.
- Complete pytest, Ruff lint/format and applicable whitespace/link checks pass.
  Historical corpus/IR/freeze/evidence hashes remain unchanged. Store new reports
  under a new M2h2 evidence root; never run old self-overwriting evaluators.
- Record engineering inspection of new real renders for ordering, feedback/timing
  clarity, reference distinction, package/support association, fanout tracing and
  readable fields. State the actual reviewer/method; human review remains pending
  if unavailable. Agent inspection cannot be relabeled human blind approval.

Only after known regressions **and** the new interaction probes/coverage pass
should a separately authorized blind corpus be considered. Do not create,
reserve, sample or author corpus.v7 during M2h2. Do not begin M3 or declare full
M2 PASS from this repair. Stop this review at this implementation handoff.
