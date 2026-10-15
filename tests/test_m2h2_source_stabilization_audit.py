"""Focused controls for source stabilization and historical evidence guards."""

from pathlib import Path

from run_m2h2_source_stabilization_audit import (
    EXPECTED_HISTORICAL_INVENTORY,
    check_frozen_inventory,
    check_local_links,
    prohibited_source_imports,
)


def test_frozen_inventory_guard_rejects_changed_count_and_hash() -> None:
    assert check_frozen_inventory(90, EXPECTED_HISTORICAL_INVENTORY) == []
    assert check_frozen_inventory(89, EXPECTED_HISTORICAL_INVENTORY)
    assert check_frozen_inventory(90, "0" * 64)


def test_local_markdown_links_preserve_anchors_and_detect_missing_files(
    tmp_path: Path,
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "exists.md").write_text("# Existing\n")
    document = docs / "review.md"
    document.write_text(
        "[existing](exists.md#section) [anchor](#inside) "
        "[remote](https://example.com/) [missing](missing.md)\n"
    )
    assert check_local_links(tmp_path, document) == [
        "docs/review.md: missing link missing.md"
    ]


def test_local_markdown_links_reject_path_escape(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    document = docs / "review.md"
    document.write_text("[escaped](../../external.md)\n")
    assert check_local_links(tmp_path, document)


def test_prohibited_solver_imports_and_dynamic_imports() -> None:
    source = (
        "import ortools.sat.python.cp_model\n"
        "from pulp import LpProblem\n"
        "from importlib import import_module\n"
        "solver = import_module('cvxpy')\n"
    )
    errors = prohibited_source_imports(source, "m2_example.py")
    assert len(errors) == 3
    assert prohibited_source_imports("import math\n", "m2_example.py") == []


def test_production_fixture_dispatch_table_is_rejected() -> None:
    assert prohibited_source_imports(
        'rules = {"V6-3": "special", "normal": "generic"}\n', "m2_example.py"
    )
    assert prohibited_source_imports(
        'rules = {"reference": "generic"}\n', "m2_example.py"
    ) == []
