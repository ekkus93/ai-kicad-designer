"""Historical native SVG extraction validation without visual acceptance claims."""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from extract_m2h2_baseline_renders import extract_baseline_renders  # noqa: E402


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "repo"
    part_path = root / "fixtures" / "m2h2" / "part01.json"
    part_path.parent.mkdir(parents=True)
    records = []
    for case in ("base__linear", "i4__mixed"):
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 210 140">'
            f"<title>{case}</title></svg>"
        ).encode()
        records.append(
            {
                "case": case,
                "svg_sha256": _hash(svg),
                "encoding": "gzip+base64",
                "data": base64.b64encode(gzip.compress(svg, mtime=0)).decode(),
            }
        )
    part = {
        "schema": "m2h2.native-render-archive.1",
        "qualification_head": "historical-fixture",
        "archive_part": 1,
        "archive_parts": 1,
        "renders": records,
    }
    raw = json.dumps(part).encode()
    part_path.write_bytes(raw)
    manifest = {
        "historical_qualification_sha": "historical-fixture",
        "native_svg_count": 2,
        "sorted_case_svg_sha256_inventory_sha256": "historical-inventory-fixture",
        "archive_parts": [{"path": "fixtures/m2h2/part01.json", "sha256": _hash(raw)}],
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return root, manifest_path, part_path


def test_extract_checks_all_hashes_and_produces_deterministic_selected_index(
    tmp_path: Path,
) -> None:
    root, manifest, _ = _fixture(tmp_path)
    output = tmp_path / "out"
    result = extract_baseline_renders(root, manifest, output, ("i4__mixed",))
    assert result["verified_svg_count"] == 2
    assert result["extracted_svg_count"] == 1
    assert result["evidence_scope"] == "historical_archive_only_no_composition_acceptance"
    assert (output / "i4__mixed.svg").is_file()
    assert not (output / "base__linear.svg").exists()
    assert [entry["case"] for entry in result["entries"]] == ["base__linear", "i4__mixed"]
    assert result["entries"][1]["canvas"]["viewBox"] == "0 0 210 140"
    assert json.loads((output / "index.json").read_text()) == result


def test_archive_part_digest_mismatch_is_rejected_without_output(tmp_path: Path) -> None:
    root, manifest, part = _fixture(tmp_path)
    part.write_bytes(part.read_bytes() + b" ")
    output = tmp_path / "out"
    with pytest.raises(ValueError, match="part SHA-256 mismatch"):
        extract_baseline_renders(root, manifest, output)
    assert not output.exists()


def test_svg_digest_mismatch_is_rejected_after_verified_part_digest(tmp_path: Path) -> None:
    root, manifest_path, part_path = _fixture(tmp_path)
    part = json.loads(part_path.read_text())
    part["renders"][1]["svg_sha256"] = "0" * 64
    raw = json.dumps(part).encode()
    part_path.write_bytes(raw)
    manifest = json.loads(manifest_path.read_text())
    manifest["archive_parts"][0]["sha256"] = _hash(raw)
    manifest_path.write_text(json.dumps(manifest))
    output = tmp_path / "out"
    with pytest.raises(ValueError, match="SVG digest mismatch"):
        extract_baseline_renders(root, manifest_path, output)
    assert not output.exists()


def test_unsafe_case_path_and_missing_case_are_rejected(tmp_path: Path) -> None:
    root, manifest_path, part_path = _fixture(tmp_path)
    with pytest.raises(ValueError, match="unrecognized archived case"):
        extract_baseline_renders(root, manifest_path, tmp_path / "missing", ("absent",))
    part = json.loads(part_path.read_text())
    part["renders"][0]["case"] = "../bad"
    raw = json.dumps(part).encode()
    part_path.write_bytes(raw)
    manifest = json.loads(manifest_path.read_text())
    manifest["archive_parts"][0]["sha256"] = _hash(raw)
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="invalid archived case ID"):
        extract_baseline_renders(root, manifest_path, tmp_path / "unsafe")
