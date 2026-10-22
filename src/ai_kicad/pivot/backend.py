"""Capability-negotiated backend contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import Field

from .evidence import StrictModel


class SupportLevel(StrEnum):
    VERIFIED = "verified"
    EXPERIMENTAL = "experimental"
    UNSUPPORTED = "unsupported"


class RuntimeMode(StrEnum):
    HEADLESS = "headless"
    GUI = "gui"
    EITHER = "either"


class Capability(StrictModel):
    operation: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    support: SupportLevel
    runtime: RuntimeMode
    kicad_versions: list[str]
    transactional: bool
    rollback: bool
    notes: list[str] = Field(default_factory=list)


class BackendManifest(StrictModel):
    backend_id: str = Field(min_length=1)
    backend_version: str = Field(min_length=1)
    capabilities: list[Capability]

    def capability(
        self, operation: str, *, required: SupportLevel = SupportLevel.VERIFIED
    ) -> Capability:
        matches = [item for item in self.capabilities if item.operation == operation]
        if len(matches) != 1:
            raise UnsupportedCapability(operation, "operation is not uniquely declared")
        capability = matches[0]
        if required is SupportLevel.VERIFIED and capability.support is not SupportLevel.VERIFIED:
            raise UnsupportedCapability(operation, f"required verified, found {capability.support}")
        if capability.support is SupportLevel.UNSUPPORTED:
            raise UnsupportedCapability(operation, "backend declares operation unsupported")
        return capability


class BackendError(RuntimeError):
    code = "BACKEND_UNAVAILABLE"

    def __init__(self, operation: str, detail: str, *, mutation_occurred: bool = False):
        super().__init__(detail)
        self.operation = operation
        self.detail = detail
        self.mutation_occurred = mutation_occurred

    def response(self) -> dict:
        return {
            "status": "error",
            "error": {
                "code": self.code,
                "scope": self.operation,
                "detail": self.detail,
                "mutation_occurred": self.mutation_occurred,
                "recommended_recovery": "Inspect the exact revision and capability manifest.",
            },
        }


class UnsupportedCapability(BackendError):
    code = "UNSUPPORTED_CAPABILITY"


class DesignBackend(Protocol):
    manifest: BackendManifest

    def call(self, operation: str, request: dict) -> dict: ...


DIRECT_PILOT_MANIFEST = BackendManifest(
    backend_id="direct-kicad-v0",
    backend_version="design-backend.v1",
    capabilities=[
        Capability(
            operation="create_schematic",
            schema_version="schematic.create.v1",
            support=SupportLevel.VERIFIED,
            runtime=RuntimeMode.HEADLESS,
            kicad_versions=["10.0.6"],
            transactional=True,
            rollback=True,
            notes=["preserved M2b compiler, locked toolchain, ERC, exported netlist and independent comparison"],
        ),
        Capability(
            operation="create_project",
            schema_version="project.create.v1",
            support=SupportLevel.VERIFIED,
            runtime=RuntimeMode.HEADLESS,
            kicad_versions=["10.0.6"],
            transactional=True,
            rollback=True,
        ),
        Capability(
            operation="apply_schematic_transaction",
            schema_version="schematic.transaction.v1",
            support=SupportLevel.VERIFIED,
            runtime=RuntimeMode.HEADLESS,
            kicad_versions=["10.0.6"],
            transactional=True,
            rollback=True,
            notes=["structured native file candidate plus independent parse/readback"],
        ),
        Capability(
            operation="apply_placements",
            schema_version="placement.apply.v1",
            support=SupportLevel.VERIFIED,
            runtime=RuntimeMode.HEADLESS,
            kicad_versions=["10.0.6"],
            transactional=True,
            rollback=True,
            notes=["revision-bound native-board candidate; atomic write to a new output path"],
        ),
        Capability(
            operation="assign_footprints",
            schema_version="footprint.assign.v1",
            support=SupportLevel.VERIFIED,
            runtime=RuntimeMode.HEADLESS,
            kicad_versions=["10.0.6"],
            transactional=True,
            rollback=True,
            notes=["revision-bound approved footprint files and complete pin/pad maps"] ,
        ),
        Capability(
            operation="verify_pin_pad_map",
            schema_version="pin-pad-map.verify.v1",
            support=SupportLevel.VERIFIED,
            runtime=RuntimeMode.HEADLESS,
            kicad_versions=["10.0.6"],
            transactional=False,
            rollback=False,
            notes=["checks locked footprint bytes, all symbol pins, unique pads and pin-one identity"],
        ),
        Capability(
            operation="sync_pcb",
            schema_version="pcb.sync-import.v1",
            support=SupportLevel.EXPERIMENTAL,
            runtime=RuntimeMode.HEADLESS,
            kicad_versions=["10.0.6"],
            transactional=True,
            rollback=True,
            notes=[
                "imports a separately synchronized board after exact schematic, model, footprint, pad/net partition and DRC checks; does not synthesize footprints"
            ],
        ),
        Capability(
            operation="route_nets",
            schema_version="router.import.v1",
            support=SupportLevel.EXPERIMENTAL,
            runtime=RuntimeMode.HEADLESS,
            kicad_versions=["10.0.6"],
            transactional=True,
            rollback=True,
            notes=[
                "imports a separately produced route candidate after revision, geometry, netlist, DRC and connectivity checks; does not implement a general autorouter"
            ],
        ),
        Capability(
            operation="run_erc",
            schema_version="verification.erc.v1",
            support=SupportLevel.VERIFIED,
            runtime=RuntimeMode.HEADLESS,
            kicad_versions=["10.0.6"],
            transactional=False,
            rollback=False,
        ),
        Capability(
            operation="run_drc",
            schema_version="verification.drc.v1",
            support=SupportLevel.VERIFIED,
            runtime=RuntimeMode.HEADLESS,
            kicad_versions=["10.0.6"],
            transactional=False,
            rollback=False,
        ),
        Capability(
            operation="export_fabrication",
            schema_version="manufacturing.export.v1",
            support=SupportLevel.VERIFIED,
            runtime=RuntimeMode.HEADLESS,
            kicad_versions=["10.0.6"],
            transactional=False,
            rollback=False,
        ),
        Capability(
            operation="native_schematic_ipc",
            schema_version="schematic.ipc.experimental.v1",
            support=SupportLevel.EXPERIMENTAL,
            runtime=RuntimeMode.HEADLESS,
            kicad_versions=["10.99.0 development snapshot"],
            transactional=True,
            rollback=True,
        ),
    ],
)
