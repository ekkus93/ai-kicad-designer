"""Replace repeated REF/VCC labels with visibly connected schematic rails."""

from __future__ import annotations

import argparse
from pathlib import Path

from tools.pivot.redraw_external_ports import _junction, _once, _wire


def connect_power_rails(source: Path, destination: Path) -> None:
    text = source.read_text(encoding="utf-8")
    labels = (
        ("VCC", "125.73", "102.87"),
        ("VCC", "143.51", "93.98"),
        ("REF", "106.68", "133.35"),
        ("REF", "123.19", "93.98"),
        ("REF", "144.78", "118.11"),
    )
    for name, x, y in labels:
        text = _once(
            text,
            rf'^  \(label "{name}" \(at {x} {y} 0\)[^\n]*\n',
            "",
            f"{name} label at {x},{y}",
        )
    text = _once(
        text,
        r'^  \(wire \(pts \(xy 143\.51 93\.98\) \(xy 143\.51 97\.79\)\)[^\n]*\n',
        "",
        "obsolete U1 VCC label stub",
    )
    text = _once(
        text,
        r'^  \(wire \(pts \(xy 125\.73 102\.87\) \(xy 130\.81 102\.87\)\)[^\n]*\n',
        _wire(("128.27", "102.87"), ("130.81", "102.87"), "reset-pin-wire"),
        "U1 RESET pin wire split for VCC branch",
    )

    wires = (
        # VCC rail: supply connector, R1 upper pin, timer RESET and VCC pin.
        _wire(("97.79", "71.12"), ("154.94", "71.12"), "vcc-common-rail"),
        _wire(("97.79", "71.12"), ("97.79", "86.36"), "vcc-to-r1-riser"),
        _wire(("97.79", "86.36"), ("106.68", "86.36"), "vcc-to-r1"),
        _wire(("128.27", "71.12"), ("128.27", "102.87"), "vcc-to-reset"),
        # REF rail below the circuit: C1, C2, U1 ground and return connector.
        _wire(("106.68", "133.35"), ("106.68", "140.97"), "ref-to-c1"),
        _wire(("123.19", "93.98"), ("123.19", "140.97"), "ref-to-c2"),
        _wire(("143.51", "118.11"), ("143.51", "140.97"), "ref-to-return"),
        _wire(("106.68", "140.97"), ("143.51", "140.97"), "ref-common-rail"),
    )
    junctions = (
        _junction(("128.27", "71.12"), "vcc-reset-rail-junction"),
        _junction(("128.27", "102.87"), "vcc-reset-pin-junction"),
        _junction(("154.94", "71.12"), "vcc-supply-junction"),
        _junction(("123.19", "140.97"), "ref-c2-junction"),
        _junction(("143.51", "140.97"), "ref-return-junction"),
    )
    insertion_point = '  (junction (at 106.68 99.06)'
    if text.count(insertion_point) != 1:
        raise ValueError("could not locate the top-level schematic wire block")
    text = text.replace(insertion_point, "".join(junctions + wires) + insertion_point)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8", newline="")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    connect_power_rails(args.source, args.destination)


if __name__ == "__main__":
    main()
