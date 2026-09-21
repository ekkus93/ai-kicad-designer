# M2 composition remediation specification

Status: implementation handoff following M2d2; no remediation implemented by this review.

## 1. Decision and scope

The governing architecture is fundamentally sufficient for the qualified M2
circuits. The implementation has not realized its separation of electrical,
semantic, and presentation graphs, overlapping constraints, local motif
geometry, and global envelope placement. Two blind failures falsify the
implemented composition mechanism; they do not demonstrate that those
architectural principles are insufficient.

Retain one geometry owner per symbol occurrence, overlapping semantic
relationships, local fragments, and semantic ports. Replace the *implemented*
fragment and stage-graph representations: the former is a post-placement
ownership record rather than a composable object; the latter conflates signal
and supply edges. Replace primary-core selection with enumeration of local
functional instances and one common composition pipeline.

No governing document changes are required. In particular,
[SCHEMATIC_LAYOUT_SPEC](SCHEMATIC_LAYOUT_SPEC.md) sections 2–7 and 11 already
require the distinctions below; [CIRCUIT_IR_SPEC](CIRCUIT_IR_SPEC.md) sections
4, 5, and 9 already distinguish blocks, ports, functions, packages, terminals,
and graphical occurrences. This document supplies the missing executable
design and a bounded repair milestone. It does not change acceptance thresholds,
expand the supported electrical asset envelope, or claim M2 qualification.

The next milestone is **M2e1 — instance-based schematic composition repair**.
Its results will be development and known regression evidence. A later fresh
corpus.v4, outside that milestone, must test generalization. Full M2 still
requires the real human review specified in the implementation/evaluation plans.

## 2. Evidence and root causes

### 2.1 Evidence boundary

Reviewed the schematic/IR specs, architecture review, M2 implementation exit
criteria, the three historical summaries, V3 automated results and five failed
reports, `m2_compose.py`, the relevant layout/measurement portions of `m2b.py`,
and `test_m2d1.py`, `test_m2c1.py`, and `test_m2b.py`. Also inspected the exact
M2d1 development probe, V3-7 input, and relevant historical layout predicates
at the v2 frozen commit. No new design or build was run for this review.

Evidence locations:

- [v2 blind summary](../fixtures/m2blind/SUMMARY.md): 2/8 at
  `07efd669000bc1ab17f6d291660951e0d9012de9`.
- [M2d1 repair summary](../fixtures/m2d1/SUMMARY.md): all eight *known* v2 cases
  passed, plus a development probe.
- [v3 blind summary](../fixtures/m2blind_v3/SUMMARY.md) and
  [automated results](../fixtures/m2blind_v3/automated_results.json): 3/8 at
  `f8ea5b055aad1a9e97a659e025c20e185a626533`, with an unchanged freeze.

V3-1, V3-5, and V3-6 passed real KiCad 10.0.6 electrical comparison, ERC,
layout gates, and five-run reproducibility. All eight V3 inputs passed the
standalone parser/resolver. All five rejected V3 cases stopped before export.
Their reports say `invalid` after `validate_resolve: ok`; the code shows
layout restrictions rather than the claimed electrical contradictions.
Parser success alone is not proof of every semantic predicate, but the
reported failures do not establish invalid circuits.

### 2.2 First blind failure: whole-design family functions

Before M2d1, family layout functions consumed the complete design and required
their own inventory to exhaust it. H1 rejected multiple passive structures;
H4 required the other amplifier function to be unused; H5/H8 left passives
outside the active function's recognized neighborhood; H6/H7 rejected the LED
load as unplaced. H2 and H3 fitted neighborhoods the active layout already
knew how to draw.

Thus the principal v2 defect was not inability to draw an RC or LED. It was
that recognition, occurrence allocation, local construction, interfaces, and
sheet completion were coupled in a family function. There was no reusable
boundary at which another qualified local structure could join.

M2d1 relaxed completion using `partial=True`, attached residual passive
structures, and allowed the second amplifier to be an active *buffer*. Those
were useful repairs, but retained the original family functions as sheet
cores. Post-hoc owner checks proved coverage without establishing independent
fragment planning.

### 2.3 Second blind failure: exact code paths

The following references identify functions and predicates at the frozen M2d1
source; line numbers are navigation aids for that revision.

| Case and preserved report | Immediate cause | Architectural implication |
|---|---|---|
| [V3-2](../fixtures/m2blind_v3/runs/V3-2/run1.failed/reports/failure.json) | `power_stage_layout`, `m2b.py:581–610`, requires exactly one `Conn_01x01` on each regulator rail. The output interface is downstream of the RC. | A semantic output port is incorrectly inferred from external connector presence. |
| [V3-3](../fixtures/m2blind_v3/runs/V3-3/run1.failed/reports/failure.json) | `timing_layout`, `m2b.py:693–719`, similarly requires a connector on the timer output, before the filter. | Timer-local construction owns external interfaces and cannot expose an internal output boundary. |
| [V3-4](../fixtures/m2blind_v3/runs/V3-4/run1.failed/reports/failure.json) | `active_layout`, `m2b.py:1143–1180,1356–1385`, calls the other function `parked` and requires output and minus pins on the same net, even when `unused` is false. | The second function's resistor feedback/input network is never independently recognized. Physical identity support exists, but functional layout remains asymmetric. |
| [V3-7](../fixtures/m2blind_v3/runs/V3-7/run1.failed/reports/failure.json) | `active_layout` uses a fixed sheet origin; `_serial_shunt(..., prepend=True)` adds another stage to the left; `measure`, `m2b.py:932–936`, rejects the resulting coordinates. | No complete envelope is computed and translated/packed before page validation. This is failure of one construction, not proof that the circuit cannot fit A4. |
| [V3-8](../fixtures/m2blind_v3/runs/V3-8/run1.failed/reports/failure.json) | `compose_layout` rejects more than one recognized core kind from timer, power stage, amplifier. | Compatible functional instances cannot coexist. Removing this guard alone would expose further global support-count, connector, and supply-assertion assumptions. |

