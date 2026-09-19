"""Independent observed schematic inventory and KiCad XML electrical partition."""

from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

from .sexpr import ParseError, children, one, parse


@dataclass(frozen=True)
class ObservedElectricalGraph:
    # All tuples derive from actual schematic definitions/instances or KiCad XML.
    inventory: dict[str, tuple[str, tuple[str, ...], str]]
    nets: dict[str, frozenset[tuple[str, str]]]
    xml_components: dict[str, tuple[str, str]]


def observe_electrical(schematic: Path, xml_path: Path) -> ObservedElectricalGraph:
    tree = parse(schematic.read_text())
    if tree[0] != "kicad_sch":
        raise ParseError("not a KiCad schematic")
    definitions = {}
    for symbol in children(one(tree, "lib_symbols"), "symbol"):
        lib_id = symbol[1]
        pins = []
        for unit in children(symbol, "symbol"):
            for pin in children(unit, "pin"):
                pins.append(str(one(pin, "number")[1]))
        if lib_id in definitions or len(pins) != len(set(pins)):
            raise ParseError(f"ambiguous embedded pin inventory: {lib_id}")
        definitions[lib_id] = tuple(sorted(pins))
    inventory = {}
    for instance in children(tree, "symbol"):
        lib_id = one(instance, "lib_id")[1]
        properties = {p[1]: p[2] for p in children(instance, "property")}
        ref = properties.get("Reference")
        value = properties.get("Value")
        actual_pins = tuple(sorted(str(pin[1]) for pin in children(instance, "pin")))
        if ref in inventory or lib_id not in definitions or actual_pins != definitions[lib_id]:
            raise ParseError(f"invalid symbol/pin instance: {ref}")
        inventory[ref] = (lib_id, actual_pins, value)
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
    for net in xml_root.findall("./nets/net"):
        name = net.attrib["name"]
        members = frozenset(
            (node.attrib["ref"], node.attrib["pin"]) for node in net.findall("node")
        )
        if not members or name in nets or assigned.intersection(members):
            raise ParseError(f"invalid/duplicate XML net: {name}")
        assigned.update(members)
        nets[name] = members
    return ObservedElectricalGraph(inventory, nets, xml_components)


def verify_electrical(expected: dict, observed: ObservedElectricalGraph) -> dict:
    errors = []
    components = {c["refdes"]: c for c in expected["logical"]["components"]}
    if set(components) != set(observed.inventory) or set(components) != set(
        observed.xml_components
    ):
        errors.append("component inventory mismatch")
    uses = {
        expected_component["refdes"]: use
        for use in expected["schematic"]["symbols"]
        for expected_component in expected["logical"]["components"]
        if expected_component["id"] == use["component"]
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
    inventoried = {(ref, pin) for ref, (_, pins, _) in observed.inventory.items() for pin in pins}
    observed_members = set().union(*observed.nets.values()) if observed.nets else set()
    if inventoried != observed_members:
        errors.append(
            f"XML terminal coverage differs: missing {sorted(inventoried - observed_members)}, extra {sorted(observed_members - inventoried)}"
        )
    return {
        "status": "pass" if not errors else "fail",
        "diagnostics": errors,
        "expected_nets": {k: sorted(v) for k, v in expected_nets.items()},
        "observed_nets": {k: sorted(v) for k, v in observed.nets.items()},
    }
