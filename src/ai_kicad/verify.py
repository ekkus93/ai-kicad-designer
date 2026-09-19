"""Independent observed schematic inventory, NC positions and KiCad XML nets."""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import xml.etree.ElementTree as ET

from .sexpr import ParseError, children, one, parse


@dataclass(frozen=True)
class ObservedElectricalGraph:
    inventory: dict[str, tuple[str, tuple[str, ...], str]]
    nets: dict[str, frozenset[tuple[str, str]]]
    xml_components: dict[str, tuple[str, str]]
    no_connects: frozenset[tuple[str, str]]


def _nm(value: str) -> int:
    number = Decimal(str(value)) * 1_000_000
    if number != number.to_integral_value():
        raise ParseError(f"off-nanometer schematic coordinate: {value}")
    return int(number)


def observe_electrical(schematic: Path, xml_path: Path) -> ObservedElectricalGraph:
    tree = parse(schematic.read_text())
    if tree[0] != "kicad_sch":
        raise ParseError("not a KiCad schematic")
    definitions = {}
    for symbol in children(one(tree, "lib_symbols"), "symbol"):
        lib_id = symbol[1]
        pins = {}
        for unit in children(symbol, "symbol"):
            for pin in children(unit, "pin"):
                number = str(one(pin, "number")[1])
                at = one(pin, "at")
                if number in pins:
                    raise ParseError(f"ambiguous embedded pin inventory: {lib_id}")
                pins[number] = (_nm(at[1]), _nm(at[2]))
        if lib_id in definitions:
            raise ParseError(f"duplicate embedded symbol: {lib_id}")
        definitions[lib_id] = pins
    inventory = {}
    physical_positions = {}
    for instance in children(tree, "symbol"):
        lib_id = one(instance, "lib_id")[1]
        properties = {p[1]: p[2] for p in children(instance, "property")}
        ref = properties.get("Reference")
        value = properties.get("Value")
        actual_pins = tuple(sorted(str(pin[1]) for pin in children(instance, "pin")))
        if (
            ref in inventory
            or lib_id not in definitions
            or actual_pins != tuple(sorted(definitions[lib_id]))
        ):
            raise ParseError(f"invalid symbol/pin instance: {ref}")
        at = one(instance, "at")
        if len(at) != 4 or str(at[3]) != "0":
            raise ParseError("unsupported M1 symbol orientation")
        x, y = _nm(at[1]), _nm(at[2])
        for pin, (px, py) in definitions[lib_id].items():
            physical_positions.setdefault((x + px, y - py), []).append((ref, pin))
        inventory[ref] = (lib_id, actual_pins, value)
    markers = children(tree, "no_connect")
    no_connects = set()
    for marker in markers:
        at = one(marker, "at")
        position = (_nm(at[1]), _nm(at[2]))
        terminals = physical_positions.get(position, [])
        if len(terminals) != 1 or terminals[0] in no_connects:
            raise ParseError(f"NC marker lacks one unique physical pin: {position}")
        no_connects.add(terminals[0])
    xml_root = ET.parse(xml_path).getroot()
    if xml_root.tag != "export":
        raise ParseError("not a KiCad XML export")
    xml_components = {}
    for comp in xml_root.findall("./components/comp"):
        ref = comp.attrib["ref"]
        libsource = comp.find("libsource")
        if libsource is None or ref in xml_components:
            raise ParseError(f"invalid XML component: {ref}")
        xml_pins = tuple(sorted(pin.attrib["num"] for pin in comp.findall("./units/unit/pins/pin")))
        if ref not in inventory or xml_pins != inventory[ref][1]:
            raise ParseError(f"XML physical pin inventory differs: {ref}")
        xml_components[ref] = (
            f"{libsource.attrib['lib']}:{libsource.attrib['part']}",
            comp.findtext("value", ""),
        )
    nets = {}
    assigned = set()
    xml_nc = set()
    for net in xml_root.findall("./nets/net"):
        name = net.attrib["name"]
        nodes = net.findall("node")
        members = frozenset((node.attrib["ref"], node.attrib["pin"]) for node in nodes)
        if not members or name in nets or assigned.intersection(members):
            raise ParseError(f"invalid/duplicate XML net: {name}")
        assigned.update(members)
        if name.startswith("unconnected-"):
            if len(nodes) != 1:
                raise ParseError("malformed KiCad unconnected terminal")
            if nodes[0].attrib.get("pintype", "").endswith("+no_connect"):
                xml_nc.update(members)
            else:
                nets[name] = members
        else:
            nets[name] = members
    if xml_nc != no_connects:
        raise ParseError(
            f"schematic/XML NC evidence differs: {sorted(no_connects)} versus {sorted(xml_nc)}"
        )
    return ObservedElectricalGraph(inventory, nets, xml_components, frozenset(no_connects))