V3-7 has a particularly direct static explanation: the upstream resistor of
the Sallen-Key core is at `ax - 56*PITCH`, with `ax = 100*PITCH`. The prepend
operation puts another series symbol 27 pitches left of that resistor's
input pin, then puts an input stub further left. That can cross the 16-pitch
left margin without proving excessive *width*. Neither a global translation
nor alternative packing is attempted. The preserved report contains no full
failed-scene envelope, so this review does not certify an alternative fit.

### 2.4 Separate fault categories

| Category | Finding | Evidence strength |
|---|---|---|
| IR/semantic model | Full 0.1 IR is adequate. Executable `m2b.1` has no authored blocks/ports and only a narrow relationship vocabulary; derive a typed plan from its existing fields. Power assertions lack rich provenance, and arbitrary passive direction remains ambiguous. | No new IR field is needed to express these requested topologies; broader engineering semantics remain outside this profile. |
| Motif recognition | Global relation inventories (`2` amplifiers/feedbacks/decouplers; `1` regulator plus `2` supports; `1` timer/ladder/control) substitute for per-instance matching. Active layout finds neighboring series/shunt/bridge relations using first matches. | Direct code evidence; mixed-unit failure and mixed-core rejection expose this. |
| Geometry ownership | `Draft.add` catches duplicate placement and the composer catches missing occurrences. But fragments are constructed from already-mutated position sets; ownership is an execution outcome. Shared net membership is used as attachment eligibility. | Checks are useful but do not provide an ownership plan or constraint reconciliation. |
| Interface/port model | `LayoutFragment.ports` maps names to net strings, without terminal witnesses, endpoint geometry, or role. `_anchor` scans for a long horizontal segment or a label. Family functions own connectors. | Direct V3-2/V3-3 failures; latent attachment fragility. |
| Package/unit model | NE5532 pins and three units are represented, but active layout assumes one primary function and one direct-feedback secondary function in one package. | Direct V3-4 failure. This is not evidence of physical pin mapping failure. |
| Stage graph | Nodes are selected relationships, not local functional instances. Timer supply becomes its `input`; regulator edges join the same untyped graph as signal edges. All cycles are rejected; feedback is not consistently abstracted out of internal structure. | Direct code evidence; V3-8 stops before the consequences are measured. |
| Placement/packing | Absolute family anchors, fixed offsets, asymmetric prepend/append rules, no measured fragment envelope or global compaction. | Direct V3-7 failure; no demonstrated global infeasibility. |
| Routing | Manual local routes plus geometric trunk/label selection for branches; no contract for which part of a protected net may be attached to. | Architectural risk, not a separately observed KiCad routing failure in these five cases. |
| Implementation-only assumptions | Exactly one mixed connector, exact whole-sheet support counts, required external flags at every local core, one core kind, direct feedback on the other unit. | These restrictions contradict the governing architecture; none is a necessary electrical condition. |
| Evaluation/diagnostics | Layout restrictions surface as `invalid`; failed candidates omit geometry/constraint witnesses. Golden-byte tests favor retaining familiar whole-sheet geometry. | Makes failure analysis and structural repair harder; does not negate the genuine blind failures. |

### 2.5 Why the regression suite did not establish generalization

`test_m2d1.py` checks known v2 occurrence coverage, a two-buffer package,
renaming/permutation, unmatched relationships, a graph cycle, and the regulator
probe. These are valuable invariants, but they do not test multiple local core
instances, different function semantics in one package, or connector-free
internal ports.

The [regulator probe](../fixtures/m2d1/regulated_rc_probe.json) retains `load.1`
on `VOUT`; the RC endpoint `POST` contains only its resistor and capacitor.
Consequently the regulator still finds its output connector. This probe did
not exercise regulator → RC → external output, despite exercising an added RC.

The existing M2b/M2c1 mutation tests strongly support the observation boundary.
Their golden comparisons also bind legal output to historical coordinates.
Preserving those coordinates is not a substitute for the new fragment
invariants, and changing coordinates must not mean overwriting the historical
qualification files.

## 3. Semantic planning before geometry

### 3.1 One electrical graph; one typed semantic graph; several projections

Keep terminal-to-net membership immutable. Construct a semantic plan with
functional-instance nodes, package-resource nodes, interface nodes, and
net-indexed typed incidences. Derive projections for ordering, support
placement, power distribution, and routing. Do not maintain several separately
inferred graphs that can disagree about identities.

