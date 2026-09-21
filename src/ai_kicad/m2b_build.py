"""M2b qualification build through locked KiCad and independent artifact checks."""

import json
import sys

from .assets import sha256
from .ir import InputError, load_json
from .kicad import ToolFailure, run_headless, validate_toolchain
from .m2a import ROOT, emit, observe
from .m2b import assets, check_observed_layout, compare, validate
from .m2_compose import compose_with_evidence


def build(args) -> int:
    out = args.out.resolve()
    if not str(out.parent).isascii():
        print("M2b output parent must be ASCII under locked KiCad C locale", file=sys.stderr)
        return 2
    stage_name = (
        out.name + ".staging"
        if out.name.isascii()
        else ".m2b-" + sha256(str(out).encode())[:16] + ".staging"
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
            raise InputError("M2b supports only target schematic")
        bundled = ROOT / "fixtures/m2b/assets.lock.json"
        if sha256(args.assets_lock.read_bytes()) != sha256(bundled.read_bytes()):
            raise InputError("M2b asset lock differs from qualified bundle")
        from .__main__ import _policy

        policy = _policy(args.policy_lock)
        if policy["grid_nm"] != 1_270_000:
            raise InputError("unsupported M2b drafting grid")
        resolved = assets()
        design = validate(load_json(args.design), resolved)
        stages.append({"stage": "validate_resolve", "status": "ok"})
        launcher = validate_toolchain(args.toolchain_lock, ROOT / "requirements.lock")
        scene, composition = compose_with_evidence(design, resolved)
        stages.append({"stage": "layout_schematic", "status": "ok"})
        reports = stage / "reports"
        reports.mkdir(exist_ok=True)
        (reports / "composition.json").write_text(json.dumps(composition, indent=2) + "\n")
        owned_assets = {c["asset"] for c in design["components"]}
        emitted_assets = {
            key: asset
            for key, asset in resolved.items()
            if key not in ("Regulator_Linear:L7805", "Timer:NE555D") or key in owned_assets
        }
        schematic = emit(design, emitted_assets, scene, stage)
        local_libraries = {
            "Regulator_Linear": "L7805",
            "Timer": "NE555D",
        }
        used_libraries = {c["asset"].split(":", 1)[0] for c in design["components"]} & set(
            local_libraries
        )
        if used_libraries:
            lines = ["(sym_lib_table", "  (version 7)"]
            for library in sorted(used_libraries):
                stem = local_libraries[library]
                (schematic.parent / f"{stem}.kicad_sym").write_bytes(
                    (ROOT / "fixtures/m2b" / f"{stem}.kicad_sym").read_bytes()
                )
                lines.append(
                    f'  (lib (name "{library}") (type "KiCad") '
                    f'(uri "${{KIPRJMOD}}/{stem}.kicad_sym") (options "") (descr "Locked KiCad 10.0.6 symbol"))'
                )
            lines.append(")")
            (schematic.parent / "sym-lib-table").write_text("\n".join(lines) + "\n")
        stages.append({"stage": "emit_schematic", "status": "ok"})
        netlist, erc, svgs = run_headless(
            schematic, launcher, stage, ROOT / "fixtures/m2a/sym-lib-table"
        )
        stages.append({"stage": "kicad_cli", "status": "ok"})
        observed = observe(schematic, netlist)
        electrical = compare(design, observed, resolved)
        (reports / "electrical.json").write_text(json.dumps(electrical, indent=2) + "\n")
        if electrical["status"] != "pass":
            stages.append({"stage": "verify_electrical", "status": "fail"})
            raise ToolFailure("M2b artifact connectivity differs from expected Circuit IR")
        layout = {**scene.metrics, **check_observed_layout(schematic, observed, design)}
        (reports / "layout.json").write_text(json.dumps(layout, indent=2) + "\n")
        stages.append({"stage": "verify_electrical_layout", "status": "pass"})
        artifacts = [
            {"path": str(path.relative_to(stage)), "sha256": sha256(path.read_bytes())}
            for path in sorted(stage.rglob("*"))
            if path.is_file()
            and "config" not in path.relative_to(stage).parts
            and path.suffix != ".kicad_prl"
        ]
        (reports / "manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": "m2b.1",
                    "corpus_manifest_sha256": sha256(
                        (ROOT / "fixtures/m2b/corpus.v1.json").read_bytes()
                    ),
                    "design_sha256": sha256(
                        json.dumps(design, sort_keys=True, separators=(",", ":")).encode()
                    ),
                    "asset_lock_sha256": sha256(args.assets_lock.read_bytes()),
                    "m2a_asset_lock_sha256": sha256(
                        (ROOT / "fixtures/m2a/assets.lock.json").read_bytes()
                    ),
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
        reports = stage / "reports"
        reports.mkdir(exist_ok=True)
        (reports / "failure.json").write_text(
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
        print(f"M2b build failed: {exc}; evidence: {failed}", file=sys.stderr)
        return 2 if isinstance(exc, InputError) else 4
