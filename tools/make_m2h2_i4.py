"""Author parallel-breadth and protected-path-class interaction circuits."""

from __future__ import annotations

import json

from make_m2h2_probes import Circuit, rc

from ai_kicad.m2a import ROOT


def series(circuit: Circuit, stem: str, ref: str, input_net: str, output_net: str) -> None:
    circuit.part(f"{stem}_r", ref, "Device:R", "1k")
    circuit.add(input_net, (f"{stem}_r", "1"))
    circuit.net(output_net, (f"{stem}_r", "2"))
    circuit.relation(
        f"{stem}.series",
        "series",
        component=f"{stem}_r",
        input=input_net,
        output=output_net,
    )


def case(breadth: int, protected: str) -> tuple[dict, dict]:
    assert breadth in (1, 2, 3)
    assert protected in {"local", "cross", "mixed"}
    circuit = Circuit(
        f"m2h2_i4_b{breadth}_{protected}",
        f"M2h2I4B{breadth}{protected.title()}",
    )
    circuit.part("input", "J1", "Connector_Generic:Conn_01x01", "Signal input")
    circuit.net("INPUT", ("input", "1"))
    connector = 2
    if protected != "cross":
        circuit.part("return", "J2", "Connector_Generic:Conn_01x01", "Common return")
        circuit.net("RETURN", ("return", "1"))
        connector = 3
    source = "INPUT"
    resistor = 1
    capacitor = 1
    if protected == "cross":
        series(circuit, "root", "R1", "INPUT", "FORK")
        source = "FORK"
        resistor = 2
    elif protected == "mixed":
        rc(circuit, "root", "R1", "C1", "INPUT", "FORK", "RETURN")
        source = "FORK"
        resistor = 2
        capacitor = 2
    for branch in range(1, breadth + 1):
        stem = f"branch_{branch}"
        output = f"OUTPUT_{branch}"
        if protected == "local" or (protected == "mixed" and branch == 1):
            rc(circuit, stem, f"R{resistor}", f"C{capacitor}", source, output, "RETURN")
            capacitor += 1
        else:
            series(circuit, stem, f"R{resistor}", source, output)
        resistor += 1
        circuit.part(
            f"output_{branch}",
            f"J{connector + branch - 1}",
            "Connector_Generic:Conn_01x01",
            f"Output {branch}",
        )
        circuit.add(output, (f"output_{branch}", "1"))
        if protected != "local":
            circuit.path(
                f"root.branch_{branch}.cross",
                ("root_r", "2"),
                (f"{stem}_r", "1"),
                kind="cross_fragment",
                maximum_span_nm=80_000_000,
            )
    design, paths = circuit.finish()
    expected = {
        "schema_version": "m2h2.interaction-expected.1",
        "frozen_before_real_layout": True,
        "factor_cell": f"I4:parallel_breadth={breadth if breadth < 3 else '3+'}|protected_paths={protected}",
        "selected_triple": [
            "unequal_consumers",
            "cross_fragment_bound",
            "sibling_vertical_order",
        ]
        if breadth == 2 and protected == "mixed"
        else None,
        "partitions": {net["id"]: sorted(net["members"]) for net in design["nets"]},
        "terminal_inventory": sorted(member for net in design["nets"] for member in net["members"]),
        "path_obligations": paths,
        "precedence": [
            {"source": ["root_r", "2"], "target": [f"branch_{branch}_r", "1"], "strict_x": True}
            for branch in range(1, breadth + 1)
        ]
        if protected != "local"
        else [],
    }
    return design, expected


def main() -> None:
    root = ROOT / "fixtures/m2h2/interaction/i4"
    root.mkdir(parents=True, exist_ok=True)
    for breadth in range(1, 4):
        for protected in ("local", "cross", "mixed"):
            design, expected = case(breadth, protected)
            stem = f"b{breadth}_{protected}"
            for suffix, value in (("json", design), ("expected.json", expected)):
                path = root / f"{stem}.{suffix}"
                if path.exists():
                    raise SystemExit(f"refusing to overwrite {path}")
                path.write_text(json.dumps(value, indent=2) + "\n")


if __name__ == "__main__":
    main()
