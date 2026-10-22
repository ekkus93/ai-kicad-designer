"""Tamper and path-safety checks for immutable pivot fixture manifests."""

import hashlib
import json
from pathlib import Path

from tools.pivot.verify_fixture import verify_manifest
from tools.pivot.experiment_paths import create_experiment_dir
from tools.pivot.verify_native_project import verify_native_project
from tools.pivot.redraw_external_ports import redraw_external_ports
from tools.pivot.connect_led_branch import connect_led_branch

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "fixtures/pivot/reference_555_led_flasher_v1/manifest.json"


def test_reference_fixture_manifest_matches_frozen_artifacts() -> None:
    assert verify_manifest(MANIFEST, ROOT) == []


def test_modified_artifact_is_reported_as_tampered(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    artifact = fixture / "input.json"
    artifact.write_text("original")
    manifest = fixture / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "pivot-fixture-manifest.v1",
                "input_hashes": {"input.json": hashlib.sha256(b"original").hexdigest()},
                "toolchain_lock": "toolchain.lock",
                "toolchain_lock_sha256": hashlib.sha256(b"lock").hexdigest(),
                "m2b_asset_lock": "m2b.lock",
                "m2b_asset_lock_sha256": hashlib.sha256(b"lock").hexdigest(),
                "m2a_asset_lock": "m2a.lock",
                "m2a_asset_lock_sha256": hashlib.sha256(b"lock").hexdigest(),
            }
        )
    )
    artifact.write_text("changed")
    assert "hash mismatch: input.json" in verify_manifest(manifest, tmp_path)


def test_manifest_cannot_read_outside_repository(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    fixture = repo / "fixture"
    fixture.mkdir()
    outside = tmp_path / "outside"
    outside.write_text("secret")
    manifest = fixture / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "pivot-fixture-manifest.v1",
                "input_hashes": {"../../outside": hashlib.sha256(b"secret").hexdigest()},
                "toolchain_lock": "missing",
                "toolchain_lock_sha256": "0" * 64,
                "m2b_asset_lock": "missing",
                "m2b_asset_lock_sha256": "0" * 64,
                "m2a_asset_lock": "missing",
                "m2a_asset_lock_sha256": "0" * 64,
            }
        )
    )
    errors = verify_manifest(manifest, repo)
    assert "path escapes repository: ../../outside" in errors


def test_experiment_directory_is_new_and_outside_protected_fixture_tree(tmp_path: Path) -> None:
    first = create_experiment_dir(tmp_path, "backend-smoke-run-001")
    assert first == tmp_path / "fixtures/pivot/experiments/backend-smoke-run-001"
    try:
        create_experiment_dir(tmp_path, "backend-smoke-run-001")
    except FileExistsError:
        pass
    else:
        raise AssertionError("existing experiment output was overwritten")
    assert not first.is_relative_to(tmp_path / "fixtures/m2h2")


def test_native_project_reference_files_are_locked_and_tamper_evident(tmp_path: Path) -> None:
    native = ROOT / "fixtures/pivot/reference_555_led_flasher_v1/native_project"
    assert verify_native_project(native) == []
    target = tmp_path / "native"
    import shutil

    shutil.copytree(native, target)
    (target / "Reference555LedFlasher.kicad_pcb").write_bytes(b"tampered")
    assert any("hash mismatch" in error for error in verify_native_project(target))


def test_redrawn_fixture_preserves_v1_and_is_reproducible(tmp_path: Path) -> None:
    v1 = ROOT / "fixtures/pivot/reference_555_led_flasher_v1/native_project"
    v2 = ROOT / "fixtures/pivot/reference_555_led_flasher_v2/native_project"
    assert verify_native_project(v1) == []
    assert verify_native_project(v2) == []
    output = tmp_path / "Reference555LedFlasher.kicad_sch"
    redraw_external_ports(v1 / "Reference555LedFlasher.kicad_sch", output)
    assert output.read_bytes() == (v2 / "Reference555LedFlasher.kicad_sch").read_bytes()


def test_redrawn_fixture_manifest_is_locked() -> None:
    manifest = ROOT / "fixtures/pivot/reference_555_led_flasher_v2/manifest.json"
    assert verify_manifest(manifest, ROOT) == []


def test_led_branch_redraw_is_reproducible_and_fixture_is_locked(tmp_path: Path) -> None:
    v2 = ROOT / "fixtures/pivot/reference_555_led_flasher_v2/native_project"
    v3 = ROOT / "fixtures/pivot/reference_555_led_flasher_v3/native_project"
    assert verify_native_project(v3) == []
    output = tmp_path / "Reference555LedFlasher.kicad_sch"
    connect_led_branch(v2 / "Reference555LedFlasher.kicad_sch", output)
    assert output.read_bytes() == (v3 / "Reference555LedFlasher.kicad_sch").read_bytes()
    assert verify_manifest(ROOT / "fixtures/pivot/reference_555_led_flasher_v3/manifest.json", ROOT) == []
