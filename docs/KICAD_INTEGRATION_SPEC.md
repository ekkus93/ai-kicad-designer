# KiCad Integration Specification

Status: proposed adapter contract, researched 2026-09-19. **Facts** below describe documented KiCad behavior; **decisions** describe this project's planned implementation. No KiCad 10 installation or end-to-end manufacturing qualification was performed during this architecture task.

## 1. Supported-version policy

**Fact:** KiCad 10.0.6 is an officially released stable version, published 2026-08-29. [Release announcement](https://www.kicad.org/blog/2026/08/KiCad-10.0.6-Release/)

**Decision:** qualify the first output backend against **KiCad 10.0.6 on Linux x86-64**. Pin the actual executable/package build, libraries, configuration, fonts and operating-system image by hash; `10.0` alone is not a toolchain lock. Older corpus artifacts are read-only inputs; their conversion is explicit and preserves originals. There is no promise of writing files compatible with KiCad 9. Every patch upgrade requires adapter, electrical, render and manufacturing regressions. Major upgrades require a separate backend qualification and review of APIs and formats.

**Observed locally:** `kicad-cli version` reported `9.0.9`. A temporary XML export of the NE5532 current baseline reproduced its documented incomplete `VPLUS15` net despite exit code zero and an annotation warning. The local system Python exposes `LoadBoard`, `SaveBoard`, `ExportSpecctraDSN` and `ImportSpecctraSES`. These are useful probes, not KiCad 10 qualification.

## 2. Documented facts and chosen boundary

| Documented fact | Project decision |
|---|---|
| Schematics, boards, symbol/footprint libraries use S-expressions; coordinate values are in millimeters. [Format introduction](https://dev-docs.kicad.org/en/file-formats/sexpr-intro/) | Use a typed AST codec and exact decimal conversion at the file boundary. |
| Schematics contain embedded symbol definitions, symbol instances and hierarchy paths. [Schematic format](https://dev-docs.kicad.org/en/file-formats/sexpr-schematic/) | Generate explicit instances and stable UUIDs; verify multi-unit/hierarchy identity independently. |
| Board files describe footprints, pads, nets, layers, tracks and zones. [Board format](https://dev-docs.kicad.org/en/file-formats/sexpr-pcb/) | Generate board structure directly from `BoardLayout`, without a GUI “update PCB” step. |
| Project settings use JSON `.kicad_pro`. [KiCad developer announcement](https://forum.kicad.info/t/new-project-file-format/23705) | Own a version-tested minimal project template plus typed settings/rule projection. |
| KiCad 9/10 IPC requires a running GUI; the development documentation describes headless support for 11. [IPC limitations](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/) | Do not make IPC a dependency of the stable headless compiler. Reassess when a suitable stable release is qualified. |
| SWIG bindings are deprecated; removal is planned for KiCad 11. [Binding policy](https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/) | Permit only an isolated, replaceable KiCad 10 DSN/SES bridge, not domain objects throughout the core. |
| The PCB editor supports DSN export and SES routing import into the corresponding existing board. [Router workflow](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html) | Preserve the exact placed source board and verify that the imported session changes only permitted routing. |

The stable 10 CLI reference documents ERC, DRC, netlists, renders and exports, but no DSN/SES subcommand. **Inference/decision:** use the narrow bridge below; do not invent `kicad-cli pcb export dsn`. [CLI reference](https://docs.kicad.org/10.0/en/cli/cli.html)

## 3. File parsing and generation

Implement a small UTF-8 S-expression tokenizer/parser with atoms retaining exact lexemes, quoted strings, source locations, limits and a generic AST. The semantic layer decodes only supported forms. Unknown nonsemantic data in imported documents remains opaque; unknown electrical or physical constructs make qualification unsupported. Syntax preservation is not a claim of understanding.

Generated artifacts use canonical ordering, deterministic UUIDv5 identifiers, exact decimal millimeters and no machine-specific paths or wall-clock timestamps. Set the generator to this project, not `eeschema` or `pcbnew`. The backend's header/version tags and mandatory fields come from qualification fixtures saved/read by the exact supported version; do not infer a header date from the calendar or copy a KiCad 9 header unchanged.

Separate codecs for symbols, schematics, footprints, boards and library tables. Use ordinary JSON serialization for `.kicad_pro`; custom design rules have their own validated syntax. Emit only documented/tested fields. Preserve arbitrary user documents only in an explicit import workflow; early milestones create a new project rather than promise lossless editing.

Pin transforms get their own tests: symbol-library coordinates, placed schematic coordinates, mirrors, rotations, text, common-unit graphics, alternate body styles and bottom-side footprints are not assumed to share one sign convention. Keep logical pin identity outside the graphics transform. Missing units, unresolved inheritance or ambiguous pin numbering are hard failures.

A successful internal parse is only the first test. Acceptance requires KiCad export/reload behavior, observed net membership and version-qualified validation. Structural normalization never repairs an emitted invalid project before evaluating it. Corpus conversions, if necessary, generate separate artifacts with before/after connectivity evidence.

## 4. Libraries and asset resolution

**Decision:** use explicit asset requests plus `assets.lock.json`; never discover assets from arbitrary user library search order during a build. Resolve qualified library IDs against pinned symbol and footprint snapshots. Record source, license, file content hashes, inherited bases and the selected unit/style. Validate complete pin inventories, electrical types, physical pad maps and geometry before layout.

Use standard library assets whenever suitable. Embed the used resolved symbol definitions in schematics and footprint instances in the board as required by their formats. Do **not** create project-local duplicate symbol/footprint libraries just to rename normal parts. Portable editing uses the locked standard library release or an explicit dependency bundle of that release.

Create `project.kicad_sym` and `project.pretty/*.kicad_mod` only for reviewed custom assets or a necessary unavailable dependency with known provenance. Use project-relative `sym-lib-table`/`fp-lib-table` entries for those assets; `${KIPRJMOD}` resolves project-local references. Test a relocated project under a clean configuration. Preserve original library identity in the asset manifest rather than forcing every imported symbol into a synthetic “project” library.

A custom asset requires a reason, datasheet/mechanical evidence, complete pin/pad correspondence, courtyard/body geometry and a review record. Pin count inferred only from currently connected nets is insufficient. Placeholder assets may appear in diagnostic illustrations, but never in a successful compiled design.

For KiCad power semantics, keep an explicit adapter test matrix covering visible power symbols, hidden power inputs, local references and split supplies. Ordinary power symbols connect globally by value; local net labels are sheet-scoped and hierarchical labels connect through sheet pins. [Schematic semantics](https://docs.kicad.org/10.0/en/eeschema/eeschema.html) The compiler's stricter policy is to reject any unresolved implicit connection and never normalize ground names by spelling.

## 5. Project artifact contract

Publish a same-basename project and root schematic, child sheets when needed, and a board once the PCB target exists. Include custom rules and local library tables only when needed. Project settings, schematics and boards must travel together; KiCad's [project file guide](https://docs.kicad.org/10.0/en/kicad/kicad.pdf) identifies those as design-bearing files.

Proposed bundle:

```text
project/Design.kicad_pro
project/Design.kicad_sch
project/sheets/<stable-sheet-id>.kicad_sch      # when hierarchical
project/Design.kicad_pcb                      # PCB targets
project/Design.kicad_dru                      # when custom rules apply
project/project.kicad_sym, project/project.pretty/  # only justified custom assets
input/circuit.json, assets.lock.json, toolchain.lock.json, policy.lock.json
derived/resolved.json, semantic.json, schematic-layout.json, board-layout.json
reports/manifest.json, artifact-map.json, electrical.json, quality.json
reports/raw/, renders/, manufacturing/       # according to target readiness
```

A schematic-only build does not fabricate an empty PCB and claim a complete project. The manifest lists absent targets explicitly. A file tree is assembled in a staging directory, fully checked, then published atomically as a new build. Previous accepted artifacts remain available.

Project generation owns rule severity, net classes, layer mapping and output configuration. Avoid global ERC/DRC exclusions. Approved waivers are separate, specific, evidence-backed records bound to a violation identity and artifact/constraint scope; stale waivers fail matching. Copper connectivity violations cannot be waived into electrical equivalence.

## 6. Headless verification and command contracts

**Facts:** the CLI provides JSON ERC/DRC reports, XML schematic netlists and SVG/PDF outputs. `--exit-code-violations` distinguishes rule violations; PCB DRC supports schematic parity and zone refill/save. [KiCad 10 CLI](https://docs.kicad.org/10.0/en/cli/cli.html)

**Decision:** invoke subprocesses with argument arrays, explicit paths, controlled configuration/locale and bounded watchdogs. Save stdout/stderr, executable hash, arguments and output hashes. Reject missing, empty, malformed or stale reports even when a command exits zero. The following are adapter qualification commands, run on the staged project:

```sh
kicad-cli sch export netlist --format kicadxml -o reports/netlist.xml project/Design.kicad_sch
kicad-cli sch erc --format json --severity-all --exit-code-violations -o reports/erc.json project/Design.kicad_sch
kicad-cli sch export svg -o renders/schematic/ project/Design.kicad_sch
kicad-cli pcb drc --format json --severity-all --schematic-parity --refill-zones --save-board --exit-code-violations -o reports/drc.json project/Design.kicad_pcb
```

Zone refill modifies only the staging board. Hash the resulting board; manufacturing exports must use those exact validated bytes. Any later canonicalization/save requires renewed checks. Inspect report schema and every violation category; do not parse only a textual summary count. A missing tool is `tool_failed`, never a skipped success.

### Electrical observation

Read real KiCad XML exports into a separate `ObservedElectricalGraph`, not back into the proposed IR with repair defaults. Resolve actual references and sheet paths through a bijective ArtifactMap and cross-check observed symbol identities. Unknown/duplicate references or missing units fail. Compare the entire terminal inventory and net partition, not just selected named nets.

For `required` names, enforce the exact planned KiCad scope/name mapping. For `display`/`automatic` names, permit name differences only after a unique full-terminal-partition match. Preserve sheet-instance identity; never strip path prefixes and merge alike names. Do not interpret generated `unconnected-*` names as evidence of intended NC. Read actual NC markers and pin geometry independently and verify that no wire, label or hidden-power rule connects that terminal. Generated virtual power/flag objects are excluded from physical inventory only through a verified typed allowlist, not a broad reference-name filter.

For a placed board, independently read every pad assignment and compare its mapped logical terminal/net. This proves assignments, not completed copper. For a routed board, also require post-fill DRC, no unconnected copper obligations, no shorts, protected-net rules and schematic parity. Internal jumpers and net ties have explicit, localized semantics; they cannot justify globally equating arbitrary grounds.

## 7. DSN/SES bridge and router qualification

The documented KiCad 10 Python bindings expose board-taking overloads of `ExportSpecctraDSN` and `ImportSpecctraSES`. [API reference](https://docs.kicad.org/doxygen-python-10.0/namespacepcbnew.html)

**Decision:** run a tiny subprocess under the matching KiCad system Python: load the staged board and project settings, export DSN, later reload the identical source board, import SES, and save a candidate. No `pcbnew` objects escape this process. Verify successful calls, file existence and content; test in an environment without a display or GUI session. Confirm exported net-class values by reading DSN rather than assuming project settings loaded.

Qualify Freerouting 2.4.1 using its [release](https://github.com/freerouting/freerouting/releases/tag/v2.4.1), [versioned CLI](https://raw.githubusercontent.com/freerouting/freerouting/v2.4.1/docs/command_line_arguments.md) and [settings](https://raw.githubusercontent.com/freerouting/freerouting/v2.4.1/docs/settings.md). A proposed starting invocation is `java -jar freerouting.jar --gui.enabled=false -de placed.dsn -do routed.ses -mp 100 -mt 1`. Qualify the exact effective settings, JRE and deterministic seed mechanism against that version's implementation; the CLI document does not establish that a seed flag guarantees reproducibility. Historical maintainer discussion records a seed-parameter defect in 2.1. [Maintainer report](https://github.com/freerouting/freerouting/discussions/583)

The complete request/projection/diff contract is in [PCB placement](PCB_PLACEMENT_SPEC.md). Test width/clearance/via/layer rules, obstacles, fixed copper and every supported pad shape. Reject unsupported mandatory rules before routing. Diff footprints, poses, net/pad assignments, outline, rules and protected copper after import. Then use KiCad fill/DRC and the independent checks. Neither DSN export success nor an SES file certifies preserved engineering intent.

This bridge has a planned replacement boundary: qualify stable headless IPC when it provides the required operations, or a narrow maintained KiCad bridge. SWIG deprecation is not a reason to introduce GUI automation or pretend an undocumented CLI exists. If no deterministic supported router path qualifies, keep placement deliverables and block automatic manufacturing until this boundary is resolved.

## 8. Renders and manufacturing outputs

**Facts:** CLI exports include Gerbers, drill files, BOM and component positions; PCB SVG/PDF and 3D render/STEP outputs are available. [CLI export catalog](https://docs.kicad.org/10.0/en/cli/cli.html)

**Decision:** generate review SVGs per schematic sheet and per selected board layer, plus PDFs for page-scale review. Pin font/theme/background/page settings. A separate overlay shows semantic groups, violations and constraint witnesses; keep a clean render for blind review. Optional 3D images need locked models and rendering environment and cannot replace footprint/copper checks.

Manufacturing generation takes an electrically and physically qualified candidate and an explicit variant/process profile. Export into staging; set `release_ready` only after export validation and required review succeed. Export the complete chosen copper/mask/silk/paste/outline layer set, plated and nonplated drills as appropriate, BOM with approved manufacturer/MPN/value/footprint/quantity/refdes, and assembly positions. Use one declared origin and one documented top/bottom rotation convention throughout. Cross-check native BOM export against IR population and native position export against actual board poses; retain original exports and any assembler-specific transformation with its parameters.

Parse generated files with independent format readers: verify units, outline/extent, layer polarity/order, drill counts and locations, component counts, DNP handling and coordinate transforms. Check at least one asymmetrical bottom-side component and one through-hole/slot case before qualifying those features. Inspect a CAM render of exported layers rather than only a PCB editor screenshot. Hash outputs and bind them to the validated board and profiles. A fresh validation run is required if any output-affecting input changes.

Do not include temporary local settings, caches or lock files as design inputs. Package a manifest explaining every manufacturing file, units, origin, variant, fabrication profile and any remaining engineering limitations. Missing MPNs, unresolved mandatory SI/thermal constraints, incomplete routing or unverified CAM transformations block release.

## 9. Deterministic qualification suite

Use a controlled config directory, explicit library paths, fixed locale/timezone, locked fonts and no network access during execution. Runtime configuration must not read personal KiCad settings. Capture command help and report-schema probes for the pinned binary. Compare clean reruns in different work directories, including non-ASCII and space-containing paths.

Require byte-identical core documents and normalized geometry/reports; define an exact allowlist for tool-added timestamps, source absolute paths and similar nonsemantic report metadata. Preserve raw files too. Do not normalize away geometry, net names, ordering with semantic meaning or violations. Refilling zones and manufacturing export must pass the same repeatability contract.

Fixtures cover single/multi-unit symbols, inherited symbols, mirrors/rotations, NCs, hidden power, names containing special characters, hierarchy/repeated instances, labels/buses, duplicate pad numbers, net ties, bottom layers, zones, holes and routing sessions. Deliberately broken variants must fail. M1 implements only the first supported subset and rejects the rest explicitly; [milestones](IMPLEMENTATION_PLAN.md) expand the capability matrix without weakening gates.

## 10. Lock and report schemas for M1

These are proposed wire contracts, with `additionalProperties: false` and required fields unless marked optional. Asset and policy file references are paths relative to the lock file's parent; reject traversal outside the explicitly supplied bundle. Executable paths are absolute paths inside the qualified execution image. SHA256 values are lowercase 64-character hex strings. Locks are created in an explicit preparation step and validated before compilation; the build never updates them.

| File | Required structure |
|---|---|
| `assets.lock.json` | `{schema_version: "1.0", assets: AssetLock[]}`; each `AssetLock` has `id, kind, library_id, path, file_sha256, dependencies, source, license, resolved_digest`. `dependencies` is an array of `{path, sha256}`; `source` is `{uri, revision}`. IDs match IR requests or named policy assets. |
| `toolchain.lock.json` | `{schema_version: "1.0", platform, image_digest, executables, python_lock_sha256, configuration_digest, fonts_digest, environment, capabilities}`. Executable entries are `{id, path, version, file_sha256}`; environment is `{locale, timezone}`; capabilities is an ordered list of tested capability IDs. |
| `policy.lock.json` | `{schema_version: "1.0", profiles: [{id, revision, path, sha256}]}`; entries include the referenced drafting, search, stackup and process profiles as applicable. The target must reject an unresolved profile. |
| `manifest.json` | `{schema_version: "1.0", build_key, design_digest, target, lock_digests, stages, checks, artifacts, readiness}`. Stage entries carry the architecture's `StageResult` fields. Check entries are `{id, status, artifact_digests, evidence, diagnostics}`. Artifacts are `{path, media_type, sha256, producer_stage}`. |

`readiness` has explicit booleans `schematic_compiled`, `schematic_reviewed`, `placement_verified`, `routing_verified`, `manufacturing_verified`, `release_ready`, with evidence references for each true value. False means not established; consult check states to distinguish failure from unevaluated work. Set `release_ready` only after all release-obligation checks and required reviews pass. Runtime duration and wall-clock execution records belong to raw audit metadata outside canonical report comparisons.

`drafting.v1`'s M1 profile contains `grid_nm=1270000`, `text_height_nm=1270000`, `wire_gap_nm=1270000`, `symbol_gap_nm=2540000`, `block_gap_nm=5080000`, `margins_nm={left:20320000,top:25400000,right:20320000,bottom:25400000}`, `seed=0`, and named `power_assets` for reference/positive/negative/flag. Bind these to locked standard `power:GND`, `power:VCC`, `power:VEE` and `power:PWR_FLAG` definitions; customize displayed net values only under the qualified power-symbol rule. Policy-inserted objects receive their own ArtifactMap entries. A flag for a return requires evidence that the external supply actually includes that return terminal; net spelling alone is insufficient.

M2 extends the profile with the bounded-search fields in the schematic specification, versioning the profile digest. A profile file is data under a known schema, not executable hooks. Initial M1 graphs and layouts are persisted as canonical typed JSON. Layout objects have `id` and `origin_ids`; geometric fields use exact integers. Symbol uses reference `(component, asset, unit, body_style)`, wires reference a net ID and ordered endpoints, labels reference a net ID and scope, and text carries an occupied envelope. Logical terminal/net graphs have identity and membership without presentation coordinates. Object collections sort by ID; deliberate path/vertex orders remain ordered. Detailed public editing APIs are unnecessary for this first compiler slice.
