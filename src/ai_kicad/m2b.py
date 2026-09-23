"""Small semantic analog profile: strict terminals, shared anchors, deterministic geometry."""

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path

from .assets import _extract_symbol, sha256
from .ir import InputError
from .m2a import Asset, Pin, PITCH, ROOT, Scene, _nm, load_assets
from .m2_geometry import ConductorSegment, canonical_conductor_tree, conductor_reachable
from .sexpr import children, one, parse, quote

EXTRA = {
    "Device:R": "R",
    "Device:LED": "LED",
    "Connector_Generic:Conn_01x01": "Conn_01x01",
    "Regulator_Linear:L7805": "L7805",
    "Timer:NE555D": "NE555D",
}

LOCKED_PIN_ROLES = {
    "Regulator_Linear:L7805": {"1": "IN", "2": "GND", "3": "OUT"},
    "Timer:NE555D": {
        "1": "GND",
        "2": "TRIG",
        "3": "OUT",
        "4": "~{RST}",
        "5": "CONT",
        "6": "THRES",
        "7": "DISCH",
        "8": "VCC",
    },
}
POWER_STAGE_ASSETS = {
    "Regulator_Linear:L7805": {
        "polarity": "positive",
        "roles": {"input": "IN", "output": "OUT", "reference": "GND"},
    },
}


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
        "amplifier": ({"component", "function", "input", "output"}, {"reference", "unused"}),
        "feedback": ({"component", "function", "source", "sense", "net", "polarity"}, {"resistor"}),
        "power_rails": ({"component", "unit", "positive", "negative", "reference"}, set()),
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
            {"upper", "lower", "capacitor", "supply", "discharge", "timing", "reference"},
            set(),
        ),
        "bridge": ({"component", "first", "second", "purpose"}, set()),
        "reference_divider": ({"upper", "lower", "positive", "local", "negative"}, set()),
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
        if r["kind"] == "bridge":
            if r["purpose"] != "feedback" or (
                (r["component"], "1") not in nets[r["first"]]
                or (r["component"], "2") not in nets[r["second"]]
            ):
                raise InputError("bridge physical terminal/net mismatch")
        if r["kind"] == "reference_divider":
            if (
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


def _turn(pin: Pin, angle: int) -> tuple[int, int]:
    """KiCad library Y is upward; sheet Y is downward."""
    x, y = pin.x, -pin.y
    return {0: (x, y), 90: (y, -x), 180: (-x, -y), 270: (-y, x)}[angle]


def orientation_for_flow(asset: Asset, first: str, second: str, axis: str) -> int:
    """Select a legal quarter turn from resolved physical pin endpoints."""
    pins = {p.number: p for unit in asset.units.values() for p in unit}
    if first not in pins or second not in pins:
        raise InputError("orientation terminals absent from locked asset")
    for angle in (0, 90, 180, 270):
        a, b = _turn(pins[first], angle), _turn(pins[second], angle)
        if axis == "right" and a[1] == b[1] and a[0] < b[0]:
            return angle
        if axis == "down" and a[0] == b[0] and a[1] < b[1]:
            return angle
    raise InputError("resolved pin geometry cannot satisfy semantic flow")


@dataclass
class Draft:
    design: dict
    resolved: dict[str, Asset]
    positions: dict[tuple[str, int], tuple[int, int]]
    angles: dict[tuple[str, int], int]
    wires: list
    wire_nets: list[str]
    labels: list
    junctions: list
    text_positions: dict

    def point(self, component: str, number: str) -> tuple[int, int]:
        c = next(c for c in self.design["components"] if c["id"] == component)
        unit, pin = next(
            (u, p)
            for u, pins in self.resolved[c["asset"]].units.items()
            for p in pins
            if p.number == number
        )
        x, y = self.positions[(component, unit)]
        dx, dy = _turn(pin, self.angles.get((component, unit), 0))
        return x + dx, y + dy

    def route(self, net: str, *points):
        for a, b in zip(points, points[1:]):
            if a != b:
                if a[0] != b[0] and a[1] != b[1]:
                    raise InputError("internal non-orthogonal routing request")
                self.wires.append((a, b))
                self.wire_nets.append(net)

    def label(self, net: str, point):
        self.labels.append((net, point))

    def add(self, component: str, x: int, y: int, unit: int = 1, angle: int = 0):
        key = (component, unit)
        if key in self.positions:
            raise InputError("duplicate geometry owner")
        self.positions[key] = (x, y)
        self.angles[key] = angle
        asset = next(c for c in self.design["components"] if c["id"] == component)["asset"]
        self.text_positions[key] = (
            (x + 8 * PITCH, y - 2 * PITCH) if asset == "Device:C" else (x, y - 8 * PITCH)
        )


def passive_layout(design: dict, resolved: dict[str, Asset], partial: bool = False) -> Scene:
    """Compose series, shunt and diode relations through net anchors."""
    if not partial:
        from .m2_compose import compose_layout

        return compose_layout(design, resolved)
    relations = design["relationships"]
    series = [r for r in relations if r["kind"] == "series"]
    shunts = [r for r in relations if r["kind"] == "shunt"]
    polarities = [r for r in relations if r["kind"] == "polarity"]
    if not series or not shunts and not polarities:
        raise InputError("unsupported passive composition")
    flows = [r for r in relations if r["kind"] == "signal_flow"]
    s = next((r for r in series if flows and r["input"] == flows[0]["input"]), series[0])
    shunts = [r for r in shunts if r["node"] == s["output"]]
    polarities = [r for r in polarities if r["anode"] == s["output"]]
    if len(shunts) + len(polarities) != 1:
        raise InputError(f"series {s['id']}: no unique downstream shunt/polarity rule")
    final_net = polarities[0]["cathode"] if polarities else s["output"]
    if len(flows) != 1 or flows[0]["input"] != s["input"] or flows[0]["output"] != final_net:
        raise InputError("signal flow relation does not match passive path")
    components = {c["id"]: c for c in design["components"]}
    if components[s["component"]]["asset"] not in ("Device:R", "Device:C"):
        raise InputError("passive series requires a two-terminal passive")
    d = Draft(design, resolved, {}, {}, [], [], [], [], {})
    anchor_x, anchor_y = 96 * PITCH, 64 * PITCH
    d.add(
        s["component"],
        anchor_x,
        anchor_y,
        angle=orientation_for_flow(
            resolved[components[s["component"]]["asset"]], "1", "2", "right"
        ),
    )
    left = d.point(s["component"], "1")
    right = d.point(s["component"], "2")
    net_members = {n["id"]: {tuple(m) for m in n["members"]} for n in design["nets"]}
    ports = {
        net: next(
            (
                cid
                for cid, pin in members
                if pin == "1" and components[cid]["asset"] == "Connector_Generic:Conn_01x01"
            ),
            None,
        )
        for net, members in net_members.items()
    }
    if ports.get(s["input"]) is None:
        raise InputError("missing signal input interface")
    d.add(ports[s["input"]], anchor_x - 31 * PITCH, anchor_y, angle=180)
    source = d.point(ports[s["input"]], "1")
    d.route(s["input"], source, left)
    d.label(s["input"], source)
    if polarities:
        p = polarities[0]
        if s["output"] != p["anode"]:
            raise InputError("series and polarity relations do not compose")
        d.add(
            p["component"],
            anchor_x + 30 * PITCH,
            anchor_y,
            angle=orientation_for_flow(
                resolved[components[p["component"]]["asset"]], "2", "1", "right"
            ),
        )
        anode = d.point(p["component"], "2")
        cathode = d.point(p["component"], "1")
        d.route(s["output"], right, anode)
        if ports.get(p["cathode"]) is None:
            raise InputError("missing return interface")
        d.add(ports[p["cathode"]], anchor_x + 61 * PITCH, anchor_y)
        return_pin = d.point(ports[p["cathode"]], "1")
        d.route(p["cathode"], cathode, return_pin)
        d.label(p["cathode"], return_pin)
    else:
        sh = shunts[0]
        if s["output"] != sh["node"]:
            raise InputError("series and shunt relations do not compose")
        d.add(sh["component"], anchor_x + 30 * PITCH, anchor_y + 22 * PITCH)
        node = (d.positions[(sh["component"], 1)][0], right[1])
        shunt_top, shunt_bottom = d.point(sh["component"], "1"), d.point(sh["component"], "2")
        d.route(s["output"], right, node, shunt_top)
        if ports.get(s["output"]) is None or ports.get(sh["reference"]) is None:
            raise InputError("missing output/reference interface")
        d.add(ports[s["output"]], anchor_x + 65 * PITCH, anchor_y)
        out = d.point(ports[s["output"]], "1")
        d.route(s["output"], node, out)
        d.junctions.append(node)
        d.label(s["output"], out)
        d.add(ports[sh["reference"]], anchor_x + 65 * PITCH, anchor_y + 40 * PITCH)
        ref = d.point(ports[sh["reference"]], "1")
        d.route(sh["reference"], shunt_bottom, (shunt_bottom[0], ref[1]), ref)
        d.label(sh["reference"], ref)
    if not partial and len(d.positions) != len(design["components"]):
        raise InputError("unsupported passive component occurrence")
    if not partial:
        choose_text_slots(design, d)
    metrics = {} if partial else measure(design, resolved, d)
    text_angles = {key: angle for key, angle in d.angles.items() if angle in (90, 270)}
    return Scene(
        d.positions,
        d.wires,
        d.wire_nets,
        d.labels,
        d.junctions,
        metrics,
        d.angles,
        d.text_positions,
        text_angles,
    )


def power_stage_layout(design: dict, resolved: dict[str, Asset], partial: bool = False) -> Scene:
    """Place a three-terminal power stage between its interfaces and local support."""
    if not partial:
        from .m2_compose import compose_layout

        return compose_layout(design, resolved)
    stages = [r for r in design["relationships"] if r["kind"] == "power_stage"]
    supports = [r for r in design["relationships"] if r["kind"] == "decoupling"]
    if len(stages) != 1 or len(supports) != 2:
        raise InputError("unsupported power-stage relation inventory")
    stage = stages[0]
    stage_id = stage["component"]
    support_by_pin = {tuple(r["consumer"]): r for r in supports}
    if set(support_by_pin) != {
        (stage_id, stage["pins"]["input"]),
        (stage_id, stage["pins"]["output"]),
    } or any(
        {r["supply"], r["return"]} != {stage["reference"], stage[role]}
        for role in ("input", "output")
        for r in (support_by_pin[(stage_id, stage["pins"][role])],)
    ):
        raise InputError("support relationships do not attach to power-stage rails")
    components = {c["id"]: c for c in design["components"]}
    members = {n["id"]: {tuple(m) for m in n["members"]} for n in design["nets"]}
    ports = {}
    for net in (stage["input"], stage["output"], stage["reference"]):
        matches = [
            cid
            for cid, pin in members[net]
            if pin == "1" and components[cid]["asset"] == "Connector_Generic:Conn_01x01"
        ]
        if len(matches) != 1:
            raise InputError("power stage requires one interface per rail")
        ports[net] = matches[0]
    d = Draft(design, resolved, {}, {}, [], [], [], [], {})
    sx, sy = 116 * PITCH, 67 * PITCH
    stage_asset = resolved[components[stage_id]["asset"]]
    d.add(
        stage_id,
        sx,
        sy,
        angle=orientation_for_flow(
            stage_asset, stage["pins"]["input"], stage["pins"]["output"], "right"
        ),
    )
    input_pin = d.point(stage_id, stage["pins"]["input"])
    output_pin = d.point(stage_id, stage["pins"]["output"])
    reference_pin = d.point(stage_id, stage["pins"]["reference"])
    in_relation = support_by_pin[(stage_id, stage["pins"]["input"])]
    out_relation = support_by_pin[(stage_id, stage["pins"]["output"])]
    cap_y = sy + 22 * PITCH if reference_pin[1] > sy else sy - 22 * PITCH

    def support_endpoints(relation, rail, x):
        rail_pin = "1" if relation["supply"] == rail else "2"
        reference_pin_number = "2" if rail_pin == "1" else "1"
        rail_above = cap_y > sy
        angle = (
            0 if (rail_above and rail_pin == "1") or (not rail_above and rail_pin == "2") else 180
        )
        d.add(relation["component"], x, cap_y, angle=angle)
        return d.point(relation["component"], rail_pin), d.point(
            relation["component"], reference_pin_number
        )

    left_rail, left_reference = support_endpoints(in_relation, stage["input"], sx - 24 * PITCH)
    right_rail, right_reference = support_endpoints(out_relation, stage["output"], sx + 24 * PITCH)
    d.add(ports[stage["input"]], sx - 55 * PITCH, sy, angle=180)
    d.add(ports[stage["output"]], sx + 55 * PITCH, sy)
    reference_y = cap_y + (19 * PITCH if cap_y > sy else -19 * PITCH)
    d.add(ports[stage["reference"]], sx + 55 * PITCH, reference_y)
    source = d.point(ports[stage["input"]], "1")
    load = d.point(ports[stage["output"]], "1")
    return_port = d.point(ports[stage["reference"]], "1")
    left_node = (left_rail[0], sy)
    right_node = (right_rail[0], sy)
    d.route(stage["input"], source, left_node, input_pin)
    d.route(stage["input"], left_node, left_rail)
    d.route(stage["output"], output_pin, right_node, load)
    d.route(stage["output"], right_node, right_rail)
    d.junctions.extend((left_node, right_node))
    return_y = return_port[1]
    d.route(stage["reference"], left_reference, (left_reference[0], return_y), return_port)
    d.route(stage["reference"], right_reference, (right_reference[0], return_y))
    d.route(stage["reference"], reference_pin, (reference_pin[0], return_y))
    d.junctions.extend(((right_reference[0], return_y), (reference_pin[0], return_y)))
    for net, point in (
        (stage["input"], source),
        (stage["output"], load),
        (stage["reference"], return_port),
    ):
        d.label(net, point)
    flags = {a["net"]: a for a in design["power_assertions"]}
    if not {stage["input"], stage["reference"]} <= set(flags):
        raise InputError("power stage lacks external source assertions")
    for net, point in (
        (stage["input"], left_node),
        (stage["reference"], (reference_pin[0], return_y)),
    ):
        d.positions[(flags[net]["id"], 1)] = point
    if not partial and {cid for cid, _ in d.positions if cid in components} != set(components):
        raise InputError("unplaced power-stage component")
    if not partial:
        choose_text_slots(design, d)
    metrics = {} if partial else measure(design, resolved, d)
    return Scene(
        d.positions,
        d.wires,
        d.wire_nets,
        d.labels,
        d.junctions,
        metrics,
        d.angles,
        d.text_positions,
    )


def timing_layout(design: dict, resolved: dict[str, Asset], partial: bool = False) -> Scene:
    """Compose a vertical timing ladder beside a physical timer symbol."""
    if not partial:
        from .m2_compose import compose_layout

        return compose_layout(design, resolved)
    timers = [r for r in design["relationships"] if r["kind"] == "timer"]
    ladders = [r for r in design["relationships"] if r["kind"] == "timing_ladder"]
    controls = [r for r in design["relationships"] if r["kind"] == "decoupling"]
    if len(timers) != 1 or len(ladders) != 1 or len(controls) != 1:
        raise InputError("unsupported timing relation inventory")
    timer, ladder, control = timers[0], ladders[0], controls[0]
    if any(timer[k] != ladder[k] for k in ("supply", "reference", "timing", "discharge")):
        raise InputError("timer and timing ladder nets disagree")
    if control["consumer"] != [timer["component"], timer["pins"]["control"]] or (
        control["supply"],
        control["return"],
    ) != (timer["control"], timer["reference"]):
        raise InputError("timer control bypass relation disagrees")
    components = {c["id"]: c for c in design["components"]}
    nets = {n["id"]: {tuple(m) for m in n["members"]} for n in design["nets"]}
    ports = {}
    for net in (timer["supply"], timer["output"], timer["reference"]):
        matches = [
            cid
            for cid, pin in nets[net]
            if pin == "1" and components[cid]["asset"] == "Connector_Generic:Conn_01x01"
        ]
        if len(matches) != 1:
            raise InputError("timer requires supply, output and reference interfaces")
        ports[net] = matches[0]
    d = Draft(design, resolved, {}, {}, [], [], [], [], {})
    tx, ty = 143 * PITCH, 75 * PITCH
    lx = tx - 43 * PITCH
    d.add(timer["component"], tx, ty)
    d.text_positions[(timer["component"], 1)] = (tx + 18 * PITCH, ty - 12 * PITCH)
    p = {role: d.point(timer["component"], number) for role, number in timer["pins"].items()}
    d.add(ladder["upper"], lx, ty - 25 * PITCH)
    d.add(ladder["lower"], lx, ty - 5 * PITCH)
    d.add(ladder["capacitor"], lx, ty + 21 * PITCH)
    d.add(control["component"], tx - 16 * PITCH, ty - 10 * PITCH)
    upper_top, upper_bottom = d.point(ladder["upper"], "1"), d.point(ladder["upper"], "2")
    lower_top, lower_bottom = d.point(ladder["lower"], "1"), d.point(ladder["lower"], "2")
    timing_top, timing_bottom = d.point(ladder["capacitor"], "1"), d.point(ladder["capacitor"], "2")
    control_top, control_bottom = (
        d.point(control["component"], "1"),
        d.point(control["component"], "2"),
    )
    d.add(ports[timer["supply"]], lx - 28 * PITCH, ty - 35 * PITCH, angle=180)
    d.add(ports[timer["output"]], tx + 36 * PITCH, p["output"][1])
    d.add(ports[timer["reference"]], tx + 36 * PITCH, ty + 32 * PITCH)
    source = d.point(ports[timer["supply"]], "1")
    load = d.point(ports[timer["output"]], "1")
    return_port = d.point(ports[timer["reference"]], "1")
    supply_y = source[1]
    d.route(timer["supply"], source, (lx, supply_y), upper_top)
    d.route(timer["supply"], (lx, supply_y), (p["supply"][0], supply_y), p["supply"])
    d.junctions.append((lx, supply_y))
    d.route(timer["supply"], p["reset"], (p["reset"][0] - 5 * PITCH, p["reset"][1]))
    d.label(timer["supply"], (p["reset"][0] - 5 * PITCH, p["reset"][1]))
    discharge_y = (upper_bottom[1] + lower_top[1]) // 2
    discharge_x = p["discharge"][0] - 10 * PITCH
    d.route(timer["discharge"], upper_bottom, (lx, discharge_y), lower_top)
    d.route(
        timer["discharge"],
        (lx, discharge_y),
        (discharge_x, discharge_y),
        (discharge_x, p["discharge"][1]),
        p["discharge"],
    )
    d.junctions.append((lx, discharge_y))
    timing_y = p["trigger"][1] + 6 * PITCH
    sense_x = p["trigger"][0] - 7 * PITCH
    d.route(timer["timing"], lower_bottom, (lx, timing_y), timing_top)
    d.route(
        timer["timing"],
        (lx, timing_y),
        (sense_x, timing_y),
        (sense_x, p["threshold"][1]),
        p["threshold"],
    )
    d.route(timer["timing"], (sense_x, p["trigger"][1]), p["trigger"])
    d.junctions.extend(((lx, timing_y), (sense_x, p["trigger"][1])))
    d.route(timer["output"], p["output"], load)
    d.route(timer["reference"], timing_bottom, (lx, return_port[1]), return_port)
    d.route(timer["reference"], p["reference"], (p["reference"][0], return_port[1]))
    d.junctions.append((p["reference"][0], return_port[1]))
    control_y = min(p["control"][1], control_top[1]) - 5 * PITCH
    d.route(
        timer["control"],
        p["control"],
        (p["control"][0], control_y),
        (control_top[0], control_y),
        control_top,
    )
    d.route(timer["reference"], control_bottom, (control_bottom[0], control_bottom[1] + 3 * PITCH))
    d.label(timer["reference"], (control_bottom[0], control_bottom[1] + 3 * PITCH))
    for net, point in (
        (timer["supply"], source),
        (timer["output"], load),
        (timer["reference"], return_port),
    ):
        d.label(net, point)
    flags = {a["net"]: a for a in design["power_assertions"]}
    if not {timer["supply"], timer["reference"]} <= set(flags):
        raise InputError("timer lacks external supply assertions")
    for net, point in (
        (timer["supply"], (lx, supply_y)),
        (timer["reference"], (p["reference"][0], return_port[1])),
    ):
        d.positions[(flags[net]["id"], 1)] = point
    if not partial and {cid for cid, _ in d.positions if cid in components} != set(components):
        raise InputError("unplaced timer component")
    if not partial:
        choose_text_slots(design, d)
    metrics = {} if partial else measure(design, resolved, d)
    return Scene(
        d.positions,
        d.wires,
        d.wire_nets,
        d.labels,
        d.junctions,
        metrics,
        d.angles,
        d.text_positions,
    )


def measure(design: dict, resolved: dict[str, Asset], draft: Draft) -> dict:
    """Conservative independent-of-render preflight; observed gates run after KiCad."""
    rectangles = []
    for (cid, unit), (x, y) in draft.positions.items():
        c = next((c for c in design["components"] if c["id"] == cid), None)
        if c is None:
            continue
        body = resolved[c["asset"]].bodies.get(unit) or resolved[c["asset"]].bodies.get(0)
        if body:
            left, top, right, bottom = body
            corners = [
                _turn(Pin("", "", "", xx, yy), draft.angles.get((cid, unit), 0))
                for xx in (left, right)
                for yy in (top, bottom)
            ]
            xs, ys = [x + z[0] for z in corners], [y + z[1] for z in corners]
            rectangles.append((cid, (min(xs), min(ys), max(xs), max(ys))))
    for i, (cid, a) in enumerate(rectangles):
        for other, b in rectangles[i + 1 :]:
            if max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3]):
                raise InputError(f"symbol body overlap: {cid}, {other}")
    for net, (a, b) in zip(draft.wire_nets, draft.wires, strict=True):
        if a[0] != b[0] and a[1] != b[1]:
            raise InputError("diagonal wire")
        for cid, rect in rectangles:
            if a in {
                draft.point(cid, p.number)
                for pins in resolved[
                    next(c for c in design["components"] if c["id"] == cid)["asset"]
                ].units.values()
                for p in pins
            } or b in {
                draft.point(cid, p.number)
                for pins in resolved[
                    next(c for c in design["components"] if c["id"] == cid)["asset"]
                ].units.values()
                for p in pins
            }:
                continue
            left, top, right, bottom = rect
            if (
                a[0] == b[0]
                and left < a[0] < right
                and max(min(a[1], b[1]), top) < min(max(a[1], b[1]), bottom)
            ):
                raise InputError(f"wire through body: {net}, {cid}")
            if (
                a[1] == b[1]
                and top < a[1] < bottom
                and max(min(a[0], b[0]), left) < min(max(a[0], b[0]), right)
            ):
                raise InputError(f"wire through body: {net}, {cid}")

    def on_segment(p, a, b):
        return (a[0] == b[0] == p[0] and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])) or (
            a[1] == b[1] == p[1] and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
        )

    for i, (a, b) in enumerate(draft.wires):
        for j in range(i + 1, len(draft.wires)):
            if draft.wire_nets[i] == draft.wire_nets[j]:
                continue
            c, e = draft.wires[j]
            if (
                a[0] == b[0]
                and c[1] == e[1]
                and on_segment((a[0], c[1]), a, b)
                and on_segment((a[0], c[1]), c, e)
            ):
                raise InputError(
                    f"unrelated wire crossing: {draft.wire_nets[i]} {a}->{b}, {draft.wire_nets[j]} {c}->{e}"
                )
            if (
                a[1] == b[1]
                and c[0] == e[0]
                and on_segment((c[0], a[1]), a, b)
                and on_segment((c[0], a[1]), c, e)
            ):
                raise InputError(
                    f"unrelated wire crossing: {draft.wire_nets[i]} {a}->{b}, {draft.wire_nets[j]} {c}->{e}"
                )
            if a[0] == b[0] == c[0] == e[0] and max(min(a[1], b[1]), min(c[1], e[1])) <= min(
                max(a[1], b[1]), max(c[1], e[1])
            ):
                raise InputError("unrelated wire overlap")
            if a[1] == b[1] == c[1] == e[1] and max(min(a[0], b[0]), min(c[0], e[0])) <= min(
                max(a[0], b[0]), max(c[0], e[0])
            ):
                raise InputError("unrelated wire overlap")
    for c in design["components"]:
        key_units = resolved[c["asset"]].units
        for unit in key_units:
            x, y = draft.text_positions[(c["id"], unit)]
            for value, py in ((c["refdes"], y), (c["value"], y + 2 * PITCH)):
                width = max(635_000, len(value) * 445_000)
                box = (x - width, py - 850_000, x + width, py + 850_000)
                for a, b in draft.wires:
                    if (
                        a[0] == b[0]
                        and box[0] < a[0] < box[2]
                        and max(min(a[1], b[1]), box[1]) < min(max(a[1], b[1]), box[3])
                    ):
                        raise InputError(f"wire through text: {c['id']}")
                    if (
                        a[1] == b[1]
                        and box[1] < a[1] < box[3]
                        and max(min(a[0], b[0]), box[0]) < min(max(a[0], b[0]), box[2])
                    ):
                        raise InputError(f"wire through text: {c['id']}")
    endpoints = {p for a, b in draft.wires for p in (a, b)} | {p for _, p in draft.labels}
    for c in design["components"]:
        for pins in resolved[c["asset"]].units.values():
            for p in pins:
                if draft.point(c["id"], p.number) not in endpoints:
                    raise InputError(f"unrouted pin: {c['id']}:{p.number}")
    points = endpoints | set(draft.positions.values()) | set(draft.text_positions.values())
    if any(
        not (20_320_000 <= x <= 276_680_000 and 25_400_000 <= y <= 184_600_000) for x, y in points
    ):
        raise InputError("content exceeds A4 margin")
    bends = sum(
        1
        for i, (_, b) in enumerate(draft.wires)
        for c, e in draft.wires[i + 1 :]
        if b == c and ((draft.wires[i][0][0] == b[0]) != (c[0] == e[0]))
    )
    length = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in draft.wires)
    if bends > max(16, 3 * len(draft.wires)):
        raise InputError("excessive wire bends")
    return {
        "body_overlap_count": 0,
        "wire_through_body_count": 0,
        "wire_through_text_count": 0,
        "unrelated_wire_crossing_count": 0,
        "unrouted_pin_count": 0,
        "page_margin_pass": True,
        "wire_count": len(draft.wires),
        "label_count": len(draft.labels),
        "bend_count": bends,
        "wire_length_mm": length / 1_000_000,
        "symbol_occurrences": len(draft.positions),
    }


