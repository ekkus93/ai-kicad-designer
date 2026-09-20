"""One-time M2c2 held-out IR authoring; never invoked by the build pipeline."""

import copy
import hashlib
import json
from pathlib import Path

from ai_kicad.m2b import assets, validate

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def template(name, case_id):
    data = copy.deepcopy(json.loads((ROOT / "fixtures/m2b" / f"{name}.json").read_text()))
    data["id"] = case_id
    data["name"] = "Blind" + case_id.title().replace("_", "")
    return data


def net(data, name):
    return next(item for item in data["nets"] if item["id"] == name)


def component(cid, refdes, asset, value):
    return {"id": cid, "refdes": refdes, "asset": asset, "value": value}


def relation(rid, kind, **kwargs):
    return {"id": rid, "kind": kind, **kwargs}


def add_led_load(data, supply, ret, resistor_ref):
    data["components"] += [
        component("load_r", resistor_ref, "Device:R", "1k"),
        component("load_led", "D1", "Device:LED", "LED"),
    ]
    net(data, supply)["members"].append(["load_r", "1"])
    data["nets"].append({"id": "LEDMID", "members": [["load_r", "2"], ["load_led", "2"]]})
    net(data, ret)["members"].append(["load_led", "1"])
    data["relationships"] += [
        relation("load.series", "series", component="load_r", input=supply, output="LEDMID"),
        relation("load.polarity", "polarity", component="load_led", anode="LEDMID", cathode=ret),
    ]


cases = {}

h = template("rc_lowpass", "rc_lowpass_led_indicator")
add_led_load(h, "OUT", "REF", "R2")
cases["H1"] = h

h = template("noninverting_gain", "rc_highpass_noninverting")
net(h, "IN")["members"].remove(["amp", "3"])
net(h, "IN")["members"].append(["filter_c", "1"])
net(h, "REF")["members"].append(["filter_r", "2"])
h["nets"].append({"id": "FILTER", "members": [["filter_c", "2"], ["filter_r", "1"], ["amp", "3"]]})
h["components"] += [
    component("filter_c", "C3", "Device:C", "10n"),
    component("filter_r", "R3", "Device:R", "10k"),
]
next(r for r in h["relationships"] if r["id"] == "stage.a")["input"] = "FILTER"
h["relationships"] += [
    relation("highpass.series", "series", component="filter_c", input="IN", output="FILTER"),
    relation("highpass.shunt", "shunt", component="filter_r", node="FILTER", reference="REF"),
]
cases["H2"] = h

h = template("dual_rail_reference", "dual_rail_reference_buffer")
net(h, "IN")["members"] = []
h["nets"] = [n for n in h["nets"] if n["id"] != "IN"]
net(h, "VREF")["members"] += [["interface", "1"], ["amp", "3"]]
next(r for r in h["relationships"] if r["id"] == "stage.a")["input"] = "VREF"
cases["H3"] = h

h = template("dual_buffer", "dual_active_opamp_chain")
net(h, "OUT")["members"] = [["amp", "1"], ["amp", "2"], ["amp", "5"]]
net(h, "REF")["members"].remove(["amp", "5"])
net(h, "PARK")["id"] = "CHAIN_OUT"
net(h, "CHAIN_OUT")["members"].append(["interface", "2"])
next(r for r in h["relationships"] if r["id"] == "stage.a")["output"] = "OUT"
stage_b = next(r for r in h["relationships"] if r["id"] == "stage.b")
stage_b.pop("unused")
stage_b.update(input="OUT", output="CHAIN_OUT", reference="REF")
next(r for r in h["relationships"] if r["id"] == "loop.b")["net"] = "CHAIN_OUT"
next(f for f in h["components"][0]["functions"] if f["id"] == "b")["role"] = "buffer"
cases["H4"] = h

h = template("sallen_key", "sallen_key_output_rc")
net(h, "OUT")["members"].remove(["interface", "2"])
net(h, "OUT")["members"].append(["output_r", "1"])
net(h, "REF")["members"].append(["output_c", "2"])
h["nets"].append(
    {"id": "POST", "members": [["output_r", "2"], ["output_c", "1"], ["interface", "2"]]}
)
h["components"] += [
    component("output_r", "R3", "Device:R", "4k7"),
    component("output_c", "C5", "Device:C", "10n"),
]
h["relationships"] += [
    relation("output.series", "series", component="output_r", input="OUT", output="POST"),
    relation("output.shunt", "shunt", component="output_c", node="POST", reference="REF"),
]
cases["H5"] = h

h = template("linear_regulator", "regulated_led_load")
add_led_load(h, "VOUT", "REF", "R1")
cases["H6"] = h

h = template("timer_astable", "timer_led_output")
add_led_load(h, "OUT", "REF", "R3")
cases["H7"] = h

h = template("inverting_gain", "rc_inverting_amplifier")
net(h, "IN")["members"].remove(["rin", "1"])
net(h, "IN")["members"].append(["filter_c", "1"])
net(h, "REF")["members"].append(["filter_r", "2"])
h["nets"].append({"id": "COUPLED", "members": [["filter_c", "2"], ["filter_r", "1"], ["rin", "1"]]})
h["components"] += [
    component("filter_c", "C3", "Device:C", "10n"),
    component("filter_r", "R3", "Device:R", "100k"),
]
next(r for r in h["relationships"] if r["id"] == "input_resistor")["input"] = "COUPLED"
next(r for r in h["relationships"] if r["id"] == "stage.a")["input"] = "COUPLED"
h["relationships"] += [
    relation("input.highpass.series", "series", component="filter_c", input="IN", output="COUPLED"),
    relation(
        "input.highpass.shunt", "shunt", component="filter_r", node="COUPLED", reference="REF"
    ),
]
cases["H8"] = h

manifest = {
    "schema_version": "m2blind.corpus.v2",
    "evaluation": "M2c2 — frozen blind M2 qualification",
    "freeze_commit": "07efd669000bc1ab17f6d291660951e0d9012de9",
    "required_accepted_count": 8,
    "cases": [
        {
            "review_order_key": key,
            "id": data["id"],
            "ir": f"ir/{key}.json",
            "split": "held_out",
            "requested_design": data["id"],
            "valid_request": True,
        }
        for key, data in cases.items()
    ],
}

resolved = assets()
(OUT / "ir").mkdir(exist_ok=True)
ir_hashes = {}
for key, data in cases.items():
    validate(data, resolved)
    path = OUT / "ir" / f"{key}.json"
    path.write_text(json.dumps(data, indent=2) + "\n")
    ir_hashes[key] = hashlib.sha256(path.read_bytes()).hexdigest()
(OUT / "ir.sha256.json").write_text(json.dumps(ir_hashes, indent=2) + "\n")
path = OUT / "corpus.v2.json"
path.write_text(json.dumps(manifest, indent=2) + "\n")
(OUT / "corpus.v2.sha256").write_text(
    f"{hashlib.sha256(path.read_bytes()).hexdigest()}  corpus.v2.json\n"
)
print("IR validated and frozen:", ir_hashes)
print("corpus:", hashlib.sha256(path.read_bytes()).hexdigest())
