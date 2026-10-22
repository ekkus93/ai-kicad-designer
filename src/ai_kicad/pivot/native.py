"""Independent observers for the supported KiCad schematic and PCB subset."""

from __future__ import annotations

import math
import hashlib
from collections import defaultdict
from pathlib import Path

from ai_kicad.m2a import observe
from ai_kicad.m2b import assets, compare, validate
from ai_kicad.sexpr import children, one, parse

from .model import DesignModel


class NativeObservationError(ValueError):
    """Native output is ambiguous or structurally unsafe to reconcile."""


def inspect_schematic(design: dict, schematic: Path, netlist: Path) -> dict:
    tree = parse(schematic.read_text())
    if children(tree, "sheet"):
        raise NativeObservationError(
            "hierarchical schematic sheets are unsupported; refusing ambiguous instance resync"
        )
    root_path = "/" + str(one(tree, "uuid")[1])
    for symbol in children(tree, "symbol"):
        references = [prop[2] for prop in children(symbol, "property") if prop[1] == "Reference"]
        instances = children(symbol, "instances")
        projects = children(instances[0], "project") if len(instances) == 1 else []
        paths = children(projects[0], "path") if len(projects) == 1 else []
        if (
            len(references) != 1
            or len(instances) != 1
            or len(projects) != 1
            or len(paths) != 1
            or paths[0][1] != root_path
        ):
            raise NativeObservationError(
                "schematic instance path is missing, repeated or outside the root sheet"
            )
        path_refs = [entry[1] for entry in children(paths[0], "reference")]
        if path_refs != references:
            raise NativeObservationError("schematic instance path/refdes mismatch")
    expected = validate(design, assets())
    return compare(expected, observe(schematic, netlist))


def verify_pin_pad_maps(model: DesignModel, footprint_root: Path) -> dict:
    """Check approved footprint hashes and physical pad coverage per instance."""
    root = footprint_root.resolve()
    results = []
    errors = []
    for component in model.components:
        if component.footprint is None or component.footprint_sha256 is None:
            errors.append(f"{component.reference}: footprint assignment is missing")
            continue
        library, footprint_name = component.footprint.split(":", 1)
        path = (root / f"{library}.pretty" / f"{footprint_name}.kicad_mod").resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
            errors.append(f"{component.reference}: approved footprint file is absent or unsafe")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != component.footprint_sha256:
            errors.append(f"{component.reference}: approved footprint hash mismatch")
            continue
        footprint = parse(path.read_text())
        pads = [str(pad[1]) for pad in children(footprint, "pad")]
        if len(pads) != len(set(pads)):
            errors.append(f"{component.reference}: footprint has duplicate physical pad numbers")
            continue
        mapping = {entry.pin: entry.pad for entry in component.pin_pad_map}
        pad_one = mapping.get("1")
        if pad_one is not None and pad_one != "1":
            errors.append(f"{component.reference}: symbol pin 1 must map to physical pad 1")
        if set(mapping.values()) - set(pads):
            errors.append(f"{component.reference}: pin/pad map references absent physical pads")
        if set(mapping) != {pin.number for pin in component.pins}:
            errors.append(f"{component.reference}: not every symbol pin has a physical pad")
        results.append(
            {
                "reference": component.reference,
                "footprint": component.footprint,
                "footprint_sha256": digest,
                "mapped_pin_count": len(mapping),
                "required_pin_count": len(component.pins),
                "physical_pad_numbers": sorted(pads),
                "pin_one_pad": pad_one,
            }
        )
    return {
        "status": "PASS" if not errors and len(results) == len(model.components) else "FAIL",
        "revision_id": model.revision_id,
        "components": results,
        "errors": errors,
    }


