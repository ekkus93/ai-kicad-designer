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
