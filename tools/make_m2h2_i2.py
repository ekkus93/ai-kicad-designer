"""Author shared-reference dependency and consumer-count interaction circuits."""

from __future__ import annotations

import json

from make_m2h2_probes import Circuit, rc

from ai_kicad.m2a import ROOT


def case(reference: str, consumers: int) -> tuple[dict, dict]:
    assert reference in {"external", "internal", "distinct"}
    assert 1 <= consumers <= 3
    circuit = Circuit(
        f"m2h2_i2_{reference}_{consumers}",
        f"M2h2I2{reference.title()}{consumers}",
    )
    circuit.part("input", "J1", "Connector_Generic:Conn_01x01", "Signal input")
    circuit.net("INPUT", ("input", "1"))
    connector_index = 2
    if reference == "external":
        circuit.part("bias", "J2", "Connector_Generic:Conn_01x01", "External bias")
        circuit.net("BIAS", ("bias", "1"))
        connector_index = 3
        reference_nets = ("BIAS",)
    else:
        circuit.part("positive", "J2", "Connector_Generic:Conn_01x01", "Positive rail")
        circuit.part("negative", "J3", "Connector_Generic:Conn_01x01", "Negative rail")
        circuit.net("VPLUS", ("positive", "1"))
        circuit.net("VMINUS", ("negative", "1"))
        connector_index = 4
        reference_nets = ("BIAS",) if reference == "internal" else ("BIAS_A", "BIAS_B")
        for index, net in enumerate(reference_nets):
            upper = f"divider_{index}_upper"
            lower = f"divider_{index}_lower"
            circuit.part(upper, f"R{2 * index + 1}", "Device:R", "10k")
            circuit.part(lower, f"R{2 * index + 2}", "Device:R", "10k")
            circuit.add("VPLUS", (upper, "1"))
            circuit.add("VMINUS", (lower, "2"))
            circuit.net(net, (upper, "2"), (lower, "1"))
            circuit.relation(
                f"divider_{index}",
                "reference_divider",
                upper=upper,
                lower=lower,
                positive="VPLUS",
                local=net,
                negative="VMINUS",
            )
    resistor = 1 if reference == "external" else 2 * len(reference_nets) + 1
    for index in range(consumers):
        net = f"OUTPUT_{index + 1}"
        reference_net = reference_nets[index % len(reference_nets)]
        rc(
            circuit,
            f"consumer_{index + 1}",
            f"R{resistor + index}",
            f"C{index + 1}",
            "INPUT",
            net,
            reference_net,
        )
        circuit.part(
            f"output_{index + 1}",
            f"J{connector_index + index}",
            "Connector_Generic:Conn_01x01",
            f"Output {index + 1}",
        )
        circuit.add(net, (f"output_{index + 1}", "1"))
    design, paths = circuit.finish()
    expected = {
        "schema_version": "m2h2.interaction-expected.1",
        "frozen_before_real_layout": True,
        "factor_cell": f"I2:reference={reference}|distribution_consumers={consumers if consumers < 3 else '3+'}",
        "partitions": {net["id"]: sorted(net["members"]) for net in design["nets"]},
        "terminal_inventory": sorted(member for net in design["nets"] for member in net["members"]),
        "path_obligations": paths,
        "precedence": [],
    }
    return design, expected


def main() -> None:
    root = ROOT / "fixtures/m2h2/interaction/i2"
    root.mkdir(parents=True, exist_ok=True)
    for reference in ("external", "internal", "distinct"):
        for consumers in range(1, 4):
            design, expected = case(reference, consumers)
            stem = f"{reference}_{consumers}"
            for suffix, value in (("json", design), ("expected.json", expected)):
                path = root / f"{stem}.{suffix}"
                if path.exists():
                    raise SystemExit(f"refusing to overwrite {path}")
                path.write_text(json.dumps(value, indent=2) + "\n")


if __name__ == "__main__":
    main()
