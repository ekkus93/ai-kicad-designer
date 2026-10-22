# ADR-000: MCP pivot branch baseline

**Status:** Accepted for the isolated `mcp` branch  
**Date:** 2026-10-21  
**Baseline:** `f14a02c3140fd455ded8391ea65b8416b5d6e170`

## Context

The MCP architecture and execution plan are proposals for an isolated pivot.
The project owner directed work to continue on the existing `mcp` branch and
authorized execution of `docs/MCP_ARCHITECTURE_TODO.md`. The branch starts from
the project checkpoint at `5303c5f40424148b954adf297b84bac704eaf182` and adds
the two MCP architecture documents.

The checkout contains pre-existing untracked M2H2 evidence. Those files are
preserved and excluded from the tracked baseline inventory. The tracked M2H2
tree has 22,544 files and is recorded by both its Git tree ID and every tracked
blob ID in `fixtures/pivot/m2h2_protection_inventory_2026-10-21.json`.

## Decision

- Keep all pivot changes on `mcp` until the owner directs otherwise.
- Keep `master` and the existing M2H2 acceptance track independent.
- Retain KiCad 10.0.6 as the pinned real-tool baseline; its executable and
  library hashes are verified by the repository lock.
- Use a fixed 5 V NE555 astable with a low-current LED indicator as the first
  reference topology. The exact circuit corpus and board remain P0-003 work.
- Evaluate MCP implementations against the same design and independent gates
  before selecting a backend. No external code is copied or bundled as part of
  this baseline decision.

## Consequences

The existing M2h2 track remains **INCOMPLETE** and its source, fixtures, and
historical records are not changed. The pivot backend remains unselected until
the P0 experiments produce comparable real-tool evidence. The choice of a
reference topology does not assert that a PCB or fabrication package exists.

## Evidence

- `fixtures/pivot/mcp_branch_baseline_2026-10-21.json`
- `fixtures/pivot/m2h2_protection_inventory_2026-10-21.json`
- `fixtures/pivot/mcp_backend_capability_inventory_2026-10-21.json`
