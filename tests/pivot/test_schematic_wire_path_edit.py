"""Bounded orthogonal wire edits for native schematic review."""

import pytest
from pydantic import ValidationError

from ai_kicad.pivot.schematic_review import AddWirePath, SchematicReview
from ai_kicad.pivot.schematic_review_native import (
    edit_schematic_text,
    resolve_wire_path_points,
    terminal_inventory_for_design,
)
from ai_kicad.sexpr import children, one, parse

SCHEMATIC = """(kicad_sch (version 20250114)
 (lib_symbols (symbol \"Device:R\" (property \"Reference\" \"R\" (at 0 0 0))))
 (wire (pts (xy 10.16 20.32) (xy 20.32 20.32)) (stroke (width 0) (type default)) (uuid \"old\"))
 (symbol (lib_id \"Device:R\") (at 20 30 90) (unit 1)
   (property \"Reference\" \"R1\" (at 25 30 0))
   (property \"Value\" \"10k\" (at 25 33 0))
   (pin \"1\" (uuid \"abc\"))))"""


def path_action(
    start: tuple[str, str] = ("J1", "1"),
    end: tuple[str, str] = ("R1", "1"),
    waypoints: list[tuple[float, float]] | None = None,
) -> AddWirePath:
    return AddWirePath(
        operation="add_wire_path",
        net="VCC",
        from_ref=start[0],
        from_pin=start[1],
        to_ref=end[0],
        to_pin=end[1],
        waypoints=[{"x_mm": x, "y_mm": y} for x, y in (waypoints or [])],
    )


TERMINALS = [
    {"net": "VCC", "reference": "J1", "pin": "1", "x_mm": 30.48, "y_mm": 30.48},
    {"net": "VCC", "reference": "R1", "pin": "1", "x_mm": 45.72, "y_mm": 40.64},
]


def test_wire_path_edit_adds_each_orthogonal_segment_without_rewriting_existing_wire() -> None:
    edited = edit_schematic_text(
        SCHEMATIC,
        [path_action(waypoints=[(30.48, 40.64)])],
        terminal_inventory=TERMINALS,
    )
    before, after = parse(SCHEMATIC), parse(edited)
    assert children(before, "wire") == children(after, "wire")[:1]
    assert len(children(after, "wire")) == 3
    assert all(len(children(wire, "pts")[0][1:]) == 2 for wire in children(after, "wire"))


def test_wire_path_edit_rejects_duplicate_geometry() -> None:
    inventory = [
        {"net": "VCC", "reference": "J1", "pin": "1", "x_mm": 10.16, "y_mm": 20.32},
        {"net": "VCC", "reference": "R1", "pin": "1", "x_mm": 20.32, "y_mm": 20.32},
    ]
    with pytest.raises(ValueError, match="duplicates existing wire geometry"):
        edit_schematic_text(SCHEMATIC, [path_action()], terminal_inventory=inventory)


def test_wire_path_action_accepts_diagonal_waypoints_for_elbow_expansion() -> None:
    inventory = [
        {"net": "VCC", "reference": "J1", "pin": "1", "x_mm": 30.48, "y_mm": 30.48},
        {"net": "VCC", "reference": "R1", "pin": "1", "x_mm": 40.64, "y_mm": 40.64},
    ]
    edited = edit_schematic_text(SCHEMATIC, [path_action()], terminal_inventory=inventory)
    wires = children(parse(edited), "wire")
    assert len(wires) == 3
    assert children(wires[1], "pts")[0][1:] == [
        ["xy", "30.480000", "30.480000"],
        ["xy", "30.480000", "40.640000"],
    ]
    assert children(wires[2], "pts")[0][1:] == [
        ["xy", "30.480000", "40.640000"],
        ["xy", "40.640000", "40.640000"],
    ]


def test_wire_path_is_routed_around_existing_conductor() -> None:
    inventory = [
        {"net": "VCC", "reference": "J1", "pin": "1", "x_mm": 15.24, "y_mm": 15.24},
        {"net": "VCC", "reference": "R1", "pin": "1", "x_mm": 15.24, "y_mm": 25.4},
    ]
    edited = edit_schematic_text(SCHEMATIC, [path_action()], terminal_inventory=inventory)
    new_wires = children(parse(edited), "wire")[1:]
    route_segments = [
        [(float(point[1]), float(point[2])) for point in children(one(wire, "pts"), "xy")]
        for wire in new_wires
    ]
    assert all(first[0] == second[0] or first[1] == second[1] for first, second in route_segments)
    assert all(
        not (
            first[0] == second[0] == 15.24
            and min(first[1], second[1]) < 20.32 < max(first[1], second[1])
        )
        for first, second in route_segments
    )


