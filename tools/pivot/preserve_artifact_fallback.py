"""Preserve qualification outputs locally when Actions artifact upload fails."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _files(root: Path, inputs: list[Path]) -> dict[str, tuple[Path, str]]:
    inventory: dict[str, tuple[Path, str]] = {}
    for source in inputs:
        unresolved = root / source
        if unresolved.is_symlink():
            raise ValueError(f"artifact input must not be a symlink: {source}")
        candidate = unresolved.resolve()
        if not candidate.is_relative_to(root):
            raise ValueError(f"artifact input escapes repository: {source}")
        if candidate.is_symlink():
            raise ValueError(f"artifact input must not be a symlink: {source}")
        if not candidate.exists():
            continue
        paths = (candidate,) if candidate.is_file() else tuple(sorted(candidate.rglob("*")))
        for path in paths:
            if path.is_symlink():
                raise ValueError(f"artifact tree contains a symlink: {path.relative_to(root)}")
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            inventory[relative] = (path, _sha256(path))
    if not inventory:
        raise ValueError("no regular artifact files were found to preserve")
    return inventory


def preserve(
    *,
    root: Path,
    destination: Path,
    inputs: list[Path],
    source_sha: str,
    run_url: str,
) -> dict:
    root = root.resolve()
    destination = destination.resolve()
    if not destination.is_relative_to(root):
        raise ValueError("fallback destination must be inside repository root")
    if len(source_sha) != 40 or any(
        character not in "0123456789abcdef" for character in source_sha
    ):
        raise ValueError("source SHA must be a full lowercase Git commit hash")
    if not run_url.startswith("https://github.com/"):
        raise ValueError("run URL must point to GitHub Actions")

    source_files = _files(root, inputs)
    file_hashes = {name: digest for name, (_path, digest) in sorted(source_files.items())}
    content_identity = {"source_sha": source_sha, "files": file_hashes}
    content_sha = hashlib.sha256(
        json.dumps(content_identity, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    final = destination / f"sha256-{content_sha}"
    manifest = {
        "schema_version": "pivot-artifact-fallback.v1",
        "content_sha256": content_sha,
        "source_sha": source_sha,
        "run_url": run_url,
        "run_urls": [run_url],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": file_hashes,
    }

    destination.mkdir(parents=True, exist_ok=True)
    if final.exists():
        existing = json.loads((final / "manifest.json").read_text())
        if existing.get("content_sha256") != content_sha or existing.get("files") != file_hashes:
            raise ValueError(f"content-address collision or damaged fallback: {final}")
        for relative, expected in file_hashes.items():
            if _sha256(final / "files" / relative) != expected:
                raise ValueError(f"stored artifact hash mismatch: {relative}")
        run_urls = list(
            dict.fromkeys((*existing.get("run_urls", [existing.get("run_url")]), run_url))
        )
        existing["run_urls"] = run_urls
        existing["run_url"] = run_urls[-1]
        manifest_path = final / "manifest.json"
        temporary_manifest = final / ".manifest.json.tmp"
        temporary_manifest.write_text(json.dumps(existing, indent=2) + "\n")
        os.replace(temporary_manifest, manifest_path)
        summary_path = final / "summary.md"
        summary_path.write_text(
            "## Qualification artifact upload failed\n\n"
            + "\n".join(f"- Workflow run: {url}" for url in run_urls)
            + f"\n- Source commit: `{source_sha}`\n"
            + f"- Local content-addressed fallback: `{final.as_posix()}`\n"
            + f"- Content SHA-256: `{content_sha}` ({len(file_hashes)} files)\n"
        )
        return {**existing, "path": final.as_posix(), "reused": True}

    temporary = Path(tempfile.mkdtemp(prefix=f".{content_sha}.", dir=destination))
    try:
        for relative, (source, _digest) in source_files.items():
            target = temporary / "files" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if _sha256(target) != file_hashes[relative]:
                raise ValueError(f"artifact changed while copying: {relative}")
        (temporary / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        summary = (
            "## Qualification artifact upload failed\n\n"
            f"- Workflow run: {run_url}\n"
            f"- Source commit: `{source_sha}`\n"
            f"- Local content-addressed fallback: `{final.as_posix()}`\n"
            f"- Content SHA-256: `{content_sha}` ({len(file_hashes)} files)\n"
        )
        (temporary / "summary.md").write_text(summary)
        os.replace(temporary, final)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return {**manifest, "path": final.as_posix(), "reused": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--summary-file", type=Path)
    args = parser.parse_args()
    try:
        result = preserve(
            root=args.root,
            destination=args.destination,
            inputs=args.input,
            source_sha=args.source_sha,
            run_url=args.run_url,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"artifact fallback failed: {error}", file=sys.stderr)
        return 1
    summary = Path(result["path"]) / "summary.md"
    if args.summary_file:
        with args.summary_file.open("a") as stream:
            stream.write(summary.read_text())
            stream.write("\n")
    print(f"preserved {len(result['files'])} files at {result['path']}")
    print(f"content_sha256={result['content_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
