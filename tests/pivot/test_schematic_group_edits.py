"""Generic rail-connection and symbol-group movement edits for native schematic review."""

import pytest
from pydantic import ValidationError

from ai_kicad.pivot.schematic_review import ConnectRail, MoveSymbols, SchematicReview
from ai_kicad.pivot.schematic_review_native import (
    NativeSchematicEngine,
    _point_groups,
    _release_endpoints,
    edit_schematic_text,
)
from ai_kicad.sexpr import children, one, parse

LIBRARY = (
    '(lib_symbols (symbol "Device:R" (symbol "R_1_1" (rectangle (start -1 -2) (end 1 2))) '
    '(property "Reference" "R" (at 0 0 0))))'
)


def symbol(reference: str, x: float, y: float) -> str:
    return (
        f'(symbol (lib_id "Device:R") (at {x} {y} 0) (unit 1) '
        f'(property "Reference" "{reference}" (at {x + 5.08:.2f} {y} 0)) '
        f'(property "Value" "1k" (at {x + 5.08:.2f} {y + 2.54:.2f} 0)))'
    )


def wire(first: tuple[float, float], second: tuple[float, float]) -> str:
    return (
        f"(wire (pts (xy {first[0]} {first[1]}) (xy {second[0]} {second[1]})) "
        '(stroke (width 0) (type default)) (uuid "w"))'
    )


def terminal(net: str | None, reference: str, pin: str, x: float, y: float) -> dict:
    return {"net": net, "reference": reference, "pin": pin, "x_mm": x, "y_mm": y}


def schematic(*forms: str) -> str:
    return "(kicad_sch (version 20250114) " + LIBRARY + " " + " ".join(forms) + ")"


def wire_points(text: str) -> list[list[tuple[float, float]]]:
    return [
        [(float(point[1]), float(point[2])) for point in children(one(item, "pts"), "xy")]
        for item in children(parse(text), "wire")
    ]


def nm(points: list[tuple[float, float]]) -> list[tuple[int, int]]:
    return [(round(x * 1_000_000), round(y * 1_000_000)) for x, y in points]


RAIL = [
    terminal("VCC", "R1", "1", 25.4, 25.4),
    terminal("VCC", "R2", "1", 76.2, 25.4),
    terminal("VCC", "R3", "1", 50.8, 76.2),
]


def test_connect_rail_wires_every_label_joined_terminal_into_one_tree() -> None:
    text = schematic(
        symbol("R1", 25.4, 30.48), symbol("R2", 76.2, 30.48), symbol("R3", 50.8, 81.28)
    )
    edited = edit_schematic_text(
        text, [ConnectRail(operation="connect_rail", net="VCC")], terminal_inventory=RAIL
    )
    points = nm([(item["x_mm"], item["y_mm"]) for item in RAIL])
    assert len(_point_groups(parse(text), points)) == 3
    assert len(_point_groups(parse(edited), points)) == 1
    assert all(
        first[0] == second[0] or first[1] == second[1] for first, second in wire_points(edited)
    )


def test_connect_rail_reuses_existing_wire_with_a_junction() -> None:
    text = schematic(wire((25.4, 25.4), (76.2, 25.4)))
    inventory = RAIL[:2] + [terminal("VCC", "R3", "1", 50.8, 38.1)]
    edited = edit_schematic_text(
        text, [ConnectRail(operation="connect_rail", net="VCC")], terminal_inventory=inventory
    )
    junctions = [tuple(one(item, "at")[1:3]) for item in children(parse(edited), "junction")]
    assert junctions == [("50.800000", "25.400000")]
    assert sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in wire_points(edited)[1:]) == (
        pytest.approx(12.7)
    )


def test_connect_rail_routes_around_foreign_net_terminals() -> None:
    inventory = RAIL[:2] + [terminal("OUT", "R9", "2", 50.8, 25.4)]
    edited = edit_schematic_text(
        schematic(),
        [ConnectRail(operation="connect_rail", net="VCC")],
        terminal_inventory=inventory,
    )
    assert all(
        not (
            first[1] == second[1] == 25.4
            and min(first[0], second[0]) <= 50.8 <= max(first[0], second[0])
        )
        for first, second in wire_points(edited)
    )


