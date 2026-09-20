"""M2a qualification command using the locked M1 KiCad subprocess boundary."""

import json
from pathlib import Path
import sys

from .assets import sha256
from .ir import InputError, load_json
from .kicad import ToolFailure, run_headless, validate_toolchain
from .m2a import (
    ROOT,
    check_observed_layout,
    compare,
    emit,
    fixture,
    layout,
    load_assets,
    observe,
    validate,
)


def build(args) -> int:
    out = args.out.resolve()
    if not str(out.parent).isascii():
        print("M2a output parent must be ASCII under locked KiCad C locale", file=sys.stderr)
        return 2
    stage_name = (
        out.name + ".staging"
        if out.name.isascii()
        else ".m2a-" + sha256(str(out).encode())[:16] + ".staging"
    )
    stage = out.with_name(stage_name)
    failed = out.with_name(out.name + ".failed")
    if any(path.exists() for path in (out, stage, failed)):
        print("output, staging or failed directory already exists", file=sys.stderr)
        return 4
    stage.mkdir(parents=True)
    stages = []
    try:
        if args.target != "schematic":
            raise InputError("M2a supports only target schematic")
        bundled = ROOT / "fixtures/m2a/assets.lock.json"
        if sha256(args.assets_lock.read_bytes()) != sha256(bundled.read_bytes()):
            raise InputError("M2a asset lock differs from qualified bundle")
        from .__main__ import _policy

        if _policy(args.policy_lock)["grid_nm"] != 1_270_000:
            raise InputError("unsupported drafting policy")
        raw = load_json(args.design)
        assets = load_assets()
        design = validate(raw, assets)
        stages.append({"stage": "validate_resolve", "status": "ok"})
        launcher = validate_toolchain(args.toolchain_lock, ROOT / "requirements.lock")
        scene = layout(design, assets)
        stages.append({"stage": "layout_schematic", "status": "ok"})
        schematic = emit(design, assets, scene, stage)
        stages.append({"stage": "emit_schematic", "status": "ok"})
        netlist, erc, svgs = run_headless(
            schematic, launcher, stage, ROOT / "fixtures/m2a/sym-lib-table"
        )
        stages.append({"stage": "kicad_cli", "status": "ok"})
        observed = observe(schematic, netlist)
        result = compare(design, observed)
        scene.metrics.update(check_observed_layout(observed))
        reports = stage / "reports"
        (reports / "electrical.json").write_text(json.dumps(result, indent=2) + "\n")
        (reports / "layout.json").write_text(json.dumps(scene.metrics, indent=2) + "\n")
        stages.append({"stage": "verify_electrical", "status": result["status"]})
        if result["status"] != "pass":
            raise ToolFailure("observed M2a electrical graph differs from expected IR")
        artifacts = []
        for path in sorted(stage.rglob("*")):
            if path.is_file() and "config" not in path.relative_to(stage).parts:
                artifacts.append(
                    {"path": str(path.relative_to(stage)), "sha256": sha256(path.read_bytes())}
                )
        (reports / "manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": "m2a.1",
                    "design_sha256": sha256(json.dumps(design, sort_keys=True).encode()),
                    "asset_lock_sha256": sha256(args.assets_lock.read_bytes()),
                    "toolchain_lock_sha256": sha256(args.toolchain_lock.read_bytes()),
                    "policy_lock_sha256": sha256(args.policy_lock.read_bytes()),
                    "stages": stages,
                    "checks": {
                        "electrical": "pass",
                        "erc": "pass",
                        "svg": "pass",
                        "layout": "pass",
                    },
                    "artifacts": artifacts,
                    "readiness": {
                        "schematic_compiled": True,
                        "schematic_reviewed": False,
                        "placement_verified": False,
                        "release_ready": False,
                    },
                },
                indent=2,
            )
            + "\n"
        )
        stage.rename(out)
        print(out)
        return 0
    except Exception as exc:
        report = stage / "reports"
        report.mkdir(exist_ok=True)
        (report / "failure.json").write_text(
            json.dumps(
                {
                    "status": "invalid" if isinstance(exc, InputError) else "tool_failed",
                    "message": str(exc),
                    "stages": stages,
                },
                indent=2,
            )
            + "\n"
        )
        stage.rename(failed)
        print(f"M2a build failed: {exc}; evidence: {failed}", file=sys.stderr)
        return 2 if isinstance(exc, InputError) else 4


def write_fixture(path: Path) -> None:
    path.write_text(json.dumps(fixture(), indent=2) + "\n")
