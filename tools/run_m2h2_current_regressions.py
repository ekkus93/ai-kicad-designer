"""Run one-build locked M2h2 current-source regression checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from ai_kicad.m2a import ROOT
from run_m2g2_qualification import _build, _erc_violations, _json, _sha, _signature

CANONICAL_LIMIT_NM = 250_000_000
KICAD_VERSION = "10.0.6"

CASES = {
    "v6-3": ROOT / "fixtures/m2blind_v6/ir/V6-3.json",
    "dp2": ROOT / "fixtures/m2h2/development/dp2.json",
    "i4__b2_mixed": ROOT / "fixtures/m2h2/interaction/i4/b2_mixed.json",
}


def _toolchain_versions() -> dict[str, str]:
    lock = _json(ROOT / "fixtures/m1a/toolchain.lock.json")
    return {
        executable["id"]: executable["version"]
        for executable in lock.get("executables", [])
        if executable.get("id") in {"kicad-cli", "kicad-cli-binary"}
    }


def _source_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): _sha(path)
        for path in sorted((ROOT / "src/ai_kicad").glob("*.py"))
    }


def _reference_nets(design: dict[str, Any]) -> list[str]:
    generated = sorted(
        {
            relationship["local"]
            for relationship in design.get("relationships", [])
            if relationship.get("kind") == "reference_divider" and relationship.get("local")
        }
    )
    if generated:
        return generated
    return ["VREF"] if any(net.get("id") == "VREF" for net in design.get("nets", [])) else []


def _connector_ids(design: dict[str, Any]) -> set[str]:
    return {
        component["id"]
        for component in design.get("components", [])
        if component.get("asset", "").startswith("Connector_Generic:")
    }


def _component_asset_count(design: dict[str, Any], asset: str) -> int:
    return sum(1 for component in design.get("components", []) if component.get("asset") == asset)


def _net_has_external_connector(design: dict[str, Any], net: str) -> bool:
    connectors = _connector_ids(design)
    return any(
        component_id in connectors
        for candidate in design.get("nets", [])
        if candidate.get("id") == net
        for component_id, _pin in candidate.get("members", [])
    )


def _net_witnesses(signature: dict[str, Any]) -> dict[str, dict[str, Any]]:
    certificate = signature["composition"]["obligation_certificate"]
    return {
        witness["net"]: witness
        for witness in certificate.get("net_graph_witnesses", [])
        if "net" in witness
    }


def _case_errors(case_id: str, design: dict[str, Any], signature: dict[str, Any]) -> list[str]:
    errors = []
    if signature["electrical"]["status"] != "pass":
        errors.append("independent electrical observation did not pass")
    if signature["electrical"].get("diagnostics"):
        errors.append("independent electrical observer reported diagnostics")
    if _erc_violations(signature["erc"]) != 0:
        errors.append("unexpected ERC violations were reported")
    certificate = signature["composition"]["obligation_certificate"]
    if certificate.get("serialized_scene_verified") != "pass":
        errors.append("serialized-scene verification did not pass")

    witnesses = _net_witnesses(signature)
    for net in _reference_nets(design):
        witness = witnesses.get(net)
        if not witness:
            errors.append(f"missing canonical graph witness for {net}")
            continue
        canonical_length = witness.get("canonical_length_nm")
        if not isinstance(canonical_length, int):
            errors.append(f"missing canonical length for {net}")
        elif canonical_length > CANONICAL_LIMIT_NM:
            errors.append(f"{net} canonical length {canonical_length} exceeds {CANONICAL_LIMIT_NM}")
        if witness.get("component_count") != 1:
            errors.append(f"{net} has component_count={witness.get('component_count')}")

    if case_id == "dp2":
        if _component_asset_count(design, "Amplifier_Operational:NE5532") != 2:
            errors.append("DP2 does not contain exactly two NE5532 packages")
        for net in _reference_nets(design):
            if _net_has_external_connector(design, net):
                errors.append(f"DP2 generated reference {net} uses an external connector")
            terminal_count = len(witnesses.get(net, {}).get("terminal_components", []))
            if terminal_count != 9:
                errors.append(f"DP2 {net} terminal count {terminal_count} is not 9")
    return errors


def _run_case(case_id: str, design_path: Path, output: Path) -> dict[str, Any]:
    design = _json(design_path)
    destination = output / case_id / "run1"
    started = time.perf_counter()
    returncode = _build(design_path, destination)
    actual = destination if returncode == 0 else destination.with_name("run1.failed")
    record: dict[str, Any] = {
        "id": case_id,
        "design": str(design_path.relative_to(ROOT)),
        "design_sha256": _sha(design_path),
        "run": 1,
        "returncode": returncode,
        "path": str(actual.relative_to(ROOT)),
        "runtime_seconds": round(time.perf_counter() - started, 6),
    }
    if returncode != 0:
        record.update(accepted=False, failure=_json(actual / "reports/failure.json"))
        return record

    signature = _signature(actual)
    errors = _case_errors(case_id, design, signature)
    reference_metrics = {
        net: {
            "canonical_length_nm": witness.get("canonical_length_nm"),
            "component_count": witness.get("component_count"),
            "terminal_count": len(witness.get("terminal_components", [])),
        }
        for net, witness in _net_witnesses(signature).items()
        if net in _reference_nets(design)
    }
    record.update(
        accepted=not errors,
        errors=errors,
        electrical_status=signature["electrical"]["status"],
        electrical_diagnostics=signature["electrical"].get("diagnostics"),
        erc_violation_count=_erc_violations(signature["erc"]),
        serialized_scene_verified=signature["composition"]["obligation_certificate"][
            "serialized_scene_verified"
        ],
        reference_metrics=reference_metrics,
        layout=signature["layout"],
    )
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    output = args.out.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"refusing to overwrite nonempty regression directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    versions = _toolchain_versions()
    version_errors = [
        f"{tool} version {version} is not {KICAD_VERSION}"
        for tool, version in sorted(versions.items())
        if version != KICAD_VERSION
    ]
    if set(versions) != {"kicad-cli", "kicad-cli-binary"}:
        version_errors.append(f"missing locked KiCad executables: {sorted(versions)}")

    results = []
    for case_id, design_path in CASES.items():
        result = _run_case(case_id, design_path, output)
        results.append(result)
        print(
            json.dumps(
                {
                    "case": case_id,
                    "returncode": result["returncode"],
                    "accepted": result["accepted"],
                }
            ),
            flush=True,
        )

    payload = {
        "schema_version": "m2h2.current-regression.1",
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "git_status": subprocess.check_output(
            ["git", "status", "--short"], cwd=ROOT, text=True
        ).splitlines(),
        "python": sys.version,
        "toolchain_versions": versions,
        "toolchain_lock_sha256": _sha(ROOT / "fixtures/m1a/toolchain.lock.json"),
        "asset_lock_sha256": _sha(ROOT / "fixtures/m2b/assets.lock.json"),
        "policy_lock_sha256": _sha(ROOT / "fixtures/m1a/policy.lock.json"),
        "source_sha256": _source_hashes(),
        "version_errors": version_errors,
        "results": results,
        "accepted": sum(item["accepted"] for item in results),
        "total": len(results),
    }
    (output / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(
        json.dumps({key: payload[key] for key in ("accepted", "total", "version_errors")}),
        flush=True,
    )
    if version_errors or payload["accepted"] != payload["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
