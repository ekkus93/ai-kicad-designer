"""Bounded multi-unit op-amp experiment; M1's compiler remains independent."""

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
import re
import uuid
import xml.etree.ElementTree as ET

from .assets import _extract_symbol, sha256
from .ir import InputError
from .schematic import _mm
from .sexpr import children, one, parse, quote


PITCH = 1_270_000
ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "fixtures/m2a/assets"
FILES = {
    "Amplifier_Operational:NE5532": ("NE5532.kicad_sym", "LM2904.kicad_sym"),
    "Device:C": ("C.kicad_sym",),
    "Connector_Generic:Conn_01x05": ("Conn_01x05.kicad_sym",),
    "power:PWR_FLAG": ("PWR_FLAG.kicad_sym",),
}


@dataclass(frozen=True)
class Pin:
    number: str
    name: str
    electrical_type: str
    x: int
    y: int


@dataclass(frozen=True)
class Asset:
    library_id: str
    definition: str
    units: dict[int, tuple[Pin, ...]]
    bodies: dict[int, tuple[int, int, int, int] | None]


def _nm(value: str) -> int:
    from decimal import Decimal

    scaled = Decimal(value) * 1_000_000
    if scaled != scaled.to_integral_value():
        raise InputError("off-nanometer asset geometry")
    return int(scaled)


def load_assets() -> dict[str, Asset]:
    lock = json.loads((ROOT / "fixtures/m2a/assets.lock.json").read_text())
    if lock["schema_version"] != "m2a.1" or set(lock["assets"]) != set(FILES):
        raise InputError("M2a asset lock mismatch")
    if sha256((ROOT / "fixtures/m2a/sym-lib-table").read_bytes()) != lock["symbol_table_sha256"]:
        raise InputError("M2a symbol table hash mismatch")
    result = {}
    for lib_id, filenames in FILES.items():
        if set(lock["assets"][lib_id]) != set(filenames):
            raise InputError(f"asset dependency inventory mismatch: {lib_id}")
        sources = {}
        for filename in filenames:
            data = (ASSETS / filename).read_bytes()
            if sha256(data) != lock["assets"][lib_id][filename]:
                raise InputError(f"asset hash mismatch: {filename}")
            sources[filename] = data.decode()
        short = lib_id.split(":", 1)[1]
        if short == "NE5532":
            child = parse(_extract_symbol(sources["NE5532.kicad_sym"], "NE5532"))
            if one(child, "extends")[1] != "LM2904":
                raise InputError("NE5532 inheritance changed")
            base = _extract_symbol(sources["LM2904.kicad_sym"], "LM2904")
            child_source = _extract_symbol(sources["NE5532.kicad_sym"], "NE5532")

            def property_span(source: str, name: str) -> tuple[int, int]:
                start = source.index(f'(property "{name}"')
                depth = 0
                quoted = False
                escape = False
                for i in range(start, len(source)):
                    char = source[i]
                    if quoted:
                        if escape:
                            escape = False
                        elif char == chr(92):
                            escape = True
                        elif char == '"':
                            quoted = False
                    elif char == '"':
                        quoted = True
                    elif char == "(":
                        depth += 1
                    elif char == ")":
                        depth -= 1
                        if depth == 0:
                            return start, i + 1
                raise InputError("unterminated inherited symbol property")

            for prop in (
                "Reference",
                "Value",
                "Footprint",
                "Datasheet",
                "Description",
                "ki_keywords",
                "ki_fp_filters",
            ):
                a, b = property_span(base, prop)
                c, d = property_span(child_source, prop)
                base = base[:a] + child_source[c:d] + base[b:]
            definition = base.replace('(symbol "LM2904"', f"(symbol {quote(lib_id)}", 1)
            definition = definition.replace('(symbol "LM2904_', '(symbol "NE5532_')
        else:
            definition = _extract_symbol(sources[filenames[0]], short)
            definition = definition.replace(
                f"(symbol {quote(short)}", f"(symbol {quote(lib_id)}", 1
            )
        tree = parse(definition)
        units: dict[int, list[Pin]] = {}
        bodies = {}
        seen = set()
        for unit in children(tree, "symbol"):
            suffix = unit[1].rsplit("_", 2)
            if len(suffix) != 3 or suffix[-1] not in ("0", "1"):
                raise InputError("unsupported body style")
            number = int(suffix[-2])
            if number in bodies and children(unit, "pin"):
                raise InputError("stacked/duplicate unit unsupported")
            pins = []
            for pin in children(unit, "pin"):
                if children(pin, "hide") or "hide" in pin[:4]:
                    raise InputError("hidden pins unsupported in M2a")
                at = one(pin, "at")
                identity = str(one(pin, "number")[1])
                if identity in seen:
                    raise InputError("stacked/common physical pins unsupported in M2a")
                seen.add(identity)
                pins.append(Pin(identity, str(one(pin, "name")[1]), pin[1], _nm(at[1]), _nm(at[2])))
            if pins:
                units[number] = pins
            rects = children(unit, "rectangle")
            if rects:
                rect = rects[0]
                a, b = one(rect, "start"), one(rect, "end")
                bodies[number] = (_nm(a[1]), _nm(a[2]), _nm(b[1]), _nm(b[2]))
            else:
                points = [
                    xy
                    for shape in children(unit, "polyline")
                    for pts in children(shape, "pts")
                    for xy in children(pts, "xy")
                ]
                if points:
                    xs, ys = [_nm(p[1]) for p in points], [_nm(p[2]) for p in points]
                    bodies[number] = (min(xs), max(ys), max(xs), min(ys))
                else:
                    bodies[number] = None
        result[lib_id] = Asset(lib_id, definition, {k: tuple(v) for k, v in units.items()}, bodies)
    op = result["Amplifier_Operational:NE5532"]
    if {
        u: {p.number: (p.name, p.electrical_type) for p in pins} for u, pins in op.units.items()
    } != {
        1: {"1": ("", "output"), "2": ("-", "input"), "3": ("+", "input")},
        2: {"5": ("+", "input"), "6": ("-", "input"), "7": ("", "output")},
        3: {"4": ("V-", "power_in"), "8": ("V+", "power_in")},
    }:
        raise InputError("NE5532 unit/pin semantics changed")
    return result


