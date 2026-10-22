# ADR-002: Canonical design graph

**Status:** Accepted
**Date:** 2026-10-22
**Scope:** `mcp` pivot

## Decision

`design-model.v1` is the canonical engineering source of truth. Stable design,
component, pin, net, footprint, pad, constraint, and manufacturing-profile
identities live in a typed versioned document. KiCad schematic and PCB files
are revision-bound realizations of that graph, not substitutes for it.

Every accepted native revision must be reconstructed by an independent
observer and compared to the canonical terminal partitions and pin/pad/net
mapping. Producer success messages, visual rendering, ERC, and DRC cannot
replace that comparison. Unsupported hierarchy, multi-unit, hidden-power, or
manufacturing semantics fail explicitly rather than being approximated.

The existing historical compiler and IR remain unchanged. A separate adapter
maps their supported fixed-reference subset into `design-model.v1`; the new
model therefore does not rebaseline M2H2 fixtures or acceptance rules.

## Evidence and rejected alternatives

The reference design's independent exported-netlist comparison passed in the
direct, Konnect, Seeed, and ProductOfAmerica probes. Konnect's component-net
API collapsed unnamed physical partitions, showing why a backend response or
native file hash alone cannot be the canonical connectivity model. A KiCad
document-only source of truth was rejected because stable intent and revision
invalidation cannot be recovered reliably from presentation geometry.
