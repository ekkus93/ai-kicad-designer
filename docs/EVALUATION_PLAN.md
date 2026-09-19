# Evaluation Plan

Status: proposed qualification protocol, 2026-09-19. Evaluation certifies a stated capability envelope, never “all circuit design.” [Architecture](ARCHITECTURE.md) defines immutable inputs; [milestones](IMPLEMENTATION_PLAN.md) define when evidence is required. Numerical thresholds below are initial acceptance targets to freeze before experiments, not results achieved by this repository.

## 1. Separate questions and gates

A design can parse correctly, preserve connectivity, pass ERC, look poor, route badly and still fail its functional requirements. Record these outcomes separately.

| Gate | Evidence | Failure consequence |
|---|---|---|
| G0: valid input/assets | Strict schema, references, complete terminal inventory, reviewed asset/pin maps and supported capabilities | Stop target before generation |
| G1: electrical identity | Exact expected versus real KiCad-exported partitions, component identities and NC states | Reject artifact regardless of visual score |
| G2: geometric/presentation legality | No body/text collisions, unrelated wire-through-symbol/pin, out-of-page objects or ambiguous electrical intersections | Reject schematic candidate |
| G3: engineering rules | ERC and applicable domain/rating/relationship checks; explicit evidence for unresolved functional requirements | Block claimed engineering readiness |
| G4: readability | Per-topology structural envelopes, blind rendered review, adversarial metric tests | Withhold schematic-quality milestone |
| G5: physical implementation | Pad/net equivalence, fixed/region constraints, route completion, filled-copper DRC, SI/loop/return/thermal obligations | Withhold PCB/manufacturing readiness |
| G6: manufacturing | Validated exports, correct population/origin/layers/drills, CAM and assembly review | No release package |
| G7: reproducibility | Locked reruns reproduce core documents, geometry and normalized reports | Withhold deterministic-pipeline claim |

Each check reports `pass|fail|unsupported|not_evaluated` and links artifact hashes, rule version and observations. Unsupported constraints and missing reports are not passes. Review approval is bound to the exact artifact hash; a new layout invalidates the old visual approval. A successful M1 schematic does not imply G5/G6.

## 2. Corpus and metadata

Every fixture needs `fixture_id`, source/hash/license, family, intended capability, authoritative logical design, semantic annotations, expected gate outcomes, required libraries/toolchain, split assignment and review status. Keep pristine original KiCad files, any explicit converted version, IR migration report, renders, raw CLI outputs and normalized measurements separately. Tags may include `organization_reference`, `electrically_certified`, `manufacturing_certified`, `known_negative`, `legacy_comparison`; these are independent flags rather than one misleading “good” bit.

### Existing evidence

| Fixture | Correct use | Explicit limitation |
|---|---|---|
| Class-D | Control/driver/power partition, paired structures and signal progression | Simulation-oriented source; not an automatically accepted BOM/PCB or universal metric optimum |
| Sallen-Key | Two stages, local feedback and passive grouping, multi-unit power presentation | Conventional choices are contextual; upward grounds are present; source geometry is not a placement template |
| SensorProject | Hierarchy, MCU/interfaces, custom assets, real board and constraints | Working-prototype provenance is not independent manufacturing/electrical certification; dense regions remain critiqueable |
| Passive headphone bad/golden | Label-sprawl versus connected-tree comparison, branch/junction checks | `TestLib:R` stands in for connectors and other parts; baseline README repeats old expectations; electrical status must be measured |
| NE5532 regressed | Detect pillar composition, tangled feedback/support and detached output parts | Stored JSON says same-column support count 7 whereas README says 5; recompute rather than choose the convenient number |
| NE5532 current | Historical visual comparison and mandatory negative electrical test | Local KiCad 9.0.9 export has `VPLUS15={C1.1}` instead of four expected terminals; source IR differs from the regressed IR (18 versus 19 components) |
| 555 PWM | Timing-node, CTRL bypass, gate network and low-side load semantic invariants | IR-only baseline; it is not evidence that a new renderer or board succeeds |

Do not label the two NE5532 outputs a same-circuit quality improvement without reconciling their electrical inputs. A fresh comparison should regenerate both algorithms from one reviewed IR. No unverified local-only corpus is eligible.

### Required coverage progression

| Family | Required designs and variations | First emphasis |
|---|---|---|
| Basic passives | LED + resistor, divider, RC low/high-pass; short/long names, alternate symbols | M1–M2 |
| Analog | Buffer, inverting/non-inverting amplifier, Sallen-Key, multi-stage analog; gain/feedback variants | M2 |
| Supplies/references | Linear regulator, switching regulator, split supplies, virtual grounds/references; separated returns | M2–M4 |
| Timing/switching | 555, BJT/MOSFET switch, relay driver with protection, crystal/clock networks | M2–M4 |
| Embedded/interfaces | MCU minimum system, sensor interfaces, USB, I2C, SPI, UART; alternate pinouts/packages | M3–M6 |
| Structure | Buses, repeated channels, hierarchy, connector-heavy designs, mixed-signal designs | M3–M6 |
| Physical difficulty | Differential pairs, dense pad escape, two-sided assembly, odd outlines, fixed connectors, thermal/antenna keepouts | M4–M6, with unsupported advanced analysis reported explicitly |

