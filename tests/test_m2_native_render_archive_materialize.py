"""Baseline-native extraction must preserve exact bytes and reject tampering."""

import base64
import gzip
import hashlib
import json

import pytest

from ai_kicad.m2_composition_native_archive import verify_native_render_parts
from ai_kicad.m2_native_render_archive_materialize import (
    load_native_baseline,
    materialize_native_baseline,
)


def _archive(tmp_path):
    qualification_head = "a" * 40
    parts = []
    for number, (case, svg) in enumerate(
        (
            ("base__linear", b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'),
            ("i4__mixed", b'<svg xmlns="http://www.w3.org/2000/svg"><g/></svg>'),
        ),
        start=1,
    ):
        parts.append(
            {
                "schema": "m2h2.native-render-archive.1",
                "qualification_head": qualification_head,
                "archive_part": number,
                "archive_parts": 2,
                "renders": [
                    {
                        "case": case,
                        "encoding": "gzip+base64",
                        "svg_sha256": hashlib.sha256(svg).hexdigest(),
                        "data": base64.b64encode(gzip.compress(svg, mtime=0)).decode(),
                    }
                ],
            }
        )
    details = verify_native_render_parts(parts)
    entries = []
    for number, part in enumerate(parts, start=1):
        name = f"part{number:02d}.json"
        data = json.dumps(part, sort_keys=True).encode()
        (tmp_path / name).write_bytes(data)
        entries.append({"path": name, "sha256": hashlib.sha256(data).hexdigest()})
    manifest = {
        "schema_version": "m2h2.human-composition-native-render-baseline.1",
        "historical_qualification_sha": qualification_head,
        "native_svg_count": 2,
        "sorted_case_svg_sha256_inventory_sha256": details.inventory_sha256,
        "archive_parts": entries,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return manifest_path, manifest


def test_extracts_selected_verified_svg_and_non_acceptance_manifest(tmp_path):
    manifest, _ = _archive(tmp_path)
    output = tmp_path / "extracted"
    inventory = materialize_native_baseline(tmp_path, manifest, output, cases=("i4__mixed",))
    assert inventory.render_count == 2
    assert sorted(path.name for path in output.iterdir()) == [
        "i4__mixed.svg",
        "inspection_inventory.json",
    ]
    assert output.joinpath("i4__mixed.svg").read_bytes().endswith(b"<g/></svg>")
    record = json.loads(output.joinpath("inspection_inventory.json").read_text())
    assert record["status"] == "historical_baseline_only_not_current_qualification"
    assert record["native_render_engineering_inspection_completed"] is False
    assert record["extracted_cases"][0]["case_id"] == "i4__mixed"
    with pytest.raises(FileExistsError):
        materialize_native_baseline(tmp_path, manifest, output)


def test_rejects_tampered_part_without_creating_output(tmp_path):
    manifest, _ = _archive(tmp_path)
    (tmp_path / "part01.json").write_text("tampered")
    out = tmp_path / "must_not_exist"
    with pytest.raises(ValueError, match="digest mismatch"):
        materialize_native_baseline(tmp_path, manifest, out)
    assert not out.exists()


def test_rejects_manifest_inventory_mismatch(tmp_path):
    manifest_path, manifest = _archive(tmp_path)
    manifest["native_svg_count"] = 3
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="inventory does not match"):
        load_native_baseline(tmp_path, manifest_path)


def test_rejects_archive_part_path_traversal(tmp_path):
    manifest_path, manifest = _archive(tmp_path)
    manifest["archive_parts"][0]["path"] = "../outside.json"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="outside the verified repository root"):
        load_native_baseline(tmp_path, manifest_path)


def test_unknown_selection_does_not_create_output(tmp_path):
    manifest, _ = _archive(tmp_path)
    out = tmp_path / "not_created"
    with pytest.raises(ValueError, match="requested native-render case"):
        materialize_native_baseline(tmp_path, manifest, out, cases=("unknown",))
    assert not out.exists()


def test_real_preserved_archive_can_extract_mixed_falsification_seed(tmp_path):
    """Exercise the actual frozen ten-part archive, not just a synthetic fixture."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    manifest = (
        root / "fixtures/m2h2/human_composition_baseline_2026-10-08/"
        "native_render_archive_manifest_42ab8452.json"
    )
    inventory, parts = load_native_baseline(root, manifest)
    assert inventory.render_count == 90
    assert len(parts) == 10
    assert "i4__b2_mixed" in dict(inventory.case_hashes)

    output = tmp_path / "mixed"
    materialize_native_baseline(root, manifest, output, cases=("i4__b2_mixed",))
    svg = output.joinpath("i4__b2_mixed.svg").read_bytes()
    assert b"<svg" in svg[:4096]
    receipt = json.loads(output.joinpath("inspection_inventory.json").read_text())
    assert receipt["complete_archive_svg_count"] == 90
    assert receipt["native_render_engineering_inspection_completed"] is False
