"""Keep source-level audit findings authoritative in locked M2h2 qualification."""

import pytest
import run_m2g2_qualification as m2g2
from run_m2h2_qualification import qualification_passed


def test_policy_assertion_is_not_cp_sat_usage(tmp_path, monkeypatch):
    source_dir = tmp_path / "src" / "ai_kicad"
    source_dir.mkdir(parents=True)
    (source_dir / "m2_hard_gates.py").write_text('EXPECTED_HARD_GATES = {"cp_sat_absent": True}\n')
    monkeypatch.setattr(m2g2, "ROOT", tmp_path)
    result = m2g2._anti_overfitting_audit()
    assert result["pass"]
    assert not result["cp_sat_introduced"]
    assert result["findings"] == []


@pytest.mark.parametrize(
    "source",
    ["import ortools.sat.python.cp_model\n", "from cp_sat import Solver\n"],
)
def test_real_solver_dependencies_are_rejected(tmp_path, monkeypatch, source):
    source_dir = tmp_path / "src" / "ai_kicad"
    source_dir.mkdir(parents=True)
    (source_dir / "m2_solver.py").write_text(source)
    monkeypatch.setattr(m2g2, "ROOT", tmp_path)
    result = m2g2._anti_overfitting_audit()
    assert not result["pass"]
    assert result["cp_sat_introduced"]
    assert len(result["findings"]) == 1


def test_qualification_pass_requires_audits_and_negative_case():
    report = {
        "total": 56,
        "accepted": 56,
        "negative_v3_8_accepted": True,
        "historical_preservation": {"pass": True},
        "anti_overfitting": {"pass": True},
    }
    assert qualification_passed(report)
    for update in (
        {"total": 55, "accepted": 55},
        {"accepted": 55},
        {"negative_v3_8_accepted": False},
        {"historical_preservation": {"pass": False}},
        {"anti_overfitting": {"pass": False}},
    ):
        rejected = {**report, **update}
        assert not qualification_passed(rejected)
