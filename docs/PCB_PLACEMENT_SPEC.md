# PCB Placement Specification

Status: proposed physical-design contract, 2026-09-19. The logical design and constraint vocabulary are defined in [Circuit IR](CIRCUIT_IR_SPEC.md). PCB placement consumes those constraints and resolved footprints, never schematic coordinates.

## 1. Inputs, outputs and qualification scope

Input: `ResolvedDesign`, accepted mechanical requirements, locked stackup/fabrication profiles and a physical-search policy. Output: `BoardPlan`, feasible candidate `BoardLayout` objects, constraint witnesses, congestion estimates and a `RouteRequest`. Physical terminal identity is stable across footprints, pad shapes and schematic units.

First qualify ordinary two-layer, low-voltage rigid boards with at most 50 components, mostly orthogonal poses, real footprints and explicit connectors/mounting holes. This is a first implementation envelope, not an asserted algorithmic limit. Represent more advanced constraints immediately; return `unsupported` for a requested target whose mandatory constraints cannot yet be verified. An unrouted placement is never manufacturing-ready.

## 2. Mechanical model and legal poses

Board geometry consists of a closed non-self-intersecting outer polygon, explicit cutouts, holes, keepouts, layer stackup, component-height regions and manufacturing origin. V0.1 uses polygonal outlines; curved boards require a later qualified geometry capability. Holes and connectors get mechanically specified dimensions and tolerances from evidence, not guessed locations.

Use integer nanometers and an explicit top-view coordinate frame (+x right, +y up, counterclockwise rotation). Bottom placement reflects the footprint in the board plane and remaps layers without renumbering pads. The KiCad adapter owns coordinate/angle conversion; asymmetrical test footprints verify all allowed rotations and sides. Board coordinates cannot be inferred from schematic axes.

For each footprint, resolve copper, drill, mask/paste, courtyard, body, assembly and optional 3D envelopes. A missing courtyard cannot silently become a point; require a reviewed conservative envelope before placement qualification. Keep copper clearances, component assembly spacing and body overhang rules separate. Through-hole parts can obstruct both sides even when their bodies are on one side. Opposite-side components require 3D/lead clearance checks rather than a blanket exemption from overlap.

