# ADR-003: Tool visibility and dispatch gating

**Status:** Accepted
**Date:** 2026-10-22
**Scope:** `mcp` pivot

## Decision

Expose one logical MCP server with small phase and task bundles. Tool
visibility is only a context optimization. A separate dispatch policy checks
phase, exact design revision, workspace target, operation risk, write lease,
idempotency key, and budget for every call, including manually forged calls.

State, capability, revision, validation, checkpoint, rollback, and phase
transition tools remain available across phases. Domain writes require
compare-and-swap against the current revision and create isolated candidates.
Manufacturing export is authorized only from a validated PCB revision.

## Evidence and rejected alternatives

Three matched repetitions with 4, 57, and 236 visible Konnect tools showed
that the four-tool task bundle completed required calls consistently. The
larger inventories repeatedly supplied an invalid `project_dir` argument and
used materially more prompt tokens. Hidden-tool, traversal, and symlink calls
are already rejected by the benchmark runner tests. Backend toolset loading
alone was rejected as authorization because a caller can forge `tools/call`.
