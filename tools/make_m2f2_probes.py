"""Author the two M2f2 typed-packing development probes deterministically."""

from __future__ import annotations

import copy
import json

from ai_kicad.m2a import ROOT


OUTPUT = ROOT / "fixtures/m2f2/ir"


def _write(name: str, design: dict) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / name).write_text(json.dumps(design, indent=2) + "\n")


def _three_consumers() -> dict:
    source = ROOT / "fixtures/m2e1/ir/regulator_parallel_rc.json"
    design = copy.deepcopy(json.loads(source.read_text()))
    design.update(
        id="m2f2_regulator_three_consumers",
        name="M2f2RegulatorThreeConsumers",
    )
    design["components"].extend(
        [
            {
                "id": "filter3_r",
                "refdes": "R5",
                "asset": "Device:R",
                "value": "47",
            },
            {
                "id": "load3",
                "refdes": "J5",
                "asset": "Connector_Generic:Conn_01x01",
                "value": "Output 3",
            },
        ]
    )
    next(net for net in design["nets"] if net["id"] == "VOUT")["members"].append(["filter3_r", "1"])
    design["nets"].append(
        {
            "id": "FILTERED3",
            "members": [["filter3_r", "2"], ["load3", "1"]],
        }
    )
    design["relationships"].append(
        {
            "id": "filter3.series",
            "kind": "series",
            "component": "filter3_r",
            "input": "VOUT",
            "output": "FILTERED3",
        }
    )
    return design


def _rename(value, component_map: dict[str, str], net_map: dict[str, str]):
    if isinstance(value, str):
        return component_map.get(value, net_map.get(value, value))
    if isinstance(value, list):
        return [_rename(item, component_map, net_map) for item in value]
    if isinstance(value, dict):
        return {key: _rename(item, component_map, net_map) for key, item in value.items()}
    return value


def _chain_copy(base: dict, prefix: str, ordinal: int) -> dict:
    result = copy.deepcopy(base)
    component_map = {item["id"]: f"{prefix}_{item['id']}" for item in result["components"]}
    shared = {"VPLUS", "VMINUS", "REF"}
    net_map = {
        item["id"]: item["id"] if item["id"] in shared else f"{prefix.upper()}_{item['id']}"
        for item in result["nets"]
    }
    counters = {"U": ordinal, "J": ordinal}
    passive_offset = (ordinal - 1) * 4
    for component in result["components"]:
        old_id = component["id"]
        component["id"] = component_map[old_id]
        refdes = component["refdes"]
        prefix_text = refdes.rstrip("0123456789")
        number = int(refdes[len(prefix_text) :])
        if prefix_text in counters:
            component["refdes"] = f"{prefix_text}{counters[prefix_text]}"
        else:
            component["refdes"] = f"{prefix_text}{number + passive_offset}"
    for net in result["nets"]:
        net["id"] = net_map[net["id"]]
        net["members"] = [[component_map[item], pin] for item, pin in net["members"]]
    result["relationships"] = [
        _rename(item, component_map, net_map) for item in result["relationships"]
    ]
    for relation in result["relationships"]:
        relation["id"] = f"{prefix}.{relation['id']}"
    return result


def _two_chains() -> dict:
    source = ROOT / "fixtures/m2blind_v3/ir/V3-4.json"
    base = json.loads(source.read_text())
    first = _chain_copy(base, "a", 1)
    second = _chain_copy(base, "b", 2)
    nets: dict[str, dict] = {}
    for net in [*first["nets"], *second["nets"]]:
        if net["id"] in nets:
            nets[net["id"]]["members"].extend(net["members"])
        else:
            nets[net["id"]] = copy.deepcopy(net)
    nets["VPLUS"]["members"].extend([["regulator", "3"], ["regulator_output_c", "1"]])
    nets["REF"]["members"].extend(
        [
            ["regulator", "2"],
            ["regulator_input_c", "2"],
            ["regulator_output_c", "2"],
        ]
    )
    nets["VIN"] = {
        "id": "VIN",
        "members": [
            ["source", "1"],
            ["regulator", "1"],
            ["regulator_input_c", "1"],
        ],
    }
    components = [*first["components"], *second["components"]]
    components.extend(
        [
            {
                "id": "regulator",
                "refdes": "U3",
                "asset": "Regulator_Linear:L7805",
                "value": "L7805",
            },
            {
                "id": "regulator_input_c",
                "refdes": "C9",
                "asset": "Device:C",
                "value": "330n",
            },
            {
                "id": "regulator_output_c",
                "refdes": "C10",
                "asset": "Device:C",
                "value": "100n",
            },
            {
                "id": "source",
                "refdes": "J3",
                "asset": "Connector_Generic:Conn_01x01",
                "value": "Positive supply input",
            },
        ]
    )
    relationships = [*first["relationships"], *second["relationships"]]
    relationships.extend(
        [
            {
                "id": "regulator.conversion",
                "kind": "power_stage",
                "component": "regulator",
                "input": "VIN",
                "output": "VPLUS",
                "reference": "REF",
                "pins": {"input": "1", "output": "3", "reference": "2"},
                "polarity": "positive",
            },
            {
                "id": "regulator.bypass.input",
                "kind": "decoupling",
                "component": "regulator_input_c",
                "consumer": ["regulator", "1"],
                "supply": "VIN",
                "return": "REF",
            },
            {
                "id": "regulator.bypass.output",
                "kind": "decoupling",
                "component": "regulator_output_c",
                "consumer": ["regulator", "3"],
                "supply": "VPLUS",
                "return": "REF",
            },
        ]
    )
    return {
        "profile": "m2b.1",
        "id": "m2f2_two_signal_chains_shared_rail",
        "name": "M2f2TwoSignalChainsSharedRail",
        "components": components,
        "nets": list(nets.values()),
        "relationships": relationships,
        "no_connects": [],
        "power_assertions": [
            {"id": "flag.input", "refdes": "#FLG01", "net": "VIN"},
            {"id": "flag.negative", "refdes": "#FLG02", "net": "VMINUS"},
            {"id": "flag.return", "refdes": "#FLG03", "net": "REF"},
        ],
    }


def main() -> None:
    _write("regulator_three_consumers.json", _three_consumers())
    _write("two_signal_chains_shared_rail.json", _two_chains())


if __name__ == "__main__":
    main()