def assign_footprint_maps(model: DesignModel, assignments: list[dict], footprint_root: Path) -> DesignModel:
    """Return a complete new model revision with explicitly approved footprint mappings."""
    model.require_revision_match()
    by_id = {component.component_id: component for component in model.components}
    unassigned = {key for key, component in by_id.items() if component.footprint is None}
    requested: dict[str, dict] = {}
    for assignment in assignments:
        component_id = assignment["component_id"]
        if component_id not in by_id:
            raise NativeObservationError(f"unknown component_id: {component_id}")
        if component_id not in unassigned:
            raise NativeObservationError(f"component already has an approved footprint: {component_id}")
        if component_id in requested:
            raise NativeObservationError(f"duplicate footprint assignment: {component_id}")
        requested[component_id] = assignment
    if set(requested) != unassigned:
        raise NativeObservationError("assign every unassigned component in one atomic operation")

    root = footprint_root.resolve()
    payload = model.model_dump(mode="json")
    for component in payload["components"]:
        assignment = requested.get(component["component_id"])
        if assignment is None:
            continue
        footprint_name = assignment["footprint"]
        if footprint_name.count(":") != 1:
            raise NativeObservationError("footprint identity must be Library:Footprint")
        library, footprint = footprint_name.split(":", 1)
        path = (root / f"{library}.pretty" / f"{footprint}.kicad_mod").resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
            raise NativeObservationError(f"approved footprint is absent or unsafe: {footprint_name}")
        component["footprint"] = footprint_name
        component["footprint_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        component["pin_pad_map"] = assignment["pin_pad_map"]

    payload["parent_revision"] = model.revision_id
    payload["revision_id"] = "sha256:" + "0" * 64
    candidate = DesignModel.model_validate(payload)
    payload["revision_id"] = candidate.content_revision()
    candidate = DesignModel.model_validate(payload)
    verification = verify_pin_pad_maps(candidate, root)
    if verification["status"] != "PASS":
        raise NativeObservationError("footprint assignment validation failed: " + "; ".join(verification["errors"]))
    return candidate


def _number(node: list, tag: str) -> tuple[float, ...]:
    return tuple(float(value) for value in one(node, tag)[1:] if not isinstance(value, list))


def _position(footprint: list, pad: list) -> tuple[float, float]:
    fx, fy, *rotation = _number(footprint, "at")
    px, py, *_ = _number(pad, "at")
    angle = math.radians(rotation[0] if rotation else 0.0)
    return (
        round(fx + px * math.cos(angle) - py * math.sin(angle), 6),
        round(fy + px * math.sin(angle) + py * math.cos(angle), 6),
    )


class _UnionFind:
    def __init__(self):
        self.parent: dict[tuple, tuple] = {}

    def find(self, item: tuple) -> tuple:
        self.parent.setdefault(item, item)
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, left: tuple, right: tuple) -> None:
        self.parent[self.find(left)] = self.find(right)


