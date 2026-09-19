# Schematic Layout Specification

Status: proposed deterministic layout algorithm, 2026-09-19. Inputs follow [Circuit IR](CIRCUIT_IR_SPEC.md); output is the `SchematicLayout` contract in [architecture](ARCHITECTURE.md). This is a semantic constraint problem with geometry and routing, not generic graph drawing.

## 1. Success and non-negotiable constraints

A reader should recognize what a circuit does, identify interfaces and rails, and trace important paths without mentally reconstructing a netlist. Electrical equivalence is mandatory at every accepted output. No placement, mirroring, pin swapping, labeling, hierarchy change or optimization may change logical connectivity. A draft can fail quality review even when electrically correct.

Use the positive examples as evidence for structural relationships. The Sallen-Key stages demonstrate feedback adjacency and readable progression; Class-D demonstrates paired driver/power structures; SensorProject demonstrates hierarchy and interface grouping. They do not prescribe absolute coordinates, universal symbol orientations or permitted error counts. In particular, the Sallen-Key reference's upward ground symbols are a defensible local choice, not a requirement to copy or a reason to fail the drawing.

## 2. Planning pipeline

The stage sequence is resolve geometry → verify/recognize semantics → form blocks and motifs → choose sheets/interfaces → enumerate motif variants → coarse placement → fine placement/text → routing → independent checks → bounded repair → export and review. Record rule IDs and reasons; persist boundaries needed for diagnosis and replay. M1 need not serialize every transient stage.

Maintain three related graphs:

1. Electrical hypergraph: real terminals grouped into nets; immutable.
2. Semantic graph: components/functions, directed functional paths, power domains and typed relationships. Feedback and bidirectional interfaces are explicitly marked.
3. Presentation graph: symbol units, motif ports, sheet ports, wires, labels and power symbols. A net may appear as several wired islands joined by a valid label scope; each island remains traceable to the one logical net.

Build the directed block graph from declared signal paths and verified pin semantics. Remove supply distribution and explicitly classified feedback arcs from **ordering only**, never from connectivity. Collapse remaining strongly connected components and arrange the resulting DAG. Ambiguous passive or bidirectional connectivity does not justify inventing direction.

## 3. Block decomposition and topology recognition

Honor authored block ownership after reference validation. Refine large blocks using verified motifs and typed interfaces. If ownership is absent in an imported candidate, propose a partition using connected local neighborhoods after downweighting high-degree supply nets; keep it visible as an inferred proposal. The accepted IR still needs a total block ownership map.

Recognition operates on bounded subgraphs around active functions, interfaces and authored relationships. Use typed terminal incidence, component kind/value category, domain and evidence. Do not key rules to `R2`, `U1`, net-name substrings or corpus filenames.

| Structure | Required recognition evidence | Relative drafting constraints |
|---|---|---|
| LED + resistor, divider, RC | Series/shunt incidence and known polarity/reference | Series path straight; shunt/return below when appropriate; divider tap unmistakable |
| Buffer, inverting/non-inverting amplifier | Active function pin semantics and closed feedback path | Input before active device, output after; reserve an outside feedback corridor near the relevant input |
| Sallen-Key and multi-stage analog | Verified passive network and active-device connections | Preserve local loop geometry and stage order; no remote labels within the critical motif |
| Decoupling | Capacitor spans the declared supply/return and is assigned to consumers | Compact supply-support group, clear package association, separate from signal feedback |
| Linear regulator | IN/OUT/reference semantics plus associated capacitors | Input network left, regulator center, output network right; reference and bypass clear |
| Switching regulator | Switch node, inductor/diode/FET and declared current-loop paths | Keep high-current power path legible; feedback/sense path distinct from switching nodes |
| 555 timer | Trigger/threshold timing node, discharge/control/reset semantics | Timing network beside timing pins; CTRL bypass separate; load/gate chain readable |
| BJT/MOSFET switch, relay driver | Gate/base, load/return, protection diode and polarity | Control enters from left; load above switching device where appropriate; flyback association visible |
| MCU, crystal, interfaces | Pin functions, power units, declared clocks/buses/support | MCU as anchor with interface regions; clocks and local support grouped; unused pins explicit |
| Repeated channels | Explicit correspondence or verified isomorphic typed subgraphs | Shared orientation/order/spacing grammar without forcing unequal channels into identical boxes |

A motif match is `{rule_id, rule_version, terminals, members, relationships, predicates, variants}`. Predicates are independently recomputable. Multiple possible matches are ranked by accepted relationship evidence, specificity, matched terminal coverage, then stable ID. Do not select a disjoint component cover: feedback, filters, bias and decoupling legitimately overlap. Give each symbol unit one geometry owner in its block, and let relationship rules contribute constraints over shared anchors/ports. Composition unifies the same anchor IDs without duplicating symbols. Distinguish incompatible hard constraints from merely overlapping recognition. Start with stable priority ordering and explicit authored relationships, not a separate set-packing optimizer.