| Relation in the derived plan | Endpoints / evidence | Ordering and geometry effect |
|---|---|---|
| Signal progression | Output and input ports, evidenced by amplifier functions or declared passive progression | Left-to-right order between local functional blocks; internal motif progression stays local. |
| Supply dependency | Source power-output port to consumer supply port, using actual pin roles and nets | Power-region proximity/preferred source placement; never a signal-stage x inequality. |
| Reference/return sharing | All ports on the same exact reference net | Distribution and association; no direction, no net merging. |
| Support association | Capacitor terminals plus declared consumer terminal | Local support ownership/maximum span; not a signal stage. |
| Feedback / reactive bridge | Exact source, sense and component transitions | Protected local path/corridor; excluded from signal ordering. |
| Branch/load attachment | Source-net port to branch input and explicit return | Fanout and route-tree attachment; a sink branch need not rank the main path behind it. |
| Package resource use | Function instance to its package supply occurrence | Single shared occurrence and support affinity; no signal order. |

Type *port incidences*, not entire nets exclusively. An output net can feed a
signal input and an indicator branch. A regulator rail can feed timer power,
an RC supply filter, and an indicator without turning these into one serial
signal chain. A reference-generator output and an amplifier reference port
share reference semantics even if the generator is physically above or below.

For regulator → timer → LED, the plan contains a supply dependency from
regulator power output to timer supply, then a load attachment from timer
signal output to the LED branch. Timer supply is never its signal input.
For regulator → RC → load, the RC has intrinsic input/output progression;
its connection to the regulator is a supply-path dependency. Its internal
resistor direction remains explicit even though the regulator is not a
signal-stage predecessor.

Collapse internal protected structures before deriving inter-block signal
order. Compute SCCs on the remaining signal projection. Feedback already
classified by evidence must not create an ordering cycle. A residual SCC is
a coupled placement group with its internal obligations retained. In M2e1,
support local feedback SCCs handled by existing motifs; reject an unrecognized
cross-functional loop as `unsupported` with its relationship IDs. Contradictory
hard x-order constraints are `SEMANTIC_CONFLICT`, not silently broken by a sort.

### 3.2 Derivation from the executable profile

Keep `m2b.1` inputs accepted unchanged. Use existing component asset/unit/pin
maps, `amplifier`, `feedback`, `series`, `shunt`, `polarity`, `bridge`,
`power_stage`, `timer`, `timing_ladder`, `decoupling`, `power_rails`,
`reference_divider`, and `signal_flow` assertions. No new relationship kind,
fake component, pin remap, or authored coordinate is needed.

Build indices by terminal, function, consumer, and net. Recognize each active
function independently, then its feedback and input/reference elements.
Recognize each regulator and its own support consumers; each timer and its
matching ladder/control network; each reference divider; each residual
series/shunt or resistor/LED neighborhood. Never count support relationships
across the whole design. Require local pin/net predicates before accepting a
match. Ambiguous matches with incompatible obligations must be reported with
their witnesses, not resolved by the first relationship in the array.

The narrow profile's function `role` is not sufficient topology evidence:
existing amplifier inputs can retain the historical string `buffer` even
when their resistor feedback defines gain. Use verified pin incidence and
relationships to distinguish buffer, inverting, non-inverting, and Sallen-Key
forms. An explicit `unused` assertion determines unused-function intent;
absence from a selected chain never does.

Full IR already offers `BlockPort`, domains, and interface contact roles.
Their richer future authoring is not a prerequisite here. In this profile,
derive a total *presentation* ownership map, record the inference/provenance,
and leave input bytes untouched. Do not claim this implements the complete
0.1 block schema. Infer external-interface contact roles only where connected
relationships/pin semantics justify them; otherwise use a neutral interface
presentation. Do not infer direction from a connector's library name or net
spelling.

Use the following local boundaries; do not preserve the old active-layout
function's habit of absorbing every nearby passive stage:

| Local construction | Recognition and boundary |
|---|---|
| Buffer | A function with a verified direct negative-feedback path; input at its plus terminal, output at its output tree, reference supplied separately. |
| Non-inverting gain | Resistor feedback from output to minus plus a verified gain-setting shunt from minus to reference; include those resistors locally. The input boundary is the plus terminal. |
| Inverting gain | Resistor feedback from output to minus plus an input series resistor into minus; plus is on the declared reference. Include both resistors; the signal input boundary is the input resistor's outer terminal, not the plus terminal. |
| Sallen-Key | A verified two-series/one-shunt network into plus and a reactive bridge from the intermediate node to output, with the amplifier feedback. Keep this protected network together; expose the first series element's outer input, output tree, and reference. An RC before or after that boundary stays separate. |
| RC / LED / series | Match series/shunt or series/polarity incidence at the shared intermediate node. Other same-net branches do not invalidate the match. A residual ordinary series element can expose two ports without requiring a shunt; its upstream/downstream peers supply composition context. |
| Regulator | One regulator occurrence and supports matched to its exact IN/OUT consumers; expose terminal-backed power input/output/reference trees. |
| Timer | One timer occurrence, its verified timing ladder, reset supply connection and control bypass; expose supply/output/reference while keeping discharge/timing/control local. |
| Reference / package power | Divider midpoint and rail endpoints, or one dedicated supply occurrence with its own consumer-associated decouplers; expose exact rail/reference identities. |

In a compound local structure, the executable `amplifier.input` may name a
net *inside* the fragment (as in existing Sallen-Key IRs). Preserve that assertion
and its witness, but derive the fragment's external signal boundary by following
the verified local series path to its first element. Do not rewrite the input
IR to equate these two different levels of port. Likewise an inverting
function's reference input must never be mistaken for its signal entry.

