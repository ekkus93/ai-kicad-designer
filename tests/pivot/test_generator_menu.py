"""Generator runner-up drawings as menu entries (brief v12, spec R8.2, task P6-011u)."""

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_kicad.pivot.edit_menu import ValidationCache
from ai_kicad.pivot.generator_menu import generator_entries

ROOT = Path(__file__).resolve().parents[2]
PASS = {
    "checks": {"erc": "PASS", "electrical_equivalence": "PASS", "page_balance": "PASS"},
    "quality": None,
}


def _base(tmp_path, text="drawn"):
    schematic = tmp_path / "base.kicad_sch"
    schematic.write_text(text)
    return SimpleNamespace(schematic=schematic, revision="sha256:" + "0" * 64, report=PASS)


def _variants():
    return {
        "v1": {"class": "connector_reorientation", "excluded": "J2|mirror", "description": "a"},
        "v2": {"class": "block_move", "excluded": "J3|move", "description": "b"},
    }


def test_each_variant_becomes_a_checked_entry_with_keep_last(tmp_path):
    base = _base(tmp_path)
    tried = []

    def validate(action):
        tried.append(action)
        revision = "sha256:" + ("1" if action["variant"] == "v1" else "2") * 64
        return SimpleNamespace(revision=revision, report=PASS)

    entries, record = generator_entries(base, _variants(), "drawn", validate, ValidationCache())
    assert [e["id"] for e in entries] == ["connector_reorientation-1", "block_move-2", "keep-1"]
    assert entries[0]["action"] == {"operation": "use_variant", "variant": "v1"}
    assert entries[0]["scratch_revision"] == "sha256:" + "1" * 64
    assert entries[-1]["action"] == {"operation": "keep_drawing"}
    assert record["native_validations"] == 2 and record["budget_exhausted"] is None


def test_a_variant_that_makes_a_check_fail_is_not_offered(tmp_path):
    base = _base(tmp_path)

    def validate(action):
        checks = {"erc": "PASS", "electrical_equivalence": "PASS", "page_balance": "FAIL"}
        report = {"checks": checks, "quality": None}
        return SimpleNamespace(revision="sha256:" + "3" * 64, report=report)

    entries, record = generator_entries(base, _variants(), "drawn", validate, ValidationCache())
    assert [e["id"] for e in entries] == ["keep-1"]
    assert {r["reason"] for r in record["rejected"]} == {"makes page_balance fail"}


def test_variants_are_not_offered_once_the_drawing_has_changed(tmp_path):
    base = _base(tmp_path, text="edited")
    entries, record = generator_entries(
        base, _variants(), "drawn", lambda a: pytest.fail("validated"), ValidationCache()
    )
    assert [e["id"] for e in entries] == ["keep-1"] and "changed" in record["not_offered"]


def test_briefs_before_v12_have_no_generator_menu():
    from ai_kicad.pivot.schematic_review_brief import brief_generator_menu

    for version in ("v10", "v11"):
        path = ROOT / f"fixtures/pivot/schematic_review_brief_{version}.json"
        assert brief_generator_menu(path) is None
    menu = brief_generator_menu(ROOT / "fixtures/pivot/schematic_review_brief_v12.json")
    assert menu is not None and menu.variants >= 1 and menu.seconds > 0


@pytest.mark.skipif(not os.environ.get("AI_KICAD_APPRUN"), reason="needs the KiCad AppRun")
def test_v12_offers_the_regulators_runner_up_drawings_and_choosing_one_matches_scratch(
    tmp_path,
):
    """The regulator under v12: its compile records runner-up drawings within budget, the
    menu offers them with "keep", and applying an entry reproduces its scratch revision."""
    from ai_kicad.pivot.edit_menu import MenuPolicy
    from ai_kicad.pivot.schematic_review import ACTION_ADAPTER
    from ai_kicad.pivot.schematic_review_service import NativeSchematicReviewService
    from tools.pivot.run_review_loop_corpus import CORPUS

    design = next(p for p in CORPUS if "linear_regulator" in str(p))
    service = NativeSchematicReviewService(
        Path(os.environ["AI_KICAD_APPRUN"]),
        "m",
        review_brief=ROOT / "fixtures/pivot/schematic_review_brief_v12.json",
    )
    engine = service.engine(design)
    source = engine.initial(tmp_path / "initial")
    record = json.loads((tmp_path / "initial/presentation.json").read_text())["generator_variants"]
    assert record["variants"], record
    assert len(record["variants"]) <= record["budget"]["variants"]
    assessment = engine.assess(source, tmp_path / "initial")
    assert all(value == "PASS" for value in assessment.report["checks"].values())
    menu = engine.edit_menu(
        assessment, tmp_path / "menu", MenuPolicy(), ValidationCache(), service.quality_thresholds
    )
    generated = [e for e in menu["entries"] if e["action"]["operation"] == "use_variant"]
    assert generated and menu["entries"][-1]["id"] == "keep-1"
    entry = generated[0]
    chosen = engine.apply(
        assessment.schematic, tmp_path / "chosen", [ACTION_ADAPTER.validate_python(entry["action"])]
    )
    trial = engine.assess(chosen, tmp_path / "chosen")
    assert trial.revision == entry["scratch_revision"]
    assert all(value == "PASS" for value in trial.report["checks"].values())
