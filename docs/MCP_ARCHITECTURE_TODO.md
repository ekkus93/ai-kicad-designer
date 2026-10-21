# AI KiCad Designer — MCP Architecture Pivot TODO

**Status:** NOT STARTED / PLANNED  
**Draft date:** 2026-10-21  
**Governing specification:** [`docs/MCP_ARCHITECTURE_SPEC.md`](MCP_ARCHITECTURE_SPEC.md)  
**Repository baseline when drafted:** `master` `274bc25f25a20734d97bec22bc57cae5adec11cc` (re-read at execution).  
**Pivot branch:** TO BE CREATED BY OWNER; record exact name and start SHA before any changes.  
**Working policy:** one pivot branch; no per-checklist branches/PRs; no mutation of `master` or frozen legacy acceptance evidence without separate explicit approval.

> **Goal of this execution plan:** Deliver one **verified, reviewable fabrication ZIP** for a small reference PCB, using one logical KiCad MCP server, a controller that gates tools by task/design phase, native KiCad artifacts, independent verification, and repeatable tests. First prove an end-to-end board; advanced circuit invention, aesthetic M2h2 closure, and a KiCad fork are later work.

## Ground rules and completion semantics

- [ ] **G-001** On the pivot branch, pin baseline commit, branch name, toolchain versions, chosen reference design, owner decisions and this TODO's exact blob hash; record in a non-historical `fixtures/pivot/` manifest. **Evidence:** exact branch/source SHA, manifest. **Dependencies:** none.
- [ ] **G-002** Verify existing protected M2h2 source/fixtures/frozen-input hashes against baseline; preserve all old checklists, CI data, and historical findings. **Evidence:** immutable inventory and matching hashes. **Dependencies:** G-001.
- [ ] **G-003** Establish one evidence convention for every task: input revision, action/tool/backend build, outputs, tests, pass/fail/unsupported, commit CI links, and blockers. No checkbox from prose or requested-but-unobserved runs. **Evidence:** schema and validating tests. **Dependencies:** G-001.
- [ ] **G-004** Create decision records for baseline and backend choices; document that this TODO governs the pivot only and M2h2 remains **INCOMPLETE**. **Evidence:** ADRs and status page. **Dependencies:** G-001.
- [ ] **G-005** Confirm user's runner policies, project paths and test environment. Prefer `uv` for Python environments, pin KiCad versions, and avoid containers if the runner policy prohibits them. **Evidence:** repeatable bootstrap script and host environment manifest. **Dependencies:** G-001.

**Completion rule:** A box is checked only on implementation + independent evidence for its exact stated scope; mocked outputs, stale evidence and skipped CI cannot satisfy hardware or KiCad-real-tool checks. Default all boxes unchecked. Retain historical FAIL/PASS results without amendment. No unapproved PCB fabrication order.

## P0 — Preservation, comparison and decisive backend experiment

**Purpose:** Avoid rebuilding existing capabilities blindly; make the integration and fork decisions using actual results.

