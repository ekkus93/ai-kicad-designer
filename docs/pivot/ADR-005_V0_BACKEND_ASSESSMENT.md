# ADR-005: v0 backend assessment

**Status:** Accepted
**Date:** 2026-10-22

## Decision

The v0 pilot uses the existing `ai_kicad` compiler, immutable native KiCad files, locked KiCad 10.0.6 CLI checks/exports, and official KiCad IPC only where a live GUI operation is needed. The logical MCP server exposes this implementation through typed capability declarations and phase-gated controller tools.

This backend meets the v0 product criterion for the reference board. Three clean runs (19–21) produce a native editable project and review ZIP with exact schematic connectivity, exact symbol-pin to pad/net mapping, connected native copper, zero unwaived ERC/DRC findings, parsed Gerber/drill geometry, DFM checks, and human-readable top/bottom renders.

## Measured fallback usage and gaps

- The reference routed board originated in the pinned ProductOfAmerica/Freerouting experiment and is now treated as revision-bound native input. Current v0 reruns validate and export it directly; they do not claim a general autorouter.
- Konnect remains an optional external AGPL adapter. It proved useful for live KiCad 10 IPC, but its schematic API collapses unnamed net identities and it is not required at runtime.
- The isolated KiCad 10.99 development API supports headless schematic transactions. Board access without a loaded board remains unsupported in that probe.
- The in-repository direct adapter is Python under this repository's license. KiCad remains an external GPL application; Konnect is not vendored or distributed here.
- Advanced circuit synthesis, general routing, SMT assembly output, and physical fabrication are outside the v0 proof.

## Consequence

No KiCad fork is justified for v0. Any future native change must begin with a concrete, reproducible essential capability gap and a separate owner-approved RFC.

## Evidence

- `fixtures/pivot/experiments/reference_poc_2026-10-22_run19` through `run21`; clean ZIP extraction and KiCad/observer verification is recorded in `fixtures/pivot/experiments/reference_poc_review_2026-10-22_run2/reports/clean-extract-validation.json`
- `fixtures/pivot/experiments/reference_poc_repeatability_2026-10-22.json`
- `fixtures/pivot/experiments/konnect_desktop_live_probe_2026-10-22_run1`
- `fixtures/pivot/experiments/kicad_development_headless_2026-10-22_run3`
