"""Regression coverage for real-tool mixed-branch current-source validation."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from run_m2h2_current_regressions import CASES, _case_errors, _reference_nets  # noqa: E402


def test_mixed_branch_is_in_locked_current_source_regressions() -> None:
    assert CASES["i4__b2_mixed"].relative_to(ROOT).as_posix() == (
        "fixtures/m2h2/interaction/i4/b2_mixed.json"
    )


def test_reference_free_design_does_not_invent_vref() -> None:
    design = {"nets": [{"id": "INPUT"}, {"id": "OUTPUT_1"}]}
    assert _reference_nets(design) == []
    signature = {
        "electrical": {"status": "pass", "diagnostics": []},
        "erc": {"sheets": [{"violations": []}]},
        "composition": {
            "obligation_certificate": {
                "serialized_scene_verified": "pass",
                "net_graph_witnesses": [],
            }
        },
    }
    assert _case_errors("i4__b2_mixed", design, signature) == []


def test_existing_reference_fallback_is_preserved() -> None:
    assert _reference_nets({"nets": [{"id": "VREF"}]}) == ["VREF"]
    assert _reference_nets(
        {
            "relationships": [{"kind": "reference_divider", "local": "BIAS"}],
            "nets": [{"id": "BIAS"}],
        }
    ) == ["BIAS"]
