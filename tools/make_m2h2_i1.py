"""Author the finite passive depth/branch interaction circuits."""

from __future__ import annotations

import json

from ai_kicad.m2a import ROOT
from make_m2h2_probes import Circuit, amplifier, rc


def case(depth: int, degree: int) -> tuple[dict, list[dict]]:
    circuit = Circuit(f"m2h2_i1_d{depth}_b{degree}", f"M2h2I1D{depth}B{degree}")
    circuit.part("input", "J1", "Connector_Generic:Conn_01x01", "Signal input")
    circuit.part("return", "J2", "Connector_Generic:Conn_01x01", "Common return")
    circuit.net("INPUT", ("input", "1"))
    circuit.net("RETURN", ("return", "1"))
    source = "INPUT"
    resistor = 1
    capacitor = 1
    for stage in range(1, depth):
        output = f"MID_{stage}"
        rc(circuit, f"prefix_{stage}", f"R{resistor}", f"C{capacitor}", source, output, "RETURN")
        resistor += 1
        capacitor += 1
        source = output
    for branch in range(1, degree + 1):
        output = f"OUTPUT_{branch}"
        rc(circuit, f"branch_{branch}", f"R{resistor}", f"C{capacitor}", source, output, "RETURN")
        resistor += 1
        capacitor += 1
        circuit.part(
            f"output_{branch}",
            f"J{branch + 2}",
            "Connector_Generic:Conn_01x01",
            f"Branch {branch} output",
        )
        circuit.add(output, (f"output_{branch}", "1"))
    return circuit.finish()


def expectations(design: dict, paths: list[dict], depth: int, degree: int) -> dict:
    partitions = {net["id"]: sorted(net["members"]) for net in design["nets"]}
    terminal_inventory = sorted((member for members in partitions.values() for member in members))
    source = "INPUT" if depth == 1 else f"MID_{depth - 1}"
    producer = ["input", "1"] if depth == 1 else [f"prefix_{depth - 1}_r", "2"]
    precedence = [
        {
            "source": producer,
            "target": [f"branch_{branch}_r", "1"],
            "strict_x": True,
            "net": source,
        }
        for branch in range(1, degree + 1)
    ]
    return {
        "schema_version": "m2h2.interaction-expected.1",
        "frozen_before_real_layout": True,
        "factor_cell": f"I1:serial_depth={depth if depth < 3 else '3+'}|branch_degree={degree if degree < 3 else '3+'}",
        "partitions": partitions,
        "terminal_inventory": terminal_inventory,
        "path_obligations": paths,
        "precedence": precedence,
    }


def selected_triple(*, powered: bool = False) -> tuple[dict, dict]:
    """Passive intermediate, active successor and an independent sibling band."""
    circuit = Circuit(
        "m2h2_i1_selected_triple_powered" if powered else "m2h2_i1_selected_triple",
        "M2h2I1SelectedTriplePowered" if powered else "M2h2I1SelectedTriple",
    )
    for cid, ref, value in (
        ("input", "J1", "Signal input"),
        ("return", "J2", "Common return"),
        ("output", "J3", "Buffered output"),
        ("branch_output", "J4", "Passive branch"),
        ("positive", "J5", "Positive supply"),
        ("negative", "J6", "Negative supply"),
        ("reference", "J7", "External reference"),
    ):
        circuit.part(cid, ref, "Connector_Generic:Conn_01x01", value)
    for net, pin in (
        ("INPUT", "input"),
        ("RETURN", "return"),
        ("OUT", "output"),
        ("VPLUS", "positive"),
        ("VMINUS", "negative"),
        ("VREF", "reference"),
    ):
        circuit.net(net, (pin, "1"))
    if powered:
        circuit.assertion("VPLUS", 1)
        circuit.assertion("VMINUS", 2)
    rc(circuit, "root", "R1", "C1", "INPUT", "MID", "RETURN")
    rc(circuit, "intermediate", "R2", "C2", "MID", "FILTERED", "RETURN")
    rc(circuit, "sibling", "R3", "C3", "MID", "BRANCH_OUT", "RETURN")
    circuit.add("BRANCH_OUT", ("branch_output", "1"))
    amplifier(
        circuit,
        "stage",
        "U1",
        active="buffer",
        input_net="FILTERED",
        output_net="OUT",
        positive="VPLUS",
        negative="VMINUS",
        reference="VREF",
        capacitor_first=4,
    )
    design, paths = circuit.finish()
    partitions = {net["id"]: sorted(net["members"]) for net in design["nets"]}
    for assertion in design["power_assertions"]:
        partitions[assertion["net"]].append([assertion["id"], "1"])
        partitions[assertion["net"]].sort()
    return design, {
        "schema_version": "m2h2.interaction-expected.1",
        "frozen_before_real_layout": True,
        "selected_triple": ["passive_intermediate", "active_successor", "multiple_bands"],
        "partitions": partitions,
        "terminal_inventory": sorted(
            member for members in partitions.values() for member in members
        ),
        "path_obligations": paths,
        "precedence": [
            {"source": ["root_r", "2"], "target": ["intermediate_r", "1"], "strict_x": True},
            {"source": ["intermediate_r", "2"], "target": ["stage", "3"], "strict_x": True},
            {"source": ["root_r", "2"], "target": ["sibling_r", "1"], "strict_x": True},
        ],
    }


def main() -> None:
    root = ROOT / "fixtures/m2h2/interaction/i1"
    root.mkdir(parents=True, exist_ok=True)
    for depth in range(1, 4):
        for degree in range(1, 4):
            design, paths = case(depth, degree)
            stem = f"d{depth}_b{degree}"
            for suffix, value in (
                ("json", design),
                ("expected.json", expectations(design, paths, depth, degree)),
            ):
                path = root / f"{stem}.{suffix}"
                if path.exists():
                    raise SystemExit(f"refusing to overwrite {path}")
                path.write_text(json.dumps(value, indent=2) + "\n")


if __name__ == "__main__":
    main()
