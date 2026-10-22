"""Verify the immutable native KiCad reference project input set."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def verify_native_project(root: Path) -> list[str]:
    root = root.resolve()
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != "native-project-fixture.v1":
        return ["unsupported native project manifest schema"]
    errors = []
    expected = manifest.get("files", {})
    actual_paths = {
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and path != manifest_path
    }
    if actual_paths != set(expected):
        errors.append("native project inventory differs from fixture manifest")
    for relative, digest in expected.items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
            errors.append(f"native project path is absent or unsafe: {relative}")
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            errors.append(f"native project hash mismatch: {relative}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path("fixtures/pivot/reference_555_led_flasher_v1/native_project"),
    )
    args = parser.parse_args()
    errors = verify_native_project(args.fixture)
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"PASS: {args.fixture}")


if __name__ == "__main__":
    main()
