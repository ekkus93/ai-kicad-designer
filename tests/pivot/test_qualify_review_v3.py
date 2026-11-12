from pathlib import Path

from ai_kicad.pivot.schematic_review import POWER_SYMBOL_RAIL_GUIDANCE, rail_guidance
from tools.pivot.qualify_review_v3 import HISTORICAL, image_only, score


class _Assessment:
    def __init__(self, checks: dict):
        self.report = {
            "checks": checks,
            "diagnostics": ["power symbols touch other drawing items"],
            "intended_circuit": {"name": "x"},
            "field_inventory": [],
            "terminal_inventory": [],
        }

    @property
    def passed(self) -> bool:
        return all(value == "PASS" for value in self.report["checks"].values())


def test_image_only_withholds_outcomes_but_keeps_power_symbol_guidance(monkeypatch):
    import tools.pivot.qualify_review_v3 as harness

    monkeypatch.setattr(harness, "replace", lambda assessment, report: report)
    checks = {"erc": "PASS", "rail_presentation": "FAIL", "power_symbol_clearance": "PASS"}
    report = image_only(_Assessment(checks))
    assert report["checks"] == {name: "WITHHELD" for name in checks}
    assert "diagnostics" not in report
    assert rail_guidance(report["checks"]) == POWER_SYMBOL_RAIL_GUIDANCE


def test_score_separates_defect_naming_from_false_rail_claims():
    case = {"assessment": _Assessment({"erc": "PASS"}), "cue": r"vminus.*close"}
    row = {
        "decision": "revise",
        "issues": ["VMINUS text is too close to C2", "Rails rely on text labels only"],
        "actions": [],
    }
    score(row, case)
    assert row["model_rejects"] and row["names_defect"] and row["false_rail_claim"]
    assert not row["loop_would_accept"]
    accepted = {"decision": "accept", "issues": [], "actions": []}
    score(accepted, case)
    assert accepted["loop_would_accept"] and not accepted["names_defect"]


def test_historical_sources_exist():
    root = Path(__file__).resolve().parents[2] / "fixtures/pivot/experiments"
    for item in HISTORICAL:
        assert (root / item["source"]).is_dir(), item["source"]
