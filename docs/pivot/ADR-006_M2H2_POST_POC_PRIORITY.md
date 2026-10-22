# ADR-006: keep M2h2 aesthetic optimization deferred

**Status:** Accepted
**Date:** 2026-10-22

## Decision

Do not resume targeted M2h2 aesthetic optimization as part of the MCP v0 work. Preserve its frozen definitions and historical **INCOMPLETE** status.

The reference PCB work produced a review package using a small phase-gated tool inventory and exact engineering observers. Earlier benchmark evidence showed that task-gated tools completed required calls more reliably and with fewer tokens than phase-wide or full Konnect inventories. The remaining product risks are general circuit coverage, routing coverage, assembly data, and physical validation. Improving historical schematic aesthetics does not close those risks.

Reconsider M2h2 only with a benchmark that measures human schematic reading performance or a demonstrated manufacturing workflow failure caused by schematic presentation. That future benchmark must retain the frozen M2h2 acceptance definitions; it cannot relabel the historical result as complete.
