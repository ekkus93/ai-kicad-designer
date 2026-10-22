"""Tamper and path-safety checks for immutable pivot fixture manifests."""

import hashlib
import json
from pathlib import Path

from tools.pivot.verify_fixture import verify_manifest
from tools.pivot.experiment_paths import create_experiment_dir
from tools.pivot.verify_native_project import verify_native_project

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
