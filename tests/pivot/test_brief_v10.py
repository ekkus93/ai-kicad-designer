"""Brief v10 and its reviewer-loop profile (docs/pivot/REVIEWER_LOOP_SPEC.md R0, R5)."""

import json
from pathlib import Path

from pydantic import ValidationError
import pytest

from ai_kicad.pivot.quality_measures import DEFAULT_QUALITY_THRESHOLDS
from ai_kicad.pivot.schematic_review_brief import (
    SchematicReviewBriefV10,
    brief_requires_level_power_block,
    brief_requires_power_block,
    brief_requires_text_and_ground_checks,
    brief_review_profile,
    load_review_brief,
)
import ai_kicad.pivot.schematic_review_service as service_module
from ai_kicad.pivot.schematic_review_service import NativeSchematicReviewService

ROOT = Path(__file__).resolve().parents[2]
V9 = ROOT / "fixtures/pivot/schematic_review_brief_v9.json"
V10 = ROOT / "fixtures/pivot/schematic_review_brief_v10.json"
SCHEMA_V10 = ROOT / "fixtures/pivot/schematic_review_brief.v10.schema.json"
APPRUN = Path("/unused/AppRun")


def test_v10_brief_selects_the_spec_profile():
    profile = brief_review_profile(V10)
    assert profile.profile_id == "reviewer-loop.v10"
    assert profile.reviewer.model_dump() == {
        "svg_source": True,
        "with_images": True,
        "think": False,
        "withhold_checks": True,
        "max_actions": 4,
    }
    assert profile.edit_mode == "menu_only"
    assert profile.quality.policy == "report_only"
    assert profile.quality.thresholds == DEFAULT_QUALITY_THRESHOLDS
    assert profile.menu.model_dump() == {
        "per_class": 3,
        "total": 8,
        "optional_when_passing": 2,
        "geometric_proposals": 12,
        "native_validations": 8,
        "seconds": 20,
    }
    assert profile.refusals.equivalence_grid_mm == 1.27


def test_v10_keeps_every_v9_check_and_layout_rule():
    assert brief_requires_level_power_block(V10) and brief_requires_power_block(V10)
    assert brief_requires_text_and_ground_checks(V10)
    v9, v10 = json.loads(V9.read_text()), json.loads(V10.read_text())
    assert v10["criteria"] == v9["criteria"]


def test_v10_schema_matches_typed_contract():
    expected = SchematicReviewBriefV10.model_json_schema()
    expected["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    expected["$id"] = "https://ai-kicad-designer.local/schemas/schematic-review-brief.v10.json"
    assert json.loads(SCHEMA_V10.read_text()) == expected


def test_v10_profile_is_strict(tmp_path):
    data = json.loads(V10.read_text())
    data["review_profile"]["quality"]["thresholds"].pop("bends_added")
    path = tmp_path / "brief.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValidationError, match="quality thresholds must name exactly"):
        load_review_brief(path)
    data = json.loads(V10.read_text())
    data["review_profile"]["quality"]["policy"] = "enforce"
    path.write_text(json.dumps(data))
    with pytest.raises(ValidationError):
        load_review_brief(path)
    data = json.loads(V10.read_text())
    data["review_profile"]["edit_mode"] = "free_form"
    path.write_text(json.dumps(data))
    with pytest.raises(ValidationError):
        load_review_brief(path)


def test_v9_enables_no_v10_behaviour():
    assert brief_review_profile(V9) is None
    service = NativeSchematicReviewService(APPRUN, "model", review_brief=V9)
    assert service.profile is None
    assert service.edit_mode == "free_form"
    assert service.quality_thresholds is None
    assert (service.svg_source, service.with_images, service.think) == (False, False, False)
    assert (service.withhold_checks, service.max_actions) == (False, 1)


def test_v10_service_uses_the_profile():
    service = NativeSchematicReviewService(APPRUN, "model", review_brief=V10)
    assert (service.svg_source, service.with_images, service.think) == (True, True, False)
    assert (service.withhold_checks, service.max_actions) == (True, 4)
    assert service.edit_mode == "menu_only"
    assert service.quality_thresholds == DEFAULT_QUALITY_THRESHOLDS
    assert service.level_power_block and service.text_and_ground_checks
    # Passing a setting the profile already selects is not a conflict.
    NativeSchematicReviewService(APPRUN, "model", review_brief=V10, svg_source=True)
    with pytest.raises(ValueError, match="think=True conflicts"):
        NativeSchematicReviewService(APPRUN, "model", review_brief=V10, think=True)


def test_free_form_edits_need_the_explicit_experimental_flag():
    service = NativeSchematicReviewService(
        APPRUN, "model", review_brief=V10, experimental_free_form_edits=True
    )
    assert service.edit_mode == "free_form_experimental"
    with pytest.raises(ValueError, match="need a brief v10 profile"):
        NativeSchematicReviewService(
            APPRUN, "model", review_brief=V9, experimental_free_form_edits=True
        )


def test_v10_run_records_brief_hash_model_digest_options_and_toolchain(monkeypatch, tmp_path):
    seen = {}

    class Engine:
        toolchain = {"kicad": "10.0.6"}

        def __init__(self, *args, **kwargs):
            seen["engine"] = kwargs

    class Reviewer:
        def __init__(self, model, **options):
            self.identity = {"model": model, "digest": "abc123"}
            seen["reviewer"] = options

    def fake_loop(engine, reviewer, output, **kwargs):
        seen["loop"] = kwargs
        return {}

    monkeypatch.setattr(service_module, "NativeSchematicEngine", Engine)
    monkeypatch.setattr(service_module, "OllamaSchematicReviewer", Reviewer)
    monkeypatch.setattr(service_module, "run_schematic_review", fake_loop)
    service = NativeSchematicReviewService(APPRUN, "model", review_brief=V10)
    service.review(ROOT / "fixtures/m2b/rc_lowpass.json", tmp_path)
    record = seen["loop"]["run_record"]
    assert record["review_brief_sha256"] == service_module.file_hash(V10)
    assert record["review_profile"] == "reviewer-loop.v10"
    assert record["edit_mode"] == "menu_only"
    assert record["model_digest"] == "abc123"
    assert record["options"]["svg_source"] and record["options"]["max_actions"] == 4
    assert record["toolchain"] == {"kicad": "10.0.6"}
    assert seen["loop"]["quality_thresholds"] == DEFAULT_QUALITY_THRESHOLDS
    assert seen["engine"]["quality_thresholds"] == DEFAULT_QUALITY_THRESHOLDS
    assert seen["reviewer"]["svg_source"] and seen["reviewer"]["withhold_checks"]