Predicate overlap is expected: the Sallen-Key includes buffer and RC relations.
Collect them all, then use the protected bridge/path closure to establish the
local construction. A plain RC attached to a non-inverting input has no such
bridge requirement and stays its own fragment. This distinction depends on
local electrical incidence, not the identity of the external neighbor.

## 4. Ownership, overlap, and the fragment contract

### 4.1 Identities and ownership planning

Use these separate keys:

- Physical terminal: `(component_id, physical_pin_number)`.
- Functional instance: `(component_id, function_id)` for multi-unit devices;
  `(component_id, recognized_function_kind)` for the qualified single-unit devices.
- Graphical occurrence: `(component_id, unit, body_style, occurrence_id)`;
  the narrow adapter may derive the last two fields when uniquely fixed.
- Presentation owner: a derived fragment ID, independent of refdes or page position.

Every resolved occurrence has exactly one owner before geometry is constructed.
Relations may reference occurrences owned elsewhere and never thereby acquire
their geometry. Nets have no symbol owner. A producer does not own every
consumer touching its output net. Policy power flags have separately typed
artifact identities and owners; they are not extra physical packages.

Ownership selection procedure:

1. Collect all local rule matches and their required anchor/constraint claims
   without placing anything. Identify package power and connector occurrences
   as separate resources, not implicit parts of every active match.
2. Allocate functional occurrences to their functional instance, dedicated
   power occurrences to their package resource, and each whole connector to
   one interface fragment. Associate supports by actual consumer terminal.
3. Allocate passive occurrences using the most specific verified local
   structure. A Sallen-Key bridge and its RC network form one protected local
   construction; their series/shunt/feedback relations all remain present.
   Residual RCs and LED loads form their own fragments.
4. If two construction claims share an occurrence or require an inseparable
   local path across tentative owners, merge their constraint groups and
   unify that occurrence's anchor. Merge only on shared occurrence/protected
   path obligations, never simply because they share a rail or output net.
   The merged group is solved from constraints, not a new combination handler.
5. Check anchor equalities, permitted poses, hard orders, protected corridors,
   support spans, and terminal maps together. Compatible overlap is accepted.
   Disjoint allowed poses or contradictory bounds produce a conflict witness.
   If a compatible merged group lacks a supported constructive variant,
   return `unsupported`; do not discard a relationship or duplicate a symbol.

Constraints carry `{id, origins, strength, kind, anchors, parameters}`.
Resolve equalities first, then intersect allowed poses and propagate order/gap
bounds. Detect negative/directed cycles in difference constraints before
placement. On conflict, report a deterministic irreducible subset of involved
hard constraints by bounded deletion testing; do not claim a minimum-cardinality
proof. Preferences may rank feasible variants but never remove hard constraints.

One occurrence can thus be in signal progression, feedback, support, a power
domain, and a package relation simultaneously. These are distinct constraints
over one owned anchor. Logical package ownership and geometric placement
ownership need not coincide.

### 4.2 Minimum fragment representation

Separate `BlockPlan` (semantic identities/constraints) from `FragmentVariant`
(one feasible local geometric realization). Use immutable records and local
integer-nanometer coordinates. A fragment variant contains:

| Field | Required content |
|---|---|
| Identity/provenance | Fragment and variant IDs; rule/version IDs; function, component, and relationship origins. |
| Owned occurrences | Exact owner set, symbol transforms, required field positions/envelopes, and physical pin mapping references. |
| Anchors | Named local points tied to an occurrence pin or a certified point on a local net tree. |
| Ports | Stable port ID, exact net ID, incidence role, terminal witnesses, and one or more legal access anchors with escape direction. |
| Local geometry | Explicit protected wire trees by net, permitted tap anchors/segments, junctions, and justified local labels. |
| Obstacles and envelope | Body, text, pin/escape, local wire/corridor occupied regions; their conservative union bounding box. |
| Constraints/requests | Hard attachment/path/span obligations and soft adjacency/resource-use requests, with origin IDs. |

A port is not only a net string. Its access anchor must be proven to belong to
the local net tree for its terminal witnesses. A port may have multiple access
choices, but a global route cannot attach to an arbitrary convenient segment
inside a protected loop. Boundary stubs count in the envelope.

Keep rail requirements as typed ports; shared-resource requirements as typed
semantic edges; flow preferences as constraints. Do not create independent
mutable copies of this information in three fields. Expansion directions
belong to the finite local variant generator: permitted corridor sides and
clearance increments, not an open-ended resize API. Routing corridors are
obstacles/reservations of a variant. The global composer chooses the variant,
origin, shared tracks, and inter-block routes; it never edits its protected
local geometry in place.

Local generators receive their `BlockPlan`, referenced asset geometry, and
applicable drafting policy. They cannot query unrelated components, count all
sheet supports, choose sheet coordinates, place another block's connector,
or finalize global metrics. Use a shared obstacle/anchor helper for local
relative construction; avoid rebuilding the old whole-design functions under
new names.

## 5. Interfaces, packages, and supply resources

### 5.1 Interfaces without invented connectors

An external connector is a real component and an interface fragment. Its
contacts expose their existing nets. Preserve multi-contact connectors as one
symbol occurrence and keep pin-number lookup readable.

