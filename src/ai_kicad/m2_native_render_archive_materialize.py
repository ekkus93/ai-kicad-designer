"""Safely materialize hash-verified historical M2h2 native SVGs for inspection.

This is historical baseline extraction, never a current-source PASS oracle.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree

from .m2_composition_native_archive import NativeRenderInventory, verify_native_render_parts


def load_native_baseline(
    root: Path, manifest_path: Path
) -> tuple[NativeRenderInventory, tuple[dict, ...]]:
    """Verify the frozen archive manifest, part bytes, and all 90 SVG digests."""
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != "m2h2.human-composition-native-render-baseline.1":
        raise ValueError("unexpected historical native-render manifest schema")
    records = manifest.get("archive_parts")
    if not isinstance(records, list) or not records:
        raise ValueError("historical native-render manifest must list archive parts")

    resolved_root = root.resolve()
    parts: list[dict] = []
    seen_paths: set[str] = set()
    for item in records:
        if not isinstance(item, dict):
            raise TypeError("invalid native-render part manifest entry")
        relative = item.get("path")
        digest = item.get("sha256")
        if not isinstance(relative, str) or not isinstance(digest, str):
            raise TypeError("missing native-render part identity")
        source = (resolved_root / relative).resolve()
        if not source.is_relative_to(resolved_root) or not source.is_file():
            raise ValueError("native-render part is outside the verified repository root")
        if relative in seen_paths:
            raise ValueError("duplicate native-render part path")
        seen_paths.add(relative)
        payload = source.read_bytes()
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ValueError(f"native-render archive part digest mismatch: {relative}")
        part = json.loads(payload)
        if not isinstance(part, dict):
            raise TypeError("native-render part must be an object")
        parts.append(part)

    inventory = verify_native_render_parts(parts)
    if (
        inventory.qualification_head != manifest.get("historical_qualification_sha")
        or inventory.render_count != manifest.get("native_svg_count")
        or inventory.inventory_sha256 != manifest.get("sorted_case_svg_sha256_inventory_sha256")
    ):
        raise ValueError("native-render manifest inventory does not match verified parts")
    return inventory, tuple(parts)


def materialize_native_baseline(
    root: Path,
    manifest_path: Path,
    destination: Path,
    *,
    cases: tuple[str, ...] | None = None,
) -> NativeRenderInventory:
    """Write selected verified baseline SVGs without replacing existing evidence.

    Verify the complete archive before writing anything. The resulting inspection
    inventory is explicitly historical and never asserts aesthetic acceptance.
    """
    inventory, parts = load_native_baseline(root, manifest_path)
    available = dict(inventory.case_hashes)
    selected = set(available) if cases is None else set(cases)
    if not selected or selected - available.keys():
        raise ValueError("requested native-render case is missing from verified archive")
    if any(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", case) is None for case in selected):
        raise ValueError("invalid native-render case filename")

    # Decode and validate SVG structure before creating the destination.
    svg_by_case: dict[str, bytes] = {}
    for part in parts:
        for render in part["renders"]:
            case = render["case"]
            if case not in selected:
                continue
            svg = gzip.decompress(base64.b64decode(render["data"], validate=True))
            if hashlib.sha256(svg).hexdigest() != available[case]:
                raise ValueError("native SVG digest changed after archive verification")
            try:
                element = ElementTree.fromstring(svg)
            except ElementTree.ParseError as exc:
                raise ValueError(f"invalid historical SVG XML for {case}") from exc
            if element.tag.rsplit("}", 1)[-1] != "svg":
                raise ValueError(f"invalid historical SVG root for {case}")
            svg_by_case[case] = svg

    destination.mkdir(parents=True, exist_ok=False)
    entries = []
    for case in sorted(selected):
        filename = f"{case}.svg"
        (destination / filename).write_bytes(svg_by_case[case])
        entries.append({"case_id": case, "svg_sha256": available[case], "file": filename})
    report = {
        "schema_version": "m2h2.historical-native-svg-extraction.1",
        "status": "historical_baseline_only_not_current_qualification",
        "historical_qualification_sha": inventory.qualification_head,
        "complete_archive_svg_count": inventory.render_count,
        "complete_archive_inventory_sha256": inventory.inventory_sha256,
        "native_render_engineering_inspection_completed": False,
        "extracted_cases": entries,
    }
    (destination / "inspection_inventory.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return inventory
