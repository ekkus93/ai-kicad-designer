"""Author shared-supply consumer/support interaction circuits."""

from __future__ import annotations

import json

from ai_kicad.m2a import ROOT
from make_m2h2_i4 import series
from make_m2h2_probes import Circuit, amplifier, timer


def case(consumers: int, support: str) -> tuple[dict, dict]:
    assert consumers in (1, 2, 3)
    assert support in {"0", "1-2", "3+"}
    circuit = Circuit(
        f"m2h2_i5_c{consumers}_s{support.replace('-', '_').replace('+', 'plus')}",
        f"M2h2I5C{consumers}S{support.replace('-', '').replace('+', 'Plus')}",
    )
    circuit.part("positive", "J1", "Connector_Generic:Conn_01x01", "Positive supply")
    circuit.net("VPLUS", ("positive", "1"))
    next_connector = 2
    if support != "0":
        circuit.part("negative", "J2", "Connector_Generic:Conn_01x01", "Negative return")
        circuit.net("VMINUS", ("negative", "1"))
        circuit.assertion("VPLUS", 1)
        circuit.assertion("VMINUS", 2)
        next_connector = 3
    # A timer owns four timing/control support cells; a buffer package owns
    # two decoupling cells.  Count physical support cells, not relation kinds.
    timer_count = 0 if support != "3+" else (2 if consumers == 3 else 1)
    amp_count = 1 if support == "1-2" else 0
    passive_count = consumers - timer_count - amp_count
    for index in range(timer_count):
        output = f"TIMER_{index + 1}_OUT"
        timer(
            circuit,
            f"timer_{index + 1}",
            f"U{index + 1}",
            2 * index + 1,
            2 * index + 1,
            "VPLUS",
            "VMINUS",
            output,
        )
        circuit.part(
            f"timer_output_{index + 1}",
            f"J{next_connector}",
            "Connector_Generic:Conn_01x01",
            f"Timer output {index + 1}",
        )
        circuit.add(output, (f"timer_output_{index + 1}", "1"))
        next_connector += 1
    if amp_count:
        circuit.part("reference", f"J{next_connector}", "Connector_Generic:Conn_01x01", "Reference")
        circuit.net("VREF", ("reference", "1"))
        next_connector += 1
        circuit.part("amp_input", f"J{next_connector}", "Connector_Generic:Conn_01x01", "Input")
        circuit.net("AMP_IN", ("amp_input", "1"))
        next_connector += 1
        circuit.part("amp_output", f"J{next_connector}", "Connector_Generic:Conn_01x01", "Output")
        circuit.net("AMP_OUT", ("amp_output", "1"))
        next_connector += 1
        amplifier(
            circuit,
            "stage",
            f"U{timer_count + 1}",
            active="buffer",
            input_net="AMP_IN",
            output_net="AMP_OUT",
            positive="VPLUS",
            negative="VMINUS",
            reference="VREF",
            capacitor_first=2 * timer_count + 1,
        )
    for index in range(passive_count):
        output = f"PASSIVE_{index + 1}_OUT"
        series(circuit, f"load_{index + 1}", f"R{2 * timer_count + index + 1}", "VPLUS", output)
        circuit.part(
            f"passive_output_{index + 1}",
            f"J{next_connector}",
            "Connector_Generic:Conn_01x01",
            f"Passive output {index + 1}",
        )
        circuit.add(output, (f"passive_output_{index + 1}", "1"))
        next_connector += 1
    design, paths = circuit.finish()
    expected = {
        "schema_version": "m2h2.interaction-expected.1",
        "frozen_before_real_layout": True,
        "factor_cell": f"I5:supply_consumers={consumers if consumers < 3 else '3+'}|support_count={support}",
        "selected_triple": [
            "three_gateway_distribution",
            "multiple_shelves",
            "restricted_entry",
        ]
        if consumers == 3 and support == "3+"
        else None,
        "partitions": {net["id"]: sorted(net["members"]) for net in design["nets"]},
        "terminal_inventory": sorted(member for net in design["nets"] for member in net["members"]),
        "path_obligations": paths,
        "precedence": [],
    }
    return design, expected


def main() -> None:
    root = ROOT / "fixtures/m2h2/interaction/i5"
    root.mkdir(parents=True, exist_ok=True)
    for consumers in range(1, 4):
        for support in ("0", "1-2", "3+"):
            design, expected = case(consumers, support)
            stem = f"c{consumers}_s{support.replace('-', '_').replace('+', 'plus')}"
            for suffix, value in (("json", design), ("expected.json", expected)):
                path = root / f"{stem}.{suffix}"
                if path.exists():
                    raise SystemExit(f"refusing to overwrite {path}")
                path.write_text(json.dumps(value, indent=2) + "\n")


if __name__ == "__main__":
    main()
