"""Contract tests for the versioned owner readability brief."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_kicad.pivot.schematic_review_brief import (
    SchematicReviewBrief,
    SchematicReviewBriefV2,
    format_review_brief,
    load_review_brief,
    resolve_review_brief,
)

ROOT = Path(__file__).resolve().parents[2]
BRIEF_PATH = ROOT / "fixtures/pivot/schematic_review_brief_v1.json"
SCHEMA_PATH = ROOT / "fixtures/pivot/schematic_review_brief.v1.schema.json"
BRIEF_V2_PATH = ROOT / "fixtures/pivot/schematic_review_brief_v2.json"
SCHEMA_V2_PATH = ROOT / "fixtures/pivot/schematic_review_brief.v2.schema.json"


def test_review_brief_schema_matches_typed_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    expected = SchematicReviewBrief.model_json_schema()
    expected["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    expected["$id"] = "https://ai-kicad-designer.local/schemas/schematic-review-brief.v1.json"
    assert schema == expected


def test_owner_brief_maps_each_preference_to_measurement_or_visual_rubric() -> None:
    brief = load_review_brief(BRIEF_PATH)
    criteria = {item.criterion_id: item for item in brief.criteria}
    assert set(criteria) == {"label_association", "page_composition", "visible_local_rails"}
    assert all(item.measurements or item.visual_rubric for item in brief.criteria)
    assert (
        next(
            item.threshold
            for item in criteria["label_association"].measurements
            if item.check_id == "field_locality"
        )
        == 25.4
    )
    assert (
        next(
            item.qualification
            for item in criteria["page_composition"].measurements
            if item.check_id == "observed_page_utilization"
        )
        == "profile_target"
    )
    assert criteria["visible_local_rails"].qualification_status == "not_yet_qualified"


def test_review_prompt_preserves_unqualified_visual_limits() -> None:
    prompt = format_review_brief(load_review_brief(BRIEF_PATH))
    assert "label_association" in prompt
    assert "visible_local_rails" in prompt
    assert "not_yet_qualified" in prompt
    assert "profile_target" in prompt
    assert "do not replace image review" in prompt


def test_brief_rejects_missing_owner_criterion() -> None:
    data = json.loads(BRIEF_PATH.read_text())
    data["criteria"] = data["criteria"][:-1]
    with pytest.raises(ValidationError, match="at least 3 items"):
        SchematicReviewBrief.model_validate(data)


def test_brief_rejects_unmapped_visual_preference() -> None:
    data = json.loads(BRIEF_PATH.read_text())
    data["criteria"][0]["visual_rubric"] = []
    with pytest.raises(ValidationError):
        SchematicReviewBrief.model_validate(data)


def test_versioned_brief_controls_locality_gate() -> None:
    maximum, prompt = resolve_review_brief(BRIEF_PATH, None)
    assert maximum == 25.4
    assert prompt is not None and "field_locality" in prompt


def test_versioned_brief_rejects_conflicting_locality_override() -> None:
    with pytest.raises(ValueError, match="conflicts with the versioned review brief"):
        resolve_review_brief(BRIEF_PATH, 20.0)


def test_v2_review_brief_schema_matches_typed_contract() -> None:
    schema = json.loads(SCHEMA_V2_PATH.read_text())
    expected = SchematicReviewBriefV2.model_json_schema()
    expected["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    expected["$id"] = "https://ai-kicad-designer.local/schemas/schematic-review-brief.v2.json"
    assert schema == expected


def test_v2_review_brief_adds_independent_owner_association_gate() -> None:
    brief = load_review_brief(BRIEF_V2_PATH)
    assert isinstance(brief, SchematicReviewBriefV2)
    labels = next(item for item in brief.criteria if item.criterion_id == "label_association")
    owner_gate = next(
        item for item in labels.measurements if item.check_id == "field_owner_association"
    )
    assert owner_gate.threshold == 5.08
    assert owner_gate.qualification == "independent_gate"


def test_v2_review_brief_rejects_missing_owner_association_gate() -> None:
    data = json.loads(BRIEF_V2_PATH.read_text())
    data["criteria"][0]["measurements"] = [
        item
        for item in data["criteria"][0]["measurements"]
        if item["check_id"] != "field_owner_association"
    ]
    with pytest.raises(ValidationError, match="owner checks"):
        SchematicReviewBriefV2.model_validate(data)
