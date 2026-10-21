import json
from pathlib import Path

from ai_kicad.m2_compose import compose_with_evidence
from ai_kicad.m2_composition_production_integration_audit import (
    production_ranking_integration_passes,
)
from ai_kicad.m2a import ROOT
from ai_kicad.m2b import assets, validate


def test_production_composer_uses_semantic_ranking() -> None:
    package = Path(__file__).resolve().parents[1] / "src/ai_kicad"
    source = (package / "m2_compose.py").read_text() + (
        package / "m2_compose_workflow.py"
    ).read_text()
    assert production_ranking_integration_passes(source)


def test_interleaved_output_case_selects_observer_clean_proved_candidate() -> None:
    resolved = assets()
    design = validate(
        json.loads((ROOT / "fixtures/m2h2/interaction/i3/a3_interleaved.json").read_text()),
        resolved,
    )
    _scene, evidence = compose_with_evidence(design, resolved)
    selection = evidence["candidate_selection"]

    assert selection["selected_selection_key"][:3] == [0, 0, 0]
    assert selection["selected_semantic_penalty_breakdown"]["interface_side_violations"] == 0
