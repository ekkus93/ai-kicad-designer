"""Independent Gerber/Excellon inspection and deterministic review packaging."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path

from .release import verify_artifact_manifest


REQUIRED_SUFFIXES = {".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".gm1", ".drl"}
COORDINATE_REQUIRED_SUFFIXES = {".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gm1"}
GERBER_SUFFIXES = REQUIRED_SUFFIXES - {".drl"} | {".gbr", ".gba", ".gbp", ".gta", ".gtp"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_gerber(path: Path) -> dict:
    text = path.read_text()
    if "%FSLAX46Y46*%" not in text or "%MOMM*%" not in text or not text.rstrip().endswith("M02*"):
        raise ValueError(f"malformed metric Gerber: {path.name}")
    coordinates = [
        (int(x) / 1_000_000, int(y) / 1_000_000) for x, y in re.findall(r"X(-?\d+)Y(-?\d+)", text)
    ]
    if not coordinates:
        raise ValueError(f"Gerber has no coordinates: {path.name}")
    xs, ys = zip(*coordinates, strict=True)
    return {
        "path": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "bounds_mm": [min(xs), min(ys), max(xs), max(ys)],
        "coordinate_count": len(coordinates),
    }


def inspect_drill(path: Path) -> dict:
    text = path.read_text()
    if "M48" not in text or "METRIC" not in text or not text.rstrip().endswith("M30"):
        raise ValueError(f"malformed metric Excellon: {path.name}")
    tools = {name: float(diameter) for name, diameter in re.findall(r"(T\d+)C([0-9.]+)", text)}
    holes = [(float(x), float(y)) for x, y in re.findall(r"X(-?[0-9.]+)Y(-?[0-9.]+)", text)]
    if not tools or not holes:
        raise ValueError("drill file has no tools or holes")
    return {
        "path": path.name,
        "sha256": sha256(path),
        "tools_mm": tools,
        "hole_count": len(holes),
        "bounds_mm": [
            min(x for x, _ in holes),
            min(y for _, y in holes),
            max(x for x, _ in holes),
            max(y for _, y in holes),
        ],
    }


def inspect_fabrication(directory: Path, width_mm: float, height_mm: float) -> dict:
    files = [path for path in directory.iterdir() if path.is_file()]
    suffixes = {path.suffix for path in files}
    missing = sorted(REQUIRED_SUFFIXES - suffixes)
    if missing:
        raise ValueError(f"missing required fabrication files: {missing}")
    gerbers = [
        inspect_gerber(path) for path in files if path.suffix in COORDINATE_REQUIRED_SUFFIXES
    ]
    inventory = [
        {"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in files
        if path.suffix in GERBER_SUFFIXES
    ]
    edge = next(item for item in gerbers if item["path"].endswith("Edge_Cuts.gm1"))
    edge_width = edge["bounds_mm"][2] - edge["bounds_mm"][0]
    edge_height = edge["bounds_mm"][3] - edge["bounds_mm"][1]
    if abs(edge_width - width_mm) > 0.001 or abs(edge_height - height_mm) > 0.001:
        raise ValueError("Gerber outline disagrees with manufacturing profile")
    drills = [inspect_drill(path) for path in files if path.suffix == ".drl"]
    return {
        "status": "PASS",
        "required_suffixes": sorted(REQUIRED_SUFFIXES),
        "gerbers": gerbers,
        "gerber_inventory": inventory,
        "drills": drills,
        "outline_mm": [edge_width, edge_height],
    }


def deterministic_zip(source: Path, destination: Path) -> str:
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(source.rglob("*")):
            if (
                not path.is_file()
                or path == destination
                or {"workflow", "config"} & set(path.relative_to(source).parts)
                or path.suffix == ".kicad_prl"
                or path.name == "package.sha256"
            ):
                continue
            info = zipfile.ZipInfo(str(path.relative_to(source)), (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    return sha256(destination)


def write_manifest(
    root: Path,
    revision_id: str,
    checks: dict,
    limitations: list[str],
    provenance: dict | None = None,
) -> dict:
    artifacts = {
        str(path.relative_to(root)): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and path.name not in {"fabrication_manifest.json", "review-package.zip", "package.sha256"}
        and not {"workflow", "config"} & set(path.relative_to(root).parts)
        and path.suffix != ".kicad_prl"
    }
    manifest = {
        "schema_version": "fabrication-manifest.v1",
        "revision_id": revision_id,
        "state": "PACKAGE_READY_FOR_REVIEW",
        "manufacturing_readiness": "BLOCKED_PENDING_PROFILE_AND_OWNER_REVIEW",
        "artifacts": artifacts,
        "checks": checks,
        "provenance": provenance or {},
        "limitations": limitations,
        "claims": {
            "ordered": False,
            "assembled": False,
            "physically_tested": False,
            "fabricator_accepted": False,
        },
    }
    (root / "fabrication_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def verify_review_package(package: Path, destination: Path) -> dict:
    with zipfile.ZipFile(package) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise ValueError(f"corrupt ZIP member: {bad_member}")
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError("ZIP path escapes clean extraction directory")
        archive.extractall(destination)
    manifest_path = destination / "fabrication_manifest.json"
    if not manifest_path.is_file():
        raise ValueError("package has no fabrication manifest")
    manifest = json.loads(manifest_path.read_text())
    verify_artifact_manifest(destination, manifest, manifest["revision_id"])
    report_path = destination / "reports/verification_report.json"
    report = json.loads(report_path.read_text())
    if report.get("revision_id") != manifest["revision_id"] or report.get("status") != "PASS":
        raise ValueError("verification report does not bind to the package revision")
    project = destination / "editable_project"
    required = [
        project / "Reference555LedFlasher.kicad_pro",
        project / "Reference555LedFlasher.kicad_sch",
        project / "Reference555LedFlasher.kicad_pcb",
        destination / "previews/board-top.png",
        destination / "previews/board-bottom.png",
    ]
    if not all(path.is_file() for path in required):
        raise ValueError("package is missing native project or human preview files")
    return {
        "status": "PASS",
        "revision_id": manifest["revision_id"],
        "artifact_count": len(manifest["artifacts"]),
        "native_project": str(project),
    }