For each qualified family include at least one authored minimal circuit, one realistic composition, one symbol/package substitution and one adversarial/negative case. Grow beyond the three existing positive projects. Share origins/topology ancestry across train/tune/holdout boundaries only within the same split: resistor-value or refdes variants of one circuit are not independent test examples.

## 3. Electrical-equivalence test oracle

Generate expected terminal inventory and net partitions from the accepted IR. Obtain observed partitions from a real, fresh KiCad netlist export. Map actual references/sheet instances bijectively to stable IDs; compare all members, named-net scope rules, package identities, values, approved parts and pin mappings. Report split/merged/missing/extra nets and terminals with exact differences. Handle symbol units and physical terminals separately. Inspect actual NC markers and hidden-pin effects; NC is not inferred from absence in XML.

For boards, compare every footprint/pad assignment to the expected logical terminal. Repeated pad geometries and internal jumpers need explicit tests; net-tie exceptions are localized. Then independently evaluate actual routed/filled connectivity and DRC. Pad net codes alone do not establish a conducting path or absence of shorts.

Mutation cases must all be rejected: remove one branch, move a wire off a pin by one grid unit, cross wires with/without a junction, merge a rail with a reference, duplicate a terminal, omit a power unit, mis-map a package pad, rename a required net, confuse identical local names across sheets, attach a bus member incorrectly, connect an NC pin, swap amplifier inputs, or short a net outside an approved tie footprint. Include invisible/hard-to-see defects. The NE5532 current baseline is a permanent rejection fixture even if its visual score rises.

Metamorphic tests preserve electrical invariants under entity-array permutation, wire subdivision, legal translation, unit drawing separation and accepted presentation changes. Do not assume arbitrary rotation/reflection preserves readable semantics, only connectivity. No test may derive its expected connectivity from the same emitted hidden metadata it is testing.

## 4. Schematic measurements

Compute measurements from the actual emitted scene and independent render observations, not merely the optimizer's internal cost. Normalize collinear wire subdivisions before bend/length metrics and distinguish virtual power objects, text, units and physical packages.

| Measurement | Definition / diagnostic |
|---|---|
| Symbol/text overlap | Intersections of occupied envelopes excluding explicitly permitted field/body relationships; include pin names/numbers |
| Wire-through-symbol | Unrelated segment intersects body or occupied pin/text region; legitimate pin conductor entry is excepted |
| Crossings / ambiguity | Unrelated interior crossings, endpoint near-misses, collinear overlaps, junction visibility; separate valid branches from crossings |
| Bends / detours | Direction changes in canonical net trees; routed length divided by an obstacle-aware lower bound, with bends localized per motif |
| Long wires | Count/length relative to usable sheet diagonal and expected block-local span, not only millimeters |
| Functional grouping | Intra-block compactness versus inter-block gaps, semantic interleaving, protected motifs split across regions |
| Feedback coherence | Source-to-sense path visibly local, explicit, traceable and in its reserved region; not just resistor distance to the op-amp center |
| Decoupling coherence | Correct consumer/supply association and compact readable support group; this does not certify PCB proximity |
| Flow | Reversed ordered functional edges after excluding feedback, supplies and declared bidirectional interfaces |
| Power presentation | Inconsistent rail/reference conventions, remote ambiguous sources, duplicated supply noise; count justified exceptions separately |
| Spacing / composition | Minimum and lower-tail envelope gaps, worst local congestion, block aspect ratios and occupied-area distribution |
| Labels / reader jumps | Labeled islands per net, unexplained breaks in local motifs, scope ambiguity and distance between corresponding islands |
| Buses | Member completeness/order, readable labels and breakout, crossing/ambiguity at entries, hierarchy correspondence |
| Repeated channels | Corresponding motif orientation/port-order consistency after normalizing local anchors and symbol sizes |

Absolute hard limits: zero electrical mismatches, unrelated symbol/body collisions, clipped required text, unrelated wire-to-pin contacts and page overflow. For minimal LED/divider/buffer motifs require zero unrelated wire crossings and zero continuity-label breaks inside the motif. Larger families get reviewed, frozen envelopes rather than a universal zero-crossings claim. Report worst case and per-family results; an average cannot hide one unusable schematic.

### Anti-gaming tests

