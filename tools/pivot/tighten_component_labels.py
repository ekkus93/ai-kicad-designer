"""Move component reference/value fields closer to their schematic symbols."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


POSITIONS = {
    "C1": {"Reference": ("116.84", "127", "111.76", "127"), "Value": ("116.84", "129.54", "111.76", "129.54")},
    "C2": {"Reference": ("133.35", "87.63", "116.84", "87.63"), "Value": ("133.35", "90.17", "116.84", "90.17")},
    "R2": {"Reference": ("116.84", "105.41", "111.76", "105.41"), "Value": ("116.84", "107.95", "111.76", "107.95")},
    "R3": {"Reference": ("172.72", "85.09", "167.64", "85.09"), "Value": ("172.72", "87.63", "167.64", "87.63")},
    "D1": {"Reference": ("172.72", "92.71", "167.64", "92.71"), "Value": ("172.72", "95.25", "167.64", "95.25")},
    "J3": {"Reference": ("160.02", "115.57", "154.94", "115.57"), "Value": ("160.02", "118.11", "154.94", "118.11")},
    "J1": {"Reference": ("162.56", "60.96", "162.56", "63.5"), "Value": ("162.56", "63.5", "162.56", "66.04")},
}


def tighten_component_labels(source: Path, destination: Path) -> None:
    text = source.read_text(encoding="utf-8")
    for reference, fields in POSITIONS.items():
        starts = [m.start() for m in re.finditer(r"^  \(symbol \(lib_id", text, re.MULTILINE)]
        ends = starts[1:] + [text.find("\n  (sheet_instances", starts[-1])]
        blocks = {start: (end if end >= 0 else len(text)) for start, end in zip(starts, ends)}
        symbols = [start for start, end in blocks.items()
                   if re.search(rf'\(property "Reference" "{re.escape(reference)}"', text[start:end])]
        if len(symbols) != 1:
            raise ValueError(f"expected one symbol for {reference}, found {len(symbols)}")
        start = symbols[0]
        for field, (old_x, old_y, new_x, new_y) in fields.items():
            pattern = (
                rf'(\(property "{field}" "[^"]+"\s+\(at\s+)'
                rf'{re.escape(old_x)}\s+{re.escape(old_y)}\s+0(\))'
            )
            end = blocks[start]
            block = text[start:end]
            updated, count = re.subn(
                pattern,
                lambda match: match.group(1) + f"{new_x} {new_y} 0" + match.group(2),
                block,
                count=1,
                flags=re.MULTILINE,
            )
            if count != 1:
                raise ValueError(f"could not move {reference} {field} field")
            text = text[:start] + updated + text[end:]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8", newline="")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    tighten_component_labels(args.source, args.destination)


if __name__ == "__main__":
    main()