A functional block port exists because its verified function has that
terminal/net boundary. Regulator IN/OUT/reference and timer
supply/output/reference ports exist with zero external connectors on those
nets. An internal connection is a route obligation between such ports.
One external connector may serve several blocks; no block may seize it as
proof of its own boundary. Connector addition/removal must not alter the
functional fragment's protected internal construction.

Distribution is a net-level presentation decision over several typed ports.
For a small regulator/timer subsystem, route the regulated supply explicitly
to the timer supply tree. Scope-correct labels may serve remote shared rails
under the existing policy, but cannot replace a protected local path or
silently hide the subsystem's supply dependency. Local reference remains its
own electrical net even if it happens to have zero nominal voltage.

Source assertions are processed once by the global resource planner. Preserve
explicit `m2b.1` flags and their exact nets without treating them as evidence
of connector presence. A driven regulator output can supply a timer without
requiring another external-supply assertion. Existing explicit redundant
flags are not authorization to merge sources or nets; ERC and engineering
claims remain separate. Do not add/remove assertions in the known IRs to get
them through the new engine.

### 5.2 Multi-unit packages

The package registry inventories all resolved units once. It relates each
functional instance to one physical package and its dedicated supply unit.
Any number of functional units up to the actual package inventory may be
active, including none; all required units remain accounted for.

For NE5532, recognize unit 1 and unit 2 independently using their real pin-role
maps. Each may be a buffer, gain stage, or qualified active filter, with its
own input/reference/output ports and feedback network. Reuse the same local
function constructor with the appropriate pin map. Unit 3 is one separate
package power fragment, with its associated decoupling. Multiple functional
fragments request proximity to that resource; none duplicates it.

An explicitly unused unit still needs its authored bias/feedback configuration
validated and drawn. M2e1 keeps the qualified parked-buffer form and explicit
rejection of unqualified NC/hidden-pin configurations. It must also support a
package whose two functions are both explicitly unused and correctly biased;
the signal-order projection may then be empty. A component is not considered
unused merely because another component was selected first.

Independent packages use the same path. No exactly-one-package predicate,
literal `U1A`/`U1B` dispatch, or assumption that numeric unit order is signal
order is permitted. The final observer must still establish all required
physical pins and units from actual emitted artifacts.

## 6. Global placement, sizing, and page policy

### 6.1 Deterministic constructive mechanism

Implement measured-envelope placement before introducing an optimizer:

1. Generate at most eight local variants per block, in a fixed rule-defined
   order. Each includes text slots, protected routes, and port escape space.
   Variants may choose a legal feedback corridor side or connector orientation;
   do not mirror whole drawings without recomputing text/pin semantics.
2. Normalize local envelope origins. Build the signal-order projection of
   functional blocks. Place ordered components using envelope-edge and
   port-access separation, not symbol-center increments. For a directed
   predecessor/successor require enough x separation for both envelopes and
   route clearance; align compatible signal ports in y where feasible.
3. Place independent signal chains on separate shelves. Preserve left-to-right
   order within each chain in M2e1; do not wrap a chain back to the left and
   weaken the current stage-order checks. Use fanout sinks in adjacent rows,
   with deterministic ordering by semantic IDs only as a final tie-break.
4. Place power/reference generators and package supply fragments in adjacent
   support bands using consumer affinity and real envelopes. Put branch loads
   beside/below their source's accessible output corridor. Their whole envelope
   contributes to packing; branch attachment is not a late free-space guess.
5. Place external interface fragments at the perimeter or a mixed-interface
   lookup region according to contact roles. Reserve routing lanes between
   those fragments and functional blocks before accepting a packing.
6. Compact slack: solve the fixed-order separation inequalities toward their
   minimum legal gaps in x and y. Preserve all body/text/wire and protected
   corridor clearances. Move an entire fragment; never compress its local
   motif beyond a separately validated local variant.
7. Translate the complete arrangement into the allowed page rectangle using
   its measured minimum coordinates. Translation is mandatory before rejecting
   an otherwise sufficiently small drawing for a negative/leftward extension.
8. Route inter-block obligations. On a witnessed conflict, try a reserved lane,
   deterministic local shift or alternative variant, then channel expansion
   and repacking within the budgets below. Recheck the full geometry after
   each attempt. Select only among candidates passing every hard gate.

Use a beam of at most eight partial placements. Extend blocks in stable
topological order; evaluate their at-most-eight variants and four generic
placement choices: aligned signal row, next independent shelf, upper support
band, lower support band. Admit only choices compatible with typed constraints.
Rank/prune by hard infeasibility, envelope overflow lower bounds, required
reader jumps, congestion demand, dimensions, then canonical identity.
Final feasible candidates use the existing semantic/legality-first ranking.
Bound route-repair rounds to three per complete placement. Record candidate
counts, chosen variant/origin, discarded constraint witnesses, and budget use.
These are operation-count bounds, not machine-speed-dependent stopping rules.

Do not promise that every set of legal local fragments fits: routing clearance,
an authored order, or a genuinely oversized envelope can make the complete
request infeasible. The common mechanism must accept arbitrary compatible
local contributors without family-pair dispatch, and explain bounded failure.

### 6.2 Page-fit and failure policy for M2e1

