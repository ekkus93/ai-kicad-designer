"""Bring the LED indicator branch into the visible 555 circuit wiring."""

from __future__ import annotations

import argparse
import re
import uuid
from pathlib import Path

from tools.pivot.redraw_external_ports import _junction, _move_symbol, _once, _wire

ROOT_SHEET_UUID = uuid.UUID("67f9fc10-0a66-5669-bb17-4da3d7e288a2")


def connect_led_branch(source: Path, destination: Path) -> None:
    text = source.read_text(encoding="utf-8")

    # Remove the LED branch's isolated VCC/OUT label connections and wires.
    for start, end in (
        ("116.84 81.28", "116.84 85.09"),
        ("116.84 85.09", "116.84 90.17"),
        ("116.84 97.79", "116.84 101.6"),
        ("116.84 109.22", "116.84 113.03"),
        ("116.84 81.28", "119.38 81.28"),
        ("119.38 81.28", "121.92 81.28"),
    ):
        text = _once(
            text,
            rf'^  \(wire \(pts \(xy {re.escape(start.split()[0])} {re.escape(start.split()[1])}\) '
            rf'\(xy {re.escape(end.split()[0])} {re.escape(end.split()[1])}\)\)[^\n]*\n',
            "",
            f"old LED branch wire {start} to {end}",
        )
    text = _once(
        text,
        r'^  \(junction \(at 119\.38 81\.28\)[^\n]*\n',
        "",
        "old isolated VCC junction",
    )
    for name, x, y in (("VCC", "116.84", "81.28"), ("OUT", "116.84", "113.03")):
        text = _once(
            text,
            rf'^  \(label "{name}" \(at {x} {y} 0\)[^\n]*\n',
            "",
            f"old LED branch {name} label",
        )

    text = _move_symbol(
        text,
        lib_id="Device:R",
        reference="R3",
        old_at="116.84 93.98",
        new_at="198.12 87.63",
        old_reference_at="127 91.44",
        new_reference_at="208.28 85.09",
        old_value_at="127 93.98",
        new_value_at="208.28 87.63",
    )
    text = _move_symbol(
        text,
        lib_id="Device:LED",
        reference="D1",
        old_at="116.84 105.41",
        new_at="198.12 99.06",
        old_reference_at="132.08 95.25",
        new_reference_at="208.28 92.71",
        old_value_at="132.08 97.79",
        new_value_at="208.28 95.25",
    )
    text = _move_symbol(
        text,
        lib_id="Connector_Generic:Conn_01x01",
        reference="J1",
        old_at="127.00 81.28",
        new_at="198.12 71.12",
        old_reference_at="127.00 71.12",
        new_reference_at="198.12 60.96",
        old_value_at="127.00 73.66",
        new_value_at="198.12 63.5",
    )
    text = _move_symbol(
        text,
        lib_id="Connector_Generic:Conn_01x01",
        reference="J2",
        old_at="210.82 107.95",
        new_at="228.6 107.95",
        old_reference_at="210.82 96.52",
        new_reference_at="228.6 96.52",
        old_value_at="210.82 99.06",
        new_value_at="228.6 99.06",
    )

    # Move the supply flag onto the new visible VCC bus.
    text = _move_symbol(
        text,
        lib_id="power:PWR_FLAG",
        reference="#FLG01",
        old_at="119.38 81.28",
        new_at="190.5 78.74",
        old_reference_at="119.38 81.28",
        new_reference_at="190.5 78.74",
        old_value_at="119.38 83.82",
        new_value_at="190.5 81.28",
    )

    # Replace the output lead with a longer run that taps the LED cathode.
    old_output_wires = (
        '  (wire (pts (xy 186.69 107.95) (xy 201.93 107.95)) (stroke (width 0) (type default)) (uuid "7c4cf12b-0971-59c0-a30f-573554458829") )\n',
        '  (wire (pts (xy 201.93 107.95) (xy 205.74 107.95)) (stroke (width 0) (type default)) (uuid "436f64db-4672-552f-bda0-2e5a667f4727") )\n',
    )
    for wire in old_output_wires:
        text = _once(text, re.escape(wire), "", "old output connector wire")
    text = _once(
        text,
        r'^  \(label "OUT" \(at 205\.74 107\.95 0\)[^\n]*\n',
        "",
        "old output net label",
    )
    output_label = (
        '  (label "OUT" (at 205.74 107.95 0) '
        '(effects (font (size 1.27 1.27)) (justify left bottom)) '
        '(uuid "cfee78c0-9962-5bc1-bcff-9950a2dadd7b") )\n'
    )

    added_wires = (
        _wire(("198.12", "91.44"), ("198.12", "95.25"), "led-resistor-to-led-new"),
        _wire(("198.12", "102.87"), ("198.12", "107.95"), "led-to-output"),
        _wire(("179.07", "97.79"), ("190.5", "97.79"), "vcc-bus-bottom"),
        _wire(("190.5", "71.12"), ("190.5", "78.74"), "vcc-bus-upper"),
        _wire(("190.5", "78.74"), ("190.5", "83.82"), "vcc-bus-flag-to-branch"),
        _wire(("190.5", "83.82"), ("190.5", "97.79"), "vcc-bus-lower"),
        _wire(("190.5", "71.12"), ("193.04", "71.12"), "vcc-to-j1"),
        _wire(("190.5", "83.82"), ("198.12", "83.82"), "vcc-to-led"),
        _wire(("186.69", "107.95"), ("198.12", "107.95"), "output-to-led"),
        _wire(("198.12", "107.95"), ("223.52", "107.95"), "output-to-j2"),
    )
    additions = (
        _junction(("190.5", "78.74"), "vcc-flag-junction"),
        _junction(("190.5", "83.82"), "vcc-bus-junction"),
        _junction(("198.12", "107.95"), "output-led-junction"),
    ) + added_wires
    insertion_point = '  (junction (at 142.24 99.06)'
    if text.count(insertion_point) != 1:
        raise ValueError("could not find wire insertion point")
    text = text.replace(insertion_point, "".join(additions) + output_label + insertion_point)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8", newline="")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    connect_led_branch(args.source, args.destination)


if __name__ == "__main__":
    main()
