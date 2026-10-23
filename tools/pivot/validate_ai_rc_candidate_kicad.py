#!/usr/bin/env python3
"""Render one held-out M2b topology through KiCad and independent observers.

This deliberately records the host identity without enforcing the frozen-host
preflight. It is suitable for exploratory candidates and must not be described
as locked-host qualification when the host differs from the fixture lock.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path

from ai_kicad.kicad import run_headless
from ai_kicad.m2_compose import compose_with_evidence
from ai_kicad.m2a_artifacts import emit, observe, verify_serialized_scene
from ai_kicad.m2b import assets, check_observed_layout, compare, validate
from ai_kicad.ir import load_json


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--kicad-apprun", required=True, type=Path)
    parser.add_argument("--symbol-table", type=Path, default=Path("fixtures/m1a/sym-lib-table"))
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        parser.error(f"output directory already exists: {out}")
    out.mkdir(parents=True)
    design = validate(load_json(args.design), assets())
    resolved = assets()
    scene, composition = compose_with_evidence(design, resolved)
    schematic = emit(design, resolved, scene, out)
    verify_serialized_scene(design, scene, schematic)
    netlist, erc_path, svgs = run_headless(schematic, args.kicad_apprun.resolve(), out, args.symbol_table.resolve())
    observed = observe(schematic, netlist)
    electrical = compare(design, observed, resolved)
    layout = check_observed_layout(schematic, observed, design)
    erc = json.loads(erc_path.read_text())
    blocking_layout_metrics = (
        "observed_body_overlap_count",
        "observed_wire_through_body_count",
        "observed_wire_through_text_count",
        "observed_unrelated_wire_crossing_count",
        "observed_unrelated_pin_contact_count",
        "observed_pin_endpoint_mismatch_count",
        "observed_flow_reversal_count",
        "observed_stage_order_reversal_count",
    )
    layout_pass = layout.get("observed_page_margin_pass") is True and all(
        layout.get(key) == 0 for key in blocking_layout_metrics
    )
    erc_pass = bool(erc.get("sheets")) and all(not sheet["violations"] for sheet in erc["sheets"])
    launcher = args.kicad_apprun.resolve()
    cli = launcher.parent / "shared/bin/kicad-cli"
    report = {
        "schema_version": "ai-topology-native-kicad-check.v1",
        "status": "PASS" if electrical["status"] == "pass" and layout_pass and erc_pass else "FAIL",
        "kicad_version": erc.get("kicad_version"),
        "runner_identity": {
            "os": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "locked_host_qualification": False,
        "lock_note": "Host identity is recorded; run_headless uses KiCad 10.0.6, but frozen-host preflight is intentionally not bypassed or claimed.",
        "launcher_sha256": sha256(launcher),
        "kicad_cli_sha256": sha256(cli),
        "design_sha256": sha256(args.design),
        "schematic_sha256": sha256(schematic),
        "netlist_sha256": sha256(netlist),
        "erc_sha256": sha256(erc_path),
        "svg_sha256": sha256(svgs[0]),
        "electrical": electrical,
        "layout": layout,
        "composition": composition,
        "acceptance_checks": {
            "electrical_partition": "PASS" if electrical["status"] == "pass" else "FAIL",
            "erc": "PASS" if erc_pass else "FAIL",
            "observed_layout": "PASS" if layout_pass else "FAIL",
            "layout_hard_failure_metrics": {key: layout.get(key) for key in blocking_layout_metrics},
            "locked_host_qualification": "NOT_CLAIMED",
        },
    }
    (out / "kicad_check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "kicad_version": report["kicad_version"], "acceptance_checks": report["acceptance_checks"]}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
