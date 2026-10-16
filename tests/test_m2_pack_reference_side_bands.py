"""Fanout columns keep reference-free siblings away from the reference rail."""

from ai_kicad.m2a import PITCH
from ai_kicad.m2_fragments import FragmentVariant, PortAnchor
from ai_kicad.m2_geometry import Gateway
from ai_kicad.m2_pack import _fanout_column_groups, _make_units
from ai_kicad.m2_semantics import BlockPlan, SemanticEdge, SemanticPlan, SemanticPort


def _fragment(block_id: str, kind: str, reference: str | None) -> FragmentVariant:
    ports = []
    gateways = []
    for suffix, role, direction, point in (
        ("input", "signal_in", "left", (0, 4 * PITCH)),
        ("output", "signal_out", "right", (12 * PITCH, 4 * PITCH)),
        ("reference", "reference", reference, (6 * PITCH, 8 * PITCH)),
    ):
        if direction is None:
            continue
        port = SemanticPort(f"{block_id}.{suffix}", block_id, f"{block_id}.{suffix}", role, ())
        ports.append(PortAnchor(port, point, direction))
        gateways.append(
            Gateway(
                port.id,
                port.net,
                (),
                f"{block_id}:{port.net}",
                point,
                direction,
                (point, point),
                frozenset({direction}),
                (),
            )
        )
    block = BlockPlan(block_id, kind, (), frozenset(), tuple(ports))
    return FragmentVariant(
        id=f"{block_id}.v0",
        block=block,
        positions={},
        angles={},
        text_positions={},
        wires=(),
        wire_nets=(),
        labels=(),
        junctions=(),
        ports=tuple(ports),
        envelope=(0, 0, 12 * PITCH, 8 * PITCH if reference else 4 * PITCH),
        protected_wires=frozenset(),
        gateways=tuple(gateways),
    )


def _fanout_plan(chosen: dict[str, FragmentVariant]) -> SemanticPlan:
    return SemanticPlan(
        blocks=tuple(chosen[name].block for name in sorted(chosen)),
        edges=(
            SemanticEdge("signal", "root", "shunted", "fork", ()),
            SemanticEdge("branch", "root", "plain", "fork", ()),
        ),
        owners={},
        signal_order=(),
    )


def _rows(chosen: dict[str, FragmentVariant]) -> dict[str, int]:
    units = _make_units(
        _fanout_plan(chosen),
        chosen,
        attach_branches=False,
        branches_beside=False,
        stack_interfaces=False,
    )
    unit = next(item for item in units if set(item.ids) == set(chosen))
    return {fragment_id: dy for fragment_id, _, dy in unit.offsets}


def test_reference_free_sibling_stacks_above_downward_reference_siblings() -> None:
    chosen = {
        "root": _fragment("root", "rc", "down"),
        "shunted": _fragment("shunted", "rc", "down"),
        "plain": _fragment("plain", "series", None),
    }
    assert _fanout_column_groups(chosen, ("plain", "shunted")) == (("plain",), ("shunted",))
    assert _fanout_column_groups(chosen, ("shunted", "plain")) == (("plain",), ("shunted",))
    rows = _rows(chosen)
    # The signal row stays aligned; the reference-free branch sits above it.
    assert rows["root"] == rows["shunted"]
    assert rows["plain"] < rows["root"]
    assert rows["plain"] + 4 * PITCH < rows["root"]


def test_reference_free_sibling_stacks_below_upward_reference_siblings() -> None:
    chosen = {
        "root": _fragment("root", "rc", "up"),
        "shunted": _fragment("shunted", "rc", "up"),
        "plain": _fragment("plain", "series", None),
    }
    assert _fanout_column_groups(chosen, ("plain", "shunted")) == ((), ("shunted", "plain"))
    rows = _rows(chosen)
    assert rows["root"] == rows["shunted"] == 0
    assert rows["plain"] > rows["shunted"]


def test_uniform_reference_ownership_keeps_declaration_order() -> None:
    chosen = {
        "root": _fragment("root", "rc", "down"),
        "shunted": _fragment("shunted", "rc", "down"),
        "plain": _fragment("plain", "rc", "down"),
    }
    column = ("plain", "shunted")
    assert _fanout_column_groups(chosen, column) == ((), column)
    rows = _rows(chosen)
    assert rows["root"] == rows["plain"] == 0
    assert rows["shunted"] > rows["plain"]


def test_mixed_reference_directions_keep_declaration_order() -> None:
    chosen = {
        "root": _fragment("root", "rc", "down"),
        "shunted": _fragment("shunted", "rc", "right"),
        "plain": _fragment("plain", "series", None),
    }
    column = ("plain", "shunted")
    assert _fanout_column_groups(chosen, column) == ((), column)
    assert _fanout_column_groups(chosen, ("plain",)) == ((), ("plain",))
