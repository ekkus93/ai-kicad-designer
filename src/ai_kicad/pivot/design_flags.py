"""Report-only design-review flags from the intended circuit (reviewer loop spec R7.6).

These are electrical design questions for a separate design review, not layout defects.
They never change a check, an edit, or DESIGN_REQUIREMENTS_CHECKED (which stays PENDING).
The rules use part types and pin roles, not per-design names.
"""

from __future__ import annotations

import re

# Supply pins by part family: (positive, return or negative).
TIMER_SUPPLY = ("8", "1")
OPAMP_SUPPLY = ("8", "4")
_UNITS = {"": 1.0, "r": 1.0, "k": 1e3, "m": 1e6}


def _ohms(value: str) -> float | None:
    """Resistance of a value such as '10k', '4.7k', '4k7', '1M' or '470'; else None."""
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([rRkKmM]?)(\d*)\s*(?:ohm|Ω)?\s*", value)
    if not match:
        return None
    number, unit, tail = match.groups()
    if tail:
        number = f"{number}.{tail}"
    return float(number) * _UNITS[unit.lower()]


def _net_of(design: dict) -> dict[tuple[str, str], str]:
    return {(cid, pin): net["id"] for net in design["nets"] for cid, pin in net["members"]}


def design_review_flags(design: dict) -> list[dict]:
    """Each design-review question the intended circuit raises."""
    parts = {item["id"]: item for item in design["components"]}
    net_of = _net_of(design)
    flags = []
    rails: set[str] = {item["net"] for item in design.get("power_assertions", [])}
    for cid, part in parts.items():
        if part["asset"].startswith("Amplifier_Operational:"):
            rails |= {net_of[(cid, pin)] for pin in OPAMP_SUPPLY if (cid, pin) in net_of}
    for cid, part in sorted(parts.items(), key=lambda item: item[1]["refdes"]):
        asset = part["asset"]
        if asset.startswith("Timer:") and "555" in asset:
            vcc, ret = (net_of.get((cid, pin)) for pin in TIMER_SUPPLY)
            bypass = [
                other["refdes"]
                for oid, other in parts.items()
                if other["asset"] == "Device:C"
                and {net_of.get((oid, "1")), net_of.get((oid, "2"))} == {vcc, ret}
            ]
            if not bypass:
                flags.append(
                    {
                        "flag": "timer_supply_bypass_missing",
                        "parts": [part["refdes"]],
                        "detail": f"no capacitor from {vcc} to {ret} near {part['refdes']} "
                        "pins 8 and 1; a control-pin capacitor does not replace supply "
                        "bypassing",
                    }
                )
        if asset.startswith("Regulator_Linear:"):
            flags.append(
                {
                    "flag": "regulator_datasheet_checks_unrecorded",
                    "parts": [part["refdes"]],
                    "detail": f"{part['value']}: input-voltage headroom, load current, thermal "
                    "dissipation and the datasheet's capacitor and stability requirements "
                    "are not recorded",
                }
            )
        if asset.startswith("Amplifier_Operational:"):
            supply = [net_of.get((cid, pin)) for pin in OPAMP_SUPPLY]
            flags.append(
                {
                    "flag": "opamp_swing_unverified",
                    "parts": [part["refdes"]],
                    "detail": f"{part['value']} input common-mode and output swing against "
                    f"rails {supply[0]}/{supply[1]}, input bias and loading are not verified",
                }
            )
    for net in design["nets"]:
        resistors = [(cid, pin) for cid, pin in net["members"] if parts[cid]["asset"] == "Device:R"]
        ends = []
        for cid, pin in resistors:
            other = "2" if pin == "1" else "1"
            ends.append((cid, net_of.get((cid, other))))
        to_rails = [(cid, end) for cid, end in ends if end in rails]
        if len(to_rails) >= 2 and len({end for _cid, end in to_rails}) >= 2:
            (first, a), (second, b) = to_rails[:2]
            values = [_ohms(parts[first]["value"]), _ohms(parts[second]["value"])]
            thevenin = (
                values[0] * values[1] / (values[0] + values[1]) if None not in values else None
            )
            flags.append(
                {
                    "flag": "divider_reference",
                    "parts": sorted([parts[first]["refdes"], parts[second]["refdes"]]),
                    "net": net["id"],
                    "thevenin_ohms": thevenin,
                    "detail": f"{net['id']} is a resistor divider between {a} and {b}"
                    + (f" with about {thevenin / 1e3:g} kΩ source impedance" if thevenin else "")
                    + "; it is not a stiff reference unless buffered, so its loads need review",
                }
            )
    return flags
