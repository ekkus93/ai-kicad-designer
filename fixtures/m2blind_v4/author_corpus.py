"""Author and validate the fixed corpus.v4 without invoking layout or KiCad."""

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


def identify(data: dict, design_id: str, name: str) -> dict:
    data["id"] = design_id
    data["name"] = name
    return data


def opamp_flags(reference: str = "REF") -> list[dict]:
    flags = [
        {"id": "flag.positive", "refdes": "#FLG01", "net": "VPLUS"},
        {"id": "flag.negative", "refdes": "#FLG02", "net": "VMINUS"},
    ]
    if reference == "REF":
        flags.append({"id": "flag.reference", "refdes": "#FLG03", "net": reference})
    return flags


def add_led(data: dict, source: str, reference: str, r_ref: str = "R9") -> None:
    data["components"] += [
        component("indicator_r", r_ref, "Device:R", "1k"),
        component("indicator_led", "D1", "Device:LED", "LED"),
    ]
    net(data, source)["members"].append(["indicator_r", "1"])
    net(data, reference)["members"].append(["indicator_led", "1"])
    data["nets"].append(
        {"id": "LEDMID", "members": [["indicator_r", "2"], ["indicator_led", "2"]]}
    )
    data["relationships"] += [
        relation("indicator.series", "series", component="indicator_r", input=source, output="LEDMID"),
        relation(
            "indicator.polarity",
            "polarity",
            component="indicator_led",
            anode="LEDMID",
            cathode=reference,
        ),
    ]


def v4_1() -> dict:
    data = identify(load("fixtures/m2b/inverting_gain.json"), "lowpass_inverting_led", "V4LowpassInvertingLed")
    net(data, "IN")["members"].remove(["rin", "1"])
    net(data, "IN")["members"].append(["input_filter_r", "1"])
    net(data, "REF")["members"].append(["input_filter_c", "2"])
    data["nets"].append(
        {
            "id": "FILTERED",
            "members": [["input_filter_r", "2"], ["input_filter_c", "1"], ["rin", "1"]],
        }
    )
    data["components"] += [
        component("input_filter_r", "R3", "Device:R", "10k"),
        component("input_filter_c", "C3", "Device:C", "10n"),
    ]
    data["relationships"] += [
        relation("input.lowpass.series", "series", component="input_filter_r", input="IN", output="FILTERED"),
        relation("input.lowpass.shunt", "shunt", component="input_filter_c", node="FILTERED", reference="REF"),
    ]
    rel(data, "input_resistor")["input"] = "FILTERED"
    add_led(data, "OUT", "REF", "R4")
    data["power_assertions"] = opamp_flags()
    return data


def v4_2() -> dict:
    data = identify(load("fixtures/m2b/noninverting_gain.json"), "highpass_noninverting_lowpass", "V4HighpassNoninvertingLowpass")
    net(data, "IN")["members"].remove(["amp", "3"])
    net(data, "IN")["members"].append(["input_c", "1"])
    net(data, "REF")["members"] += [["input_r", "2"], ["output_c", "2"]]
    net(data, "OUT")["members"].remove(["interface", "2"])
    net(data, "OUT")["members"].append(["output_r", "1"])
    data["nets"] += [
        {"id": "COUPLED", "members": [["input_c", "2"], ["input_r", "1"], ["amp", "3"]]},
        {"id": "FINAL", "members": [["output_r", "2"], ["output_c", "1"], ["interface", "2"]]},
    ]
    data["components"] += [
        component("input_c", "C3", "Device:C", "100n"),
        component("input_r", "R3", "Device:R", "100k"),
        component("output_r", "R4", "Device:R", "1k"),
        component("output_c", "C4", "Device:C", "100n"),
    ]
    rel(data, "stage.a")["input"] = "COUPLED"
    data["relationships"] += [
        relation("input.highpass.series", "series", component="input_c", input="IN", output="COUPLED"),
        relation("input.highpass.shunt", "shunt", component="input_r", node="COUPLED", reference="REF"),
        relation("output.lowpass.series", "series", component="output_r", input="OUT", output="FINAL"),
        relation("output.lowpass.shunt", "shunt", component="output_c", node="FINAL", reference="REF"),
    ]
    data["power_assertions"] = opamp_flags()
    return data