def choose_text_slots(design: dict, draft: Draft) -> None:
    """Choose a finite outside slot from actual text length and routed segments."""
    for c in design["components"]:
        if c["asset"] not in ("Device:C", "Device:R"):
            continue
        key = (c["id"], 1)
        if key not in draft.positions:
            continue
        sx, sy = draft.positions[key]
        horizontal = draft.angles.get(key, 0) in (90, 270)
        slots = [draft.text_positions[key]]
        slots += (
            [
                (sx, sy - 8 * PITCH),
                (sx, sy + 5 * PITCH),
                (sx, sy - 12 * PITCH),
                (sx, sy + 9 * PITCH),
                (sx, sy - 16 * PITCH),
            ]
            if horizontal
            else [
                (sx + 8 * PITCH, sy - 2 * PITCH),
                (sx - 8 * PITCH, sy - 2 * PITCH),
                (sx + 12 * PITCH, sy - 2 * PITCH),
                (sx - 12 * PITCH, sy - 2 * PITCH),
                (sx + 16 * PITCH, sy - 2 * PITCH),
                (sx - 16 * PITCH, sy - 2 * PITCH),
                (sx + 12 * PITCH, sy - 10 * PITCH),
                (sx - 12 * PITCH, sy - 10 * PITCH),
                (sx + 20 * PITCH, sy - 2 * PITCH),
                (sx - 20 * PITCH, sy - 2 * PITCH),
            ]
        )
        for x, y in slots:
            clear = True
            for value, py in ((c["refdes"], y), (c["value"], y + 2 * PITCH)):
                half = max(635_000, len(value) * 445_000)
                clearance = 1_000_000
                for a, b in draft.wires:
                    if (
                        a[0] == b[0]
                        and x - half - clearance < a[0] < x + half + clearance
                        and max(min(a[1], b[1]), py - 850_000 - clearance)
                        < min(max(a[1], b[1]), py + 850_000 + clearance)
                    ):
                        clear = False
                    if (
                        a[1] == b[1]
                        and py - 850_000 - clearance < a[1] < py + 850_000 + clearance
                        and max(min(a[0], b[0]), x - half - clearance)
                        < min(max(a[0], b[0]), x + half + clearance)
                    ):
                        clear = False
            if clear:
                draft.text_positions[key] = (x, y)
                break
        else:
            raise InputError(f"no clear value/reference slot for {c['id']}")


