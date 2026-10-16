"""Implementation details for m2a artifacts."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from .ir import InputError
from .m2a import PITCH
from .m2a_core import (
    Asset,
    Scene,
    _assert_scene_certificate,
    _nm,
    _uid,
)
from .schematic import _mm
from .sexpr import children, one, parse, quote


def emit(design: dict, assets: dict[str, Asset], scene: Scene, out: Path) -> Path:
    _assert_scene_certificate(scene, design, assets)
    project = out / "project"
    project.mkdir(parents=True, exist_ok=True)
    root = _uid(design, "sheet", "root")
    name = design["name"]
    lines = [
        '(kicad_sch (version 20250114) (generator "ai_kicad") (generator_version "0.1.0")',
        f'  (uuid {quote(root)}) (paper "A4")',
        "  (lib_symbols",
    ]
    lines.extend(assets[k].definition for k in sorted(assets))
    lines.append("  )")
    for i, (a, b) in enumerate(scene.wires):
        lines.append(
            f"  (wire (pts (xy {_mm(a[0])} {_mm(a[1])}) (xy {_mm(b[0])} {_mm(b[1])})) "
            f"(stroke (width 0) (type default)) (uuid {quote(_uid(design, 'wire', str(i)))}) )"
        )
    for i, (x, y) in enumerate(scene.junctions):
        lines.append(
            f"  (junction (at {_mm(x)} {_mm(y)}) (diameter 0) (color 0 0 0 0) "
            f"(uuid {quote(_uid(design, 'junction', str(i)))}) )"
        )
    for i, (net, (x, y)) in enumerate(scene.labels):
        lines.append(
            f"  (label {quote(net)} (at {_mm(x)} {_mm(y)} 0) "
            f"(effects (font (size 1.27 1.27)) (justify left bottom)) "
            f"(uuid {quote(_uid(design, 'label', str(i)))}) )"
        )
    components = {c["id"]: c for c in design["components"]}
    components.update(
        {
            a["id"]: {
                "id": a["id"],
                "refdes": a["refdes"],
                "asset": "power:PWR_FLAG",
                "value": "PWR_FLAG",
            }
            for a in design["power_assertions"]
        }
    )
    for component, unit in sorted(scene.positions):
        c = components[component]
        asset = assets[c["asset"]]
        x, y = scene.positions[(component, unit)]
        ref = c["refdes"]
        lines.append(
            f"  (symbol (lib_id {quote(asset.library_id)}) (at {_mm(x)} {_mm(y)} {scene.angles.get((component, unit), 0)}) "
            f"(unit {unit or 1}) (in_bom yes) (on_board yes) (dnp no) "
            f"(uuid {quote(_uid(design, 'symbol', component + ':' + str(unit)))})"
        )
        tx, ty = scene.text_positions.get((component, unit), (x + 10 * PITCH, y - 8 * PITCH))
        text_angle = scene.text_angles.get((component, unit), 0)
        hidden = "(hide yes) " if c["asset"] == "power:PWR_FLAG" else ""
        lines.append(
            f'    (property "Reference" {quote(ref)} (at {_mm(tx)} {_mm(ty)} {text_angle}) '
            f"{hidden}(effects (font (size 1.27 1.27))))"
        )
        lines.append(
            f'    (property "Value" {quote(c["value"])} (at {_mm(tx)} {_mm(ty + 2 * PITCH)} {text_angle}) '
            f"{hidden}(effects (font (size 1.27 1.27))))"
        )
        for pin in asset.units.get(unit, asset.units.get(0, ())):
            lines.append(
                f"    (pin {quote(pin.number)} "
                f"(uuid {quote(_uid(design, 'pin', component + ':' + str(unit) + ':' + pin.number))}))"
            )
        lines.append(
            f"    (instances (project {quote(name)} (path {quote('/' + root)} "
            f"(reference {quote(ref)}) (unit {unit or 1})))) )"
        )
    lines += ["  (embedded_fonts no)", ")"]
    schematic = project / f"{name}.kicad_sch"
    schematic.write_text("\n".join(lines) + "\n")
    (project / f"{name}.kicad_pro").write_text(
        json.dumps({"meta": {"filename": f"{name}.kicad_pro", "version": 1}}, indent=2) + "\n"
    )
    return schematic


def verify_serialized_scene(design: dict, scene: Scene, schematic: Path) -> None:
    """Resolve emitted integer coordinates and compare them to the frozen scene."""
    if scene.certificate_digest is None:
        raise InputError("SCENE_CERTIFICATE_MISSING")
    _assert_scene_certificate(scene)
    tree = parse(schematic.read_text())
    wires = []
    for wire in children(tree, "wire"):
        points = children(one(wire, "pts"), "xy")
        if len(points) != 2:
            raise InputError("SERIALIZED_SCENE_WIRE_POINTS")
        wires.append(tuple((_nm(point[1]), _nm(point[2])) for point in points))
    labels = [
        (label[1], (_nm(one(label, "at")[1]), _nm(one(label, "at")[2])))
        for label in children(tree, "label")
    ]
    junctions = [
        (_nm(one(junction, "at")[1]), _nm(one(junction, "at")[2]))
        for junction in children(tree, "junction")
    ]
    if tuple(wires) != tuple(scene.wires):
        raise InputError("SERIALIZED_SCENE_WIRES_CHANGED")
    if tuple(labels) != tuple(scene.labels):
        raise InputError("SERIALIZED_SCENE_LABELS_CHANGED")
    if tuple(junctions) != tuple(scene.junctions):
        raise InputError("SERIALIZED_SCENE_JUNCTIONS_CHANGED")

    references = {component["refdes"]: component["id"] for component in design["components"]}
    references.update(
        (assertion["refdes"], assertion["id"]) for assertion in design["power_assertions"]
    )
    serialized_positions = {}
    serialized_angles = {}
    serialized_text = {}
    serialized_text_angles = {}
    for symbol in children(tree, "symbol"):
        properties = {item[1]: item for item in children(symbol, "property")}
        reference = properties.get("Reference")
        value = properties.get("Value")
        if reference is None or value is None or reference[2] not in references:
            raise InputError("SERIALIZED_SCENE_SYMBOL_IDENTITY")
        unit = int(one(symbol, "unit")[1])
        key = (references[reference[2]], unit)
        if key in serialized_positions:
            raise InputError(f"SERIALIZED_SCENE_SYMBOL_DUPLICATE: {key}")
        at = one(symbol, "at")
        serialized_positions[key] = (_nm(at[1]), _nm(at[2]))
        serialized_angles[key] = int(at[3])
        text_at = one(reference, "at")
        value_at = one(value, "at")
        text_point = (_nm(text_at[1]), _nm(text_at[2]))
        if (_nm(value_at[1]), _nm(value_at[2])) != (
            text_point[0],
            text_point[1] + 2 * PITCH,
        ):
            raise InputError(f"SERIALIZED_SCENE_VALUE_POSITION: {key}")
        if int(value_at[3]) != int(text_at[3]):
            raise InputError(f"SERIALIZED_SCENE_VALUE_ANGLE: {key}")
        serialized_text[key] = text_point
        serialized_text_angles[key] = int(text_at[3])
    if serialized_positions != dict(scene.positions):
        raise InputError("SERIALIZED_SCENE_SYMBOL_POSITIONS_CHANGED")
    if serialized_angles != {key: scene.angles.get(key, 0) for key in scene.positions}:
        raise InputError("SERIALIZED_SCENE_SYMBOL_ANGLES_CHANGED")
    if serialized_text != dict(scene.text_positions):
        raise InputError("SERIALIZED_SCENE_TEXT_POSITIONS_CHANGED")
    if serialized_text_angles != {key: scene.text_angles.get(key, 0) for key in scene.positions}:
        raise InputError("SERIALIZED_SCENE_TEXT_ANGLES_CHANGED")
    _assert_scene_certificate(scene)


def observe(schematic: Path, xml_path: Path) -> dict:
    """Discover units, pins and connectivity from emitted bytes and KiCad XML only."""
    tree = parse(schematic.read_text())
    definitions = {}
    for symbol in children(one(tree, "lib_symbols"), "symbol"):
        units = {}
        seen_physical = set()
        for body in children(symbol, "symbol"):
            number = int(body[1].rsplit("_", 2)[-2])
            pins = {}
            for pin in children(body, "pin"):
                identity = str(one(pin, "number")[1])
                at = one(pin, "at")
                if children(pin, "hide") or identity in seen_physical:
                    raise InputError("hidden or stacked embedded pin unsupported in M2a")
                seen_physical.add(identity)
                if identity in pins:
                    raise InputError("duplicate embedded physical pin")
                pins[identity] = {
                    "name": str(one(pin, "name")[1]),
                    "type": pin[1],
                    "x": _nm(at[1]),
                    "y": _nm(at[2]),
                }
            if pins:
                units[number] = pins
        if 0 in units:
            common = units.pop(0)
            units[1] = {**common, **units.get(1, {})}
        definitions[symbol[1]] = units
    occurrences = {}
    pin_positions = {}
    for symbol in children(tree, "symbol"):
        lib = one(symbol, "lib_id")[1]
        references = [p[2] for p in children(symbol, "property") if p[1] == "Reference"]
        if len(references) != 1:
            raise InputError("observed required reference text missing")
        ref = references[0]
        unit = int(one(symbol, "unit")[1])
        declared = {str(p[1]) for p in children(symbol, "pin")}
        actual = definitions[lib].get(unit, {})
        if declared != set(actual) or (ref, unit) in occurrences:
            raise InputError(f"invalid actual occurrence pins: {ref} unit {unit}")
        at = one(symbol, "at")
        angle = int(at[3])
        if angle not in (0, 90, 180, 270):
            raise InputError("unsupported occurrence rotation")
        x, y = _nm(at[1]), _nm(at[2])
        for pin, info in actual.items():
            px, py = info["x"], -info["y"]
            dx, dy = {0: (px, py), 90: (py, -px), 180: (-px, -py), 270: (-py, px)}[angle]
            pin_positions[(ref, pin)] = (x + dx, y + dy)
        properties = {
            prop[1]: {
                "value": prop[2],
                "position": (_nm(one(prop, "at")[1]), _nm(one(prop, "at")[2])),
            }
            for prop in children(symbol, "property")
            if prop[1] in ("Reference", "Value")
        }
        occurrences[(ref, unit)] = {
            "lib": lib,
            "pins": actual,
            "uuid": one(symbol, "uuid")[1],
            "properties": properties,
        }
    xml = ET.parse(xml_path).getroot()
    xml_components = {}
    for comp in xml.findall("./components/comp"):
        ref = comp.attrib["ref"]
        units = {
            ord(u.attrib["name"]) - ord("A") + 1: {p.attrib["num"] for p in u.findall("./pins/pin")}
            for u in comp.findall("./units/unit")
        }
        source = one_xml(comp, "libsource")
        xml_components[ref] = {
            "lib": source.attrib["lib"] + ":" + source.attrib["part"],
            "units": units,
        }
    actual_wires = []
    for wire in children(tree, "wire"):
        points = [(_nm(xy[1]), _nm(xy[2])) for xy in children(one(wire, "pts"), "xy")]
        if len(points) != 2:
            raise InputError("unsupported KiCad wire geometry")
        actual_wires.append(tuple(points))
    actual_labels = [
        (label[1], (_nm(one(label, "at")[1]), _nm(one(label, "at")[2])))
        for label in children(tree, "label")
    ]
    actual_junctions = [
        (_nm(one(junction, "at")[1]), _nm(one(junction, "at")[2]))
        for junction in children(tree, "junction")
    ]
    nets = {}
    for net in xml.findall("./nets/net"):
        nets[net.attrib["name"].lstrip("/")] = sorted(
            (n.attrib["ref"], n.attrib["pin"]) for n in net.findall("node")
        )
    return {
        "occurrences": occurrences,
        "xml_components": xml_components,
        "nets": nets,
        "pin_positions": pin_positions,
        "labels": actual_labels,
        "wires": actual_wires,
        "junctions": actual_junctions,
    }


def check_observed_layout(observed: dict) -> dict:
    """Check rendered schematic source geometry independently of compiler scene."""
    wire_endpoints = {point for wire in observed["wires"] for point in wire}
    wire_endpoints.update(point for _, point in observed["labels"])
    physical_occurrences = {
        key: item
        for key, item in observed["occurrences"].items()
        if item["lib"] != "power:PWR_FLAG"
    }
    missing = sorted(
        (ref, pin)
        for (ref, pin), point in observed["pin_positions"].items()
        if ref in {key[0] for key in physical_occurrences} and point not in wire_endpoints
    )
    if missing:
        raise InputError(f"emitted pin endpoint not routed: {missing}")
    for (ref, unit), item in physical_occurrences.items():
        props = item["properties"]
        if set(props) != {"Reference", "Value"} or props["Reference"]["value"] != ref:
            raise InputError(f"{ref} unit {unit}: reference/value text missing")
        for prop in props.values():
            x, y = prop["position"]
            if not (20_320_000 <= x <= 276_680_000 and 25_400_000 <= y <= 184_600_000):
                raise InputError(f"{ref} unit {unit}: text outside page")
            # Conservative KiCad stroke-font keepout around centered 1.27 mm text.
            half_width = max(635_000, len(prop["value"]) * 445_000)
            left, right = x - half_width, x + half_width
            top, bottom = y - 850_000, y + 850_000
            for a, b in observed["wires"]:
                if (
                    a[0] == b[0]
                    and left < a[0] < right
                    and max(min(a[1], b[1]), top) < min(max(a[1], b[1]), bottom)
                ):
                    raise InputError(f"{ref} unit {unit}: wire through reference/value text")
                if (
                    a[1] == b[1]
                    and top < a[1] < bottom
                    and max(min(a[0], b[0]), left) < min(max(a[0], b[0]), right)
                ):
                    raise InputError(f"{ref} unit {unit}: wire through reference/value text")
    amp = next(
        (
            ref
            for (ref, unit), item in physical_occurrences.items()
            if unit == 1 and item["lib"] == "Amplifier_Operational:NE5532"
        ),
        None,
    )
    if amp is None:
        raise InputError("amplifier A occurrence missing")
    first = observed["occurrences"][(amp, 1)]["pins"]
    plus = next(number for number, info in first.items() if info["name"] == "+")
    output = next(number for number, info in first.items() if info["type"] == "output")
    if observed["pin_positions"][(amp, plus)][0] >= observed["pin_positions"][(amp, output)][0]:
        raise InputError("actual amplifier input not left of output")
    return {
        "actual_pin_endpoint_match": True,
        "physical_reference_value_fields": 2 * len(physical_occurrences),
        "text_on_page": True,
        "wire_through_text_count": 0,
        "input_left_of_output": True,
    }


def one_xml(node: ET.Element, tag: str) -> ET.Element:
    found = node.find(tag)
    if found is None:
        raise InputError(f"missing XML {tag}")
    return found


def compare(design: dict, observed: dict) -> dict:
    errors = []
    components = {c["id"]: c for c in design["components"]}
    by_ref = {c["refdes"]: c for c in components.values()}
    virtual = {a["refdes"]: {"asset": "power:PWR_FLAG"} for a in design["power_assertions"]}
    occurrence_refs = {**by_ref, **virtual}
    expected_occurrences = {
        (c["refdes"], unit)
        for c in components.values()
        for unit in ((1, 2, 3) if c["id"] == "amp" else (1,))
    }
    expected_occurrences.update((a["refdes"], 1) for a in design["power_assertions"])
    if set(observed["occurrences"]) != expected_occurrences:
        errors.append("physical package/unit occurrence identity differs")
    for (ref, unit), item in observed["occurrences"].items():
        c = occurrence_refs.get(ref)
        if c is None or item["lib"] != c["asset"]:
            errors.append(f"{ref} unit {unit}: physical package/library differs")
            continue
        if c.get("id") == "amp":
            function = next((f for f in c["functions"] if f["unit"] == unit), None)
            if function is None or set(function["pins"].values()) != set(item["pins"]):
                errors.append(f"{ref} unit {unit}: physical pin inventory differs")
            elif any(
                item["pins"][n]["name"] != {"plus": "+", "minus": "-"}[role]
                for role, n in function["pins"].items()
                if role in ("plus", "minus")
            ):
                # Compare actual library pin semantics, never emitter pin_map metadata.
                errors.append(f"{ref} unit {unit}: amplifier polarity differs")
            if function is not None:
                required_types = {
                    "plus": "input",
                    "minus": "input",
                    "out": "output",
                    "positive": "power_in",
                    "negative": "power_in",
                }
                for role, number in function["pins"].items():
                    if (
                        number in item["pins"]
                        and item["pins"][number]["type"] != required_types[role]
                    ):
                        errors.append(f"{ref} unit {unit}: physical pin type differs")
    xml_components = observed["xml_components"]
    if set(xml_components) != set(by_ref):
        errors.append("KiCad XML physical component inventory differs")
    for ref, c in by_ref.items():
        actual = xml_components.get(ref)
        wanted = {u: set(o["pins"]) for (r, u), o in observed["occurrences"].items() if r == ref}
        if actual is None or actual["lib"] != c["asset"] or actual["units"] != wanted:
            errors.append(f"{ref}: KiCad XML unit/pin inventory differs")
    expected_nets = {}
    for net in design["nets"]:
        expected_nets[net["id"]] = sorted(
            (components[m[0]]["refdes"], m[1]) for m in net["members"]
        )
    for name, members in expected_nets.items():
        if name == "PARK":
            if members not in observed["nets"].values():
                errors.append("parked amplifier connection differs")
        elif observed["nets"].get(name) != members:
            errors.append(f"{name}: real KiCad connectivity differs")
    if len(observed["nets"]) != len(expected_nets):
        errors.append("real KiCad net inventory differs")

    def on_segment(point, a, b):
        return (a[0] == b[0] == point[0] and min(a[1], b[1]) <= point[1] <= max(a[1], b[1])) or (
            a[1] == b[1] == point[1] and min(a[0], b[0]) <= point[0] <= max(a[0], b[0])
        )

    def connected_to(start, destinations):
        reachable = {start}
        for _ in range(len(observed["wires"]) + 1):
            growth = {
                point
                for a, b in observed["wires"]
                if any(on_segment(point, a, b) for point in reachable)
                for point in (a, b)
            }
            if growth <= reachable:
                break
            reachable |= growth
        return bool(reachable & destinations)

    for assertion in design["power_assertions"]:
        flag_position = observed["pin_positions"].get((assertion["refdes"], "1"))
        net_name = assertion["net"]
        member_positions = {
            observed["pin_positions"].get((ref, pin)) for ref, pin in expected_nets[net_name]
        }
        label_positions = {position for label, position in observed["labels"] if label == net_name}
        if flag_position is None or not connected_to(
            flag_position, member_positions | label_positions
        ):
            errors.append(f"{assertion['refdes']}: power assertion not on {net_name}")
    return {
        "status": "pass" if not errors else "fail",
        "diagnostics": errors,
        "expected_nets": expected_nets,
        "observed_nets": observed["nets"],
        "observed_units": sorted([ref, unit] for ref, unit in observed["occurrences"]),
    }
