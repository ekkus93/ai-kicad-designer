"""Revision and validation gates used before manufacturing export."""

from __future__ import annotations

import hashlib
from pathlib import Path


class ReleaseGateError(RuntimeError):
    code = "RELEASE_GATE_FAILED"


def verify_artifact_manifest(root: Path, manifest: dict, expected_revision: str) -> None:
    if manifest.get("revision_id") != expected_revision:
        raise ReleaseGateError("stale or mismatched revision manifest")
    for relative, expected_hash in manifest.get("artifacts", {}).items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ReleaseGateError("manifest artifact is absent or escapes package")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected_hash:
            raise ReleaseGateError("manifest artifact hash mismatch")


def require_clean_native_reports(erc: dict, drc: dict) -> None:
    erc_violations = [
        item for sheet in erc.get("sheets", []) for item in sheet.get("violations", [])
    ]
    if erc_violations:
        raise ReleaseGateError("ERC contains blocking findings")
    if drc.get("violations") or drc.get("unconnected_items"):
        raise ReleaseGateError("DRC contains blocking or unrouted findings")