def test_wire_path_is_routed_around_symbol_body() -> None:
    schematic = SCHEMATIC.replace(
        '(symbol "Device:R" (property "Reference" "R" (at 0 0 0)))',
        '(symbol "Device:R" (symbol "R_1_1" '
        "(rectangle (start -3 -3) (end 3 3))) "
        '(property "Reference" "R" (at 0 0 0)))',
    ).replace("(at 20 30 90)", "(at 20 20 0)")
    inventory = [
        {"net": "VCC", "reference": "J1", "pin": "1", "x_mm": 10.16, "y_mm": 20.32},
        {"net": "VCC", "reference": "R1", "pin": "1", "x_mm": 30.48, "y_mm": 20.32},
    ]
    edited = edit_schematic_text(schematic, [path_action()], terminal_inventory=inventory)
    route_segments = [
        [(float(point[1]), float(point[2])) for point in children(one(wire, "pts"), "xy")]
        for wire in children(parse(edited), "wire")[1:]
    ]
    assert all(
        not (
            (first[1] == second[1] and 17 < first[1] < 23 and first[0] < 23 and second[0] > 17)
            or (first[0] == second[0] and 17 < first[0] < 23 and first[1] < 23 and second[1] > 17)
        )
        for first, second in route_segments
    )


def test_wire_path_rejects_off_grid_route_points() -> None:
    with pytest.raises(ValueError, match="must use the KiCad 1.27 mm grid"):
        edit_schematic_text(
            SCHEMATIC,
            [path_action(waypoints=[(30.5, 40.64)])],
            terminal_inventory=TERMINALS,
        )


def test_wire_path_adds_junction_when_starting_on_existing_conductor() -> None:
    inventory = [
        {"net": "VCC", "reference": "J1", "pin": "1", "x_mm": 15.24, "y_mm": 20.32},
        {"net": "VCC", "reference": "R1", "pin": "1", "x_mm": 15.24, "y_mm": 30.48},
    ]
    edited = edit_schematic_text(SCHEMATIC, [path_action()], terminal_inventory=inventory)
    junctions = children(parse(edited), "junction")
    assert len(junctions) == 1
    assert one(junctions[0], "at")[1:] == ["15.240000", "20.320000"]


def test_wire_path_action_rejects_zero_length_segments() -> None:
    with pytest.raises(ValueError, match="repeats waypoint"):
        edit_schematic_text(
            SCHEMATIC,
            [path_action(start=("J1", "1"), end=("J1", "1"))],
            terminal_inventory=TERMINALS,
        )


def test_wire_path_action_is_available_in_revision_bound_review_contract() -> None:
    review = SchematicReview.model_validate(
        {
            "base_revision": "sha256:" + "a" * 64,
            "decision": "revise",
            "issues": ["visible power rail is split"],
            "actions": [
                {
                    "operation": "add_wire_path",
                    "net": "VCC",
                    "from_ref": "J1",
                    "from_pin": "1",
                    "to_ref": "R1",
                    "to_pin": "1",
                    "waypoints": [],
                }
            ],
            "rationale": "Join the listed VCC terminals with an explicit wire.",
        }
    )
    assert isinstance(review.actions[0], AddWirePath)


def test_wire_path_endpoints_must_match_listed_terminals_on_declared_net() -> None:
    action = path_action()
    inventory = [
        {"net": "VCC", "reference": "J1", "pin": "1", "x_mm": 10, "y_mm": 20},
        {"net": "VCC", "reference": "R1", "pin": "1", "x_mm": 20, "y_mm": 20},
        {"net": "REF", "reference": "R1", "pin": "1", "x_mm": 20, "y_mm": 20},
    ]
    assert [(point.x_mm, point.y_mm) for point in resolve_wire_path_points(action, inventory)] == [
        (10, 20),
        (20, 20),
    ]
    invalid = path_action(end=("J2", "1"))
    with pytest.raises(ValueError, match="J2.1 is not an intended terminal on VCC"):
        resolve_wire_path_points(invalid, inventory)


def test_review_must_submit_only_one_wire_route_per_revision() -> None:
    base = {
        "base_revision": "sha256:" + "a" * 64,
        "decision": "revise",
        "issues": ["connect VCC"],
        "rationale": "Add one route and check it before planning the next.",
    }
    action = {
        "operation": "add_wire_path",
        "net": "VCC",
        "from_ref": "J1",
        "from_pin": "1",
        "to_ref": "R1",
        "to_pin": "1",
        "waypoints": [],
    }
    with pytest.raises(ValidationError, match="at most 1 item"):
        SchematicReview.model_validate({**base, "actions": [action, action]})


def test_terminal_inventory_keeps_intended_net_ownership_after_candidate_netlist_failure() -> None:
    design = {
        "components": [
            {"id": "source", "refdes": "J1"},
            {"id": "load", "refdes": "R1"},
        ],
        "nets": [{"id": "VCC", "members": [["source", "1"], ["load", "1"]]}],
    }
    observed = {
        "pin_positions": {
            ("J1", "1"): (10_000_000, 20_000_000),
            ("R1", "1"): (30_000_000, 20_000_000),
        },
        "nets": {"Net-(R1-1)": [("R1", "1")]},
    }

    inventory = terminal_inventory_for_design(design, observed)

    assert [item["net"] for item in inventory] == ["VCC", "VCC"]
    assert [
        (point.x_mm, point.y_mm) for point in resolve_wire_path_points(path_action(), inventory)
    ] == [(10, 20), (30, 20)]