- [ ] **P0-001** Snapshot current package/import/CLI graph (`src/ai_kicad`, `tools`, `tests`, GitHub workflows, locked KiCad 10.0.6) without moving code. **Acceptance:** baseline map identifies reusable IR, schema, compiler, observer, layout, export and test seams; existing import/CLI smoke tests pass unchanged. **Deps:** G-002.
- [ ] **P0-002** Pin published feature/tool inventories and versions for Konnect, ProductOfAmerica and Seeed; distinguish advertised vs implemented vs independently verified; inventory licensing and integration constraints. **Acceptance:** source-linked machine-readable capability matrix; no fabricated support claims. **Deps:** G-004.
- [ ] **P0-003** Build a two-layer known-good **555 LED flasher** reference corpus: exact electrical design, approved symbol/footprint/MPN and voltage ranges, reference netlist, expected behavior, PCB profile, initial BOM, known-good KiCad project and checksums. **Acceptance:** reference inputs independently parse and their schematic ERC/equivalence pass; assumptions documented. **Deps:** P0-001.
- [ ] **P0-004** Create `fixtures/pivot/` immutable fixture versioning and separate experiment output directories; failure outputs retained rather than overwritten. **Acceptance:** tamper/hash tests and no writes to `fixtures/m2h2/` during benchmark. **Deps:** G-002.
- [ ] **P0-005** Implement reusable benchmark runner with common task prompts/specs, model settings, tool/time/token limits, error taxonomy, exact backend version, and independent scoring. **Acceptance:** same fixture and judge applied to every backend; `unsupported` distinguished from incorrect. **Deps:** P0-003, P0-004.
- [ ] **P0-006** Install/run Konnect with pinned KiCad 10 environment in isolation and test project/schematic read-write, native openability, ERC, footprint assignment, board operations, DRC, Gerber/drill export, rollback, and failure diagnostics. **Acceptance:** actual tool call logs and saved artifacts; pass/partial/unsupported per capability, not just tool listing. **Deps:** P0-005.
- [ ] **P0-007** Test ProductOfAmerica against its implemented subset using the same fixture; specifically attempt native save/open, pin wiring, PCB sync, autorouting, validation and export. **Acceptance:** independent before/after files and quantified tool errors. **Deps:** P0-005.
- [ ] **P0-008** Test Seeed against its implemented subset, emphasizing net/pin analysis and experimental schematic edits. **Acceptance:** independently reconstructed connectivity and honest unsupported entries. **Deps:** P0-005.
- [ ] **P0-009** Test a direct automation baseline: existing compiler + `kicad-cli`/structured files/PCB IPC, and LLM coding agent editing native files with post-parse validation. **Acceptance:** identical benchmark metrics and native equivalence gates; do not assume MCP wins. **Deps:** P0-005.
- [ ] **P0-010** Compare model runs with full Konnect tool inventory, toolset loading, phase-gated subset and task-gated subset; measure success, correctness, tokens, latency and invalid calls. **Acceptance:** ≥3 trial repetitions per feasible configuration, budget matched and regression tests for hidden-tool rejection. **Deps:** P0-006.
- [ ] **P0-011** In a distinct, nonproduction KiCad 11 development environment, probe schematic/headless IPC commands, version compatibility, batch-write/undo/readback semantics and unsupported operations. **Acceptance:** reproducible capability/failure inventory; locked KiCad 10.0.6 untouched. **Deps:** P0-003.
- [ ] **P0-012** Publish ADR-001 (selected backend and license posture), ADR-002 (canonical design graph), ADR-003 (tool gating), ADR-004 (toolchain split), with reasons for rejecting alternatives. **Acceptance:** decisions supported by measurements, source, and test evidence; no KiCad fork chosen solely on preference. **Deps:** P0-006–P0-011.
- [ ] **P0-013** Regression gate: original relevant CLI/pytest/Ruff and locked V6-3/DP2 test evidence remains available; compare exact-source results without claiming M2h2 visual PASS. **Acceptance:** no unauthorized legacy regressions; CI evidence linked. **Deps:** P0-001, P0-012.

**P0 EXIT:** Selected pilot backend (possibly mixed), frozen reference board, baseline report and a documented list of precise missing operations. If Konnect or another MCP fails actual core benchmarks, proceed with direct KiCad adapter rather than expanding MCP scope for its own sake.

## P1 — Canonical model, one MCP and trustworthy controller