def compare(design: dict, observed: dict, resolved: dict[str, Asset] | None = None) -> dict:
    """Compare intended terminals with independent artifact/CLI inventories."""
    diagnostics = []
    resolved = resolved or assets()
    components = {c["id"]: c for c in design["components"]}
    by_ref = {c["refdes"]: c for c in design["components"]}
    expected_occurrences = {
        (c["refdes"], unit)
        for c in design["components"]
        for unit in (1, 2, 3)
        if c["asset"] == "Amplifier_Operational:NE5532"
    }
    expected_occurrences |= {
        (c["refdes"], 1)
        for c in design["components"]
        if c["asset"] != "Amplifier_Operational:NE5532"
    }
    expected_occurrences |= {(a["refdes"], 1) for a in design["power_assertions"]}
    if set(observed["occurrences"]) != expected_occurrences:
        diagnostics.append("physical occurrence inventory differs")
    for (ref, unit), item in observed["occurrences"].items():
        c = by_ref.get(ref)
        if c is None:
            if (
                ref not in {a["refdes"] for a in design["power_assertions"]}
                or item["lib"] != "power:PWR_FLAG"
                or set(item["pins"]) != {"1"}
            ):
                diagnostics.append(f"unexpected occurrence {ref}:{unit}")
            continue
        if item["lib"] != c["asset"]:
            diagnostics.append(f"{ref}:{unit} library differs")
            continue
        actual = item["pins"]
        if c["asset"] == "Amplifier_Operational:NE5532":
            f = next((f for f in c["functions"] if f["unit"] == unit), None)
            if f is None or set(actual) != set(f["pins"].values()):
                diagnostics.append(f"{ref}:{unit} physical pin inventory differs")
            elif any(
                actual[num]["name"]
                != {"plus": "+", "minus": "-", "positive": "V+", "negative": "V-"}.get(
                    role, actual[num]["name"]
                )
                for role, num in f["pins"].items()
            ):
                diagnostics.append(f"{ref}:{unit} actual pin polarity differs")
        elif c["asset"] == "Device:LED":
            if {n: p["name"] for n, p in actual.items()} != {"1": "K", "2": "A"}:
                diagnostics.append(f"{ref}: actual diode polarity differs")
        elif c["asset"] in LOCKED_PIN_ROLES:
            if {n: p["name"] for n, p in actual.items()} != LOCKED_PIN_ROLES[c["asset"]]:
                diagnostics.append(f"{ref}: actual locked physical pin roles differ")
        elif set(actual) != {p.number for p in resolved[c["asset"]].units[unit]}:
            diagnostics.append(f"{ref} actual pin inventory differs")
    if set(observed["xml_components"]) != set(by_ref):
        diagnostics.append("KiCad XML physical component inventory differs")
    for ref, c in by_ref.items():
        actual = observed["xml_components"].get(ref)
        wanted = {
            unit: set(o["pins"]) for (r, unit), o in observed["occurrences"].items() if r == ref
        }
        if actual is None or actual["lib"] != c["asset"] or actual["units"] != wanted:
            diagnostics.append(f"{ref} KiCad XML unit/pin inventory differs")
    expected = {
        frozenset((components[cid]["refdes"], pin) for cid, pin in n["members"])
        for n in design["nets"]
    }
    actual = {
        frozenset(tuple(member) for member in members) for members in observed["nets"].values()
    }
    if expected != actual:
        diagnostics.append("real KiCad connectivity differs")
    endpoint_positions = observed["pin_positions"]
    endpoints = {p for a, b in observed["wires"] for p in (a, b)} | {
        p for _, p in observed["labels"]
    }
    missing = sorted(
        (ref, pin)
        for (ref, pin), point in endpoint_positions.items()
        if ref in by_ref and point not in endpoints
    )
    if missing:
        diagnostics.append(f"actual pin endpoints unrouted: {missing}")

    def on_segment(point, start, end):
        return (
            start[0] == end[0] == point[0]
            and min(start[1], end[1]) <= point[1] <= max(start[1], end[1])
        ) or (
            start[1] == end[1] == point[1]
            and min(start[0], end[0]) <= point[0] <= max(start[0], end[0])
        )

    def connected_to(start, destinations):
        reachable = {start}
        for _ in range(len(observed["wires"]) + 1):
            growth = {
                point
                for a, b in observed["wires"]
                if any(on_segment(known, a, b) for known in reachable)
                for point in (a, b)
            }
            if growth <= reachable:
                break
            reachable |= growth
        return bool(reachable & destinations)

    expected_nets = {
        net["id"]: {(components[cid]["refdes"], pin) for cid, pin in net["members"]}
        for net in design["nets"]
    }
    for assertion in design["power_assertions"]:
        flag = endpoint_positions.get((assertion["refdes"], "1"))
        net = assertion["net"]
        targets = {endpoint_positions.get(key) for key in expected_nets[net]}
        targets |= {point for name, point in observed["labels"] if name == net}
        if flag is None or not connected_to(flag, targets):
            diagnostics.append(f"{assertion['refdes']}: power assertion not on {net}")
    for ref, unit in expected_occurrences:
        if ref not in by_ref or (ref, unit) not in observed["occurrences"]:
            continue
        props = observed["occurrences"][(ref, unit)]["properties"]
        if (
            set(props) != {"Reference", "Value"}
            or props["Reference"]["value"] != ref
            or props["Value"]["value"] != by_ref[ref]["value"]
        ):
            diagnostics.append(f"{ref}:{unit} required reference/value differs")
    return {
        "status": "pass" if not diagnostics else "fail",
        "diagnostics": diagnostics,
        "expected_partitions": sorted([sorted(x) for x in expected]),
        "observed_partitions": sorted([sorted(x) for x in actual]),
    }


