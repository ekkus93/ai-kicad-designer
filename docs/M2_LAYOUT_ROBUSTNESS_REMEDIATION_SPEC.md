# M2 layout robustness remediation specification

Status: architectural review and implementation handoff, 2026-09-21.
No remediation is implemented by this document.

## 1. Decision, scope, and evidence boundary

Retain instance-based composition, typed semantic projections, one owner per
symbol occurrence, and independent electrical/layout observation. Repair the
contract between local geometry, global placement, routing, and observation.
The three investigated failures are **not one packing defect**:

- V5-3 is a stale-envelope defect, specifically post-pack text growth.
- V5-6 is a port-escape/obstacle-enforcement defect in global routing.
- V5-7 is an independent explicit-path observer false negative exposed by an
  unsplit T-branch. Its preserved local feedback and inter-block path are wired.

The first two share an architectural implementation gap: a packed fragment is
not an enforceable reservation, and later operations can invalidate its
geometry assumptions without renegotiation. The third needs an independent
observer correction and canonical tree handling, not a new motif arrangement.
None demonstrates an inadequate electrical IR or a need for whole-circuit
templates, a general maze router, hierarchy, or CP-SAT.

The next implementation milestone is **M2g2 — route-aware layout closure and
branch observation repair**, assigned to a fresh Sol session. Sections 4–13 are
its normative handoff. Existing governing specifications are sufficient:
[SCHEMATIC_LAYOUT_SPEC](SCHEMATIC_LAYOUT_SPEC.md), especially sections 4–7,
9–11, already require occupied envelopes, corridors, bounded repair and
canonical net trees; [EVALUATION_PLAN](EVALUATION_PLAN.md), sections 3–4 and 8,
requires independent observation and subdivision-invariant connectivity.
[M2_COMPOSITION_REMEDIATION_SPEC](M2_COMPOSITION_REMEDIATION_SPEC.md), sections
4, 6 and 7, already specifies much of the unrealized contract. This document
refines implementation choices and budgets for M2g2; it does not revise their
acceptance thresholds or their historical milestone declarations.

### Evidence provenance and discrepancy

The request states corpus.v5 passed 5/8. The available
[SUMMARY](../fixtures/m2blind_v5/SUMMARY.md) and
[automated results](../fixtures/m2blind_v5/automated_results.json) both record
**4/8**, with passes V5-2, V5-4, V5-5 and V5-8, each reproduced five times.
V5-1 additionally failed `wire through body: VPLUS, cpos`. Do not silently
replace this record with 5/8 or retroactively promote V5-7 after diagnosing
the observer. The supplied earlier progression is 2/8, 3/8, 7/8; the available
V5 record ends it at 4/8. V5-1 remains a required known regression, while the
detailed causal analysis here concerns the requested three cases.

Reviewed the three failure directories in full: their JSON reports, raw CLI
results, emitted project/schematic files, exported XML, SVG structure and
configuration evidence where present; the input IRs and composition records;
the V5 automated/reproducibility/regression records; the M2f2 summary and
tests; and the responsible source functions cited below. V5-3 and V5-7 each
preserve 18 files. V5-6 preserves only `reports/failure.json`: there is no
failed scene, composition record, export, or render for that case.

Current HEAD is `7c28afa28b88761cc35ddfecae4dfa8f4da60ba9`. Every current
`src/` file listed in the V5 implementation freeze matches its recorded hash.
Read-only, in-memory reconstruction below therefore uses the frozen
implementation. It is analysis, not new KiCad qualification. No historical
evaluator was executed, no frozen artifact was rewritten, and no new circuit
was built. SVG structure inspection is not human engineering approval.
Neither `.local/` nor `research/legacy_openclaw/` was inspected.

## 2. Root causes and limits of the evidence

### 2.1 V5-3: measured packing followed by unmeasured text movement

The [composition record](../fixtures/m2blind_v5/runs/V5-3/run1.failed/reports/composition.json)
rejects the side-affinity candidate at 226.06 × 63.50 mm and accepts the
lower-affinity candidate with a prospective content bound of
201.30 × 134.62 mm. Electrical comparison passes; real KiCad ERC has zero
violations. The [failure](../fixtures/m2blind_v5/runs/V5-3/run1.failed/reports/failure.json)
is the observed spread gate.

Recomputing the current observer's extent definition from the preserved
schematic/XML gives **204.47 × 140.97 mm**. The vertical extremities are the
feedback capacitor's Reference position at y=25.40 mm and the lower reference
wire/label at y=166.37 mm. The capacitor's reference was initially at
(107.95, 33.02) mm in placed fragment coordinates, then moved to
(97.79, 25.40) mm. Its fragment envelope begins at y=29.21 mm. Positive
decoupler text also moves left from x=40.64 to x=20.32 mm, outside its packed
envelope beginning at x=25.908 mm. These coordinates are diagnostic evidence,
not proposed geometry rules.

`m2_fragments._envelope` includes current symbol bodies, local wires, label
anchor points, and approximated reference/value rectangles, padded by two
pitches on each side. It does **not** omit support bodies or existing local
feedback wires. But `_finish` measures the default text positions before
`choose_text_slots` and `_clear_nonpassive_text` run. In
`m2_compose.compose_with_evidence`, both text selectors run after packing and
inter-block routing; neither updates the fragment envelope or calls the packer
again. `measure` checks margin points and collisions, but not the 210 × 140 mm
spread limit. The independent observer eventually rejects the sheet.

Thus optimistic *final* envelopes are demonstrated, but route expansion alone
is not the observed cause here. The accepted inter-block segments remain
inside the placed-envelope union. Text relocation invalidates the size bound.
The M2f2 subtraction of `4*PITCH` from the envelope union is sound only for
unchanged contained geometry with that exact uniform padding. It is not a
budget for unmeasured text, flags, or new routing tracks.

M2f2 repaired false supply ordering and redundant global gaps. It could not
make a one-way packing estimate authoritative for geometry subsequently
changed by a different stage. This failure does not prove single-sheet
infeasibility; no alternative final layout is certified by this review.

