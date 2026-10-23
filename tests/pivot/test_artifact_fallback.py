"""Failure-path coverage for durable local Actions artifact preservation."""

import hashlib
import json
from pathlib import Path

import pytest

from tools.pivot.preserve_artifact_fallback import preserve


def test_upload_failure_fallback_is_content_addressed_and_idempotent(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    output = root / "fixtures/m2h2/qualification-run"
    output.mkdir(parents=True)
    (output / "report.json").write_text('{"status":"PASS"}\n')
    (output / "nested.txt").write_text("rendered evidence\n")

    kwargs = {
        "root": root,
        "destination": root / "fixtures/pivot/artifact-fallbacks",
        "inputs": [Path("fixtures/m2h2/qualification-run")],
        "source_sha": "a" * 40,
        "run_url": "https://github.com/example/repo/actions/runs/123",
    }
    first = preserve(**kwargs)
    second = preserve(**kwargs)
    repeated_run = preserve(
        **{
            **kwargs,
            "run_url": "https://github.com/example/repo/actions/runs/124",
        }
    )

    assert first["content_sha256"] == second["content_sha256"]
    assert first["reused"] is False
    assert second["reused"] is True
    assert repeated_run["run_urls"] == [
        "https://github.com/example/repo/actions/runs/123",
        "https://github.com/example/repo/actions/runs/124",
    ]
    stored = Path(first["path"])
    manifest = json.loads((stored / "manifest.json").read_text())
    assert manifest["schema_version"] == "pivot-artifact-fallback.v1"
    assert (
        manifest["files"]["fixtures/m2h2/qualification-run/report.json"]
        == hashlib.sha256(b'{"status":"PASS"}\n').hexdigest()
    )
    assert (
        "Workflow run: https://github.com/example/repo/actions/runs/124"
        in (stored / "summary.md").read_text()
    )


def test_corrupt_content_addressed_copy_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    output = root / "run"
    output.mkdir(parents=True)
    (output / "evidence.txt").write_text("proof")
    kwargs = {
        "root": root,
        "destination": root / "fallback",
        "inputs": [Path("run")],
        "source_sha": "b" * 40,
        "run_url": "https://github.com/example/repo/actions/runs/456",
    }
    first = preserve(**kwargs)
    (Path(first["path"]) / "files/run/evidence.txt").write_text("tampered")
    with pytest.raises(ValueError, match="stored artifact hash mismatch"):
        preserve(**kwargs)


def test_symlinked_artifact_input_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.write_text("secret")
    (root / "link").symlink_to(outside)
    with pytest.raises(ValueError, match="must not be a symlink"):
        preserve(
            root=root,
            destination=root / "fallback",
            inputs=[Path("link")],
            source_sha="c" * 40,
            run_url="https://github.com/example/repo/actions/runs/789",
        )
