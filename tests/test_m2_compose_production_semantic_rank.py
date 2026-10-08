from pathlib import Path

from ai_kicad.m2_composition_production_integration_audit import (
    production_ranking_integration_passes,
)


def test_production_composer_uses_semantic_ranking() -> None:
    source = (Path(__file__).resolve().parents[1] / "src/ai_kicad/m2_compose.py").read_text()
    assert production_ranking_integration_passes(source)
