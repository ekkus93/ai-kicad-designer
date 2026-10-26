"""Persistent phase controller, tool policy and compact model handoffs."""

from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Callable, Protocol

from .backend import DIRECT_PILOT_MANIFEST, DesignBackend
from .model import DesignModel
from .revisions import RevisionStore, StaleRevision
from .requirements import assess_requirements


class Phase(StrEnum):
    REQUIREMENTS = "REQUIREMENTS"
    CIRCUIT_DESIGN = "CIRCUIT_DESIGN"
    SCHEMATIC = "SCHEMATIC"
    FOOTPRINTS = "FOOTPRINTS"
    PCB_PLACEMENT = "PCB_PLACEMENT"
    PCB_ROUTING = "PCB_ROUTING"
    MANUFACTURING_REVIEW = "MANUFACTURING_REVIEW"
    REVIEW_READY = "REVIEW_READY"


PHASES = list(Phase)
REQUIRED_GATE = {
    Phase.CIRCUIT_DESIGN: "requirements_explicit",
    Phase.SCHEMATIC: "circuit_design_validated",
    Phase.FOOTPRINTS: "schematic_validated",
    Phase.PCB_PLACEMENT: "footprints_validated",
    Phase.PCB_ROUTING: "placement_validated",
    Phase.MANUFACTURING_REVIEW: "pcb_validated",
    Phase.REVIEW_READY: "package_ready_for_review",
}
# Leaving SCHEMATIC also requires joint machine/model visual acceptance of the same revision.
VISUAL_REVIEW_GATE = "schematic_visual_review"
ADDITIONAL_REQUIRED_GATES = {Phase.FOOTPRINTS: (VISUAL_REVIEW_GATE,)}


class SchematicReviewService(Protocol):
    """Runs the full generate/check/render/review/edit loop into a new output directory."""

    timeout_seconds: float

    def review(self, design: Path, output: Path) -> dict: ...


class Provider(Protocol):
    provider_id: str

    def complete(self, handoff: dict) -> dict: ...


class ControllerError(RuntimeError):
    code = "INVALID_INPUT"


class NotAuthorized(ControllerError):
    code = "NOT_AUTHORIZED_IN_PHASE"


class BudgetExceeded(ControllerError):
    code = "BUDGET_EXCEEDED"


class UnsupportedTool(ControllerError):
    code = "UNSUPPORTED_CAPABILITY"


@dataclass(frozen=True)
class Tool:
    name: str
    phase: Phase | None
    write: bool
    schema: dict
    handler: Callable[[dict], dict]
    implemented: bool = True
    # Long-running tools (a complete review loop) declare their own transport timeout.
    timeout_seconds: float | None = None


ALWAYS = {
    "get_design_state",
    "get_capabilities",
    "get_validation_report",
    "create_checkpoint",
    "rollback_to_checkpoint",
    "request_phase_transition",
}

PHASE_TOOLS = {
    Phase.REQUIREMENTS: {"define_requirements"},
    Phase.CIRCUIT_DESIGN: {"edit_circuit_graph", "check_design_calculations"},
    Phase.SCHEMATIC: {"create_schematic", "inspect_schematic", "run_erc", "review_schematic"},
    Phase.FOOTPRINTS: {"assign_footprints", "verify_pin_pad_map", "sync_pcb"},
    Phase.PCB_PLACEMENT: {"set_board_profile", "apply_placements", "inspect_board"},
    Phase.PCB_ROUTING: {"route_nets", "run_drc", "verify_board_connectivity"},
    Phase.MANUFACTURING_REVIEW: {
        "prepare_fabrication_package",
        "verify_gerber_drill_package",
        "inspect_fabrication_manifest",
    },
    Phase.REVIEW_READY: {"inspect_fabrication_manifest"},
}