- [ ] **P1-001** Specify and validate `design-model.v1`: stable design/revision identifiers, components, pins, nets, hierarchy, footprints/pads, electrical constraints and manufacturing profile. **Acceptance:** JSON schema and round-trip/migration tests; duplicate/missing ID negatives. **Deps:** P0-012.
- [ ] **P1-002** Map old `ai_kicad` IR to the canonical graph without changing the historical compiler. **Acceptance:** lossless mapping for POC topology; rejected unsupported multi-unit/hidden semantics surfaced explicitly; existing tests unchanged. **Deps:** P1-001.
- [ ] **P1-003** Implement immutable design revisions, content-addressed saved native files, `expected_revision` compare-and-swap, atomic candidate promotion, checkpoint and rollback. **Acceptance:** stale writes denied; crash/restart and partial-write fault injection preserve last valid state. **Deps:** P1-001.
- [ ] **P1-004** Implement capability-negotiated backend adapter interface; never silently downgrade method guarantees. **Acceptance:** declared supported/experimental/unsupported, KiCad GUI/headless preconditions and typed errors exercised in mock and real adapter tests. **Deps:** P0-012.
- [ ] **P1-005** Implement **one logical KiCad MCP server** with modular registries, versioned tool schemas, typed responses, tracing, workspace confinement and operation budgets. **Acceptance:** MCP initialize, `tools/list`, `tools/call`, valid/invalid schema, malformed/timeout/path traversal tests. **Deps:** P1-003, P1-004.
- [ ] **P1-006** Implement phase/task tool visibility in the workflow controller; start with small always-on state/capability/revision tools and lazy-loaded domain sets. **Acceptance:** mock LLM sees schematic tools but not Gerber export in schematic phase; token inventory measured. **Deps:** P1-005.
- [ ] **P1-007** Enforce **dispatch-time** phase/authorization gating independently of visibility. **Acceptance:** forged call to hidden manufacturing tool rejected; read-only actions allowed; writes fail on wrong revision or target. **Deps:** P1-006.
- [ ] **P1-008** Implement `REQUIREMENTS → CIRCUIT_DESIGN → SCHEMATIC → FOOTPRINTS → PCB_PLACEMENT → PCB_ROUTING → MANUFACTURING_REVIEW → REVIEW_READY` transition model with backward repairs. **Acceptance:** only qualified transition allowed; downstream gates invalidated on upstream mutation. **Deps:** P1-003, P1-007.
- [ ] **P1-009** Persist compact LLM phase handoffs (task, exact revision, validation, unresolved issues), with provider abstraction for hosted/local models. **Acceptance:** resume after clean process restart without tool-history context dependence. **Deps:** P1-008.
- [ ] **P1-010** Add `dry_run` plans, batch edits, idempotency keys, traces and safe uncertain-write reconciliation. **Acceptance:** duplicate/ambiguous writes do not duplicate board objects or corrupt revisions. **Deps:** P1-003, P1-005.
- [ ] **P1-011** Secure tool execution: workspace path canonicalization, untrusted text separation, tool-call budgets, secret-free logs and single-writer lease. **Acceptance:** negative/security tests pass, including forged paths, symlinks, replay and concurrent edits. **Deps:** P1-005, P1-010.
- [ ] **P1-012** Add CLI operations to create/inspect/resume/validate one design and launch the MCP service. **Acceptance:** POC controller works without an IDE, external GUI controller or specific hosted model. **Deps:** P1-009.

**P1 EXIT:** The LLM can only invoke phase-authorized tools; data loss, stale writes and unauthorized export paths are rejected. At least one real backend is accessible through typed internal interfaces and MCP.

## P2 — Known-good circuit to verified native schematic and PCB mapping

- [ ] **P2-001** Build project create/read/commit adapter for selected backend with exact saved-file readback. **Acceptance:** KiCad opens generated project; prior revision immutable. **Deps:** P1-004, P0-003.
- [ ] **P2-002** Add transactional schematic symbol and net creation, reference assignment and native serialization through selected backend or preserved compiler. **Acceptance:** complete fixed circuit emitted without manual wire editing. **Deps:** P2-001, P1-002.
- [ ] **P2-003** Add independent schematic connectivity observer reading emitted KiCad native schematic/export netlist. **Acceptance:** exact `(instance,sheet,unit,pin) → net` match to locked reference, no unexpected shorts/opens; negative fixture swaps/drops caught. **Deps:** P2-002.
- [ ] **P2-004** Validate symbol identity, library checksum and pin types; require zero unwaived unexpected ERC and distinguish warnings/unsupported. **Acceptance:** locked KiCad report tied to exact revision with negative controls. **Deps:** P2-003.
- [ ] **P2-005** Implement `assign_footprints` with approved part package and exact symbol-pin ↔ physical-pad map validation (include polarity/pin-one checks). **Acceptance:** 100% required instances mapped, wrong numbering explicitly rejected. **Deps:** P2-004.
- [ ] **P2-006** Create native `.kicad_pcb`, synchronize from schematic, reconcile unique instance and net identities. **Acceptance:** KiCad native PCB parses; independently verify component/refdes and pin/pad/net equivalence. **Deps:** P2-005.
- [ ] **P2-007** Test edited-schematic resync and detect intentional stale PCB, wrong footprint, swapped net, duplicate/missing component, and ambiguous hierarchical instance. **Acceptance:** typed hard failures and safe rework, no silent PCB overwrite. **Deps:** P2-006.
- [ ] **P2-008** Publish source/revision-bound schematic/PCB equivalence JSON report with warnings and evidence file hashes. **Acceptance:** report regenerated independently on fresh process; invalidation after design change verified. **Deps:** P2-007.

**P2 EXIT:** The known-good circuit is a native KiCad schematic and PCB containing the intended complete set of physical pads/nets. Passing ERC is **not** treated as full functional verification.

## P3 — Placement, routing, DRC and bounded repair