M2e1 qualifies single-sheet A4 landscape using the existing margins, text
sizes, and hard-gate limits. Compute the usable rectangle from the policy;
for the present policy it is 256.36 by 159.2 mm. Envelope checks include full
required text and symbol extents, not just their origins. The emitter and
independent checker must agree with the selected page.

Page containment is not the only size gate. The current observed evaluator
also rejects content extents above 210 mm wide or 140 mm high, net wire length
above 250 mm, local path/fragmentation spans above 80 mm, support spans above
60 mm, and observed feedback span above 45 mm; the active constructor also
has its 40 mm local feedback-corridor limit. Preserve these distinct metric
definitions and thresholds in the repair. Pack toward the stricter applicable
limits and validate full extents as well as the existing measured vector.
An A4 fit alone cannot override the anti-spreading or detour checks. Report
which constraint failed rather than calling every limit a page-margin error.

Try compaction, alternative local variants, independent shelves/support bands,
and translation before failing. Do not make text or symbols smaller, move
support beyond its permitted span, or waive crossings to fit.

The governing future sequence A4 → A3 → hierarchy remains valid when policy
and backend support permit it. Do not implement A3 or sheet partitioning in
this milestone. If the A4 budget is exhausted, report that larger pages or
hierarchy could be future capabilities, not that they were attempted. A future
explicit page-policy change requires qualification of emission, margins,
utilization metrics, and render settings together; changing only a constant
in placement is insufficient.

Use `infeasible` only with a proof within the stated model, such as every
permitted variant of an indivisible block exceeding the usable page, or a
mandatory chain width lower bound exceeding it. Report the assumptions and
bound. If the finite search finds no layout without such a proof, return
`budget_exhausted`. Unsupported motif/loop capabilities are `unsupported`;
contradictory electrical or hard semantic assertions are `invalid` with a
specific conflict code. Preserve candidate envelope, obstacle, port, route,
and constraint reports, and a clearly failed diagnostic drawing if available.
Do not recategorize the preserved V3 reports retroactively.

## 7. Routing contract

Local constructors route feedback, timing, filter bridges, and directly
associated support inside their fragments. The global router treats these
wires/corridors as protected obstacles except at certified ports/tap windows.
Source and return branches inside a local support group remain explicit.

After placement, transform each access anchor and its escape direction by the
fragment transform. Recheck its net/terminal witness against the transformed
local tree. These concrete coordinates, not labels found by scanning the
sheet, are inter-block endpoints.

Build one route obligation per electrical net over all its required fragment
ports. Keep local trees as preconnected portions. Route constrained ports
first, then other signal/branch connections, then shared rails; preserve local
reservations regardless of net degree. Within each net, attach remaining
ports to the existing tree using shortest admissible candidate length, bends,
and stable port ID as tie-breaks.

For M2e1 use finite channel routing:

1. Exact escape stubs to reserved lanes outside occupied envelopes.
2. Try straight and one-bend paths, then two-bend paths using endpoint tracks
   and nearest reserved horizontal/vertical lanes.
3. If needed, search the sparse rectilinear graph formed by port escapes,
   inflated obstacle boundaries, and reserved lanes, with integer length/bend
   costs and deterministic node ordering. Search corridor intersections, not
   every point on a sheet-sized grid. Exhaustion returns a blocked-port/obstacle
   witness to the placement repair loop.
4. Attach branches at an existing certified same-net tap or an admissible
   segment of the inter-block tree. Split the segment explicitly and generate
   junctions from actual degree. Do not choose the longest visible wire, steal
   another block's output ownership, or pierce a feedback corridor.

This is the restricted visibility/channel implementation of the existing
routing spec, not a PCB/general maze router. Use the current qualified zero
unrelated-crossing gate; no new crossing allowance is introduced. Reject
collinear overlaps of different nets, off-pin joins, and unrelated pin/body/
text contacts. Wire subdivision must preserve connectivity and normalize for
metrics. Local labels require a predeclared scope/style reason and budget;
they are not a congestion fallback for a protected path.

Rebuild scene connectivity before emission, then require fresh KiCad export,
independent observation/comparison, ERC, and observed layout checks. The
observer must not accept the planner's statement that a port is connected as
evidence of a real wire.

## 8. CP-SAT decision

Do not introduce CP-SAT in M2e1. V3-2/3/4/8 are representational or explicit
support restrictions; a solver cannot create the missing semantic boundaries.
V3-7 proves that one anchored construction overflows, not that bounded
envelope placement fails. A solver over the existing whole-sheet cores would
preserve their false connector/package assumptions.

Implement the constructive sequence in section 6 first. A later solver
experiment is justified only after saved constraints demonstrate repeated
packing failures despite correct local fragments and legal ports. Limit such
an experiment to choosing finite variants and integer block origins with
non-overlap, order, support-span, and corridor constraints. No electrical
membership, motif recognition, or wire semantics become solver variables.
Compare against the constructive baseline on development cases, with identical
hard gates. If promoted later, lock the solver version, seed 0, one worker,
stable insertion order, at most 20 deterministic-time units per conflicted
block and 100 per sheet, as already specified. A wall watchdog aborts without
publishing an alternate time-dependent winner. Five clean builds must agree.

## 9. M2e1 implementation plan for Sol

### 9.1 Responsibilities and sequencing

Use ordinary typed records/functions. The module names below are recommended
boundaries, not a demand for a workflow framework.

