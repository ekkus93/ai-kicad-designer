"""Regression guards for persisted M2h2 native render inspection transport."""

from __future__ import annotations

from pathlib import Path

import pytest

from audit_m2h2_persisted_native_renders import (
    inventory_case,
    require_deterministic_geometry,
)


def _write_native_svg(run: Path, *, title: str, path_data: str = "M 1 2 L 3 4") -> None:
    output = run / "renders" / "schematic"
    output.mkdir(parents=True)
    (output / "test.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><title>'
        + title
        + '</title><path d="'
        + path_data
        + '"/></svg>'
    )


def test_five_native_renders_normalize_volatile_titles(tmp_path: Path) -> None:
    for index in range(1, 6):
        _write_native_svg(tmp_path / f"run{index}", title=f"volatile-{index}")
    report = inventory_case(tmp_path, "base__generic", [{}] * 5)
    assert len(report["renders"]) == 5
    assert not report["byte_identical"]
    assert report["normalized_identical"]
    assert len({item["sha256"] for item in report["renders"]}) == 5
    assert len({item["normalized_svg_sha256"] for item in report["renders"]}) == 1


def test_geometry_mutation_is_not_normalized_away(tmp_path: Path) -> None:
    for index in range(1, 6):
        geometry = "M 1 2 L 3 9" if index == 3 else "M 1 2 L 3 4"
        _write_native_svg(tmp_path / f"run{index}", title=f"volatile-{index}", path_data=geometry)
    report = inventory_case(tmp_path, "base__generic", [{}] * 5)
    assert not report["normalized_identical"]


def test_missing_or_extra_renders_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="expected five qualification runs"):
        inventory_case(tmp_path, "base__generic", [{}] * 4)
    for index in range(1, 6):
        _write_native_svg(tmp_path / f"run{index}", title=str(index))
    (tmp_path / "run1/renders/schematic/extra.svg").write_text("<svg/>")
    with pytest.raises(ValueError, match="run1 has 2 SVGs"):
        inventory_case(tmp_path, "base__generic", [{}] * 5)


def test_non_svg_payload_is_rejected(tmp_path: Path) -> None:
    for index in range(1, 6):
        _write_native_svg(tmp_path / f"run{index}", title=str(index))
    (tmp_path / "run4/renders/schematic/test.svg").write_text("this is not SVG")
    with pytest.raises(ValueError, match="not native SVG content"):
        inventory_case(tmp_path, "base__generic", [{}] * 5)


def test_normalized_geometry_mismatch_fails_qualification(tmp_path: Path) -> None:
    for index in range(1, 6):
        geometry = "M 1 2 L 3 9" if index == 3 else "M 1 2 L 3 4"
        _write_native_svg(tmp_path / f"run{index}", title=f"volatile-{index}", path_data=geometry)
    record = inventory_case(tmp_path, "base__generic", [{}] * 5)
    with pytest.raises(ValueError, match="base__generic"):
        require_deterministic_geometry({"cases": [record]})


def test_normalized_geometry_gate_allows_volatile_titles(tmp_path: Path) -> None:
    for index in range(1, 6):
        _write_native_svg(tmp_path / f"run{index}", title=f"volatile-{index}")
    record = inventory_case(tmp_path, "base__generic", [{}] * 5)
    require_deterministic_geometry({"cases": [record]})
