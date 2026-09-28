"""Freeze active-core count by requested band-structure interactions."""

from __future__ import annotations

import json

from ai_kicad.m2a import ROOT
from make_m2h2_probes import Circuit, rc, timer


def case(active: int, band: str) -> tuple[dict, dict]:
    assert active in (0, 1, 2, 3)
    assert band in ("one", "multiple", "interleaved")
    circuit = Circuit(f"m2h2_i3_a{active}_{band}", f"M2h2I3A{active}{band.title()}")
    paths = []
    precedence = []
    if active:
        circuit.part("positive", "J1", "Connector_Generic:Conn_01x01", "Positive supply")
        circuit.part("negative", "J2", "Connector_Generic:Conn_01x01", "Negative return")
        circuit.net("VPLUS", ("positive", "1"))
        circuit.net("VMINUS", ("negative", "1"))
        circuit.assertion("VPLUS", 1)
        circuit.assertion("VMINUS", 2)
        connector = 3
        filters = {"one": 0, "multiple": 1, "interleaved": 2}[band]
        for index in range(active):
            stem = f"timer_{index + 1}"
            timer(
                circuit,
                stem,
                f"U{index + 1}",
                2 * index + 1,
                2 * index + 1,
                "VPLUS",
                "VMINUS",
                f"RAW_{index + 1}",
            )
            if index < filters:
                filter_stem = f"filter_{index + 1}"
                output = f"FILTERED_{index + 1}"
                rc(
                    circuit,
                    filter_stem,
                    f"R{2 * active + index + 1}",
                    f"C{2 * active + index + 1}",
                    f"RAW_{index + 1}",
                    output,
                    "VMINUS",
                )
                precedence.append(
                    {
                        "source": [stem, "3"],
                        "target": [f"{filter_stem}_r", "1"],
                        "strict_x": True,
                    }
                )
            else:
                output = f"RAW_{index + 1}"
            circuit.part(
                f"output_{index + 1}",
                f"J{connector}",
                "Connector_Generic:Conn_01x01",
                f"Channel {index + 1} output",
            )
            circuit.add(output, (f"output_{index + 1}", "1"))
            connector += 1
        # A separate passive branch creates a real backfill opportunity even
        # with a single active core. It does not change the active count.
        if band == "interleaved":
            rc(
                circuit,
                "auxiliary",
                f"R{2 * active + 3}",
                f"C{2 * active + 3}",
                "VPLUS",
                "AUX_OUT",
                "VMINUS",
            )
            circuit.part(
                "aux_output", f"J{connector}", "Connector_Generic:Conn_01x01", "Auxiliary output"
            )
            circuit.add("AUX_OUT", ("aux_output", "1"))
    else:
        circuit.part("input", "J1", "Connector_Generic:Conn_01x01", "Signal input")
        circuit.part("return", "J2", "Connector_Generic:Conn_01x01", "Common return")
        circuit.net("INPUT", ("input", "1"))
        circuit.net("RETURN", ("return", "1"))
        count = {"one": 1, "multiple": 2, "interleaved": 3}[band]
        for index in range(count):
            output = f"OUTPUT_{index + 1}"
            rc(
                circuit,
                f"branch_{index + 1}",
                f"R{index + 1}",
                f"C{index + 1}",
                "INPUT",
                output,
                "RETURN",
            )
            circuit.part(
                f"output_{index + 1}",
                f"J{index + 3}",
                "Connector_Generic:Conn_01x01",
                f"Output {index + 1}",
            )
            circuit.add(output, (f"output_{index + 1}", "1"))
    design, paths = circuit.finish()
    expected = {
        "schema_version": "m2h2.interaction-expected.1",
        "frozen_before_real_layout": True,
        "factor_cell": f"I3:active_cores={active if active < 3 else '3+'}|bands={band}",
        "requested_band_structure": band,
        "active_core_count": active,
        "partitions": {net["id"]: sorted(net["members"]) for net in design["nets"]},
        "terminal_inventory": sorted(member for net in design["nets"] for member in net["members"]),
        "path_obligations": paths,
        "precedence": precedence,
    }
    return design, expected


def main() -> None:
    root = ROOT / "fixtures/m2h2/interaction/i3"
    root.mkdir(parents=True, exist_ok=True)
    for active in (0, 1, 2, 3):
        for band in ("one", "multiple", "interleaved"):
            stem = f"a{active}_{band}"
            design, expected = case(active, band)
            for suffix, value in (("json", design), ("expected.json", expected)):
                path = root / f"{stem}.{suffix}"
                if path.exists():
                    raise SystemExit(f"refusing to overwrite {path}")
                path.write_text(json.dumps(value, indent=2) + "\n")


if __name__ == "__main__":
    main()