def test_connect_rail_rejects_noop_when_rail_is_already_wired() -> None:
    text = schematic(wire((25.4, 25.4), (76.2, 25.4)))
    with pytest.raises(ValueError, match="already wire-joined"):
        edit_schematic_text(
            text,
            [ConnectRail(operation="connect_rail", net="VCC")],
            terminal_inventory=RAIL[:2],
        )


def test_move_symbols_carries_private_wiring_and_labels() -> None:
    text = schematic(
        symbol("R1", 25.4, 30.48),
        wire((25.4, 25.4), (25.4, 20.32)),
        '(label "VCC" (at 25.4 20.32 0) (effects (font (size 1.27 1.27))) (uuid "l"))',
        wire((101.6, 25.4), (127.0, 25.4)),
    )
    inventory = [terminal("VCC", "R1", "1", 25.4, 25.4), terminal("OUT", "R2", "1", 101.6, 25.4)]
    edited = edit_schematic_text(
        text,
        [MoveSymbols(operation="move_symbols", references=["R1"], dx_mm=12.7, dy_mm=0)],
        terminal_inventory=inventory,
    )
    tree = parse(edited)
    assert one(children(tree, "symbol")[0], "at")[1:3] == ["38.100000", "30.480000"]
    assert one(children(tree, "label")[0], "at")[1:3] == ["38.100000", "20.320000"]
    assert wire_points(edited) == [[(38.1, 25.4), (38.1, 20.32)], [(101.6, 25.4), (127.0, 25.4)]]


def test_move_symbols_reroutes_a_net_shared_with_a_fixed_symbol() -> None:
    text = schematic(
        symbol("R1", 25.4, 30.48), symbol("R2", 76.2, 30.48), wire((25.4, 25.4), (76.2, 25.4))
    )
    inventory = [terminal("N1", "R1", "1", 25.4, 25.4), terminal("N1", "R2", "1", 76.2, 25.4)]
    edited = edit_schematic_text(
        text,
        [MoveSymbols(operation="move_symbols", references=["R1"], dx_mm=0, dy_mm=25.4)],
        terminal_inventory=inventory,
    )
    tree = parse(edited)
    assert one(children(tree, "symbol")[0], "at")[1:3] == ["25.400000", "55.880000"]
    moved_points = nm([(25.4, 50.8), (76.2, 25.4)])
    assert len(_point_groups(tree, moved_points)) == 1
    assert sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in wire_points(edited)) == (
        pytest.approx(25.4 + 50.8)
    )


def test_move_symbols_brings_pin_mounted_flags_along() -> None:
    text = schematic(symbol("R1", 25.4, 30.48), symbol("#FLG01", 25.4, 25.4))
    inventory = [
        terminal("VCC", "R1", "1", 25.4, 25.4),
        terminal(None, "#FLG01", "1", 25.4, 25.4),
    ]
    edited = edit_schematic_text(
        text,
        [MoveSymbols(operation="move_symbols", references=["R1"], dx_mm=-12.7, dy_mm=0)],
        terminal_inventory=inventory,
    )
    positions = [one(item, "at")[1:3] for item in children(parse(edited), "symbol")]
    assert positions == [["12.700000", "30.480000"], ["12.700000", "25.400000"]]


@pytest.mark.parametrize(
    ("action", "message"),
    [
        (
            MoveSymbols(operation="move_symbols", references=["R1"], dx_mm=1.0, dy_mm=0),
            "1.27 mm grid",
        ),
        (
            MoveSymbols(operation="move_symbols", references=["R404"], dx_mm=2.54, dy_mm=0),
            "not found",
        ),
    ],
)
def test_move_symbols_rejects_off_grid_and_unknown_symbols(action, message) -> None:
    with pytest.raises(ValueError, match=message):
        edit_schematic_text(
            schematic(symbol("R1", 25.4, 30.48)),
            [action],
            terminal_inventory=[terminal("VCC", "R1", "1", 25.4, 25.4)],
        )


