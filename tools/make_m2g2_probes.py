"""Author and freeze the M2g2 development probes before layout tuning."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fixtures/m2g2/probes"


def component(cid: str, refdes: str, asset: str, value: str, **extra) -> dict:
    return {"id": cid, "refdes": refdes, "asset": asset, "value": value, **extra}


def dual_regulator() -> tuple[dict, list[dict]]:
    components = [
        component("source", "J1", "Connector_Generic:Conn_01x01", "Shared supply input"),
        component("return", "J2", "Connector_Generic:Conn_01x01", "Shared return"),
        component("out_a", "J3", "Connector_Generic:Conn_01x01", "Filtered output A"),
        component("out_b", "J4", "Connector_Generic:Conn_01x01", "Regulated output B"),
        component("reg_a", "U1", "Regulator_Linear:L7805", "L7805"),
        component("reg_b", "U2", "Regulator_Linear:L7805", "L7805"),
        component("a_in_c", "C1", "Device:C", "330n"),
        component("a_out_c", "C2", "Device:C", "100n"),
        component("b_in_c", "C3", "Device:C", "330n"),
        component("b_out_c", "C4", "Device:C", "100n"),
        component("filter_r", "R1", "Device:R", "100"),
        component("filter_c", "C5", "Device:C", "10u"),
        component("indicator_r", "R2", "Device:R", "1k"),
        component("indicator_led", "D1", "Device:LED", "LED"),
    ]
    nets = [
        {
            "id": "VIN",
            "members": [
                ["source", "1"],
                ["reg_a", "1"],
                ["a_in_c", "1"],
                ["reg_b", "1"],
                ["b_in_c", "1"],
            ],
        },
        {
            "id": "REF",
            "members": [
                ["return", "1"],
                ["reg_a", "2"],
                ["a_in_c", "2"],
                ["a_out_c", "2"],
                ["reg_b", "2"],
                ["b_in_c", "2"],
                ["b_out_c", "2"],
                ["filter_c", "2"],
                ["indicator_led", "1"],
            ],
        },
        {"id": "VOUT_A", "members": [["reg_a", "3"], ["a_out_c", "1"], ["filter_r", "1"]]},
        {"id": "FILTERED_A", "members": [["filter_r", "2"], ["filter_c", "1"], ["out_a", "1"]]},
        {
            "id": "VOUT_B",
            "members": [["reg_b", "3"], ["b_out_c", "1"], ["indicator_r", "1"], ["out_b", "1"]],
        },
        {"id": "LED_B", "members": [["indicator_r", "2"], ["indicator_led", "2"]]},
    ]
    relationships = []
    for name in ("a", "b"):
        relationships.extend(
            [
                {
                    "id": f"reg.{name}",
                    "kind": "power_stage",
                    "component": f"reg_{name}",
                    "input": "VIN",
                    "output": f"VOUT_{name.upper()}",
                    "reference": "REF",
                    "pins": {"input": "1", "output": "3", "reference": "2"},
                    "polarity": "positive",
                },
                {
                    "id": f"reg.{name}.input_support",
                    "kind": "decoupling",
                    "component": f"{name}_in_c",
                    "consumer": [f"reg_{name}", "1"],
                    "supply": "VIN",
                    "return": "REF",
                },
                {
                    "id": f"reg.{name}.output_support",
                    "kind": "decoupling",
                    "component": f"{name}_out_c",
                    "consumer": [f"reg_{name}", "3"],
                    "supply": f"VOUT_{name.upper()}",
                    "return": "REF",
                },
            ]
        )
    relationships.extend(
        [
            {
                "id": "a.filter.series",
                "kind": "series",
                "component": "filter_r",
                "input": "VOUT_A",
                "output": "FILTERED_A",
            },
            {
                "id": "a.filter.shunt",
                "kind": "shunt",
                "component": "filter_c",
                "node": "FILTERED_A",
                "reference": "REF",
            },
            {
                "id": "b.indicator.series",
                "kind": "series",
                "component": "indicator_r",
                "input": "VOUT_B",
                "output": "LED_B",
            },
            {
                "id": "b.indicator.polarity",
                "kind": "polarity",
                "component": "indicator_led",
                "anode": "LED_B",
                "cathode": "REF",
            },
        ]
    )
    design = {
        "profile": "m2b.1",
        "id": "m2g2_dual_regulator_mixed_loads",
        "name": "M2g2DualRegulatorMixedLoads",
        "components": components,
        "nets": nets,
        "relationships": relationships,
        "no_connects": [],
        "power_assertions": [
            {"id": "flag.input", "refdes": "#FLG01", "net": "VIN"},
            {"id": "flag.return", "refdes": "#FLG02", "net": "REF"},
        ],
    }
    obligations = [
        {
            "id": f"support.reg_{name}.{pin}",
            "from": [f"reg_{name}", pin],
            "through": [f"{name}_{support}_c", "1"],
            "net": net,
        }
        for name in ("a", "b")
        for pin, support, net in (("1", "in", "VIN"), ("3", "out", f"VOUT_{name.upper()}"))
    ] + [
        {
            "id": "path.output_a",
            "from": ["reg_a", "3"],
            "through": ["filter_r", "1"],
            "to": ["out_a", "1"],
        },
        {
            "id": "path.output_b",
            "from": ["reg_b", "3"],
            "through": ["indicator_r", "1"],
            "to": ["indicator_led", "2"],
        },
    ]
    return design, obligations


def passive_fanout() -> tuple[dict, list[dict]]:
    components = [
        component("input", "J1", "Connector_Generic:Conn_01x01", "Signal input"),
        component("return", "J2", "Connector_Generic:Conn_01x01", "Return"),
        component("out_a", "J3", "Connector_Generic:Conn_01x01", "Branch A output"),
        component("out_b", "J4", "Connector_Generic:Conn_01x01", "Branch B output"),
        component("root_r", "R1", "Device:R", "1k"),
        component("root_c", "C1", "Device:C", "100n"),
        component("a_r", "R2", "Device:R", "2k2"),
        component("a_c", "C2", "Device:C", "47n"),
        component("b_r", "R3", "Device:R", "4k7"),
        component("b_c", "C3", "Device:C", "22n"),
        component("load_r", "R4", "Device:R", "1k"),
        component("load_led", "D1", "Device:LED", "LED"),
    ]
    nets = [
        {"id": "INPUT", "members": [["input", "1"], ["root_r", "1"]]},
        {"id": "FANOUT", "members": [["root_r", "2"], ["root_c", "1"], ["a_r", "1"], ["b_r", "1"]]},
        {
            "id": "BRANCH_A",
            "members": [["a_r", "2"], ["a_c", "1"], ["out_a", "1"], ["load_r", "1"]],
        },
        {"id": "BRANCH_B", "members": [["b_r", "2"], ["b_c", "1"], ["out_b", "1"]]},
        {"id": "LED_NODE", "members": [["load_r", "2"], ["load_led", "2"]]},
        {
            "id": "REF",
            "members": [
                ["return", "1"],
                ["root_c", "2"],
                ["a_c", "2"],
                ["b_c", "2"],
                ["load_led", "1"],
            ],
        },
    ]
    relationships = [
        {
            "id": "root.series",
            "kind": "series",
            "component": "root_r",
            "input": "INPUT",
            "output": "FANOUT",
        },
        {
            "id": "root.shunt",
            "kind": "shunt",
            "component": "root_c",
            "node": "FANOUT",
            "reference": "REF",
        },
        {
            "id": "branch.a.series",
            "kind": "series",
            "component": "a_r",
            "input": "FANOUT",
            "output": "BRANCH_A",
        },
        {
            "id": "branch.a.shunt",
            "kind": "shunt",
            "component": "a_c",
            "node": "BRANCH_A",
            "reference": "REF",
        },
        {
            "id": "branch.b.series",
            "kind": "series",
            "component": "b_r",
            "input": "FANOUT",
            "output": "BRANCH_B",
        },
        {
            "id": "branch.b.shunt",
            "kind": "shunt",
            "component": "b_c",
            "node": "BRANCH_B",
            "reference": "REF",
        },
        {
            "id": "branch.a.load.series",
            "kind": "series",
            "component": "load_r",
            "input": "BRANCH_A",
            "output": "LED_NODE",
        },
        {
            "id": "branch.a.load.polarity",
            "kind": "polarity",
            "component": "load_led",
            "anode": "LED_NODE",
            "cathode": "REF",
        },
    ]
    design = {
        "profile": "m2b.1",
        "id": "m2g2_passive_two_level_fanout",
        "name": "M2g2PassiveTwoLevelFanout",
        "components": components,
        "nets": nets,
        "relationships": relationships,
        "no_connects": [],
        "power_assertions": [{"id": "flag.return", "refdes": "#FLG01", "net": "REF"}],
    }
    obligations = [
        {
            "id": "path.root",
            "from": ["input", "1"],
            "through": ["root_r", "1"],
            "to": ["root_r", "2"],
        },
        {
            "id": "path.branch_a",
            "from": ["root_r", "2"],
            "through": ["a_r", "1"],
            "to": ["out_a", "1"],
        },
        {
            "id": "path.branch_b",
            "from": ["root_r", "2"],
            "through": ["b_r", "1"],
            "to": ["out_b", "1"],
        },
        {
            "id": "path.second_depth",
            "from": ["a_r", "2"],
            "through": ["load_r", "1"],
            "to": ["load_led", "2"],
        },
    ]
    return design, obligations


def timer_gain() -> tuple[dict, list[dict]]:
    base = json.loads((ROOT / "fixtures/m2blind_v5/ir/V5-2.json").read_text())
    base["id"] = "m2g2_timer_split_filtered_gain_indicator"
    base["name"] = "M2g2TimerSplitFilteredGainIndicator"
    base["components"] = [
        c for c in base["components"] if c["id"] not in {"indicator_r", "indicator_led"}
    ]
    base["components"].extend(
        [
            component("highpass_c", "C5", "Device:C", "100n"),
            component("highpass_r", "R3", "Device:R", "100k"),
            component("amp_input_r", "R4", "Device:R", "10k"),
            component("feedback_r", "R5", "Device:R", "47k"),
            component("indicator_r", "R6", "Device:R", "1k"),
            component("indicator_led", "D1", "Device:LED", "LED"),
        ]
    )
    base["nets"] = [
        {
            "id": "VCC",
            "members": [
                ["source", "1"],
                ["timer", "8"],
                ["timer", "4"],
                ["charge", "1"],
                ["amp", "8"],
                ["cpos", "1"],
            ],
        },
        {"id": "DISCH", "members": [["charge", "2"], ["discharge", "1"], ["timer", "7"]]},
        {
            "id": "TIMING",
            "members": [["discharge", "2"], ["timing_cap", "1"], ["timer", "2"], ["timer", "6"]],
        },
        {"id": "OUT", "members": [["timer", "3"], ["highpass_c", "1"], ["indicator_r", "1"]]},
        {
            "id": "COUPLED",
            "members": [["highpass_c", "2"], ["highpass_r", "1"], ["amp_input_r", "1"]],
        },
        {"id": "SUM", "members": [["amp_input_r", "2"], ["amp", "2"], ["feedback_r", "1"]]},
        {"id": "GAIN_OUT", "members": [["amp", "1"], ["feedback_r", "2"], ["output", "1"]]},
        {
            "id": "REF",
            "members": [
                ["timer", "1"],
                ["timing_cap", "2"],
                ["control_bypass", "2"],
                ["return", "1"],
                ["cpos", "2"],
                ["cneg", "1"],
                ["amp", "3"],
                ["amp", "5"],
                ["highpass_r", "2"],
                ["indicator_led", "1"],
            ],
        },
        {"id": "CONT", "members": [["timer", "5"], ["control_bypass", "1"]]},
        {"id": "VMINUS", "members": [["negative", "1"], ["amp", "4"], ["cneg", "2"]]},
        {"id": "PARK", "members": [["amp", "6"], ["amp", "7"]]},
        {"id": "LEDMID", "members": [["indicator_r", "2"], ["indicator_led", "2"]]},
    ]
    keep = [
        r
        for r in base["relationships"]
        if r["id"] not in {"buffer.stage", "buffer.loop", "indicator.series", "indicator.polarity"}
    ]
    keep.extend(
        [
            {
                "id": "gain.stage",
                "kind": "amplifier",
                "component": "amp",
                "function": "a",
                "input": "COUPLED",
                "output": "GAIN_OUT",
                "reference": "REF",
            },
            {
                "id": "gain.feedback",
                "kind": "feedback",
                "component": "amp",
                "function": "a",
                "source": "1",
                "sense": "2",
                "net": "GAIN_OUT",
                "polarity": "negative",
                "resistor": "feedback_r",
            },
            {
                "id": "highpass.series",
                "kind": "series",
                "component": "highpass_c",
                "input": "OUT",
                "output": "COUPLED",
            },
            {
                "id": "highpass.shunt",
                "kind": "shunt",
                "component": "highpass_r",
                "node": "COUPLED",
                "reference": "REF",
            },
            {
                "id": "gain.input",
                "kind": "series",
                "component": "amp_input_r",
                "input": "COUPLED",
                "output": "SUM",
            },
            {
                "id": "indicator.series",
                "kind": "series",
                "component": "indicator_r",
                "input": "OUT",
                "output": "LEDMID",
            },
            {
                "id": "indicator.polarity",
                "kind": "polarity",
                "component": "indicator_led",
                "anode": "LEDMID",
                "cathode": "REF",
            },
        ]
    )
    base["relationships"] = keep
    obligations = [
        {
            "id": "path.timer_highpass_gain",
            "from": ["timer", "3"],
            "through": [["highpass_c", "1"], ["amp_input_r", "1"], ["amp", "2"]],
            "to": ["amp", "1"],
        },
        {
            "id": "path.timer_indicator",
            "from": ["timer", "3"],
            "through": ["indicator_r", "1"],
            "to": ["indicator_led", "2"],
        },
        {
            "id": "path.gain_feedback",
            "from": ["amp", "1"],
            "through": ["feedback_r", "2"],
            "to": ["amp", "2"],
        },
        {
            "id": "path.timer_timing",
            "from": ["timer", "7"],
            "through": [["charge", "2"], ["discharge", "1"]],
            "to": ["timer", "2"],
        },
    ]
    return base, obligations


def partitions(design: dict) -> dict:
    return {
        net["id"]: sorted(net["members"]) for net in sorted(design["nets"], key=lambda n: n["id"])
    }


def write_case(case_id: str, design: dict, obligations: list[dict], *, ancestry: list[str]) -> dict:
    filename = f"{case_id}.json"
    expected_name = f"{case_id}.expected.json"
    design_text = json.dumps(design, indent=2, sort_keys=False) + "\n"
    expected = {
        "schema_version": "m2g2.probe-expectations.1",
        "frozen_before_layout_tuning": True,
        "partitions": partitions(design),
        "path_obligations": obligations,
        "ancestry_comparison": ancestry,
        "minimum_local_access_variants": 2,
    }
    expected_text = json.dumps(expected, indent=2, sort_keys=True) + "\n"
    (OUT / filename).write_text(design_text)
    (OUT / expected_name).write_text(expected_text)
    return {
        "id": case_id,
        "design_id": design["id"],
        "file": filename,
        "expectations": expected_name,
        "ir_sha256": hashlib.sha256(design_text.encode()).hexdigest(),
        "expectations_sha256": hashlib.sha256(expected_text.encode()).hexdigest(),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    reg, reg_obligations = dual_regulator()
    fanout, fanout_obligations = passive_fanout()
    timer, timer_obligations = timer_gain()
    long_fields = copy.deepcopy(fanout)
    long_fields["id"] += "_long_fields"
    long_fields["name"] += "LongFields"
    next(c for c in long_fields["components"] if c["id"] == "out_b")["value"] = (
        "CONNECTOR_VALUE_24_CHARS"
    )
    assert len(next(c for c in long_fields["components"] if c["id"] == "out_b")["value"]) == 24
    old_net, new_net = "BRANCH_B", "REQUIRED_NET_LABEL20"
    assert len(new_net) == 20
    next(n for n in long_fields["nets"] if n["id"] == old_net)["id"] = new_net
    for relation in long_fields["relationships"]:
        for key, value in tuple(relation.items()):
            if value == old_net:
                relation[key] = new_net
    exchanged = copy.deepcopy(timer)
    exchanged["id"] += "_unit_exchange"
    exchanged["name"] += "UnitExchange"
    amp = next(c for c in exchanged["components"] if c["id"] == "amp")
    a, b = amp["functions"][0], amp["functions"][1]
    a["unit"], b["unit"] = b["unit"], a["unit"]
    a["pins"], b["pins"] = b["pins"], a["pins"]
    pin_swap = {"1": "7", "2": "6", "3": "5", "7": "1", "6": "2", "5": "3"}
    for net in exchanged["nets"]:
        net["members"] = [
            [cid, pin_swap.get(pin, pin) if cid == "amp" else pin] for cid, pin in net["members"]
        ]
    for relation in exchanged["relationships"]:
        if relation["kind"] == "feedback" and relation["component"] == "amp":
            relation["source"] = pin_swap[relation["source"]]
            relation["sense"] = pin_swap[relation["sense"]]

    cases = [
        write_case(
            "dual_regulator_mixed_loads",
            reg,
            reg_obligations,
            ancestry=[
                "new topology; compared with m2e1 regulator_parallel_rc and m2f2 regulator_three_consumers"
            ],
        ),
        write_case(
            "passive_two_level_fanout",
            fanout,
            fanout_obligations,
            ancestry=["new passive-only two-level topology; no active-stage ancestor"],
        ),
        write_case(
            "timer_split_filtered_gain_indicator",
            timer,
            timer_obligations,
            ancestry=[
                "new composition of timer support, high-pass, inverting gain, and direct indicator; compared with V5-2 and V3-6"
            ],
        ),
        write_case(
            "passive_two_level_fanout_long_fields",
            long_fields,
            fanout_obligations,
            ancestry=["metamorphic field/net-width stress of passive_two_level_fanout"],
        ),
        write_case(
            "timer_split_filtered_gain_indicator_unit_exchange",
            exchanged,
            timer_obligations,
            ancestry=["supported A/B unit exchange of timer_split_filtered_gain_indicator"],
        ),
    ]
    manifest = {
        "schema_version": "m2g2.probes.1",
        "authored_before_layout_tuning": True,
        "cases": cases,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