- [ ] **P3-001** Define a concrete, vetted two-layer board/fabricator profile: outline, thickness, copper, track/via/drill, soldermask, silkscreen, clearance and keepout assumptions. **Acceptance:** constraints validated against chosen fab capabilities; unknown rules block readiness. **Deps:** P2-008.
- [ ] **P3-002** Implement deterministic initial footprint placement from explicit board constraints or backend plans, plus explicit revision-bound placement apply and readback. **Acceptance:** legal pads/footprints/holes and no off-board/collision violations; no dependence on deprecated autoplace apply. **Deps:** P3-001.
- [ ] **P3-003** Evaluate available routing backends (Freerouting DSN/SES or an accepted alternative) against POC; define safe import semantics. **Acceptance:** router output tied to exact board revision and netlist; bad/stale/incomplete imports rejected. **Deps:** P3-002.
- [ ] **P3-004** Implement full required-net routing with track/via/zones, refill and native save/readback; avoid success on visually routed but electrically open nets. **Acceptance:** all POC required nets connected in native board, no unapproved shorts and no unresolved unrouted segments. **Deps:** P3-003.
- [ ] **P3-005** Run KiCad DRC on saved/reconciled revision after zone refill and route import, with machine-readable violation classification. **Acceptance:** zero unwaived blocking errors; ruleset and KiCad binary pinned. **Deps:** P3-004.
- [ ] **P3-006** Independently compare PCB pad/copper connectivity to canonical net mapping; reject netlist drift, shorts, unrouted nets, and stale DRC. **Acceptance:** negative mutated boards fail even if native renderer looks plausible. **Deps:** P3-005.
- [ ] **P3-007** Implement bounded LLM repair loop: inspect violations, select narrow edits, produce candidate, rerun applicable gates, retain rejected evidence and known-good revision. **Acceptance:** at least one intentionally introduced DRC fault repaired without undoing other verified nets; bounded failure terminates as `BLOCKED/FAIL`, not false `PASS`. **Deps:** P3-006, P1-008.
- [ ] **P3-008** Record placement/routing quality metrics for future optimization separately from correctness gates; no redefinition of original M2h2 thresholds. **Acceptance:** route length, via count, copper usage, density/keepout scores stored with revision. **Deps:** P3-006.

**P3 EXIT:** Fixed low-voltage PCB complete, validated with native KiCad DRC and an independent net/pad connectivity audit; source and failure evidence reproducible. No claim of analog performance or physical test.

## P4 — Manufacturing export, independent inspection and first complete POC

- [ ] **P4-001** Implement fab export: Gerber layers (copper, mask, legend, board outline and required fab layers), plated/nonplated Excellon drills, slots/drill report as applicable. **Acceptance:** files generated only from `PCB_VALIDATED` exact revision. **Deps:** P3-007.
- [ ] **P4-002** Build a separate Gerber/drill parser or viewer-based inspection adapter, verify nonempty required layers, board outline agreement, hole locations/sizes and coordinate consistency. **Acceptance:** intentionally missing/swapped/malformed layer or drill data fails. **Deps:** P4-001.
- [ ] **P4-003** Implement fab-profile DFM checklist: stackup, thickness, trace/space, via/drill minima, copper-to-edge, soldermask slivers, silkscreen clearance, board dimensions and explicit assumptions. **Acceptance:** unsupported unverified rules become warnings/blockers, never automatically approved. **Deps:** P4-002.
- [ ] **P4-004** Implement immutable `fabrication_manifest.json` and `verification_report.json` with all tool, library and project hashes, ERC/DRC/graph/DFM findings and waivers. **Acceptance:** package checksum verification and cross-file revision checks pass. **Deps:** P4-003.
- [ ] **P4-005** Package zipped native editable KiCad project, fabrication files, report, machine-readable manifest and human-readable previews. **Acceptance:** unzip in clean directory; independent inspection and native openability work without hidden local dependencies. **Deps:** P4-004.
- [ ] **P4-006** Implement `PACKAGE_READY_FOR_REVIEW` with explicit summary of what *is not* verified. **Acceptance:** no `ORDERED`, `ASSEMBLED`, `PHYSICALLY_TESTED`, or “PCBWay accepted” state without external evidence and authorization. **Deps:** P4-005.
- [ ] **P4-007** Run same complete POC ≥3 times from clean state and compare stable semantic/artifact invariants; document permitted nondeterministic file details. **Acceptance:** all gates pass on each independent run with recorded SHA/version/manifest. **Deps:** P4-006.
- [ ] **P4-008** Complete E2E negative matrix: unconnected pin, wrong pad, short, stale PCB, missing unrouted net, bad DRC, missing drill, wrong Gerber outline, bad revision manifest, disallowed phase export. **Acceptance:** all blocked at the intended gate and retain known-good revision. **Deps:** P4-007.
- [ ] **P4-009** Publish a repeatable design-to-fab demo and evidence-ledger summary, including human inspection screenshots and measured token/time/repair costs. **Acceptance:** reproducible from documented host setup; all real-tool checks linked to exact source and native project revision. **Deps:** P4-008.
- [ ] **P4-010** Write ADR on whether the selected MCP/IPC backend meets v0; record missing operations, fallback usage, licensing and maintenance costs. **Acceptance:** no forced KiCad fork; P4 meets product criterion independent of backend choice. **Deps:** P4-009.

