# MCP pivot handoff for desktop development

**Date:** 2026-10-22  
**Branch:** `mcp`  
**Pivot baseline commit:** `f14a02c3140fd455ded8391ea65b8416b5d6e170` (`spec and TODO files for new mcp architecture`)

## Owner direction

Development is moving to a machine with a desktop. Continue the MCP pivot on the `mcp` branch and follow [`MCP_ARCHITECTURE_TODO.md`](../MCP_ARCHITECTURE_TODO.md). Keep the locked KiCad 10.0.6 environment unchanged. The owner did not authorize upgrading the installed KiCad. Do not change the KiCad installation as part of this handoff.

## Workspace state

The pivot implementation, TODO progress, evidence, and this handoff are committed on `mcp`. Use the commit containing this handoff when moving to the desktop machine. The workspace also contains pre-existing untracked M2H2 investigation artifacts under `fixtures/m2h2/` and `.serena/`; they were not included in the pivot commit. Preserve them locally if still needed, and do not fold them into the pivot handoff.

The KiCad 10.99 nightly package previously downloaded for the P0-011 probe was only extracted under `/tmp/kicad-nightly-root`. No system packages were installed and the locked KiCad 10.0.6 installation was not changed. The extracted binary has an `api-server` command, but it could not start because its runtime dependencies were absent. This temporary directory is not needed to continue KiCad 10 headless CLI work.

## Progress recorded in the TODO

Completed: G-001 through G-005, P0-001 through P0-005, P0-007, P0-008, and P0-010. The main evidence is under `fixtures/pivot/`, including the reference 555 LED flasher, backend capability inventory, independent ProductOfAmerica DRC repair assessment, Seeed connectivity/edit probes, and tool visibility comparison.

The pivot-focused suite previously passed 21 tests, and Ruff lint/format checks passed for the pivot work. P0-013 remains open, so this is not a claim that the full project regression gate has passed. The ProductOfAmerica candidate passed independent KiCad 10 DRC after repair and produced Gerber/drill files, but is not claimed fabrication-ready or physically verified.

Still open in P0: P0-006 (Konnect write/PCB/rollback coverage), P0-009 (direct automation baseline), P0-011 (KiCad 11 API/version probe), P0-012 (backend/model/tooling ADRs), and P0-013 (regression gate). P1 and later milestones remain open. Read the TODO entries and their evidence paths before repeating experiments.

## Headless KiCad clarification

Headless use is supported for KiCad CLI operations such as ERC, DRC, netlist generation, and exports. The current locked KiCad 10 IPC API is hosted by a running GUI process; a physical monitor is not necessary if a virtual display is used. KiCad 11 adds a headless `kicad-cli api-server`, but that is a separate development-version probe, not a reason to upgrade the installed KiCad. Use the existing KiCad 10 CLI for headless tasks on the desktop and record the exact executable/version in new evidence.

## Resume steps

1. Preserve/copy the full working tree, including the untracked pivot directories and modified TODO, onto the desktop machine.
2. Confirm the checkout is on `mcp`, inspect `git status`, and verify the locked KiCad 10.0.6 installation and tool paths before running anything.
3. Read [`MCP_ARCHITECTURE_SPEC.md`](../MCP_ARCHITECTURE_SPEC.md), [`MCP_ARCHITECTURE_TODO.md`](../MCP_ARCHITECTURE_TODO.md), and [`pivot/STATUS.md`](STATUS.md).
4. Continue with open P0 tasks, reusing the existing fixture/evidence conventions. Keep each experiment isolated and write-once under `fixtures/pivot/experiments/`.
5. Run the repository's pivot-focused checks and then applicable regression checks before updating completion boxes. Do not mark a task complete based on tool inventory or model claims alone.