class WorkflowController:
    def __init__(
        self,
        workspace: Path,
        *,
        operation_budget: int = 100,
        backend: DesignBackend | None = None,
        schematic_review: SchematicReviewService | None = None,
        require_visual_schematic_review: bool = True,
    ):
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.state_path = self.workspace / "controller-state.json"
        self.handoff_path = self.workspace / "phase-handoff.json"
        self.trace_path = self.workspace / "traces.jsonl"
        self.revisions = RevisionStore(self.workspace / "design-store")
        self.operation_budget = operation_budget
        self.backend = backend
        self.schematic_review = schematic_review
        self.require_visual_schematic_review = require_visual_schematic_review
        self.tools: dict[str, Tool] = {}
        self._register_builtin_tools()
        if backend is not None:
            self._attach_backend_tools()
        if schematic_review is not None:
            self._attach_schematic_review_tool()
        if not self.state_path.is_file():
            self._save_state(
                {
                    "phase": Phase.REQUIREMENTS,
                    "design_id": None,
                    "revision_id": None,
                    "gates": {},
                    "checkpoints": {},
                    "operations": 0,
                    "idempotency": {},
                    "unresolved_issues": [],
                }
            )

    def _state(self) -> dict:
        return json.loads(self.state_path.read_text())

    def _save_state(self, state: dict) -> None:
        descriptor, temporary = tempfile.mkstemp(prefix="state-", dir=self.workspace, text=True)
        try:
            os.write(descriptor, (json.dumps(state, indent=2) + "\n").encode())
            os.fsync(descriptor)
            os.close(descriptor)
            os.replace(temporary, self.state_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def confined_path(self, value: str, *, must_exist: bool = False) -> Path:
        path = Path(value)
        lexical = self.workspace / path if not path.is_absolute() else path
        candidate = lexical.resolve()
        if not candidate.is_relative_to(self.workspace):
            raise ControllerError("path escapes designated workspace")
        relative = lexical.absolute().relative_to(self.workspace)
        cursor = self.workspace
        if any((cursor := cursor / part).is_symlink() for part in relative.parts):
            raise ControllerError("workspace paths may not traverse symlinks")
        if must_exist and not candidate.exists():
            raise ControllerError("path is absent or resolves through a symlink")
        return candidate

    def visible_tools(self, task_tools: set[str] | None = None) -> list[dict]:
        state = self._state()
        names = ALWAYS | PHASE_TOOLS[Phase(state["phase"])]
        if task_tools is not None:
            names = ALWAYS | (names & task_tools)
        return [
            {
                "name": tool.name,
                **(
                    {"description": "This operation is not implemented by the configured backend."}
                    if not tool.implemented
                    else {}
                ),
                "inputSchema": {
                    **tool.schema,
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "$id": (
                        "https://schemas.ai-kicad-designer.local/mcp/"
                        f"{tool.name}.v1.json"
                    ),
                },
            }
            for name in sorted(names)
            if (tool := self.tools.get(name)) is not None
        ]

    def dispatch(self, name: str, arguments: dict, *, trace_id: str | None = None) -> dict:
        tool = self.tools.get(name)
        if tool is None or not tool.write:
            return self._dispatch(name, arguments, trace_id=trace_id)
        key = arguments.get("idempotency_key")
        if key:
            prior = self._state().get("idempotency", {}).get(key)
            if prior:
                if prior["status"] == "COMPLETED":
                    return prior["response"]
                return {
                    "status": "RECONCILIATION_REQUIRED",
                    "idempotency_key": key,
                    "state": prior["status"],
                    "mutation_occurred": "unknown",
                }
        with self.revisions.writer(f"tool:{name}:{key or 'missing'}"):
            return self._dispatch(name, arguments, trace_id=trace_id)

    def _dispatch(self, name: str, arguments: dict, *, trace_id: str | None = None) -> dict:
        state = self._state()
        trace_id = trace_id or secrets.token_hex(12)
        if state["operations"] >= self.operation_budget:
            raise BudgetExceeded("tool-call budget exhausted")
        tool = self.tools.get(name)
        if tool is None:
            raise ControllerError("unknown tool")
        phase = Phase(state["phase"])
        if name not in ALWAYS and name not in PHASE_TOOLS[phase]:
            raise NotAuthorized(f"{name} is not authorized in {phase}")
        required = set(tool.schema.get("required", []))
        if missing := required - set(arguments):
            raise ControllerError(f"missing required arguments: {sorted(missing)}")
        if tool.write:
            expected = arguments.get("expected_revision")
            if expected != state["revision_id"]:
                raise StaleRevision("write expected_revision is stale")
        idempotency_key = arguments.get("idempotency_key")
        if tool.write and not idempotency_key:
            raise ControllerError("idempotency_key is required for every write")
        if not tool.implemented:
            raise UnsupportedTool(f"{name} is not implemented by the configured backend")
        if tool.write and idempotency_key in state["idempotency"]:
            previous = state["idempotency"][idempotency_key]
            if previous["status"] == "COMPLETED":
                return previous["response"]
            return {
                "status": "RECONCILIATION_REQUIRED",
                "idempotency_key": idempotency_key,
                "state": previous["status"],
                "mutation_occurred": "unknown",
            }
        state["operations"] += 1
        if tool.write:
            state["idempotency"][idempotency_key] = {
                "status": "IN_PROGRESS",
                "tool": name,
                "expected_revision": arguments.get("expected_revision"),
            }
        self._save_state(state)
        try:
            response = tool.handler(arguments)
            response.setdefault("trace_id", trace_id)
            response.setdefault(
                "mutation_occurred", tool.write and not arguments.get("dry_run", False)
            )
            if tool.write and idempotency_key:
                state = self._state()
                if response.get("mutation_occurred") and response.get("new_revision_id"):
                    if response["source_revision"] != state["revision_id"]:
                        raise StaleRevision("backend result no longer matches current revision")
                    state["revision_id"] = response["new_revision_id"]
                state["idempotency"][idempotency_key] = {
                    "status": "COMPLETED",
                    "response": response,
                }
                self._save_state(state)
            self._trace(trace_id, name, arguments, "PASS")
            return response
        except Exception as exc:
            if tool.write and idempotency_key:
                state = self._state()
                state["idempotency"][idempotency_key] = {
                    "status": "UNCERTAIN",
                    "tool": name,
                    "error": type(exc).__name__,
                    "expected_revision": arguments.get("expected_revision"),
                }
                self._save_state(state)
            self._trace(trace_id, name, {"keys": sorted(arguments)}, type(exc).__name__)
            raise

    def _trace(self, trace_id: str, name: str, arguments: dict, status: str) -> None:
        redacted = {
            key: ("[REDACTED]" if re.search(r"token|secret|password", key, re.I) else value)
            for key, value in arguments.items()
        }
        with self.trace_path.open("a") as stream:
            stream.write(
                json.dumps(
                    {"trace_id": trace_id, "tool": name, "arguments": redacted, "status": status}
                )
                + "\n"
            )

    def set_revision(self, design_id: str, revision_id: str) -> None:
        state = self._state()
        state["design_id"] = design_id
        state["revision_id"] = revision_id
        self._save_state(state)

    def record_gate(self, gate: str, status: str, revision_id: str) -> None:
        state = self._state()
        if revision_id != state["revision_id"]:
            raise StaleRevision("gate result targets stale revision")
        state["gates"][gate] = {"status": status, "revision_id": revision_id}
        self._save_state(state)

    def persist_handoff(self, task: str, provider: Provider | None = None) -> dict:
        state = self._state()
        handoff = {
            "task": task,
            "design_id": state["design_id"],
            "revision_id": state["revision_id"],
            "phase": state["phase"],
            "validation": state["gates"],
            "unresolved_issues": state["unresolved_issues"],
            "provider": provider.provider_id if provider else None,
        }
        if provider:
            handoff["provider_result"] = provider.complete(handoff)
        self.handoff_path.write_text(json.dumps(handoff, indent=2) + "\n")
        return handoff

    def _register_builtin_tools(self) -> None:
        object_schema = {"type": "object", "properties": {}, "additionalProperties": False}

        def register(
            name: str,
            phase: Phase | None,
            write: bool,
            schema: dict,
            handler,
            *,
            implemented: bool = True,
        ):
            self.tools[name] = Tool(name, phase, write, schema, handler, implemented)

        register("get_design_state", None, False, object_schema, lambda _: self._state())
        register(
            "get_capabilities",
            None,
            False,
            object_schema,
            lambda _: DIRECT_PILOT_MANIFEST.model_dump(mode="json"),
        )
        register(
            "get_validation_report",
            None,
            False,
            object_schema,
            lambda _: {"gates": self._state()["gates"]},
        )
        write_properties = {
            "expected_revision": {"type": ["string", "null"]},
            "idempotency_key": {"type": "string"},
            "dry_run": {"type": "boolean", "default": False},
        }
        transition_schema = {
            "type": "object",
            "properties": {**write_properties, "target_phase": {"type": "string"}},
            "required": ["expected_revision", "target_phase", "idempotency_key"],
            "additionalProperties": False,
        }
        register(
            "request_phase_transition",
            None,
            True,
            transition_schema,
            self._transition,
        )
        checkpoint_schema = {
            "type": "object",
            "properties": {**write_properties, "name": {"type": "string"}},
            "required": ["expected_revision", "name", "idempotency_key"],
            "additionalProperties": False,
        }
        register("create_checkpoint", None, True, checkpoint_schema, self._checkpoint)
        register("rollback_to_checkpoint", None, True, checkpoint_schema, self._rollback)
        for phase, names in PHASE_TOOLS.items():
            for name in names:
                write = not name.startswith(("get_", "inspect_", "verify_", "run_", "check_"))
                schema = (
                    {
                        "type": "object",
                        "properties": write_properties,
                        "required": (["expected_revision", "idempotency_key"] if write else []),
                        "additionalProperties": True,
                    }
                    if write
                    else {"type": "object", "properties": {}, "additionalProperties": True}
                )
                register(
                    name,
                    phase,
                    write,
                    schema,
                    lambda _: {},
                    implemented=False,
                )
        self.tools["define_requirements"] = Tool(
            "define_requirements",
            Phase.REQUIREMENTS,
            True,
            {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "expected_revision": {"type": ["string", "null"]},
                    "idempotency_key": {"type": "string"},
                    "dry_run": {"type": "boolean"},
                },
                "required": ["description", "expected_revision", "idempotency_key"],
                "additionalProperties": False,
            },
            self._define_requirements,
        )

    def _attach_schematic_review_tool(self) -> None:
        self.tools["review_schematic"] = Tool(
            "review_schematic",
            Phase.SCHEMATIC,
            True,
            {
                "type": "object",
                "properties": {
                    "design": {"type": "string"},
                    "output": {"type": "string"},
                    "expected_revision": {"type": ["string", "null"]},
                    "idempotency_key": {"type": "string"},
                },
                "required": ["design", "output", "expected_revision", "idempotency_key"],
                "additionalProperties": False,
            },
            self._review_schematic,
            timeout_seconds=self.schematic_review.timeout_seconds,
        )

    def _review_schematic(self, request: dict) -> dict:
        """Run the bounded visual loop and bind its outcome to the current revision."""
        assert self.schematic_review is not None
        design = self.confined_path(request["design"], must_exist=True)
        output = self.confined_path(request["output"])
        if output.exists():
            raise ControllerError("review output already exists")
        revision = self._state()["revision_id"]
        self._require_design_matches_revision(design, revision)
        result = self.schematic_review.review(design, output)
        accepted = result.get("status") == "ACCEPTED_FOR_REVIEW" and bool(
            result.get("accepted_schematic")
        )
        state = self._state()
        if state["revision_id"] != revision:
            raise StaleRevision("schematic review finished after a revision change")
        gate = {
            "status": "PASS" if accepted else "FAIL",
            "revision_id": revision,
            "review_status": result.get("status"),
            "accepted_schematic": (
                str(output / result["accepted_schematic"]) if accepted else None
            ),
            "result": str(output / "result.json"),
        }
        state["gates"][VISUAL_REVIEW_GATE] = gate
        if not accepted:
            state["unresolved_issues"].append(
                {
                    "gate": VISUAL_REVIEW_GATE,
                    "revision_id": revision,
                    "reason": result.get("reason"),
                }
            )
        self._save_state(state)
        return {"status": gate["status"], "gate": gate, "review": result}

    def _require_design_matches_revision(self, design: Path, revision: str) -> None:
        """The reviewed circuit must be the current revision's canonical circuit."""
        model = DesignModel.model_validate_json(
            (self.revisions.revision_path(revision) / "design.json").read_text()
        )
        canonical_refs = {item.component_id: item.reference for item in model.components}
        legacy = json.loads(design.read_text())
        legacy_refs = {item["id"]: item["refdes"] for item in legacy["components"]}
        canonical = (
            {item.reference: item.value for item in model.components},
            {
                frozenset(f"{canonical_refs[t.component_id]}.{t.pin}" for t in net.terminals)
                for net in model.nets
            },
        )
        reviewed = (
            {item["refdes"]: item["value"] for item in legacy["components"]},
            {
                frozenset(f"{legacy_refs[component]}.{pin}" for component, pin in net["members"])
                for net in legacy["nets"]
            },
        )
        if reviewed != canonical:
            raise ControllerError(
                "review design does not match the current revision's components, values or nets"
            )

    def _define_requirements(self, request: dict) -> dict:
        assessment = assess_requirements(request["description"])
        if request.get("dry_run", False):
            return assessment | {"mutation_occurred": False}
        state = self._state()
        state["requirement_assessment"] = {
            "source_text": request["description"],
            **assessment,
        }
        self._save_state(state)
        return assessment | {"mutation_occurred": True}

    def _attach_backend_tools(self) -> None:
        assert self.backend is not None

        def backend_call(operation: str, request: dict) -> dict:
            return self.backend.call(
                operation,
                {
                    key: value
                    for key, value in request.items()
                    if key not in {"expected_revision", "idempotency_key", "dry_run"}
                }
                | ({"dry_run": request["dry_run"]} if "dry_run" in request else {}),
            )

        path_properties = {
            "source": {"type": "string"},
            "output": {"type": "string"},
        }
        for name, operation in (("run_erc", "run_erc"), ("run_drc", "run_drc")):
            existing = self.tools[name]
            self.tools[name] = Tool(
                name,
                existing.phase,
                False,
                {
                    "type": "object",
                    "properties": path_properties,
                    "required": ["source", "output"],
                    "additionalProperties": False,
                },
                lambda request, selected=operation: backend_call(selected, request),
            )
        existing = self.tools["create_schematic"]
        self.tools["create_schematic"] = Tool(
            existing.name,
            existing.phase,
            True,
            {
                "type": "object",
                "properties": {
                    "design": {"type": "string"},
                    "bom": {"type": "string"},
                    "footprint_lock": {"type": "string"},
                    "board_profile": {"type": "string"},
                    "design_model": {"type": "string"},
                    "toolchain_lock": {"type": "string"},
                    "output": {"type": "string"},
                    "expected_revision": {"type": ["string", "null"]},
                    "idempotency_key": {"type": "string"},
                    "dry_run": {"type": "boolean"},
                },
                "required": [
                    "design", "bom", "footprint_lock", "board_profile", "design_model",
                    "toolchain_lock", "output", "expected_revision", "idempotency_key",
                ],
                "additionalProperties": False,
            },
            lambda request: self.backend.call(
                "create_schematic",
                {key: value for key, value in request.items() if key != "idempotency_key"},
            ),
        )
        existing = self.tools["verify_pin_pad_map"]
        self.tools["verify_pin_pad_map"] = Tool(
            existing.name,
            existing.phase,
            False,
            {
                "type": "object",
                "properties": {
                    "design_model": {"type": "string"},
                    "footprint_root": {"type": "string"},
                },
                "required": ["design_model", "footprint_root"],
                "additionalProperties": False,
            },
            lambda request: self.backend.call("verify_pin_pad_map", request),
        )
        existing = self.tools["assign_footprints"]
        self.tools["assign_footprints"] = Tool(
            existing.name,
            existing.phase,
            True,
            {
                "type": "object",
                "properties": {
                    "design_model": {"type": "string"},
                    "footprint_root": {"type": "string"},
                    "output": {"type": "string"},
                    "assignments": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "component_id": {"type": "string"},
                                "footprint": {"type": "string"},
                                "pin_pad_map": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "pin": {"type": "string"},
                                            "pad": {"type": "string"},
                                        },
                                        "required": ["pin", "pad"],
                                        "additionalProperties": False,
                                    },
                                },
                            },
                            "required": ["component_id", "footprint", "pin_pad_map"],
                            "additionalProperties": False,
                        },
                    },
                    "expected_revision": {"type": ["string", "null"]},
                    "idempotency_key": {"type": "string"},
                    "dry_run": {"type": "boolean"},
                },
                "required": [
                    "design_model", "footprint_root", "output", "assignments",
                    "expected_revision", "idempotency_key",
                ],
                "additionalProperties": False,
            },
            lambda request: self.backend.call(
                "assign_footprints",
                {key: value for key, value in request.items() if key != "idempotency_key"},
            ),
        )
        existing = self.tools["sync_pcb"]
        self.tools["sync_pcb"] = Tool(
            existing.name,
            existing.phase,
            True,
            {
                "type": "object",
                "properties": {
                    "schematic": {"type": "string"},
                    "source_design": {"type": "string"},
                    "bom": {"type": "string"},
                    "footprint_lock": {"type": "string"},
                    "board_profile": {"type": "string"},
                    "candidate": {"type": "string"},
                    "output": {"type": "string"},
                    "design_model": {"type": "string"},
                    "netlist": {"type": "string"},
                    "drc_report": {"type": "string"},
                    "candidate_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                    "expected_revision": {"type": ["string", "null"]},
                    "idempotency_key": {"type": "string"},
                    "dry_run": {"type": "boolean"},
                },
                "required": [
                    "schematic", "source_design", "bom", "footprint_lock", "board_profile",
                    "candidate", "output", "design_model", "netlist", "drc_report",
                    "candidate_sha256", "expected_revision", "idempotency_key",
                ],
                "additionalProperties": False,
            },
            lambda request: self.backend.call(
                "sync_pcb",
                {key: value for key, value in request.items() if key != "idempotency_key"},
            ),
        )
        existing = self.tools["apply_placements"]
        self.tools["apply_placements"] = Tool(
            existing.name,
            existing.phase,
            True,
            {
                "type": "object",
                "properties": {
                    **path_properties,
                    "plan": {"type": "object"},
                    "expected_revision": {"type": ["string", "null"]},
                    "idempotency_key": {"type": "string"},
                    "dry_run": {"type": "boolean"},
                },
                "required": [
                    "source",
                    "output",
                    "plan",
                    "expected_revision",
                    "idempotency_key",
                ],
                "additionalProperties": False,
            },
            lambda request: self.backend.call(
                "apply_placements",
                {
                    "source": request["source"],
                    "output": request["output"],
                    "plan": request["plan"],
                    "expected_revision": request["expected_revision"],
                    **({"dry_run": request["dry_run"]} if "dry_run" in request else {}),
                },
            ),
        )
        existing = self.tools["route_nets"]
        self.tools["route_nets"] = Tool(
            existing.name,
            existing.phase,
            True,
            {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "candidate": {"type": "string"},
                    "output": {"type": "string"},
                    "design_model": {"type": "string"},
                    "drc_report": {"type": "string"},
                    "candidate_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                    "expected_revision": {"type": ["string", "null"]},
                    "idempotency_key": {"type": "string"},
                    "dry_run": {"type": "boolean"},
                },
                "required": [
                    "source",
                    "candidate",
                    "output",
                    "design_model",
                    "drc_report",
                    "candidate_sha256",
                    "expected_revision",
                    "idempotency_key",
                ],
                "additionalProperties": False,
            },
            lambda request: self.backend.call(
                "route_nets",
                {
                    key: request[key]
                    for key in (
                        "source",
                        "candidate",
                        "output",
                        "design_model",
                        "drc_report",
                        "candidate_sha256",
                        "expected_revision",
                        "dry_run",
                    )
                    if key in request
                },
            ),
        )
        existing = self.tools["prepare_fabrication_package"]
        self.tools["prepare_fabrication_package"] = Tool(
            existing.name,
            existing.phase,
            True,
            {
                "type": "object",
                "properties": {
                    **path_properties,
                    "expected_revision": {"type": ["string", "null"]},
                    "idempotency_key": {"type": "string"},
                    "dry_run": {"type": "boolean"},
                },
                "required": ["source", "output", "expected_revision", "idempotency_key"],
                "additionalProperties": False,
            },
            lambda request: backend_call("export_fabrication", request),
        )

    def _transition(self, request: dict) -> dict:
        state = self._state()
        current = Phase(state["phase"])
        target = Phase(request["target_phase"])
        current_index = PHASES.index(current)
        target_index = PHASES.index(target)
        if target_index == current_index:
            return {"status": "unchanged", "phase": current}
        if target_index == current_index + 1:
            required_gates = [REQUIRED_GATE[target]]
            if self.require_visual_schematic_review:
                required_gates += ADDITIONAL_REQUIRED_GATES.get(target, ())
            for required in required_gates:
                gate = state["gates"].get(required) or {}
                if gate.get("status") != "PASS" or gate.get("revision_id") != state["revision_id"]:
                    raise NotAuthorized(f"transition requires current PASS gate {required}")
        elif target_index > current_index + 1:
            raise NotAuthorized("phase transitions cannot skip forward")
        if request.get("dry_run"):
            return {"status": "plan_valid", "phase": current, "target_phase": target}
        if target_index < current_index:
            invalidated = {
                required
                for phase, required in REQUIRED_GATE.items()
                if PHASES.index(phase) > target_index
            } | {
                required
                for phase, gates in ADDITIONAL_REQUIRED_GATES.items()
                if PHASES.index(phase) > target_index
                for required in gates
            }
            state["gates"] = {
                name: result for name, result in state["gates"].items() if name not in invalidated
            }
        state["phase"] = target
        self._save_state(state)
        return {"status": "applied", "phase": target}

    def _checkpoint(self, request: dict) -> dict:
        state = self._state()
        if request.get("dry_run"):
            return {"status": "plan_valid", "name": request["name"]}
        state["checkpoints"][request["name"]] = state["revision_id"]
        self._save_state(state)
        return {"status": "applied", "revision_id": state["revision_id"]}

    def _rollback(self, request: dict) -> dict:
        state = self._state()
        target = state["checkpoints"].get(request["name"])
        if target is None:
            raise ControllerError("unknown checkpoint")
        if request.get("dry_run"):
            return {"status": "plan_valid", "target_revision": target}
        self.revisions.rollback(target, expected_revision=state["revision_id"])
        state["revision_id"] = target
        state["gates"] = {}
        self._save_state(state)
        return {"status": "applied", "revision_id": target}
