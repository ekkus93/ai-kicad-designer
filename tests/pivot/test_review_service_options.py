from pathlib import Path

import pytest

import ai_kicad.pivot.schematic_review_service as service_module
from ai_kicad.pivot.schematic_review_service import NativeSchematicReviewService


class _Stop(Exception):
    pass


@pytest.mark.parametrize(("kwargs", "expected"), [({}, 2048), ({"output_tokens": 4096}, 4096)])
def test_review_service_passes_output_cap_to_reviewer(monkeypatch, tmp_path, kwargs, expected):
    seen = {}

    def fake_reviewer(model, **options):
        seen.update(options)
        raise _Stop

    monkeypatch.setattr(service_module, "NativeSchematicEngine", lambda *a, **k: None)
    monkeypatch.setattr(service_module, "OllamaSchematicReviewer", fake_reviewer)
    service = NativeSchematicReviewService(
        Path("/unused/AppRun"), "model", context_tokens=262144, **kwargs
    )
    with pytest.raises(_Stop):
        service.review(Path("fixtures/m2b/rc_lowpass.json"), tmp_path)
    assert seen["output_tokens"] == expected
    assert seen["context_tokens"] == 262144


def test_v4_brief_turns_on_readability_checks():
    root = Path(__file__).resolve().parents[2] / "fixtures/pivot"
    v4 = NativeSchematicReviewService(
        Path("/unused/AppRun"), "model", review_brief=root / "schematic_review_brief_v4.json"
    )
    v3 = NativeSchematicReviewService(
        Path("/unused/AppRun"), "model", review_brief=root / "schematic_review_brief_v3.json"
    )
    assert v4.power_symbol_rails and v4.readability_checks
    assert v3.power_symbol_rails and not v3.readability_checks


def test_v6_brief_turns_on_field_ownership():
    root = Path(__file__).resolve().parents[2] / "fixtures/pivot"
    v6 = NativeSchematicReviewService(
        Path("/unused/AppRun"), "model", review_brief=root / "schematic_review_brief_v6.json"
    )
    v5 = NativeSchematicReviewService(
        Path("/unused/AppRun"), "model", review_brief=root / "schematic_review_brief_v5.json"
    )
    assert v6.page_balance and v6.field_ownership
    assert v5.page_balance and not v5.field_ownership


def test_v7_brief_turns_on_text_and_ground_checks():
    root = Path(__file__).resolve().parents[2] / "fixtures/pivot"
    v7 = NativeSchematicReviewService(
        Path("/unused/AppRun"), "model", review_brief=root / "schematic_review_brief_v7.json"
    )
    v6 = NativeSchematicReviewService(
        Path("/unused/AppRun"), "model", review_brief=root / "schematic_review_brief_v6.json"
    )
    assert v7.field_ownership and v7.text_and_ground_checks
    assert v6.field_ownership and not v6.text_and_ground_checks


def test_review_service_passes_think_and_svg_source_to_reviewer(monkeypatch, tmp_path):
    seen = {}

    def fake_reviewer(model, **options):
        seen.update(options)
        raise _Stop

    monkeypatch.setattr(service_module, "NativeSchematicEngine", lambda *a, **k: None)
    monkeypatch.setattr(service_module, "OllamaSchematicReviewer", fake_reviewer)
    service = NativeSchematicReviewService(
        Path("/unused/AppRun"), "model", think=True, svg_source=True
    )
    with pytest.raises(_Stop):
        service.review(Path("fixtures/m2b/rc_lowpass.json"), tmp_path)
    assert seen["think"] is True and seen["svg_source"] is True
