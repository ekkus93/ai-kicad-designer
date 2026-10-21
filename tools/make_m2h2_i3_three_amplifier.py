"""Additional compact three-core I3 probe using qualified NE5532 units."""

from __future__ import annotations

import json

from make_m2h2_probes import Circuit, amplifier

from ai_kicad.m2a import ROOT


def case() -> tuple[dict, dict]:
    circuit = Circuit("m2h2_i3_three_amplifier_one_band", "M2h2I3ThreeAmplifierOneBand")
    for cid, ref, value in (
        ("positive", "J1", "Positive rail"),
        ("negative", "J2", "Negative rail"),
        ("reference", "J3", "External reference"),
    ):
        circuit.part(cid, ref, "Connector_Generic:Conn_01x01", value)
    circuit.net("VPLUS", ("positive", "1"))
    circuit.net("VMINUS", ("negative", "1"))
    circuit.net("VREF", ("reference", "1"))
    circuit.assertion("VPLUS", 1)
    circuit.assertion("VMINUS", 2)
    for index in range(1, 4):
        circuit.part(
            f"input_{index}", f"J{2 * index + 2}", "Connector_Generic:Conn_01x01", f"Input {index}"
        )
        circuit.part(
            f"output_{index}",
            f"J{2 * index + 3}",
            "Connector_Generic:Conn_01x01",
            f"Output {index}",
        )
        circuit.net(f"INPUT_{index}", (f"input_{index}", "1"))
        circuit.net(f"OUTPUT_{index}", (f"output_{index}", "1"))
    circuit.part(
        "pair",
        "U1",
        "Amplifier_Operational:NE5532",
        "NE5532",
        functions=[
            {
                "id": "a",
                "role": "buffer",
                "unit": 1,
                "pins": {"out": "1", "minus": "2", "plus": "3"},
            },
            {
                "id": "b",
                "role": "buffer",
                "unit": 2,
                "pins": {"out": "7", "minus": "6", "plus": "5"},
            },
            {
                "id": "power",
                "role": "supply",
                "unit": 3,
                "pins": {"negative": "4", "positive": "8"},
            },
        ],
    )
    circuit.part("pair_cpos", "C1", "Device:C", "100n")
    circuit.part("pair_cneg", "C2", "Device:C", "100n")
    circuit.add("VPLUS", ("pair", "8"), ("pair_cpos", "1"))
    circuit.add("VMINUS", ("pair", "4"), ("pair_cneg", "2"))
    circuit.add("VREF", ("pair_cpos", "2"), ("pair_cneg", "1"))
    for index, function, out_pin, minus_pin, plus_pin in (
        (1, "a", "1", "2", "3"),
        (2, "b", "7", "6", "5"),
    ):
        circuit.add(f"INPUT_{index}", ("pair", plus_pin))
        circuit.add(f"OUTPUT_{index}", ("pair", out_pin), ("pair", minus_pin))
        circuit.relation(
            f"pair.{function}.stage",
            "amplifier",
            component="pair",
            function=function,
            input=f"INPUT_{index}",
            output=f"OUTPUT_{index}",
            reference="VREF",
        )
        circuit.relation(
            f"pair.{function}.loop",
            "feedback",
            component="pair",
            function=function,
            source=out_pin,
            sense=minus_pin,
            net=f"OUTPUT_{index}",
            polarity="negative",
        )
    circuit.relation(
        "pair.rails",
        "power_rails",
        component="pair",
        unit=3,
        positive="VPLUS",
        negative="VMINUS",
        reference="VREF",
    )
    for suffix, pin, supply, ret in (
        ("cpos", "8", "VPLUS", "VREF"),
        ("cneg", "4", "VREF", "VMINUS"),
    ):
        circuit.relation(
            f"pair.{suffix}",
            "decoupling",
            component=f"pair_{suffix}",
            consumer=["pair", pin],
            supply=supply,
            **{"return": ret},
        )
        circuit.path(
            f"pair.{suffix}.support",
            ("pair", pin),
            (f"pair_{suffix}", "1" if suffix == "cpos" else "2"),
            kind="support",
            maximum_span_nm=60_000_000,
        )
    amplifier(
        circuit,
        "single",
        "U2",
        active="buffer",
        input_net="INPUT_3",
        output_net="OUTPUT_3",
        positive="VPLUS",
        negative="VMINUS",
        reference="VREF",
        capacitor_first=3,
    )
    design, paths = circuit.finish()
    expected = {
        "schema_version": "m2h2.interaction-expected.1",
        "frozen_before_real_layout": True,
        "factor_cell": "I3:active_cores=3+|bands=one",
        "active_core_count": 3,
        "requested_band_structure": "one",
        "partitions": {net["id"]: sorted(net["members"]) for net in design["nets"]},
        "terminal_inventory": sorted(member for net in design["nets"] for member in net["members"]),
        "path_obligations": paths,
        "precedence": [],
    }
    return design, expected


def main() -> None:
    root = ROOT / "fixtures/m2h2/interaction/i3"
    root.mkdir(parents=True, exist_ok=True)
    design, expected = case()
    for suffix, value in (("json", design), ("expected.json", expected)):
        path = root / f"three_amplifier_one_band.{suffix}"
        if path.exists():
            raise SystemExit(f"refusing to overwrite {path}")
        path.write_text(json.dumps(value, indent=2) + "\n")


if __name__ == "__main__":
    main()
