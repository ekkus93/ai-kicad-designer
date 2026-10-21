"""Freeze package/reference and long-field interaction cases before layout."""

from __future__ import annotations

import copy
import json

from make_m2h2_i2 import case as reference_without_package
from make_m2h2_i4 import case as branch_case
from make_m2h2_i5 import case as support_case
from make_m2h2_probes import Circuit, amplifier

from ai_kicad.m2a import ROOT


def _expected(design: dict, paths: list[dict], cell: str) -> dict:
    return {
        "schema_version": "m2h2.interaction-expected.1",
        "frozen_before_real_layout": True,
        "factor_cell": cell,
        "partitions": {net["id"]: sorted(net["members"]) for net in design["nets"]},
        "terminal_inventory": sorted(member for net in design["nets"] for member in net["members"]),
        "path_obligations": paths,
        "precedence": [],
    }


def package_reference(packages: int, reference: str) -> tuple[dict, dict]:
    assert packages in (0, 1, 2)
    assert reference in ("external", "internal", "distinct")
    cell = f"I6:shared_packages={packages if packages < 2 else '2+'}|reference={reference}"
    if packages == 0:
        design, prior = reference_without_package(reference, 2)
        design = copy.deepcopy(design)
        design["id"] = f"m2h2_i6_pkg0_{reference}"
        design["name"] = f"M2h2I6Pkg0{reference.title()}"
        prior = copy.deepcopy(prior)
        prior["factor_cell"] = cell
        return design, prior
    circuit = Circuit(
        f"m2h2_i6_pkg{packages}_{reference}", f"M2h2I6Pkg{packages}{reference.title()}"
    )
    circuit.part("positive", "J1", "Connector_Generic:Conn_01x01", "Positive rail")
    circuit.part("negative", "J2", "Connector_Generic:Conn_01x01", "Negative rail")
    circuit.net("VPLUS", ("positive", "1"))
    circuit.net("VMINUS", ("negative", "1"))
    circuit.assertion("VPLUS", 1)
    circuit.assertion("VMINUS", 2)
    next_connector = 3
    domains = ("BIAS_A", "BIAS_B") if reference == "distinct" else ("BIAS",)
    for domain_index, domain in enumerate(domains):
        if reference == "external":
            circuit.part(
                f"bias_{domain_index}",
                f"J{next_connector}",
                "Connector_Generic:Conn_01x01",
                "Reference input",
            )
            circuit.net(domain, (f"bias_{domain_index}", "1"))
            next_connector += 1
        else:
            upper = f"divider_{domain_index}_upper"
            lower = f"divider_{domain_index}_lower"
            circuit.part(upper, f"R{2 * domain_index + 1}", "Device:R", "10k")
            circuit.part(lower, f"R{2 * domain_index + 2}", "Device:R", "10k")
            circuit.add("VPLUS", (upper, "1"))
            circuit.add("VMINUS", (lower, "2"))
            circuit.net(domain, (upper, "2"), (lower, "1"))
            circuit.relation(
                f"divider_{domain_index}",
                "reference_divider",
                upper=upper,
                lower=lower,
                positive="VPLUS",
                local=domain,
                negative="VMINUS",
            )
    for index in range(packages):
        stem = f"stage_{index + 1}"
        input_net, output_net = f"INPUT_{index + 1}", f"OUTPUT_{index + 1}"
        circuit.part(
            f"input_{index + 1}",
            f"J{next_connector}",
            "Connector_Generic:Conn_01x01",
            "Input channel",
        )
        circuit.net(input_net, (f"input_{index + 1}", "1"))
        next_connector += 1
        circuit.part(
            f"output_{index + 1}",
            f"J{next_connector}",
            "Connector_Generic:Conn_01x01",
            "Output channel",
        )
        circuit.net(output_net, (f"output_{index + 1}", "1"))
        next_connector += 1
        amplifier(
            circuit,
            stem,
            f"U{index + 1}",
            active="buffer",
            input_net=input_net,
            output_net=output_net,
            positive="VPLUS",
            negative="VMINUS",
            reference=domains[index % len(domains)],
            capacitor_first=2 * index + 1,
        )
    design, paths = circuit.finish()
    return design, _expected(design, paths, cell)


def text_support(text: str, support: str) -> tuple[dict, dict]:
    design, expected = support_case(3 if support == "3+" else 1, support)
    design, expected = copy.deepcopy(design), copy.deepcopy(expected)
    design["id"] = f"m2h2_i6_text_{text}_support_{support.replace('-', '_').replace('+', 'plus')}"
    design["name"] = (
        f"M2h2I6Text{text.title()}Support{support.replace('-', '').replace('+', 'Plus')}"
    )
    if text == "long":
        for component in design["components"]:
            if component["asset"] == "Device:R":
                component["value"] = "R12345678901234567890123"
                break
        for component in design["components"]:
            if component["asset"].startswith("Connector_Generic:"):
                component["value"] = "RequiredLabel1234567"
                break
    expected["factor_cell"] = f"I6:text_stress={text}|support_count={support}"
    return design, expected


def text_branch(text: str, branch: int) -> tuple[dict, dict]:
    design, expected = branch_case(branch, "mixed")
    design, expected = copy.deepcopy(design), copy.deepcopy(expected)
    design["id"] = f"m2h2_i6_text_{text}_branch_{branch}"
    design["name"] = f"M2h2I6Text{text.title()}Branch{branch}"
    if text == "long":
        next(component for component in design["components"] if component["asset"] == "Device:R")[
            "value"
        ] = "R12345678901234567890123"
        next(
            component
            for component in design["components"]
            if component["asset"].startswith("Connector_Generic:")
        )["value"] = "RequiredLabel1234567"
    expected["factor_cell"] = (
        f"I6:text_stress={text}|branch_degree={branch if branch < 3 else '3+'}"
    )
    return design, expected


def main() -> None:
    root = ROOT / "fixtures/m2h2/interaction/i6"
    root.mkdir(parents=True, exist_ok=True)
    cases = [
        (f"pkg{count}_{reference}", package_reference(count, reference))
        for count in (0, 1, 2)
        for reference in ("external", "internal", "distinct")
    ]
    cases += [
        (
            f"text_{text}_support_{support.replace('-', '_').replace('+', 'plus')}",
            text_support(text, support),
        )
        for text in ("nominal", "long")
        for support in ("0", "1-2", "3+")
    ]
    cases += [
        (f"text_{text}_branch_{branch}", text_branch(text, branch))
        for text in ("nominal", "long")
        for branch in (1, 2, 3)
    ]
    for stem, (design, expected) in cases:
        for suffix, value in (("json", design), ("expected.json", expected)):
            path = root / f"{stem}.{suffix}"
            if path.exists():
                raise SystemExit(f"refusing to overwrite {path}")
            path.write_text(json.dumps(value, indent=2) + "\n")


if __name__ == "__main__":
    main()
