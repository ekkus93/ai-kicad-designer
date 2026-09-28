"""Author the two-tall-core/shared-package/long-field interaction probe."""

from __future__ import annotations

import json

from ai_kicad.m2a import ROOT
from make_m2h2_probes import Circuit, amplifier, rc, timer


def selected_triple() -> tuple[dict, dict]:
    circuit = Circuit("m2h2_i3_selected_triple", "M2h2I3SelectedTriple")
    for cid, ref, value in (
        ("positive", "J1", "Positive supply"),
        ("negative", "J2", "Negative return"),
        ("reference", "J3", "External reference"),
        ("output_a", "J4", "Amplified timing channel A"),
        ("output_b", "J5", "Filtered timing channel B"),
    ):
        circuit.part(cid, ref, "Connector_Generic:Conn_01x01", value)
    circuit.net("VPLUS", ("positive", "1"))
    circuit.net("VMINUS", ("negative", "1"))
    circuit.net("VREF", ("reference", "1"))
    circuit.net("LONG_OUTPUT_CHANNEL_A", ("output_a", "1"))
    circuit.assertion("VPLUS", 1)
    circuit.assertion("VMINUS", 2)
    timer(circuit, "timer_a", "U1", 1, 1, "VPLUS", "VMINUS", "TIMER_A_OUT")
    timer(circuit, "timer_b", "U2", 3, 3, "VPLUS", "VMINUS", "TIMER_B_OUT")
    rc(circuit, "filter_a", "R5", "C7", "TIMER_A_OUT", "FILTERED_A", "VMINUS")
    rc(circuit, "filter_b", "R6", "C8", "TIMER_B_OUT", "OUTPUT_B", "VMINUS")
    circuit.add("OUTPUT_B", ("output_b", "1"))
    amplifier(
        circuit,
        "stage",
        "U3",
        active="buffer",
        input_net="FILTERED_A",
        output_net="LONG_OUTPUT_CHANNEL_A",
        positive="VPLUS",
        negative="VMINUS",
        reference="VREF",
        capacitor_first=5,
    )
    design, paths = circuit.finish()
    expected = {
        "schema_version": "m2h2.interaction-expected.1",
        "frozen_before_real_layout": True,
        "selected_triple": ["two_tall_cores", "shared_package", "long_text"],
        "partitions": {net["id"]: sorted(net["members"]) for net in design["nets"]},
        "terminal_inventory": sorted(member for net in design["nets"] for member in net["members"]),
        "path_obligations": paths,
        "precedence": [
            {"source": ["timer_a", "3"], "target": ["filter_a_r", "1"], "strict_x": True},
            {"source": ["filter_a_r", "2"], "target": ["stage", "3"], "strict_x": True},
            {"source": ["timer_b", "3"], "target": ["filter_b_r", "1"], "strict_x": True},
        ],
    }
    return design, expected


def main() -> None:
    root = ROOT / "fixtures/m2h2/interaction/i3"
    root.mkdir(parents=True, exist_ok=True)
    design, expected = selected_triple()
    for suffix, value in (("json", design), ("expected.json", expected)):
        path = root / f"selected_triple.{suffix}"
        if path.exists():
            raise SystemExit(f"refusing to overwrite {path}")
        path.write_text(json.dumps(value, indent=2) + "\n")


if __name__ == "__main__":
    main()
