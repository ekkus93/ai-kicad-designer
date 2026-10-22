# ADR-001: Defer MCP backend selection

**Status:** Accepted as a temporary decision; selection remains open
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

Do not select one MCP backend as the production or canonical implementation
yet. Continue evaluating the candidates behind the same adapter boundary and
keep the direct KiCad baseline available. Use task-gated tool visibility for
further model trials because it had the fewest invalid calls; this is not an
approval to trust its engineering output.

The backend license posture is also undecided. ProductOfAmerica's GPL-3.0-or-
later terms need an owner decision on whether an external optional runtime is
acceptable for the intended distribution. No third-party backend source or
binary is added to the repository by this decision.

## Consequences

- P0-006, P0-009, P0-011 and P0-012 remain open pending their stated evidence.
- The benchmark results establish capability measurements, not fabrication
  qualification or autonomous engineering correctness.
- KiCad 10.0.6 remains the locked baseline; the extracted 10.99 nightly probe is
  isolated under `/tmp` and is not a supported toolchain decision.
- The existing M2H2 acceptance track remains **INCOMPLETE**. This pivot does not
  change its source, fixtures, thresholds, historical evidence or status.

## Evidence

- `fixtures/pivot/mcp_backend_capability_inventory_2026-10-21.json`
- `fixtures/pivot/experiments/tool_visibility_comparison_2026-10-22.json`
- `fixtures/pivot/experiments/productofamerica_drc_repair_2026-10-22_run1/independent_assessment.json`
- `fixtures/pivot/experiments/seeed_edit_probe_2026-10-22_run1/independent_assessment.json`
- `fixtures/pivot/experiments/mcp_protected_tree_audit_2026-10-22_run1.json`
