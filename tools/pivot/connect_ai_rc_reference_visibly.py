#!/usr/bin/env python3
"""Draw the AI RC candidate's return as a single physical schematic wire."""
from __future__ import annotations

import argparse
import re
import uuid
from pathlib import Path

NS = uuid.UUID("e3150a4f-11ea-45bb-9b4c-5b3028841c84")


def wire(a: tuple[float, float], b: tuple[float, float], key: str) -> str:
    uid = uuid.uuid5(NS, key)
    return (
        f'  (wire (pts (xy {a[0]:g} {a[1]:g}) (xy {b[0]:g} {b[1]:g})) '
        f'(stroke (width 0) (type default)) (uuid "{uid}") )'
    )


def connect_return(source: Path, destination: Path) -> None:
    text = source.read_text()
    # Move J3 beneath the capacitor, with its pin facing the capacitor branch.
    starts = [m.start() for m in re.finditer(r'^  \(symbol \(lib_id "Connector_Generic:Conn_01x01"\)', text, re.M)]
    blocks = []
    for start in starts:
        end = text.find("\n  (symbol ", start + 3)
        if end < 0:
            end = text.find("\n  (embedded_fonts", start)
        blocks.append((start, end, text[start:end]))
    selected = next((item for item in blocks if '(property "Reference" "J3"' in item[2]), None)
    if selected is None:
        raise ValueError("J3 connector not found")
    start, end, block = selected
    block = block.replace('(at 88.9 34.29 0)', '(at 142.24 71.12 0)', 1)
    block = block.replace('(at 99.06 31.75 0)', '(at 152.4 68.58 0)', 1)
    block = block.replace('(at 99.06 34.45 0)', '(at 152.4 71.28 0)', 1)
    text = text[:start] + block + text[end:]

    lines = text.splitlines()
    kept = []
    for line in lines:
        if '(uuid "d6b8458e-9331-5a7c-ad12-ed4fc3a4f0db")' in line:
            continue
        if '(uuid "d023b65a-e866-56bf-bc28-0cc83a8efa5e")' in line:
            continue
        if '(label "REF" (at 80.01 34.29 0)' in line:
            continue
        if '(label "REF" (at 132.08 62.23 0)' in line:
            continue
        if line == '  (embedded_fonts no)':
            kept.extend([
                wire((132.08, 62.23), (132.08, 71.12), "cap-return-vertical"),
                wire((132.08, 71.12), (137.16, 71.12), "return-connector-horizontal"),
            ])
        kept.append(line)
    if len(kept) == len(lines):
        raise ValueError("expected return labels and branch wires were not removed")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(kept) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    connect_return(args.source, args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