**P4 EXIT = FIRST MAJOR PIVOT SUCCESS:** One verified, complete, fabrication-ready-for-human-review 2-layer PCB package produced without manually building the schematic or layout. Do **not** describe it as already manufactured or proven electrically functional.

## P5 — Optional physical fabrication and testing (requires owner authorization)

- [ ] **P5-001** Human independently reviews exact Gerber/drill ZIP and native KiCad project; record revision and decision. **Acceptance:** explicit signed-off decision; no automatic external order. **Deps:** P4 exit.
- [ ] **P5-002** If authorized, submit the exact approved revision to a manufacturer and retain quotation/order record, manufacturing feedback and any accepted corrections. **Acceptance:** cost/action approval was obtained first; manufacturing profile and revision match. **Deps:** P5-001.
- [ ] **P5-003** Inspect delivered board, assemble or arrange assembly under separate approval, execute documented power-on/test plan with measured voltage/current/behavior and photos. **Acceptance:** recorded actual measurements and defects, not inferred success from fabrication. **Deps:** P5-002.
- [ ] **P5-004** Reconcile measured issues into a new design revision and test regression; preserve original fab evidence. **Acceptance:** postmortem and root-cause tests, no retroactive modification of accepted files. **Deps:** P5-003.

## P6 — Post-POC expansion: circuit synthesis, SPICE, PCBA

These features are **planned**, not prerequisites for P4 except when a specific POC engineering check shows they are indispensable.

- [ ] **P6-001** Model natural-language specs with explicit ambiguity/assumptions handling and typed engineering constraints; require clarification for safety-critical unknowns. **Acceptance:** adversarial requirement cases do not silently invent vital voltage/current/pin data. **Deps:** P4 exit.
- [ ] **P6-002** Datasheet-backed component catalog, parametric filtering, approved footprints and supplier mappings; keep BOM and library data pinned. **Acceptance:** wrong voltage/package/pinout/substitution negatives caught. **Deps:** P6-001.
- [ ] **P6-003** Add engineering calculations and domain-specific assertions (resistor ratings, regulator headroom/heat, decoupling, LED current, source loading). **Acceptance:** comparison with independently computed reference cases and boundary tests. **Deps:** P6-002.
- [ ] **P6-004** Add ngspice/SPICE simulation for supported analog subcircuits and machine-readable expected behavior with limits. **Acceptance:** failing transient/operating point scenarios reject bad circuit revisions; clearly document simulation limitations. **Deps:** P6-003.
- [ ] **P6-005** Add BOM/part substitution and PCBWay-compatible centroid/PnP/paste and assembly-drawing export. **Acceptance:** every SMT refdes matches correct side/rotation/footprint and approved BOM quantities; parser/rotation negatives caught. **Deps:** P4 exit, P6-002.
- [ ] **P6-006** Evaluate AI-generated new circuit topology against a diverse held-out test suite and human electrical review. **Acceptance:** independent calculation/simulation/real-tool gates, reproducible results and explicit unknowns. **Deps:** P6-004.
- [ ] **P6-007** Expand board profiles only after separate engineering gates for higher current/voltage, RF, switching supplies, high-speed constraints, multilayer and thermal effects. **Acceptance:** supported/unsupported domain manifest and tailored tests; no blanket certification. **Deps:** P6-006.
- [ ] **P6-008** Decide whether to resume targeted M2h2 aesthetic optimization, based on measured human readability and manufacturing task performance; retain frozen historical acceptance definitions. **Acceptance:** benchmark-based prioritization ADR, not assumed completion of previous TODO. **Deps:** P4 exit.

