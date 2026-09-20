"""M1 schematic build command."""

import argparse
import json
from pathlib import Path
import sys

from pydantic import ValidationError

from .assets import AssetLock, resolve, sha256
from .ir import InputError, load_json, validate
from .kicad import ToolFailure, run_headless, validate_toolchain
from .schematic import Infeasible, emit_schematic, layout_schematic
from .verify import observe_electrical, verify_electrical


def _policy(path: Path) -> dict:
    lock = load_json(path)
    if (
        set(lock) != {"schema_version", "profiles"}
        or lock["schema_version"] != "m1.1"
        or len(lock["profiles"]) != 1
    ):
        raise InputError("unsupported policy lock")
    profile = lock["profiles"][0]
    if (
        set(profile) != {"id", "revision", "path", "sha256"}
        or profile["id"] != "drafting.v1"
        or profile["revision"] != "m1a"
    ):
        raise InputError("unsupported drafting policy")
    file = (path.parent / profile["path"]).resolve()
    if not file.is_relative_to(path.parent.resolve()):
        raise InputError("policy path traverses lock directory")
    try:
        data = file.read_bytes()
    except OSError as exc:
        raise InputError("policy file unavailable") from exc
    if sha256(data) != profile["sha256"]:
        raise InputError("policy file mismatch")
    return load_json(file)