def _member(component: str, pin: str) -> list[str]:
    return [component, pin]


def fixture(ref: str = "U1", reverse: bool = False) -> dict:
    """Semantic M2a IR; no symbol positions or reference-name based discovery."""
    components = [
        {
            "id": "amp",
            "refdes": ref,
            "asset": "Amplifier_Operational:NE5532",
            "value": "NE5532",
            "functions": [
                {
                    "id": "a",
                    "role": "buffer",
                    "unit": 1,
                    "pins": {"out": "1", "minus": "2", "plus": "3"},
                },
                {
                    "id": "b",
                    "role": "parked_buffer",
                    "unit": 2,
                    "pins": {"out": "7", "minus": "6", "plus": "5"},
                },
                {
                    "id": "power",
                    "role": "supply",
                    "unit": 3,
                    "pins": {"negative": "4", "positive": "8"},
                },
            ],
        },
        {"id": "cpos", "refdes": "C1", "asset": "Device:C", "value": "100n"},
        {"id": "cneg", "refdes": "C2", "asset": "Device:C", "value": "100n"},
        {
            "id": "interface",
            "refdes": "J1",
            "asset": "Connector_Generic:Conn_01x05",
            "value": "Conn_01x05",
        },
    ]
    nets = [
        {"id": "IN", "members": [_member("interface", "1"), _member("amp", "3")]},
        {
            "id": "OUT",
            "members": [_member("interface", "2"), _member("amp", "1"), _member("amp", "2")],
        },
        {
            "id": "VPLUS",
            "members": [_member("interface", "3"), _member("amp", "8"), _member("cpos", "1")],
        },
        {
            "id": "VMINUS",
            "members": [_member("interface", "4"), _member("amp", "4"), _member("cneg", "2")],
        },
        {
            "id": "REF",
            "members": [
                _member("interface", "5"),
                _member("amp", "5"),
                _member("cpos", "2"),
                _member("cneg", "1"),
            ],
        },
        {"id": "PARK", "members": [_member("amp", "6"), _member("amp", "7")]},
    ]
    relationships = [
        {
            "id": "stage.a",
            "kind": "amplifier",
            "component": "amp",
            "function": "a",
            "input": "IN",
            "output": "OUT",
            "reference": "REF",
        },
        {
            "id": "stage.b",
            "kind": "amplifier",
            "component": "amp",
            "function": "b",
            "input": "REF",
            "output": "PARK",
            "unused": True,
        },
        {
            "id": "loop.a",
            "kind": "feedback",
            "component": "amp",
            "function": "a",
            "source": "1",
            "sense": "2",
            "net": "OUT",
            "polarity": "negative",
        },
        {
            "id": "loop.b",
            "kind": "feedback",
            "component": "amp",
            "function": "b",
            "source": "7",
            "sense": "6",
            "net": "PARK",
            "polarity": "negative",
        },
        {
            "id": "supply",
            "kind": "power_rails",
            "component": "amp",
            "unit": 3,
            "positive": "VPLUS",
            "negative": "VMINUS",
            "reference": "REF",
        },
        {
            "id": "bypass.plus",
            "kind": "decoupling",
            "component": "cpos",
            "consumer": _member("amp", "8"),
            "supply": "VPLUS",
            "return": "REF",
        },
        {
            "id": "bypass.minus",
            "kind": "decoupling",
            "component": "cneg",
            "consumer": _member("amp", "4"),
            "supply": "REF",
            "return": "VMINUS",
        },
    ]
    if reverse:
        components.reverse()
        nets.reverse()
        relationships.reverse()
        for net in nets:
            net["members"].reverse()
    return {
        "profile": "m2a.1",
        "id": "dual-buffer",
        "name": "DualBuffer",
        "components": components,
        "nets": nets,
        "relationships": relationships,
        "no_connects": [],
        "power_assertions": [
            {"id": "flag.1", "refdes": "#FLG01", "net": "VPLUS"},
            {"id": "flag.2", "refdes": "#FLG02", "net": "VMINUS"},
            {"id": "flag.3", "refdes": "#FLG03", "net": "REF"},
        ],
    }


