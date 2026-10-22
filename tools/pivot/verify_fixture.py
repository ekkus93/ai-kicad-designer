"""Verify a frozen pivot fixture manifest without modifying any artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def verify_manifest(manifest_path: Path, repository_root: Path) -> list[str]:
    """Return hash/path errors, rejecting manifest paths that escape the repo."""
    manifest_path = manifest_path.resolve()
    repository_root = repository_root.resolve()
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != "pivot-fixture-manifest.v1":
        return ["unsupported fixture manifest schema"]
    fixture_root = manifest_path.parent
    errors = []
    for relative_path, expected_hash in sorted(manifest.get("input_hashes", {}).items()):
        candidate = (fixture_root / relative_path).resolve()
        if not candidate.is_relative_to(repository_root):
            errors.append(f"path escapes repository: {relative_path}")
            continue
        try:
            actual_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
        except OSError:
            errors.append(f"artifact unavailable: {relative_path}")
            continue
        if actual_hash != expected_hash:
            errors.append(f"hash mismatch: {relative_path}")
    for path_key, hash_key in (
        ("toolchain_lock", "toolchain_lock_sha256"),
        ("m2b_asset_lock", "m2b_asset_lock_sha256"),
        ("m2a_asset_lock", "m2a_asset_lock_sha256"),
    ):
        candidate = (repository_root / manifest[path_key]).resolve()
        if not candidate.is_relative_to(repository_root):
            errors.append(f"lock path escapes repository: {manifest[path_key]}")
            continue
        try:
            actual_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
        except OSError:
            errors.append(f"lock unavailable: {manifest[path_key]}")
            continue
        if actual_hash != manifest[hash_key]:
            errors.append(f"lock hash mismatch: {manifest[path_key]}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    errors = verify_manifest(args.manifest, args.repo_root)
    if errors:
        print("\n".join(errors))
        return 1
    print(f"PASS: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