def active_layout(design: dict, resolved: dict[str, Asset], partial: bool = False) -> Scene:
    """Construct functional stage, feedback corridor and support islands from relations."""
    if not partial:
        from .m2_compose import compose_layout

        return compose_layout(design, resolved)
    relations = design["relationships"]
    stages = [r for r in relations if r["kind"] == "amplifier"]
    rails = [r for r in relations if r["kind"] == "power_rails"]
    feedbacks = [r for r in relations if r["kind"] == "feedback"]
    decouplers = [r for r in relations if r["kind"] == "decoupling"]
    if len(stages) != 2 or len(rails) != 1 or len(feedbacks) != 2 or len(decouplers) != 2:
        raise InputError("unsupported active-stage relation inventory")
    active_stages = [r for r in stages if not r.get("unused")]
    active = next(
        (r for r in active_stages if r["input"] not in {s["output"] for s in active_stages}),
        active_stages[0] if active_stages else None,
    )
    parked = next((r for r in stages if r is not active), None)
    if (
        active is None
        or parked is None
        or active["component"] != parked["component"]
        or active["component"] != rails[0]["component"]
    ):
        raise InputError("unsupported active-stage function composition")
    amp = active["component"]
    component = next(c for c in design["components"] if c["id"] == amp)
    functions = {f["id"]: f for f in component["functions"]}
    af, pf = functions[active["function"]], functions[parked["function"]]
    if {af["unit"], pf["unit"]} != {1, 2} or rails[0]["unit"] != 3:
        raise InputError("unsupported function unit assignment")
    net_members = {n["id"]: {tuple(m) for m in n["members"]} for n in design["nets"]}
    by_pin = {member: net for net, members in net_members.items() for member in members}
    fb = next((r for r in feedbacks if r["function"] == af["id"] and r["component"] == amp), None)
    parked_fb = next(
        (r for r in feedbacks if r["function"] == pf["id"] and r["component"] == amp), None
    )
    if (
        fb is None
        or parked_fb is None
        or fb["source"] != af["pins"]["out"]
        or fb["sense"] != af["pins"]["minus"]
        or parked_fb["source"] != pf["pins"]["out"]
        or parked_fb["sense"] != pf["pins"]["minus"]
    ):
        raise InputError("feedback pin roles mismatch")
    if fb["polarity"] != "negative" or parked_fb["polarity"] != "negative":
        raise InputError("positive feedback unsupported")
    d = Draft(design, resolved, {}, {}, [], [], [], [], {})
    ax, ay = 100 * PITCH, 59 * PITCH
    bx, by = (ax, ay + 57 * PITCH) if parked.get("unused") else (ax + 70 * PITCH, ay)
    px, py = ax + 64 * PITCH, ay + 33 * PITCH
    d.add(amp, ax, ay, af["unit"])
    d.add(amp, bx, by, pf["unit"])
    d.add(amp, px, py, rails[0]["unit"])
    d.text_positions[(amp, rails[0]["unit"])] = (px, py - 16 * PITCH)
    plus = d.point(amp, af["pins"]["plus"])
    minus = d.point(amp, af["pins"]["minus"])
    out = d.point(amp, af["pins"]["out"])
    plus_net = by_pin[(amp, af["pins"]["plus"])]
    minus_net = by_pin[(amp, af["pins"]["minus"])]
    out_net = by_pin[(amp, af["pins"]["out"])]
    if fb["net"] != out_net:
        raise InputError("feedback source net mismatch")
    if active["output"] != out_net:
        raise InputError("amplifier output relation differs from physical output net")
    # A horizontal resistor has pin 1 to the left and pin 2 to the right.
    feedback_resistor = fb.get("resistor")
    corridor_y = minus[1] + 12 * PITCH
    sense_x = minus[0] - 5 * PITCH
    branch_x = out[0] + 9 * PITCH
    feedback_node = (sense_x, corridor_y)
    branch = (branch_x, out[1])
    if feedback_resistor:
        d.add(
            feedback_resistor,
            ax + 7 * PITCH,
            corridor_y,
            angle=orientation_for_flow(resolved["Device:R"], "1", "2", "right"),
        )
        rleft, rright = d.point(feedback_resistor, "1"), d.point(feedback_resistor, "2")
        if (
            by_pin[(feedback_resistor, "1")] != minus_net
            or by_pin[(feedback_resistor, "2")] != out_net
        ):
            raise InputError("feedback resistor terminal/net mismatch")
        d.route(minus_net, minus, (sense_x, minus[1]), feedback_node, rleft)
        d.route(out_net, rright, (branch_x, corridor_y), branch, out)
    else:
        if minus_net != out_net:
            raise InputError("direct feedback requires same source and sense net")
        d.route(
            out_net, minus, (sense_x, minus[1]), feedback_node, (branch_x, corridor_y), branch, out
        )
    d.junctions.append(branch)
    d.route(out_net, branch, (branch_x + 7 * PITCH, branch[1]))
    d.label(out_net, (branch_x + 7 * PITCH, branch[1]))
    # Gain-reference resistor or inverting input resistor may share the sense net.
    series = [r for r in relations if r["kind"] == "series"]
    shunts = [r for r in relations if r["kind"] == "shunt"]
    gain_leg = next(
        (r for r in shunts if r["node"] == minus_net and r["component"] != feedback_resistor), None
    )
    input_leg = next((r for r in series if r["output"] == minus_net), None)
    input_filter = next((r for r in series if r["output"] == plus_net), None)
    upstream = (
        next((r for r in series if r["output"] == input_filter["input"]), None)
        if input_filter
        else None
    )
    bridges = [r for r in relations if r["kind"] == "bridge"]
    if bridges and (
        len(bridges) != 1
        or upstream is None
        or bridges[0]["first"] != upstream["output"]
        or bridges[0]["second"] != out_net
    ):
        raise InputError("bridge does not compose with the signal path and output")
    accepted_input = (
        input_leg["input"] if input_leg else input_filter["output"] if input_filter else plus_net
    )
    if active["input"] != accepted_input:
        raise InputError("amplifier input relation does not match semantic stage port")
    if gain_leg and input_leg:
        raise InputError("unsupported simultaneous gain and inverting input legs")
    if gain_leg:
        d.add(
            gain_leg["component"],
            sense_x,
            corridor_y + 9 * PITCH,
            angle=orientation_for_flow(resolved["Device:R"], "1", "2", "down"),
        )
        d.text_positions[(gain_leg["component"], 1)] = (sense_x - 8 * PITCH, corridor_y + 5 * PITCH)
        top, bottom = d.point(gain_leg["component"], "1"), d.point(gain_leg["component"], "2")
        d.route(minus_net, feedback_node, top)
        d.junctions.append(feedback_node)
        d.route(gain_leg["reference"], bottom, (bottom[0], bottom[1] + 5 * PITCH))
        d.label(gain_leg["reference"], (bottom[0], bottom[1] + 5 * PITCH))
    if input_leg:
        d.add(
            input_leg["component"],
            ax - 25 * PITCH,
            minus[1],
            angle=orientation_for_flow(resolved["Device:R"], "1", "2", "right"),
        )
        pin1, pin2 = d.point(input_leg["component"], "1"), d.point(input_leg["component"], "2")
        d.route(minus_net, pin2, minus)
        d.junctions.append(minus)
        d.route(input_leg["input"], pin1, (pin1[0] - 5 * PITCH, pin1[1]))
        d.label(input_leg["input"], (pin1[0] - 5 * PITCH, pin1[1]))
    if input_filter:
        d.add(
            input_filter["component"],
            ax - 34 * PITCH,
            plus[1],
            angle=orientation_for_flow(resolved["Device:R"], "1", "2", "right"),
        )
        rin, rout = d.point(input_filter["component"], "1"), d.point(input_filter["component"], "2")
        cap_relation = next((r for r in shunts if r["node"] == plus_net), None)
        if cap_relation is None:
            raise InputError("input filter lacks shunt relation")
        node = (plus[0] - 13 * PITCH, plus[1])
        d.add(cap_relation["component"], node[0], plus[1] + 16 * PITCH)
        cap_top, cap_bottom = (
            d.point(cap_relation["component"], "1"),
            d.point(cap_relation["component"], "2"),
        )
        d.route(plus_net, rout, node, plus)
        d.route(plus_net, node, cap_top)
        d.junctions.append(node)
        d.route(cap_relation["reference"], cap_bottom, (cap_bottom[0], cap_bottom[1] + 5 * PITCH))
        d.label(cap_relation["reference"], (cap_bottom[0], cap_bottom[1] + 5 * PITCH))
        if upstream:
            up_component = upstream["component"]
            up_asset = resolved[
                next(c for c in design["components"] if c["id"] == up_component)["asset"]
            ]
            d.add(
                up_component,
                ax - 56 * PITCH,
                plus[1],
                angle=orientation_for_flow(up_asset, "1", "2", "right"),
            )
            upstream_left, upstream_right = d.point(up_component, "1"), d.point(up_component, "2")
            bridge_node = (ax - 45 * PITCH, plus[1])
            d.route(input_filter["input"], upstream_right, bridge_node, rin)
            d.junctions.append(bridge_node)
            d.route(
                upstream["input"], upstream_left, (upstream_left[0] - 5 * PITCH, upstream_left[1])
            )
            d.label(upstream["input"], (upstream_left[0] - 5 * PITCH, upstream_left[1]))
            if bridges:
                bridge = bridges[0]
                bridge_id = bridge["component"]
                bridge_asset = resolved[
                    next(c for c in design["components"] if c["id"] == bridge_id)["asset"]
                ]
                bridge_y = plus[1] - 19 * PITCH
                d.add(
                    bridge_id,
                    ax - 9 * PITCH,
                    bridge_y,
                    angle=orientation_for_flow(bridge_asset, "1", "2", "right"),
                )
                bridge_left, bridge_right = d.point(bridge_id, "1"), d.point(bridge_id, "2")
                d.route(bridge["first"], bridge_node, (bridge_node[0], bridge_y), bridge_left)
                d.route(bridge["second"], bridge_right, (branch_x, bridge_y), branch)
        else:
            d.route(input_filter["input"], rin, (rin[0] - 5 * PITCH, rin[1]))
            d.label(input_filter["input"], (rin[0] - 5 * PITCH, rin[1]))
    elif not input_leg:
        d.route(plus_net, plus, (plus[0] - 7 * PITCH, plus[1]))
        d.label(plus_net, (plus[0] - 7 * PITCH, plus[1]))
    if input_leg:
        d.route(plus_net, plus, (plus[0] - 7 * PITCH, plus[1]))
        d.label(plus_net, (plus[0] - 7 * PITCH, plus[1]))
    # The other function may be parked or a second active stage in the same package.
    pout = d.point(amp, pf["pins"]["out"])
    pminus = d.point(amp, pf["pins"]["minus"])
    pplus = d.point(amp, pf["pins"]["plus"])
    parked_net = by_pin[(amp, pf["pins"]["out"])]
    if parked_net != by_pin[(amp, pf["pins"]["minus"])]:
        raise InputError("parked unit feedback disconnected")
    pcorridor = pminus[1] + 9 * PITCH
    pbranch = (pout[0] + 7 * PITCH, pout[1])
    d.route(
        parked_net,
        pminus,
        (pminus[0] - 5 * PITCH, pminus[1]),
        (pminus[0] - 5 * PITCH, pcorridor),
        (pbranch[0], pcorridor),
        pbranch,
        pout,
    )
    if parked.get("unused"):
        d.route(by_pin[(amp, pf["pins"]["plus"])], pplus, (pplus[0] - 5 * PITCH, pplus[1]))
        d.label(by_pin[(amp, pf["pins"]["plus"])], (pplus[0] - 5 * PITCH, pplus[1]))
    else:
        if parked["input"] != out_net or parked["output"] != parked_net:
            raise InputError(f"stages {active['id']}, {parked['id']}: incompatible ports")
        first_out = (branch_x + 7 * PITCH, branch[1])
        second_in = (pplus[0] - 5 * PITCH, pplus[1])
        d.route(out_net, first_out, (second_in[0], first_out[1]), second_in, pplus)
        second_out = (pbranch[0] + 7 * PITCH, pbranch[1])
        d.route(parked_net, pbranch, second_out)
        d.label(parked_net, second_out)
    # Power unit and split-rail decoupling are separate owned occurrences.
    pospin = d.point(amp, "8")
    negpin = d.point(amp, "4")
    positive, negative, reference = (
        rails[0]["positive"],
        rails[0]["negative"],
        rails[0]["reference"],
    )
    if by_pin[(amp, "8")] != positive or by_pin[(amp, "4")] != negative:
        raise InputError("power rail physical pin mismatch")
    cap_pos = next(
        (r for r in decouplers if r["supply"] == positive and r["return"] == reference), None
    )
    cap_neg = next(
        (r for r in decouplers if r["supply"] == reference and r["return"] == negative), None
    )
    if cap_pos is None or cap_neg is None:
        raise InputError("unsupported split-rail decoupling")
    d.add(cap_pos["component"], px - 17 * PITCH, py)
    d.add(cap_neg["component"], px + 17 * PITCH, py)
    cp1, cp2 = d.point(cap_pos["component"], "1"), d.point(cap_pos["component"], "2")
    cn1, cn2 = d.point(cap_neg["component"], "1"), d.point(cap_neg["component"], "2")
    pos_flag = (((cp1[0] + pospin[0]) // (2 * PITCH)) * PITCH, cp1[1])
    neg_flag = (((cn2[0] + negpin[0]) // (2 * PITCH)) * PITCH, cn2[1])
    d.route(positive, pospin, (pospin[0], cp1[1]), pos_flag, cp1)
    d.route(negative, negpin, (negpin[0], cn2[1]), neg_flag, cn2)
    d.label(positive, pospin)
    d.label(negative, negpin)
    d.route(reference, cp2, (cp2[0], cp2[1] + 5 * PITCH))
    d.label(reference, (cp2[0], cp2[1] + 5 * PITCH))
    d.route(reference, cn1, (cn1[0], cn1[1] - 5 * PITCH))
    d.label(reference, (cn1[0], cn1[1] - 5 * PITCH))
    dividers = [r for r in relations if r["kind"] == "reference_divider"]
    if dividers:
        if len(dividers) != 1 or any(
            dividers[0][role] != net
            for role, net in (("positive", positive), ("local", reference), ("negative", negative))
        ):
            raise InputError("reference divider and split rails disagree")
        divider = dividers[0]
        divider_x = px - 37 * PITCH
        d.add(divider["upper"], divider_x, py - 13 * PITCH)
        d.add(divider["lower"], divider_x, py + 13 * PITCH)
        upper_top, upper_bottom = d.point(divider["upper"], "1"), d.point(divider["upper"], "2")
        lower_top, lower_bottom = d.point(divider["lower"], "1"), d.point(divider["lower"], "2")
        local_node = (divider_x, cp2[1])
        d.route(reference, upper_bottom, local_node, lower_top)
        d.route(reference, local_node, cp2)
        d.junctions.append(local_node)
        d.route(positive, upper_top, (divider_x, upper_top[1] - 5 * PITCH))
        d.label(positive, (divider_x, upper_top[1] - 5 * PITCH))
        d.route(negative, lower_bottom, (divider_x, lower_bottom[1] + 5 * PITCH))
        d.label(negative, (divider_x, lower_bottom[1] + 5 * PITCH))
        d.label(reference, local_node)
    # Mixed connector is a lookup island; each terminal carries its semantic net.
    connectors = [c for c in design["components"] if c["asset"].startswith("Connector_Generic:")]
    if len(connectors) != 1:
        raise InputError("active stage requires one mixed interface")
    interface = connectors[0]
    d.add(interface["id"], ax - 58 * PITCH, ay + 25 * PITCH)
    for pin in resolved[interface["asset"]].units[1]:
        net = by_pin[(interface["id"], pin.number)]
        point = d.point(interface["id"], pin.number)
        end = (point[0] - 4 * PITCH, point[1])
        d.route(net, point, end)
        d.label(net, end)
    flags = {a["net"]: a for a in design["power_assertions"]}
    required_flags = {positive, negative} if dividers else {positive, negative, reference}
    if set(flags) != required_flags:
        raise InputError("missing external supply assertions")
    for net, point in (
        (positive, pos_flag),
        (negative, neg_flag),
        (reference, (cp2[0], cp2[1] + 5 * PITCH)),
    ):
        if net in flags:
            d.positions[(flags[net]["id"], 1)] = point
            d.angles[(flags[net]["id"], 1)] = 0
    # Each component is placed once even when it belongs to several relations.
    placed = {cid for cid, _ in d.positions if cid in {c["id"] for c in design["components"]}}
    if not partial and placed != {c["id"] for c in design["components"]}:
        raise InputError(
            f"components without geometry owner: {sorted({c['id'] for c in design['components']} - placed)}"
        )
    if not partial:
        choose_text_slots(design, d)
    metrics = {} if partial else measure(design, resolved, d)
    metrics.update(
        {
            "feedback_local_span_mm": (branch_x - sense_x) / 1_000_000,
            "input_left_of_output": plus[0] < out[0],
        }
    )
    if metrics["feedback_local_span_mm"] > 40 or not metrics["input_left_of_output"]:
        raise InputError("active motif feedback span or flow violation")
    return Scene(
        d.positions,
        d.wires,
        d.wire_nets,
        d.labels,
        d.junctions,
        metrics,
        d.angles,
        d.text_positions,
        {key: angle for key, angle in d.angles.items() if angle in (90, 270)},
    )


def check_observed_layout(schematic: Path, observed: dict, design: dict) -> dict:
    """Measure actual emitted geometry using embedded definitions and KiCad's netlist."""
    tree = parse(schematic.read_text())
    bodies = {}
    for definition in children(one(tree, "lib_symbols"), "symbol"):
        for unit in children(definition, "symbol"):
            unit_no = int(unit[1].rsplit("_", 2)[-2])
            points = []
            for shape in unit[2:]:
                if not isinstance(shape, list):
                    continue
                if shape[0] == "rectangle":
                    points += [one(shape, "start"), one(shape, "end")]
                elif shape[0] == "polyline":
                    points += [xy for pts in children(shape, "pts") for xy in children(pts, "xy")]
            if points:
                xs, ys = [_nm(p[1]) for p in points], [_nm(p[2]) for p in points]
                bodies[(definition[1], unit_no)] = (min(xs), max(ys), max(xs), min(ys))
    instances = {}
    rectangles = []
    for symbol in children(tree, "symbol"):
        ref = next(p[2] for p in children(symbol, "property") if p[1] == "Reference")
        lib = one(symbol, "lib_id")[1]
        if lib != "power:PWR_FLAG" and any(
            children(prop, "hide")
            for prop in children(symbol, "property")
            if prop[1] in ("Reference", "Value")
        ):
            raise InputError("observed required reference/value hidden")
        unit = int(one(symbol, "unit")[1])
        at = one(symbol, "at")
        x, y, angle = _nm(at[1]), _nm(at[2]), int(at[3])
        instances[(ref, unit)] = (x, y, angle)
        if lib == "power:PWR_FLAG":
            continue
        boxes = [box for key, box in bodies.items() if key[0] == lib and key[1] in (0, unit)]
        if boxes:
            left, top, right, bottom = (
                min(z[0] for z in boxes),
                max(z[1] for z in boxes),
                max(z[2] for z in boxes),
                min(z[3] for z in boxes),
            )
            corners = [
                _turn(Pin("", "", "", xx, yy), angle)
                for xx in (left, right)
                for yy in (top, bottom)
            ]
            xs, ys = [x + z[0] for z in corners], [y + z[1] for z in corners]
            rectangles.append((ref, (min(xs), min(ys), max(xs), max(ys))))
    for i, (ref, a) in enumerate(rectangles):
        for other, b in rectangles[i + 1 :]:
            if max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3]):
                raise InputError(f"observed body overlap: {ref}, {other}")
    wires = observed["wires"]
    labels = observed["labels"]
    pin_positions = observed["pin_positions"]
    pin_to_net = {
        (ref, pin): name for name, members in observed["nets"].items() for ref, pin in members
    }

    def on_segment(p, a, b):
        return (a[0] == b[0] == p[0] and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])) or (
            a[1] == b[1] == p[1] and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
        )

    wire_net = [set() for _ in wires]
    for i, (a, b) in enumerate(wires):
        if a[0] != b[0] and a[1] != b[1]:
            raise InputError("observed diagonal wire")
        for key, point in pin_positions.items():
            if on_segment(point, a, b) and key in pin_to_net:
                wire_net[i].add(pin_to_net[key])
        for name, point in labels:
            if on_segment(point, a, b):
                wire_net[i].add(name)
    for _ in range(len(wires)):
        changed = False
        for i, (a, b) in enumerate(wires):
            for j, (c, e) in enumerate(wires):
                if i == j or not any(on_segment(p, c, e) for p in (a, b)):
                    continue
                combined = wire_net[i] | wire_net[j]
                if combined != wire_net[i] or combined != wire_net[j]:
                    wire_net[i] = wire_net[j] = combined
                    changed = True
        if not changed:
            break
    if any(len(names) != 1 for names in wire_net):
        raise InputError("observed wire net attribution ambiguous")
    names = [next(iter(x)) for x in wire_net]
    observed_junctions = set(observed.get("junctions", ()))
    conductor_trees = {}
    for net in sorted(set(names)):
        indexed = [
            (index, wire)
            for index, (name, wire) in enumerate(zip(names, wires, strict=True))
            if name == net
        ]
        conductor_trees[net] = canonical_conductor_tree(
            (
                ConductorSegment(a, b, net, "independent-observer", (f"wire.{index}",))
                for index, (a, b) in indexed
            ),
            junctions=observed_junctions,
            pins=(
                point
                for terminal, point in pin_positions.items()
                if pin_to_net.get(terminal) == net
            ),
        )
    if "junctions" in observed:
        missing_junctions = sorted(
            point
            for tree in conductor_trees.values()
            for point in tree.junctions
            if point not in observed_junctions
        )
        if missing_junctions:
            raise InputError(f"observed branch junction missing: {missing_junctions}")
    for i, (a, b) in enumerate(wires):
        for ref, rect in rectangles:
            if a in {point for (r, _), point in pin_positions.items() if r == ref} or b in {
                point for (r, _), point in pin_positions.items() if r == ref
            }:
                continue
            left, top, right, bottom = rect
            if (
                a[0] == b[0]
                and left < a[0] < right
                and max(min(a[1], b[1]), top) < min(max(a[1], b[1]), bottom)
            ):
                raise InputError(f"observed wire through body: {ref}")
            if (
                a[1] == b[1]
                and top < a[1] < bottom
                and max(min(a[0], b[0]), left) < min(max(a[0], b[0]), right)
            ):
                raise InputError(f"observed wire through body: {ref}")
        for key, point in pin_positions.items():
            if key in pin_to_net and pin_to_net[key] != names[i] and on_segment(point, a, b):
                raise InputError("wire touches unrelated physical pin")
        for j, (c, e) in enumerate(wires[i + 1 :], i + 1):
            if names[i] == names[j]:
                continue
            if (
                a[0] == b[0]
                and c[1] == e[1]
                and on_segment((a[0], c[1]), a, b)
                and on_segment((a[0], c[1]), c, e)
            ):
                raise InputError("observed unrelated wire crossing")
            if (
                a[1] == b[1]
                and c[0] == e[0]
                and on_segment((c[0], a[1]), a, b)
                and on_segment((c[0], a[1]), c, e)
            ):
                raise InputError("observed unrelated wire crossing")
            if a[0] == b[0] == c[0] == e[0] and max(min(a[1], b[1]), min(c[1], e[1])) <= min(
                max(a[1], b[1]), max(c[1], e[1])
            ):
                raise InputError("observed unrelated wire overlap")
            if a[1] == b[1] == c[1] == e[1] and max(min(a[0], b[0]), min(c[0], e[0])) <= min(
                max(a[0], b[0]), max(c[0], e[0])
            ):
                raise InputError("observed unrelated wire overlap")
    minimum_text_clearance = None
    for (ref, unit), item in observed["occurrences"].items():
        if item["lib"] == "power:PWR_FLAG":
            continue
        props = item["properties"]
        if set(props) != {"Reference", "Value"}:
            raise InputError("observed required text missing")
        for prop in props.values():
            x, y = prop["position"]
            half = max(635_000, len(prop["value"]) * 445_000)
            box = (x - half, y - 850_000, x + half, y + 850_000)
            for a, b in wires:
                wire_box = (
                    min(a[0], b[0]),
                    min(a[1], b[1]),
                    max(a[0], b[0]),
                    max(a[1], b[1]),
                )
                clearance = max(box[0] - wire_box[2], wire_box[0] - box[2], 0) + max(
                    box[1] - wire_box[3], wire_box[1] - box[3], 0
                )
                minimum_text_clearance = (
                    clearance
                    if minimum_text_clearance is None
                    else min(minimum_text_clearance, clearance)
                )
                if (
                    a[0] == b[0]
                    and box[0] < a[0] < box[2]
                    and max(min(a[1], b[1]), box[1]) < min(max(a[1], b[1]), box[3])
                ):
                    raise InputError("observed wire through text")
                if (
                    a[1] == b[1]
                    and box[1] < a[1] < box[3]
                    and max(min(a[0], b[0]), box[0]) < min(max(a[0], b[0]), box[2])
                ):
                    raise InputError("observed wire through text")
    all_points = (
        [p for a, b in wires for p in (a, b)]
        + [p for _, p in labels]
        + [
            v["position"]
            for item in observed["occurrences"].values()
            for v in item["properties"].values()
        ]
    )
    if any(
        not (20_320_000 <= x <= 276_680_000 and 25_400_000 <= y <= 184_600_000)
        for x, y in all_points
    ):
        raise InputError("observed content outside A4 margin")
    extent_points = all_points + list(pin_positions.values())
    width_mm = (max(p[0] for p in extent_points) - min(p[0] for p in extent_points)) / 1_000_000
    height_mm = (max(p[1] for p in extent_points) - min(p[1] for p in extent_points)) / 1_000_000
    if width_mm > 210 or height_mm > 140:
        raise InputError("observed layout spreads unnecessarily across the page")
    by_ref = {c["id"]: c["refdes"] for c in design["components"]}
    series_relations = [r for r in design["relationships"] if r["kind"] == "series"]
    for upstream in series_relations:
        for downstream in series_relations:
            if upstream is downstream or upstream["output"] != downstream["input"]:
                continue
            left = pin_positions[(by_ref[upstream["component"]], "2")]
            right = pin_positions[(by_ref[downstream["component"]], "1")]
            if left[0] >= right[0]:
                raise InputError("observed functional stage order reversal")
    spans = []
    for relation in design["relationships"]:
        if relation["kind"] == "feedback" and not any(
            r["kind"] == "amplifier"
            and r["component"] == relation["component"]
            and r["function"] == relation["function"]
            and r.get("unused")
            for r in design["relationships"]
        ):
            ref = by_ref[relation["component"]]
            source = pin_positions[(ref, relation["source"])]
            sense = pin_positions[(ref, relation["sense"])]
            span = abs(source[0] - sense[0]) / 1_000_000
            spans.append(span)
            if span > 45:
                raise InputError("excessive local feedback span")
    length_by_net = {net: tree.length for net, tree in conductor_trees.items()}
    if any(length > 250_000_000 for length in length_by_net.values()):
        raise InputError("obvious excessive net detour")
    endpoints = {p for a, b in wires for p in (a, b)} | {p for _, p in labels}
    missing = [
        (ref, pin)
        for (ref, pin), point in pin_positions.items()
        if (ref, pin) in pin_to_net and point not in endpoints
    ]
    if missing:
        raise InputError(f"observed pin endpoint mismatch: {missing}")
    reversals = 0
    for relation in design["relationships"]:
        kind = relation["kind"]
        if kind == "series":
            ref = by_ref[relation["component"]]
            start, end = pin_positions[(ref, "1")], pin_positions[(ref, "2")]
            reversals += not (start[0] < end[0] or start[1] < end[1])
        elif kind == "polarity":
            ref = by_ref[relation["component"]]
            start, end = pin_positions[(ref, "2")], pin_positions[(ref, "1")]
            reversals += not (start[0] < end[0] or start[1] < end[1])
        elif kind == "amplifier" and not relation.get("unused"):
            component = next(c for c in design["components"] if c["id"] == relation["component"])
            function = next(f for f in component["functions"] if f["id"] == relation["function"])
            ref = component["refdes"]
            reversals += (
                pin_positions[(ref, function["pins"]["plus"])][0]
                >= pin_positions[(ref, function["pins"]["out"])][0]
            )
    if reversals:
        raise InputError("observed functional flow reversal")
    relation_by_kind = {}
    for relation in design["relationships"]:
        relation_by_kind.setdefault(relation["kind"], []).append(relation)

    def pin(component, number):
        return by_ref[component], number

    def wired_path(first, second):
        net = pin_to_net.get(first)
        if net is None or pin_to_net.get(second) != net:
            return False
        if net not in conductor_trees:
            return False
        return conductor_reachable(
            conductor_trees[net], pin_positions[first], pin_positions[second]
        )

    local_paths = []

    def require_path(first, second, relation):
        if not wired_path(first, second):
            raise InputError(f"observed local motif lacks explicit wire path: {relation}")
        a, b = pin_positions[first], pin_positions[second]
        local_paths.append((relation, (abs(a[0] - b[0]) + abs(a[1] - b[1])) / 1_000_000))

    for first in relation_by_kind.get("series", []):
        for second in relation_by_kind.get("series", []):
            if first is not second and first["output"] == second["input"]:
                a, b = pin(first["component"], "2"), pin(second["component"], "1")
                require_path(a, b, "ordered series")
                if pin_positions[a][0] >= pin_positions[b][0]:
                    raise InputError("observed functional stage order reversal")
        for second in relation_by_kind.get("polarity", []):
            if first["output"] == second["anode"]:
                require_path(
                    pin(first["component"], "2"), pin(second["component"], "2"), "series/polarity"
                )
        for second in relation_by_kind.get("shunt", []):
            if first["output"] == second["node"]:
                require_path(
                    pin(first["component"], "2"), pin(second["component"], "1"), "series/shunt"
                )
        for second in relation_by_kind.get("amplifier", []):
            if second.get("unused") or first["output"] != second["input"]:
                continue
            component = next(c for c in design["components"] if c["id"] == second["component"])
            function = next(f for f in component["functions"] if f["id"] == second["function"])
            source = pin(first["component"], "2")
            input_leg = next(
                (
                    r
                    for r in relation_by_kind.get("series", [])
                    if r["input"] == first["output"]
                    and pin_to_net.get(pin(r["component"], "2"))
                    == pin_to_net.get(pin(second["component"], function["pins"]["minus"]))
                ),
                None,
            )
            target = (
                pin(input_leg["component"], "1")
                if input_leg
                else pin(second["component"], function["pins"]["plus"])
            )
            require_path(source, target, "series/amplifier")
            if pin_positions[source][0] >= pin_positions[target][0]:
                raise InputError("observed functional stage order reversal")
    for relation in relation_by_kind.get("feedback", []):
        if any(
            stage["component"] == relation["component"]
            and stage["function"] == relation["function"]
            and stage.get("unused")
            for stage in relation_by_kind.get("amplifier", [])
        ):
            continue
        source = pin(relation["component"], relation["source"])
        sense = pin(relation["component"], relation["sense"])
        if "resistor" in relation:
            require_path(source, pin(relation["resistor"], "2"), "feedback source")
            require_path(sense, pin(relation["resistor"], "1"), "feedback sense")
        else:
            require_path(source, sense, "direct feedback")
    for relation in relation_by_kind.get("bridge", []):
        peers = [
            pin(cid, number)
            for net in design["nets"]
            if net["id"] == relation["first"]
            for cid, number in net["members"]
            if cid != relation["component"]
            and not next(c for c in design["components"] if c["id"] == cid)["asset"].startswith(
                "Connector_Generic:"
            )
        ]
        if peers and not any(wired_path(peer, pin(relation["component"], "1")) for peer in peers):
            raise InputError("observed bridge is visually detached")
        for stage in relation_by_kind.get("amplifier", []):
            if stage.get("unused") or stage["output"] != relation["second"]:
                continue
            component = next(c for c in design["components"] if c["id"] == stage["component"])
            function = next(f for f in component["functions"] if f["id"] == stage["function"])
            require_path(
                pin(relation["component"], "2"),
                pin(stage["component"], function["pins"]["out"]),
                "bridge feedback",
            )
    for relation in relation_by_kind.get("decoupling", []):
        consumer = pin(*relation["consumer"])
        cap = next(
            pin(relation["component"], number)
            for number in ("1", "2")
            if pin_to_net.get(pin(relation["component"], number)) == pin_to_net.get(consumer)
        )
        require_path(consumer, cap, "decoupling")
    for relation in relation_by_kind.get("timing_ladder", []):
        require_path(pin(relation["upper"], "2"), pin(relation["lower"], "1"), "timing discharge")
        require_path(pin(relation["lower"], "2"), pin(relation["capacitor"], "1"), "timing node")
        if not (
            pin_positions[pin(relation["upper"], "1")][1]
            < pin_positions[pin(relation["lower"], "1")][1]
            < pin_positions[pin(relation["capacitor"], "1")][1]
        ):
            raise InputError("observed timing ladder order reversal")
    for relation in relation_by_kind.get("reference_divider", []):
        require_path(
            pin(relation["upper"], "2"), pin(relation["lower"], "1"), "local reference divider"
        )
    excessive_local_paths = [item for item in local_paths if item[1] > 80]
    if excessive_local_paths:
        raise InputError(
            "observed local motif is excessively fragmented: "
            f"paths={excessive_local_paths} threshold_mm=80"
        )
    local_spans = []
    support_spans = []
    for relation in design["relationships"]:
        kind = relation["kind"]
        if kind == "polarity":
            diode_ref = by_ref[relation["component"]]
            anode = pin_positions[(diode_ref, "2")]
            peers = [
                pin_positions[(by_ref[cid], pin)]
                for net in design["nets"]
                if net["id"] == relation["anode"]
                for cid, pin in net["members"]
                if cid != relation["component"]
            ]
            if peers:
                local_spans.append(
                    min(abs(anode[0] - p[0]) + abs(anode[1] - p[1]) for p in peers) / 1_000_000
                )
        elif kind == "shunt":
            shunt_ref = by_ref[relation["component"]]
            terminal = pin_positions[(shunt_ref, "1")]
            peers = [
                pin_positions[(by_ref[cid], pin)]
                for net in design["nets"]
                if net["id"] == relation["node"]
                for cid, pin in net["members"]
                if cid != relation["component"]
                and not next(c for c in design["components"] if c["id"] == cid)["asset"].startswith(
                    "Connector_Generic:"
                )
            ]
            if peers:
                local_spans.append(
                    min(abs(terminal[0] - p[0]) + abs(terminal[1] - p[1]) for p in peers)
                    / 1_000_000
                )
        elif kind == "feedback" and "resistor" in relation:
            amp_ref = by_ref[relation["component"]]
            resistor_ref = by_ref[relation["resistor"]]
            for amp_pin, resistor_pin in ((relation["sense"], "1"), (relation["source"], "2")):
                a = pin_positions[(amp_ref, amp_pin)]
                b = pin_positions[(resistor_ref, resistor_pin)]
                local_spans.append((abs(a[0] - b[0]) + abs(a[1] - b[1])) / 1_000_000)
        elif kind == "decoupling":
            consumer_ref = by_ref[relation["consumer"][0]]
            cap_ref = by_ref[relation["component"]]
            consumer = pin_positions[(consumer_ref, relation["consumer"][1])]
            member = next(
                p
                for p in ("1", "2")
                if (cap_ref, p)
                in observed["nets"].get(pin_to_net[(consumer_ref, relation["consumer"][1])], [])
            )
            cap = pin_positions[(cap_ref, member)]
            span = (abs(consumer[0] - cap[0]) + abs(consumer[1] - cap[1])) / 1_000_000
            local_spans.append(span)
            support_spans.append(span)
    if any(span > 80 for span in local_spans):
        raise InputError("observed motif fragmentation")
    if any(span > 60 for span in support_spans):
        raise InputError("observed support component detached from consumer")
    bends = sum(tree.bends for tree in conductor_trees.values())
    if bends > max(16, len(wires) * 3):
        raise InputError("observed excessive bends")
    return {
        "observed_body_overlap_count": 0,
        "observed_wire_through_body_count": 0,
        "observed_wire_through_text_count": 0,
        "observed_unrelated_wire_crossing_count": 0,
        "observed_unrelated_pin_contact_count": 0,
        "observed_pin_endpoint_mismatch_count": 0,
        "observed_flow_reversal_count": 0,
        "observed_motif_fragmentation_mm": max(local_spans, default=0),
        "observed_bend_count": bends,
        "observed_required_visible_fields": 2
        * sum(item["lib"] != "power:PWR_FLAG" for item in observed["occurrences"].values()),
        "observed_page_margin_pass": True,
        "observed_feedback_span_mm": max(spans, default=0),
        "observed_wire_length_mm": sum(tree.length for tree in conductor_trees.values())
        / 1_000_000,
        "observed_wire_count": sum(
            len(tree.geometry_signature) for tree in conductor_trees.values()
        ),
        "observed_raw_wire_count": len(wires),
        "observed_actual_junction_count": sum(
            len(tree.junctions) for tree in conductor_trees.values()
        ),
        "observed_stage_order_reversal_count": 0,
        "observed_local_wire_span_mm": max((span for _, span in local_paths), default=0),
        "observed_local_wire_span_witness": max(
            local_paths, key=lambda item: item[1], default=None
        ),
        "observed_support_locality_mm": max(support_spans, default=0),
        "observed_content_width_mm": width_mm,
        "observed_content_height_mm": height_mm,
        "observed_page_utilization": round(width_mm * height_mm / (256.36 * 159.2), 6),
        "observed_text_wire_clearance_mm": (
            None if minimum_text_clearance is None else minimum_text_clearance / 1_000_000
        ),
    }
