"""CLI for creating, inspecting and resuming pivot design workspaces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_kicad.ir import load_json
from ai_kicad.m2b import assets

from .controller import WorkflowController
from .direct_backend import DirectKiCadBackend
from .mcp_server import serve
from .model import DesignModel, from_legacy_ir


def _model_from_fixture(fixture: Path) -> DesignModel:
    return from_legacy_ir(
        load_json(fixture / "design.json"),
        assets(),
        load_json(fixture / "bom.json"),
        load_json(fixture / "footprint_assets.lock.json"),
        load_json(fixture / "board_profile.json"),
    )


def run(args: argparse.Namespace) -> int:
    args.workspace.mkdir(parents=True, exist_ok=True)
    backend = (
        DirectKiCadBackend(args.workspace, args.kicad_cli)
        if getattr(args, "kicad_cli", None) is not None
        else None
    )
    controller = WorkflowController(args.workspace, backend=backend)
    if args.pivot_command == "create":
        model = _model_from_fixture(args.fixture)
        with controller.revisions.writer("pivot-cli"):
            revision = controller.revisions.commit(
                model,
                {},
                expected_revision=None,
                idempotency_key=f"create:{model.revision_id}",
            )
        controller.set_revision(model.design_id, revision)
        controller.persist_handoff("created canonical design")
        print(json.dumps(controller._state(), indent=2))
        return 0
    if args.pivot_command in {"inspect", "resume"}:
        payload = controller._state()
        if args.pivot_command == "resume" and controller.handoff_path.is_file():
            payload["handoff"] = json.loads(controller.handoff_path.read_text())
        print(json.dumps(payload, indent=2))
        return 0
    if args.pivot_command == "validate":
        revision = controller.revisions.current_revision()
        valid = revision is not None and controller.revisions.verify(revision)
        print(json.dumps({"revision_id": revision, "valid": valid}))
        return 0 if valid else 4
    if args.pivot_command == "mcp-serve":
        serve(controller)
        return 0
    raise AssertionError(args.pivot_command)


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    pivot = subparsers.add_parser("pivot")
    commands = pivot.add_subparsers(dest="pivot_command", required=True)
    for name in ("create", "inspect", "resume", "validate", "mcp-serve"):
        command = commands.add_parser(name)
        command.add_argument("--workspace", type=Path, required=True)
        if name == "create":
            command.add_argument("--fixture", type=Path, required=True)
        if name == "mcp-serve":
            command.add_argument("--kicad-cli", type=Path)
    pivot.set_defaults(pivot_handler=run)
