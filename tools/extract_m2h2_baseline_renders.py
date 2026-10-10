"""Verify and extract immutable M2h2 historical native KiCad SVG renders.

Historical electrical PASS is retained. Extracting and indexing SVGs is *not*
independent composition observation, visual engineering inspection, or a
current-source/five-run qualification result.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import gzip
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    Path("fixtures/m2h2/human_composition_baseline_2026-10-08")
    / "native_render_archive_manifest_42ab8452.json"
)
CASE_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,180}\Z")
ARCHIVE_SCHEMA = "m2h2.native-render-archive.1"
SVG_TAG = "{http://www.w3.org/2000/svg}svg"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_relative(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe archived path: {relative!r}")
    target = (root / path).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"archived path escapes root: {relative!r}")
    return target


def _decode_svg(record: dict) -> tuple[bytes, dict[str, str]]:
    case_id = record["case"]
    if not isinstance(case_id, str) or CASE_PATTERN.fullmatch(case_id) is None:
        raise ValueError(f"invalid archived case ID: {case_id!r}")
    if record.get("encoding") != "gzip+base64":
        raise ValueError(f"unsupported archived encoding for {case_id}")
    try:
        compressed = base64.b64decode(record["data"], validate=True)
        svg = gzip.decompress(compressed)
    except (ValueError, binascii.Error, OSError) as exc:
        raise ValueError(f"invalid archived SVG for {case_id}") from exc
    actual_sha = _sha256(svg)
    if actual_sha != record["svg_sha256"]:
        raise ValueError(f"SVG digest mismatch for {case_id}")
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as exc:
        raise ValueError(f"invalid SVG XML for {case_id}") from exc
    if root.tag != SVG_TAG:
        raise ValueError(f"unexpected SVG root element for {case_id}: {root.tag!r}")
    canvas = {key: root.attrib.get(key, "") for key in ("viewBox", "width", "height")}
    return svg, canvas


def extract_baseline_renders(
    repo_root: Path,
    manifest_path: Path,
    output_dir: Path,
    selected_cases: tuple[str, ...] = (),
) -> dict:
    """Validate *all* archive parts and SVGs before writing selected outputs."""
    repo_root = repo_root.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verified: dict[str, tuple[bytes, dict]] = {}
    part_count = len(manifest["archive_parts"])
    if not part_count:
        raise ValueError("historical archive manifest has no parts")

    for index, item in enumerate(manifest["archive_parts"], start=1):
        path = _safe_relative(repo_root, item["path"])
        data = path.read_bytes()
        if _sha256(data) != item["sha256"]:
            raise ValueError(f"archive part SHA-256 mismatch: {item['path']}")
        part = json.loads(data)
        if part.get("schema") != ARCHIVE_SCHEMA:
            raise ValueError(f"unexpected native archive schema: {item['path']}")
        if part.get("archive_part") != index or part.get("archive_parts") != part_count:
            raise ValueError(f"archive part numbering/count mismatch: {item['path']}")
        if part.get("qualification_head") != manifest["historical_qualification_sha"]:
            raise ValueError(f"archive qualification SHA mismatch: {item['path']}")
        for record in part["renders"]:
            svg, canvas = _decode_svg(record)
            case_id = record["case"]
            if case_id in verified:
                raise ValueError(f"duplicate archived case: {case_id}")
            verified[case_id] = (
                svg,
                {
                    "case": case_id,
                    "svg_sha256": record["svg_sha256"],
                    "archive_part": index,
                    "archive_path": item["path"],
                    "canvas": canvas,
                    "size_bytes": len(svg),
                },
            )
    if len(verified) != manifest["native_svg_count"]:
        raise ValueError("archive SVG count differs from preserved baseline manifest")

    selected = set(selected_cases) if selected_cases else set(verified)
    missing = selected - verified.keys()
    if missing:
        raise ValueError(f"unrecognized archived case IDs: {sorted(missing)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for case_id in sorted(verified):
        svg, entry = verified[case_id]
        if case_id in selected:
            (output_dir / f"{case_id}.svg").write_bytes(svg)
        entries.append({**entry, "extracted": case_id in selected})

    result = {
        "schema_version": "m2h2.historical-render-extraction.1",
        "historical_qualification_sha": manifest["historical_qualification_sha"],
        "preserved_case_inventory_sha256": manifest["sorted_case_svg_sha256_inventory_sha256"],
        "verified_svg_count": len(verified),
        "extracted_svg_count": len(selected),
        "entries": entries,
        "evidence_scope": "historical_archive_only_no_composition_acceptance",
    }
    (output_dir / "index.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--case", action="append", default=[], dest="cases")
    args = parser.parse_args()
    manifest = args.manifest
    if not manifest.is_absolute():
        manifest = args.repo_root / manifest
    report = extract_baseline_renders(args.repo_root, manifest, args.output_dir, tuple(args.cases))
    print(
        json.dumps(
            {
                "verified_svg_count": report["verified_svg_count"],
                "extracted_svg_count": report["extracted_svg_count"],
                "index": str(args.output_dir / "index.json"),
                "evidence_scope": report["evidence_scope"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
