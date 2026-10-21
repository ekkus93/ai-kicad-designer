"""Implementation details for m2a core."""

from __future__ import annotations

import copy
import itertools
import json
import re
import uuid
from dataclasses import dataclass, field
from types import MappingProxyType

from .assets import _extract_symbol, sha256
from .ir import InputError
from .m2a_constants import (
    ASSETS,
    FILES,
    PITCH,
    ROOT,
)
from .sexpr import children, one, parse, quote


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
    certificate_digest: str | None = None
    certificate_input_digest: str | None = None
    certificate_policy: dict | None = None


def scene_geometry_digest(scene: Scene) -> str:
    """Hash every compiler-owned geometry value consumed by the emitter."""
    payload = {
        "positions": [[key[0], key[1], *point] for key, point in sorted(scene.positions.items())],
        "wires": [
            [list(first), list(second), net]
            for (first, second), net in zip(scene.wires, scene.wire_nets, strict=True)
        ],
        "labels": [[net, *point] for net, point in scene.labels],
        "junctions": [list(point) for point in scene.junctions],
        "angles": [[key[0], key[1], angle] for key, angle in sorted(scene.angles.items())],
        "text_positions": [
            [key[0], key[1], *point] for key, point in sorted(scene.text_positions.items())
        ],
        "text_angles": [
            [key[0], key[1], angle] for key, angle in sorted(scene.text_angles.items())
        ],
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())


def certify_scene_geometry(scene: Scene) -> Scene:
    """Freeze the exact geometry being certified before serialization."""
    if set(scene.positions) != set(scene.text_positions):
        raise InputError(
            f"SCENE_TEXT_POSITION_INCOMPLETE: missing={sorted(set(scene.positions) - set(scene.text_positions))}"
        )
    frozen = Scene(
        MappingProxyType(dict(scene.positions)),
        tuple(scene.wires),
        tuple(scene.wire_nets),
        tuple(scene.labels),
        tuple(scene.junctions),
        dict(scene.metrics),
        MappingProxyType(dict(scene.angles)),
        MappingProxyType(dict(scene.text_positions)),
        MappingProxyType(dict(scene.text_angles)),
    )
    frozen.certificate_digest = scene_geometry_digest(frozen)
    return frozen


def scene_input_digest(scene: Scene, design: dict, assets: dict[str, Asset], policy: dict) -> str:
    """Bind emitted design, locked symbol geometry and gates to one scene."""
    payload = {
        "scene_geometry_sha256": scene_geometry_digest(scene),
        "proof_metrics": scene.metrics,
        "design": design,
        "assets": {
            key: {
                "library_id": asset.library_id,
                "definition": asset.definition,
                "units": {
                    str(unit): [
                        [pin.number, pin.name, pin.electrical_type, pin.x, pin.y] for pin in pins
                    ]
                    for unit, pins in sorted(asset.units.items())
                },
                "bodies": {str(unit): body for unit, body in sorted(asset.bodies.items())},
            }
            for key, asset in sorted(assets.items())
        },
        "policy": policy,
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())


def certify_scene_inputs(
    scene: Scene, design: dict, assets: dict[str, Asset], policy: dict
) -> Scene:
    if scene.certificate_digest is None:
        raise InputError("SCENE_CERTIFICATE_MISSING")
    _assert_scene_certificate(scene)
    scene.certificate_policy = MappingProxyType(dict(policy))
    scene.certificate_input_digest = scene_input_digest(
        scene, design, assets, dict(scene.certificate_policy)
    )
    return scene


def _assert_scene_certificate(
    scene: Scene, design: dict | None = None, assets: dict[str, Asset] | None = None
) -> None:
    if (
        scene.certificate_digest is not None
        and scene_geometry_digest(scene) != scene.certificate_digest
    ):
        raise InputError("SCENE_CERTIFICATE_STALE: serialized geometry changed after proof")
    if scene.certificate_input_digest is not None:
        if scene.certificate_policy is None or design is None or assets is None:
            if design is not None or assets is not None:
                raise InputError("SCENE_CERTIFICATE_INPUTS_INCOMPLETE")
        elif (
            scene_input_digest(scene, design, assets, dict(scene.certificate_policy))
            != scene.certificate_input_digest
        ):
            raise InputError(
                "SCENE_CERTIFICATE_STALE: design, assets or policy changed after proof"
            )


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
        segments = [(a, b) for a, b in itertools.pairwise(points) if a != b]
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
            elif (
                a[0] == b[0] == c[0] == d[0]
                and max(min(a[1], b[1]), min(c[1], d[1])) <= min(max(a[1], b[1]), max(c[1], d[1]))
            ) or (
                a[1] == b[1] == c[1] == d[1]
                and max(min(a[0], b[0]), min(c[0], d[0])) <= min(max(a[0], b[0]), max(c[0], d[0]))
            ):
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