| Module | Work |
|---|---|
| `m2_semantics.py` (new) | Indices, independent instance recognition, package registry, typed port incidences, ownership/constraint plan, semantic conflict reports. No coordinates. |
| `m2_fragments.py` (new) | Local constructors for passive structures, amplifier functions, regulator, timer, reference divider, package power, and external interfaces. Common anchor/obstacle helpers and finite variants. |
| `m2_compose.py` | Replace primary-core selection and residual append/prepend with the semantic-plan → fragment-variants → placement → routing orchestration. No family-pair dispatch. |
| `m2_pack.py` (new) | Measured envelopes, signal DAG placement, support bands, beam/compaction/translation, bounded repair and page diagnostics. |
| `m2_route.py` (new) | Concrete port transforms, channel graph, net trees, shared rails and branch splitting. No motif recognition. |
| `m2b.py` | Keep profile validation/asset semantics and independent comparison/measurement responsibilities. Extract local geometry from whole-design functions; compatibility entry points may delegate to the common composer without selecting old family sheets. |
| `m2b_build.py` | Integrate the common path, preserve staged failure artifacts, record derived plans/geometry/budgets, and retain fresh KiCad and independent gates. |

First implement semantic-plan invariants with synthetic small graphs. Next
extract local builders and prove connector/package isolation. Then implement
packing/routing with synthetic geometry. Only then run complete known circuit
builds. This order prevents a sequence of five V3-specific patches.

Do not broaden electrical validation beyond existing qualified assets to make
a composition pass. Move latent function/feedback predicates out of placement
into semantic validation, preserving distinctions between invalid incidence
and unsupported local capability. Add multiple-core support by enumeration,
not by raising inventory constants.

No changes to historical qualification directories. Put new evidence in a new
M2e1 directory; read historical IRs as immutable regression inputs. Record
source/tool/assets/policy hashes and label v1 tuning and v2/v3 known regression
correctly. Do not invoke historical evaluator scripts that overwrite their
own evidence or deliberately reject changed source freezes.

### 9.2 Minimum generic acceptance tests

Each test must assert semantic identity/geometry facts and failure witnesses,
not just snapshot the new implementation's output.

| Test group | Required assertions |
|---|---|
| Instance enumeration | Two regulators, two timers, and two independent NE5532 packages can each be planned without a whole-sheet inventory predicate. Multiple types coexist through the same composer. |
| Internal interfaces | Local regulator/timer fragments construct with no connectors in their local input. Add, move downstream, and duplicate real external interface contacts while keeping functional ports unchanged; no fake connector is synthesized. |
| Function semantics | Both NE5532 units independently cover buffer/non-inverting/inverting forms; mixed orders and reversed physical-unit assignment work. Test zero, one, and two active units with complete inventory; exactly one power occurrence per package. |
| Typed dependencies | Regulator output → timer supply creates a power edge and no signal x-order edge; timer output → load does create signal/load incidence. Same reference net creates no stage order. Two distinct reference nets never alias. |
| Support isolation | Add an unrelated consumer's decoupler and verify the original block's support match/ownership stays fixed. Support on the wrong consumer/net is rejected with its relationship ID. |
| Overlap/conflict | A resistor shared by feedback and another supported relation has one occurrence and retains both constraints. Compatible anchor claims unify; incompatible pose/order claims return a conflict witness independent of insertion order. Sharing only a net never merges fragments. |
| Fragment locality | Perturb/add downstream or sibling structures; after normalizing each local origin and chosen variant, protected internal geometry is unchanged. Local port witnesses and envelope containment remain valid. |
| Packing | Synthetic variable-size envelopes, long required text, prepend extension, fanout, and support bands use actual extents. A small drawing initially left of the margin is translated to pass. A known feasible alternate variant is found; an oversize indivisible block yields a bound; search exhaustion is not reported as proven infeasibility. |
| Routing | Multi-sink nets form one intended tree; taps split segments and create junctions. Wrong-net, blocked, off-pin, and protected-corridor attachments fail. Supply routing never alters timing/feedback geometry. Independent detach/junction/label-only mutations fail. |
| Determinism | Permute all set-like arrays, change relationship/component IDs consistently, rename refdes, and swap functional-unit allocation with matching real pin maps. Semantics and gates persist; unique structural orders persist. Exact geometry equality is required for set permutations, not for text-width changes or genuinely symmetric tie-breaks. |
| Diagnostics | Every unsupported/invalid/exhausted case preserves origins, blocked ports/constraints, candidate envelopes and attempted budgets. Missing evidence cannot be marked pass. |
| Independent gates | Recompute electrical partitions from emitted KiCad files and XML, and local path/identity/span facts from actual observed geometry. Do not let a fragment's own `pass` flag or owner list certify it. |

Mutation tests must include moving/removing an emitted package power unit,
swapping actual amplifier pin numbers, detaching the second function's
feedback, severing the regulator-to-consumer supply, and replacing a required
local path with labels. Retain the current negative tests for hidden required
text, distant decoupling, stage reversal, and page-scale spreading.

### 9.3 New development compositions

Author and review these before layout work for them. They are intentionally
development probes, not a blind corpus. Use only current qualified assets and
relationship vocabulary and record their topology expectations separately
from generator output.

