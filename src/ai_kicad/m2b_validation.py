"""Implementation details for m2b validation."""

from __future__ import annotations

import copy
import json
import re

from .assets import _extract_symbol, sha256
from .ir import InputError
from .m2a import ROOT, Asset, Pin, _nm, load_assets
from .m2b import (
    EXTRA,
    LOCKED_PIN_ROLES,
    POWER_STAGE_ASSETS,
)
from .sexpr import children, one, parse, quote


def assets() -> dict[str, Asset]:
    result = load_assets()
    lock = json.loads((ROOT / "fixtures/m2b/assets.lock.json").read_text())
    if (
        set(lock) != {"schema_version", "source", "license", "assets"}
        or lock["schema_version"] != "m2b.1"
        or set(lock["assets"]) != set(EXTRA.values())
    ):
        raise InputError("M2b asset lock inventory mismatch")
    for lib_id, stem in EXTRA.items():
        source = (ROOT / "fixtures/m2b" / f"{stem}.kicad_sym").read_bytes()
        if sha256(source) != lock["assets"][stem]:
            raise InputError(f"M2b asset hash mismatch: {stem}")
        definition = _extract_symbol(source.decode(), stem).replace(
            f"(symbol {quote(stem)}", f"(symbol {quote(lib_id)}", 1
        )
        units = {}
        bodies = {}
        seen = set()
        for body in children(parse(definition), "symbol"):
            number = int(body[1].rsplit("_", 2)[-2])
            pins = []
            for pin in children(body, "pin"):
                n = str(one(pin, "number")[1])
                if n in seen or children(pin, "hide"):
                    raise InputError("unsupported duplicate or hidden pin")
                seen.add(n)
                at = one(pin, "at")
                pins.append(Pin(n, str(one(pin, "name")[1]), pin[1], _nm(at[1]), _nm(at[2])))
            if pins:
                units[number] = tuple(pins)
            points = []
            for shape in body[2:]:
                if isinstance(shape, list) and shape[0] == "rectangle":
                    points += [one(shape, "start"), one(shape, "end")]
                elif isinstance(shape, list) and shape[0] == "polyline":
                    points += [xy for pts in children(shape, "pts") for xy in children(pts, "xy")]
            if points:
                xs, ys = [_nm(p[1]) for p in points], [_nm(p[2]) for p in points]
                bodies[number] = (min(xs), max(ys), max(xs), min(ys))
        if 0 in units:
            common = units.pop(0)
            if 1 not in units or {p.number for p in common} & {p.number for p in units[1]}:
                raise InputError("unsupported common physical pins")
            units[1] = common + units[1]
        if (
            lib_id in LOCKED_PIN_ROLES
            and {p.number: p.name for pins in units.values() for p in pins}
            != LOCKED_PIN_ROLES[lib_id]
        ):
            raise InputError(f"locked physical pin roles changed: {lib_id}")
        result[lib_id] = Asset(lib_id, definition, units, bodies)
    return result


def _fields(item, required, optional=()):
    if (
        not isinstance(item, dict)
        or not set(required) <= set(item)
        or set(item) - set(required) - set(optional)
    ):
        raise InputError(f"unsupported fields: expected {required}, optional {optional}")


