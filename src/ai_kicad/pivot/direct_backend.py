"""Selected direct KiCad CLI/native-file backend implementation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from argparse import Namespace
from pathlib import Path

from ai_kicad.ir import load_json
from ai_kicad.m2a import ROOT as REPO_ROOT
from ai_kicad.m2b import assets as m2b_assets
from ai_kicad.m2b_build import build as build_m2b
from ai_kicad.sexpr import parse

from .backend import BackendError, DIRECT_PILOT_MANIFEST, SupportLevel
from .model import DesignModel, from_legacy_ir
from .native import (
    assign_footprint_maps,
    board_component_inventory,
    inspect_board,
    inspect_schematic,
    verify_pin_pad_maps,
)
from .placement import apply_placement


class DirectKiCadBackend:
    manifest = DIRECT_PILOT_MANIFEST

    def __init__(self, workspace: Path, cli: Path, environment: dict[str, str] | None = None):
        self.workspace = workspace.resolve()
        self.cli = cli.resolve()
        self.environment = environment or {}
        if not self.cli.is_file():
            raise BackendError("initialize", "KiCad CLI executable is absent")

    def _path(self, value: str) -> Path:
        lexical = self.workspace / value
        candidate = lexical.resolve()
        if Path(value).is_absolute() or not candidate.is_relative_to(self.workspace):
            raise BackendError("path", "path escapes backend workspace")
        cursor = self.workspace
        if any((cursor := cursor / part).is_symlink() for part in Path(value).parts):
            raise BackendError("path", "backend path traverses symlink")
        return candidate

    def _run(self, operation: str, arguments: list[str]) -> dict:
        environment = dict(os.environ)
        environment.update({"LC_ALL": "C", "TZ": "UTC"})
        environment.update(self.environment)
        try:
            result = subprocess.run(
                [str(self.cli), *arguments],
                cwd=self.workspace,
                env=environment,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise BackendError(
                operation, f"KiCad process unavailable: {type(exc).__name__}"
            ) from exc
        if result.returncode:
            raise BackendError(operation, result.stderr or result.stdout)
        return {
            "status": "PASS",
            "operation": operation,
            "command": [str(self.cli), *arguments],
            "stdout": result.stdout,
            "stderr": result.stderr,
            "mutation_occurred": False,
        }

    def call(self, operation: str, request: dict) -> dict:
        required = (
            SupportLevel.EXPERIMENTAL
            if operation in {"route_nets", "sync_pcb"}
            else SupportLevel.VERIFIED
        )
        capability = self.manifest.capability(operation, required=required)
        if operation == "create_schematic":
            design_path = self._path(request["design"])
            bom_path = self._path(request["bom"])
            footprint_lock_path = self._path(request["footprint_lock"])
            profile_path = self._path(request["board_profile"])
            model_path = self._path(request["design_model"])
            toolchain_path = self._path(request["toolchain_lock"])
            destination = self._path(request["output"])
            if not all(path.is_file() for path in (
                design_path, bom_path, footprint_lock_path, profile_path, model_path, toolchain_path
            )):
                raise BackendError(operation, "all locked design inputs and toolchain lock must exist")
            if destination.exists():
                raise BackendError(operation, "schematic output must be a new directory")
            model = DesignModel.model_validate_json(model_path.read_text())
            model.require_revision_match()
            if model.revision_id != request["expected_revision"]:
                raise BackendError(operation, "schematic compilation targets a stale design revision")
            try:
                reconstructed = from_legacy_ir(
                    load_json(design_path),
                    m2b_assets(),
                    load_json(bom_path),
                    load_json(footprint_lock_path),
                    load_json(profile_path),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise BackendError(operation, f"legacy inputs failed canonical conversion: {exc}") from exc
            actual_graph = model.model_dump(mode="json", exclude={"revision_id", "parent_revision"})
            expected_graph = reconstructed.model_dump(
                mode="json", exclude={"revision_id", "parent_revision"}
            )
            if actual_graph != expected_graph:
                raise BackendError(operation, "canonical model does not match the supplied compiler inputs")
            lock_data = load_json(toolchain_path)
            locked_cli = next(
                (Path(item["path"]).resolve() for item in lock_data.get("executables", [])
                 if item.get("id") == "kicad-cli"),
                None,
            )
            if locked_cli is None:
                raise BackendError(operation, "toolchain lock has no KiCad CLI launcher")
            if request.get("dry_run", False):
                return {
                    "status": "PLAN_VALID",
                    "mutation_occurred": False,
                    "source_revision": model.revision_id,
                    "output": request["output"],
                    "compiler": "M2b",
                    "kicad_version": "10.0.6",
                }
            destination.parent.mkdir(parents=True, exist_ok=True)
            candidate_dir = destination.with_name(destination.name + ".candidate")
            failed_dir = destination.with_name(destination.name + ".failed")
            if candidate_dir.exists() or failed_dir.exists():
                raise BackendError(operation, "candidate/failure evidence path already exists")
            args = Namespace(
                design=design_path,
                target="schematic",
                assets_lock=REPO_ROOT / "fixtures/m2b/assets.lock.json",
                toolchain_lock=toolchain_path,
                policy_lock=REPO_ROOT / "fixtures/m1a/policy.lock.json",
                out=candidate_dir,
            )
            if build_m2b(args) != 0:
                generated_failure = candidate_dir.with_name(candidate_dir.name + ".failed")
                if generated_failure.exists():
                    os.replace(generated_failure, failed_dir)
                raise BackendError(operation, f"M2b schematic compiler failed; evidence: {failed_dir}")
            schematic_files = sorted((candidate_dir / "project").glob("*.kicad_sch"))
            netlist = candidate_dir / "reports/netlist.xml"
            erc = candidate_dir / "reports/erc.json"
            if len(schematic_files) != 1 or not netlist.is_file() or not erc.is_file():
                os.replace(candidate_dir, failed_dir)
                raise BackendError(operation, f"compiled schematic artifacts are incomplete; evidence: {failed_dir}")
            observer = inspect_schematic(
                load_json(design_path), schematic_files[0], netlist
            )
            if observer["status"] != "pass":
                os.replace(candidate_dir, failed_dir)
                raise BackendError(operation, f"independent schematic equivalence failed; evidence: {failed_dir}")
            evidence = {
                "schema_version": "pivot-schematic-evidence.v1",
                "design_revision": model.revision_id,
                "compiler": "M2b",
                "kicad_cli": str(locked_cli),
                "kicad_version": "10.0.6",
                "source_design_sha256": hashlib.sha256(design_path.read_bytes()).hexdigest(),
                "canonical_model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
                "schematic_sha256": hashlib.sha256(schematic_files[0].read_bytes()).hexdigest(),
                "netlist_sha256": hashlib.sha256(netlist.read_bytes()).hexdigest(),
                "erc_sha256": hashlib.sha256(erc.read_bytes()).hexdigest(),
                "independent_observation": observer,
                "mutation_occurred": True,
            }
            (candidate_dir / "pivot-schematic-evidence.json").write_text(
                json.dumps(evidence, indent=2, sort_keys=True) + "\n"
            )
            os.replace(candidate_dir, destination)
            return {
                "status": "PASS",
                "mutation_occurred": True,
                "source_revision": model.revision_id,
                "output": request["output"],
                "schematic": str(
                    (destination / schematic_files[0].relative_to(candidate_dir)).relative_to(
                        self.workspace
                    )
                ),
                "schematic_sha256": evidence["schematic_sha256"],
                "netlist_sha256": evidence["netlist_sha256"],
                "erc_sha256": evidence["erc_sha256"],
                "independent_observation": observer,
            }
        if operation == "create_project":
            source = self._path(request["source"])
            destination = self._path(request["destination"])
            if not source.is_dir() or destination.exists():
                raise BackendError(operation, "source must exist and destination must be new")
            if request.get("dry_run", False):
                return {"status": "PLAN_VALID", "mutation_occurred": False}
            stage = Path(tempfile.mkdtemp(prefix="project-candidate-", dir=destination.parent))
            shutil.rmtree(stage)
            try:
                shutil.copytree(source, stage, symlinks=False)
            except Exception:
                shutil.rmtree(stage, ignore_errors=True)
                raise
            source_hashes = {
                str(path.relative_to(source)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(source.rglob("*"))
                if path.is_file() and not path.is_symlink()
            }
            destination_hashes = {
                str(path.relative_to(stage)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(stage.rglob("*"))
                if path.is_file()
            }
            if source_hashes != destination_hashes:
                shutil.rmtree(stage)
                raise BackendError(operation, "exact saved-file readback failed")
            os.replace(stage, destination)
            return {"status": "PASS", "mutation_occurred": True, "hashes": destination_hashes}
        if operation in {"run_erc", "run_drc"}:
            source = self._path(request["source"])
            output = self._path(request["output"])
            output.parent.mkdir(parents=True, exist_ok=True)
            domain = "sch" if operation == "run_erc" else "pcb"
            command = [
                domain,
                operation.removeprefix("run_"),
                "--format",
                "json",
                "--output",
                str(output),
                str(source),
            ]
            response = self._run(operation, command)
            response["report"] = json.loads(output.read_text())
            return response
        if operation == "export_fabrication":
            source = self._path(request["source"])
            output = self._path(request["output"])
            output.mkdir(parents=True, exist_ok=False)
            gerber = self._run(
                operation, ["pcb", "export", "gerbers", "--output", str(output), str(source)]
            )
            drill = self._run(
                operation,
                ["pcb", "export", "drill", "--output", str(output), "--generate-map", str(source)],
            )
            return {
                "status": "PASS",
                "operation": operation,
                "calls": [gerber, drill],
                "mutation_occurred": True,
            }
        if operation == "apply_schematic_transaction":
            source = self._path(request["source"])
            changes = request["changes"]
            text = source.read_text()
            candidate = text
            for change in changes:
                old, new = change["old"], change["new"]
                if candidate.count(old) != 1:
                    raise BackendError(operation, "transaction preimage is not unique")
                candidate = candidate.replace(old, new, 1)
            parse(candidate)
            if request.get("dry_run", False):
                return {"status": "PLAN_VALID", "mutation_occurred": False, "changes": len(changes)}
            temporary = source.with_suffix(source.suffix + ".candidate")
            temporary.write_text(candidate)
            os.replace(temporary, source)
            return {"status": "PASS", "mutation_occurred": True, "changes": len(changes)}
        if operation == "apply_placements":
            source = self._path(request["source"])
            destination = self._path(request["output"])
            if not source.is_file() or destination.exists():
                raise BackendError(operation, "source must exist and output must be new")
            if request.get("dry_run", False):
                plan = request["plan"]
                if plan.get("revision_id") != request["expected_revision"]:
                    raise BackendError(operation, "placement plan revision is stale")
                return {"status": "PLAN_VALID", "mutation_occurred": False}
            result = apply_placement(
                source,
                destination,
                request["plan"],
                expected_revision=request["expected_revision"],
            )
            return result | {"mutation_occurred": True}
        if operation == "verify_pin_pad_map":
            model_path = self._path(request["design_model"])
            footprint_root = self._path(request["footprint_root"])
            model = DesignModel.model_validate_json(model_path.read_text())
            model.require_revision_match()
            result = verify_pin_pad_maps(model, footprint_root)
            if result["status"] != "PASS":
                raise BackendError(operation, json.dumps(result["errors"]))
            return result | {"mutation_occurred": False}
        if operation == "assign_footprints":
            model_path = self._path(request["design_model"])
            footprint_root = self._path(request["footprint_root"])
            destination = self._path(request["output"])
            if not model_path.is_file() or destination.exists():
                raise BackendError(operation, "source model must exist and output must be new")
            model = DesignModel.model_validate_json(model_path.read_text())
            model.require_revision_match()
            if model.revision_id != request["expected_revision"]:
                raise BackendError(operation, "footprint assignment targets a stale design revision")
            try:
                candidate = assign_footprint_maps(model, request["assignments"], footprint_root)
            except (KeyError, TypeError, ValueError) as exc:
                raise BackendError(operation, str(exc)) from exc
            output = candidate.model_dump_json(indent=2) + "\n"
            if request.get("dry_run", False):
                return {
                    "status": "PLAN_VALID",
                    "mutation_occurred": False,
                    "source_revision": model.revision_id,
                    "new_revision_id": candidate.revision_id,
                    "assigned_components": len(request["assignments"]),
                    "fully_assigned": True,
                }
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(destination.name + ".candidate")
            try:
                temporary.write_text(output)
                saved = DesignModel.model_validate_json(temporary.read_text())
                saved.require_revision_match()
                if saved != candidate:
                    raise BackendError(operation, "canonical model candidate failed exact readback")
                os.replace(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
            return {
                "status": "PASS",
                "mutation_occurred": True,
                "source_revision": model.revision_id,
                "new_revision_id": candidate.revision_id,
                "output_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                "assigned_components": len(request["assignments"]),
                "fully_assigned": True,
                "pin_pad_verification": verify_pin_pad_maps(candidate, footprint_root),
            }
        if operation == "sync_pcb":
            schematic = self._path(request["schematic"])
            source_design = self._path(request["source_design"])
            bom_path = self._path(request["bom"])
            footprint_lock_path = self._path(request["footprint_lock"])
            profile_path = self._path(request["board_profile"])
            candidate = self._path(request["candidate"])
            destination = self._path(request["output"])
            model_path = self._path(request["design_model"])
            if not all(
                path.is_file()
                for path in (
                    schematic,
                    source_design,
                    bom_path,
                    footprint_lock_path,
                    profile_path,
                    candidate,
                )
            ) or destination.exists():
                raise BackendError(operation, "schematic/candidate must exist and output must be new")
            model = DesignModel.model_validate_json(model_path.read_text())
            model.require_revision_match()
            if model.revision_id != request["expected_revision"]:
                raise BackendError(operation, "synchronized board targets a stale design revision")
            reconstructed = from_legacy_ir(
                load_json(source_design),
                m2b_assets(),
                load_json(bom_path),
                load_json(footprint_lock_path),
                load_json(profile_path),
            )
            actual_graph = model.model_dump(mode="json", exclude={"revision_id", "parent_revision"})
            expected_graph = reconstructed.model_dump(
                mode="json", exclude={"revision_id", "parent_revision"}
            )
            if actual_graph != expected_graph:
                raise BackendError(operation, "schematic inputs do not match the canonical design revision")
            if hashlib.sha256(candidate.read_bytes()).hexdigest() != request["candidate_sha256"]:
                raise BackendError(operation, "synchronized board hash differs from declared input")
            netlist = self._path(request["netlist"])
            netlist.parent.mkdir(parents=True, exist_ok=True)
            self._run(
                operation,
                [
                    "sch",
                    "export",
                    "netlist",
                    "--format",
                    "kicadxml",
                    "--output",
                    str(netlist),
                    str(schematic),
                ],
            )
            schematic_report = inspect_schematic(
                json.loads(source_design.read_text()), schematic, netlist
            )
            if schematic_report["status"] != "pass":
                raise BackendError(operation, "source schematic failed independent equivalence")
            board_report = inspect_board(model, candidate)
            expected_refs = sorted(component.reference for component in model.components)
            if (
                board_report["unmatched_partitions"]
                or board_report["footprint_mismatches"]
                or board_report["component_references"] != expected_refs
            ):
                raise BackendError(operation, "synchronized board pin/pad/net identity mismatch")
            drc_path = self._path(request["drc_report"])
            drc_path.parent.mkdir(parents=True, exist_ok=True)
            drc = self._run(
                operation,
                [
                    "pcb",
                    "drc",
                    "--severity-all",
                    "--format",
                    "json",
                    "--output",
                    str(drc_path),
                    str(candidate),
                ],
            )
            drc_report = json.loads(drc_path.read_text())
            if drc_report.get("violations"):
                raise BackendError(operation, "KiCad DRC rejected synchronized board geometry")
            if request.get("dry_run", False):
                return {
                    "status": "PLAN_VALID",
                    "mutation_occurred": False,
                    "schematic": schematic_report,
                    "board": board_report,
                    "drc": drc_report,
                    "unconnected_items_expected": "synchronization precedes routing",
                    "capability": capability.model_dump(mode="json"),
                }
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(destination.name + ".candidate")
            shutil.copy2(candidate, temporary)
            os.replace(temporary, destination)
            return {
                "status": "PASS",
                "mutation_occurred": True,
                "candidate_sha256": request["candidate_sha256"],
                "imported_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                "schematic": schematic_report,
                "board": board_report,
                "drc": drc_report,
                "drc_command": drc["command"],
                "capability": capability.model_dump(mode="json"),
                "unconnected_items_expected": "synchronization precedes routing",
            }
        if operation == "route_nets":
            source = self._path(request["source"])
            candidate = self._path(request["candidate"])
            destination = self._path(request["output"])
            model_path = self._path(request["design_model"])
            if not source.is_file() or not candidate.is_file() or destination.exists():
                raise BackendError(operation, "base/candidate must exist and output must be new")
            model = DesignModel.model_validate_json(model_path.read_text())
            model.require_revision_match()
            if model.revision_id != request["expected_revision"]:
                raise BackendError(operation, "router candidate targets a stale design revision")
            candidate_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
            if candidate_hash != request["candidate_sha256"]:
                raise BackendError(operation, "router candidate hash differs from declared input")
            base_inventory = board_component_inventory(source)
            candidate_inventory = board_component_inventory(candidate)
            if base_inventory != candidate_inventory:
                raise BackendError(
                    operation, "router candidate changed footprint, placement, pad, or net identity"
                )
            observed = inspect_board(model, candidate)
            if observed["status"] != "PASS":
                raise BackendError(operation, "independent native observer rejected routed candidate")
            drc_path = self._path(request["drc_report"])
            drc_path.parent.mkdir(parents=True, exist_ok=True)
            destination.parent.mkdir(parents=True, exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix="route-candidate-", dir=candidate.parent))
            temporary = stage / candidate.name
            shutil.copy2(candidate, temporary)
            project = candidate.with_suffix(".kicad_pro")
            fp_table = candidate.parent / "fp-lib-table"
            if project.is_file():
                shutil.copy2(project, temporary.with_suffix(".kicad_pro"))
            if fp_table.is_file():
                shutil.copy2(fp_table, stage / "fp-lib-table")
            footprint_libraries = candidate.parent / "footprints"
            if footprint_libraries.is_dir():
                shutil.copytree(footprint_libraries, stage / "footprints")
            try:
                drc_result = self._run(
                    operation,
                    [
                        "pcb",
                        "drc",
                        "--refill-zones",
                        "--save-board",
                        "--severity-all",
                        "--format",
                        "json",
                        "--output",
                        str(drc_path),
                        str(temporary),
                    ],
                )
            except Exception:
                shutil.rmtree(stage, ignore_errors=True)
                raise
            drc_report = json.loads(drc_path.read_text())
            if drc_report.get("violations") or drc_report.get("unconnected_items"):
                shutil.rmtree(stage, ignore_errors=True)
                raise BackendError(operation, "KiCad DRC or unrouted-item gate rejected candidate")
            refilled_inventory = board_component_inventory(temporary)
            if refilled_inventory != base_inventory:
                shutil.rmtree(stage, ignore_errors=True)
                raise BackendError(operation, "zone refill changed footprint or net identities")
            observed = inspect_board(model, temporary)
            if observed["status"] != "PASS":
                shutil.rmtree(stage, ignore_errors=True)
                raise BackendError(operation, "readback observer rejected saved route candidate")
            if request.get("dry_run", False):
                refilled_hash = hashlib.sha256(temporary.read_bytes()).hexdigest()
                shutil.rmtree(stage, ignore_errors=True)
                return {
                    "status": "PLAN_VALID",
                    "mutation_occurred": False,
                    "candidate_sha256": candidate_hash,
                    "refilled_candidate_sha256": refilled_hash,
                    "observer": observed,
                    "drc": drc_report,
                    "capability": capability.model_dump(mode="json"),
                }
            os.replace(temporary, destination)
            shutil.rmtree(stage, ignore_errors=True)
            return {
                "status": "PASS",
                "mutation_occurred": True,
                "candidate_sha256": candidate_hash,
                "imported_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                "observer": observed,
                "drc": drc_report,
                "capability": capability.model_dump(mode="json"),
                "drc_command": drc_result["command"],
            }
        raise BackendError(operation, "verified operation has no direct adapter implementation")
