"""Author and validate fixed corpus.v5 without invoking layout or KiCad."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from ai_kicad.m2b import assets, validate


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def load(relative: str) -> dict:
    return copy.deepcopy(json.loads((ROOT / relative).read_text()))


def component(cid: str, refdes: str, asset: str, value: str) -> dict:
    return {"id": cid, "refdes": refdes, "asset": asset, "value": value}


def relation(rid: str, kind: str, **fields: object) -> dict:
    return {"id": rid, "kind": kind, **fields}


def net(data: dict, net_id: str) -> dict:
    return next(item for item in data["nets"] if item["id"] == net_id)


def rel(data: dict, rel_id: str) -> dict:
    return next(item for item in data["relationships"] if item["id"] == rel_id)


def comp(data: dict, component_id: str) -> dict:
    return next(item for item in data["components"] if item["id"] == component_id)


def identify(data: dict, design_id: str, name: str) -> dict:
    data["id"] = design_id
    data["name"] = name
    return data


def add_regulator(data: dict, output: str, start: int) -> None:
    data["components"] += [
        component("regulator", f"U{start}", "Regulator_Linear:L7805", "L7805"),
        component("regulator_input_c", f"C{start + 2}", "Device:C", "330n"),
        component("regulator_output_c", f"C{start + 3}", "Device:C", "100n"),
        component("source", f"J{start}", "Connector_Generic:Conn_01x01", "Supply input"),
    ]
    net(data, output)["members"] += [
        ["regulator", "3"],
        ["regulator_output_c", "1"],
    ]
    net(data, "REF")["members"] += [
        ["regulator", "2"],
        ["regulator_input_c", "2"],
        ["regulator_output_c", "2"],
    ]
    data["nets"].append(
        {
            "id": "VIN",
            "members": [
                ["source", "1"],
                ["regulator", "1"],
                ["regulator_input_c", "1"],
            ],
        }
    )
    data["relationships"] += [
        relation(
            "regulator.conversion",
            "power_stage",
            component="regulator",
            input="VIN",
            output=output,
            reference="REF",
            pins={"input": "1", "output": "3", "reference": "2"},
            polarity="positive",
        ),
        relation(
            "regulator.bypass.input",
            "decoupling",
            component="regulator_input_c",
            consumer=["regulator", "1"],
            supply="VIN",
            **{"return": "REF"},
        ),
        relation(
            "regulator.bypass.output",
            "decoupling",
            component="regulator_output_c",
            consumer=["regulator", "3"],
            supply=output,
            **{"return": "REF"},
        ),
    ]


def v5_1() -> dict:
    data = identify(
        load("fixtures/m2blind_v4/ir/V4-4.json"),
        "regulated_parallel_opamp_channels",
        "V5RegulatedParallelOpampChannels",
    )
    comp(data, "interface")["value"] = "Channel A and rails"
    comp(data, "output_b")["value"] = "Output B"
    data["components"].append(component("input_b", "J3", "Connector_Generic:Conn_01x01", "Input B"))
    net(data, "IN")["id"] = "IN_A"
    net(data, "IN_A")["members"].remove(["amp", "5"])
    data["nets"].append({"id": "IN_B", "members": [["input_b", "1"], ["amp", "5"]]})
    rel(data, "stage.a")["input"] = "IN_A"
    rel(data, "stage.b")["input"] = "IN_B"
    function_b = next(item for item in comp(data, "amp")["functions"] if item["id"] == "b")
    function_b["role"] = "buffer"
    net(data, "OUTB")["members"].remove(["rf_b", "2"])
    net(data, "OUTB")["members"].append(["amp", "6"])
    net(data, "FB")["members"].remove(["amp", "6"])
    net(data, "FB")["members"].remove(["rf_b", "1"])
    net(data, "FB")["members"].remove(["rg_b", "1"])
    net(data, "REF")["members"].remove(["rg_b", "2"])
    data["nets"] = [item for item in data["nets"] if item["id"] != "FB"]
    data["components"] = [item for item in data["components"] if item["id"] not in {"rf_b", "rg_b"}]
    data["relationships"] = [
        item for item in data["relationships"] if item["id"] != "gain_b.reference"
    ]
    rel(data, "loop.b").pop("resistor", None)
    data["components"] += [
        component("rf_a", "R1", "Device:R", "100k"),
        component("rg_a", "R2", "Device:R", "10k"),
    ]
    net(data, "OUT")["members"].remove(["amp", "2"])
    net(data, "OUT")["members"].append(["rf_a", "2"])
    net(data, "REF")["members"].append(["rg_a", "2"])
    data["nets"].append({"id": "FB_A", "members": [["amp", "2"], ["rf_a", "1"], ["rg_a", "1"]]})
    rel(data, "loop.a")["resistor"] = "rf_a"
    data["relationships"].append(
        relation("gain_a.reference", "shunt", component="rg_a", node="FB_A", reference="REF")
    )
    net(data, "VPLUS")["members"].remove(["interface", "3"])
    add_regulator(data, "VPLUS", 4)
    net(data, "VIN")["members"].remove(["source", "1"])
    data["components"] = [item for item in data["components"] if item["id"] != "source"]
    net(data, "VIN")["members"].append(["interface", "3"])
    data["power_assertions"] = [
        {"id": "flag.input", "refdes": "#FLG01", "net": "VIN"},
        {"id": "flag.negative", "refdes": "#FLG02", "net": "VMINUS"},
        {"id": "flag.return", "refdes": "#FLG03", "net": "REF"},
    ]
    return data


def v5_2() -> dict:
    data = identify(
        load("fixtures/m2b/timer_astable.json"),
        "timer_buffer_led",
        "V5TimerBufferLed",
    )
    net(data, "OUT")["members"].remove(["output", "1"])
    data["components"] += [
        {
            **copy.deepcopy(load("fixtures/m2b/noninverting_gain.json")["components"][0]),
            "refdes": "U2",
        },
        component("cpos", "C3", "Device:C", "100n"),
        component("cneg", "C4", "Device:C", "100n"),
        component("negative", "J4", "Connector_Generic:Conn_01x01", "Negative rail"),
        component("indicator_r", "R3", "Device:R", "1k"),
        component("indicator_led", "D1", "Device:LED", "LED"),
    ]
    net(data, "VCC")["members"] += [["amp", "8"], ["cpos", "1"]]
    net(data, "REF")["members"] += [
        ["cpos", "2"],
        ["cneg", "1"],
        ["amp", "5"],
        ["indicator_led", "1"],
    ]
    net(data, "OUT")["members"].append(["amp", "3"])
    data["nets"] += [
        {"id": "VMINUS", "members": [["negative", "1"], ["amp", "4"], ["cneg", "2"]]},
        {
            "id": "BUFFERED",
            "members": [["amp", "1"], ["amp", "2"], ["output", "1"], ["indicator_r", "1"]],
        },
        {"id": "PARK", "members": [["amp", "6"], ["amp", "7"]]},
        {"id": "LEDMID", "members": [["indicator_r", "2"], ["indicator_led", "2"]]},
    ]
    data["relationships"] += [
        relation(
            "buffer.stage",
            "amplifier",
            component="amp",
            function="a",
            input="OUT",
            output="BUFFERED",
            reference="REF",
        ),
        relation(
            "buffer.loop",
            "feedback",
            component="amp",
            function="a",
            source="1",
            sense="2",
            net="BUFFERED",
            polarity="negative",
        ),
        relation(
            "park.stage",
            "amplifier",
            component="amp",
            function="b",
            input="REF",
            output="PARK",
            unused=True,
        ),
        relation(
            "park.loop",
            "feedback",
            component="amp",
            function="b",
            source="7",
            sense="6",
            net="PARK",
            polarity="negative",
        ),
        relation(
            "amp.supply",
            "power_rails",
            component="amp",
            unit=3,
            positive="VCC",
            negative="VMINUS",
            reference="REF",
        ),
        relation(
            "amp.bypass.plus",
            "decoupling",
            component="cpos",
            consumer=["amp", "8"],
            supply="VCC",
            **{"return": "REF"},
        ),
        relation(
            "amp.bypass.minus",
            "decoupling",
            component="cneg",
            consumer=["amp", "4"],
            supply="REF",
            **{"return": "VMINUS"},
        ),
        relation(
            "indicator.series", "series", component="indicator_r", input="BUFFERED", output="LEDMID"
        ),
        relation(
            "indicator.polarity",
            "polarity",
            component="indicator_led",
            anode="LEDMID",
            cathode="REF",
        ),
    ]
    data["power_assertions"] = [
        {"id": "flag.supply", "refdes": "#FLG01", "net": "VCC"},
        {"id": "flag.negative", "refdes": "#FLG02", "net": "VMINUS"},
        {"id": "flag.return", "refdes": "#FLG03", "net": "REF"},
    ]
    return data


def v5_3() -> dict:
    data = identify(
        load("fixtures/m2blind_v4/ir/V4-5.json"),
        "sallen_key_inverting_rc",
        "V5SallenKeyInvertingRc",
    )
    data["components"] = [
        item for item in data["components"] if item["id"] not in {"indicator_r", "indicator_led"}
    ]
    data["relationships"] = [
        item for item in data["relationships"] if not item["id"].startswith("indicator.")
    ]
    data["nets"] = [item for item in data["nets"] if item["id"] != "LEDMID"]
    net(data, "REF")["members"].remove(["indicator_led", "1"])
    net(data, "FINAL")["members"] = []
    net(data, "OUT")["members"].remove(["amp", "5"])
    net(data, "REF")["members"].append(["amp", "5"])
    data["components"] += [
        component("invert_input", "R3", "Device:R", "10k"),
        component("invert_feedback", "R4", "Device:R", "100k"),
        component("output_r", "R5", "Device:R", "1k"),
        component("output_c", "C5", "Device:C", "100n"),
    ]
    net(data, "OUT")["members"].append(["invert_input", "1"])
    net(data, "REF")["members"].append(["output_c", "2"])
    net(data, "FINAL")["members"] = [["amp", "7"], ["invert_feedback", "2"], ["output_r", "1"]]
    data["nets"] += [
        {"id": "SUM_B", "members": [["amp", "6"], ["invert_input", "2"], ["invert_feedback", "1"]]},
        {"id": "FILTERED", "members": [["output_r", "2"], ["output_c", "1"], ["interface", "2"]]},
    ]
    rel(data, "stage.b")["input"] = "OUT"
    rel(data, "loop.b")["resistor"] = "invert_feedback"
    data["relationships"] += [
        relation("invert.input", "series", component="invert_input", input="OUT", output="SUM_B"),
        relation(
            "output.filter.series", "series", component="output_r", input="FINAL", output="FILTERED"
        ),
        relation(
            "output.filter.shunt", "shunt", component="output_c", node="FILTERED", reference="REF"
        ),
    ]
    return data


def v5_4() -> dict:
    data = identify(
        load("fixtures/m2blind_v4/ir/V4-3.json"),
        "reference_parallel_dual_amplifiers",
        "V5ReferenceParallelDualAmplifiers",
    )
    data["components"] = [
        item for item in data["components"] if item["id"] not in {"output_r", "output_c"}
    ]
    data["relationships"] = [
        item for item in data["relationships"] if not item["id"].startswith("output.lowpass")
    ]
    data["nets"] = [item for item in data["nets"] if item["id"] != "FINAL"]
    net(data, "OUT")["members"].remove(["output_r", "1"])
    net(data, "VREF")["members"].remove(["output_c", "2"])
    net(data, "OUT")["members"].append(["interface", "2"])
    data["components"] += [
        component("input_b", "J2", "Connector_Generic:Conn_01x01", "Input B"),
        component("output_b", "J3", "Connector_Generic:Conn_01x01", "Output B"),
        component("input_b_r", "R5", "Device:R", "10k"),
        component("feedback_b", "R6", "Device:R", "100k"),
    ]
    function_b = next(item for item in comp(data, "amp")["functions"] if item["id"] == "b")
    function_b["role"] = "amplifier"
    net(data, "PARK")["id"] = "OUT_B"
    net(data, "OUT_B")["members"] = [["amp", "7"], ["feedback_b", "2"], ["output_b", "1"]]
    net(data, "VREF")["members"].remove(["amp", "5"])
    net(data, "VREF")["members"].append(["amp", "5"])
    data["nets"] += [
        {"id": "IN_B", "members": [["input_b", "1"], ["input_b_r", "1"]]},
        {"id": "SUM_B", "members": [["input_b_r", "2"], ["amp", "6"], ["feedback_b", "1"]]},
    ]
    stage_b = rel(data, "stage.b")
    stage_b.pop("unused")
    stage_b.update(input="IN_B", output="OUT_B", reference="VREF")
    rel(data, "loop.b").update(net="OUT_B", resistor="feedback_b")
    data["relationships"].append(
        relation("input_b.series", "series", component="input_b_r", input="IN_B", output="SUM_B")
    )
    return data


def v5_5() -> dict:
    data = identify(
        load("fixtures/m2e1/ir/dual_timer_led.json"),
        "dual_timer_mixed_loads",
        "V5DualTimerMixedLoads",
    )
    data["components"] = [
        item for item in data["components"] if item["id"] not in {"indicator_r", "indicator_led"}
    ]
    data["relationships"] = [
        item for item in data["relationships"] if not item["id"].startswith("indicator.")
    ]
    data["nets"] = [item for item in data["nets"] if item["id"] != "LEDMID"]
    net(data, "OUT")["members"] = [["timer", "3"], ["filter_r", "1"]]
    net(data, "REF")["members"] = [
        member for member in net(data, "REF")["members"] if member != ["indicator_led", "1"]
    ]
    net(data, "REF")["members"].append(["filter_c", "2"])
    data["components"] += [
        component("filter_r", "R7", "Device:R", "1k"),
        component("filter_c", "C5", "Device:C", "100n"),
    ]
    data["nets"].append(
        {"id": "FILTERED", "members": [["filter_r", "2"], ["filter_c", "1"], ["output", "1"]]}
    )
    data["relationships"] += [
        relation(
            "output.filter.series", "series", component="filter_r", input="OUT", output="FILTERED"
        ),
        relation(
            "output.filter.shunt", "shunt", component="filter_c", node="FILTERED", reference="REF"
        ),
    ]
    return data


def v5_6() -> dict:
    data = identify(
        load("fixtures/m2b/sallen_key.json"),
        "regulated_sallen_key_indicator",
        "V5RegulatedSallenKeyIndicator",
    )
    net(data, "VPLUS")["members"].remove(["interface", "3"])
    data["components"] += [
        component("indicator_r", "R3", "Device:R", "1k"),
        component("indicator_led", "D1", "Device:LED", "LED"),
    ]
    net(data, "OUT")["members"].append(["indicator_r", "1"])
    net(data, "REF")["members"].append(["indicator_led", "1"])
    data["nets"].append({"id": "LEDMID", "members": [["indicator_r", "2"], ["indicator_led", "2"]]})
    data["relationships"] += [
        relation(
            "indicator.series", "series", component="indicator_r", input="OUT", output="LEDMID"
        ),
        relation(
            "indicator.polarity",
            "polarity",
            component="indicator_led",
            anode="LEDMID",
            cathode="REF",
        ),
    ]
    add_regulator(data, "VPLUS", 3)
    net(data, "VIN")["members"].remove(["source", "1"])
    data["components"] = [item for item in data["components"] if item["id"] != "source"]
    net(data, "VIN")["members"].append(["interface", "3"])
    data["power_assertions"] = [
        {"id": "flag.input", "refdes": "#FLG01", "net": "VIN"},
        {"id": "flag.negative", "refdes": "#FLG02", "net": "VMINUS"},
        {"id": "flag.return", "refdes": "#FLG03", "net": "REF"},
    ]
    return data


def v5_7() -> dict:
    data = identify(
        load("fixtures/m2blind_v4/ir/V4-4.json"),
        "highpass_parallel_dual_opamp",
        "V5HighpassParallelDualOpamp",
    )
    data["components"] += [
        component("input_c", "C3", "Device:C", "100n"),
        component("input_r", "R3", "Device:R", "100k"),
    ]
    net(data, "IN")["members"] = [["interface", "1"], ["input_c", "1"]]
    net(data, "REF")["members"].append(["input_r", "2"])
    data["nets"].append(
        {
            "id": "HIGHPASS",
            "members": [["input_c", "2"], ["input_r", "1"], ["amp", "3"], ["amp", "5"]],
        }
    )
    rel(data, "stage.a")["input"] = "HIGHPASS"
    rel(data, "stage.b")["input"] = "HIGHPASS"
    data["relationships"] += [
        relation(
            "input.highpass.series", "series", component="input_c", input="IN", output="HIGHPASS"
        ),
        relation(
            "input.highpass.shunt", "shunt", component="input_r", node="HIGHPASS", reference="REF"
        ),
    ]
    return data


def v5_8() -> dict:
    data = identify(
        load("fixtures/m2blind_v4/ir/V4-6.json"),
        "regulated_timer_dual_output_load",
        "V5RegulatedTimerDualOutputLoad",
    )
    data["components"] += [
        component("indicator_r", "R4", "Device:R", "1k"),
        component("indicator_led", "D1", "Device:LED", "LED"),
    ]
    net(data, "OUT")["members"].append(["indicator_r", "1"])
    net(data, "REF")["members"].append(["indicator_led", "1"])
    data["nets"].append({"id": "LEDMID", "members": [["indicator_r", "2"], ["indicator_led", "2"]]})
    data["relationships"] += [
        relation(
            "indicator.series", "series", component="indicator_r", input="OUT", output="LEDMID"
        ),
        relation(
            "indicator.polarity",
            "polarity",
            component="indicator_led",
            anode="LEDMID",
            cathode="REF",
        ),
    ]
    return data


BUILDERS = [v5_1, v5_2, v5_3, v5_4, v5_5, v5_6, v5_7, v5_8]

DESCRIPTIONS = [
    (
        "regulated_parallel_opamp_channels",
        "regulated independent non-inverting and buffer channels in one NE5532 package",
    ),
    (
        "timer_buffer_led",
        "astable timer feeding an NE5532 buffer, output interface, and LED branch",
    ),
    ("sallen_key_inverting_rc", "Sallen-Key unit feeding an inverting unit and RC output stage"),
    (
        "reference_parallel_dual_amplifiers",
        "shared local reference feeding independent non-inverting and inverting channels",
    ),
    (
        "dual_timer_mixed_loads",
        "two astable timers on one external supply with RC and LED/output loads",
    ),
    ("regulated_sallen_key_indicator", "regulated Sallen-Key active filter with output LED branch"),
    (
        "highpass_parallel_dual_opamp",
        "RC high-pass fanout to buffer and non-inverting NE5532 units",
    ),
    ("regulated_timer_dual_output_load", "regulated timer with LED and RC output branches"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not (HERE / "implementation_freeze.json").is_file():
        raise SystemExit("implementation freeze must exist before corpus authoring")
    if (HERE / "corpus.v5.json").exists() or (HERE / "ir").exists():
        raise SystemExit("refusing to overwrite an existing frozen corpus")
    ir_dir = HERE / "ir"
    ir_dir.mkdir()
    validation = {}
    ir_hashes = {}
    cases = []
    for index, (builder, (design_id, summary)) in enumerate(
        zip(BUILDERS, DESCRIPTIONS, strict=True), 1
    ):
        case_id = f"V5-{index}"
        data = builder()
        if data["id"] != design_id:
            raise RuntimeError(f"builder/design mismatch for {case_id}")
        validate(data, assets())
        path = ir_dir / f"{case_id}.json"
        path.write_text(json.dumps(data, indent=2) + "\n")
        validate(json.loads(path.read_text()), assets())
        ir_hashes[case_id] = sha256(path)
        validation[case_id] = {
            "status": "pass",
            "parser_resolver_semantic_validation": "pass",
        }
        cases.append(
            {
                "case_id": case_id,
                "design_id": design_id,
                "name": data["name"],
                "request_summary": summary,
                "validity": "valid_supported_held_out_request",
                "ir": f"ir/{case_id}.json",
            }
        )
    corpus = {
        "schema_version": "corpus.v5",
        "evaluation": "M2g1 — corpus.v5 frozen blind qualification",
        "split": "held_out_blind",
        "fixed_case_count": 8,
        "required_accepted_count": 8,
        "historical_status": {
            "corpus.v1": "development/tuning evidence",
            "corpus.v2": "historical blind failure and known regression evidence",
            "corpus.v3": "historical blind failure and known regression evidence",
            "corpus.v4": "historical blind failure and known regression evidence",
            "M2f2": "29/29 qualified cases across 69/69 builds",
        },
        "cases": cases,
    }
    corpus_path = HERE / "corpus.v5.json"
    corpus_path.write_text(json.dumps(corpus, indent=2) + "\n")
    (HERE / "corpus.v5.sha256").write_text(f"{sha256(corpus_path)}  corpus.v5.json\n")
    (HERE / "ir.sha256.json").write_text(json.dumps(ir_hashes, indent=2) + "\n")
    (HERE / "ir_validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    print(
        json.dumps(
            {"corpus_sha256": sha256(corpus_path), "ir_sha256": ir_hashes},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
