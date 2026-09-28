"""Typed M2 proof conflicts and the repair classes they permit."""

from __future__ import annotations

from enum import Enum

from .ir import InputError


class ConflictKind(str, Enum):
    PRECEDENCE = "precedence_violation"
    LOCAL_SPAN = "local_span_violation"
    BLOCKED_GATEWAY = "blocked_gateway"
    ROUTE_BUDGET = "route_budget"
    CANONICAL_LENGTH = "canonical_net_length"
    NET_CONNECTIVITY = "net_connectivity"
    GATEWAY_WITNESS = "gateway_witness"
    DANGLING_ENDPOINT = "dangling_endpoint"
    JUNCTION = "junction"
    OWNERSHIP = "ownership"
    COLLISION = "collision"
    RESERVATION = "reservation"
    PAGE_SPREAD = "page_spread"
    SERIALIZATION = "serialization"


class TypedConflict(InputError):
    """Machine-readable failure with retained human diagnostic text."""

    def __init__(
        self,
        category: ConflictKind,
        message: str,
        *,
        obligation: str | None = None,
        net: str | None = None,
        owners: tuple[str, ...] = (),
        offending_geometry: tuple = (),
        actual: int | None = None,
        limit: int | None = None,
        lower_bound: int | None = None,
        decisions: tuple[str, ...] = (),
        repair_classes: tuple[str, ...] = (),
    ) -> None:
        self.category = category
        self.kind = category.value
        self.obligation = obligation
        self.net = net
        self.owners = owners
        self.offending_geometry = offending_geometry
        self.actual = actual
        self.limit = limit
        self.lower_bound = lower_bound
        self.decisions = decisions
        self.repair_classes = repair_classes
        super().__init__(message)
