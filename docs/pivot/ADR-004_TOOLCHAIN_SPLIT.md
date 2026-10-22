# ADR-004: Production and development KiCad toolchain split

**Status:** Accepted
**Date:** 2026-10-22
**Scope:** `mcp` pivot

## Decision

KiCad 10.0.6 remains the production and qualification baseline. The original
six pinned AppImage files retain their exact hashes. A migrated machine gets a
separate host lock only after all six identities match; this does not rewrite
or claim qualification for the historical runner's CPU and OS identity.

KiCad development snapshots run from isolated AppImages with separate config,
workspace, Python binding, socket, and evidence directories. They may inform
capability negotiation but cannot produce production acceptance evidence until
a released version is explicitly adopted and qualified.

## Evidence and rejected alternatives

The desktop AppImage matches all six pinned KiCad 10.0.6 file hashes. Its
historical runner preflight correctly fails on the new CPU and OS, while the
separate desktop preflight records the distinction without changing the lock.
The isolated official 10.99.0 development AppImage ran `api-server`, read the
reference schematic and netlist, dropped and pushed batched edits, restored
the original value, and left every locked KiCad 10 file hash unchanged.

Upgrading the installed KiCad, rewriting the historical platform lock, and
treating a 10.99 snapshot as a released KiCad 11 build were rejected.