def build(args: argparse.Namespace) -> int:
    out = args.out.resolve()
    stage = out.with_name(out.name + ".staging")
    failed = out.with_name(out.name + ".failed")
    if out.exists() or stage.exists() or failed.exists():
        print("output, staging or failed directory already exists", file=sys.stderr)
        return 4
    stage.mkdir(parents=True)
    stages = []
    try:
        if args.target != "schematic":
            raise InputError("M1 supports only target schematic")
        repo = Path(__file__).resolve().parents[2]
        expected = validate(load_json(args.design))
        stages.append({"stage": "validate", "status": "ok"})
        lock = AssetLock.model_validate(load_json(args.assets_lock))
        symbols = resolve(expected, lock, args.assets_lock.parent)
        stages.append({"stage": "resolve", "status": "ok"})
        policy = _policy(args.policy_lock)
        supported_policy = {
            "grid_nm": 1_270_000,
            "text_height_nm": 1_270_000,
            "wire_gap_nm": 1_270_000,
            "symbol_gap_nm": 2_540_000,
            "block_gap_nm": 5_080_000,
            "margins_nm": {
                "left": 20_320_000,
                "top": 25_400_000,
                "right": 20_320_000,
                "bottom": 25_400_000,
            },
            "seed": 0,
            "power_assets": {},
        }
        if policy != supported_policy:
            raise InputError("unsupported M1 drafting policy")
        launcher = validate_toolchain(args.toolchain_lock, repo / "requirements.lock")
        layout = layout_schematic(symbols)
        stages.append({"stage": "layout_schematic", "status": "ok"})
        schematic = emit_schematic(expected, symbols, layout, stage)
        stages.append({"stage": "emit_schematic", "status": "ok"})
        netlist, erc, svgs = run_headless(schematic, launcher, stage)
        stages.append({"stage": "kicad_cli", "status": "ok"})
        observed = observe_electrical(schematic, netlist)
        comparison = verify_electrical(expected, observed)
        reports = stage / "reports"
        (reports / "electrical.json").write_text(json.dumps(comparison, indent=2) + "\n")
        stages.append(
            {
                "stage": "verify_electrical",
                "status": "ok" if comparison["status"] == "pass" else "tool_failed",
            }
        )
        erc_data = json.loads(erc.read_text())
        if comparison["status"] != "pass":
            raise ToolFailure("observed electrical graph differs from expected IR")
        # M1 captures ERC evidence; unexpected actual violations block acceptance.
        sheets = erc_data.get("sheets")
        violations = (
            [v for sheet in sheets for v in sheet["violations"]]
            if isinstance(sheets, list)
            else None
        )
        if not isinstance(violations, list):
            raise ToolFailure("ERC report has no violation inventory")
        if violations:
            raise ToolFailure(f"ERC returned {len(violations)} violations")
        files = [
            p
            for p in stage.rglob("*")
            if p.is_file()
            and "config" not in p.relative_to(stage).parts
            and p.suffix != ".kicad_prl"
        ]
        design_digest = sha256(json.dumps(expected, sort_keys=True, separators=(",", ":")).encode())
        lock_digests = {
            "assets": sha256(args.assets_lock.read_bytes()),
            "toolchain": sha256(args.toolchain_lock.read_bytes()),
            "policy": sha256(args.policy_lock.read_bytes()),
        }
        source_files = sorted((repo / "src/ai_kicad").glob("*.py")) + [repo / "pyproject.toml"]
        compiler_digest = sha256(
            b"".join(
                str(path.relative_to(repo)).encode() + b"\0" + path.read_bytes() + b"\0"
                for path in source_files
            )
        )
        build_key = sha256(
            json.dumps(
                {"design": design_digest, "locks": lock_digests, "compiler": compiler_digest},
                sort_keys=True,
            ).encode()
        )

        def artifact(path: Path) -> dict:
            relative = str(path.relative_to(stage))
            media = {
                ".kicad_sch": "application/x-kicad-schematic",
                ".kicad_pro": "application/json",
                ".xml": "application/xml",
                ".svg": "image/svg+xml",
                ".json": "application/json",
            }.get(path.suffix, "application/octet-stream")
            producer = (
                "emit_schematic"
                if path.suffix in (".kicad_sch", ".kicad_pro")
                else "verify_electrical"
                if path.name == "electrical.json"
                else "kicad_cli"
            )
            return {
                "path": relative,
                "media_type": media,
                "sha256": sha256(path.read_bytes()),
                "producer_stage": producer,
            }

        manifest = {
            "schema_version": "m1.1",
            "build_key": build_key,
            "target": "schematic",
            "design_digest": design_digest,
            "compiler_digest": compiler_digest,
            "lock_digests": lock_digests,
            "stages": stages,
            "checks": [
                {
                    "id": "electrical",
                    "status": "pass",
                    "artifact_digests": [sha256((reports / "electrical.json").read_bytes())],
                    "evidence": "reports/electrical.json",
                    "diagnostics": [],
                },
                {
                    "id": "erc",
                    "status": "pass",
                    "artifact_digests": [sha256(erc.read_bytes())],
                    "evidence": "reports/erc.json",
                    "diagnostics": [],
                },
                {
                    "id": "svg",
                    "status": "pass",
                    "artifact_digests": [sha256(p.read_bytes()) for p in svgs],
                    "evidence": [str(p.relative_to(stage)) for p in svgs],
                    "diagnostics": [],
                },
            ],
            "artifacts": [artifact(p) for p in sorted(files)],
            "readiness": {
                "schematic_compiled": True,
                "schematic_reviewed": False,
                "placement_verified": False,
                "routing_verified": False,
                "manufacturing_verified": False,
                "release_ready": False,
            },
        }
        (reports / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        stage.rename(out)
        print(out)
        return 0
    except Exception as exc:
        # Preserve all generated evidence under a visibly rejected directory.
        code = (
            2
            if isinstance(exc, (InputError, ValidationError))
            else 3
            if isinstance(exc, Infeasible)
            else 4
        )
        report = stage / "reports"
        report.mkdir(exist_ok=True)
        (report / "failure.json").write_text(
            json.dumps(
                {
                    "status": "invalid"
                    if code == 2
                    else "infeasible"
                    if code == 3
                    else "tool_failed",
                    "message": str(exc),
                    "stages": stages,
                },
                indent=2,
            )
            + "\n"
        )
        stage.rename(failed)
        print(f"M1 build failed: {exc}; evidence: {failed}", file=sys.stderr)
        return code


def main() -> None:
    parser = argparse.ArgumentParser(prog="ai_kicad")
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("build")
    command.add_argument("design", type=Path)
    command.add_argument("--target", required=True)
    command.add_argument("--assets-lock", type=Path, required=True)
    command.add_argument("--toolchain-lock", type=Path, required=True)
    command.add_argument("--policy-lock", type=Path, required=True)
    command.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if load_json(args.design).get("profile") == "m2a.1":
        from .m2a_build import build as build_m2a

        raise SystemExit(build_m2a(args))
    raise SystemExit(build(args))


if __name__ == "__main__":
    main()