def _validate_power_assertions(
    data: dict,
    components: dict[str, dict],
    nets: dict[str, set[tuple[str, str]]],
    resolved: dict[str, Asset],
) -> None:
    """Validate authored source claims against resolved terminal electrical roles."""
    terminal_types = {
        (component["id"], pin.number): pin.electrical_type
        for component in components.values()
        for pins in resolved[component["asset"]].units.values()
        for pin in pins
    }
    assertions_by_net: dict[str, list[dict]] = {}
    for assertion in data["power_assertions"]:
        assertions_by_net.setdefault(assertion["net"], []).append(assertion)

    diagnostics = []
    for net, assertions in sorted(assertions_by_net.items()):
        drivers = sorted(
            terminal for terminal in nets[net] if terminal_types[terminal] == "power_out"
        )
        if drivers:
            diagnostics.append(
                "POWER_ASSERTION_DRIVER_CONFLICT: authored PWR_FLAG assertion(s) "
                f"{sorted(item['id'] for item in assertions)} on net {net!r} conflict with "
                f"resolved Power-output terminal(s) {drivers}"
            )
        if len(assertions) > 1:
            diagnostics.append(
                "POWER_ASSERTION_DRIVER_CONFLICT: multiple authored PWR_FLAG power-output "
                f"assertions share net {net!r}: {sorted(item['id'] for item in assertions)}"
            )

    for relation in sorted(
        (item for item in data["relationships"] if item["kind"] == "power_stage"),
        key=lambda item: item["id"],
    ):
        net = relation["input"]
        members = nets[net]
        types = {terminal_types[terminal] for terminal in members}
        if "power_out" in types:
            continue
        interface_terminals = sorted(
            terminal
            for terminal in members
            if components[terminal[0]]["asset"].startswith("Connector_")
        )
        if not interface_terminals or not types <= {"passive", "power_in"}:
            diagnostics.append(
                "POWER_SOURCE_EVIDENCE_UNPROVEN: power-stage input "
                f"{relation['id']!r} on net {net!r} has no resolved Power-output terminal, and "
                "the current profile cannot prove a passive external-supply interface; "
                f"resolved electrical roles are {sorted(types)}"
            )
        elif net not in assertions_by_net:
            diagnostics.append(
                "POWER_SOURCE_ASSERTION_REQUIRED: power-stage input "
                f"{relation['id']!r} on externally supplied net {net!r} requires an explicit "
                f"PWR_FLAG assertion; interface terminals are {interface_terminals}"
            )

    if diagnostics:
        raise InputError("; ".join(diagnostics))


