"""Versioned visual review briefs and their human/model-readable prompt."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .evidence import StrictModel


class ReviewMeasurement(StrictModel):
    """A reported measurable constraint, with its qualification level explicit."""

    check_id: str = Field(min_length=1)
    operator: Literal["<=", ">=", "=="]
    threshold: float = Field(ge=0, allow_inf_nan=False)
    unit: str = Field(min_length=1)
    source: str = Field(min_length=1)
    qualification: Literal["independent_gate", "profile_target"]


class ReviewCriterion(StrictModel):
    """One owner-facing requirement and the machine/rubric evidence for it."""

    criterion_id: Literal["label_association", "page_composition", "visible_local_rails"]
    requirement: str = Field(min_length=1)
    measurements: list[ReviewMeasurement]
    visual_rubric: list[str] = Field(min_length=1)
    qualification_status: Literal["qualified", "not_yet_qualified"]
    limitation: str = Field(min_length=1)


class SchematicReviewBrief(StrictModel):
    """Owner-readable criteria sent with the exact images under review."""

    schema_version: Literal["schematic-review-brief.v1"]
    brief_id: Literal["owner-readability.v1"]
    scope: str = Field(min_length=1)
    source_documents: list[str] = Field(min_length=1)
    criteria: list[ReviewCriterion] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def require_all_owner_criteria(self) -> SchematicReviewBrief:
        ids = [criterion.criterion_id for criterion in self.criteria]
        expected = {"label_association", "page_composition", "visible_local_rails"}
        if set(ids) != expected or len(ids) != len(expected):
            raise ValueError("review brief must define each owner criterion exactly once")
        labels = next(item for item in self.criteria if item.criterion_id == "label_association")
        if not {"field_locality", "field_separation"}.issubset(
            {measurement.check_id for measurement in labels.measurements}
        ):
            raise ValueError("label association requires locality and field-separation checks")
        return self


class SchematicReviewBriefV2(SchematicReviewBrief):
    """Owner readability brief with an independent gross ownership mismatch gate."""

    schema_version: Literal["schematic-review-brief.v2"]
    brief_id: Literal["owner-readability.v2"]

    @model_validator(mode="after")
    def require_owner_association_gate(self) -> SchematicReviewBriefV2:
        labels = next(item for item in self.criteria if item.criterion_id == "label_association")
        required = {"field_locality", "field_separation", "field_owner_association"}
        if not required.issubset({measurement.check_id for measurement in labels.measurements}):
            raise ValueError("v2 label association requires locality, separation, and owner checks")
        rails = next(item for item in self.criteria if item.criterion_id == "visible_local_rails")
        if "visible_rail_continuity" not in {
            measurement.check_id for measurement in rails.measurements
        }:
            raise ValueError("v2 visible rails require an independent wire-continuity check")
        return self


class SchematicReviewBriefV3(SchematicReviewBrief):
    """Owner brief that accepts conventional power symbols as rail presentation."""

    schema_version: Literal["schematic-review-brief.v3"]
    brief_id: Literal["owner-readability.v3"]

    @model_validator(mode="after")
    def require_rail_presentation_gates(self) -> SchematicReviewBriefV3:
        labels = next(item for item in self.criteria if item.criterion_id == "label_association")
        required = {"field_locality", "field_separation", "field_owner_association"}
        if not required.issubset({measurement.check_id for measurement in labels.measurements}):
            raise ValueError("v3 label association requires locality, separation, and owner checks")
        rails = next(item for item in self.criteria if item.criterion_id == "visible_local_rails")
        if not {"rail_presentation", "power_symbol_clearance"}.issubset(
            {measurement.check_id for measurement in rails.measurements}
        ):
            raise ValueError(
                "v3 rails require independent rail-presentation and power-symbol clearance checks"
            )
        return self


BRIEF_MODELS = {
    "schematic-review-brief.v2": SchematicReviewBriefV2,
    "schematic-review-brief.v3": SchematicReviewBriefV3,
}
ReviewBrief = SchematicReviewBrief | SchematicReviewBriefV2 | SchematicReviewBriefV3


def load_review_brief(path: Path) -> ReviewBrief:
    """Parse a JSON brief and reject unknown or incomplete criteria."""
    data = path.read_text()
    model = BRIEF_MODELS.get(json.loads(data).get("schema_version"), SchematicReviewBrief)
    return model.model_validate_json(data)


def brief_allows_power_symbol_rails(path: Path | None) -> bool:
    """Whether the versioned brief accepts power symbols in place of rail wiring."""
    if path is None or path.suffix.lower() != ".json":
        return False
    return isinstance(load_review_brief(path), SchematicReviewBriefV3)


def format_review_brief(brief: ReviewBrief) -> str:
    """Render a stable review prompt without presenting rubric judgment as a hard gate."""
    lines = [
        f"Review brief {brief.brief_id} ({brief.schema_version}).",
        brief.scope,
        "Machine measurements are evidence with the qualification listed; they do not replace image review.",
    ]
    for criterion in brief.criteria:
        lines.extend(("", f"{criterion.criterion_id}: {criterion.requirement}"))
        for measurement in criterion.measurements:
            lines.append(
                f"- Measurement {measurement.check_id}: {measurement.operator} "
                f"{measurement.threshold:g} {measurement.unit} "
                f"({measurement.qualification}; source: {measurement.source})."
            )
        lines.append("- Inspect the images for:")
        lines.extend(f"  - {item}" for item in criterion.visual_rubric)
        lines.append(f"- Qualification status: {criterion.qualification_status}.")
        lines.append(f"- Limitation: {criterion.limitation}")
    lines.append(
        "Report unresolved criteria as issues; do not infer a pass from ERC or netlist equivalence."
    )
    return "\n".join(lines)


def resolve_review_brief(
    path: Path | None,
    maximum_field_distance_override_mm: float | None,
) -> tuple[float, str | None]:
    """Resolve the prompt and locality gate from a JSON or freeform brief."""
    if path is None:
        maximum = (
            maximum_field_distance_override_mm
            if maximum_field_distance_override_mm is not None
            else 25.4
        )
        return maximum, None
    if path.suffix.lower() != ".json":
        maximum = (
            maximum_field_distance_override_mm
            if maximum_field_distance_override_mm is not None
            else 25.4
        )
        return maximum, path.read_text()

    brief = load_review_brief(path)
    locality = next(
        measurement
        for criterion in brief.criteria
        for measurement in criterion.measurements
        if measurement.check_id == "field_locality"
    )
    if (
        maximum_field_distance_override_mm is not None
        and maximum_field_distance_override_mm != locality.threshold
    ):
        raise ValueError("field-distance override conflicts with the versioned review brief")
    return locality.threshold, format_review_brief(brief)
