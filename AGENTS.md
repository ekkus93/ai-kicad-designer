# Repository Guidelines

## Project Structure & Module Organization

This repository is an early-stage AI-assisted KiCad designer. `docs/PRODUCT_GOAL.md` defines the intended flow from circuit requirements through structured Circuit IR to a deterministic EDA pipeline. `examples/good/` holds licensed reference designs, `examples/bad/` captures known layout failures, and `examples/baseline/` holds comparison fixtures. `research/legacy_openclaw/` contains reusable Python code and tests from an earlier project; it is a reference snapshot, not the architecture for the new application. The root `scripts/` directory has no active commands yet.

## Build, Test, and Development Commands

There is no root-level build or application entry point yet. For work on the legacy Python snapshot, run commands from `research/legacy_openclaw/`:

```sh
python -m pip install -e '.[dev]'   # Install the package and test/lint tools
python -m pytest                   # Run the snapshot test suite
python -m pytest --cov=kicad_pcb   # Check coverage against the 70% configured floor
ruff check src tests               # Check Python lint rules
ruff format --check src tests      # Check formatting
```

## Coding Style & Naming Conventions

Python targets 3.11. Use four-space indentation, double quotes, and a 100-character line limit, as configured in `research/legacy_openclaw/pyproject.toml`. Use `snake_case` for modules and functions, `PascalCase` for classes, and descriptive names for Circuit IR fields and KiCad artifacts. Run Ruff before submitting Python changes.

## Testing Guidelines

Tests use pytest and live in `research/legacy_openclaw/tests/unit/`; name new files `test_*.py` and test functions `test_*`. Keep unit tests focused on observable parser, validation, document, or evaluation behavior. Mark tests that need external tools with the configured `integration` or `requires_kicad` markers. Add or update a fixture when changing behavior represented by the curated examples.

## Commit & Pull Request Guidelines

Recent commits use brief plain-language subjects without a required prefix. Write a specific subject describing the change. In pull requests, explain the behavior changed, link any relevant issue, list the checks run, and include a rendered schematic or board image when visual output changes. Keep third-party KiCad examples accompanied by provenance and license details; see `examples/good/MANIFEST.md`.
