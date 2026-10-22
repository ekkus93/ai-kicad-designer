import json
import re
import shutil
from pathlib import Path

import pytest

from ai_kicad.pivot.cli import _model_from_fixture
from ai_kicad.pivot.native import NativeObservationError, inspect_board, inspect_schematic
from ai_kicad.pivot.release import (
    ReleaseGateError,
    require_clean_native_reports,
    verify_artifact_manifest,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/pivot/reference_555_led_flasher_v1"
BOARD = FIXTURE / "native_project/Reference555LedFlasher.kicad_pcb"
REFERENCE_RUN = ROOT / "fixtures/pivot/experiments/reference_poc_2026-10-22_run16"


def test_pin_open_short_route_and_wrong_pad_fail_native_observation(tmp_path):
    model = _model_from_fixture(FIXTURE)
    original = BOARD.read_text()
    cases = {
        "open": ('(net "/OUT")', ""),
        "short": ('(net "/OUT")', '(net "/REF")'),
        "wrong_pad": ('(pad "1" thru_hole rect', '(pad "9" thru_hole rect'),
    }
    results = {}
    for case, (old, new) in cases.items():
        assert old in original
        candidate = tmp_path / f"{case}.kicad_pcb"
        candidate.write_text(original.replace(old, new, 1))
        try:
            report = inspect_board(model, candidate)
            results[case] = report["status"] == "FAIL"
        except ValueError:
            results[case] = True
    assert results == {"open": True, "short": True, "wrong_pad": True}


def test_duplicate_hierarchical_instance_reference_is_a_typed_hard_failure(tmp_path):
    from ai_kicad.pivot.native import NativeObservationError

    model = _model_from_fixture(FIXTURE)
    source = BOARD.read_text()
    assert '(property "Reference" "R2"' in source
    candidate = tmp_path / "duplicate-reference.kicad_pcb"
    candidate.write_text(source.replace('(property "Reference" "R2"', '(property "Reference" "R1"', 1))
    with pytest.raises(NativeObservationError, match="duplicate footprint reference"):
        inspect_board(model, candidate)


def test_schematic_observer_rejects_hierarchy_instead_of_merging_instance_paths(tmp_path):
    source = FIXTURE / "native_project/Reference555LedFlasher.kicad_sch"
    candidate = tmp_path / "hierarchical.kicad_sch"
    schematic = source.read_text().rstrip()
    assert schematic.endswith(")")
    candidate.write_text(
        schematic[:-1]
        + '\n  (sheet (uuid "8d0fdf11-60fb-4daf-ae40-d2cba09c2601") '
        + '(property "Sheetname" "Child") (property "Sheetfile" "child.kicad_sch"))\n)\n'
    )
    with pytest.raises(NativeObservationError, match="hierarchical schematic sheets"):
        inspect_schematic(
            json.loads((FIXTURE / "design.json").read_text()),
            candidate,
            REFERENCE_RUN / "reports/netlist.xml",
        )
    path_match = re.search(r'\(path "([^"]+)"', schematic)
    assert path_match
    duplicate = tmp_path / "repeated-instance-path.kicad_sch"
    duplicate.write_text(
        schematic.replace(path_match.group(1), path_match.group(1) + "/child", 1)
    )
    with pytest.raises(NativeObservationError, match="outside the root sheet"):
        inspect_schematic(
            json.loads((FIXTURE / "design.json").read_text()),
            duplicate,
            REFERENCE_RUN / "reports/netlist.xml",
        )


def test_stale_board_and_wrong_revision_manifest_fail(tmp_path):
    manifest = json.loads((REFERENCE_RUN / "fabrication_manifest.json").read_text())
    candidate = tmp_path / "package"
    shutil.copytree(REFERENCE_RUN, candidate, ignore=shutil.ignore_patterns("workflow", "config"))
    board = candidate / "editable_project/Reference555LedFlasher.kicad_pcb"
    board.write_bytes(board.read_bytes() + b"\n")
    with pytest.raises(ReleaseGateError, match="hash"):
        verify_artifact_manifest(candidate, manifest, manifest["revision_id"])
    with pytest.raises(ReleaseGateError, match="stale"):
        verify_artifact_manifest(candidate, manifest, "sha256:" + "f" * 64)


def test_bad_drc_and_phase_export_are_blocked(tmp_path):
    with pytest.raises(ReleaseGateError, match="DRC"):
        require_clean_native_reports(
            {"sheets": [{"violations": []}]},
            {"violations": [{"type": "clearance"}], "unconnected_items": []},
        )
    from ai_kicad.pivot.controller import NotAuthorized, WorkflowController

    controller = WorkflowController(tmp_path / "workspace")
    with pytest.raises(NotAuthorized):
        controller.dispatch(
            "prepare_fabrication_package",
            {"expected_revision": None, "idempotency_key": "hidden-export"},
        )