def inspect_board(model: DesignModel, board: Path) -> dict:
    """Derive component/pad/net partitions and endpoint copper connectivity."""
    root = parse(board.read_text())
    expected_by_reference = {component.reference: component for component in model.components}
    expected_by_id = {component.component_id: component for component in model.components}
    # Canonical pins map to physical pads; compare physical terminal partitions by exact membership.
    expected_partitions = {
        net.net_id: sorted(
            (
                expected_by_id[terminal.component_id].reference,
                next(
                    mapping.pad
                    for mapping in expected_by_id[terminal.component_id].pin_pad_map
                    if mapping.pin == terminal.pin
                ),
            )
            for terminal in net.terminals
        )
        for net in model.nets
    }
    actual: dict[str, list[tuple[str, str]]] = defaultdict(list)
    pad_positions: dict[str, list[tuple[float, float]]] = defaultdict(list)
    references = set()
    footprint_mismatches = []
    for footprint in children(root, "footprint"):
        reference_properties = [
            item for item in children(footprint, "property") if item[1] == "Reference"
        ]
        if len(reference_properties) != 1:
            raise NativeObservationError("footprint lacks unique Reference property")
        reference = reference_properties[0][2]
        references.add(reference)
        expected_component = expected_by_reference.get(reference)
        if expected_component is None or footprint[1] != expected_component.footprint:
            footprint_mismatches.append(reference)
        for pad in children(footprint, "pad"):
            net = one(pad, "net")[1]
            actual[net].append((reference, str(pad[1])))
            pad_positions[net].append(_position(footprint, pad))
    if len(references) != sum(
        1 for footprint in children(root, "footprint") if children(footprint, "property")
    ):
        raise NativeObservationError("board contains duplicate footprint reference identities")
    partition_map = {}
    unmatched = []
    for canonical, terminals in expected_partitions.items():
        matches = [native for native, observed in actual.items() if sorted(observed) == terminals]
        if len(matches) == 1:
            partition_map[canonical] = matches[0]
        else:
            unmatched.append(canonical)

    graph: dict[str, _UnionFind] = defaultdict(_UnionFind)
    track_count = 0
    track_length = 0.0
    track_widths = []
    via_count = 0
    for segment in children(root, "segment"):
        start = _number(segment, "start")
        end = _number(segment, "end")
        layer = one(segment, "layer")[1]
        net = one(segment, "net")[1]
        graph[net].union((layer, *start), (layer, *end))
        track_count += 1
        track_length += math.dist(start, end)
        track_widths.append(_number(segment, "width")[0])
    for via in children(root, "via"):
        at = _number(via, "at")
        net = one(via, "net")[1]
        layers = one(via, "layers")[1:]
        for layer in layers[1:]:
            graph[net].union((layers[0], *at), (layer, *at))
        via_count += 1
    for net, positions in pad_positions.items():
        for position in positions:
            graph[net].union(("F.Cu", *position), ("B.Cu", *position))
    connectivity = {}
    for canonical, native in partition_map.items():
        positions = pad_positions[native]
        uf = graph[native]
        pad_roots = {
            uf.find((layer, *position))
            for position in positions
            for layer in ("F.Cu", "B.Cu")
            if (layer, *position) in uf.parent
        }
        connectivity[canonical] = len(pad_roots) == 1 and len(positions) >= 2
    return {
        "status": "PASS"
        if not unmatched
        and references == set(expected_by_reference)
        and not footprint_mismatches
        and connectivity
        and all(connectivity.values())
        else "FAIL",
        "component_references": sorted(references),
        "net_name_mapping_by_terminal_partition": partition_map,
        "unmatched_partitions": unmatched,
        "footprint_mismatches": sorted(footprint_mismatches),
        "copper_connectivity": connectivity,
        "metrics": {
            "track_count": track_count,
            "track_length_mm": round(track_length, 4),
            "min_track_width_mm": min(track_widths) if track_widths else None,
            "via_count": via_count,
        },
    }


def board_component_inventory(board: Path) -> dict[str, dict]:
    """Return geometry, footprint and pad/net identities independent of routing."""
    root = parse(board.read_text())
    inventory: dict[str, dict] = {}
    net_names = {
        str(net[1]): str(net[2]) for net in children(root, "net") if len(net) > 2
    }

    def pad_net(pad: list) -> tuple[str, str]:
        net = one(pad, "net")
        identity = str(net[2]) if len(net) > 2 else str(net[1])
        return str(pad[1]), net_names.get(identity, identity)

    for footprint in children(root, "footprint"):
        references = [
            item[2] for item in children(footprint, "property") if item[1] == "Reference"
        ]
        if len(references) != 1:
            raise NativeObservationError("footprint lacks unique Reference property")
        reference = references[0]
        if reference in inventory:
            raise NativeObservationError("board contains duplicate footprint reference identities")
        at = _number(footprint, "at")
        at = (*at[:2], at[2] if len(at) > 2 else 0.0)
        inventory[reference] = {
            "footprint": footprint[1],
            "at": tuple(round(value, 6) for value in at),
            "pads": tuple(
                sorted(
                    pad_net(pad) for pad in children(footprint, "pad")
                )
            ),
        }
    return inventory
