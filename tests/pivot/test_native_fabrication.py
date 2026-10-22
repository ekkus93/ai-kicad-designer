import shutil
from pathlib import Path

import pytest

from ai_kicad.pivot.cli import _model_from_fixture
from ai_kicad.pivot.fabrication import (
    deterministic_zip,
    inspect_fabrication,
    verify_review_package,
    write_manifest,
)
from ai_kicad.pivot.native import inspect_board
from ai_kicad.pivot.release import (
    ReleaseGateError,
    require_clean_native_reports,
    verify_artifact_manifest,
)
from ai_kicad.pivot.repair import bounded_repair


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/pivot/reference_555_led_flasher_v1"
BOARD = (
    ROOT
    / "fixtures/pivot/experiments/productofamerica_drc_repair_2026-10-22_run1/workspace/Reference555LedFlasher_repair.kicad_pcb"
)
FAB = (
    ROOT
    / "fixtures/pivot/experiments/direct_automation_baseline_2026-10-22_run5/workspace/fabrication"
)


def test_independent_board_observer_exact_mapping_and_copper_graph():
    report = inspect_board(_model_from_fixture(FIXTURE), BOARD)
    assert report["status"] == "PASS"
    assert report["metrics"] == {
        "track_count": 46,
        "track_length_mm": 260.9907,
        "min_track_width_mm": 0.2,
        "via_count": 0,
    }
    assert set(report["copper_connectivity"].values()) == {True}


def test_board_observer_catches_wrong_pad_net_and_missing_route(tmp_path):
    model = _model_from_fixture(FIXTURE)
    source = BOARD.read_text()
    wrong = tmp_path / "wrong.kicad_pcb"
    wrong.write_text(source.replace('(net "/VCC")', '(net "/REF")', 1))
    assert inspect_board(model, wrong)["status"] == "FAIL"
    missing = tmp_path / "missing.kicad_pcb"
    first_segment = source.index("\n\t(segment")
    depth = 0
    end = None
    for index in range(first_segment + 2, len(source)):
        depth += (source[index] == "(") - (source[index] == ")")
        if depth == 0 and source[index] == ")":
            end = index + 1
            break
    missing.write_text(source[:first_segment] + source[end:])
    assert inspect_board(model, missing)["status"] == "FAIL"


def test_board_observer_catches_wrong_footprint_and_missing_component(tmp_path):
    model = _model_from_fixture(FIXTURE)
    source = BOARD.read_text()
    wrong = tmp_path / "wrong-footprint.kicad_pcb"
    wrong.write_text(
        source.replace(
            '(footprint "Package_DIP:DIP-8_W7.62mm"', '(footprint "Package_DIP:WRONG"', 1
        )
    )
    assert inspect_board(model, wrong)["status"] == "FAIL"
    missing = tmp_path / "missing-component.kicad_pcb"
    start = source.index('(footprint "Package_DIP:DIP-8_W7.62mm"')
    depth = 0
    end = None
    for index in range(start, len(source)):
        depth += (source[index] == "(") - (source[index] == ")")
        if depth == 0:
            end = index + 1
            break
    missing.write_text(source[:start] + source[end:])
    assert inspect_board(model, missing)["status"] == "FAIL"


@pytest.mark.parametrize("mutation", ["missing", "malformed", "outline"])
def test_fabrication_negative_controls(tmp_path, mutation):
    candidate = tmp_path / mutation
    shutil.copytree(FAB, candidate)
    if mutation == "missing":
        next(candidate.glob("*.drl")).unlink()
    elif mutation == "malformed":
        next(candidate.glob("*.gtl")).write_text("not gerber")
    else:
        edge = next(candidate.glob("*Edge_Cuts.gm1"))
        edge.write_text(edge.read_text().replace("X50000000", "X49000000"))
    with pytest.raises(ValueError):
        inspect_fabrication(candidate, 50.0, 35.0)


def test_manifest_claim_boundaries_and_deterministic_zip(tmp_path):
    package = tmp_path / "package"
    shutil.copytree(FAB, package / "fabrication")
    checks = {"gerber_drill": inspect_fabrication(package / "fabrication", 50, 35)}
    manifest = write_manifest(package, "sha256:" + "1" * 64, checks, ["No physical test."])
    assert manifest["state"] == "PACKAGE_READY_FOR_REVIEW"
    assert manifest["manufacturing_readiness"] == "BLOCKED_PENDING_PROFILE_AND_OWNER_REVIEW"
    assert set(manifest["claims"].values()) == {False}
    one = deterministic_zip(package, tmp_path / "one.zip")
    two = deterministic_zip(package, tmp_path / "two.zip")
    assert one == two
    verify_artifact_manifest(package, manifest, "sha256:" + "1" * 64)
    with pytest.raises(ReleaseGateError, match="stale"):
        verify_artifact_manifest(package, manifest, "sha256:" + "2" * 64)
    artifact = next(iter(manifest["artifacts"]))
    (package / artifact).write_bytes(b"tampered")
    with pytest.raises(ReleaseGateError, match="hash"):
        verify_artifact_manifest(package, manifest, "sha256:" + "1" * 64)


def test_existing_review_zip_clean_extraction_binds_all_hashes(tmp_path):
    package = ROOT / "fixtures/pivot/experiments/reference_poc_2026-10-22_run7/review-package.zip"
    result = verify_review_package(package, tmp_path / "clean")
    assert result["status"] == "PASS"
    board = Path(result["native_project"]) / "Reference555LedFlasher.kicad_pcb"
    board.write_bytes(board.read_bytes() + b"\n")
    import json

    manifest = json.loads((tmp_path / "clean/fabrication_manifest.json").read_text())
    with pytest.raises(ReleaseGateError, match="hash"):
        verify_artifact_manifest(tmp_path / "clean", manifest, result["revision_id"])


def test_bad_native_reports_and_bounded_repair(tmp_path):
    with pytest.raises(ReleaseGateError, match="ERC"):
        require_clean_native_reports(
            {"sheets": [{"violations": [{"type": "unconnected_pin"}]}]},
            {"violations": [], "unconnected_items": []},
        )
    with pytest.raises(ReleaseGateError, match="DRC"):
        require_clean_native_reports(
            {"sheets": [{"violations": []}]},
            {"violations": [{"type": "short"}], "unconnected_items": []},
        )
    known_good = tmp_path / "known-good.txt"
    known_good.write_text("width=0.20\n")

    def propose(candidate, attempt):
        candidate.write_text(f"width={0.10 if attempt == 1 else 0.20:.2f}\n")

    result = bounded_repair(
        known_good,
        tmp_path / "attempts",
        propose,
        lambda candidate: (candidate.read_text() == "width=0.20\n", candidate.read_text().strip()),
        limit=2,
    )
    assert result.status == "PASS" and result.attempts == 2
    assert (tmp_path / "attempts/candidate-1.txt").is_file()
    assert known_good.read_text() == "width=0.20\n"


def test_bounded_repair_stops_as_blocked(tmp_path):
    known_good = tmp_path / "known-good.txt"
    known_good.write_text("preserved")
    result = bounded_repair(
        known_good,
        tmp_path / "attempts",
        lambda candidate, attempt: candidate.write_text(f"bad-{attempt}"),
        lambda candidate: (False, candidate.read_text()),
        limit=2,
    )
    assert result.status == "BLOCKED" and result.accepted is None and result.attempts == 2
