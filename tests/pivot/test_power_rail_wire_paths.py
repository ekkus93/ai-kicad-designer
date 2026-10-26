"""Wire-only continuity checks for asserted REF/VCC nets."""

from ai_kicad import m2b_observation


def test_asserted_rail_requires_wire_path_between_all_net_terminals(monkeypatch) -> None:
    design = {
        "components": [
            {"id": "source", "refdes": "J1"},
            {"id": "timer", "refdes": "U1"},
            {"id": "resistor", "refdes": "R1"},
        ],
        "nets": [{"id": "VCC", "members": [["source", "1"], ["timer", "8"], ["resistor", "1"]]}],
        "power_assertions": [{"id": "assert.vcc", "refdes": "#FLG01", "net": "VCC"}],
    }
    positions = {("J1", "1"): (0, 0), ("U1", "8"): (10, 0), ("R1", "1"): (20, 0)}
    pin_to_net = {terminal: "VCC" for terminal in positions}
    trees = {"VCC": object()}
    paths = []

    def reachable(_tree, first, second):
        paths.append((first, second))
        return second != positions[("R1", "1")]

    monkeypatch.setattr(m2b_observation, "conductor_reachable", reachable)
    witnesses = m2b_observation._power_rail_wire_path_witnesses(
        design, positions, pin_to_net, trees
    )

    assert len(paths) == 2
    assert witnesses == [
        {
            "net": "VCC",
            "from_terminal": ["J1", "1"],
            "to_terminal": ["R1", "1"],
            "reason": "no continuous native wire path between same-net terminals",
        }
    ]


def test_asserted_rail_rejects_separate_same_name_label_components(monkeypatch) -> None:
    design = {
        "components": [{"id": "a", "refdes": "J1"}, {"id": "b", "refdes": "U1"}],
        "nets": [{"id": "REF", "members": [["a", "1"], ["b", "1"]]}],
        "power_assertions": [{"id": "assert.ref", "refdes": "#FLG02", "net": "REF"}],
    }
    positions = {("J1", "1"): (0, 0), ("U1", "1"): (100, 0)}
    # Equal net names from the KiCad netlist do not establish a shared wire route.
    disconnected = {"REF": object()}
    monkeypatch.setattr(m2b_observation, "conductor_reachable", lambda *_args: False)
    assert m2b_observation._power_rail_wire_path_witnesses(
        design,
        positions,
        {terminal: "REF" for terminal in positions},
        disconnected,
    )
