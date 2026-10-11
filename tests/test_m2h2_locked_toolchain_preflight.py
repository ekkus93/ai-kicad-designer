"""Regression coverage for fail-closed locked toolchain preflight."""

import hashlib
import subprocess

import check_m2h2_locked_toolchain as tool


def _lock(tmp_path, content: bytes = b"toolchain-binary") -> dict:
    executable = tmp_path / "AppRun"
    executable.write_bytes(content)
    library = tmp_path / "sharun"
    library.write_bytes(b"pinned-library")
    return {
        "platform": {"os": "test-os", "architecture": "x86_64"},
        "executables": [
            {
                "id": "kicad-cli",
                "path": str(executable),
                "version": "10.0.6",
                "file_sha256": hashlib.sha256(content).hexdigest(),
            },
        ],
        "libraries": [
            {
                "id": "sharun",
                "path": str(library),
                "file_sha256": hashlib.sha256(b"pinned-library").hexdigest(),
            },
        ],
    }


def test_exact_pins_and_version_are_accepted(tmp_path, monkeypatch) -> None:
    lock = _lock(tmp_path)
    monkeypatch.setattr(
        tool.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "10.0.6\n", ""),
    )
    report = tool.inspect_lock(lock, {"os": "test-os", "architecture": "x86_64"})
    assert report["ok"]
    assert not report["mismatches"]
    assert all(entry["sha256_matches"] for entry in report["files"])


def test_deleted_volatile_library_fails_closed(tmp_path, monkeypatch) -> None:
    lock = _lock(tmp_path)
    (tmp_path / "sharun").unlink()
    monkeypatch.setattr(
        tool.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "10.0.6\n", ""),
    )
    report = tool.inspect_lock(lock, {"os": "test-os", "architecture": "x86_64"})
    assert not report["ok"]
    assert report["mismatches"][0]["id"] == "sharun"
    assert report["mismatches"][0]["actual_sha256"] is None


def test_modified_pinned_binary_is_not_accepted(tmp_path, monkeypatch) -> None:
    lock = _lock(tmp_path)
    (tmp_path / "AppRun").write_bytes(b"unverified")

    def forbid_probe(*_args, **_kwargs):
        raise AssertionError("unverified launcher must not be executed")

    monkeypatch.setattr(tool.subprocess, "run", forbid_probe)
    report = tool.inspect_lock(lock, {"os": "test-os", "architecture": "x86_64"})
    assert not report["ok"]
    assert report["mismatches"][0]["id"] == "kicad-cli"


def test_incorrect_version_and_platform_are_rejected(tmp_path, monkeypatch) -> None:
    lock = _lock(tmp_path)
    monkeypatch.setattr(
        tool.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "10.0.5\n", ""),
    )
    report = tool.inspect_lock(lock, {"os": "other-os", "architecture": "x86_64"})
    assert not report["ok"]
    assert {issue["id"] for issue in report["mismatches"]} == {"platform.os", "version_probe"}
