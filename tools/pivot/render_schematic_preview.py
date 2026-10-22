"""Render a tightly framed, hash-recorded KiCad schematic PNG preview."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def render_preview(cli: Path, schematic: Path, output: Path, metadata: Path) -> dict:
    cli = cli.resolve()
    schematic = schematic.resolve()
    if not cli.is_file() or not schematic.is_file():
        raise FileNotFoundError("KiCad CLI and schematic must be existing files")
    renderer = shutil.which("rsvg-convert")
    cropper = shutil.which("convert")
    if renderer is None or cropper is None:
        raise RuntimeError("rsvg-convert and ImageMagick convert are required for the PNG preview")

    output.parent.mkdir(parents=True, exist_ok=True)
    metadata.parent.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, LC_ALL="C", TZ="UTC")
    with tempfile.TemporaryDirectory(prefix="pivot-schematic-preview-") as temporary:
        svg_dir = Path(temporary)
        export = subprocess.run(
            [
                str(cli),
                "sch",
                "export",
                "svg",
                "--output",
                str(svg_dir),
                str(schematic),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            env=environment,
            check=True,
        )
        svg = svg_dir / f"{schematic.stem}.svg"
        full_page = svg_dir / "full-page.png"
        raster = subprocess.run(
            [
                renderer,
                "--width=2400",
                f"--output={full_page}",
                str(svg),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            env=environment,
            check=True,
        )
        crop = subprocess.run(
            [cropper, str(full_page), "-crop", "1400x800+500+400", "+repage", str(output)],
            capture_output=True,
            text=True,
            timeout=120,
            env=environment,
            check=True,
        )
        cli_version = subprocess.run(
            [str(cli), "version"], capture_output=True, text=True, timeout=30, env=environment, check=True
        ).stdout.strip()
        renderer_version = subprocess.run(
            [renderer, "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            env=environment,
            check=True,
        ).stdout.strip()
        color_count_result = subprocess.run(
            [cropper, str(output), "-format", "%k", "info:"],
            capture_output=True,
            text=True,
            timeout=30,
            env=environment,
            check=True,
        )
        color_count = int(color_count_result.stdout.strip())
        cropper_version = subprocess.run(
            [cropper, "-version"],
            capture_output=True,
            text=True,
            timeout=30,
            env=environment,
            check=True,
        ).stdout.splitlines()[0]
        result = {
            "schema_version": "schematic-preview.v1",
            "source_schematic": schematic.name,
            "source_sha256": _sha256(schematic),
            "kicad_cli_version": cli_version,
            "kicad_cli_sha256": _sha256(cli),
            "svg_renderer_version": renderer_version,
            "svg_renderer_path": renderer,
            "png_cropper_version": cropper_version,
            "png_cropper_path": cropper,
            "svg_sha256": _sha256(svg),
            "png_path": str(output),
            "png_sha256": _sha256(output),
            "png_bytes": output.stat().st_size,
            "png_color_count": color_count,
            "render_size_px": {"width": 2400, "height": 1698},
            "crop_px": {"left": 500, "top": 400, "width": 1400, "height": 800},
            "commands": [
                export.args,
                raster.args,
                crop.args,
            ],
        }
        if (
            output.stat().st_size < 1000
            or color_count < 100
            or output.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n"
        ):
            raise RuntimeError("KiCad schematic preview did not produce a valid PNG")
        metadata.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--schematic", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args()
    result = render_preview(args.cli, args.schematic, args.output, args.metadata)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