| Metric shortcut | Adversarial layout | Required detector |
|---|---|---|
| Minimize length / crossings | Label every terminal | Reader jumps, protected explicit motifs and blind trace task |
| Increase x-columns | Move each stacked part sideways by one tick | Motif coherence and block aspect/role organization |
| Reduce stub ratio | Lengthen stubs or split/merge wire segments | Canonical net-tree measurement and detour factor |
| Increase spacing | Spread a small design over an enormous page or many sheets | Fixed page/text policy, interface cuts and task completion time |
| Eliminate overlap | Hide values or shrink text | Required-field presence and rendered readability at fixed scale |
| Improve average density | Sacrifice one dense critical region | Worst-window and per-motif limits |
| Maximize power-symbol count | Add redundant grounds/flags | Redundancy, electrical/source-assertion checks and review |
| Copy a reference | Reproduce coordinates for familiar part names | Held-out pinouts, symbol dimensions, topology compositions and renamed IDs |

A weighted score may order already feasible candidates but is never the acceptance gate. Keep raw metrics, semantic exceptions and review results; do not collapse them into one headline number.

## 5. Visual and engineering review

Produce clean KiCad SVG/PDF sheets, fixed-scale crops of critical motifs, and a separate diagnostic overlay. Use the same page size, minimum text size and render settings for comparisons. Randomize candidate order and hide algorithm/baseline names from reviewers. Review at full-sheet and readable printed scale, not only zoomed thumbnails.

Use two reviewers with relevant electronics experience for milestone gates, including one who did not author the layout rule. Ask them to identify blocks, trace a named input-to-output path, explain feedback/timing behavior, locate supply/return and decoupling, and map an interface across sheets. Record correctness, time and confusion points, plus 1–5 ratings for organization, path traceability, motif recognition, labeling and drafting consistency.

Initial acceptance: both reviewers report no severe defect, every dimension has a median of at least 4/5, no individual rating is below 3, and trace tasks are answered correctly. Compare trace time to a reviewed human reference where one exists; a >25% slowdown triggers investigation rather than automatic universal rejection. A milestone needs at least 90% acceptance on its valid held-out designs and no known severe regression. A failed design remains visible in the denominator and limits the qualified envelope.

A visual-language model can triage likely clutter or annotate areas for inspection with pinned prompts/model identifiers. Its output is nonauthoritative and may be nondeterministic. It cannot waive an electrical gate or replace the independent human milestone review. Human approval is an evidence input bound to hashes; core compilation remains reproducible without calling reviewers or models.

## 6. PCB and manufacturing evaluation

Measure hard mechanical violation counts, pad-access availability, specified decoupling pad distances and actual return lengths, clock paths, declared critical-loop area/perimeter/vias, differential skew/uncoupled length, return-plane discontinuities, congestion overflow, route completion, track/via counts, fixed-part drift, thermal obligations and assembly access. Report placement proxies separately from post-route measurements.

Test the congestion estimator against actual external routing on held-out placements, including deliberately compact but unroutable boards. Compare alternatives with identical outline, stackup, netlist and routing budget. Use hand-placed references where available; a different board outline is not a fair placement improvement. Never reward schematic-like placement unless it meets the physical constraints.

Require zero unexpected ERC/DRC violations for qualified outputs. Any allowed advisory must be narrowly documented and visible, never a blanket severity suppression. After routing and zone fill require complete physical connectivity, no shorts, consistent schematic/board mapping and every mandatory physical constraint verified. Impedance, current-carrying and thermal claims need their own evidence; ordinary DRC is insufficient.

Manufacturing checks parse Gerbers and drill files, compare extents/layers/polarities/holes to the validated board, reconcile BOM and position counts with population, verify units/origin/bottom rotations, and review independent CAM renders. Include DNP, through-hole, bottom-side and slotted-hole fixtures before advertising those capabilities. Fabricate and electrically inspect a small demonstrator before describing the process as manufacturing-proven; producing files alone is only export qualification.

## 7. Experimental discipline and milestone declarations

Split by circuit ancestry/topology, board origin and library variant. Keep a frozen tuning set and a genuinely held-out set; additions after viewing failures enter the next named evaluation revision. Record exclusions and reasons before scoring. Include unsupported requests as capability-coverage failures rather than removing them from the requested benchmark silently.

Use ablations: disable motifs, replace explicit routing with labels, remove congestion feedback, and remove semantic costs. Run a simple generic placement only as a comparator. Measure whether each added mechanism improves blinded readability/routability, not just its own objective. Do not import a large unlicensed corpus to increase sample size.

For each milestone record corpus revision, toolchain/policy hashes, all gate results, per-family acceptance, worst cases, runtime/memory distributions, deterministic reruns and outstanding unsupported capabilities. M1 needs deterministic electrical vertical slices, not a general readability claim. M2/M3 need real analog/hierarchy quality evidence. M4 needs constrained placement and router-boundary evidence. M5 needs manufacturing exports and a physical demonstrator. M6 needs breadth and held-out review before product infrastructure can start. Exact entry/exit requirements live in [the implementation plan](IMPLEMENTATION_PLAN.md).

Any metric threshold change after seeing test results creates a new protocol version and reruns the frozen corpus. Golden images/files require reviewed electrical and visual certification, not automatic snapshot updates. Golden bytes check deterministic regression; they never define the only acceptable geometry for future algorithms.
