# Circuit IR Specification

Status: proposed contract `0.1.0`, 2026-09-19. This document is normative for field meanings and validation. The implementation will supply strict Pydantic models and checked-in generated JSON Schema; neither exists yet. [Architecture](ARCHITECTURE.md) defines stages, [schematic layout](SCHEMATIC_LAYOUT_SPEC.md) and [PCB placement](PCB_PLACEMENT_SPEC.md) define their consumers.

## 1. Representation and evolution

Circuit IR describes an engineering design, not a KiCad document. It has four separate views: logical/electrical identity, schematic presentation requirements, PCB implementation requirements, and manufacturing/assembly requirements. Resolved library geometry and generated coordinates live in derived artifacts. Authored board boundaries and mechanically fixed positions are legitimate physical requirements; routine symbol and footprint placement coordinates are not.

Use UTF-8 JSON. Reject duplicate keys, extra fields, numeric coercion and unknown union discriminators. IDs match `[a-z][a-z0-9_.-]{0,95}` and are unique within their entity collection; references are typed by their field, not inferred from ID prefixes. IDs survive refdes/value changes. Human names are case-sensitive NFC strings; whitespace in names is preserved and checked, not silently stripped. Reference designators are unique across all instantiated physical components and cannot contain `?`.

`schema_version` uses SemVer. During `0.x`, a minor change may break compatibility; patch changes clarify without changing accepted meaning. Accept only explicitly supported versions. Migrations are pure, versioned functions yielding a new document, a field-level change report and old/new electrical fingerprints. Never migrate during compilation. Reject unknown required capabilities; optional extension data cannot influence compilation. A change to electrical semantics, pin mapping or unit interpretation requires a new minor version and compatibility fixtures.

Arrays of entities are sets sorted by ID in canonical output. Net members sort by `(component, terminal)`. Preserve ordered paths, polygon vertices, stackup layers, bus members, series elements and connector pin order. Hash canonical UTF-8 JSON with sorted object keys, compact separators and no timestamps. Normalize decimal strings to a nonexponential representation without trailing fractional zeroes; normalize negative zero to `0`. The canonical form and its version are part of the lock contract.

## 2. Primitive types

| Type | Wire representation and semantics |
|---|---|
| `TerminalRef` | `{ "component": Id, "terminal": Id }`; identifies one physical/electrical terminal, never a symbol-unit drawing |
| `FunctionRef` | `{ "component": Id, "function": Id }`; a subfunction such as one amplifier in a dual package |
| `Quantity` | `{ "value": DecimalString, "unit": Unit }`; finite signed decimal string, no implied units |
| `Range` | `{ "min": Quantity, "max": Quantity }`, same dimension, `min <= max` |
| Units | `V`, `A`, `ohm`, `F`, `H`, `Hz`, `s`, `W`, `degC`, `K/W`, `mm`, `mm2`, `deg`, `ratio`; exact SI prefixes are converted before acceptance, not stored |
| `Point` | `{ "x_mm": DecimalString, "y_mm": DecimalString }`, mechanical/physical requirements only |
| `Polygon` | Ordered list of at least three distinct Points; implicitly closed, no self-intersection; explicit holes stored separately |
| `EvidenceRef` | ID in `evidence`; confidence is annotation, never permission to violate a hard rule |
| `Constraint` | `{id, kind, strength, evidence, ...kind-specific fields}`; `strength` is `hard` or `prefer`; preferred constraints also require integer `priority` 0–9 (0 strongest) and positive integer `weight` |

Geometric quantities must convert exactly to integer nanometers; reject finer precision in version 0.1. Electrical values use decimal arithmetic. Geometry kernels and solver bounds check overflow. Tolerance is explicit where engineering requires it; numeric roundoff is not a tolerance policy.

Every field in the tables below is required unless marked `?`. Empty arrays express an explicitly empty collection; `null` is allowed only where specified. Defaulting optional display metadata must not change connectivity or hard requirements.

## 3. Top-level schema

