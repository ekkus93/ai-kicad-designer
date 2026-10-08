"""Independent integrity audit of preserved native KiCad SVG render archives."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import gzip
import hashlib
import json
from typing import Mapping, Sequence


@dataclass(frozen=True)
class NativeRenderInventory:
    qualification_head: str
    render_count: int
    inventory_sha256: str
    case_hashes: tuple[tuple[str, str], ...]


def verify_native_render_parts(parts: Sequence[Mapping[str, object]]) -> NativeRenderInventory:
    """Verify encoded SVGs and the complete numbered archive inventory."""
    if not parts:
        raise ValueError("native render archive has no parts")
    expected_parts = len(parts)
    qualification_heads: set[str] = set()
    seen_part_numbers: set[int] = set()
    case_hashes: list[tuple[str, str]] = []
    for part in parts:
        if part.get("schema") != "m2h2.native-render-archive.1":
            raise ValueError("unexpected native archive schema")
        if part.get("archive_parts") != expected_parts:
            raise ValueError("native archive part count mismatch")
        number = part.get("archive_part")
        if type(number) is not int or not 1 <= number <= expected_parts:
            raise ValueError("invalid native archive part number")
        if number in seen_part_numbers:
            raise ValueError("duplicate native archive part number")
        seen_part_numbers.add(number)
        head = part.get("qualification_head")
        if not isinstance(head, str) or len(head) != 40:
            raise ValueError("invalid qualification head")
        qualification_heads.add(head)
        renders = part.get("renders")
        if not isinstance(renders, list):
            raise ValueError("invalid native render records")
        for render in renders:
            if not isinstance(render, dict) or render.get("encoding") != "gzip+base64":
                raise ValueError("invalid native render encoding")
            case, digest, payload = (
                render.get("case"),
                render.get("svg_sha256"),
                render.get("data"),
            )
            if not isinstance(case, str) or not case:
                raise ValueError("invalid native render case")
            if not isinstance(digest, str) or not isinstance(payload, str):
                raise ValueError("invalid native render digest/payload")
            try:
                svg = gzip.decompress(base64.b64decode(payload, validate=True))
            except (ValueError, OSError) as exc:
                raise ValueError("invalid compressed native SVG") from exc
            if hashlib.sha256(svg).hexdigest() != digest:
                raise ValueError("native SVG SHA-256 mismatch")
            if b"<svg" not in svg[:4096]:
                raise ValueError("native render is not SVG")
            case_hashes.append((case, digest))
    if len(qualification_heads) != 1:
        raise ValueError("mixed qualification heads in native archive")
    if len({case for case, _ in case_hashes}) != len(case_hashes):
        raise ValueError("duplicate native render case")
    canonical = json.dumps(sorted(case_hashes), separators=(",", ":"))
    return NativeRenderInventory(
        qualification_head=next(iter(qualification_heads)),
        render_count=len(case_hashes),
        inventory_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        case_hashes=tuple(sorted(case_hashes)),
    )
