import json
import shutil
from pathlib import Path

import pytest

from ai_kicad.pivot.cli import _model_from_fixture
from ai_kicad.pivot.placement import PlacementError, apply_placement
from ai_kicad.pivot.revisions import StaleRevision


ROOT = Path(__file__).resolve().parents[2]


def _inputs(tmp_path):
    fixture = ROOT / "fixtures/pivot/reference_555_led_flasher_v1"
    source = fixture / "native_project/placement_source.kicad_pcb"
    plan = json.loads((fixture / "placement-plan.v1.json").read_text())
    model = _model_from_fixture(fixture)
    candidate = tmp_path / "placed.kicad_pcb"
    return source, plan, model, candidate


def test_revision_bound_placement_is_repeatable_and_preserves_source(tmp_path):
    source, plan, model, candidate = _inputs(tmp_path)
    original = source.read_bytes()
    first = apply_placement(source, candidate, plan, expected_revision=model.revision_id)
    first_bytes = candidate.read_bytes()
    second = apply_placement(source, candidate, plan, expected_revision=model.revision_id)
    assert first == second
    assert first_bytes == candidate.read_bytes()
    assert source.read_bytes() == original
    assert first["placements"]["U1"] == {"x_mm": 18, "y_mm": 8, "rotation_deg": 0}


def test_placement_rejects_stale_source_revision_and_incomplete_refs(tmp_path):
    source, plan, model, candidate = _inputs(tmp_path)
    with pytest.raises(StaleRevision):
        apply_placement(source, candidate, plan, expected_revision="sha256:" + "0" * 64)
    altered = tmp_path / "altered.kicad_pcb"
    shutil.copy2(source, altered)
    altered.write_bytes(altered.read_bytes() + b"\n")
    with pytest.raises(StaleRevision):
        apply_placement(altered, candidate, plan, expected_revision=model.revision_id)
    incomplete = dict(plan, placements=dict(plan["placements"]))
    incomplete["placements"].pop("U1")
    with pytest.raises(PlacementError, match="cover each footprint"):
        apply_placement(source, candidate, incomplete, expected_revision=model.revision_id)