1. **Non-inverting amplifier into Sallen-Key, using both units of one NE5532.**
   Unit A has resistor gain feedback and feeds the two-resistor/two-capacitor
   unity-gain Sallen-Key built around unit B. One dedicated package power unit
   and its positive/negative decouplers; one external input and one final
   output. Distinct local feedback networks, with the first output feeding
   the filter's first series resistor. This is neither the v2 two-buffer
   chain nor the v3 non-inverting→inverting chain. Also exchange unit assignments
   without changing functional stage order.
2. **Regulator feeding two parallel RC supply-filter outputs.** One qualified
   regulator with its normal input/output support capacitors; two distinct
   series resistors from its regulated output, each with its own shunt capacitor
   and external output connector. Common explicit return, no connector required
   directly on the regulator output. This tests fanout to equal-kind blocks,
   independent downstream port identity, and one shared regulator/support core.
3. **Two astable timers on a shared external supply, with separate outputs.**
   Two qualified NE555D instances, each with its own timing ladder and control
   capacitor, share supply/return but have distinct discharge/timing/control
   and output nets. Each output drives its own resistor/LED branch. This
   directly challenges global support inventory and false ordering through
   common rails. It uses the same local builder twice, not a dual-timer handler.

Require real KiCad electrical/ERC/layout qualification and five clean reruns
for each. These are small single-sheet development targets; if a target fails,
retain the failed evidence and repair the generic mechanism, not its topology
or the acceptance threshold. Values may be chosen for ordinary schematic
demonstration, with no unstated claims about analog performance, loading,
stability, thermal limits, or manufacturing readiness.

### 9.4 Known regressions and golden migration

All eight v2 and eight v3 requests must pass unchanged as known regression
inputs, including the previously passing sheets. Retain the 12 M2c1 tuning
designs and existing qualified M2b/M1/M2 identity/observer tests. Require
complete pytest, Ruff lint/format, and applicable whitespace checks.

Some existing tests compare new output directly to historical project/SVG
bytes. The repair may legitimately change geometry. Replace only those
historical-byte acceptance assertions with explicit electrical, legality,
local-structure, and five-clean-build reproducibility assertions; keep a
separate integrity assertion for the untouched historical evidence. Document
each such test migration and its replacement authority. Never update old
golden artifacts, delete negative tests, weaken metric limits, or retain a
hidden old renderer selected by fixture identity just to keep snapshots green.

Measure all current metric keys on final emitted geometry; do not merge a
primary fragment's stale metric dictionary over globally recomputed values.
Retain current hard gates and add independent checks for every new dependency
and unit case. Generalizing an observer loop from one function to all
functions is necessary coverage, not permission to trust planner metadata.

For the 16 known v2/v3 cases and three new development probes, compare five
clean outputs: compiler-owned project bytes, observed electrical partitions,
ERC, complete metrics, normalized SVG geometry/text, and manifests/evidence
using only the documented path/date/title exclusions. Use independent output
directories and preserve raw reports. Report each rejection and worst metrics;
an aggregate score cannot waive one failed case.

### 9.5 Completion and exclusions

M2e1 completes only when:

- Every expected physical/graphical occurrence and every semantic constraint
  has a validated owner/application or an explicit unsupported diagnostic.
- All qualified local builders accept their bounded local plans; the composer
  contains no single-core selection or pairwise family handlers.
- Typed ports, per-function feedback, package resources, support association,
  envelope packing, and route-tree attachment pass the generic tests above.
- All known v2/v3 cases and the three new probes pass the real automated gates
  and five-run reproducibility; tuning and full regression tests remain green.
- New diagrams receive recorded engineering inspection of functional grouping,
  feedback/timing locality, supply/reference distinctions, branch traceability,
  and readable fields. Inspection is development review, not fabricated blind
  human qualification. If such review is unavailable, report it pending.
- Historical source-freeze/corpus/IR/result artifacts remain unchanged; new
  evidence and all intentional test-oracle migrations are separately recorded.

Do not implement new symbol families, arbitrary analog recognition, general
constraint programming, CP-SAT, board placement/routing, hierarchy, buses,
page-size expansion, application infrastructure, or conversational IR authoring.
Do not create corpus.v4 or claim full M2 PASS in the repair milestone.

## 10. Rules against fixture memorization

Geometry dispatch must never depend on corpus/design IDs, filenames, refdes,
exact component inventories, topology hashes, or named motif pairs. IDs may
identify objects and break genuine ties; they may not select geometry rules.
Text length may affect field envelopes; text content may not choose a motif.

Part adapters may encode actual pin roles, legal units/transforms, shared-pin
semantics, and asset geometry. Family rules may encode bounded local incidence
predicates and reusable relative constraints. A Sallen-Key bridge is such a
local structure; an entire “Sallen-Key followed by RC” sheet is not.

Adding a local motif should add one recognizer/constructor and its own tests,
not alter every existing constructor. Composition uses net-indexed ports and
typed constraints irrespective of the producer/consumer family. The number
of family implementations grows with local families; incidental graph fanout
does not justify a quadratic catalog of combination handlers.

Review the implementation for global relation counts, first-match selection,
connector prerequisites, net-name dispatch, and sheet coordinates inside
local constructors, not merely for literal V3 IDs. Structural memorization
can pass identifier searches. The decisive evidence is local-context
invariance, repeated instances, internal interfaces, semantic substitutions,
and later independent held-out qualification.