| Field | Type and contract |
|---|---|
| `schema_version` | Literal `0.1.0` |
| `design` | `{id, name, revision: nonnegative integer, parent_digest: SHA256-or-null}` |
| `intent` | `{summary: string, requirements: Requirement[]}` |
| `assets` | `AssetRequest[]`, symbolic requests resolved by a separate immutable asset lock |
| `logical` | `{components, nets, blocks, domains, signal_classes, relationships, buses, no_connects, constraints}` |
| `schematic` | `{profile, symbols, constraints, hierarchy}` |
| `pcb` | `null` or `{board, footprints, constraints}` |
| `manufacturing` | `{profile: Id-or-null, variants: Variant[], constraints: Constraint[]}` |
| `evidence` | `Evidence[]` |
| `extensions?` | Namespaced metadata object, excluded from decisions unless promoted to a versioned schema field |

`Requirement = {id, text, verification: "inspection"|"analysis"|"simulation"|"measurement", evidence: EvidenceRef[]}`. Requirements are claims to verify, not automatic proof. A report records `not_evaluated` until its evidence exists.

`Evidence = {id, kind, locator, assertion, review, confidence?}`. `kind` is `user_requirement|datasheet|library|import|engineering_review|inference`; locator is a document path/URI plus optional section, and downloaded sources are content-hashed in the lock. `review` is `proposed|accepted|rejected`; confidence, if present, is a decimal string in `[0,1]`. Accepted means accepted as an input assertion, not experimentally verified. An inferred voltage rating without reviewed source evidence cannot authorize fabrication.

`AssetRequest = {id, kind: "symbol"|"footprint", library_id: string-or-null, custom_requirement?: CustomAsset}`. Exactly one existing library selection or custom requirement is supplied. A locked asset records original file hash, transitive inheritance hashes, selector, license, source revision and resolved semantic/geometry digest. No directory search-order dependence is allowed.

`CustomAsset = {reason, evidence, terminals, requirements}`: terminals enumerate required pin/pad identities; requirements refer to mechanical drawings, electrical pin types, body/lead dimensions and verification criteria. A separate asset-authoring process must produce a reviewed, locked library asset. Unfulfilled requests produce `ASSET_UNRESOLVED`; the compiler never invents a placeholder from the connected pins alone.

## 4. Logical and electrical schema

### Components, terminals and functions

`Component = {id, refdes, kind, value, part, role, owner_block, terminals, functions, properties?}`.

- `kind`: `resistor|capacitor|inductor|diode|transistor|ic|connector|switch|relay|crystal|testpoint|net_tie|mechanical|other`. `role` is an engineering description; it is not parsed as an algorithm instruction.
- `value`: a Quantity or `null` for a component with no single scalar value. `part`: `null` or `{manufacturer, mpn, datasheet_evidence}`. Schematic exploration may use generic passives; populated manufacturing variants require an approved MPN or an explicitly approved generic procurement specification.
- `properties`: typed optional `tolerance` (ratio), `voltage_rating`, `current_rating`, `power_rating`, `temperature_range`, `package_name`, and `generic_procurement_spec` string. Values do not replace datasheet evidence.
- `Terminal = {id, number, name, electrical_type, role, domain: Id-or-null, limits?}`. `number` is a string, preserving alphanumeric package pins. Type is `input|output|bidirectional|tri_state|passive|power_in|power_out|open_collector|open_emitter|unconnected|unspecified`. `limits` optionally holds voltage/current Ranges. All terminals, including unused and hidden pins, must be enumerated.
- `Function = {id, role, terminals: Id[], owner_block}` identifies an amplifier, gate, power unit or similar function. Functions may share supply terminals; they do not duplicate electrical terminals. A component has one package owner; functions may belong to different child blocks.

