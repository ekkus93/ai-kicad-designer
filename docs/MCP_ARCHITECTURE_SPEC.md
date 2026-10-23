# AI KiCad Designer — MCP-Controlled Autonomous Hardware Design Architecture

**Status:** PROPOSED / NOT IMPLEMENTED  
**Draft date:** 2026-10-21  
**Repository:** [`ekkus93/ai-kicad-designer`](https://github.com/ekkus93/ai-kicad-designer)  
**Intended development location:** a single dedicated architectural-pivot branch created by the project owner; **do not change `master` merely by adopting this proposal**.  
**Companion execution plan:** [`MCP_ARCHITECTURE_TODO.md`](MCP_ARCHITECTURE_TODO.md)  
**Research input:** `KiCad_MCP_Capability_and_Gap_Analysis_2026-10-21.md` (research report; not currently a tracked repository dependency).  
**Observed baseline:** `master` commit [`274bc25f25a20734d97bec22bc57cae5adec11cc`](https://github.com/ekkus93/ai-kicad-designer/commit/274bc25f25a20734d97bec22bc57cae5adec11cc), checked 2026-10-21. Reinspect exact Git state before implementation.

> **Primary objective:** Turn an electronic product specification into an independently verified, native KiCad schematic and PCB, then generate a reviewable fabrication/assembly package (Gerbers, drills, BOM, and placement data as applicable), with reproducible provenance and human approval before ordering or irreversible external actions.

## 1. Decision and executive summary

This specification proposes an **architectural pivot within the existing repository**, not a replacement of its source or a declaration that M2h2 is complete. The primary product is an **autonomous hardware design system**. The schematic compiler is one possible implementation of part of that product, not its governing architecture.

**Proposed initial decisions (ratify through measured spikes, not dogma):**

1. Keep `ai-kicad-designer` as the product repository. Develop the pivot on one isolated long-lived branch; reconcile deliberately with `master` when qualification criteria are met. Do not create a PR/branch for each subtask.
2. Provide **one logical KiCad MCP server** containing modular tools, plus a separate design-workflow controller / LLM host. The controller can expose a small subset of tools per phase/task while retaining the server's complete inventory. A separate proxy is optional if a client cannot gate tools; it is not a required second design MCP.
3. Use **one context-isolated engineering loop** initially; do not require multi-agent orchestration. LLM/model/provider is replaceable. The controller, validators, and artifact contracts own truth—not the model's verbal claims.
4. Prefer stable, supported native KiCad interfaces and `kicad-cli`; evaluate existing MCP backends (especially upstream Konnect), direct scripted KiCad edits, and existing `ai_kicad` implementations before deciding to adopt third-party code.
5. Keep KiCad 10.0.6 as the reproducible legacy M2h2 validation baseline. Prototype KiCad 11 development schematic/headless IPC **separately**, feature-detected and never silently substituted into qualification evidence.
6. **No KiCad fork for the first proof of concept.** Fork only when a documented, essential operation cannot be implemented safely through public APIs, CLI, file-level manipulation, or an independent native extension. Prefer upstreaming focused API changes.
7. Reach the first end-to-end PCB package using a **fixed, known-good circuit** before attempting unconstrained natural-language circuit synthesis. Do not confuse an exportable PCB with an electrically valid design or fabrication approval.
8. Preserve M2h2 evidence and frozen evaluation contracts. Treat existing visual-layout acceptance as an **open independent research track**; it does not block the new manufacturing proof of concept. Never mislabel its historical `PASS` artifacts as current-source acceptance.

## 2. Motivation and evidence boundary

### 2.1 Current state (not pivot acceptance)

At observed `master` `274bc25f`, the project is a Python 3.12 (`pyproject.toml`: `ai-kicad`, `pydantic`, pytest and Ruff) native schematic-generation and validation codebase. The CLI entry in `src/ai_kicad/__main__.py` builds a constrained schematic through an IR, locked symbol assets, KiCad CLI, and independent electrical comparison. Related modules include `ir.py`, `schematic.py`, `m2_semantics.py`, `m2_fragments.py`, `m2_pack.py`, `m2_route.py`, `m2_geometry.py`, `m2_compose.py`, `m2a.py`, `m2b.py`, `m2b_build.py`, `verify.py`, and `kicad.py`; verify their current shape before extracting interfaces.

The 2026-10-18 M2h2 note records qualification of behavior source `ee4c37a...`: 56/56 base cases ×5 (with historical V3-8 negative), 72/72 interactions ×5, and 9/9 structural classes ×5. A normalized inventory covered 137 cases/685 SVGs. **An independent 90-case human-composition comparison failed six frozen criteria** (hard defects, per-case regression, fragmentation, aesthetics, repeated structure, I4 improvement). Later fast validation at exact `master` passed, but most specialized jobs on that head were skipped. **Therefore neither the old acceptance nor a new complete current-source qualification is claimed.** See:

- [`docs/M2H2_HUMAN_READABLE_SCHEMATIC_COMPOSITION_TODO_2026-10-07.md`](M2H2_HUMAN_READABLE_SCHEMATIC_COMPOSITION_TODO_2026-10-07.md)
- [`docs/M2H2_FINALIZATION_TODO_2026-09-27.md`](M2H2_FINALIZATION_TODO_2026-09-27.md)
- [`docs/M2_GENERALIZATION_REMEDIATION_SPEC.md`](M2_GENERALIZATION_REMEDIATION_SPEC.md)
- [`fixtures/m2h2/STATUS.md`](../fixtures/m2h2/STATUS.md)

**Preservation rule:** Do not edit, move, prune, rebaseline, reclassify, or overwrite frozen historical fixtures and evidence during the pivot. Existing files under `fixtures/`, frozen DP1–DP4, blind baselines, and qualification-root identities remain intact. Historical protection/audit hashes must be checked before risky refactoring. Respect existing exclusions such as `.local/` and `research/legacy_openclaw/`.

### 2.2 External automation landscape (2026-10-21 snapshot)

| Candidate | Documented characteristics | Unresolved risk |
|---|---|---|
| [Upstream Konnect](https://github.com/mixelpixx/Konnect) | Rust MCP; ~228 domain tools, ~21 on-demand toolsets plus 7 management tools; KiCad 10 PCB IPC, schematic S-expressions, CLI, DSN/SES + Freerouting, manufacturing exports. | Beta; extensive surface is not evidence of end-to-end success. Whole-board autoplace apply is deprecated/diagnostic-only. GPL/AGPL/commercial licensing evaluation required. |
| [ProductOfAmerica/mcp-server-kicad](https://github.com/ProductOfAmerica/mcp-server-kicad) | Python, file-editing + KiCad CLI/`pcbnew`, ~109 advertised tools across project/schematic/PCB/library functionality. | Maintainer says maintenance mode; self-reported MCP vs direct-file agent benchmark favors direct-file edits on simple tasks. |
| [Seeed-Studio/kicad-mcp-server](https://github.com/Seeed-Studio/kicad-mcp-server) | Python, design/net/pin analysis, ERC/DRC, basic editing/export, component/firmware-related helpers. | Schematic editing documented experimental; wiring and complete manufacturing workflow need validation. |
| Direct local KiCad automation | Existing repo compiler, CLI, native IPC, structured files and separate routing engine. | Must enforce serializability, revision-bound writes, strict validators, and honest unsupported reports. |

These are **reported/documented** capabilities, not independently executed acceptance results. Tool count is not a selection criterion. Baseline against the same tasks, model, tool budget, failure injection, and objective verification. Keep legal review for licensing before copying third-party code, especially into redistributed/network-exposed systems.

### 2.3 KiCad API version policy

- KiCad 9/10 official IPC works with a running PCB editor; no stable native schematic IPC or headless IPC there. Use `kicad-cli` for ERC/DRC, export and inspection, and preserve a file-based schematic backend if verified safe.
- KiCad 11 development introduces schematic-editor IPC and headless API and export support. This is **experimental** in 2026; version-probe every capability and expect changes. Keep development binary, Python bindings, libraries, and evidence fully isolated from pinned KiCad 10.0.6.
- Legacy `pcbnew` Python/SWIG bindings are deprecated; do not choose them as the sole long-term integration contract.
- **Feature detection over version guessing**: declare precise command/API capability and preconditions, or `unsupported`; never silently run a different backend with weaker guarantees.

Official references: [KiCad IPC API](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/), [add-on developer version limits](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/), [developer IPC internals](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-kicad-developers/).

## 3. Scope and non-goals

### 3.1 Product scope

- User-authored functional requirements and structured constraints; start from a fixed vetted topology, then add component selection and novel circuit synthesis in later milestones.
- Native `.kicad_pro`, `.kicad_sch`, `.kicad_pcb`, compatible libraries and lock manifests.
- Connection-preserving schematic creation/editing, exact terminal/net mapping, ERC and independent checks.
- Footprint selection and validation; copper stackup, outline, placement, routing, zones, and DRC.
- Gerber RS-274X + Excellon drills (or another explicitly supported fab format), manufacturing drawing/notes, fabrication manifest; optionally BOM and pick-and-place/centroid for PCBA.
- Recoverable, evidence-gated LLM iteration, reproducible builds and artifact attribution.
- Optional user inspection in KiCad; command-line/headless automation where technically possible.

### 3.2 Explicit non-goals for initial vertical slice

- Arbitrary reliable topology invention, complex high-speed RF/multilayer/HDI/BGA design, regulated safety systems, automatic component procurement, fabrication ordering, and physically verified functionality.
- Achieving all frozen M2h2 aesthetic comparison thresholds before shipping the proof of concept.
- Training/fine-tuning an LLM, implementing a new EDA kernel, writing a general KiCad fork, or supporting every third-party MCP tool.
- Assuming ERC, DRC, SPICE, or a provider's DFM check individually proves circuit correctness, manufacturability, or reliability.
- Rewriting historical fixture sets or changing `master` outside an explicit integration decision.

## 4. End-to-end architecture

```text
User / CLI / future TUI
       |
       v
Engineering workflow controller / LLM host
  - design revision & step state, phase transition, tool selection
  - model/provider adapter, context isolation, durable task journal
  - approvals, budgets, prompt/tool output normalization
       |            \
       | small       \ read-only docs / datasheets / parts / simulation
       v              v
One logical AI KiCad MCP server (modular tool registry)
  - project, components, schematic, PCB, route, verify, export
  - dispatch-time authorization; typed contracts and provenance
       |
       v
Backend adapter boundary (not tied to MCP protocol internally)
  +-- existing ai_kicad schematic compiler & electrical observer
  +-- selected third-party MCP/adapter, e.g. Konnect (if qualified)
  +-- official KiCad IPC (PCB 10; experimental schematic/headless 11)
  +-- KiCad CLI + independently validated structured file operations
  +-- router / placement / simulator adapters (explicit capabilities)
       |
       v
Native project revisions + deterministic verification & evidence ledger
       |
       v
Reviewable fabrication package -> optional human-authorized order
```

**Logical server vs process topology:** v0 has one outward-facing design MCP tool namespace. An external Konnect process, CLI runner, or router may be a backend *service*; that does **not** obligate separate MCP servers or multiple tools exposed to the LLM. If independent subprocess isolation is warranted, use it internally. Avoid double-implementing the same KiCad operation unless an A/B backend comparison is intentional.

### 4.1 Source boundaries and example package layout (proposed, not immediate migration)

```text
src/ai_kicad/                       # existing code stays working
src/ai_kicad/pivot/
    model/                          # canonical design graph, constraints, revisions
    orchestrator/                   # phase machine, tool policy, context budgets
    mcp/                            # one logical MCP server + tool registry
    adapters/                       # existing compiler, IPC, CLI, Konnect, router
    verification/                   # graph equivalence, electrical, ERC/DRC, DFM
    manufacturing/                  # render/export/package and manifest
    evidence/                       # revision provenance, structured run records
    benchmarks/                     # controlled backend/model comparisons
tests/pivot/                         # focused tests and integration tests
fixtures/pivot/                      # non-overwriting design corpora/evidence
```

The package layout is optional. Prioritize clean dependency direction and preserved imports over mass module movement. MCP tools invoke internal Python/domain interfaces, which must also work **without running MCP**.

## 5. Canonical engineering design model

### 5.1 Source of truth

The canonical model is a **typed, versioned engineering design graph**, independent of schematic coordinates and PCB geometry. A document hash alone is not the connectivity model. Suggested version `design-model.v1`:

- `design_id`, `revision_id`, `parent_revision`, schema and provenance; immutable revision content hash.
- Project requirements: function, input/output domains, environmental assumptions, limits, design profile and human-approved waivers.
- `components`: stable instance ID; reference designator; approved symbol/library checksum; manufacturer part number and optional supplier ID; pin/pin-type map; footprint/pad map; power, tolerance, temperature, and substitution constraints.
- `nets`: stable net ID; electrical role; exact symbol-instance + unit + pin identities; reference/ground semantics; allowed connectivity; constraints (length, impedance, width, clearances, current, differential relationships where supported).
- `interfaces`: connector pinout, ESD/reverse-polarity, test access, power domains.
- `electrical_assertions`: expected rails, currents, thermal loss, frequency/time, drive capability, decoupling, forbidden shorts/opens, derating, simulation requirements.
- `pcb_constraints`: board outline/holes, layer stackup, fab capability profile, placement groups, keepouts, zones, escape/clearance rules, mechanical envelope.
- `artifacts`: schematic/board/exports, hashes, generator versions, validations, waivers, external datasheet/document references.

**Important:** No irreversible serialization of the canonical graph is trusted without independent reconstruction from the emitted KiCad native project. The model must preserve stable identity across reference renumbering, sheet hierarchy, multiple units and footprints.

### 5.2 Graph equivalence and safety invariants

- Map every required logical `(component instance, sheet path, unit, pin)` to exactly one expected electrical net and, after PCB sync, to a footprint and physical pad; handle intentionally unconnected pins explicitly.
- Verify no unexpected shorts, missing required connections, swapped pads, duplicate/missing instances, unassigned essential footprints, or hidden hierarchy ambiguity.
- Reconstruct electrical connectivity **from emitted KiCad artifacts** using an independent observer. The emitter's own success response is not authoritative.
- Preserve allowed known exceptions as narrow, evidence-backed design waivers, never a blanket "ERC OK" / "DRC OK" suppression.
- Record netlist/PCB equivalence before and after schematic changes, PCB synchronization, routing imports, and final exports.
- If KiCad native S-expression, file/API model, or observer cannot safely represent a construct, stop with a typed capability error; do not emit an approximate design labeled valid.

### 5.3 Design state and artifact provenance

Each design revision records: base SHA + toolchain/capability manifest; requirements hash; symbol/footprint/library file hashes; normalized schematic and PCB hashes; resolved component map; tool calls and validation inputs/results; DRC/ERC waivers; generated file hashes and timestamps. All write tools require `design_id` and expected `revision_id`, commit a new revision atomically, and return the exact resulting revision. No in-place destructive mutation of the only valid copy. Backend-specific live-editor operations must be reconciled to saved verified project state before commits.

## 6. LLM orchestration and dynamic tool gating

### 6.1 Single loop and context discipline

Initial system: **one engineering LLM loop** with context isolated at major phase transitions; no required multi-agent supervisors. Persist a compact, structured handoff: task, design revision, proven checks, unresolved failures, next action, source references. Models may be hosted or local. Tools should be discoverable, but the model should see only an approved active subset. Default visibility target: **roughly 5–15 tools** (benchmark the number, do not hard-code it as universal).

### 6.2 Phase machine

| Phase | Example visible tool bundle | Required evidence before forward transition |
|---|---|---|
| `REQUIREMENTS` | requirements, constraints, reference/docs search, state | requirements explicit; unresolved uncertainties listed |
| `CIRCUIT_DESIGN` | part/circuit model, calculations, simulation request, state | topology pinned and essential electrical assertions documented |
| `SCHEMATIC` | create/inspect/modify symbols/nets, run ERC, observe connectivity | serialized schematic equivalence and ERC; electrical assertions scoped |
| `FOOTPRINTS` | resolve/inspect part packages and pads, sync PCB | exact symbol-pin ↔ footprint-pad mapping; full mapping coverage |
| `PCB_PLACEMENT` | board profile, groups, placements, scoring, inspect | outline and placement legal under selected fab profile |
| `PCB_ROUTING` | routes, vias, zones, router plan/apply, DRC | all required nets connected, no unauthorized shorts, DRC pass |
| `MANUFACTURING_REVIEW` | fabrication audit, export, layers, BOM/PnP, compare artifacts | complete immutable package + review evidence; no ordering authority |
| `REVIEW_READY` | readonly inspect/report, request approval, optional rework | human review and explicit decision for any external action |

**Bidirectional remediation:** failed gate reopens the earliest relevant phase, creates an isolated candidate revision, and invalidates dependent results; it must not silently mark downstream tests as current after a design change. Research/datasheet/state/rollback tools remain accessible in all phases. One controller tool `request_phase_transition` proposes a transition, but only the deterministic controller grants it.

### 6.3 Tool visibility vs enforcement

- **Visibility:** orchestrator filters `tools/list` schemas before model calls; optional backend `load_toolset`/`unload_toolset` may reduce total cost, but backend availability does not grant execution rights.
- **Authorization:** MCP dispatch checks phase, role, design revision, write target, risk class, user consent and budget. A manually forged `tools/call` to a hidden tool must be rejected.
- **Concurrency:** one writer lease per design revision; concurrent independent read/validate operations allowed. `expected_revision` CAS on writes; no implicit retries for ambiguous writes.
- **Recovery:** only the controller can promote an accepted candidate to `current`; revert/read-only restore is version-bound and auditable.
- **No completion by narrative:** tool replies must contain structured test evidence; model assertions cannot override gates.

### 6.4 Model evaluation profiles

Measure at least: full inventory, phase-gated, task-gated, and direct code/file automation baselines using identical task, model, sampling settings, time/token limits, fixture versions, and independent judges. Track tool-call validity, semantic completion, cost/latency, provenance completeness, repairs and regressions. A tool-gated MCP must demonstrably improve success/cost or safety to be retained.

## 7. MCP tool contracts (proposed v0)

The names below are **design targets**, not claims that existing MCPs implement them. Avoid having all tools visible simultaneously. Group tools into on-demand bundles, with bulk operations preferred over hundreds of low-level coordinate calls. All mutations return a new `revision_id` and structured verification status; readonly calls must identify the revision inspected.

| Group | Representative tool names | Key semantics |
|---|---|---|
| Always-on | `get_design_state`, `get_capabilities`, `get_validation_report`, `create_checkpoint`, `rollback_to_checkpoint`, `request_phase_transition` | bounded readonly state, capability negotiation, safe revision moves |
| Requirements | `define_requirements`, `set_constraint`, `explain_assumptions` | typed requirement schema, source/assumption provenance |
| Circuit | `list_approved_components`, `inspect_part`, `edit_circuit_graph`, `check_design_calculations`, `run_spice` (later) | no undocumented pin/part substitution; require data and limits |
| Schematic | `create_schematic`, `apply_schematic_transaction`, `inspect_schematic`, `export_netlist`, `run_erc`, `verify_schematic_equivalence` | stable IDs, transactional pin-/net-level edits, independent parse |
| Footprints/PCB | `assign_footprints`, `verify_pin_pad_map`, `sync_pcb`, `set_board_profile`, `apply_placements`, `score_placements`, `inspect_board` | exact mapping and outline/keepout enforcement |
| Routing | `route_nets`, `apply_route_candidate`, `refill_zones`, `inspect_unrouted_nets`, `run_drc`, `verify_board_connectivity` | revision-bound router imports; no unverified automatic acceptance |
| Manufacturing | `prepare_fabrication_package`, `verify_gerber_drill_package`, `prepare_assembly_package`, `inspect_fabrication_manifest` | provider profile and hashes; all outputs review-only |

### 7.1 Request/response envelopes

Illustrative, subject to schema validation and versioning:

```json
{
  "tool": "apply_schematic_transaction",
  "schema_version": "tool.v1",
  "design_id": "d-001",
  "expected_revision": "rev-0007",
  "changes": [{"type": "connect_pins", "from": "U1.3", "to": "R1.1", "net_id": "n-out"}],
  "dry_run": true,
  "idempotency_key": "d-001-connect-u1r1-v1"
}
```

```json
{
  "status": "plan_valid",
  "applied": false,
  "base_revision": "rev-0007",
  "result_revision": null,
  "violations": [],
  "evidence_id": "e-0042",
  "capability": "schematic.batch_edit.v1"
}
```

Required error vocabulary: `UNSUPPORTED_CAPABILITY`, `INVALID_INPUT`, `AMBIGUOUS_IDENTITY`, `STALE_REVISION`, `CONCURRENT_EDIT`, `NOT_AUTHORIZED_IN_PHASE`, `INSUFFICIENT_EVIDENCE`, `VIOLATES_HARD_CONSTRAINT`, `BACKEND_UNAVAILABLE`, `TOOLCHAIN_MISMATCH`, `TRANSIENT_FAILURE`, `AMBIGUOUS_WRITE`, `BUDGET_EXCEEDED`. Include scope, safe diagnostic details, whether any mutation occurred, affected revision, recommended recovery, and redacted logs. Never report `success` on partially applied changes.

### 7.2 Backend adapter interface and selection

Define an internal typed `DesignBackend` capability manifest, with operations such as `create_project`, `read_schematic`, `apply_schematic_transaction`, `export_schematic_netlist`, `run_erc`, `sync_pcb`, `apply_placement_transaction`, `route_board_candidate`, `run_drc`, `export_fabrication`, `export_assembly`. Each advertises support level (`verified`, `experimental`, `unsupported`), API version, KiCad compatibility, preconditions (GUI/editor/headless), and ability to rollback. For each operation the controller selects a **pinned approved implementation**; any fallback is explicit in evidence and must satisfy the same postconditions. Do not make source-code licensing assumptions about transitive integration; an external MCP process is preferable initially for evaluation.

## 8. Engineering verification and gates

### 8.1 Verification layers

1. **Schema and provenance:** valid typed design, complete part/library identity, reproducible profile lock.
2. **Circuit design checks:** explicit supply range/ratings, current/thermal budgets, component derating, required pull-ups/decoupling/protection and relevant datasheet references; simulation when needed. Classify unsupported engineering domains as not verified.
3. **Schematic:** native parse round-trip, independent pin-net reconstruction, no unexpected ERC findings, intentional NC documented.
4. **Footprint mapping:** datasheet package, symbol pin ↔ pad numbering, footprint dimensions/orientation, mount technology, physical pin-one and polarity.
5. **PCB:** legal board outline/holes and stackup, pad/traces/via clearance, complete required connectivity, zone fills, passing native DRC with reviewed narrow waivers; check copper-to-net connectivity independently where feasible.
6. **DFM and export:** Gerbers cover required layers, drill tooling, slots and plated/unplated holes, silkscreen/mask/paste polarity, origin/orientation, outline, stackup/fab profile, and consistent revision manifest. Rendering a Gerber is not proof of fab acceptance.
7. **Assembly (optional initially):** complete BOM with MPNs, alternates/stock evidence, refdes count, position/side/rotation, placement/centroid, paste layers, assembly drawing as appropriate; provider-specific conventions verified.
8. **Human/physical:** human review before manufacturing order; actual physical success only after receiving, assembling and electrically testing the board.

### 8.2 Pass/fail taxonomy

`NOT_RUN`, `RUNNING`, `PASS`, `FAIL`, `BLOCKED`, `UNSUPPORTED`, `WAIVED_WITH_APPROVAL`, `INCONCLUSIVE`. `PASS` is valid only with source-specific verified evidence. `UNSUPPORTED`, `BLOCKED`, skipped jobs or old-source evidence are never silently `PASS`. Warnings require explicit severity and policy disposition. Every gate records exact design revision, toolchain, check configuration and artifacts.

**Release status:** `DRAFT` → `SCHEMATIC_VALIDATED` → `PCB_VALIDATED` → `PACKAGE_READY_FOR_REVIEW` → `HUMAN_APPROVED_FOR_ORDER` → `ORDERED` → `PHYSICALLY_TESTED`. The system must **not** automatically advance beyond `PACKAGE_READY_FOR_REVIEW` on its own.

### 8.3 Safety-critical and high-risk exclusions

V0 targets benign, low-voltage, low-energy demonstration circuits. High-voltage mains, lithium charging/protection, medical/life-safety, hazardous actuation, mains isolation, automotive safety, RF certification and similar domains require separate domain-specific expert gates and are out of autonomous-manufacturing scope. The controller must refuse a false implication of validation from ERC/DRC alone.

## 9. Routing, placement and native KiCad integration

### 9.1 Placement/routing ownership

- Treat automatic placement and autorouting as **candidate generators**. Score and validate all candidates independently; failures do not corrupt the last known-good board.
- Routes must be tied to a board revision and net mapping; DSN/SES or another router's output is inspected before atomic import. Incomplete routes remain `FAIL` or `BLOCKED`, never ``autoroute complete``.
- Expose coarse-grained domain operations, but retain read-only low-level inspection and bounded explicit edits for repair.
- Record failed candidates and diagnostic witnesses; route/placement quality optimization must not weaken hard clearance/connectivity/fab constraints.
- Demonstrate PCB routing on one simple 2-layer board before adding unconstrained topology or broad placement optimization.

### 9.2 Escalation ladder before forking KiCad

1. Existing verified MCP tool/adapter (Konnect/other) or current compiler.
2. Supported `kicad-cli`, KiCad GUI IPC, official add-on Python API.
3. Validated structured native-file modifications in isolated revisions (not ad hoc regex patching).
4. Small external native plugin/extension using public IPC.
5. Pinpoint, upstreamable KiCad C++ IPC patch, maintained as a minimal separate patch set or fork **only after an approved capability-gap RFC**.

A fork RFC must include: exact missing operation, reproducible failure or API limitation, external workarounds attempted, risk of data corruption, minimal API/protobuf diff, version compatibility, licensing, security, maintainability, upstream issue/PR, and test plan. A fork is not authorized merely because direct C++ access seems cleaner.

## 10. Manufacturing package profile

### 10.1 Initial target

Initial board: simple, known-good, low-voltage, two-layer **555 timer LED flasher** or equivalent vetted design, with verified electrical values and footprints. No unsupported battery charger, USB-PD, RF or complex power system. Specify a fixed board size class and mechanical clearance rather than prematurely optimizing area. A commercial manufacturer such as PCBWay is a **fabrication profile**, not an automatic ordering endpoint.

### 10.2 Required package files (fab-only)

- Native editable `.kicad_pro`, `.kicad_sch`, `.kicad_pcb` and required custom symbols/footprints or lock manifests.
- Gerbers: each used copper layer, soldermask, silkscreen, board outline, and any required fab drawing/other layers with correct coordinate settings and polarity.
- Correct plated/nonplated drill files, drill map/report, slots as necessary, and outline/holes match board model.
- `fabrication_manifest.json`: design revision and hashes, dimensions, layer count, thickness/finish/clearance/trace/drill capability assumptions, requested process options, exact output inventory, checks, warnings/waivers.
- `verification_report.json`: ERC, DRC, net equivalence, footprint/pad mapping, fab-file inspection, and unverified engineering assertions; do not claim verified values for unsupported checks.
- Preview images and human inspection instructions. Exported files should be checked by a **separate Gerber parser/viewer**, not just by the exporter.

### 10.3 Assembly extension (later acceptance gate)

BOM with quantity/refdes/MPN/footprint/tolerance/substitutions, approved sourcing notes; centroid/pick-and-place with correct side/rotation/origin/refdes mapping; required paste layers, assembly drawing and exceptions for hand-assembled/thru-hole parts. For KiCad SMT export, derive placements from the native board's position export and bind each placement to the BOM and native footprint before packaging. Normalize KiCad's side and signed-angle conventions explicitly; verify the assembler's origin and rotation convention against a known board. Generate paste and assembly drawing artifacts from that same board and include source/output hashes. An exporter mechanics smoke is not proof of BOM correctness, assembler acceptance, or PCBA readiness. Do not label a fab-only output “PCBA-ready.” [PCBWay assembly FAQ](https://www.pcbway.com/assembly-faq.html), [assembly file requirements](https://m.pcbway.com/assembly-file-requirements.html).

### 10.4 Explicit separation of outcomes

`FILES_EXPORTED` ≠ `NATIVE_VERIFIED` ≠ `FAB_PROFILE_CHECKED` ≠ `MANUFACTURER_ACCEPTED` ≠ `ELECTRICALLY_WORKING` ≠ `PHYSICALLY_TESTED`. No automatic order placement or cost-incurring external API action without specific user approval.

## 11. Benchmark and verification strategy

### 11.1 Fixed POC board and adversarial fixtures

Use at least one fixed reference circuit with locked known-good schematic, component footprints, expected netlist, and reference BOM (initial 555 flasher). Follow with representative cases from the existing M2h2 corpus that exercise internal references, shared rails, fanout and multistage behavior, **without modifying frozen fixtures**. Add negative controls: wrong pad number, unconnected reset pin, swapped polarized component, unrouted net, unexpected bridge/short, stale board revision, missing drill, wrong layer polarity, stale BOM and unapproved backend fallback.

### 11.2 Backend comparisons

Hold constant model identity, prompt, design, temperature/settings if applicable, tool cap, allowed time, file versions and judge. Compare:

- direct current `ai_kicad` generator plus scripted KiCad backend;
- Konnect adapter with task-gated toolsets;
- ProductOfAmerica / Seeed where their implemented operations can run;
- native IPC/CLI and direct structured KiCad-file agent baseline;
- KiCad 11 experimental IPC spike in separate environment.

Report success **per gate**, tool-call error rate, retries, median/p95 duration, token consumption, native-file corruption, reproducibility (repeat ≥3 for POC), and amount of human editing. Publish machine-readable benchmark with immutable input/output artifacts. A feature not implemented by a candidate is `unsupported`, not a benchmark `failure` when comparing its advertised tool subset—though it remains a product gap.

### 11.3 Test pyramid and CI

- Unit: schema/version migrations, tool registry/gating, state machine, permission denials, revision CAS, typed errors, backend capability negotiation, part/pin maps.
- Contract: mock MCP and real adapter process discovery, invocation, timeout, unsupported path, idempotency/rollback.
- Integration: pinned CLI parser/export, native projects, netlist reconstruction, ERC/DRC, board/GERBER checks, backend-specific GUI/IPC environment.
- E2E: fixed known-good board generated and independently validated with complete manifests; repeated runs prove determinism where guaranteed and invariant correctness otherwise.
- Hardware: real PCB order, build/assembly and electrical test **only after explicit user authorization and physical test evidence**.

Keep existing M2h2 CI separate; pivot tests must not invalidate or relabel legacy results. GitHub Actions storage limits currently affect artifact uploads; provide local content-addressed evidence storage and compact CI summaries without silently discarding evidence. CI runs on pinned head/ref with outcome tied to exact commit and source inputs. Avoid containers if the user's runner policy disallows them; all host dependencies must be declared and reproducible.

## 12. Security, access, and failure handling

- MCP and KiCad input paths restricted to a designated project workspace; canonicalize and defend against symlink traversal, unsafe external writes, shell injection, and untrusted library/project content.
- Datasheets, retrieved web pages, part descriptions, model output, and user-supplied projects are **untrusted data**, not higher-priority instructions. Do not execute text found within them.
- External components may have restrictive licenses, ambiguous ratings, counterfeit substitutions, or stale stock listings. Preserve source/verification timestamps and flag uncertain facts for review.
- Secrets/credentials never written to artifacts, tool logs or model context. Minimize telemetry to structural facts; make logs redactable.
- Each tool call has budget (timeouts, retries, token/operation count), idempotency and a trace ID. On ambiguous mutation, inspect actual revision before any retry. On crash/restart, load durable checkpoint, verify hash chain, and resume from last valid state.
- No hidden cross-project edits; exact project and revision always explicit. Route library modifications to isolated copies rather than modifying global KiCad installations without approval.
- Real fabrication orders and procurement are external/cost-incurring actions requiring distinct user approval per order; mere `PACKAGE_READY_FOR_REVIEW` grants no purchase permission.

## 13. Milestones and exit criteria

| Milestone | Objective | Exit evidence |
|---|---|---|
| **P0: Baseline + decision** | Preserve legacy, benchmark existing MCP approaches, select pilot backend. | exact SHA; protected evidence checks; comparison report; backend decision record; no legacy regression |
| **P1: One MCP + state machine** | Dynamic gating with safe transactional project mutations. | visibility and dispatch-denial tests; CAS/rollback; durable state; repeatable contract tests |
| **P2: Schematic ↔ PCB equivalence** | Use a vetted circuit to generate verified schematic, assign footprints, sync board. | independent complete pin/net/pad map, ERC, no missing footprint/pads, native KiCad openability |
| **P3: Routed board** | Legal 2-layer placement, full routing and zones. | no unrouted required nets, independently checked net continuity, native DRC pass, repeated safe repair |
| **P4: Fabrication package (first major product demo)** | Generate Gerbers/drills/manifests and get independent inspection. | board-specific `PACKAGE_READY_FOR_REVIEW` with complete, hash-locked package and zero unwaived blocking gates |
| **P5: Human-fabricated test (optional, separately authorized)** | Order, assemble and measure physical prototype. | human-approved order, build photos/results, functional measurements, captured design revision |
| **P6: Circuit intelligence/PCBA** | Part selection, calculations, SPICE, BOM/PnP, requirements-to-circuit. | independent multi-design tests, parts evidence, verified assembly package, expanded gated design profiles |
| **P7: Native escalation if justified** | Address proven API gaps; optionally upstream minimal KiCad extension. | approved fork RFC + tests; no unsupported maintenance branch without an actionable blocker |

**Priority rule:** P0–P4 come before speculative generic optimizers or KiCad fork work. P5 requires explicit external authorization. P6/P7 are planned extensions and do not block P4 unless a required correctness gate fails.

### 13.1 Quantifiable P4 acceptance for first board

- All required native project files open/parse in the pinned KiCad runtime.
- Independent schematic graph matches locked reference design; zero unexpected ERC and no unresolved required electrical assertions (for the vetted scope).
- Every specified symbol pin with a physical connection maps to an approved footprint pad and correct PCB net; no unassigned required footprints, missing pads, unintended shorts or open required networks.
- Board outline closed, within declared 2-layer fabrication profile, all footprints within legal mechanical limits; all required tracks/routes/zones complete.
- Latest project revision has zero blocking DRC findings (any approved nonblocking waivers must be explicit), plus independent connectivity comparison.
- Exports include used copper, solder mask, legend, outline, needed fabrication layers, plated/nonplated drill files as applicable; independent Gerber/drill inspection finds no missing necessary geometry.
- Fabrication ZIP, manifest, checksums, pinned backend/tool versions, layer/mapping report and previews reproducibly correspond to **one** design revision.
- Controller state is `PACKAGE_READY_FOR_REVIEW` and **not** `ORDERED` or `PHYSICALLY_TESTED`; user receives a clear limitations list and approval request for any further action.

## 14. Open architectural questions (experiments, not blockers to drafting)

1. Which specific Konnect calls pass our exact data-integrity and rollback tests? Are its beta and licensing conditions acceptable for an independent backend process?
2. Can native KiCad 11 schematic/headless IPC replace the separate file-based schematic adapter for required v0 cases? What is the precise API version/capability profile?
3. What is the minimum trusted independent Gerber/netlist inspection set that does not merely re-run the same exporter logic?
4. Which placement/router implementation completes the fixed test board reliably with safe revision-bound imports?
5. What license/distribution and commercial-use plans should govern third-party source inclusion? (Legal review before distribution; tool protocol alone does not settle licensing.)
6. Should the user interface remain CLI first or include an optional terminal UI later? The CLI/headless test harness is required; no GUI dependency for orchestration.
7. What standard part database, datasheet evidence, and sourcing policies are acceptable for future arbitrary circuit synthesis?
8. How much M2h2 layout optimization remains valuable once the manufacturing pipeline exists? Benchmark actual board outcomes, not aesthetic proxies alone.

## 15. Execution policy, governance, and change control

- This document and the companion TODO govern **the pivot branch only** when adopted; they **do not replace the existing M2h2 governing specification on `master`**. Any permanent policy change is an explicit future integration decision.
- The project owner creates/approves the dedicated branch; pin its actual name and base SHA in the TODO when work starts. This proposal does not create a branch, PR, commit, or scheduled job.
- All GitHub/CI operations performed **from ChatGPT** for this repository must use the user's prescribed **Ralph Bridge** where available, not the default GitHub connector. Local developer/runner workflows may use native Git and `gh` in accordance with local project policy. Do not create per-subtask branches/PRs.
- Preserve old docs and historical fixtures untouched; document any departure as a new acceptance track, not retroactive M2h2 PASS.
- Every TODO acceptance checkbox must be backed by the exact revision, toolchain, test evidence and human-authorized action as applicable. An implementation stub or passing mocked test is not completion of a real KiCad/manufacturing gate.
- Architectural decision records required for backend selection, data model, package format, KiCad 11 adoption, and any native fork.
- Stop a run only for a demonstrated external authorization/hardware/credential blocker, a contradiction requiring user decision, or exhausted safe execution scope; ordinary tests, API failures and pending CI warrant repair or independent progress.

## 16. References

- [Current repository](https://github.com/ekkus93/ai-kicad-designer)
- [KiCad IPC overview](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/)
- [KiCad IPC add-on developer guide: v9/v10/v11 capability boundaries](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/)
- [KiCad IPC developer internals](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-kicad-developers/)
- [Konnect tool directory](https://github.com/mixelpixx/Konnect/blob/main/tool-directory.md)
- [Konnect API migrations](https://github.com/mixelpixx/Konnect/blob/main/docs/API_MIGRATIONS.md)
- [ProductOfAmerica MCP](https://github.com/ProductOfAmerica/mcp-server-kicad)
- [Seeed KiCad MCP](https://github.com/Seeed-Studio/kicad-mcp-server)
- [PCBWay assembly requirements](https://www.pcbway.com/assembly-faq.html)

---

**Acceptance status at draft:** architecture proposed; no new MCP, fabricated PCB, Gerber package, physical test, backend benchmark, or fork is claimed complete by this document.