def v4_3() -> dict:
    data = identify(load("fixtures/m2b/dual_rail_reference.json"), "reference_noninverting_rc", "V4ReferenceNoninvertingRc")
    net(data, "OUT")["members"].remove(["amp", "2"])
    net(data, "OUT")["members"].remove(["interface", "2"])
    net(data, "OUT")["members"] += [["feedback_r", "2"], ["output_r", "1"]]
    net(data, "VREF")["members"] += [["gain_r", "2"], ["output_c", "2"]]
    data["nets"] += [
        {"id": "FB", "members": [["amp", "2"], ["feedback_r", "1"], ["gain_r", "1"]]},
        {"id": "FINAL", "members": [["output_r", "2"], ["output_c", "1"], ["interface", "2"]]},
    ]
    data["components"] += [
        component("feedback_r", "R3", "Device:R", "100k"),
        component("gain_r", "R4", "Device:R", "10k"),
        component("output_r", "R5", "Device:R", "1k"),
        component("output_c", "C3", "Device:C", "100n"),
    ]
    rel(data, "loop.a")["resistor"] = "feedback_r"
    data["relationships"] += [
        relation("gain.reference", "shunt", component="gain_r", node="FB", reference="VREF"),
        relation("output.lowpass.series", "series", component="output_r", input="OUT", output="FINAL"),
        relation("output.lowpass.shunt", "shunt", component="output_c", node="FINAL", reference="VREF"),
    ]
    data["power_assertions"] = opamp_flags("VREF")
    return data


def v4_4() -> dict:
    data = identify(load("fixtures/m2b/noninverting_gain.json"), "parallel_dual_opamp_functions", "V4ParallelDualOpampFunctions")
    function_b = next(item for item in data["components"][0]["functions"] if item["id"] == "b")
    function_b["role"] = "amplifier"
    data["components"].append(component("output_b", "J2", "Connector_Generic:Conn_01x01", "Output B"))
    net(data, "REF")["members"].remove(["amp", "5"])
    net(data, "IN")["members"].append(["amp", "5"])
    net(data, "OUT")["members"].remove(["rf", "2"])
    net(data, "OUT")["members"].append(["amp", "2"])
    net(data, "REF")["members"].remove(["rg", "2"])
    park = net(data, "PARK")
    park["id"] = "OUTB"
    park["members"] = [["amp", "7"], ["rf_b", "2"], ["output_b", "1"]]
    net(data, "FB")["members"] = [["amp", "6"], ["rf_b", "1"], ["rg_b", "1"]]
    net(data, "REF")["members"].append(["rg_b", "2"])
    data["components"] = [item for item in data["components"] if item["id"] not in {"rf", "rg"}]
    data["components"] += [
        component("rf_b", "R1", "Device:R", "100k"),
        component("rg_b", "R2", "Device:R", "10k"),
    ]
    data["relationships"] = [
        item for item in data["relationships"] if item["id"] not in {"gain_reference"}
    ]
    rel(data, "loop.a").pop("resistor", None)
    stage_b = rel(data, "stage.b")
    stage_b.pop("unused")
    stage_b.update(input="IN", output="OUTB", reference="REF")
    rel(data, "loop.b").update(net="OUTB", resistor="rf_b")
    data["relationships"].append(
        relation("gain_b.reference", "shunt", component="rg_b", node="FB", reference="REF")
    )
    data["power_assertions"] = opamp_flags()
    return data


def v4_5() -> dict:
    data = identify(load("fixtures/m2b/sallen_key.json"), "sallen_key_buffer_led", "V4SallenKeyBufferLed")
    function_b = next(item for item in data["components"][0]["functions"] if item["id"] == "b")
    function_b["role"] = "buffer"
    net(data, "OUT")["members"].remove(["interface", "2"])
    net(data, "OUT")["members"].append(["amp", "5"])
    net(data, "REF")["members"].remove(["amp", "5"])
    park = net(data, "PARK")
    park["id"] = "FINAL"
    park["members"] = [["amp", "7"], ["amp", "6"], ["interface", "2"]]
    stage_b = rel(data, "stage.b")
    stage_b.pop("unused")
    stage_b.update(input="OUT", output="FINAL", reference="REF")
    rel(data, "loop.b")["net"] = "FINAL"
    add_led(data, "FINAL", "REF", "R3")
    data["power_assertions"] = opamp_flags()
    return data


