"""Make the reference circuit's external connectors visually explicit.

The original schematic used matching local labels to connect J1/J2/J3 to the
circuit. This transform keeps that electrical topology while moving each
connector beside its node and replacing the label-only port stubs with wires.
"""

from __future__ import annotations

import argparse
import re
import uuid
from pathlib import Path

ROOT_SHEET_UUID = uuid.UUID("67f9fc10-0a66-5669-bb17-4da3d7e288a2")


def _once(text: str, pattern: str, replacement: str, label: str) -> str:
    result, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE | re.DOTALL)
    if count != 1:
        raise ValueError(f"expected one {label}, found {count}")
    return result


def _move_symbol(
    text: str,
    *,
    lib_id: str,
    reference: str,
    old_at: str,
    new_at: str,
    old_reference_at: str,
    new_reference_at: str,
    old_value_at: str,
    new_value_at: str,
) -> str:
    pattern = (
        rf'(?P<head>\(symbol \(lib_id "{re.escape(lib_id)}"\) \(at )'
        rf'{re.escape(old_at)}'
        rf'(?P<ref_head> \d+\).*?\(property "Reference" "{re.escape(reference)}" \(at )'
        rf'{re.escape(old_reference_at)}'
        rf'(?P<value_head> 0\).*?\(property "Value" "[^"]+" \(at )'
        rf'{re.escape(old_value_at)}(?P<tail> 0\))'
    )

    def replace(match: re.Match[str]) -> str:
        return (
            match["head"]
            + new_at
            + match["ref_head"]
            + new_reference_at
            + match["value_head"]
            + new_value_at
            + match["tail"]
        )

    return _once(text, pattern, replace, f"symbol {reference}")


def _wire(start: tuple[str, str], end: tuple[str, str], key: str) -> str:
    identifier = uuid.uuid5(ROOT_SHEET_UUID, f"external-port-redraw:{key}")
    return (
        f'  (wire (pts (xy {start[0]} {start[1]}) (xy {end[0]} {end[1]})) '
        f'(stroke (width 0) (type default)) (uuid "{identifier}") )\n'
    )


def _junction(at: tuple[str, str], key: str) -> str:
    identifier = uuid.uuid5(ROOT_SHEET_UUID, f"external-port-redraw:{key}")
    return (
        f'  (junction (at {at[0]} {at[1]}) (diameter 0) (color 0 0 0 0) '
        f'(uuid "{identifier}") )\n'
    )


def redraw_external_ports(source: Path, destination: Path) -> None:
    text = source.read_text(encoding="utf-8")

    # Remove the old connector label stubs; the three connectors will sit at
    # their circuit nodes in the new drawing.
    for y in ("90.17", "97.79", "105.41"):
        text = _once(
            text,
            rf'^  \(wire \(pts \(xy 86\.36 {y}\) \(xy 87\.63 {y}\)\)[^\n]*\n',
            "",
            f"old connector wire at y={y}",
        )
        text = _once(
            text,
            rf'^  \(wire \(pts \(xy 87\.63 {y}\) \(xy 90\.17 {y}\)\)[^\n]*\n',
            "",
            f"old connector pin wire at y={y}",
        )

    for name, y in (("OUT", "90.17"), ("REF", "97.79"), ("VCC", "105.41")):
        text = _once(
            text,
            rf'^  \(label "{name}" \(at 86\.36 {y} 0\)[^\n]*\n',
            "",
            f"old {name} connector label",
        )

    connector_positions = (
        ("J1", "95.25 105.41", "127.00 81.28", "105.41 102.87", "127.00 71.12", "105.41 105.41", "127.00 73.66"),
        ("J2", "95.25 90.17", "210.82 107.95", "95.25 80.01", "210.82 96.52", "95.25 82.55", "210.82 99.06"),
        ("J3", "95.25 97.79", "185.42 118.11", "105.41 95.25", "195.58 115.57", "105.41 97.79", "195.58 118.11"),
    )
    for ref, old_at, new_at, old_ref, new_ref, old_value, new_value in connector_positions:
        text = _move_symbol(
            text,
            lib_id="Connector_Generic:Conn_01x01",
            reference=ref,
            old_at=old_at,
            new_at=new_at,
            old_reference_at=old_ref,
            new_reference_at=new_ref,
            old_value_at=old_value,
            new_value_at=new_value,
        )

    # Move the existing ERC power flags onto the explicit VCC and REF wires.
    text = _move_symbol(
        text,
        lib_id="power:PWR_FLAG",
        reference="#FLG01",
        old_at="86.36 105.41",
        new_at="119.38 81.28",
        old_reference_at="86.36 105.41",
        new_reference_at="119.38 81.28",
        old_value_at="86.36 107.95",
        new_value_at="119.38 83.82",
    )
    text = _move_symbol(
        text,
        lib_id="power:PWR_FLAG",
        reference="#FLG02",
        old_at="86.36 97.79",
        new_at="179.07 118.11",
        old_reference_at="86.36 97.79",
        new_reference_at="179.07 118.11",
        old_value_at="86.36 100.33",
        new_value_at="179.07 120.65",
    )

    # J1's pin is 5.08 mm left of its body. J2 and J3 land directly on the
    # existing OUT and REF wire endpoints respectively.
    port_wires = (
        _wire(("116.84", "81.28"), ("119.38", "81.28"), "vcc-a"),
        _wire(("119.38", "81.28"), ("121.92", "81.28"), "vcc-b"),
    )
    flag_support = (
        _junction(("119.38", "81.28"), "vcc-junction"),
        _junction(("179.07", "118.11"), "ref-junction"),
    )
    old_ref_wire = (
        '  (wire (pts (xy 176.53 118.11) (xy 180.34 118.11)) '
        '(stroke (width 0) (type default)) '
        '(uuid "5548ccff-68a0-5c3f-b845-d0373a4520e8") )\n'
    )
    text = _once(
        text,
        re.escape(old_ref_wire),
        _wire(("176.53", "118.11"), ("179.07", "118.11"), "ref-a")
        + _wire(("179.07", "118.11"), ("180.34", "118.11"), "ref-b"),
        "REF wire for power flag split",
    )
    insertion_point = '  (junction (at 142.24 99.06)'
    if text.count(insertion_point) != 1:
        raise ValueError("could not find schematic wire insertion point")
    text = text.replace(insertion_point, "".join(flag_support + port_wires) + insertion_point)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8", newline="")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    redraw_external_ports(args.source, args.destination)


if __name__ == "__main__":
    main()
