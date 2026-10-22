"""Translate the complete schematic drawing by one grid-aligned X offset."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def center_schematic(source: Path, destination: Path, shift_mm: float = 35.56) -> None:
    text = source.read_text(encoding="utf-8")
    marker = "  (wire (pts "
    start = text.find(marker)
    if start < 0:
        raise ValueError("schematic has no top-level wire block")
    if round(shift_mm / 2.54) * 2.54 != shift_mm:
        raise ValueError("shift must align to the 2.54 mm KiCad grid")
    head, drawing = text[:start], text[start:]

    def translate(match: re.Match[str]) -> str:
        x = float(match.group("x")) - shift_mm
        if x < 0:
            raise ValueError("translation would move schematic geometry left of the page origin")
        x_text = f"{x:.4f}".rstrip("0").rstrip(".")
        return match.group("prefix") + x_text + match.group("middle")

    drawing, xy_count = re.subn(
        r"(?P<prefix>\(xy )(?P<x>-?\d+(?:\.\d+)?)(?P<middle> \d+(?:\.\d+)?\))",
        translate,
        drawing,
    )
    drawing, at_count = re.subn(
        r"(?P<prefix>\(at )(?P<x>-?\d+(?:\.\d+)?)(?P<middle> \d+(?:\.\d+)?(?: (?:0|90|180|270))?\))",
        translate,
        drawing,
    )
    if xy_count < 20 or at_count < 10:
        raise ValueError(f"unexpected schematic drawing inventory: xy={xy_count}, at={at_count}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(head + drawing, encoding="utf-8", newline="")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--shift-mm", type=float, default=35.56)
    args = parser.parse_args()
    center_schematic(args.source, args.destination, args.shift_mm)


if __name__ == "__main__":
    main()
