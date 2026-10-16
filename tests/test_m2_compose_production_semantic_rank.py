from pathlib import Path

from ai_kicad.m2_composition_production_integration_audit import (
    production_ranking_integration_passes,
)


def test_production_composer_uses_semantic_ranking() -> None:
    package = Path(__file__).resolve().parents[1] / "src/ai_kicad"
    source = (package / "m2_compose.py").read_text() + (
        package / "m2_compose_workflow.py"
    ).read_text()
    assert production_ranking_integration_passes(source)