def verify_electrical(expected: dict, observed: ObservedElectricalGraph) -> dict:
    errors = []
    components = {c["refdes"]: c for c in expected["logical"]["components"]}
    if set(components) != set(observed.inventory) or set(components) != set(
        observed.xml_components
    ):
        errors.append("component inventory mismatch")
    uses = {
        component["refdes"]: use
        for use in expected["schematic"]["symbols"]
        for component in expected["logical"]["components"]
        if component["id"] == use["component"]
    }
    requests = {item["id"]: item["library_id"] for item in expected["assets"]}
    for ref, component in components.items():
        expected_pins = {terminal["number"] for terminal in component["terminals"]}
        observed_instance = observed.inventory.get(ref)
        observed_xml = observed.xml_components.get(ref)
        expected_lib = requests[uses[ref]["asset"]]
        if (
            observed_instance is None
            or observed_instance[0] != expected_lib
            or set(observed_instance[1]) != expected_pins
        ):
            errors.append(f"{ref}: actual schematic pin/library inventory differs")
        if observed_xml is None or observed_xml[0] != expected_lib:
            errors.append(f"{ref}: XML library identity differs")
        if (
            observed_instance is not None
            and observed_xml is not None
            and observed_instance[2] != observed_xml[1]
        ):
            errors.append(f"{ref}: schematic/XML value differs")
        expected_value = "10k" if component["kind"] == "resistor" else expected_lib.split(":", 1)[1]
        if observed_instance is None or observed_instance[2] != expected_value:
            errors.append(f"{ref}: actual value differs from expected IR")
        if set(uses[ref]["pin_map"]) != expected_pins:
            errors.append(f"{ref}: intended pin map differs from physical numbering")
    expected_nets = {}
    for net in expected["logical"]["nets"]:
        members = frozenset(
            (
                next(c["refdes"] for c in components.values() if c["id"] == member["component"]),
                next(
                    t["number"]
                    for c in components.values()
                    if c["id"] == member["component"]
                    for t in c["terminals"]
                    if t["id"] == member["terminal"]
                ),
            )
            for member in net["members"]
        )
        expected_nets["/" + net["name"]] = members
    if observed.nets != expected_nets:
        for name in sorted(expected_nets.keys() | observed.nets.keys()):
            wanted, actual = (
                expected_nets.get(name, frozenset()),
                observed.nets.get(name, frozenset()),
            )
            if wanted != actual:
                errors.append(f"{name}: expected {sorted(wanted)}, observed {sorted(actual)}")
    expected_nc = {
        (
            next(
                c["refdes"] for c in components.values() if c["id"] == item["terminal"]["component"]
            ),
            next(
                t["number"]
                for c in components.values()
                if c["id"] == item["terminal"]["component"]
                for t in c["terminals"]
                if t["id"] == item["terminal"]["terminal"]
            ),
        )
        for item in expected["logical"]["no_connects"]
    }
    if observed.no_connects != expected_nc:
        errors.append(
            f"intentional NC evidence differs: expected {sorted(expected_nc)}, observed {sorted(observed.no_connects)}"
        )
    inventoried = {(ref, pin) for ref, (_, pins, _) in observed.inventory.items() for pin in pins}
    observed_members = set().union(*observed.nets.values()) if observed.nets else set()
    accounted = observed_members | observed.no_connects
    if inventoried != accounted:
        errors.append(
            f"physical terminal coverage differs: missing {sorted(inventoried - accounted)}, extra {sorted(accounted - inventoried)}"
        )
    return {
        "status": "pass" if not errors else "fail",
        "diagnostics": errors,
        "expected_nets": {k: sorted(v) for k, v in expected_nets.items()},
        "observed_nets": {k: sorted(v) for k, v in observed.nets.items()},
        "expected_nc": sorted(expected_nc),
        "observed_nc": sorted(observed.no_connects),
    }