Conflicting accepted relationships produce `SEMANTIC_CONFLICT`. Uncertain recognition retains alternatives rather than silently fixing a topology. A generic region-and-port layout can produce an explicitly unqualified draft for supported but unrecognized circuitry; it cannot claim the motif-specific acceptance gates. Missing pin semantics required for correctness are an error.

## 4. Geometry, orientation and text

The resolver supplies symbol body shapes, pin endpoints/directions, pin-name/number envelopes, properties and unit/body-style identity. Distinguish the body obstacle from the full occupied envelope. Text is measured using the pinned render font and size; conservative envelopes are permitted only with a documented margin and render verification.

Store geometry as integer nanometers. Nominal placement/routing pitch is 1.27 mm; initial profile `drafting.v1` uses 1.27 mm text, at least one pitch between unrelated routed lines, two pitches between unrelated occupied symbol envelopes, and four pitches between block envelopes including planned routing space. These are starting policies to qualify, not empirical human-quality guarantees. Library pin endpoints must be represented exactly. For off-grid custom assets, use exact endpoint tracks and a declared finer local grid; never round a terminal away from its wire.

Enumerate only library-valid orthogonal transforms. Test endpoint transforms, text readability, pin escape direction and resulting semantic orientation. Prefer inputs left, outputs right, positive rails above and returns below, with motif-specific alternatives. Diode/FET polarity, op-amp +/- identity, connector pin numbers and transformer winding identities never change. A mirror changes geometry, not pin mapping. Normalize equivalent transform matrices to one canonical encoding.

Multi-unit parts are multiple graphical uses of one package. Keep functional units with their stages; place a dedicated power unit with associated decoupling and an unambiguous reference. Unused units still follow documented bias/NC requirements. Never invent separate physical components named `U1A` and `U1B`.

Place reference and value fields from a finite candidate set outside the body/pin keepouts, maintaining consistent reading direction. Long values, net names and sheet titles reserve space before routing. When none fit, expand/reposition; do not shrink text below profile minimum or hide necessary fields to improve a score.

## 5. Placement formulation

Motifs are parameterized constraint grammars, not saved coordinates. A divider expresses resistor ordering, tap location and reference direction; an amplifier expresses an active-device anchor and feedback corridor. Widths, heights and port positions follow the actual symbol/text geometry. Each motif offers a small, fixed-order set of valid variants, such as feedback above versus below.

Start with one deterministic constructive composition and bounded local shifts/variant changes. Retain up to eight alternatives only when needed to resolve a conflict, keeping different aspect ratios/interface arrangements. If those fail systematically, CP-SAT variables may select variant, orientation and integer x/y origins for that conflicted block. Hard constraints enforce occupied-envelope separation, sheet bounds, authored orders, legal transforms and indivisible motifs. Soft tiers control semantic ordering, port alignment, spacing and estimated route demand. Use the solver first for feasibility/local legalization, then rank candidates with the common evaluator. Do not add a separate lexicographic solve per quality tier by default; that duplicates search cost before its benefit is known. If introduced by evidence, report whether each bound is proven or merely feasible. Integer objective scaling and maximum sums are checked for overflow.

Coarse placement packs block envelopes with reserved channels and ordered interfaces. Prefer left-to-right functional flow, repeated rows and conventional power areas. Connector placement follows interface role: power input, signal input, mixed connector or output; a mixed connector is not forced to the left by its reference prefix. Power, feedback and bidirectional bus edges are excluded from simple flow-violation counts.

Fine placement solves each block with actual symbol dimensions and pin access. Use deterministic coordinate descent over legal motif variants, alignments, bounded shifts and text slots after initial solving. Membership affinity penalizes distance outside a useful range; it never directly rewards all support symbols sharing one x coordinate. Allow space for the wires that explain a relationship. The NE5532 vertical-pillar failure should violate motif shape/spacing constraints even if affinity and total wire length improve.

## 6. Net-label and power policy

Choose presentation style before routing, recording a per-net reason:

- Use explicit wires for local signal chains, divider taps, analog feedback, timing, termination and critical power networks. Degree three or greater is not a reason to use labels.
- Use local labels to avoid long, unrelated traversals on one sheet when both endpoints remain readily discoverable. Permit labels at block interfaces; keep the inside of a protected motif explicit. Count reader jumps, not only label objects.
- Use hierarchical labels and matching parent-sheet pins for child interfaces. Preserve sheet-instance scope; identical local text in two child instances does not connect them.
- Use global labels for explicitly global interfaces only. Use a qualified global power symbol only for a genuinely global rail/reference with an exact approved value. A local reference or isolated return uses explicit wiring/hierarchical scope initially; KiCad 10 local power symbols are a later qualified alternative, not a global-ground workaround.
- Preserve split supplies, virtual grounds and references as distinct nets. A symbol that looks like ground cannot justify connecting them. PWR_FLAG is a power-source assertion, distinct from a supply/ground glyph; generate it only from accepted external-supply evidence and a version-qualified rule.

Set required net names through the smallest unambiguous set of labels/power values necessary; `automatic` names need no visible label. A continuity-label budget is assigned per interface in the semantic plan, not made proportional to net degree. Default budget is zero inside protected motifs; external block interfaces get one labeled island per participating block. Exceeding the budget requires a recorded alternative and quality review, not a silent route fallback.

KiCad's connection and label scopes are documented in its [schematic manual](https://docs.kicad.org/10.0/en/eeschema/eeschema.html). The policies above are deliberately stricter design choices. Hidden power pins require explicit resolution and export tests; unsupported implicit-power behavior stops compilation.

## 7. Orthogonal and multi-terminal routing

Route electrical hyperedges, not independent component-to-component edges. Each explicit net island produces a connected rectilinear tree whose leaves cover its assigned terminals; labels can join islands only under the approved scope plan.

1. Generate exact pin escape segments directed away from the body. Reserve pin access, motif feedback channels, labels, bus trunks, body/text envelopes and sheet borders as obstacles.
2. Build an orthogonal visibility graph from pin x/y coordinates, obstacle boundaries plus clearance, and reserved channel tracks. Nodes carry arrival direction so a bend has an explicit cost. Integer A* uses Manhattan lower bounds and stable `(cost, bends, x, y, direction, object_id)` ties.
3. For a multi-terminal net, seed a rectilinear minimum-spanning-tree ordering, then evaluate a bounded set of Hanan-grid Steiner branch candidates. Incrementally attach terminals to the **existing routed tree**, charging shared trunk length once. This is an approximation, not a claim of optimal rectilinear Steiner routing.
4. Order nets by protected motif/criticality, constrained access, fanout, then net ID. Supply buses are not routed first merely because they have many pins. Route feedback corridors before unrelated inter-block nets.
5. Allow unrelated-net crossings only as clear interior/interior orthogonal intersections outside protected regions, with no endpoint or junction at the crossing. Same-net connections are explicitly split into meeting segments. Never allow collinear overlap of different nets, a wire endpoint touching another net, or a wire crossing an unrelated pin.
6. Canonicalize collinear segments without deleting connection points. Emit junctions at intended degree-three-or-more branches, including four-way connections; reject ambiguous visual near-junctions. A wire may enter a symbol only along its actual pin conductor.
7. Rebuild connectivity from the completed scene and compare partitions before serialization. Repeat the check after real KiCad netlist export, which remains authoritative for KiCad interpretation.

Clearance incorporates text and pin numbers, not just rectangles around component origins. Routing costs are lexicographic: avoid illegality, protect motif paths, reduce reader ambiguity/crossings, then bends and added length. Local shared trunks are preferred over repeated label stubs. An unobstructed direct path should not gain ornamental loops to reduce a short-wire statistic.

On congestion, perform bounded rip-up/reroute using history costs and deterministic net ordering. Then expand the blocked channel or try another placement variant. The repair sequence is reroute → local shift/variant → block spacing → sheet partition. Revalidate constraints after every step. Never fix a routing failure by dropping a terminal or turning every net into labels.

## 8. Buses, repeated channels and hierarchy

Bus grouping comes from explicit IR members/protocol, not similar spelling. Choose a bus trunk only when it reduces interface clutter and preserves ordered breakout. Each scalar member has its own label and electrical attachment; graphical bus lines never union scalar nets. Member order, direction, aliases and hierarchical port correspondence must survive export. Test both vector buses and named groups, including bidirectional I2C and SPI signals with different directions.

Repeated channels use common grammar parameters, port order and alignment. Component-specific sizes may produce unequal spacing; consistency is measured relative to corresponding functional anchors. Shared supply regions must not visually mingle signal channels. Symmetry is a preference subordinate to real pin access and topology.

Partition by verified blocks/functions and routing capacity, not raw component count. First retain all indivisible motifs and strong local relationships. Starting profile targets occupied envelopes plus reserved channels below 65% of usable sheet area; a fit still requires actual route feasibility and readable text. Attempt A4, then A3, then child sheets when interface complexity is lower than a congested single-sheet solution. Authored sheet constraints take precedence.

