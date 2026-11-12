# Repository Guidelines

## Project Structure & Module Organization

The installable Python package lives in `src/ai_kicad/`; its CLI entry point is `src/ai_kicad/__main__.py`. Automated tests are in `tests/`, with `tools/` holding standalone analysis, fixture-generation, audit, and qualification scripts. `examples/` contains sample designs, `fixtures/` holds test and qualification inputs/evidence, and `docs/` contains specifications and audit records. The curated legacy snapshot under `research/legacy_openclaw/` is separate from the main package.

## Build, Test, and Development Commands

Use Python 3.12. Install the package and pinned development tools with:

```sh
python -m pip install -e '.[dev]'
```

Run the full test suite with `python -m pytest -q`; run one test module with `python -m pytest -q tests/test_m2a.py`. Check lint with `python -m ruff check src/ai_kicad tests tools`. Check formatting with `python -m ruff format --check src/ai_kicad tests tools` (format changed files using `python -m ruff format <paths>`). For a local CLI smoke test, use `python -m ai_kicad --help`.

## Coding Style & Naming Conventions

Follow Ruff settings in `pyproject.toml`: Python 3.12 syntax and a 100-character line limit. Use four-space indentation, descriptive `snake_case` names for modules, functions, and variables, and `PascalCase` for classes. Keep production code in `src/ai_kicad`; place focused regression tests in `tests/test_<area>.py`. Use type annotations and small, explicit helpers consistent with neighboring code.

## Testing Guidelines

Tests use pytest and are discovered from `tests/`. Name test files `test_*.py` and test functions `test_*`; add focused regression cases alongside the affected area. Run relevant tests after changes, then the full suite and Ruff checks for broader changes. Qualification scripts may require the locked KiCad toolchain or specific evidence inputs; consult the matching workflow and tool documentation before running them.

## Commit & Pull Request Guidelines

Recent commits use concise imperative subjects, often naming the area (for example, “Format bounded routing regression tests”). Keep commits focused and describe the behavior or evidence change. A pull request should summarize the change and its rationale, list tests and checks run, link related issues or qualification records, and include rendered schematics or other visual evidence when output quality changes.

## Evidence and Configuration

Treat frozen baselines, qualification artifacts, and audit thresholds as controlled evidence. Do not rewrite historical fixture data or weaken acceptance criteria to make a check pass; add new, clearly identified evidence instead. Keep machine-specific toolchain configuration out of source changes and follow the relevant locked-toolchain workflow for reproducible qualification.
