"""Independent human-readable composition metrics for M2h2 schematics.

This module is intentionally observer-shaped: it evaluates a completed placement
from semantic roles and geometric envelopes, and it does not consume production
candidate scores as proof.  The first governed use is the post-M2h2
human-readable schematic-composition remediation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Literal

from .m2_pack import MAX_CONTENT_HEIGHT, MAX_CONTENT_WIDTH
from .m2_semantics import SemanticPlan

Rect = tuple[int, int, int, int]
Point = tuple[int, int]
ViolationKind = Literal[
    "missing_block_geometry",
    "primary_stage_order_inversion",
    "input_side_violation",
    "output_side_violation",
]


@dataclass(frozen=True)
class CompositionViolation:
    """One independently witnessed composition defect."""

    kind: ViolationKind
    source: str
    target: str | None
    net: str | None
    actual_nm: int
    limit_nm: int
    witness: str

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "source": self.source,
            "target": self.target,
            "net": self.net,
            "actual_nm": self.actual_nm,
            "limit_nm": self.limit_nm,
            "witness": self.witness,
        }


@dataclass(frozen=True)
class CompositionMetrics:
    """Observable composition metrics independent of generator scoring."""

    block_count: int
    visible_block_count: int
    content_envelope_nm: Rect
    content_width_nm: int
    content_height_nm: int
    content_area_nm2: int
    utilization_ratio_ppm: int
    centroid_offset_x_nm: int
    centroid_offset_y_nm: int
    primary_stage_order_inversions: int
    cumulative_primary_reversal_nm: int
    input_side_violations: int
    output_side_violations: int

    def as_dict(self) -> dict:
        return {
            "block_count": self.block_count,
            "visible_block_count": self.visible_block_count,
            "content_envelope_nm": list(self.content_envelope_nm),
            "content_width_nm": self.content_width_nm,
            "content_height_nm": self.content_height_nm,
            "content_area_nm2": self.content_area_nm2,
            "utilization_ratio_ppm": self.utilization_ratio_ppm,
            "centroid_offset_x_nm": self.centroid_offset_x_nm,
            "centroid_offset_y_nm": self.centroid_offset_y_nm,
            "primary_stage_order_inversions": self.primary_stage_order_inversions,
            "cumulative_primary_reversal_nm": self.cumulative_primary_reversal_nm,
            "input_side_violations": self.input_side_violations,
            "output_side_violations": self.output_side_violations,
        }


@dataclass(frozen=True)
class CompositionReport:
    """Versioned observer result for one schematic candidate."""

    schema_version: str
    metrics: CompositionMetrics
    violations: tuple[CompositionViolation, ...]

    @property
    def passed(self) -> bool:
        return not self.violations

    def as_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "passed": self.passed,
            "metrics": self.metrics.as_dict(),
            "violations": [violation.as_dict() for violation in self.violations],
        }


def _center(rect: Rect) -> Point:
    return (rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2


def _content_envelope(rects: Iterable[Rect]) -> Rect:
    items = tuple(rects)
    if not items:
        return (0, 0, 0, 0)
    return (
        min(rect[0] for rect in items),
        min(rect[1] for rect in items),
        max(rect[2] for rect in items),
        max(rect[3] for rect in items),
    )


def _signal_edges(plan: SemanticPlan):
    for edge in plan.edges:
        if edge.kind in {"signal", "branch"}:
            yield edge.source, edge.target, edge.net, f"semantic-edge:{edge.kind}"
    for item in plan.precedence:
        yield item.source_fragment, item.target_fragment, item.net, f"precedence:{item.id}"


def _interface_signal_roles(plan: SemanticPlan) -> dict[str, set[str]]:
    roles: dict[str, set[str]] = {block.id: set() for block in plan.blocks}
    by_id = {block.id: block for block in plan.blocks}
    for block in plan.blocks:
        if block.kind != "interface":
            continue
        for port in block.ports:
            if port.role == "signal_in":
                roles[block.id].add("signal_in")
            elif port.role == "signal_out":
                roles[block.id].add("signal_out")
    for source, target, _net, _origin in _signal_edges(plan):
        source_block = by_id.get(source)
        target_block = by_id.get(target)
        if source_block is not None and source_block.kind == "interface":
            roles[source].add("signal_in")
        if target_block is not None and target_block.kind == "interface":
            roles[target].add("signal_out")
    return roles


def observe_human_composition(
    plan: SemanticPlan,
    block_envelopes: Mapping[str, Rect],
    *,
    envelope_width_nm: int = MAX_CONTENT_WIDTH,
    envelope_height_nm: int = MAX_CONTENT_HEIGHT,
) -> CompositionReport:
    """Evaluate first-order human-readable composition defects.

    The observer is deliberately conservative.  It currently rejects only defects
    that are semantic and geometric, not aesthetic preferences: reversed primary
    flow and directed interfaces placed on the wrong side of their owning stage.
    It also reports complexity/page-use metrics for later frozen thresholds.
    """

    violations: list[CompositionViolation] = []
    visible = {block_id: rect for block_id, rect in block_envelopes.items() if rect is not None}
    for block in plan.blocks:
        if block.id not in visible:
            violations.append(
                CompositionViolation(
                    "missing_block_geometry",
                    block.id,
                    None,
                    None,
                    0,
                    0,
                    "semantic block has no observed placement envelope",
                )
            )

    centers = {block_id: _center(rect) for block_id, rect in visible.items()}
    roles = _interface_signal_roles(plan)
    signal_edges = tuple(_signal_edges(plan))
    for source, target, net, origin in signal_edges:
        if source not in centers or target not in centers:
            continue
        source_x = centers[source][0]
        target_x = centers[target][0]
        delta = target_x - source_x
        if delta < 0:
            violations.append(
                CompositionViolation(
                    "primary_stage_order_inversion",
                    source,
                    target,
                    net,
                    delta,
                    0,
                    origin,
                )
            )
        if "signal_in" in roles.get(source, set()) and source_x > target_x:
            violations.append(
                CompositionViolation(
                    "input_side_violation",
                    source,
                    target,
                    net,
                    source_x - target_x,
                    0,
                    f"{origin}: directed input interface is right of its consumer",
                )
            )
        if "signal_out" in roles.get(target, set()) and target_x < source_x:
            violations.append(
                CompositionViolation(
                    "output_side_violation",
                    target,
                    source,
                    net,
                    source_x - target_x,
                    0,
                    f"{origin}: directed output interface is left of its producer",
                )
            )

    content = _content_envelope(visible.values())
    width = max(0, content[2] - content[0])
    height = max(0, content[3] - content[1])
    area = width * height
    allowed_area = envelope_width_nm * envelope_height_nm
    centroid = _center(content)
    metrics = CompositionMetrics(
        block_count=len(plan.blocks),
        visible_block_count=len(visible),
        content_envelope_nm=content,
        content_width_nm=width,
        content_height_nm=height,
        content_area_nm2=area,
        utilization_ratio_ppm=0 if allowed_area == 0 else (area * 1_000_000) // allowed_area,
        centroid_offset_x_nm=centroid[0] - envelope_width_nm // 2,
        centroid_offset_y_nm=centroid[1] - envelope_height_nm // 2,
        primary_stage_order_inversions=sum(
            1 for violation in violations if violation.kind == "primary_stage_order_inversion"
        ),
        cumulative_primary_reversal_nm=sum(
            abs(violation.actual_nm)
            for violation in violations
            if violation.kind == "primary_stage_order_inversion"
        ),
        input_side_violations=sum(
            1 for violation in violations if violation.kind == "input_side_violation"
        ),
        output_side_violations=sum(
            1 for violation in violations if violation.kind == "output_side_violation"
        ),
    )
    return CompositionReport(
        "m2h2.human-readable-composition.observer.1",
        metrics,
        tuple(violations),
    )


def block_envelopes_from_composition_evidence(evidence: Mapping) -> dict[str, Rect]:
    """Recover placed block envelopes from existing composition evidence.

    The evidence path lets the new observer audit already emitted candidates
    without depending on internal production candidate scores.
    """

    result: dict[str, Rect] = {}
    for item in evidence.get("variants", []):
        fragment = item.get("fragment")
        envelope = item.get("placed_envelope")
        if not isinstance(fragment, str) or not isinstance(envelope, list) or len(envelope) != 4:
            continue
        rect = tuple(int(value) for value in envelope)
        if fragment in result:
            prior = result[fragment]
            result[fragment] = (
                min(prior[0], rect[0]),
                min(prior[1], rect[1]),
                max(prior[2], rect[2]),
                max(prior[3], rect[3]),
            )
        else:
            result[fragment] = rect
    return result