Use deterministic greedy partitioning followed by pairwise moves minimizing cut **signal interfaces**, page count and fragmentation; power distribution has separate costs. Break ties by block ID. Generate one root and a tree of child sheet instances. In v0.1, repeated channels can have separate expanded files to simplify identity; reusable sheet-file instances are a later explicit capability with instance-path tests. Every cut net gets matched ports and a traceable scope mapping. Feedback, crystals and their immediate networks remain on one sheet unless explicitly overridden with accepted rationale.

## 9. Search, scoring and determinism

The solver-using M2 extension of `drafting.v1` permits beam width up to 8, at most 8 motif variants, 3 route-repair rounds per placement, and a fixed profile allocation of 20 CP-SAT deterministic-time units per block / 100 per sheet. Run one solver worker, fixed seed 0, stable variable insertion and documented solver version. The exact API parameters are qualified against the [upstream parameter schema](https://github.com/google/or-tools/blob/stable/ortools/sat/sat_parameters.proto). These budgets are engineering starting values, not runtime promises. A separately configured wall watchdog aborts rather than returning a machine-speed-dependent winner.

A candidate first passes electrical, collision, page and hard semantic constraints. Rank feasible candidates by `(semantic violations, reader jumps, ambiguous crossings, flow/power exceptions, crowding, bends, wire length, used area, canonical geometry digest)`. Inside a tier, documented normalized costs may be weighted; a lower tier cannot buy its way past a higher-tier violation. Retain a small Pareto set for explanation, then select deterministically. Do not claim global optimality after bounded search.

The final quality gate additionally checks per-topology limits and rendered review under [evaluation](EVALUATION_PLAN.md). Optimization cost and acceptance are intentionally separate. Increasing x-column count, lengthening wire stubs, hiding values, using giant sheets or replacing all wires with labels must not turn a poor drawing into an accepted one.

## 10. Failure contract and M1 boundary

Report `invalid` for electrical/relationship contradictions, `unsupported` for missing assets or capabilities, `infeasible` only when impossibility is established for the stated model, and `budget_exhausted` when bounded search finds no acceptable candidate. Attach conflicting constraint IDs, blocked terminals/channels, tried variants, partial diagnostic renders and exact input hashes. Diagnostic artifacts are visibly marked nonrelease and never returned as a successful project.

M1 implements only the divider grammar, its connector-NC variant, and ordinary orthogonal connections on one sheet. Place a divider as two vertical resistors with a rightward tap and a separate connector region. The NC connector variant uses the same composition and places an explicit NC marker at its unused pin. Derive spacing from occupied envelopes using the profile clearances, translate the composition to a grid-aligned origin within 20.32 mm left and 25.4 mm top margins, and route with exact pin coordinates. Enumerate finite legal transforms; no solver is needed for this grammar. M2 introduces general motif composition and, only where justified by measured conflicts, CP-SAT behind the same `SchematicLayout` interface. This narrow first slice proves the full electrical/export boundary before attempting general layout quality.

## 11. Composition and qualification guardrails

Rules emit reusable relations such as `before`, `adjacent`, `aligned-port`, `reserve-corridor`, `branch-at`, `same-sheet` and `explicit-path`, plus permissible variants. They do not own arbitrary component lists and rigid offsets. The active function, its feedback edge path and local reference provide anchors; symbol geometry sets distances. A single resistor may simultaneously be part of feedback, gain setting and a filter. Merge compatible constraints and report a minimal conflicting set of relationship/constraint IDs when composition fails; do not discard a lower-ranked accepted electrical relationship.

Before adding a named topology rule, try composition of existing relations. Require one case with overlapping feedback/filter relationships, two unlike cascaded stages, a rail-to-rail decoupler, and a different symbol pin ordering with no per-reference coordinate rule. Repeated channels share correspondence/order preferences, not forced bounding-box equality. A held-out composition must not require adding its own new template to pass the same frozen evaluation.

Large MCU symbols are not freely resynthesized by layout. Respect their locked pin groups and qualified alternate pin functions; move surrounding interface groups and route/label by semantic boundaries. If a clearer split symbol is required, propose a reviewed custom asset outside compilation. A signal-domain label cannot turn an inconvenient MCU pin into a different package contact. Keep mixed connectors together physically in the schematic when it aids pin-number lookup, even when their channels connect to several blocks.

The initial solver budgets in section 9 are ceilings for solver-using M2 experiments, not a command to run every layer of optimization. Compare constructive placement plus repair against CP-SAT on the same held-out cases and work budgets. Keep the simpler implementation when electrical legality, readability and bounded failure quality are comparable. A bounded search failure proves only that the searched variants failed; do not report physical impossibility outside that model.
