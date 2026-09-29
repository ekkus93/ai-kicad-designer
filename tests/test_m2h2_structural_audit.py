"""Portable tests for M2h2 structural anti-overfitting audit rules."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from run_m2h2_structural_audit import audit_paths  # noqa: E402


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _kinds(report: dict) -> set[str]:
    return {item["kind"] for item in report["findings"]}


def test_structural_audit_accepts_role_based_generic_dispatch(tmp_path: Path) -> None:
    module = _write(
        tmp_path / "src/ai_kicad/m2_generic.py",
        """
def choose(role: str) -> str:
    if role == "reference":
        return "generic-reference-routing"
    labels = {"VREF": "data-only literal, not control-flow dispatch"}
    return labels.get(role, "fallback")
""",
    )

    report = audit_paths([module])

    assert report["pass"] is True
    assert report["findings"] == []


def test_structural_audit_accepts_fixture_names_as_evidence_metadata(tmp_path: Path) -> None:
    module = _write(
        tmp_path / "src/ai_kicad/m2_metadata.py",
        """
def report() -> dict:
    return {"schema_version": "m2g2.composition.1", "historical_case": "V6-3"}
""",
    )

    report = audit_paths([module])

    assert report["pass"] is True
    assert report["findings"] == []


def test_structural_audit_rejects_fixture_specific_control_flow(tmp_path: Path) -> None:
    module = _write(
        tmp_path / "src/ai_kicad/m2_bad_fixture.py",
        """
def choose(design_id: str) -> int:
    if design_id == "V6-3":
        return 3
    return 0
""",
    )

    report = audit_paths([module])

    assert report["pass"] is False
    assert "fixture_specific_literal" in _kinds(report)
    assert report["findings"][0]["literal"] == "V6-3"


def test_structural_audit_rejects_literal_net_control_flow(tmp_path: Path) -> None:
    module = _write(
        tmp_path / "src/ai_kicad/m2_bad_net.py",
        """
def choose(net: str) -> int:
    if net == "VREF":
        return 1
    return 0
""",
    )

    report = audit_paths([module])

    assert report["pass"] is False
    assert "net_literal_control_flow" in _kinds(report)


def test_structural_audit_rejects_literal_refdes_match_dispatch(tmp_path: Path) -> None:
    module = _write(
        tmp_path / "src/ai_kicad/m2_bad_refdes.py",
        """
def choose(refdes: str) -> int:
    match refdes:
        case "U3":
            return 3
        case _:
            return 0
""",
    )

    report = audit_paths([module])

    assert report["pass"] is False
    assert "refdes_literal_control_flow" in _kinds(report)