def v4_6() -> dict:
    data = identify(load("fixtures/m2e1a/ir/regulator_timer_led_corrected.json"), "regulated_timer_rc_output", "V4RegulatedTimerRcOutput")
    data["components"] = [item for item in data["components"] if item["id"] not in {"indicator_r", "indicator_led"}]
    data["relationships"] = [item for item in data["relationships"] if not item["id"].startswith("indicator.")]
    data["nets"] = [item for item in data["nets"] if item["id"] != "LEDMID"]
    net(data, "OUT")["members"] = [["timer", "3"], ["filter_r", "1"]]
    net(data, "REF")["members"] = [member for member in net(data, "REF")["members"] if member != ["indicator_led", "1"]]
    net(data, "REF")["members"].append(["filter_c", "2"])
    data["components"] += [
        component("filter_r", "R3", "Device:R", "1k"),
        component("filter_c", "C5", "Device:C", "100n"),
    ]
    data["nets"].append(
        {"id": "FILTERED", "members": [["filter_r", "2"], ["filter_c", "1"], ["output", "1"]]}
    )
    data["relationships"] += [
        relation("output.filter.series", "series", component="filter_r", input="OUT", output="FILTERED"),
        relation("output.filter.shunt", "shunt", component="filter_c", node="FILTERED", reference="REF"),
    ]
    return data


def v4_7() -> dict:
    data = identify(load("fixtures/m2e1/ir/dual_timer_led.json"), "regulated_dual_timer_system", "V4RegulatedDualTimerSystem")
    remove = {"indicator_r", "indicator_led", "indicator_r2", "indicator_led2"}
    data["components"] = [item for item in data["components"] if item["id"] not in remove]
    data["relationships"] = [item for item in data["relationships"] if "indicator" not in item["id"]]
    data["nets"] = [item for item in data["nets"] if item["id"] not in {"LEDMID", "LEDMID2"}]
    net(data, "OUT")["members"] = [["timer", "3"], ["output", "1"]]
    net(data, "OUT2")["members"] = [["timer2", "3"], ["output2", "1"]]
    net(data, "REF")["members"] = [member for member in net(data, "REF")["members"] if member[0] not in remove]
    net(data, "VCC")["members"].remove(["source", "1"])
    net(data, "VCC")["members"] += [["regulator", "3"], ["regulator_output_c", "1"]]
    net(data, "REF")["members"] += [["regulator", "2"], ["regulator_input_c", "2"], ["regulator_output_c", "2"]]
    data["components"] += [
        component("regulator", "U3", "Regulator_Linear:L7805", "L7805"),
        component("regulator_input_c", "C5", "Device:C", "330n"),
        component("regulator_output_c", "C6", "Device:C", "100n"),
    ]
    data["nets"].append(
        {"id": "VIN", "members": [["source", "1"], ["regulator", "1"], ["regulator_input_c", "1"]]}
    )
    data["relationships"] += [
        relation(
            "regulator.conversion",
            "power_stage",
            component="regulator",
            input="VIN",
            output="VCC",
            reference="REF",
            pins={"input": "1", "output": "3", "reference": "2"},
            polarity="positive",
        ),
        relation("regulator.bypass.input", "decoupling", component="regulator_input_c", consumer=["regulator", "1"], supply="VIN", return_="REF"),
        relation("regulator.bypass.output", "decoupling", component="regulator_output_c", consumer=["regulator", "3"], supply="VCC", return_="REF"),
    ]
    for item in data["relationships"]:
        if "return_" in item:
            item["return"] = item.pop("return_")
    data["power_assertions"] = [
        {"id": "flag.supply", "refdes": "#FLG01", "net": "VIN"},
        {"id": "flag.return", "refdes": "#FLG02", "net": "REF"},
    ]
    return data