### 2.2 V5-6: the global route traverses local support

The [preserved failure](../fixtures/m2blind_v5/runs/V5-6/run1.failed/reports/failure.json)
reports `wire through body: VPLUS, regulator_output_c`. It occurs before
composition evidence is published. The automated summary's `packing:
not_completed` is inferred from absent artifacts, not a stack trace proving
that packing was never executed.

In-memory reconstruction with the matching source completes packing:
`candidate-1:side-affinity:pass:measured=184150000x92710000`.
The global VPLUS route then contains the vertical segment
(199.39, 43.18) → (199.39, 72.39) mm. The output capacitor body occupies
x=197.358–201.422 mm, y=65.278–66.802 mm: the segment passes through it.
The source port declares a **right** escape, but `_orthogonal` takes a
vertical first leg because the target lies to the left. It neither consults
the direction nor tests body, text, local-wire, or pin obstacles.

`_power_stage_fragment` positions support at fixed offsets from the regulator
and explicitly connects it locally; its output port happens to share the
capacitor column. This can be a legal local construction when external routing
honors a rightward escape. It is not proof that the support capacitor itself
must move. `_vertical_escape_x` consults source body obstacles only in one
multi-target lower-shelf routing case; it is not used for this single-target
route and is not a common route-feasibility predicate.

Support is consumer-associated semantically, but no access corridor is
reserved jointly with it. Local bodies are measured; downstream escape
direction, unrelated local routes, text, and the complete global obstacle set
are not coordinated. A regulator coordinate patch would leave the same error
possible around package decoupling, timer support, and ordinary shunts.

### 2.3 V5-7: a real T-branch is invisible to the path traversal

The [composition record](../fixtures/m2blind_v5/runs/V5-7/run1.failed/reports/composition.json)
contains two signal edges from the high-pass fragment to the amplifier units
and a HIGHPASS tree. The [failure](../fixtures/m2blind_v5/runs/V5-7/run1.failed/reports/failure.json)
says `series/amplifier`, not `feedback source`, `feedback sense`, or
`direct feedback`.

The emitted trunk is (53.34, 26.67) → (106.68, 26.67) mm. The nearer
amplifier branch begins at the trunk interior (58.42, 26.67) mm and has an
actual emitted junction there. Its branch ends at (58.42, 40.64) mm and joins
the local wire to U1 pin 3. The farther branch reaches U1 pin 5. XML places
both inputs, the series capacitor output and the shunt resistor on HIGHPASS;
electrical comparison and ERC pass.

Inside `m2b.check_observed_layout`, `wired_path` starts with the source pin
coordinate, finds segments containing a reachable point, and adds only each
segment's two endpoints. Reaching the trunk adds its ends but never its
interior T point. Traversal from the source therefore cannot enter the nearer
branch. It is asymmetric with respect to the traversal starting point and
depends on segment subdivision. `m2a.observe` does not expose junctions to
this traversal at all.

A separate geometric graph made by splitting the preserved wires at incident
endpoints reaches the shunt and **both** amplifier inputs without label edges.
Passing an in-memory split-segment observation through the existing checker
passes all its layout gates, including 203.20 × 57.15 mm observed content,
76.20 mm maximum explicit local span, and 27.94 mm support locality. This
diagnostic neither changes the emitted file nor requalifies the frozen run;
its changed wire-count/bend metrics are not historical metrics.

The router emits one unsplit trunk plus branch segments and junctions. That
exposes the observer bug and falls short of the specified canonical split
tree. Correct **both**: normalize compiler net trees and make the independent
observer accept equivalent legal segment subdivisions. Merely splitting the
generator output would conceal an unsound acceptance oracle. Conversely,
electrical net equality alone cannot discharge an explicit-path obligation.

No preserved local protected wire was removed or rerouted in this case.
Nonetheless, `protected_wires` is only a set of indices copied/count-reported
by composition, and `tap_segments` admits every wire on a port net. The global
router consumes neither field. Real protection against future composition
damage is still missing and belongs in this repair.

## 3. Current architecture and test coverage

Relevant implementation boundaries at the reviewed revision:

| Responsibility | Source and finding |
|---|---|
| Occurrence ownership | [m2_semantics.py](../src/ai_kicad/m2_semantics.py), `semantic_plan`, and composer owner checks enforce a total unique owner map. Keep it. |
| Local construction/envelopes | [m2_fragments.py](../src/ai_kicad/m2_fragments.py), `_finish`, `_envelope`, and the six builder families. Bodies/support/local wires are included; final text, label glyph extents and explicit access reservations are not fully modeled. |
| Variants | `fragment_variants` always returns a singleton `.v0`. Packer support for up to eight variants does not make alternative local shapes exist. |
| Packing | [m2_pack.py](../src/ai_kicad/m2_pack.py), `_signal_chains`, `_make_units`, `_pack_shelves`, `pack_fragments`. Typed shelves are useful, but return at the first pre-route fit. Connected signal DAGs are flattened into a topological row, serializing incomparable fanout siblings. There is no route-demand reservation or final-envelope feedback. |
| Routing | [m2_route.py](../src/ai_kicad/m2_route.py), `_orthogonal`, `_branch_attachment`, `_vertical_escape_x`, `route_between_fragments`. Simple coordinate recipes with one special shared-trunk case; no common obstacle-aware admissibility test. |
| Final local mutation | [m2_compose.py](../src/ai_kicad/m2_compose.py), `compose_with_evidence`, changes fields after routing and then measures once. |
| Collision/quality authority | [m2b.py](../src/ai_kicad/m2b.py), `measure` and `check_observed_layout`. Useful rejection gates; prevention and normalized geometric connectivity are incomplete. Endpoint-equals-pin exemptions also need to be limited to actual legal pin conductors. |
| Evidence publication | [m2b_build.py](../src/ai_kicad/m2b_build.py), `build`, writes composition only after composition succeeds, layout only after its checker returns. All `InputError`s become `invalid`, losing layout-failure classification and partial metrics. |

`RouteTree.edges` records semantic edges, not exclusive ownership of actual
wire intervals. The composer concatenates local and global segments. The RC
builder even emits overlapping same-net local output segments. Global
junctions can be added at ordinary bends/root ends rather than derived from
geometric degree. These are generic normalization/ownership deficiencies,
not evidence of duplicate symbol occurrences.

[test_m2f2.py](../tests/test_m2f2.py) tests typed shelves, power fanout,
permutation, refdes-independent semantic decisions, synthetic rectangle
overflow and the known V4-7 preflight. Its synthetic rectangles contain no
wires/text, and its V4-7 assertion stops before independent observation.
[test_m2e1.py](../tests/test_m2e1.py) checks nonempty protection metadata and
deterministic orthogonal fanout, but does not prove that the router respects
protection or that interior branches are reachable from every leaf.

There is no dedicated `tests/test_m2g1.py`. M2g1's relevant qualification is
[evaluate.py](../fixtures/m2blind_v5/evaluate.py), its inherited
[V4 evaluator](../fixtures/m2blind_v4/evaluate.py), and the preserved regression
and reproducibility reports. Its 147-test regression pass and four five-run
passes are useful evidence, not coverage of these missing contracts. Preserve
the negative layout tests in `test_m2c1.py` and the identity/electrical tests
in `test_m2b.py` and preceding milestones.

## 4. Placement and measured-envelope contract

Use integer nanometers and the qualified 1.27 mm pitch, with exact asset pin
coordinates. A complete local variant is immutable. A change to support,
field position, local route, or port escape produces a new measured variant;
it cannot silently mutate an already packed object.

Each variant must carry these separately typed records:

| Record | Required fields and invariant |
|---|---|
| Occupied geometry | Bodies, pin conductors/endpoints and pin text, required property/label text, local wires/junctions, approved source-assertion glyph allocation. Every item has an owner and provenance. |
| Content envelope | Bounding box of that actual geometry, without an anonymous removable padding constant. Also expose the current observer's point-based extent as a separate prospective metric. |
| Keepouts/reservations | Body/text clearance regions; protected path corridors; pin escapes; allowed interface access windows. Include clearance class, owner, net permission and geometry. Distinguish exclusive occupancy from usable reserved channel capacity. |
| Packing envelope | Conservative bound of occupied geometry plus its local reservations. Clearance is applied once; shared channels are explicit placement resources, not padding later subtracted from a global union. |
| Port access | Net, exact physical-terminal witnesses, wired-island ID, local anchor, escape direction, exact escape polyline to a boundary gateway, permitted approach directions and tap windows. |
| Obligations | Required terminal-to-terminal explicit paths, support spans, fixed topology, and presentation scope. Every obligation is assigned to a local or global route owner. |

Choose required text slots against local bodies, pins, local wires and reserved
escapes **before** measuring the variant. Record the chosen slot and its full
conservative glyph rectangle. Use the pinned font/size or the documented
conservative estimator validated against real renders; text length affects
geometry, text spelling does not choose a rule. Include net-label width and
pin-name/number extents, not just their anchor coordinates. Preserve existing
hard metric definitions and add full-content containment diagnostics rather
than misnaming a new rectangle metric as the historical point-based metric.

Global placement reserves channels from the port/net demand before declaring
a candidate routable. Allocate one track per unrelated net where their spans
overlap, with the qualified clearance; a same-net tree shares capacity.
Reserve entry gates through fragment halos and around feedback/support bands.
Do not make a fragment's entire interior available because its rectangular
envelope has unused white space. A channel may use only declared access space.

The enforceable sequence is:

1. Construct and locally validate a complete variant, including support,
   text, protected wires and escape stubs; measure its envelopes.
2. Place variants and shared channel reservations; verify separation,
   typed orders, exact transformed gateways and prospective size limits.
3. Route only through admitted access windows and channels, checking every
   segment and branch point against the complete scene.
4. Compute the actual union of placed local content, global wires, junctions,
   labels and source glyphs. Compare it with the reservation union and both
   the page and spread bounds. Attribute every outward delta to an item/owner.
5. On growth or blockage, return a structured conflict to bounded repair.
   On success, freeze geometry for emission and independently observe it.

In symbols, `local_content(v) ⊆ local_reservation(v)` and
`final_content ⊆ union(transformed local reservations, shared route reservations)`.
The latter is checked, never inferred from successful rectangle packing.
The final observed point extent must remain at most **210 × 140 mm**; full
body/text extents must also fit the qualified page margins. Unallocated growth
invalidates a candidate even when it happens to fit the page.

Conservative envelopes, planned corridors **and** bounded feedback are needed.
Conservatism covers a selected variant, not every conceivable future placement
of its text. Reserving the union of all distant text slots would unnecessarily
waste space. A selected alternate slot outside the reservation requires
remeasurement/repack. A blanket extra margin cannot substitute for this rule.

## 5. Geometry and routing ownership

Keep the existing unique occurrence owner. Extend ownership to routing
obligations and canonical conductor intervals; ownership is not ownership of
an entire electrical net by one fragment.

| Geometry | Sole authority | Permitted composition action |
|---|---|---|
| Local feedback/filter/timing tree | Owning fragment variant | Translate with fragment; replace only by a validated variant preserving terminal topology. |
| Local support wires | Consumer's fragment, including the dedicated package-power owner when applicable | Same rule; global distribution terminates at its gateway, not at an arbitrary support lead. |
| Port escape up to gateway | Fragment variant | Fixed local geometry/corridor for the selected variant. |
| Inter-block signal/branch wiring | Net-level global tree owner for the approved explicit island | Attach certified gateways and legal taps; reroute its own segments only. |
| Shared branch node | Tree owner that introduces the branch | Atomically split incident segments and record attachments; local tap permission is required to split a local segment. |
| Distributive rail | One net/island distribution owner | Connect all requested gateways using one tree; local support subtrees remain owned and preconnected. |
| Serialization normalization | Canonicalizer | Split/deduplicate equivalent same-net geometry without moving it or changing topology; preserve owner/provenance spans. |

Form one obligation inventory per `(net, approved explicit island)`, including
all required terminal incidences. Contract each already connected local tree
to its certified gateways. An inter-block semantic edge requests an attachment,
not a second independent route between endpoints already in the tree.
Reference/support/package relations continue to impose no signal-stage order.
Approved labeled interfaces retain their scope plan; labels never discharge
an explicit local obligation or become a routing-congestion fallback.

Validate every port witness against the actual terminal net and local wired
island. This also catches latent metadata errors: `_amp_block` currently uses
the plus terminal as a reference witness even where it is the signal input,
and support-edge occurrence selection can pick the first functional unit
rather than the power unit containing the consumer pin. Resolve by actual
pin/unit membership; do not reassign symbol owners to make metadata agree.

Global routes may neither cross nor merge with protected geometry merely
because net names match. At a certified same-net tap they may add a branch;
the local owner grants that exact window and the canonicalizer splits the
conductor there. No layer may sever a protected path, move another owner's
wire, or cross a protected corridor outside such permission. Cross-net
crossings remain forbidden under the current qualified M2 gates.

## 6. Consumer-local support and usable escape paths

Replace support coordinates used in isolation with a reusable support-cell
construction. Inputs are the exact consumer terminal and net, support terminal
roles and body/text geometry, return identity, local protected corridors,
allowed band sides, and the consumer's boundary gateway choices. No downstream
circuit identity or reference-designator rule is an input.

Construction order:

1. Fix the consumer's pin conductors, motif corridors and primary port escapes.
2. Enumerate allowed support bands (above/below or lateral where pin semantics
   permit). Reserve the support's body, fields, exact pin entry and return exit.
3. Attach its supply/control/shunt lead to a certified point on the local tree,
   leaving a continuing route to the external gateway. A T at the conductor
   is allowed; traversing the support body or using its body as an escape is not.
4. Route local support explicitly, validate all collisions and spans, then
   include the complete cell and access space in the variant envelope.
5. Reject an obstructed band locally; expose another validated variant. If a
   global route later blocks the gateway, reroute globally before moving support.

Distance is measured between the actual associated pins, using the unchanged
60 mm support and 80 mm local limits. Prefer compact groups within these
limits; do not optimize distance by superposing symbols or consuming an exit.
Keep support within its owner even when a nearby unrelated consumer shares a
rail. Preserve separate reference/supply domains and source assertions.

Apply this cell to regulator IN/OUT bypass, package positive/negative
decoupling, timer control/supply support and passive shunts. Timer timing
ladders and op-amp feedback add protected corridors to its obstacle input.
Part adapters may define legal pin escapes and support polarity. They may not
define a collision coordinate for a particular circuit. A legal rightward
regulator exit need not move its capacitor merely because a distant target is
below or left: the global route must first traverse the reserved escape.

## 7. Protected topology and independent observation

Replace `protected_wires` as the sole contract with `ProtectedPath` records:
`id, relationship_origins, owner, terminal_pairs, net/island, required component
transitions, local tree edges, corridor geometry, allowed tap windows,
maximum span, label_break_budget=0`. A feedback resistor creates two explicit
wire obligations on its respective nets; never treat the component body as a
wire. Cross-fragment series-to-input obligations reference gateways and remain
explicit, even when the path branches to several consumers.

For each selected variant, certify local geometric connectivity without
labels. Save a normalized topology signature and translated-geometry digest.
After routing, independently of the router's success flag, check that its
protected local geometry is unchanged modulo translation and harmless
subdivision, all required terminal pairs remain explicitly connected, and
added branches occur only at certified taps. Variant replacement may change
shape but must preserve the obligation signature and revalidate spans.

The final observer continues to derive pins/geometry from emitted definitions
and fresh XML, and required paths from accepted semantic relationships rather
than the generator's chosen owner list. Correct its traversal as follows:

1. Parse actual junctions as well as wires, physical pins, labels and bodies.
2. Build an undirected conductor graph from emitted geometry. Split wires at
   endpoint-on-segment contacts, incident pins and valid junctions; deduplicate
   collinear same-conductor intervals. Classify interior/interior crossings
   separately: no junction means no electrical union. Do not union isolated
   wires just because exported net names match.
3. Check electrical contact legality and visible junction requirements against
   actual geometry. A legal T contact is connected even if the trunk was not
   serialized as two segments. Require visible branch junctions for the M2
   presentation rule; do not infer junction presence from intended metadata.
4. Evaluate protected reachability within wired components only. Labels help
   identify the electrical net but add no edges for this test. Reachability
   must be symmetric and invariant under wire ordering, reversal, subdivision
   and equivalent collinear normalization.
5. Preserve independently measured span, detour, body/text and page gates.
   Normalize geometry before count/length/bend metrics so splitting cannot
   manipulate them. Keep raw segment counts as a separately named diagnostic.

The observer remains final authority. Correcting its graph algorithm is not
weakening the explicit-path requirement. Test it against manually authored
wire graphs and real KiCad outputs, including legal unsplit T positives and
label-only/detached negatives. Do not share the planner's topology cache with
the observer. Geometry arithmetic can be shared, but its observed inventory
and connectivity must be rebuilt from artifacts.

## 8. Branch points and bounded channel routing

Keep constructive routing on sparse orthogonal channels. Replace the
single-target/multi-target special cases with one tree-attachment path using
the same feasibility predicate for every segment, regardless of fanout.

Route obligations in this order: protected cross-fragment paths, other
constrained signal/branch connections, then distributive rails. Within each
class sort by fewest legal gateways, descending fanout, stable net/island ID.
Local protected paths and support wires are already fixed obstacles.

For each net/island:

1. Seed the tree with its certified source gateway if there is a verified
   source; otherwise use the most constrained gateway, then stable port ID.
   No electrical direction is invented for passive/reference nets.
2. Consider every unconnected required gateway against the current tree.
   Candidate taps come from declared local windows, global tree nodes,
   orthogonal projections of gateways onto global segments, and intersections
   of their x/y tracks with reserved channels (a bounded Hanan-style set).
3. Exclude candidates inside body/text/pin keepouts or protected corridors,
   without incident route capacity, or requiring an illegal approach. Include
   downstream gateway escape demands; do not occupy another pending gateway's
   only reserved track. Retain at most 32 taps per attachment, sorted by
   Manhattan lower bound, required bend lower bound, x, y and stable ID.
4. Try straight, one-bend, then two-bend connections over legal endpoint and
   channel tracks. If none succeeds, search the sparse rectilinear visibility
   graph formed by gateways, tap candidates, inflated obstacle boundaries and
   reserved lanes. No sheet-wide fine-grid maze expansion.
5. Select a feasible attachment by `(added reader jumps, pending-gateway
   capacity deficits, added bends, added wire length, envelope growth,
   target port ID, tap x, tap y, canonical segments)`. Hard deficits are
   rejected first; protected topology is never a soft cost. Charge shared
   conductor length once. Continue until all gateways are connected.
6. Split the tree at each accepted tap, then derive junctions from distinct
   incident ray degree. Ordinary elbows and degree-one roots get no branch
   dot. Do not produce overlapping source-to-tap routes for sibling targets.

Generate at most eight nearest admissible tracks on each allowed side of a
blocked channel/escape, in increasing displacement. Sparse search uses integer
length/bend costs, Manhattan lower bounds, and stable
`(cost, bends, x, y, arrival direction, object ID)` ties. Cap it at 4,096 state
expansions per tested tap and 32 tap tests per attachment. If no route is
found within that count, return a blocked-port/channel witness. These are
operation budgets, not claims that every legal drawing is discoverable.

All candidate segments test the **whole** placed scene, including unrelated
fragment bodies/fields, local support and feedback corridors, previous global
trees, exact pin conductors and pending escapes. Same-net contact is legal
only at an owned tap/endpoint. The point of a shared trunk is traceable
connectivity and reduced duplication, not permission to ignore keepouts.

## 9. Bounded variants, placement, and route-envelope feedback

### Reusable local alternatives

Expose one to eight validated variants per fragment. A variant depends only on
local terminal incidence, symbol geometry, required text, relationship
constraints and the drafting policy. It must have a stable rule/version ID,
the same occurrence inventory and topology obligations, explicit access
choices, and a newly measured envelope. Do not encode complete circuit pairs.

Required alternative dimensions are:

| Fragment class | Bounded alternatives to qualify |
|---|---|
| Regulator/support cell | Support above/below the rail where legal; continuing output gateway right, upper or lower via a reserved local escape. |
| Package power/support | Positive/negative support bands with independent usable gateways; compact wide and compact tall arrangements with exact pin roles preserved. |
| Amplifier/filter | Feedback corridor above/below where legal, outward output access top/bottom/right; recompute fields and bridge clearances. |
| Timer | Alternate control/support bands clear of discharge/timing paths; at least two output escape sides. Preserve timing-ladder order. |
| Passive branches | Horizontal/vertical series/load orientation and shunt band side as permitted by polarity/flow; left input plus upper/lower gateway where useful. |
| Interfaces | Finite field slots and legal contact-access arrangements; keep a multi-contact connector one occurrence. |

Use fixed local rule order, discard infeasible combinations, then retain
distinct access/aspect alternatives up to eight. Do not take the first eight
Cartesian products that all share the same blocked exit. First retain the
best feasible representative of each available escape-side signature; fill
remaining slots by width/height Pareto alternatives, then wire length and
canonical ID. A locally impossible side is recorded, not fabricated by
reflecting physical pin identity. Alternate text slots are resolved within
each variant before its measurement.

### Typed constructive placement

Keep genuine serial chains ordered left to right. Use signal DAG rank and
reachability to distinguish serial successors from incomparable fanout
siblings; siblings may occupy parallel rows/columns without a new order edge.
Never turn supply, support or shared reference into serial progression.
Keep the M2f2 independent shelves and consumer affinity, but permit legal
upper/lower support bands and backfill unused shelf space after complete
reservation checks. Serial chains cannot wrap back to the left to evade the
stage-order gate.

Build a beam of at most eight partial placements. Visit fragments in stable
typed topological order; break independent ties by gateway constraint count,
envelope size, then semantic ID. For each partial placement try each of its
next fragment's at-most-eight variants at four deterministic positions:
aligned successor/peer region, next independent shelf, upper affinity band,
lower affinity band. Each position is the minimum grid-aligned origin
satisfying its separation and order constraints. Reserve demanded channels
as their endpoint fragments become available. Reject collisions, forbidden
orders, blocked gateways and proven size lower-bound violations immediately.

Prune by `(overflow lower bound, unresolved route-capacity deficit, planned
reader jumps, maximum dimension utilization, area, canonical candidate key)`.
Do not compare a hard-invalid candidate with a feasible one using a weighted
score. This explores at most `8 * 8 * 4 * fragment_count` placement expansions
and retains at most eight complete seed candidates. It avoids the present
lexicographic variant-product starvation and first-pre-route-fit return.

### Exact repair budget and allowed changes

For each of the at-most-eight complete seeds, permit an initial routed attempt
and **three repair rounds**, at most **32 full layout/routing attempts per
sheet**. No recursive resetting of that budget is allowed. Partial placement
expansions, route state expansions, attempts and observed qualification runs
are counted separately in evidence. A repeated state digest is skipped and
still consumes the attempted repair round.

| Round | Operation and allowed changes |
|---|---|
| 0 | Compact the seed at legal reservation separation, translate to page, route global trees and measure final content. Local variant geometry is fixed. |
| 1 | Reroute global trees on the next legal reserved tracks/taps indicated by the earliest conflict. Positions and local variants remain fixed. Rebuild trees in canonical net order. |
| 2 | For the earliest unresolved conflict, replace the implicated local variant with the first untried feasible access/aspect alternative; for pure packing slack, try the next legal shelf/band arrangement. Repack all whole fragments with current reservations, then reroute all global trees. |
| 3 | Enlarge the implicated reservation by the measured outward growth, rounded outward to pitch, or by one pitch for a blocked channel; compact/repack with that demand and reroute. If it cannot fit, reject this seed. |

Earliest conflict means lexicographic `(class, obligation ID, owner ID,
coordinates)`, with classes ordered connectivity/protection, body/pin,
text, blocked escape/capacity, page/spread, other quality gates. Return all
conflicts for diagnostics, not only the first. In rounds 2–3, compaction is
two fixed passes (x then y) over the chosen order/separation inequalities,
moving complete fragments to minimum legal positions and rechecking all
reservations. It is not iterative coordinate descent without a bound.

Keep the electrical hypergraph, accepted semantic relationships, occurrence
owners, pin maps, presentation/label budgets, hard orders, page, text size,
thresholds and local topology obligations fixed throughout. A new local variant
may replace shape, never semantics. Do not incrementally drag protected wire
vertices during repack. Transform complete local variants and rebuild global
geometry from the obligation inventory.

Keep reservations monotone within a seed's repair lineage after a witnessed
growth; do not forget a measured text or route extent on the next round.
Other seeds may use different legal variants/reservations. Required text
cannot be moved outside its variant reservation as a late cosmetic pass.

Evaluate complete feasible candidates by the governing feasibility-first
quality tuple, using canonical tree metrics and fixed policy clearances for
crowding. Add canonical candidate identity as the final tie-break. Run real
KiCad/independent gates in that deterministic order. A new observed conflict
may consume an unused repair round for its seed; it may not start a fresh
unlimited search. At most one fresh export/check per full attempt, hence at
most 32 here. A wall watchdog only aborts and records failure; it never selects
a machine-speed-dependent partial winner. Stop with the best independently
passing candidate under the completed deterministic candidate schedule.

## 10. Exact single-sheet page-fit and collision policy

M2g2 uses A4 landscape, existing 20.32/25.40 mm left/top and corresponding
right/bottom margins (usable 256.36 × 159.20 mm), qualified text sizes and
the unchanged **210 × 140 mm** observed spread gate. Do not enlarge the page,
shrink symbols/text, hide fields, increase locality limits, or introduce sheets.

Classify each outcome separately:

| Outcome | Required action/evidence |
|---|---|
| Legal, compactable | Remove only unused global spacing, preserving all reservations; translate the complete content into the page. Translation solves position, never excessive width/height. |
| Needs local alternative | A blocked gateway or indivisible aspect problem identifies a variant/constraint witness; consume round 2 or another seed. |
| Route/text-induced growth | Report old reservation, actual extent, offending item and delta; remeasure and consume bounded repack. No stale packing pass can override this. |
| Proven infeasible within supported model | Supply a valid bound, e.g. every legal variant of an indivisible fragment exceeds the content/page limit, or a mandatory serial-chain minimum width plus required channels exceeds it. State the model and bound. |
| Search did not find a fit | `budget_exhausted`, with all attempted variants, channel choices and conflicts. Rectangle-packing failure alone is not proof of physical infeasibility. |
| Missing motif/access capability | `unsupported` with the specific required capability; do not relabel it electrical invalidity. |
| Contradictory input | `invalid` with electrical/semantic constraint witnesses. |

Preserve separate net-detour (250 mm), local explicit path/fragmentation
(80 mm), support (60 mm), observed feedback (45 mm), flow, endpoint and zero
unrelated-crossing gates. A layout below the spread bounds can still fail
these. Full body/text page containment is prospective and independently
verified; the historical point-extent metric remains reported unchanged.

Prospective and final responsibilities:

| Collision class | Prevent before acceptance | Independent final authority |
|---|---|---|
| Symbol/body or text overlap | Local variant validation and packing of occupied shapes/clearances | Reconstruct emitted bodies and rendered/required text extents. |
| Wire/body or unrelated pin | Segment feasibility against complete scene; permit entry only along the exact intended pin conductor, not any segment ending at any pin of that symbol | Recheck actual segments and actual pins, regardless of planned owners. |
| Wire/text | Select/reserve local fields first; route around body/property/pin/label text | Recompute from actual fields/glyphs; a planner margin estimate cannot waive clipping. |
| Support body/route | Reserve support cell and gateway together; global route tests both | Ordinary body/pin checks plus actual support association/path/span. |
| Local/global route interaction | Protected corridors exclude global routes except certified taps; unrelated routes keep qualified separation | Actual intersections, junctions, protected wired reachability and ambiguity. |
| Branch in keepout | Reject candidate taps and incident escape geometry before tree insertion | Derive junction degree and position from emitted conductors; check bodies/text/pins. |
| Envelope growth/page overflow | Final prospective content/reservation union and bounded repack | Actual emitted point extent plus complete occupied page containment. |

The final evaluator must never use the generator's owner/protection claims to
waive a collision. It may use provenance to explain a failure after observing
it. Improvements to observation must keep independent negative controls and
clearly version additional diagnostics, not replace difficult metrics with
easier proxies.

## 11. Solver decision

**Do not add CP-SAT in M2g2.** It cannot correct late unmeasured text,
ignored port directions, unreserved support escapes or asymmetric conductor
reachability. The evidence contains no demonstrated packing instance where
correct route-aware envelopes and bounded constructive variants have been
exhausted. Those mechanisms are the minimum warranted repair; they are
sufficient to address the identified causal mechanisms, not a proof that
every unseen circuit will fit.

Reconsider a solver only after preserving repeated constructive packing
failures with certified local variants, complete gateway/corridor demands and
independent evidence of a feasible alternative. The possible subproblem is
**finite variant selection and integer rectangle placement under typed
relative, non-overlap, channel-capacity and page constraints**. Local routing,
recognition, terminal membership, protected topology and final acceptance stay
outside it. A rectangle solver cannot certify route feasibility.

Any later experiment retains the governing pinned solver version, seed 0,
one worker, stable variable/constraint insertion, 20 deterministic-time units
per conflicted block and 100 per sheet, with a wall watchdog that aborts.
Require identical hard gates and five clean reruns against the constructive
baseline. This document does not authorize that experiment during M2g2.

## 12. Exact M2g2 implementation and qualification milestone

### Work sequence and boundaries

1. Author generic failing tests and the three new development probes below;
   freeze their semantic expectations before changing layout behavior.
2. Repair observer geometric connectivity independently and prove both
   positive unsplit-branch and negative label-only behavior. Add compiler
   canonicalization with actual-degree junctions and wire provenance.
3. Add the fragment content/reservation/gateway/path records, correct exact
   terminal witnesses, and validate local support/text before measurement.
4. Implement the bounded local alternatives and typed fanout placement, then
   common obstacle-aware global net-tree routing and the bounded repair loop.
5. Publish stage-level evidence even on failure; run complete known regression
   and new-probe real KiCad qualification, reproducibility and anti-overfitting
   audits. Record engineering inspection without claiming blind qualification.

Use existing module responsibilities: `m2_semantics` for terminal/path
obligations, `m2_fragments` for immutable local variants/support, `m2_pack` for
typed placement/channel demand, `m2_route` for global trees, `m2_compose` for
bounded transactions, `m2a.observe`/`m2b` for independent observation and
preflight, `m2b_build` for evidence and failure taxonomy. Small geometry records
or helpers may be factored out; no workflow framework or product redesign.

M2g2 implementation may edit code/tests in its own session. This review does
not. Historical fixtures, blind corpora, freeze hashes and failure artifacts
remain immutable. Put new probes, qualifications and diagnostic evidence under
`fixtures/m2g2/`; do not run a historical evaluator that writes into its own
directory or requires the old implementation freeze.

### Required generic tests independent of V5

| Test | Independently asserted result |
|---|---|
| Final text envelope | A small synthetic local fragment whose default field collides with its own wire chooses another slot before packing. A late outward field move is rejected as growth; a bounded alternate placement fits an independently known limit. |
| Envelope accounting | Nonuniform body sizes, long required labels/values, source glyphs and local feedback/support routes are contained after legal transform. No fixed global padding subtraction hides growth. Test exact-limit and one-nanometer-over-limit cases. |
| Route demand | A two-shelf scene fits pre-route rectangles but needs an extra trunk channel. A known feasible repack must reserve it and pass; the initial state must not pass as final. |
| Universal escape check | Synthetic source support below a rightward gateway, target left/below: single-sink and multi-sink routing both avoid the support and honor the same escape. Repeat with support above and with a target whose entry is blocked. |
| Support substitutions | Same support-cell tests for regulator, package-power, timer control and passive shunt; add an unrelated rail consumer and prove unchanged selected local geometry after normalization. |
| Protected path ownership | A feedback/filter/timing corridor cannot be crossed by another net or tapped by the same net outside a declared window. Supply rerouting cannot alter its normalized path. Legal certified tap preserves it. |
| Unsplit T graph | Hand-authored trunk with at least two interior taps, both wire directions, permuted order, split and unsplit forms: every leaf reaches every intended leaf without label edges. Include branch-at-end and four-way junction cases. |
| Observer negatives | Remove a branch segment but retain same-net labels and a passing electrical partition: explicit-path check still fails. Remove a required junction: presentation check fails. Add an unrelated crossing/junction or move a branch endpoint off trunk: reject the appropriate geometry/electrical error. |
| Tree canonicalization | Duplicate/overlapping same-net segments become one conductor union with provenance. Splitting/merging/reversing segments preserves canonical length, bends, degree and connectivity; unrelated overlaps never normalize into acceptance. |
| Fanout order | One source and three incomparable sinks are not forced into a serial row; two sinks with their own downstream stages retain only real precedence. Shared power/reference never creates signal order. |
| Branch feasibility | Nearest geometric tap lies inside text/support/protected keepout; select a legal reserved-channel tap. Pending downstream escape capacity is preserved. |
| Alternative feasibility | First variant has an obstructed exit, second has a clear exit; first has preferable area. Select second because hard feasibility precedes area. Variant selection cannot depend on circuit name. |
| Bounded failure | Exhaust track/tap/state/seed/repair caps on constructed blockers; repeat state is not retried indefinitely. Report `budget_exhausted`; a separate all-variants-oversize case provides a valid infeasibility bound. |
| Typed identity | Consumer pin resolves to its actual graphical unit; port witnesses belong to the stated net/local tree. One occurrence has one owner, one route obligation has one owner, and every required terminal is covered. |
| Metamorphic stability | Permute set-like arrays and segment ordering; exact canonical output agrees. Rename IDs/refdes/nets consistently and swap supported unit assignments: electrical/quality/ownership invariants agree. Different field widths may legitimately change geometry. |

Tests must include small manually specified geometric fixtures, not only
snapshots produced by the implementation under test. Preserve M1 and M2
identity/mutation tests, all 12 tuning cases and M2f2 typed-packing tests;
strengthen assertions rather than replacing them with packing success flags.
Observer changes require both real KiCad positive controls and independent
mutations. Do not make the observer depend on generator segmentation.

### Three new development probes

These are new development compositions, not corpus.v6. The v2–v5 manifests
and inspected compositions do not contain these topologies. Sol must author
their IR and independent expected partitions/relationship paths before tuning,
record an ancestry comparison, and preserve initial failures. Use only locked
qualified assets and existing relationship vocabulary. Values are ordinary
schematic examples, with no claim of analog performance or manufacturing
readiness.

1. **Two independent regulator outputs with mixed loads.** Two L7805 instances
   share an external input rail and return, each with its own IN/OUT support.
   Output A drives an RC-filtered external output; output B drives a series LED
   branch and its external output. The regulated outputs are distinct nets.
   No package power or timer is present. This differs from historical
   single-regulator fanout: two repeated producers and their support cells must
   retain separate distribution trees. Verify all four support paths, both
   downstream escapes, and no false signal order from the common input.
2. **Passive fanout with a second branch depth.** An input low-pass RC feeds
   two distinct RC branches; one branch output additionally feeds a resistor/
   LED load. Each filtered output has a real external interface; all shunts
   share the declared return. This has no active amplifier, timer or regulator.
   Verify explicit series/shunt and series/series paths, both fanout levels,
   legal junctions, downstream escape capacity and stage order. Include a
   separately recorded long-field variant (24-character connector value and
   20-character required net label) to exercise real text extents; it is a
   metamorphic stress variant, not a fourth independent topology.
3. **Timer signal split into filtered gain and a direct indicator.** One NE555D
   output drives both a high-pass RC into an inverting NE5532 function and a
   separate resistor/LED branch. The second amplifier function uses the
   qualified explicit unused configuration. Include its one package power
   occurrence, split supplies/decoupling, timer timing/control support, an
   external signal output and explicit source assertions. This is distinct
   from the historical timer→buffer and timer→RC cases: the shared signal tree
   must preserve a high-pass path, inverting input/feedback, timer corridors
   and the direct branch simultaneously. Verify each protected path and all
   consumer associations, including under the supported A/B unit exchange.

For each base probe require at least two local access variants to be locally
validated; synthetic obstruction tests must force selection of a non-default
variant. Do not force an arbitrary orientation in the final circuit if the
default is already legal. The long-field and unit-exchange variants also need
real qualification and five clean runs; they do not increase the independent
probe count. Do not edit probe topology after a failure to remove difficulty.

### Known regressions and real qualification

Require all eight V5 inputs unchanged to pass as **known regressions**,
including V5-1 and the four recorded passes. Specific acceptance evidence:

- V5-3: final observed height ≤140 mm and width ≤210 mm; every field and route
  is covered by the final reservation record. Show initial/final envelope
  deltas and actual candidate selection, not an adjusted threshold.
- V5-6: exact pin-to-pin support paths, legal output escape and zero body/text
  crossings after real export. Preserve a route/support diagnostic overlay.
- V5-7: explicit series-to-both-input paths, correct T junctions and unchanged
  local feedback topology. Both a preserved unsplit positive observation test
  and a newly emitted canonical-tree test are required. Labels alone fail.

Retain all M2f2 qualification inputs: eight v2, seven valid v3 plus its existing
corrected V3-8 equivalent, eight v4, three M2e1 probes and two M2f2 probes
(29 positive cases). Keep historical V3-8 as its existing invalid-input
negative, without editing it. Add the eight V5 positives and the three new
base probes: **40 positive base cases**, plus the two stated new-probe stress
variants and all generic/mutation tests. Retain other established M2d1/M2e1a
regression tests and their expected outcomes.

Every positive qualification case, including the two stress variants, requires
five clean builds in independent new directories with the locked KiCad 10.0.6
toolchain/assets/policy. Require fresh XML export, exact independent terminal
partitions and identities, zero ERC violations, all unchanged numerical gates,
new reservation/path invariants and real SVG renders. Missing evidence is not
a pass. Do not infer electrical success for V5-6 from its old validation stage.

Compare compiler-owned project bytes, observed partitions, ERC, canonical
geometry, full metric vectors, normalized SVG geometry/text, composition and
attempt traces, and manifest/check evidence across all five builds. Retain the
documented exclusions only: nonrendered SVG title, XML/ERC source/date and raw
CLI staging paths. Runtime telemetry may be reported separately from canonical
decision evidence; do not normalize away geometry, variant choices, route
decisions, thresholds or failure differences. No new golden bytes are written
over historical artifacts. Document any historical-byte test migration with
its independent replacement assertions.

Run complete pytest, Ruff lint/format and applicable whitespace/link checks.
Report per-case rejection reasons, worst final metrics, envelope prediction
errors, route/variant/repair counts and runtime. Compare with the existing
baseline without requiring identical geometry. Engineering inspection must
check support association, feedback/timing clarity, fanout tracing and readable
fields on the new renders. Record actual review or mark it pending; do not
fabricate human approval or claim full M2 PASS from automated repair results.

### Failure artifacts and exit criteria

Preserve a staged `layout_attempts.json` (or equivalent versioned report) even
when no schematic can be emitted. Include input/source/tool/policy hashes;
semantic/route obligation IDs; owner/variant maps; content and reservation
envelopes; transformed gateways; segment/junction provenance; full and failed
metric values with thresholds; blocked geometry pairs; protected-path witnesses;
ordered candidate/repair decisions; exact budget counters; final failure class.
Preserve diagnostic drawings where possible, clearly marked failed/nonrelease.
Report `not_evaluated` explicitly for phases that lack artifacts. Do not infer
that a computation never ran solely because its result was not published.

M2g2 is ready for subsequent blind evaluation only when every required positive
and negative test, known regression, new probe, five-run comparison and
anti-overfitting audit passes, with engineering inspection status explicit.
If any remains failing, preserve it and report M2g2 incomplete. A later fresh
blind corpus is a separate milestone after the repair gate; do not author,
sample, reserve or create corpus.v6 during this repair. Do not begin M3.

## 13. Anti-overfitting and review completion

Production geometry decisions must not depend on V5 IDs, circuit/design names,
paths, exact topology hashes, exact whole-circuit inventories, reference
designators, net spelling or pairwise whole-circuit templates. Diagnostic and
regression manifests may identify cases. Stable semantic IDs may break genuine
ties, but may not select geometry rules. Text width may affect occupied space;
its content cannot dispatch layout behavior.

Part-specific physical pin/unit semantics, legal transforms and measured
symbol geometry are allowed. Bounded reusable local motifs, support cells,
typed relative constraints and gateway/aspect variants are allowed. A local
rule cannot inspect unrelated circuit inventory to select its coordinates.

Audit literals and structural behavior: search active code for known IDs,
names, inventory/topology dispatch and refdes-dependent rules; inspect new
conditionals for disguised family pairs or global counts. Demonstrate
local-context invariance, repeated producers/consumers, branch-degree changes,
identifier permutations, supported unit exchanges and alternate field lengths.
Record pre/post hashes for historical evidence and the complete diff scope.
Passing known V5 inputs is regression repair, not evidence of new blind
generalization.

This review ends at this specification. It authorizes no implementation in
the review turn and records no new qualified layout. The next Sol session has
the scope, data contracts, operation budgets, tests and completion gate above.
