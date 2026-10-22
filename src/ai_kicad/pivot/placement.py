"""Revision-bound deterministic native PCB footprint placement."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from .revisions import StaleRevision


class PlacementError(ValueError):
    """Placement cannot be safely applied to the supplied board revision."""


def _footprint_blocks(text: str) -> list[tuple[int, int, str]]:
    """Return top-level footprint source spans, respecting quoted strings."""
    spans = []
    depth = 0
    start = None
    quote = False
    escaped = False
    token = ""
    for index, char in enumerate(text):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quote = False
            continue
        if char == '"':
            quote = True
            token = ""
        elif char == "(":
            if depth == 1 and re.match(r"\(footprint(?:\s|\))", text[index:]):
                start = index
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 1 and start is not None:
                block = text[start : index + 1]
                spans.append((start, index + 1, block))
                start = None
        elif char.isspace():
            token = ""
        else:
            token += char
    return spans


def _reference(block: str) -> str:
    matches = re.findall(r'\(property\s+"Reference"\s+"((?:\\.|[^"\\])*)"', block)
    if len(matches) != 1:
        raise PlacementError("footprint must have exactly one Reference property")
    return matches[0]


def _apply_at(block: str, x: float, y: float, rotation: float) -> str:
    matches = list(re.finditer(r"\(at\s+[^()]*\)", block))
    if not matches:
        raise PlacementError("footprint has no placement coordinate")
    replacement = f"(at {x:g} {y:g} {rotation:g})"
    match = matches[0]
    return block[: match.start()] + replacement + block[match.end() :]


def apply_placement(
    source: Path,
    destination: Path,
    plan: dict,
    *,
    expected_revision: str,
) -> dict:
    """Apply a plan to a copied board after hash, revision, and exact-ref checks."""
    if plan.get("revision_id") != expected_revision:
        raise StaleRevision("placement plan targets another design revision")
    original = source.read_bytes()
    source_hash = hashlib.sha256(original).hexdigest()
    if plan.get("source_board_sha256") != source_hash:
        raise StaleRevision("placement source board hash differs from plan")
    source_text = original.decode("utf-8")
    blocks = _footprint_blocks(source_text)
    by_ref = {_reference(block): (start, end, block) for start, end, block in blocks}
    if len(by_ref) != len(blocks):
        raise PlacementError("source board contains duplicate footprint references")
    placements = plan.get("placements", {})
    if set(placements) != set(by_ref):
        raise PlacementError("placement plan must cover each footprint exactly once")
    edits = []
    readback = {}
    for reference, placement in placements.items():
        x, y = float(placement["x_mm"]), float(placement["y_mm"])
        rotation = float(placement.get("rotation_deg", 0))
        if not all(map(lambda value: abs(value) < 1_000_000, (x, y, rotation))):
            raise PlacementError("placement coordinate is outside supported bounds")
        start, end, block = by_ref[reference]
        edits.append((start, end, _apply_at(block, x, y, rotation)))
        readback[reference] = {"x_mm": x, "y_mm": y, "rotation_deg": rotation}
    result = source_text
    for start, end, replacement in reversed(edits):
        result = result[:start] + replacement + result[end:]
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix="placement-", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(result.encode())
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {
        "status": "PASS",
        "expected_revision": expected_revision,
        "source_board_sha256": source_hash,
        "candidate_board_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "placements": readback,
    }


def load_plan(path: Path) -> dict:
    return json.loads(path.read_text())