def test_move_symbols_contract_rejects_noop_and_duplicate_references() -> None:
    for payload in (
        {"references": ["R1"], "dx_mm": 0, "dy_mm": 0},
        {"references": ["R1", "R1"], "dx_mm": 2.54, "dy_mm": 0},
    ):
        with pytest.raises(ValidationError):
            MoveSymbols(operation="move_symbols", **payload)


def test_group_edits_are_available_in_review_contract() -> None:
    review = SchematicReview.model_validate(
        {
            "base_revision": "sha256:" + "0" * 64,
            "decision": "revise",
            "issues": ["VCC is joined only by labels"],
            "actions": [{"operation": "connect_rail", "net": "VCC"}],
            "rationale": "Draw the rail.",
        }
    )
    assert isinstance(review.actions[0], ConnectRail)


def test_body_edge_touching_an_endpoint_is_trimmed_not_dropped() -> None:
    flag_body = (-500_000, -2_000_000, 500_000, 250_000)
    assert _release_endpoints(flag_body, ((0, 0),)) == (-500_000, -2_000_000, 500_000, -100_000)
    assert _release_endpoints((-5_000_000, -5_000_000, 5_000_000, 5_000_000), ((0, 0),)) is None
    assert _release_endpoints(flag_body, ((9_000_000, 0),)) == flag_body


def test_connect_rail_is_limited_to_asserted_power_nets(tmp_path) -> None:
    source = tmp_path / "source.kicad_sch"
    source.write_text(schematic())
    engine = NativeSchematicEngine.__new__(NativeSchematicEngine)
    engine.design = {"power_assertions": [{"net": "VCC"}]}
    with pytest.raises(ValueError, match="asserted power nets"):
        engine.apply(
            source, tmp_path / "candidate", [ConnectRail(operation="connect_rail", net="OUT")]
        )
    assert not (tmp_path / "candidate").exists()


def test_grid_router_matches_exact_segment_admissibility() -> None:
    import random

    from ai_kicad.m2_geometry import Reservation, segment_is_admissible
    from ai_kicad.pivot.schematic_review_native import _grid_route

    rng = random.Random(20261026)
    pitch = 1_270_000
    for trial in range(40):
        obstacles = tuple(
            Reservation(f"o{index}", "exclusive", "R1", "symbol_body", (x, y, x + w, y + h))
            for index in range(6)
            for x, y, w, h in [
                (
                    rng.randrange(0, 40_000_000),
                    rng.randrange(0, 40_000_000),
                    rng.randrange(200_000, 9_000_000),
                    rng.randrange(200_000, 9_000_000),
                )
            ]
        )
        start = (pitch * rng.randrange(0, 32), pitch * rng.randrange(0, 32))
        finish = (pitch * rng.randrange(0, 32), pitch * rng.randrange(0, 32))
        if start == finish:
            continue
        path = _grid_route(start, finish, obstacles)
        if path is None:
            continue
        assert path[0] == start and path[-1] == finish
        for first, second in zip(path, path[1:]):
            assert segment_is_admissible(
                first, second, obstacles, (), net="review-route", owner="new-review-wire"
            ), trial


def test_blocked_connect_rail_feedback_names_movable_references() -> None:
    walls = schematic(
        wire((20.32, 20.32), (30.48, 20.32)),
        wire((20.32, 30.48), (30.48, 30.48)),
        wire((20.32, 20.32), (20.32, 30.48)),
        wire((30.48, 20.32), (30.48, 30.48)),
    )
    inventory = [
        terminal("VCC", "R1", "1", 25.4, 25.4),
        terminal("VCC", "R2", "1", 76.2, 25.4),
        terminal("OUT", "R1", "2", 20.32, 20.32),
    ]
    with pytest.raises(ValueError, match=r"move_symbols for one of \['R1', 'R2'\]"):
        edit_schematic_text(
            walls, [ConnectRail(operation="connect_rail", net="VCC")], terminal_inventory=inventory
        )
    # Under review brief v3 the same blocked route points at power-symbol presentation.
    with pytest.raises(ValueError, match="request use_power_symbols for VCC"):
        edit_schematic_text(
            walls,
            [ConnectRail(operation="connect_rail", net="VCC")],
            terminal_inventory=inventory,
            rail_context={},
        )
