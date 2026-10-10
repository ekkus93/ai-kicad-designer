"""Regression coverage for real-tool mixed-branch current-source validation."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from run_m2h2_current_regressions import (  # noqa: E402
    CASES,
    _case_errors,
    _native_route_diagnostic,
    _reference_nets,
)


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
        "layout": {
            "unrelated_wire_crossing_count": 0,
            "wire_through_body_count": 0,
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


def test_native_route_diagnostic_reads_emitted_wire_geometry_without_acceptance() -> None:
    route = (((0, 0), (10, 0)), ((10, 0), (10, 10)), ((10, 10), (0, 10)))
    report = _native_route_diagnostic({"wires": route})
    reordered = _native_route_diagnostic({"wires": (route[2], route[0], route[1])})
    assert report == reordered
    assert report["routed_length_nm"] == 30
    assert report["wire_segment_count"] == 3
    assert report["bend_count"] == 2
    assert report["u_shaped_detours"] >= 1
    assert report["acceptance"] == "diagnostic_only"
    assert report["provenance"] == "parsed_native_kicad_schematic_wires"


def test_native_route_diagnostic_identifies_straight_wires() -> None:
    report = _native_route_diagnostic({"wires": [((0, 0), (10, 0))]})
    assert report["routed_length_nm"] == 10
    assert report["bend_count"] == 0
    assert report["u_shaped_detours"] == 0


def test_current_regression_gate_rejects_route_crossing_or_body_intrusion() -> None:
    design = {"nets": [{"id": "INPUT"}]}
    base = {
        "electrical": {"status": "pass", "diagnostics": []},
        "erc": {"sheets": [{"violations": []}]},
        "composition": {
            "obligation_certificate": {
                "serialized_scene_verified": "pass",
                "net_graph_witnesses": [],
            }
        },
        "layout": {
            "unrelated_wire_crossing_count": 0,
            "wire_through_body_count": 0,
        },
    }

    crossing = {
        **base,
        "layout": {**base["layout"], "unrelated_wire_crossing_count": 1},
    }
    body = {
        **base,
        "layout": {**base["layout"], "wire_through_body_count": 1},
    }
    assert any(
        "unrelated_wire_crossing_count=1" in error for error in _case_errors("x", design, crossing)
    )
    assert any("wire_through_body_count=1" in error for error in _case_errors("x", design, body))