def validate(design: dict, assets: dict[str, Asset]) -> dict:
    expected = fixture(next(c["refdes"] for c in design["components"] if c["id"] == "amp"))

    def canonical(data: dict) -> dict:
        data = copy.deepcopy(data)
        for key in ("components", "nets", "relationships"):
            data[key].sort(key=lambda x: x["id"])
        for net in data["nets"]:
            net["members"].sort()
        return data

    if canonical(design) != canonical(expected):
        raise InputError("unsupported M2a Circuit IR or inconsistent relationships")
    if not re.fullmatch(r"U[1-9][0-9]*", expected["components"][0]["refdes"]):
        raise InputError("invalid op-amp reference")
    all_pins = {
        (c["id"], p.number)
        for c in design["components"]
        for unit in assets[c["asset"]].units.values()
        for p in unit
    }
    members = [tuple(m) for n in design["nets"] for m in n["members"]]
    if len(members) != len(set(members)) or set(members) != all_pins:
        raise InputError("M2a physical terminal inventory incomplete")
    return canonical(design)


def _uid(design: dict, kind: str, key: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{design['id']}/{kind}/{key}"))


@dataclass
class Scene:
    positions: dict[tuple[str, int], tuple[int, int]]
    wires: list[tuple[tuple[int, int], tuple[int, int]]]
    wire_nets: list[str]
    labels: list[tuple[str, tuple[int, int]]]
    junctions: list[tuple[int, int]]
    metrics: dict
    angles: dict[tuple[str, int], int] = field(default_factory=dict)
    text_positions: dict[tuple[str, int], tuple[int, int]] = field(default_factory=dict)
    text_angles: dict[tuple[str, int], int] = field(default_factory=dict)


def layout(design: dict, assets: dict[str, Asset]) -> Scene:
    """Construct from function/feedback/decoupling roles and actual pin endpoints."""
    relationships = {r["id"]: r for r in design["relationships"]}
    amp_id = relationships["stage.a"]["component"]
    power = relationships["supply"]
    cpos, cneg = (
        relationships["bypass.plus"]["component"],
        relationships["bypass.minus"]["component"],
    )
    connector = next(c["id"] for c in design["components"] if c["asset"].startswith("Connector_"))
    flags = [a["id"] for a in design["power_assertions"]]
    # Spacing derives from pin/body extents; the origins merely center the motif on A4.
    op = assets["Amplifier_Operational:NE5532"]
    extent = max(abs(p.x) for p in op.units[1])
    step = ((2 * extent + 8 * PITCH + PITCH - 1) // PITCH) * PITCH
    ax, ay = 100 * PITCH, 60 * PITCH
    bx, by = ax, ay + 3 * step
    px, py = ax + 3 * step, ay + 2 * step
    cx, cy = px - step, py
    dx, dy = px + step, py
    jx, jy = ax - 2 * step, ay + step
    positions = {
        (amp_id, 1): (ax, ay),
        (amp_id, 2): (bx, by),
        (amp_id, power["unit"]): (px, py),
        (cpos, 1): (cx, cy),
        (cneg, 1): (dx, dy),
        (connector, 1): (jx, jy),
    }

    def endpoint(component: str, unit: int, number: str) -> tuple[int, int]:
        c = next(c for c in design["components"] if c["id"] == component)
        pin = next(p for p in assets[c["asset"]].units[unit] if p.number == number)
        x, y = positions[(component, unit)]
        return x + pin.x, y - pin.y

    wires = []
    wire_nets = []
    labels = []
    junctions = []

    def route(net: str, *points: tuple[int, int]) -> None:
        segments = [(a, b) for a, b in zip(points, points[1:]) if a != b]
        wires.extend(segments)
        wire_nets.extend([net] * len(segments))

    def label(net: str, point: tuple[int, int], dx: int = 0, dy: int = 0) -> None:
        end = (point[0] + dx, point[1] + dy)
        route(net, point, end)
        labels.append((net, end))

    feedback_spans = []
    input_left_of_output = True
    for unit, output, minus, plus, input_net, out_net in (
        (1, "1", "2", "3", "IN", "OUT"),
        (2, "7", "6", "5", "REF", "PARK"),
    ):
        out = endpoint(amp_id, unit, output)
        inv = endpoint(amp_id, unit, minus)
        noninv = endpoint(amp_id, unit, plus)
        branch = (out[0] + 4 * PITCH, out[1])
        corridor = inv[1] + 8 * PITCH
        left = inv[0] - 4 * PITCH
        feedback_spans.append((branch[0] - left) / 1_000_000)
        input_left_of_output &= noninv[0] < out[0]
        route(out_net, inv, (left, inv[1]), (left, corridor), (branch[0], corridor), branch, out)
        junctions.append(branch)
        if unit == 1:
            label(out_net, branch, 5 * PITCH)
        label(input_net, noninv, -6 * PITCH)
    pos = endpoint(amp_id, 3, "8")
    neg = endpoint(amp_id, 3, "4")
    ct = endpoint(cpos, 1, "1")
    cb = endpoint(cpos, 1, "2")
    nt = endpoint(cneg, 1, "1")
    nb = endpoint(cneg, 1, "2")
    positive_flag = ((ct[0] + pos[0]) // 2, ct[1])
    negative_flag = ((nb[0] + neg[0]) // 2, nb[1])
    route("VPLUS", pos, (pos[0], ct[1]), positive_flag, ct)
    route("VMINUS", neg, (neg[0], nb[1]), negative_flag, nb)
    label("VPLUS", pos)
    label("VMINUS", neg)
    label("REF", cb, -10 * PITCH)
    label("REF", nt, 0, -3 * PITCH)
    for number, net in enumerate(("IN", "OUT", "VPLUS", "VMINUS", "REF"), 1):
        label(net, endpoint(connector, 1, str(number)), -4 * PITCH)
    for flag, point in zip(flags, (positive_flag, negative_flag, (cb[0] - 10 * PITCH, cb[1]))):
        positions[(flag, 1)] = point
    metrics = check_layout(design, assets, positions, wires, wire_nets, labels)
    metrics["feedback_local_span_mm"] = max(feedback_spans)
    metrics["input_left_of_output"] = input_left_of_output
    if not input_left_of_output:
        raise InputError("amplifier input is not left of output")
    return Scene(positions, wires, wire_nets, labels, junctions, metrics)


def check_layout(
    design: dict,
    assets: dict[str, Asset],
    positions: dict,
    wires: list,
    wire_nets: list[str],
    labels: list,
) -> dict:
    if len(set(positions)) != len(positions):
        raise InputError("duplicate symbol occurrence")
    rectangles = []
    for (component, unit), (x, y) in positions.items():
        c = next((c for c in design["components"] if c["id"] == component), None)
        asset_id = c["asset"] if c else "power:PWR_FLAG"
        body = assets[asset_id].bodies.get(unit)
        if body is None:
            continue
        left, top, right, bottom = body
        rectangles.append((component, unit, (x + left, y - top, x + right, y - bottom)))
    for i, (_, _, a) in enumerate(rectangles):
        for _, _, b in rectangles[i + 1 :]:
            if max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3]):
                raise InputError("symbol body overlap")
    for a, b in wires:
        if a[0] != b[0] and a[1] != b[1]:
            raise InputError("non-orthogonal wire")
        for _, _, rect in rectangles:
            if (
                a[0] == b[0]
                and rect[0] < a[0] < rect[2]
                and max(min(a[1], b[1]), rect[1]) < min(max(a[1], b[1]), rect[3])
            ):
                raise InputError("wire through symbol body")
            if (
                a[1] == b[1]
                and rect[1] < a[1] < rect[3]
                and max(min(a[0], b[0]), rect[0]) < min(max(a[0], b[0]), rect[2])
            ):
                raise InputError("wire through symbol body")

    def on_segment(p, a, b):
        return (a[0] == b[0] == p[0] and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])) or (
            a[1] == b[1] == p[1] and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
        )

    for i, (a, b) in enumerate(wires):
        for j in range(i + 1, len(wires)):
            if wire_nets[i] == wire_nets[j]:
                continue
            c, d = wires[j]
            if a[0] == b[0] and c[1] == d[1]:
                if on_segment((a[0], c[1]), a, b) and on_segment((a[0], c[1]), c, d):
                    raise InputError("unrelated wire crossing")
            elif a[1] == b[1] and c[0] == d[0]:
                if on_segment((c[0], a[1]), a, b) and on_segment((c[0], a[1]), c, d):
                    raise InputError("unrelated wire crossing")
            elif a[0] == b[0] == c[0] == d[0]:
                if max(min(a[1], b[1]), min(c[1], d[1])) <= min(max(a[1], b[1]), max(c[1], d[1])):
                    raise InputError("unrelated wire overlap")
            elif a[1] == b[1] == c[1] == d[1]:
                if max(min(a[0], b[0]), min(c[0], d[0])) <= min(max(a[0], b[0]), max(c[0], d[0])):
                    raise InputError("unrelated wire overlap")
    connected_endpoints = {p for wire in wires for p in wire}
    connected_endpoints.update(p for _, p in labels)
    for c in design["components"]:
        for unit, pins in assets[c["asset"]].units.items():
            x, y = positions[(c["id"], unit)]
            for pin in pins:
                point = (x + pin.x, y - pin.y)
                if point not in connected_endpoints:
                    raise InputError(f"pin endpoint is not routed: {c['id']}:{pin.number}")
    all_points = [point for wire in wires for point in wire] + [p for _, p in labels]
    if any(
        not (20_320_000 <= x <= 276_680_000 and 25_400_000 <= y <= 184_600_000)
        for x, y in all_points
    ):
        raise InputError("content outside A4 drafting margin")
    feedback = next(r for r in design["relationships"] if r["id"] == "loop.a")
    if feedback["polarity"] != "negative":
        raise InputError("unsupported feedback polarity")
    return {
        "body_overlap_count": 0,
        "wire_through_body_count": 0,
        "unrelated_wire_crossing_count": 0,
        "unrouted_pin_count": 0,
        "wire_count": len(wires),
        "label_count": len(labels),
        "symbol_occurrences": len(positions),
        "page_margin_pass": True,
    }


def emit(design: dict, assets: dict[str, Asset], scene: Scene, out: Path) -> Path:
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