Use broad-phase spatial indexing and exact integer orientation/intersection predicates. For polygon boolean operations and clearance offsets, select a pinned Clipper2 implementation behind a small geometry adapter; its [upstream project](https://github.com/AngusJohnson/Clipper2) supplies clipping and offsetting. Quantization and conservative arc/offset tolerance are part of the adapter contract. Solver rectangles are only broad approximations; every candidate passes the actual polygon checker before acceptance.

Components are:

- **Fixed:** exact externally imposed position, side and angle; remove their pose variables from search.
- **Semi-fixed:** a legal edge interval/region plus allowed orientations and sides. Examples include a USB receptacle within a panel opening, LED behind a lens, or button under an actuator.
- **Free:** placement anywhere satisfying board, electrical and manufacturing constraints.

Connector mating direction, cable/tool access, switch travel, antenna keepout and power-entry clearances occupy real space. A centroid inside the outline is insufficient. An explicitly allowed connector body overhang does not permit pads, copper or unrelated components outside the board.

## 3. Electrical relationships become physical constraints

| Requirement | Placement treatment | Verification after routing |
|---|---|---|
| Decoupling | Minimize supply-pad-to-capacitor-pad distance and reserve a short return connection; group by consumer pins, not IC center | Supply/return path length, via count and placement in the actual current path |
| Crystal/clock | Place crystal and loads near oscillator pins; protect sensitive nets from unrelated routing | Actual loop/path lengths, return continuity and crossings of noisy regions |
| Switching converter | Treat declared high-di/dt loop as a cluster with ordered pad relationships; keep switch copper region bounded | Closed-loop perimeter/area, vias and switch-node extent on actual copper |
| Differential pair/USB | Preserve pair escape access and polarity; short symmetric path corridor and continuous reference | Skew, coupled/uncoupled length, gaps, via transitions and qualified impedance calculation |
| Termination | Place at the specified source/load pads, not merely in the same functional block | Stub lengths and actual path ordering |
| High current/power entry | Reserve adequate copper corridors, via arrays and connector access | Width/neckdown, copper thickness, thermal/current analysis and connector ratings |
| Analog/digital separation | Respect sensitive/noisy regions and return-current paths | No forced split-plane crossing; check return continuity |
| Antenna/RF | Enforce reviewed keepout, edge orientation and reference restrictions | Dedicated RF evidence; passing ordinary DRC cannot certify radiation behavior |
| Thermal/assembly | Respect heat-sensitive spacing, height, access and dissipation constraints | Thermal evidence plus fabrication/assembly inspection |

Critical distances use pad edges or routed paths, never component-origin distance alone. A placement lower bound does not satisfy a routed-path upper bound. Loop area is computed from the ordered loop edges in IR, not the bounding box of all pads on a net. No universal rule such as “every capacitor within 2 mm” replaces a datasheet-derived requirement.

The semantic block tree supplies cohesion preferences. Physical clusters may overlap in purpose and differ from schematic groups: a multi-unit amplifier's two signal stages share one package, and its decoupling must follow that package. Detect incompatible grouping requirements explicitly. Power-net degree must not pull every component toward the center of the board.

## 4. Objective and feasibility

Hard feasibility includes complete pin/pad mapping, fixed poses, legal board/keepout/height geometry, package envelopes, allowed side/rotation, actual specified proximity/loop limits that are placement-checkable, and process limits. Never soften a hard rule with a large penalty. Associate each result with `pass`, `fail`, `unsupported` or `not_evaluated` for every constraint ID.

Among feasible candidates, minimize a lexicographic vector:

1. Critical-path placement risk and escape obstruction.
2. Peak routing-capacity overflow and estimated unroutable demand.
3. Return-path discontinuity risk, block fragmentation and thermal-risk proxies.
4. Weighted estimated signal length/vias, assembly preference penalties and move distance from accepted prior placement.

Within a tier, use normalized bounded penalties with documented weights. For a maximum-distance preference use `max(0, measured/target - 1)`; do not reward violating another relationship to shave an already adequate distance. Power/ground nets use connection-to-plane/access models, not all-pairs attraction. For other multi-terminal nets, rectilinear Steiner/MST estimates avoid double-counting shared trunks. HPWL can be a fast coarse estimate but cannot be the acceptance criterion.

Stability is subordinate to electrical and mechanical correctness. After an incremental change, lock unaffected fixed parts and penalize movement of other unchanged parts; allow a broader solve only with a recorded reason.

## 5. Search and legalization

1. Validate mechanical geometry, terminal/pad mapping and necessary area/clearance conditions. Identify obvious contradictions, such as a fixed connector in a hard keepout. Necessary conditions are not a proof of routability.
2. Place fixed interfaces and mechanically constrained parts. Form critical clusters around decoupling, clocks and power loops. Enumerate a small set of legal relative variants using actual pad geometry.
3. Seed coarse placement with deterministic recursive partitioning of the weighted **electrical** hypergraph into legal physical regions. Preserve fixed anchors and reserve route channels. Use block affinity as a preference; do not reproduce schematic rows.
4. Use CP-SAT to choose cluster orientations, candidate regions and nonoverlapping envelopes for the small-board profile. Integer search positions initially use a 0.1 mm lattice, refined to 0.025 mm near constrained pads; exact externally fixed coordinates remain exact.
5. Improve feasible placements with deterministic large-neighborhood search: move one cluster, swap two compatible free clusters, rotate a footprint, or re-solve a congested window. Fixed neighborhood order, fixed seed, one solver worker and deterministic budgets prevent machine-speed-dependent selection.
6. Run exact polygon legality and pad-access checks on each candidate. If an approximate solver model admits a violation, add a geometric exclusion cut and re-solve; never accept an approximation as the board.
7. Evaluate the best four feasible candidates with a bounded route probe when the router is qualified. Feed failures and congestion hotspots back to local placement. Choose using routed feasibility first, not shortest unrouted estimates.

Initial policy `placement.v1`: at most 8 cluster variants, 4 retained candidates, 20 local neighborhoods and 3 placement/router feedback rounds. Allocate fixed solver deterministic-time budgets per profile. A watchdog abort yields an explicit failure. Report feasible/best-known results and bounds; do not label heuristic outcomes optimal. Simulated annealing is rejected initially because tuning and repeatability complicate diagnosis; a fixed-seed variant can be evaluated later if measured quality justifies it. A whole-board continuous force model is rejected as the primary engine because it handles fixed geometry and pin-access constraints poorly.

## 6. Congestion and routability estimation

Overlay a physical grid on each copper layer. Estimate horizontal/vertical channel capacity from usable width divided by trace width plus clearance, reduced by pads, obstacles, keepouts, via restrictions and plane requirements. Deposit net demand along alternative rectilinear paths; record peak overflow, distribution, blocked cutsets and pad escape options. Weight differential corridors and sensitive analog paths separately. Coarse cells begin at 1 mm with 0.25 mm refinement around dense pad fields, subject to board scale.

This estimate intentionally exposes uncertainty: it ignores detailed via interactions, diagonal routing choices and some return-path effects. Validate its usefulness by correlation with real route completion, vias and DRC across held-out boards. If it repeatedly favors unroutable placements, revise the model rather than declaring route failures out of scope. Rendering the capacity/overflow map makes the placement decision reviewable.

## 7. External-router contract

Select local Freerouting over Specctra DSN/SES as the first router to qualify. Candidate toolchain: Freerouting 2.4.1 with its compatible pinned JRE, exact configuration, one worker and finite pass counts. Its [versioned CLI documentation](https://raw.githubusercontent.com/freerouting/freerouting/v2.4.1/docs/command_line_arguments.md) supports headless input/output routing. This is a proposed dependency, not a claim that this repository has tested it or that every physical constraint transfers through DSN.

`RouteRequest` contains the placed-board digest, expected net/pad map, layer/rule map, fixed copper, keepouts, supported-rule projection, unsupported obligations, seed and pass budget. `RouteResult` returns input digest, tool/config digests, raw DSN/SES, imported board, preserved-object fingerprint, completion statistics and diagnostics. Network access and user configuration are disabled for the qualified invocation.

The adapter must enumerate which constraints are preserved natively, approximated conservatively, protected by pre-routed fixed copper, or unsupported. Differential impedance, return-plane continuity, thermal/current intent and tuned critical loops must not disappear into a generic clearance class. Initially route only boards in the ordinary low-speed supported envelope. Later protect sensitive paths with reviewed fixed routing and route the remainder only after testing that the external router preserves it.

Use KiCad's version-pinned DSN export/SES import bridge as defined in [integration](KICAD_INTEGRATION_SPEC.md). Apply sessions only to the exact source board. Verify unchanged footprint identities/poses, outline, nets, pad assignments, rules and protected copper, then fill zones and run DRC/connectivity again. Router completion statistics are advisory; zero remaining airwires is not evidence of no shorts.

Repeat the same route at least five times in clean work directories. Compare normalized copper geometry, not just reported lengths; retain timestamps/logs separately. A seed alone is not a determinism proof. If the candidate router remains nondeterministic, disable it for release builds and isolate/repair the source of nondeterminism or qualify another router. Caching a lucky result does not meet the requirement for a deterministic pipeline. This is an early qualification gate, not a reason to start building a full router.

## 8. Path to advanced boards and failure handling

Advance from placement-only evaluation to ordinary routed boards, then controlled groups of sensitive routes, then optional custom local escape/differential/critical-loop routing. Reuse the same RouteRequest and post-route validators. Only consider a new general router when comparative experiments show the external boundary cannot meet requirements despite good placement and rule projection.

For high-speed, RF or thermally demanding designs, reserve verification hooks for stackup-aware field solving, return-path analysis and thermal/assembly evidence. Unsupported analysis prevents the corresponding manufacturing release. Do not imply that DRC establishes operating performance.

Return explicit infeasible/budget/unsupported states with conflicting constraint IDs, coordinates and a diagnostic board render. Never move a fixed mounting hole, silently enlarge the board, swap connector pins, omit parts or downgrade constraints. A feasible placement with unrouted obligations is an inspectable milestone artifact, not a fabricated-board approval. Manufacturing acceptance is defined in [evaluation](EVALUATION_PLAN.md).
