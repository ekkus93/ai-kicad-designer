"""Qualify frozen interaction circuits with emitted KiCad evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_kicad.m2a import ROOT, observe
from run_m2g2_qualification import _build, _erc_violations, _json, _signature


def observed_structural_class(signature: dict) -> dict:
    """Return the actual structural class selected by composition evidence.

    This intentionally derives the class from the emitted run's composition
    evidence, not from the requested interaction factor-cell label.
    """
    composition = signature.get("composition", {})
    selection = composition.get("candidate_selection", {})
    selected_seed = selection.get("selected_seed")
    selected_round = selection.get("selected_round")
    seeds = {
        item.get("seed"): item for item in composition.get("structural_search", {}).get("seeds", [])
    }
    seed = seeds.get(selected_seed, {})
    proved = next(
        (
            item
            for item in selection.get("proved_candidates", [])
            if item.get("seed") == selected_seed and item.get("round") == selected_round
        ),
        {},
    )
    return {
        "source": "composition.candidate_selection",
        "selected_seed": selected_seed,
        "selected_round": selected_round,
        "placement_class": seed.get("placement_class"),
        "structure": proved.get("structure") or seed.get("structure") or [],
    }


def verify(run: Path, design: dict, expected: dict) -> dict:
    signature = _signature(run)
    schematic = next((run / "project").glob("*.kicad_sch"))
    observed = observe(schematic, run / "reports/netlist.xml")
    physical_components = {part["id"] for part in design["components"]}
    reference = {part["id"]: part["refdes"] for part in design["components"]}
    reference.update(
        (assertion["id"], assertion["refdes"]) for assertion in design["power_assertions"]
    )
    expected_partitions = sorted(
        sorted(
            (reference[component], pin)
            for component, pin in members
            if component in physical_components
        )
        for members in expected["partitions"].values()
    )
    actual_partitions = sorted(
        sorted((ref, pin) for ref, pin in members) for members in observed["nets"].values()
    )
    expected_terminals = sorted(
        tuple(item) for item in expected["terminal_inventory"] if item[0] in physical_components
    )
    actual_terminals = sorted(
        (component, pin)
        for members in observed["nets"].values()
        for ref, pin in members
        for component, component_ref in reference.items()
        if component_ref == ref
    )
    path_results = []
    for obligation in expected["path_obligations"]:
        first = observed["pin_positions"][(reference[obligation["from"][0]], obligation["from"][1])]
        second = observed["pin_positions"][(reference[obligation["to"][0]], obligation["to"][1])]
        span = abs(first[0] - second[0]) + abs(first[1] - second[1])
        limit = obligation["maximum_span_nm"]
        path_results.append(
            {
                "id": obligation["id"],
                "span_nm": span,
                "limit_nm": limit,
                "pass": limit is None or span <= limit,
            }
        )
    order_results = []
    for relation in expected["precedence"]:
        first = observed["pin_positions"][(reference[relation["source"][0]], relation["source"][1])]
        second = observed["pin_positions"][
            (reference[relation["target"][0]], relation["target"][1])
        ]
        order_results.append(
            {
                "source": relation["source"],
                "target": relation["target"],
                "source_x_nm": first[0],
                "target_x_nm": second[0],
                "pass": first[0] < second[0],
            }
        )
    generated_nets = {
        relation["local"]
        for relation in design["relationships"]
        if relation["kind"] == "reference_divider"
    }
    net_witnesses = {
        item["net"]: item
        for item in signature["composition"]["obligation_certificate"]["net_graph_witnesses"]
    }
    connector_ids = {
        component["id"]
        for component in design["components"]
        if component["asset"].startswith("Connector_Generic:")
    }
    generated_reference_proof = {
        net: {
            "no_external_connector": not any(
                member[0] in connector_ids
                for item in design["nets"]
                if item["id"] == net
                for member in item["members"]
            ),
            "component_count": net_witnesses.get(net, {}).get("component_count"),
        }
        for net in sorted(generated_nets)
    }
    passed = (
        signature["electrical"]["status"] == "pass"
        and not signature["electrical"]["diagnostics"]
        and _erc_violations(signature["erc"]) == 0
        and signature["composition"]["obligation_certificate"]["serialized_scene_verified"]
        == "pass"
        and actual_partitions == expected_partitions
        and actual_terminals == expected_terminals
        and all(item["pass"] for item in path_results + order_results)
        and all(
            proof["no_external_connector"] and proof["component_count"] == 1
            for proof in generated_reference_proof.values()
        )
        and all(
            (assertion["refdes"], 1) in observed["occurrences"]
            for assertion in design["power_assertions"]
        )
    )
    return {
        "pass": passed,
        "signature": signature,
        "observed_structural_class": observed_structural_class(signature),
        "partition_match": actual_partitions == expected_partitions,
        "terminal_match": actual_terminals == expected_terminals,
        "paths": path_results,
        "precedence": order_results,
        "generated_reference_proof": generated_reference_proof,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--group", choices=("i1", "i2", "i3", "i4", "i5", "i6"), required=True)
    parser.add_argument("--only", type=str)
    args = parser.parse_args()
    output = args.out.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for design_path in sorted((ROOT / "fixtures/m2h2/interaction" / args.group).glob("*.json")):
        if design_path.name.endswith(".expected.json"):
            continue
        if args.group == "i1" and design_path.stem == "selected_triple":
            continue  # preserved ERC-negative input without power assertions
        if args.only and design_path.stem != args.only:
            continue
        expected_path = design_path.with_suffix(".expected.json")
        design, expected = _json(design_path), _json(expected_path)
        runs = []
        for index in range(1, 6):
            destination = output / design_path.stem / f"run{index}"
            rc = _build(design_path, destination)
            actual = destination if rc == 0 else destination.with_name(destination.name + ".failed")
            record = {
                "run": index,
                "returncode": rc,
                "path": str(actual.relative_to(ROOT)),
            }
            if rc == 0:
                record.update(verify(actual, design, expected))
            else:
                record["failure"] = _json(actual / "reports/failure.json")
            runs.append(record)
            print(
                json.dumps(
                    {"case": design_path.stem, "run": index, "pass": record.get("pass", False)}
                ),
                flush=True,
            )
        reproducible = len(runs) == 5 and all(
            run.get("signature") == runs[0].get("signature") for run in runs[1:]
        )
        observed_structures = [
            run.get("observed_structural_class")
            for run in runs
            if run.get("observed_structural_class") is not None
        ]
        observed_structure_stable = len(observed_structures) == 5 and all(
            item == observed_structures[0] for item in observed_structures[1:]
        )
        results.append(
            {
                "id": design_path.stem,
                "cell": expected.get("factor_cell"),
                "selected_triple": expected.get("selected_triple"),
                "observed_structural_class": (
                    observed_structures[0] if observed_structure_stable else None
                ),
                "observed_structural_class_stable": observed_structure_stable,
                "accepted": all(run.get("pass", False) for run in runs) and reproducible,
                "reproducible": reproducible,
                "runs": runs,
            }
        )
        (output / "progress.json").write_text(json.dumps(results, indent=2) + "\n")
    (output / "results.json").write_text(
        json.dumps(
            {
                "schema_version": "m2h2.interaction-qualification.1",
                "group": args.group,
                "accepted": sum(item["accepted"] for item in results),
                "total": len(results),
                "results": results,
            },
            indent=2,
        )
        + "\n"
    )
    if not all(item["accepted"] for item in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