## P7 — Conditional native KiCad extension/fork gate

- [ ] **P7-001** Maintain precise `capability_gap.json` with an observable essential operation, required pre/postconditions, tested API versions, external adapters attempted and resulting failures. **Acceptance:** no “we need deeper control” claims without a reproducible concrete gap. **Deps:** P0-011, P4-010.
- [ ] **P7-002** Before forking, prototype through supported KiCad IPC/CLI and isolated native plugin or structured-file transaction. **Acceptance:** comparison of safety, completeness and maintenance burden with reproducible test. **Deps:** P7-001.
- [ ] **P7-003** If still essential, write owner-approved fork RFC (minimal protobuf/handler surface, undo semantics, upstreamability, license, security, pinned builds). **Acceptance:** explicit owner approval; not automatic. **Deps:** P7-002.
- [ ] **P7-004** Only after authorization, implement a minimal KiCad C++ patch/extension with integration tests and upstream proposal; maintain version-specific compatibility matrix. **Acceptance:** tests demonstrate the exact missing operation safely, not a replacement KiCad distribution for its own sake. **Deps:** P7-003.

## Cross-cutting CI/evidence checklist (required at applicable milestones)

- [ ] **X-001** Real KiCad build jobs are tied to exact commit SHA and recorded toolchain/asset hashes, not branch-name-only success; skipped CI ≠ passed.
- [ ] **X-002** Unit + type/schema tests, pytest and Ruff pass for all newly modified pivot Python modules.
- [ ] **X-003** Independent observer derives results from emitted design/board/output artifacts, not producer's own certificates.
- [ ] **X-004** Revision CAS, isolated candidate rollback, authentication/authorization, idempotency, timeout and fault-injection tests pass.
- [ ] **X-005** No untrusted datasheet/tool text elevated to executable instructions; workspace sandbox and secret redaction tested.
- [ ] **X-006** Existing frozen M2h2/DP1–DP4/historical baseline evidence remains unchanged; any accepted scoped behavior changes include regression proof.
- [ ] **X-007** Build/run/evidence scripts work on supported Ubuntu runner without Docker/Podman dependencies and with documented `uv` setup; frontend is not required for headless CI.
- [ ] **X-008** Artifact storage quota failure does not silently destroy proof: retain local content-addressed evidence with durable manifests and publish compact outcome links.
- [ ] **X-009** All hardware, physical test and purchasing claims are substantiated by real recorded evidence and explicit authorization.

## Engineering blockers and recovery rules

| Event | Correct next action | Not permitted |
|---|---|---|
| Tool isn't in phase bundle | request authorized toolset/phase transition | bypass dispatch restriction |
| Unsupported native KiCad call | test approved adapter/fallback and document evidence | silently downgrade validation |
| ERC/DRC failure | inspect structured violations and bounded repair, rerun gates | redefine hard rules to pass without decision |
| Stale board revision | reject candidate, resync/recompute from verified source | reuse old routing/manufacturing result |
| Router doesn't converge | retain last valid board, report blocked net/candidate and test alternative | claim routing complete |
| CI running/failing | inspect/poll exact-head CI and fix or work on independent tasks | claim PASS from a launched/skipped workflow |
| GitHub artifact quota exhausted | use persistent local evidence + checksum manifest, surface limitations | fabricate links or discard required evidence |
| Missing hardware/fabricator decision | stop only that physical external step and ask owner | pretend physical acceptance |
| Suspected KiCad bug/API gap | reproduce precisely and file an RFC before native changes | start a general KiCad fork immediately |

## Final completion definition

**The P0–P4 pivot is complete only when** the exact latest POC revision has a saved native KiCad schematic and PCB; independently verified connectivity through pin-pad-net mapping; passing relevant KiCad ERC and DRC; complete routed board; independent Gerber/drill inspection; immutable fabrication ZIP and validation reports; repeated clean-run qualification; and a truthful `PACKAGE_READY_FOR_REVIEW` status. Its manufacture and functionality remain unverified pending authorized P5 tests.

**The entire long-term autonomous-design vision is not complete at P4.** P5 (physical feedback), P6 (novel circuits, component engineering, SPICE, PCBA) and any P7 native extension are separate, evidence-based milestones.

**As of draft:** all pivot tasks are unchecked; no pivot code, new branch, KiCad fork, order, or fabrication-ready PCB has been created by these documents.
