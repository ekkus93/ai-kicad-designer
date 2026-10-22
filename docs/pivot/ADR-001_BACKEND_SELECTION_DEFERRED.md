# ADR-001: Select the direct KiCad adapter as the pilot backend

**Status:** Accepted; supersedes the temporary deferral recorded on 2026-10-22
**Date:** 2026-10-22
**Scope:** `mcp` pivot only
**Related:** [ADR-000](ADR-000_BRANCH_BASELINE.md), [`MCP_ARCHITECTURE_TODO.md`](../MCP_ARCHITECTURE_TODO.md)

## Context

The pivot compares Konnect, ProductOfAmerica and Seeed against one pinned
reference circuit. The measured results establish useful differences, but no
candidate yet satisfies the complete required contract:

- Konnect 0.13.0 passes native project ERC and netlist export, but its component
  net API returns null for unnamed nets. Its GUI/IPC and board transaction
  behavior have not been tested in this runner.
- ProductOfAmerica 0.21.1 synchronized footprints, routed the fixed reference
  on a disposable copy, and produced zero DRC violations/unconnected items
  after a targeted width correction. Its package is GPL-3.0-or-later. The full
  pilot still needs repeated clean runs, independent manufacturing-output
  inspection, phase-controlled dispatch, and the remaining negative tests.
- Seeed 3.4.11 produced a netlist with independently equivalent connectivity.
  A test edit serialized, but native ERC rejected the dangling label. Only
  copy-discard rollback has been demonstrated.
- Across three Qwen repetitions per configuration, four-tool task gating
  completed required calls but failed engineering accuracy. The 57-tool phase
  and 236-tool full inventories repeatedly induced invalid `get_project_info`
  arguments. See `fixtures/pivot/experiments/tool_visibility_comparison_2026-10-22.json`.

## Decision

Use the existing `ai_kicad` compiler, independently parsed native files,
KiCad CLI 10.0.6, and official KiCad IPC as the pilot backend. The outward MCP
server will call this adapter through typed domain operations. Konnect remains
an optional external experimental adapter for operations where its observed
postconditions can be independently verified; it is not the canonical design
model or an engineering judge.

The direct baseline completed the fixed schematic, exact pin/net comparison,
bounded native-file edit and byte-identical rollback, native DRC, and
Gerber/drill export in 1.95 seconds with five valid calls and no model tokens.
The live Konnect probe under Xvfb successfully performed schematic and PCB
read/write/readback, dry-run PCB synchronization, zero-result ERC/DRC,
Gerber/drill export, invalid-write rejection, and explicit restoration. Its
unnamed-net query limitation remains, and the larger model-facing tool surface
did not produce correct engineering answers in the benchmark.

Konnect is AGPL-3.0-only at the tested commit; ProductOfAmerica is
GPL-3.0-or-later and is in maintenance mode. Neither source nor binary is
vendored. Distribution or hosted use of either optional external runtime needs
separate legal review. Seeed remains a separately executed experimental
adapter. The direct adapter avoids making the v0 product depend on those
license decisions.

## Consequences

- P1 implements one logical MCP namespace over the direct adapter boundary.
- Task-gated visibility remains the model-facing default, with independent
  dispatch authorization and native postcondition checks.
- The benchmark results establish capability measurements, not fabrication
  qualification or autonomous engineering correctness.
- KiCad 10.0.6 remains the locked production baseline. The isolated official
  10.99 development AppImage successfully exposed headless schematic IPC,
  commit/drop/readback semantics, and exact restoration. It is experimental
  evidence, not a released KiCad 11 production selection.
- The existing M2H2 acceptance track remains **INCOMPLETE**. This pivot does not
  change its source, fixtures, thresholds, historical evidence or status.

## Evidence

- `fixtures/pivot/mcp_backend_capability_inventory_2026-10-21.json`
- `fixtures/pivot/experiments/tool_visibility_comparison_2026-10-22.json`
- `fixtures/pivot/experiments/productofamerica_drc_repair_2026-10-22_run1/independent_assessment.json`
- `fixtures/pivot/experiments/seeed_edit_probe_2026-10-22_run1/independent_assessment.json`
- `fixtures/pivot/experiments/mcp_protected_tree_audit_2026-10-22_run1.json`
- `fixtures/pivot/experiments/konnect_desktop_live_probe_2026-10-22_run1/independent_assessment.json`
- `fixtures/pivot/experiments/direct_automation_baseline_2026-10-22_run5/assessment.json`
- `fixtures/pivot/experiments/kicad_development_headless_2026-10-22_run3/capability_inventory.json`
