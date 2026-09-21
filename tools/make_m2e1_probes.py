"""Author the three fixed M2e1 development probes from reviewed known IRs."""

from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fixtures/m2e1/ir"


def _read(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def _component(identifier: str, refdes: str, asset: str, value: str) -> dict:
    return {"id": identifier, "refdes": refdes, "asset": asset, "value": value}


def amplifier_sallen_key() -> dict:
    design = _read("fixtures/m2blind_v3/ir/V3-4.json")
    design.update(id="m2e1_amp_sallen", name="M2e1AmpSallen")
    remove = {"stage_b_input", "stage_b_feedback"}
    design["components"] = [c for c in design["components"] if c["id"] not in remove]
    design["components"] += [
        _component("sk_upstream", "R3", "Device:R", "10k"),
        _component("sk_filter", "R4", "Device:R", "10k"),
        _component("sk_shunt", "C3", "Device:C", "10n"),
        _component("sk_bridge", "C4", "Device:C", "10n"),
    ]
    amp = next(c for c in design["components"] if c["id"] == "amp")
    next(f for f in amp["functions"] if f["id"] == "b")["role"] = "buffer"
    design["nets"] = [n for n in design["nets"] if n["id"] != "SUM_B"]
    by_net = {n["id"]: n for n in design["nets"]}
    by_net["OUT"]["members"] = [m for m in by_net["OUT"]["members"] if m[0] != "stage_b_input"]
    by_net["OUT"]["members"].append(["sk_upstream", "1"])
    by_net["REF"]["members"] = [
        member for member in by_net["REF"]["members"] if member != ["amp", "5"]
    ]
    by_net["FINAL"]["members"] = [
        ["amp", "7"],
        ["interface", "2"],
        ["sk_bridge", "2"],
        ["amp", "6"],
    ]
    design["nets"] += [
        {
            "id": "SK_INTERMEDIATE",
            "members": [["sk_upstream", "2"], ["sk_filter", "1"], ["sk_bridge", "1"]],
        },
        {"id": "SK_FILTER", "members": [["sk_filter", "2"], ["sk_shunt", "1"], ["amp", "5"]]},
    ]
    by_net["REF"]["members"].append(["sk_shunt", "2"])
    design["relationships"] = [
        r
        for r in design["relationships"]
        if r["id"] not in {"stage.b", "loop.b", "stage_b.input_resistor"}
    ]
    design["relationships"] += [
        {
            "id": "stage.b",
            "kind": "amplifier",
            "component": "amp",
            "function": "b",
            "input": "SK_FILTER",
            "output": "FINAL",
            "reference": "REF",
        },
        {
            "id": "loop.b",
            "kind": "feedback",
            "component": "amp",
            "function": "b",
            "source": "7",
            "sense": "6",
            "net": "FINAL",
            "polarity": "negative",
        },
        {
            "id": "sk.upstream",
            "kind": "series",
            "component": "sk_upstream",
            "input": "OUT",
            "output": "SK_INTERMEDIATE",
        },
        {
            "id": "sk.filter",
            "kind": "series",
            "component": "sk_filter",
            "input": "SK_INTERMEDIATE",
            "output": "SK_FILTER",
        },
        {
            "id": "sk.shunt",
            "kind": "shunt",
            "component": "sk_shunt",
            "node": "SK_FILTER",
            "reference": "REF",
        },
        {
            "id": "sk.bridge",
            "kind": "bridge",
            "component": "sk_bridge",
            "first": "SK_INTERMEDIATE",
            "second": "FINAL",
            "purpose": "feedback",
        },
    ]
    return design


def regulator_parallel_rc() -> dict:
    design = _read("fixtures/m2blind_v3/ir/V3-2.json")
    design.update(id="m2e1_regulator_parallel_rc", name="M2e1RegulatorParallelRc")
    remove = {"indicator_r", "indicator_led"}
    design["components"] = [c for c in design["components"] if c["id"] not in remove]
    design["components"] += [
        _component("filter2_r", "R3", "Device:R", "22"),
        _component("filter2_c", "C4", "Device:C", "10u"),
        _component("load2", "J4", "Connector_Generic:Conn_01x01", "Output 2"),
    ]
    design["nets"] = [n for n in design["nets"] if n["id"] != "LEDMID"]
    by_net = {n["id"]: n for n in design["nets"]}
    for net in by_net.values():
        net["members"] = [m for m in net["members"] if m[0] not in remove]
    by_net["VOUT"]["members"].append(["filter2_r", "1"])
    by_net["REF"]["members"].append(["filter2_c", "2"])
    design["nets"].append(
        {"id": "FILTERED2", "members": [["filter2_r", "2"], ["filter2_c", "1"], ["load2", "1"]]}
    )
    design["relationships"] = [
        r for r in design["relationships"] if not r["id"].startswith("indicator")
    ]
    design["relationships"] += [
        {
            "id": "filter2.series",
            "kind": "series",
            "component": "filter2_r",
            "input": "VOUT",
            "output": "FILTERED2",
        },
        {
            "id": "filter2.shunt",
            "kind": "shunt",
            "component": "filter2_c",
            "node": "FILTERED2",
            "reference": "REF",
        },
    ]
    return design


def dual_timer_led() -> dict:
    design = _read("fixtures/m2blind_v3/ir/V3-8.json")
    design.update(id="m2e1_dual_timer_led", name="M2e1DualTimerLed")
    remove = {"regulator", "regulator_input_c", "regulator_output_c"}
    design["components"] = [c for c in design["components"] if c["id"] not in remove]
    next(c for c in design["components"] if c["id"] == "timer")["refdes"] = "U1"
    additions = []
    for old, new, ref in (
        ("timer", "timer2", "U2"),
        ("charge", "charge2", "R4"),
        ("discharge", "discharge2", "R5"),
        ("timing_cap", "timing_cap2", "C3"),
        ("control_bypass", "control_bypass2", "C4"),
        ("indicator_r", "indicator_r2", "R6"),
        ("indicator_led", "indicator_led2", "D2"),
        ("output", "output2", "J4"),
    ):
        item = copy.deepcopy(next(c for c in design["components"] if c["id"] == old))
        item.update(id=new, refdes=ref)
        additions.append(item)
    design["components"] += additions
    design["nets"] = [n for n in design["nets"] if n["id"] != "VIN"]
    by_net = {n["id"]: n for n in design["nets"]}
    for net in by_net.values():
        net["members"] = [m for m in net["members"] if m[0] not in remove]
    by_net["VCC"]["members"] += [
        ["source", "1"],
        ["timer2", "8"],
        ["timer2", "4"],
        ["charge2", "1"],
    ]
    by_net["REF"]["members"] += [
        ["timer2", "1"],
        ["timing_cap2", "2"],
        ["control_bypass2", "2"],
        ["indicator_led2", "1"],
    ]
    design["nets"] += [
        {"id": "DISCH2", "members": [["charge2", "2"], ["discharge2", "1"], ["timer2", "7"]]},
        {
            "id": "TIMING2",
            "members": [
                ["discharge2", "2"],
                ["timing_cap2", "1"],
                ["timer2", "2"],
                ["timer2", "6"],
            ],
        },
        {"id": "CONT2", "members": [["timer2", "5"], ["control_bypass2", "1"]]},
        {"id": "OUT2", "members": [["timer2", "3"], ["output2", "1"], ["indicator_r2", "1"]]},
        {"id": "LEDMID2", "members": [["indicator_r2", "2"], ["indicator_led2", "2"]]},
    ]
    design["relationships"] = [
        r for r in design["relationships"] if not r["id"].startswith("regulator")
    ]
    design["relationships"] += [
        {
            "id": "timer2.function",
            "kind": "timer",
            "component": "timer2",
            "supply": "VCC",
            "reference": "REF",
            "output": "OUT2",
            "timing": "TIMING2",
            "discharge": "DISCH2",
            "control": "CONT2",
            "pins": {
                "supply": "8",
                "reference": "1",
                "output": "3",
                "trigger": "2",
                "threshold": "6",
                "discharge": "7",
                "control": "5",
                "reset": "4",
            },
        },
        {
            "id": "timing2.network",
            "kind": "timing_ladder",
            "upper": "charge2",
            "lower": "discharge2",
            "capacitor": "timing_cap2",
            "supply": "VCC",
            "discharge": "DISCH2",
            "timing": "TIMING2",
            "reference": "REF",
        },
        {
            "id": "control2.bypass",
            "kind": "decoupling",
            "component": "control_bypass2",
            "consumer": ["timer2", "5"],
            "supply": "CONT2",
            "return": "REF",
        },
        {
            "id": "indicator2.series",
            "kind": "series",
            "component": "indicator_r2",
            "input": "OUT2",
            "output": "LEDMID2",
        },
        {
            "id": "indicator2.polarity",
            "kind": "polarity",
            "component": "indicator_led2",
            "anode": "LEDMID2",
            "cathode": "REF",
        },
    ]
    return design


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    probes = {
        "amplifier_to_sallen_key": amplifier_sallen_key(),
        "regulator_parallel_rc": regulator_parallel_rc(),
        "dual_timer_led": dual_timer_led(),
    }
    for name, design in probes.items():
        (OUT / f"{name}.json").write_text(json.dumps(design, indent=2) + "\n")


if __name__ == "__main__":
    main()