def validate(raw: dict, resolved: dict[str, Asset]) -> dict:
    _fields(
        raw,
        (
            "profile",
            "id",
            "name",
            "components",
            "nets",
            "relationships",
            "no_connects",
            "power_assertions",
        ),
    )
    if (
        raw["profile"] != "m2b.1"
        or not re.fullmatch(r"[a-z][a-z0-9_-]*", raw["id"])
        or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", raw["name"])
    ):
        raise InputError("unsupported M2b profile or project identity")
    data = copy.deepcopy(raw)
    components = {}
    refs = set()
    for c in data["components"]:
        _fields(c, ("id", "refdes", "asset", "value"), ("functions",))
        if (
            c["id"] in components
            or c["asset"] not in resolved
            or not re.fullmatch(r"[A-Z]+[1-9][0-9]*", c["refdes"])
            or c["refdes"] in refs
            or not isinstance(c["value"], str)
            or not c["value"]
            or len(c["value"]) > 36
        ):
            raise InputError("invalid component identity, asset or value")
        components[c["id"]] = c
        refs.add(c["refdes"])
        if c["asset"] == "Amplifier_Operational:NE5532":
            functions = c.get("functions")
            if not isinstance(functions, list) or {f.get("unit") for f in functions} != {1, 2, 3}:
                raise InputError("NE5532 requires all three function units")
            for f in functions:
                _fields(f, ("id", "role", "unit", "pins"))
                wanted = {
                    1: {"out": "1", "minus": "2", "plus": "3"},
                    2: {"out": "7", "minus": "6", "plus": "5"},
                    3: {"negative": "4", "positive": "8"},
                }[f["unit"]]
                if f["pins"] != wanted or f["role"] not in (
                    "buffer",
                    "amplifier",
                    "parked_buffer",
                    "supply",
                ):
                    raise InputError("wrong NE5532 physical function mapping")
        elif "functions" in c:
            raise InputError("functions unsupported for this asset")
    if len(data["components"]) != len(components):
        raise InputError("duplicate component")
    pin_inventory = {
        (c["id"], p.number)
        for c in components.values()
        for unit in resolved[c["asset"]].units.values()
        for p in unit
    }
    nets = {}
    membership = []
    for net in data["nets"]:
        _fields(net, ("id", "members"))
        if (
            net["id"] in nets
            or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", net["id"])
            or len(net["members"]) < 2
        ):
            raise InputError("invalid net")
        members = [tuple(m) for m in net["members"]]
        if any(len(m) != 2 for m in members) or len(set(members)) != len(members):
            raise InputError("duplicate/invalid net members")
        nets[net["id"]] = set(members)
        membership += members
    if (
        len(membership) != len(set(membership))
        or set(membership) != pin_inventory
        or data["no_connects"]
    ):
        raise InputError("physical terminal inventory incomplete or unsupported NC")
    kinds = {
        "series": ({"component", "input", "output"}, set()),
        "shunt": ({"component", "node", "reference"}, set()),
        "polarity": ({"component", "anode", "cathode"}, set()),
        "signal_flow": ({"input", "output"}, set()),
        "amplifier": (
            {"component", "function", "input", "output"},
            {"reference", "unused"},
        ),
        "feedback": (
            {"component", "function", "source", "sense", "net", "polarity"},
            {"resistor"},
        ),
        "power_rails": (
            {"component", "unit", "positive", "negative", "reference"},
            set(),
        ),
        "decoupling": ({"component", "consumer", "supply", "return"}, set()),
        "power_stage": (
            {"component", "input", "output", "reference", "pins", "polarity"},
            set(),
        ),
        "timer": (
            {
                "component",
                "supply",
                "reference",
                "output",
                "timing",
                "discharge",
                "control",
                "pins",
            },
            set(),
        ),
        "timing_ladder": (
            {
                "upper",
                "lower",
                "capacitor",
                "supply",
                "discharge",
                "timing",
                "reference",
            },
            set(),
        ),
        "bridge": ({"component", "first", "second", "purpose"}, set()),
        "reference_divider": (
            {"upper", "lower", "positive", "local", "negative"},
            set(),
        ),
    }
    relations = {}
    for r in data["relationships"]:
        if not isinstance(r, dict) or r.get("kind") not in kinds:
            raise InputError("unsupported relationship")
        required, optional = kinds[r["kind"]]
        try:
            _fields(r, required | {"id", "kind"}, optional)
        except InputError as exc:
            raise InputError("unsupported relationship fields") from exc
        if r["id"] in relations:
            raise InputError("duplicate relationship ID")
        relations[r["id"]] = r
        for key in (
            "input",
            "output",
            "node",
            "reference",
            "anode",
            "cathode",
            "net",
            "positive",
            "negative",
            "supply",
            "return",
            "timing",
            "discharge",
            "control",
            "first",
            "second",
            "local",
        ):
            if key in r and r[key] not in nets:
                raise InputError(f"relationship {r['id']}: unknown net {key}")
        if "component" in r and r["component"] not in components:
            raise InputError("relationship component missing")
        if r["kind"] == "series" and not (
            {(r["component"], "1")} <= nets[r["input"]]
            and {(r["component"], "2")} <= nets[r["output"]]
        ):
            raise InputError("series terminal/net mismatch")
        if r["kind"] == "shunt" and not (
            {(r["component"], "1")} <= nets[r["node"]]
            and {(r["component"], "2")} <= nets[r["reference"]]
        ):
            raise InputError("shunt terminal/net mismatch")
        if r["kind"] == "polarity":
            pin_names = {
                p.name: p.number for p in resolved[components[r["component"]]["asset"]].units[1]
            }
            if (
                pin_names.get("A") is None
                or {(r["component"], pin_names["A"])} - nets[r["anode"]]
                or {(r["component"], pin_names["K"])} - nets[r["cathode"]]
            ):
                raise InputError("diode polarity mismatch")
        if r["kind"] == "feedback" and (
            r["polarity"] != "negative" or (r["component"], r["source"]) not in nets[r["net"]]
        ):
            raise InputError("feedback source/polarity mismatch")
        if r["kind"] == "decoupling" and not isinstance(r["consumer"], list):
            raise InputError("invalid support consumer")
        if r["kind"] == "decoupling":
            cid = r["component"]
            if (
                tuple(r["consumer"]) not in pin_inventory
                or (cid, "1") not in nets[r["supply"]]
                or (cid, "2") not in nets[r["return"]]
            ):
                raise InputError("support relation physical terminal/net mismatch")
        if r["kind"] == "power_rails" and (
            (r["component"], "8") not in nets[r["positive"]]
            or (r["component"], "4") not in nets[r["negative"]]
        ):
            raise InputError("power relation physical terminal/net mismatch")
        if r["kind"] == "power_stage":
            if set(r["pins"]) != {"input", "output", "reference"} or r["polarity"] not in (
                "positive",
                "negative",
            ):
                raise InputError("invalid power stage pin roles")
            asset_id = components[r["component"]]["asset"]
            adapter = POWER_STAGE_ASSETS.get(asset_id)
            if adapter is None or adapter["polarity"] != r["polarity"]:
                raise InputError("unsupported physical power-stage polarity")
            asset = resolved[asset_id]
            actual = {p.number: p.name for pins in asset.units.values() for p in pins}
            for role in ("input", "output", "reference"):
                number = r["pins"][role]
                if number not in actual or (r["component"], number) not in nets[r[role]]:
                    raise InputError("power stage physical pin/net mismatch")
            if any(actual[r["pins"][role]] != adapter["roles"][role] for role in r["pins"]):
                raise InputError("power stage actual pin role mismatch")
        if r["kind"] == "timer":
            expected_roles = {
                "supply": "VCC",
                "reference": "GND",
                "output": "OUT",
                "trigger": "TRIG",
                "threshold": "THRES",
                "discharge": "DISCH",
                "control": "CONT",
                "reset": "~{RST}",
            }
            asset = resolved[components[r["component"]]["asset"]]
            actual = {p.number: p.name for pins in asset.units.values() for p in pins}
            if set(r["pins"]) != set(expected_roles) or any(
                actual.get(r["pins"][role]) != name for role, name in expected_roles.items()
            ):
                raise InputError("timer actual physical pin roles differ")
            role_net = {
                "supply": r["supply"],
                "reset": r["supply"],
                "reference": r["reference"],
                "output": r["output"],
                "trigger": r["timing"],
                "threshold": r["timing"],
                "discharge": r["discharge"],
                "control": r["control"],
            }
            if any(
                (r["component"], r["pins"][role]) not in nets[net] for role, net in role_net.items()
            ):
                raise InputError("timer physical terminal/net mismatch")
        if r["kind"] == "timing_ladder":
            for role in ("upper", "lower", "capacitor"):
                if r[role] not in components:
                    raise InputError("timing ladder component missing")
            wanted = (
                ("upper", "1", "supply"),
                ("upper", "2", "discharge"),
                ("lower", "1", "discharge"),
                ("lower", "2", "timing"),
                ("capacitor", "1", "timing"),
                ("capacitor", "2", "reference"),
            )
            if any((r[role], pin) not in nets[r[net]] for role, pin, net in wanted):
                raise InputError("timing ladder physical terminal/net mismatch")
        if r["kind"] == "bridge" and (
            r["purpose"] != "feedback"
            or (
                (r["component"], "1") not in nets[r["first"]]
                or (r["component"], "2") not in nets[r["second"]]
            )
        ):
            raise InputError("bridge physical terminal/net mismatch")
        if r["kind"] == "reference_divider" and (
            r["upper"] not in components
            or r["lower"] not in components
            or any(
                (r[component], pin) not in nets[r[net]]
                for component, pin, net in (
                    ("upper", "1", "positive"),
                    ("upper", "2", "local"),
                    ("lower", "1", "local"),
                    ("lower", "2", "negative"),
                )
            )
        ):
            raise InputError("reference divider physical terminal/net mismatch")
    for a in data["power_assertions"]:
        _fields(a, ("id", "refdes", "net"))
        if (
            a["net"] not in nets
            or a["refdes"] in refs
            or not re.fullmatch(r"#FLG[0-9]+", a["refdes"])
        ):
            raise InputError("invalid power assertion")
        refs.add(a["refdes"])
    if len({a["id"] for a in data["power_assertions"]}) != len(data["power_assertions"]):
        raise InputError("duplicate power assertion ID")
    _validate_power_assertions(data, components, nets, resolved)
    for key in ("components", "nets", "relationships", "power_assertions"):
        data[key].sort(key=lambda item: item["id"])
    for component in data["components"]:
        if "functions" in component:
            component["functions"].sort(key=lambda item: item["unit"])
    for net in data["nets"]:
        net["members"].sort()
    return data
