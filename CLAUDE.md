# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

## Environment

- System `python3` is 3.10; use `.venv/bin/python` (3.12) or `uv run` for every `python -m ...` command.
- Locked KiCad launcher on this host: `/tmp/AppDir/AppRun` (see `fixtures/m1a/toolchain.lock.json`). Pass it explicitly to pivot tools via `--kicad-apprun` / `--kicad-cli`; the `/home/phil/Applications/...` paths in some tests and docs are desktop-only.
- Standalone tool scripts need `PYTHONPATH=src:tools` (CI) to import the package and sibling tools.

## Testing

- Default verification: `python -m pytest -q tests/pivot` plus the test modules for the changed area. The full suite takes ~45 minutes; run it only when asked.
- KiCad-dependent tests (e.g. `test_m1a`, `test_m1b`, `test_m2a`, `test_m2b`, `test_m2c1`, `tests/pivot/test_direct_backend.py`) fail rather than skip when the locked toolchain or host identity doesn't match. Report such failures as environment failures, don't "fix" them.
- If a change touches M2h2 code (non-pivot `src/ai_kicad/m2*`, `tests/test_m2h2*`, `tools/*m2h2*`, `fixtures/m2h2/`), also run `python tools/run_m2h2_structural_audit.py` and `python tools/run_m2h2_source_stabilization_audit.py`.

## Protected evidence

- Pivot work (`src/ai_kicad/pivot/`, `tests/pivot/`, `tools/pivot/`, `fixtures/pivot/`) must not modify protected M2h2 source, tests, or fixtures; the baseline is `fixtures/pivot/m2h2_protection_inventory_2026-10-21.json`. M2H2 remains INCOMPLETE (`fixtures/m2h2/STATUS.md`).
- Never touch, clean, or commit the untracked `fixtures/m2h2/*` directories — they are preserved evidence.
- Experiment outputs are write-once: allocate new `fixtures/pivot/experiments/<name>_<YYYY-MM-DD>_run<N>/` dirs via `tools/pivot/experiment_paths.py`; never overwrite a previous run.
- KiCad SVG renders and ngspice `.dat` files are hash-verified byte-for-byte (see `.gitattributes`); never reformat or strip their trailing whitespace.
- Task checkboxes in `docs/MCP_ARCHITECTURE_TODO.md` are checked only with implementation plus real-tool evidence for the stated scope; mocked output or skipped CI doesn't count.
