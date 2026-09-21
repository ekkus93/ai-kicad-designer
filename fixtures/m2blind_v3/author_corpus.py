"""One-time corpus.v3 IR authoring and schema/topology validation.

This script performs no layout or generation.  It derives new compositions
from already-qualified M2b assets and relationship vocabulary, validates them
through the frozen parser/resolver, then writes and hashes the eight IRs.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from ai_kicad.m2b import assets, validate


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def template(stem: str, design_id: str, name: str) -> dict:
    data = copy.deepcopy(json.loads((ROOT / "fixtures/m2b" / f"{stem}.json").read_text()))
    data["id"] = design_id
    data["name"] = name
    return data


def component(cid: str, refdes: str, asset: str, value: str) -> dict:
    return {"id": cid, "refdes": refdes, "asset": asset, "value": value}


def relation(rid: str, kind: str, **fields: object) -> dict:
    return {"id": rid, "kind": kind, **fields}


def net(data: dict, net_id: str) -> dict:
    return next(item for item in data["nets"] if item["id"] == net_id)


def relationship(data: dict, relationship_id: str) -> dict:
    return next(item for item in data["relationships"] if item["id"] == relationship_id)


def add_led_branch(data: dict, source: str, reference: str, resistor_ref: str) -> None:
    data["components"] += [
        component("indicator_r", resistor_ref, "Device:R", "1k"),
        component("indicator_led", "D1", "Device:LED", "LED"),
    ]
    net(data, source)["members"].append(["indicator_r", "1"])
    data["nets"].append(
        {
            "id": "LEDMID",
            "members": [["indicator_r", "2"], ["indicator_led", "2"]],
        }
    )
    net(data, reference)["members"].append(["indicator_led", "1"])
    data["relationships"] += [
        relation(
            "indicator.series",
            "series",
            component="indicator_r",
            input=source,
            output="LEDMID",
        ),
        relation(
            "indicator.polarity",
            "polarity",
            component="indicator_led",
            anode="LEDMID",
            cathode=reference,
        ),
    ]


def v3_1() -> dict:
    data = template(
        "noninverting_gain",
        "rc_lowpass_noninverting_led",
        "V3RcLowpassNoninvertingLed",
    )
    net(data, "IN")["members"].remove(["amp", "3"])
    net(data, "IN")["members"].append(["input_r", "1"])
    net(data, "REF")["members"].append(["input_c", "2"])
    data["nets"].append(
        {
            "id": "FILTERED",
            "members": [["input_r", "2"], ["input_c", "1"], ["amp", "3"]],
        }
    )
    data["components"] += [
        component("input_r", "R3", "Device:R", "10k"),
        component("input_c", "C3", "Device:C", "10n"),
    ]
    relationship(data, "stage.a")["input"] = "FILTERED"
    data["relationships"] += [
        relation(
            "input.lowpass.series",
            "series",
            component="input_r",
            input="IN",
            output="FILTERED",
        ),
        relation(
            "input.lowpass.shunt",
            "shunt",
            component="input_c",
            node="FILTERED",
            reference="REF",
        ),
    ]
    add_led_branch(data, "OUT", "REF", "R4")
    return data


def v3_2() -> dict:
    data = template("linear_regulator", "regulator_rc_led_chain", "V3RegulatorRcLedChain")
    net(data, "VOUT")["members"].remove(["load", "1"])
    net(data, "VOUT")["members"].append(["filter_r", "1"])
    net(data, "REF")["members"].append(["filter_c", "2"])
    data["nets"].append(
        {
            "id": "FILTERED",
            "members": [["filter_r", "2"], ["filter_c", "1"], ["load", "1"]],
        }
    )
    data["components"] += [
        component("filter_r", "R1", "Device:R", "100"),
        component("filter_c", "C3", "Device:C", "10u"),
    ]
    data["relationships"] += [
        relation(
            "output.filter.series",
            "series",
            component="filter_r",
            input="VOUT",
            output="FILTERED",
        ),
        relation(
            "output.filter.shunt",
            "shunt",
            component="filter_c",
            node="FILTERED",
            reference="REF",
        ),
    ]
    add_led_branch(data, "VOUT", "REF", "R2")
    return data


def v3_3() -> dict:
    data = template("timer_astable", "timer_rc_output_filter", "V3TimerRcOutputFilter")
    net(data, "OUT")["members"].remove(["output", "1"])
    net(data, "OUT")["members"].append(["filter_r", "1"])
    net(data, "REF")["members"].append(["filter_c", "2"])
    data["nets"].append(
        {
            "id": "FILTERED",
            "members": [["filter_r", "2"], ["filter_c", "1"], ["output", "1"]],
        }
    )
    data["components"] += [
        component("filter_r", "R3", "Device:R", "1k"),
        component("filter_c", "C3", "Device:C", "100n"),
    ]
    data["relationships"] += [
        relation(
            "output.filter.series",
            "series",
            component="filter_r",
            input="OUT",
            output="FILTERED",
        ),
        relation(
            "output.filter.shunt",
            "shunt",
            component="filter_c",
            node="FILTERED",
            reference="REF",
        ),
    ]
    return data


def v3_4() -> dict:
    data = template("noninverting_gain", "mixed_dual_opamp_chain", "V3MixedDualOpampChain")
    function_b = next(item for item in data["components"][0]["functions"] if item["id"] == "b")
    function_b["role"] = "amplifier"
    net(data, "REF")["members"].remove(["amp", "5"])
    net(data, "REF")["members"].append(["amp", "5"])
    net(data, "OUT")["members"].remove(["interface", "2"])
    net(data, "OUT")["members"].append(["stage_b_input", "1"])
    park = net(data, "PARK")
    park["id"] = "FINAL"
    park["members"] = [["amp", "7"], ["stage_b_feedback", "2"], ["interface", "2"]]
    data["nets"].append(
        {
            "id": "SUM_B",
            "members": [
                ["amp", "6"],
                ["stage_b_input", "2"],
                ["stage_b_feedback", "1"],
            ],
        }
    )
    data["components"] += [
        component("stage_b_input", "R3", "Device:R", "10k"),
        component("stage_b_feedback", "R4", "Device:R", "47k"),
    ]
    stage_b = relationship(data, "stage.b")
    stage_b.pop("unused")
    stage_b.update(input="OUT", output="FINAL", reference="REF")
    loop_b = relationship(data, "loop.b")
    loop_b["net"] = "FINAL"
    loop_b["resistor"] = "stage_b_feedback"
    data["relationships"].append(
        relation(
            "stage_b.input_resistor",
            "series",
            component="stage_b_input",
            input="OUT",
            output="SUM_B",
        )
    )
    return data


def v3_5() -> dict:
    data = template("sallen_key", "sallen_key_led_indicator", "V3SallenKeyLedIndicator")
    add_led_branch(data, "OUT", "REF", "R3")
    return data


def v3_6() -> dict:
    data = template(
        "dual_rail_reference",
        "dual_rail_reference_inverting_stage",
        "V3DualRailReferenceInvertingStage",
    )
    net(data, "IN")["members"].remove(["amp", "3"])
    net(data, "IN")["members"].append(["input_r", "1"])
    net(data, "VREF")["members"].append(["amp", "3"])
    net(data, "OUT")["members"].remove(["amp", "2"])
    net(data, "OUT")["members"].append(["feedback_r", "2"])
    data["nets"].append(
        {
            "id": "SUM",
            "members": [["amp", "2"], ["input_r", "2"], ["feedback_r", "1"]],
        }
    )
    data["components"] += [
        component("input_r", "R3", "Device:R", "10k"),
        component("feedback_r", "R4", "Device:R", "100k"),
    ]
    relationship(data, "loop.a")["resistor"] = "feedback_r"
    data["relationships"].append(
        relation(
            "input.resistor",
            "series",
            component="input_r",
            input="IN",
            output="SUM",
        )
    )
    return data


def v3_7() -> dict:
    data = template("sallen_key", "rc_highpass_to_sallen_key", "V3RcHighpassToSallenKey")
    net(data, "IN")["members"].remove(["upstream_r", "1"])
    net(data, "IN")["members"].append(["input_c", "1"])
    net(data, "REF")["members"].append(["input_r", "2"])
    data["nets"].append(
        {
            "id": "COUPLED",
            "members": [["input_c", "2"], ["input_r", "1"], ["upstream_r", "1"]],
        }
    )
    data["components"] += [
        component("input_c", "C5", "Device:C", "100n"),
        component("input_r", "R3", "Device:R", "100k"),
    ]
    relationship(data, "upstream.series")["input"] = "COUPLED"
    data["relationships"] += [
        relation(
            "input.highpass.series",
            "series",
            component="input_c",
            input="IN",
            output="COUPLED",
        ),
        relation(
            "input.highpass.shunt",
            "shunt",
            component="input_r",
            node="COUPLED",
            reference="REF",
        ),
    ]
    return data


def v3_8() -> dict:
    data = template("timer_astable", "regulator_timer_led_system", "V3RegulatorTimerLedSystem")
    next(item for item in data["components"] if item["id"] == "timer")["refdes"] = "U2"
    net(data, "VCC")["members"].remove(["source", "1"])
    net(data, "VCC")["members"] += [["regulator", "3"], ["regulator_output_c", "1"]]
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
    data["components"] += [
        component("regulator", "U1", "Regulator_Linear:L7805", "L7805"),
        component("regulator_input_c", "C3", "Device:C", "330n"),
        component("regulator_output_c", "C4", "Device:C", "100n"),
    ]
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
            supply="VCC",
            **{"return": "REF"},
        ),
    ]
    add_led_branch(data, "OUT", "REF", "R3")
    return data


CASES = {
    "V3-1": ("rc_lowpass_noninverting_led", v3_1),
    "V3-2": ("regulator_rc_led_chain", v3_2),
    "V3-3": ("timer_rc_output_filter", v3_3),
    "V3-4": ("mixed_dual_opamp_chain", v3_4),
    "V3-5": ("sallen_key_led_indicator", v3_5),
    "V3-6": ("dual_rail_reference_inverting_stage", v3_6),
    "V3-7": ("rc_highpass_to_sallen_key", v3_7),
    "V3-8": ("regulator_timer_led_system", v3_8),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not (HERE / "implementation_freeze.json").exists():
        raise SystemExit("implementation freeze must exist before corpus authoring")
    if (HERE / "runs").exists():
        raise SystemExit("refusing to author after execution has started")

    resolved = assets()
    authored = {key: maker() for key, (_, maker) in CASES.items()}
    for key, data in authored.items():
        validate(data, resolved)
        if data["id"] != CASES[key][0]:
            raise AssertionError(f"{key}: design ID mismatch")

    ir_dir = HERE / "ir"
    ir_dir.mkdir(exist_ok=False)
    hashes = {}
    for key, data in authored.items():
        path = ir_dir / f"{key}.json"
        path.write_text(json.dumps(data, indent=2) + "\n")
        hashes[key] = digest(path)
    (HERE / "ir.sha256.json").write_text(json.dumps(hashes, indent=2) + "\n")

    freeze = json.loads((HERE / "implementation_freeze.json").read_text())
    corpus = {
        "schema_version": "m2d2.corpus.v3",
        "evaluation": "M2d2 — corpus.v3 frozen blind composition qualification",
        "freeze_commit": freeze["git_head"],
        "required_accepted_count": 8,
        "cases": [
            {
                "case_id": key,
                "id": design_id,
                "ir": f"ir/{key}.json",
                "split": "held_out",
                "requested_design": design_id,
                "valid_request": True,
            }
            for key, (design_id, _) in CASES.items()
        ],
    }
    corpus_path = HERE / "corpus.v3.json"
    corpus_path.write_text(json.dumps(corpus, indent=2) + "\n")
    (HERE / "corpus.v3.sha256").write_text(f"{digest(corpus_path)}  corpus.v3.json\n")
    print("IR schema/topology validation passed for all eight cases")
    print(json.dumps(hashes, indent=2))
    print("corpus", digest(corpus_path))


if __name__ == "__main__":
    main()
