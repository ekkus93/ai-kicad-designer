"""Qualify frozen interaction circuits with emitted KiCad evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess

from ai_kicad.m2a import ROOT, observe
from ai_kicad.m2b import assets, validate
from ai_kicad.m2_composition_qualification_observation import (
    observe_composition_evidence,
    observe_native_pin_composition,
)
from ai_kicad.m2_semantics import semantic_plan
from run_m2g2_qualification import _build, _erc_violations, _json, _sha, _signature

LAYOUT_FAILURE_WITNESS_KEYS = frozenset(
    {
        "build_failure",
        "diagnostic",
        "diagnostics",
        "failure",
        "failure_path",
        "layout_failure",
        "logs",
        "returncode",
        "route_failure",
        "stderr",
    }
)

PARSE_ONLY_EVIDENCE_KEYS = frozenset(
    {
        "coverage_label",
        "generation_success",
        "internal_metric_only",
        "parse_success",
        "planned_cell",
        "requested_factor_label",
    }
)


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


def validate_real_tool_qualification_evidence(evidence: object) -> list[str]:
    """Return validation errors for a covered-cell real-tool evidence link."""
    if not isinstance(evidence, dict):
        return ["real-tool evidence must be an object"]
    errors = []
    if evidence.get("schema_version") != "m2h2.real-tool-evidence.1":
        errors.append("real-tool evidence schema_version must be m2h2.real-tool-evidence.1")
    if evidence.get("locked_kicad_version") != "10.0.6":
        errors.append("real-tool evidence must use locked KiCad 10.0.6")
    for field in ("exact_head_sha", "qualification_root", "results_json", "case_id"):
        value = evidence.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"real-tool evidence must include non-empty {field}")
    head = evidence.get("exact_head_sha")
    if not isinstance(head, str) or re.fullmatch(r"[0-9a-f]{40}", head) is None:
        errors.append("real-tool evidence exact_head_sha must be a full commit SHA")
    runs = evidence.get("runs")
    if (
        not isinstance(runs, list)
        or len(runs) != 5
        or any(not isinstance(run, str) or not run.strip() for run in runs)
        or len(set(run for run in runs if isinstance(run, str))) != 5
    ):
        errors.append("real-tool evidence must include exactly five distinct non-empty run links")
    forbidden = sorted(PARSE_ONLY_EVIDENCE_KEYS.intersection(evidence))
    if forbidden:
        errors.append(
            "real-tool evidence must not rely on parse/generation/planned-label keys: "
            + ", ".join(forbidden)
        )
    return errors


def validate_semantic_impossibility_witness(witness: object) -> list[str]:
    """Return validation errors for a semantic impossibility witness.

    A coverage cell may be unsupported only by semantic proof. Build, layout,
    routing, or tool failure evidence must not masquerade as impossibility.
    """
    if not isinstance(witness, dict):
        return ["semantic impossibility witness must be an object"]
    errors = []
    if witness.get("schema_version") != "m2h2.semantic-impossibility.1":
        errors.append("witness schema_version must be m2h2.semantic-impossibility.1")
    if witness.get("kind") != "semantic_impossibility":
        errors.append("witness kind must be semantic_impossibility")
    if witness.get("source") != "semantic_model":
        errors.append("witness source must be semantic_model")
    proof = witness.get("proof")
    if not isinstance(proof, str) or not proof.strip():
        errors.append("witness proof must be a non-empty semantic explanation")
    forbidden = sorted(LAYOUT_FAILURE_WITNESS_KEYS.intersection(witness))
    if forbidden:
        errors.append(
            "semantic impossibility witness must not contain layout/build failure keys: "
            + ", ".join(forbidden)
        )
    return errors


def validate_coverage_ledger_evidence(ledger: dict) -> None:
    """Validate coverage ledger evidence rules for covered and unsupported cells."""
    errors = []
    for row_id, row in ledger.get("rows", {}).items():
        for index, record in enumerate(row.get("covered_cells", [])):
            location = f"{row_id}.covered_cells[{index}]"
            if not isinstance(record, dict):
                errors.append(f"{location} must be a structured object")
                continue
            if not record.get("cell"):
                errors.append(f"{location} must name the covered cell")
            evidence = record.get("real_tool_qualification_evidence")
            for error in validate_real_tool_qualification_evidence(evidence):
                errors.append(f"{location}: {error}")
        for index, record in enumerate(row.get("unsupported_cells", [])):
            location = f"{row_id}.unsupported_cells[{index}]"
            if not isinstance(record, dict):
                errors.append(f"{location} must be a structured object")
                continue
            if not record.get("cell"):
                errors.append(f"{location} must name the unsupported cell")
            witness = record.get("semantic_impossibility_witness")
            for error in validate_semantic_impossibility_witness(witness):
                errors.append(f"{location}: {error}")
    if errors:
        raise ValueError("; ".join(errors))


def validate_coverage_ledger_impossibilities(ledger: dict) -> None:
    """Backward-compatible wrapper for semantic impossibility validation."""
    validate_coverage_ledger_evidence(ledger)


def verify(run: Path, design: dict, expected: dict) -> dict:
    signature = _signature(run)
    resolved = assets()
    plan = semantic_plan(validate(design, resolved), resolved)
    composition_observer = observe_composition_evidence(plan, signature["composition"]).as_dict()
    schematic = next((run / "project").glob("*.kicad_sch"))
    observed = observe(schematic, run / "reports/netlist.xml")
    native_pin_diagnostic = observe_native_pin_composition(plan, design, observed).as_dict()
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
        and composition_observer["passed"]
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
        "composition_observer": composition_observer,
        "native_pin_composition_diagnostic": native_pin_diagnostic,
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
    validate_coverage_ledger_evidence(
        _json(ROOT / "fixtures/m2h2/development/interaction_coverage.json")
    )
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
            run.get("signature") == runs[0].get("signature")
            and run.get("composition_observer") == runs[0].get("composition_observer")
            for run in runs[1:]
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
        summary = results[-1]
        print(
            json.dumps(
                {
                    "kind": "m2h2.interaction-case-summary.1",
                    "group": args.group,
                    "id": summary["id"],
                    "cell": summary["cell"],
                    "selected_triple": summary["selected_triple"],
                    "accepted": summary["accepted"],
                    "reproducible": summary["reproducible"],
                    "observed_structural_class": summary["observed_structural_class"],
                    "observed_structural_class_stable": summary["observed_structural_class_stable"],
                    "runs": [run["path"] for run in runs],
                },
                separators=(",", ":"),
            ),
            flush=True,
        )
        if args.group == "i3":
            for block, variant in zip(
                runs[0].get("signature", {}).get("composition", {}).get("blocks", []),
                runs[0].get("signature", {}).get("composition", {}).get("variants", []),
                strict=False,
            ):
                print(
                    json.dumps(
                        {
                            "kind": "m2h2.observed-i3-placement.1",
                            "case": design_path.stem,
                            "block": block,
                            "variant": variant,
                        },
                        separators=(",", ":"),
                    ),
                    flush=True,
                )
        (output / "progress.json").write_text(json.dumps(results, indent=2) + "\n")
    (output / "results.json").write_text(
        json.dumps(
            {
                "schema_version": "m2h2.interaction-qualification.1",
                "group": args.group,
                "git_head": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                ).strip(),
                "source_sha256": {
                    str(path.relative_to(ROOT)): _sha(path)
                    for path in sorted((ROOT / "src/ai_kicad").glob("*.py"))
                },
                "runner_sha256": _sha(Path(__file__)),
                "toolchain_lock_sha256": _sha(ROOT / "fixtures/m1a/toolchain.lock.json"),
                "asset_lock_sha256": _sha(ROOT / "fixtures/m2b/assets.lock.json"),
                "policy_lock_sha256": _sha(ROOT / "fixtures/m1a/policy.lock.json"),
                "runs_per_case": 5,
                "normalization": "run_m2g2_qualification._signature; only documented ERC date/source and SVG title fields",
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