def v4_8() -> dict:
    data = identify(load("fixtures/m2b/timer_astable.json"), "timer_dual_output_load", "V4TimerDualOutputLoad")
    net(data, "OUT")["members"].remove(["output", "1"])
    net(data, "OUT")["members"] += [["indicator_r", "1"], ["filter_r", "1"]]
    net(data, "REF")["members"] += [["indicator_led", "1"], ["filter_c", "2"]]
    data["components"] += [
        component("indicator_r", "R3", "Device:R", "1k"),
        component("indicator_led", "D1", "Device:LED", "LED"),
        component("filter_r", "R4", "Device:R", "1k"),
        component("filter_c", "C3", "Device:C", "100n"),
    ]
    data["nets"] += [
        {"id": "LEDMID", "members": [["indicator_r", "2"], ["indicator_led", "2"]]},
        {"id": "FILTERED", "members": [["filter_r", "2"], ["filter_c", "1"], ["output", "1"]]},
    ]
    data["relationships"] += [
        relation("indicator.series", "series", component="indicator_r", input="OUT", output="LEDMID"),
        relation("indicator.polarity", "polarity", component="indicator_led", anode="LEDMID", cathode="REF"),
        relation("output.filter.series", "series", component="filter_r", input="OUT", output="FILTERED"),
        relation("output.filter.shunt", "shunt", component="filter_c", node="FILTERED", reference="REF"),
    ]
    data["power_assertions"] = [
        {"id": "flag.supply", "refdes": "#FLG01", "net": "VCC"},
        {"id": "flag.return", "refdes": "#FLG02", "net": "REF"},
    ]
    return data


BUILDERS = [v4_1, v4_2, v4_3, v4_4, v4_5, v4_6, v4_7, v4_8]


DESCRIPTIONS = [
    ("lowpass_inverting_led", "RC low-pass into an inverting NE5532 stage with an output LED branch"),
    ("highpass_noninverting_lowpass", "RC high-pass, non-inverting NE5532 gain, then RC low-pass"),
    ("reference_noninverting_rc", "split-rail local reference feeding a non-inverting stage and RC output"),
    ("parallel_dual_opamp_functions", "one input feeding parallel buffer and gain functions in one NE5532"),
    ("sallen_key_buffer_led", "Sallen-Key unit feeding a buffer unit and final LED branch"),
    ("regulated_timer_rc_output", "external regulator feeding a timer with RC-filtered output"),
    ("regulated_dual_timer_system", "one external regulator feeding two parallel astable timers"),
    ("timer_dual_output_load", "one timer output feeding LED and RC-output branches"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not (HERE / "implementation_freeze.json").is_file():
        raise SystemExit("implementation freeze must exist before corpus authoring")
    if (HERE / "corpus.v4.json").exists() or (HERE / "ir").exists():
        raise SystemExit("refusing to overwrite an existing frozen corpus")
    ir_dir = HERE / "ir"
    ir_dir.mkdir()
    validation = {}
    ir_hashes = {}
    cases = []
    for index, (builder, (design_id, summary)) in enumerate(zip(BUILDERS, DESCRIPTIONS, strict=True), 1):
        case_id = f"V4-{index}"
        data = builder()
        if data["id"] != design_id:
            raise RuntimeError(f"builder/design mismatch for {case_id}")
        validate(data, assets())
        path = ir_dir / f"{case_id}.json"
        path.write_text(json.dumps(data, indent=2) + "\n")
        validate(json.loads(path.read_text()), assets())
        ir_hashes[case_id] = sha256(path)
        validation[case_id] = {"status": "pass", "parser_resolver_semantic_validation": "pass"}
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
        "schema_version": "corpus.v4",
        "evaluation": "M2f1 — corpus.v4 frozen blind qualification",
        "split": "held_out_blind",
        "fixed_case_count": 8,
        "required_accepted_count": 8,
        "historical_status": {
            "corpus.v1": "development/tuning evidence",
            "corpus.v2": "blind failure and known regression evidence",
            "corpus.v3": "blind failure and known regression evidence",
            "V3-8": "preserved invalid authored-power evidence",
            "M2e1a": "19/19 accepted regression/development cases over 95/95 builds",
        },
        "cases": cases,
    }
    corpus_path = HERE / "corpus.v4.json"
    corpus_path.write_text(json.dumps(corpus, indent=2) + "\n")
    (HERE / "corpus.v4.sha256").write_text(f"{sha256(corpus_path)}  corpus.v4.json\n")
    (HERE / "ir.sha256.json").write_text(json.dumps(ir_hashes, indent=2) + "\n")
    (HERE / "ir_validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    print(json.dumps({"corpus_sha256": sha256(corpus_path), "ir_sha256": ir_hashes}, indent=2))


if __name__ == "__main__":
    main()