Electrical types are checked against the resolved symbol, with mismatches requiring an explicit reviewed asset correction. Functional direction (for example a passive filter's input/output) is a separate relationship and is never inferred simply from a `passive` pin type.

### Nets, domains and membership

`Net = {id, name, name_policy, scope, members, domain, signal_class, criticality?}`. `name` is string-or-null; `name_policy` is `required|display|automatic`; `required` requires a name preserved in the export, including its explicit scope mapping. `scope` is `global` or a block ID. Members are nonempty TerminalRefs with no duplicates. `domain` and `signal_class` are IDs or null. Optional `criticality` is `normal|sensitive|critical`, defaults to `normal`, and affects search priority only; mandatory behavior requires an explicit hard constraint.

Every enumerated terminal appears exactly once, either in one net or in `NoConnect = {terminal, reason, evidence}`. An absent terminal is an error. A singleton net requires an explicit external/test interface or documented purpose; it is not equivalent to NC. NC markers must be emitted at every applicable presentation occurrence and verified independently of the netlist. Pins forbidden to connect by their asset may only be NC.

`Domain = {id, kind, reference_net, rail_nets, voltage, sources, evidence}`. Kind is `power|analog|digital|chassis|isolated`; reference/rail nets are IDs, voltage is Range-or-null relative to the reference net. Sources are `{terminal, kind: "external_supply"|"regulator"|"battery", evidence}`. Distinct reference nets remain distinct even if named `GND`, `0V`, `AGND` or `VREF`. Connecting them needs explicit topology, such as a net-tie component, not alias normalization.

`SignalClass = {id, kind, voltage?, current?, frequency?, edge_time?, reference_domain?, constraints: Constraint[]}`; kind is `power|analog|digital|clock|differential|rf|other`. Voltage/current/frequency use Ranges; edge time is Quantity. Expected current is not a trace-width answer; stackup, copper, temperature rise and review remain necessary.

### Electrical operating constraints

`logical.constraints` contains electrical `Constraint` objects. Signal-class constraints use the same kinds with explicit targets; membership in a class does not invent operating values. Initial tagged union:

| Kind | Required payload and verification |
|---|---|
| `elec.voltage` | `net, reference_net, allowed: Range`; compare evidenced worst-case operating envelope, never just the nominal rail name |
| `elec.current` | `source, sink: TerminalRef, allowed: Range`; positive current flows from source toward sink; operating analysis must define the path/load |
| `elec.power` | `component, max_dissipation: Quantity, derating: Quantity`; derating is a ratio in `(0,1]` applied to the evidenced rating |
| `elec.logic_compatibility` | `driver: TerminalRef, receivers: TerminalRef[], operating_mode: string`; compare output/input thresholds and absolute limits over supply/temperature corners |
| `elec.isolation` | `domains: Id[2], min_withstand_voltage: Quantity, evidence`; no direct net membership across the boundary; isolation components and physical clearance need separate verification |
| `elec.fanout` | `driver: TerminalRef, loads: TerminalRef[], max_capacitance: Quantity, max_frequency: Quantity`; aggregate evidenced load/input models |

Every hard operating constraint requires a verified analysis, simulation or measurement result to claim engineering readiness. Missing ratings or operating envelopes yield `not_evaluated` or `unsupported`, never guessed success. Schematic compilation can still produce a clearly labeled engineering draft when topology is valid; manufacturing is blocked until these obligations are discharged. Structural predicates such as duplicate membership cannot be deferred this way. M1 supports empty electrical-constraint arrays and reports prose requirements as unevaluated; M2 onward adds explicitly qualified analyses.

### Blocks, buses and relationships

`Block = {id, parent: Id-or-null, name, role, ports: BlockPort[]}`. Exactly one root, acyclic parent links. Every component/function owner resolves. `BlockPort = {id, net, direction, role}`; direction is `in|out|bidirectional|passive|power`. Ports expose existing nets; they do not create or union nets. Repeated channels have distinct component/net IDs and explicit correspondence. Version 0.1 compiles fully expanded designs; it does not require a template language.

`Bus = {id, name, members, protocol, participants, constraints}`. Members are ordered `{name, net, direction}` objects, protocol is `parallel|i2c|spi|uart|other`, participants are block IDs. A bus is an interface grouping, not an electrical connection between its members. Address/data vectors and mixed named bundles use the same ordered model. Specify signal-specific direction; I2C is not forced into a unidirectional pipeline.

`Relationship = {id, kind, evidence, ...}` is a closed tagged union:

| `kind` | Required payload and validation |
|---|---|
| `signal_path` | `terminals: TerminalRef[]`, `through: FunctionRef[]`; ordered signal progression validated against nets and component functions, not a demand that all terminals share a net |
| `divider` | `upper, lower: component IDs`, `high_net, tap_net, reference_net`; validate exactly the claimed resistor incidence |
| `feedback` | `source, sense: TerminalRef`, `elements: component IDs[]`, `polarity: negative\|positive\|unknown`; verify the declared path and active function; no polarity guessing from reference names |
| `decoupling` | `capacitors: component IDs[]`, `consumers: TerminalRef[]`, `supply_net, return_net`; each capacitor spans the claimed rails; proximity limits belong to PCB constraints |
| `termination` | `elements`, `signals: net IDs[]`, `at: source\|load\|both`, `endpoint: TerminalRef`; topology and termination values require engineering evidence |
| `associated` | `anchor: FunctionRef-or-TerminalRef`, `components: ID[]`, `purpose: string`; grouping preference only, never connectivity proof |
| `differential_pair` | `positive_net, negative_net`, `source: TerminalRef[2]`, `sink: TerminalRef[2]`; ordered polarity and distinct nets; skew/impedance are constraints |
| `clock` | `source: TerminalRef`, `loads: TerminalRef[]`, `frequency`, `reference_net` |
| `critical_loop` | `path: TerminalRef[]`, `edges: LoopEdge[]`, `mode: string`; ordered closed path including intra-component transitions and routed-net edges |
| `repeated_channel` | `blocks: ID[]`, `correspondence: object[]`; each object maps every listed block ID to corresponding FunctionRef or TerminalRef; no implicit reference suffix matching |
| `internal_short` | `component`, `terminals: ID[]`, `evidence`; asset/datasheet-backed internal conduction; all assigned to the same net |
| `net_tie` | `component`, `groups: ID[][]`; each group lists terminals connected only within the approved tie footprint; logical nets remain distinct |

`LoopEdge = {from: TerminalRef, to: TerminalRef, via_net: Id-or-null, via_component: Id-or-null}`; exactly one `via_*` is non-null. Endpoints must match the ordered path, with the last edge returning to the first. Net edges require both endpoints on that net. Component edges require both on that component. A loop bound can therefore measure the intended current loop rather than an arbitrary net bounding box.

## 5. Schematic view

`schematic.profile` names an immutable drafting policy (`drafting.v1` initially). `symbols` contains `SymbolUse = {id, component, function: Id-or-null, asset, unit: positive integer, body_style: positive integer, pin_map}`. `pin_map` maps visible/hidden symbol pin-number strings to terminal IDs of the component. Unit 0/common graphics is resolved by the asset adapter, not an extra package. All package terminals must be covered, including dedicated power units and unused functions. A terminal may have multiple graphical occurrences only where the resolved library explicitly declares the shared pin identity.

`hierarchy = {root_sheet, sheets}`; a sheet is `{id, parent: Id-or-null, blocks: ID[], page: "A4"|"A3", orientation: "landscape"|"portrait"}`. An empty `sheets` array requests deterministic partitioning with the specified root ID. No independently named net is created merely by assigning a block to a sheet. Child interfaces are generated from block ports and net cuts.

Schematic constraint kinds:

| Kind | Payload |
|---|---|
| `sch.order` | `before, after`: symbol-use or block IDs; `axis: x\|y` |
| `sch.orientation` | `symbol`, `allowed: {rotation_deg: 0\|90\|180\|270, mirror_x: bool, mirror_y: bool}[]` |
| `sch.group` | `members: symbol-use IDs[]`, `max_span_mm?: Quantity` |
| `sch.align` | `members`, `axis: x\|y`, `anchor: origin\|input_port\|output_port` |
| `sch.net_style` | `net`, `style: explicit\|local_label\|global_label\|power`; style must be legal for scope |
| `sch.sheet` | `block`, `sheet` |
| `sch.keep_motif` | `relationship`; prohibit splitting that verified relationship across sheets or label-only fragments |

Hard orientation constraints still require a library-valid transform; they cannot exchange op-amp inputs. Layout output, including text positions, belongs to `SchematicLayout`, not this section.

## 6. PCB, mechanical and manufacturing views

`Board = {id, outline, cutouts, stackup_profile, origin, holes, keepouts}`. Outline is a Polygon in v0.1; curved outlines are a future explicit capability, rejected rather than silently flattened. `origin` is a Point specifying manufacturing origin. Mechanical coordinates use a right-handed top view: +x right, +y up, angles counterclockwise. Conversion to KiCad and bottom-side poses is adapter-owned and tested.

`Hole = {id, center, diameter, plated: bool, net: Id-or-null, clearance}`; unplated mounting holes have null net. `Keepout = {id, polygon, layers: string[], prohibits: ("component"|"copper"|"via"|"track")[], height_limit?: Quantity}`. Layers resolve against the stackup profile. Component overhang and antenna exceptions require named constraints, not global outline exemptions.

`FootprintUse = {id, component, asset, pad_map, allowed_sides, allowed_rotations_deg}`. `pad_map` maps every pad number to a terminal ID, or null only for genuinely nonelectrical pads. Repeated physical pad shapes with one number remain separate geometries with the same mapped terminal. Different numbers shorted by the package require an `internal_short`; a copper net tie requires `net_tie`. Mechanical components have no logical terminals but still require a physical instance if assembled.

| Constraint kind | Required payload and meaning |
|---|---|
| `pcb.fixed` | `footprint, position, rotation_deg, side: top\|bottom`; externally imposed pose |
| `pcb.region` | `footprint, polygon, rotations_deg, sides`; allowed pose set for a semi-fixed component |
| `pcb.edge_access` | `footprint, edge_index, max_distance, outward_axis_deg, access_polygon`; connector/button/LED mating or access space |
| `pcb.proximity` | `a, b: TerminalRef`, `max_distance`, `metric: pad_edge\|routed_path`; a placement proxy cannot pass a routed-path requirement |
| `pcb.loop` | `relationship`, `max_perimeter`, `max_area`, `max_vias`; refers to a critical loop, checked again on routed copper |
| `pcb.net_rule` | `nets: ID[]`, `min_width, clearance, via_diameter, via_drill`, `allowed_layers` |
| `pcb.length` | `source, sink: TerminalRef`, `max_length`, `max_vias` |
| `pcb.differential` | `relationship`, `impedance`, `impedance_tolerance`, `max_skew`, `max_uncoupled_length`, `reference_layer`, `gap` |
| `pcb.return_path` | `nets`, `reference_net`, `reference_layers`, `max_reference_gap`; constrains actual return continuity |
| `pcb.separation` | `a, b: block IDs`, `min_distance`; does not automatically split ground planes |
| `pcb.cohesion` | `block`, `max_diameter` |
| `pcb.thermal` | `components`, `max_junction_temperature`, `ambient`, `power_dissipation`, `evidence`; analytic/simulation verification capability required |
| `pcb.height` | `footprints`, `max_height`, `region?: Polygon` |
| `pcb.overhang` | `footprint`, `allowed_polygon`; only declared body geometry may exceed outline; pad/copper bounds remain enforced |
| `mfg.process` | `profile`, `min_track`, `min_clearance`, `min_drill`, `min_annular_ring`, `copper_thickness` |
| `mfg.assembly` | `allowed_sides`, `min_component_gap`, `fiducials: ID[]`, `test_access: TerminalRef[]` |

All dimensions in this table are Quantities (area in `mm2`, impedance in `ohm`, skew in `mm` for v0.1). Footprint/component lists identify their respective entity types; constraints cannot target arbitrary text selectors. Constraint IDs link diagnostics and verification coverage. `manufacturing.profile` and stackup profiles reference immutable, versioned records in the policy lock, including fabricator limits, copper/dielectric layers, material properties and their evidence. A profile is not a generic claim that all manufacturers accept it.

`Variant = {id, name, population}` with population entries `{component, fitted: bool, approved_part: Part-or-null}`. Every assemblable component has exactly one entry. DNP excludes assembly/BOM population but normally retains board pads. Substitutions must preserve or explicitly revise verified pinout, footprint and ratings. Variant changes affecting required circuitry rerun electrical/functional checks; a DNP flag is not a topology repair. Position output includes side, centroid, rotation and documented assembler convention.

## 7. Representative complete schematic design

This is the M1 voltage-divider example. It is structurally complete for schematic compilation; the asset lock must supply the two requested library symbols plus the drafting profile's standard power assets. Generic parts and `pcb: null` intentionally make it ineligible for manufacturing. The externally supplied rail is an accepted requirement, not an inferred power source.

```json
{
  "schema_version": "0.1.0",
  "design": {"id": "divider.demo", "name": "DividerDemo", "revision": 0, "parent_digest": null},
  "intent": {"summary": "Divide an externally supplied 5 V signal by two into a high impedance load.", "requirements": [
    {"id": "req.ratio", "text": "Nominal unloaded ratio is 0.5; load resistance is at least 1 megohm.", "verification": "analysis", "evidence": ["ev.requirement"]}
  ]},
  "assets": [
    {"id": "sym.r", "kind": "symbol", "library_id": "Device:R"},
    {"id": "sym.j3", "kind": "symbol", "library_id": "Connector_Generic:Conn_01x03"}
  ],
  "logical": {
    "components": [
      {"id": "r.upper", "refdes": "R1", "kind": "resistor", "value": {"value": "10000", "unit": "ohm"}, "part": null, "role": "upper divider resistor", "owner_block": "blk.divider", "terminals": [
        {"id": "p1", "number": "1", "name": "1", "electrical_type": "passive", "role": "high", "domain": "dom.input"},
        {"id": "p2", "number": "2", "name": "2", "electrical_type": "passive", "role": "tap", "domain": "dom.input"}
      ], "functions": []},
      {"id": "r.lower", "refdes": "R2", "kind": "resistor", "value": {"value": "10000", "unit": "ohm"}, "part": null, "role": "lower divider resistor", "owner_block": "blk.divider", "terminals": [
        {"id": "p1", "number": "1", "name": "1", "electrical_type": "passive", "role": "tap", "domain": "dom.input"},
        {"id": "p2", "number": "2", "name": "2", "electrical_type": "passive", "role": "return", "domain": "dom.input"}
      ], "functions": []},
      {"id": "j.io", "refdes": "J1", "kind": "connector", "value": null, "part": null, "role": "VIN, sense and return interface", "owner_block": "blk.root", "terminals": [
        {"id": "p1", "number": "1", "name": "VIN", "electrical_type": "passive", "role": "external_supply", "domain": "dom.input"},
        {"id": "p2", "number": "2", "name": "SENSE", "electrical_type": "passive", "role": "sense_output", "domain": "dom.input"},
        {"id": "p3", "number": "3", "name": "RETURN", "electrical_type": "passive", "role": "return", "domain": "dom.input"}
      ], "functions": []}
    ],
    "nets": [
      {"id": "net.vin", "name": "VIN", "name_policy": "required", "scope": "global", "members": [{"component": "j.io", "terminal": "p1"}, {"component": "r.upper", "terminal": "p1"}], "domain": "dom.input", "signal_class": null},
      {"id": "net.sense", "name": "SENSE", "name_policy": "required", "scope": "blk.root", "members": [{"component": "r.upper", "terminal": "p2"}, {"component": "r.lower", "terminal": "p1"}, {"component": "j.io", "terminal": "p2"}], "domain": "dom.input", "signal_class": null},
      {"id": "net.return", "name": "0V", "name_policy": "required", "scope": "global", "members": [{"component": "r.lower", "terminal": "p2"}, {"component": "j.io", "terminal": "p3"}], "domain": "dom.input", "signal_class": null}
    ],
    "blocks": [
      {"id": "blk.root", "parent": null, "name": "Interface", "role": "design", "ports": []},
      {"id": "blk.divider", "parent": "blk.root", "name": "Divider", "role": "voltage scaling", "ports": [
        {"id": "in", "net": "net.vin", "direction": "in", "role": "input"},
        {"id": "out", "net": "net.sense", "direction": "out", "role": "sense"},
        {"id": "return", "net": "net.return", "direction": "power", "role": "reference"}
      ]}
    ],
    "domains": [{"id": "dom.input", "kind": "power", "reference_net": "net.return", "rail_nets": ["net.vin"], "voltage": {"min": {"value": "4.75", "unit": "V"}, "max": {"value": "5.25", "unit": "V"}}, "sources": [{"terminal": {"component": "j.io", "terminal": "p1"}, "kind": "external_supply", "evidence": ["ev.requirement"]}], "evidence": ["ev.requirement"]}],
    "signal_classes": [],
    "relationships": [{"id": "rel.divider", "kind": "divider", "upper": "r.upper", "lower": "r.lower", "high_net": "net.vin", "tap_net": "net.sense", "reference_net": "net.return", "evidence": ["ev.requirement"]}],
    "buses": [],
    "no_connects": [],
    "constraints": []
  },
  "schematic": {
    "profile": "drafting.v1",
    "symbols": [
      {"id": "s.upper", "component": "r.upper", "function": null, "asset": "sym.r", "unit": 1, "body_style": 1, "pin_map": {"1": "p1", "2": "p2"}},
      {"id": "s.lower", "component": "r.lower", "function": null, "asset": "sym.r", "unit": 1, "body_style": 1, "pin_map": {"1": "p1", "2": "p2"}},
      {"id": "s.io", "component": "j.io", "function": null, "asset": "sym.j3", "unit": 1, "body_style": 1, "pin_map": {"1": "p1", "2": "p2", "3": "p3"}}
    ],
    "constraints": [{"id": "sch.divider", "kind": "sch.keep_motif", "strength": "hard", "relationship": "rel.divider", "evidence": ["ev.requirement"]}],
    "hierarchy": {"root_sheet": "sheet.root", "sheets": [{"id": "sheet.root", "parent": null, "blocks": ["blk.root", "blk.divider"], "page": "A4", "orientation": "landscape"}]}
  },
  "pcb": null,
  "manufacturing": {"profile": null, "variants": [], "constraints": []},
  "evidence": [{"id": "ev.requirement", "kind": "user_requirement", "locator": "docs/CIRCUIT_IR_SPEC.md#7-representative-complete-schematic-design", "assertion": "Externally supplied divider test circuit and high impedance load.", "review": "accepted"}]
}
```

For an op-amp, one logical component owns physical terminals `1`–`8`; functions A and B reference their signal pins and shared supplies. Three SymbolUses can select units A, B and power. Splitting those drawings creates neither additional BOM items nor additional electrical terminals. For a crystal, the `clock` relationship identifies source/load, `associated` identifies load capacitors, and `pcb.proximity`/`pcb.return_path` carry physical obligations. These relationships supplement, never replace, net membership.

## 8. Validation layers and implementation profile

Validation order is schema → references and units → terminal/net totality → asset resolution → pin/unit/pad agreement → relationship predicates → constraint contradictions → target readiness. Return all independently discoverable errors in stable order. Never drop an unsupported constraint to get a layout.

Cross-layer invariants include bijective component/reference maps; exact physical terminal inventory; explicit sheet-scope naming; every routed segment owned by exactly one net; every bus member preserved; every populated component mapped to a footprint and BOM row. Internal-short equivalence is derived only from explicit, asset-backed groups. Net-tie exceptions are local copper rules, not global partition merging. Mechanical constraints may conflict with electrical proximity; report the involved IDs instead of choosing one silently.

The M1 executable profile supports single-sheet, single-unit resistor/LED/connector examples; the `divider` relationship; symbol resolution; net totality; source/return domains; `sch.keep_motif`; required/display/automatic names; and NC representation. The shipped example above is its exact divider input. Add a separate LED fixture with explicit anode/cathode identity. Recognized future fields may be schema-valid but must yield `unsupported` when the requested target depends on an unimplemented capability. PCB/manufacturing checks are `not_evaluated` during schematic-only builds; their omission cannot be interpreted as approval. All multi-unit, bus, hierarchy and physical cases require the later profile gates in [the implementation plan](IMPLEMENTATION_PLAN.md).
