"""Conventional power-symbol rail presentation under review brief v3."""

import json
from pathlib import Path

import pytest

from ai_kicad.m2_compose import compose_with_evidence
from ai_kicad.m2_geometry import point_on_segment
from ai_kicad.m2a_artifacts import emit, observe
from ai_kicad.m2b import assets, validate
from ai_kicad.pivot import power_symbols
from ai_kicad.pivot.power_symbols import (
    _pin_points,
    _wire_segments,
    glyph_for_net,
    label_view_text,
    power_symbol_collisions,
    power_symbol_definitions,
    rail_presentation,
    use_power_symbols_text,
)
from ai_kicad.pivot.schematic_review import SchematicReview, UsePowerSymbols
from ai_kicad.pivot.schematic_review_brief import (
    SchematicReviewBriefV3,
    brief_allows_power_symbol_rails,
    load_review_brief,
)
from ai_kicad.pivot.schematic_review_native import (
    NativeSchematicEngine,
    rail_context_for_design,
    terminal_inventory_for_design,
)
from ai_kicad.sexpr import children, one, parse

ROOT = Path(__file__).resolve().parents[2]
BRIEF_V2 = ROOT / "fixtures/pivot/schematic_review_brief_v2.json"
BRIEF_V3 = ROOT / "fixtures/pivot/schematic_review_brief_v3.json"
SCHEMA_V3 = ROOT / "fixtures/pivot/schematic_review_brief.v3.schema.json"
RAILS = ["REF", "VCC"]


def compiled(name: str, directory: Path) -> tuple[dict, str, list[dict], dict[str, dict]]:
    """Native compiler output for a corpus design, with observed terminal positions."""
    resolved = assets()
    source = ROOT / "fixtures/m2b" / f"{name}.json"
    if not source.is_file():
        source = ROOT / "fixtures/pivot" / name / "design.json"
    design = validate(json.loads(source.read_text()), resolved)
    scene, _composition = compose_with_evidence(design, resolved)
    schematic = emit(design, resolved, scene, directory)
    # Pin positions come from the schematic itself; connectivity is not needed here.
    netlist = schematic.parent / "empty-netlist.xml"
    netlist.write_text("<export><components/><nets/></export>")
    observed = observe(schematic, netlist)
    return (
        design,
        schematic.read_text(),
        terminal_inventory_for_design(design, observed),
        rail_context_for_design(design, observed),
    )


@pytest.fixture(scope="module")
def timer(tmp_path_factory) -> tuple[dict, str, list[dict], dict[str, dict]]:
    return compiled("timer_astable", tmp_path_factory.mktemp("timer"))


def convert(text: str, inventory: list[dict], context: dict, order: list[str]) -> str:
    for net in order:
        text = use_power_symbols_text(
            text, net, inventory, context[net]["flags"], context[net]["local_pairs"]
        )
    return text


def test_locked_power_symbols_match_their_manifest_hashes(tmp_path, monkeypatch):
    definitions = power_symbol_definitions()
    assert set(definitions) == {"power:GND", "power:VCC"}
    assert definitions["power:VCC"].startswith('(symbol "power:VCC"')
    copied = tmp_path / "power_symbols"
    copied.mkdir()
    manifest = json.loads(power_symbols.MANIFEST.read_text())
    for entry in manifest["symbols"].values():
        source = ROOT / entry["path"]
        target = copied / source.name
        target.write_text(source.read_text().replace('"VCC"', '"VDD"'))
        entry["path"] = str(target)
    (copied / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(power_symbols, "MANIFEST", copied / "manifest.json")
    with pytest.raises(ValueError, match="manifest hash"):
        power_symbol_definitions()


def test_return_rails_use_ground_glyphs_and_supplies_use_arrows():
    assert glyph_for_net("REF") == "power:GND"
    assert glyph_for_net("gnd") == "power:GND"
    assert glyph_for_net("VCC") == "power:VCC"
    assert glyph_for_net("VPLUS") == "power:VCC"


def test_label_only_rails_fail_presentation(timer):
    _design, text, inventory, _flags = timer
    witnesses = rail_presentation(parse(text), inventory, RAILS)
    assert {item["net"] for item in witnesses} == set(RAILS)


@pytest.mark.parametrize("order", [["REF", "VCC"], ["VCC", "REF"]])
def test_power_symbols_present_both_555_rails_without_collisions(timer, order):
    _design, text, inventory, flags = timer
    converted = convert(text, inventory, flags, order)
    tree = parse(converted)
    assert rail_presentation(tree, inventory, RAILS) == []
    assert power_symbol_collisions(converted) == []
    assert not [label for label in children(tree, "label") if label[1] in RAILS]
    placed = power_symbols.power_symbols(tree)
    assert {item["net"] for item in placed} == set(RAILS)
    assert {item["lib_id"] for item in placed if item["net"] == "REF"} == {"power:GND"}
    assert {item["lib_id"] for item in placed if item["net"] == "VCC"} == {"power:VCC"}
    # The compiler's long REF run across the sheet is gone; each terminal has a symbol.
    assert len([item for item in placed if item["net"] == "REF"]) == 4
    assert len([item for item in placed if item["net"] == "VCC"]) == 4


@pytest.mark.parametrize("order", [["REF", "VCC"], ["VCC", "REF"]])
def test_conversion_leaves_no_dangling_wire_end(timer, order):
    _design, text, inventory, flags = timer
    tree = parse(convert(text, inventory, flags, order))
    segments = _wire_segments(tree)
    anchors = _pin_points(tree) | {
        (round(float(one(label, "at")[1]) * 1e6), round(float(one(label, "at")[2]) * 1e6))
        for label in children(tree, "label")
    }
    for index, segment in enumerate(segments):
        for end in segment:
            assert end in anchors or any(
                point_on_segment(end, *other)
                for other_index, other in enumerate(segments)
                if other_index != index
            ), f"dangling wire end {end}"


def test_decoupling_wire_survives_power_symbol_conversion(tmp_path):
    from ai_kicad.pivot.schematic_review_native import _point_groups

    _design, text, inventory, context = compiled("dual_buffer", tmp_path)
    pairs = context["VMINUS"]["local_pairs"]
    assert pairs, "dual_buffer declares a VMINUS decoupling capacitor"
    before = parse(text)
    assert all(len(_point_groups(before, list(pair))) == 1 for pair in pairs)
    after = parse(convert(text, inventory, context, ["VMINUS"]))
    assert all(len(_point_groups(after, list(pair))) == 1 for pair in pairs)
    assert rail_presentation(after, inventory, ["VMINUS"]) == []


def test_label_view_restores_the_compiler_label_form(timer):
    _design, text, inventory, flags = timer
    converted = convert(text, inventory, flags, RAILS)
    view = parse(label_view_text(converted))
    assert power_symbols.power_symbols(view) == []
    assert not [
        item
        for item in children(one(view, "lib_symbols"), "symbol")
        if item[1] in {"power:GND", "power:VCC"}
    ]
    labels = {
        (
            label[1],
            (round(float(one(label, "at")[1]) * 1e6), round(float(one(label, "at")[2]) * 1e6)),
        )
        for label in children(view, "label")
    }
    for item in power_symbols.power_symbols(parse(converted)):
        assert (item["net"], item["point"]) in labels


def test_power_symbols_are_rejected_without_the_v3_rail_policy(tmp_path, timer):
    design = timer[0]
    engine = NativeSchematicEngine.__new__(NativeSchematicEngine)
    engine.design = design
    engine.power_symbol_rails = False
    with pytest.raises(ValueError, match="brief v3 rail policy"):
        engine.apply(
            tmp_path / "Design.kicad_sch",
            tmp_path / "candidate",
            [UsePowerSymbols(operation="use_power_symbols", net="VCC")],
        )


def test_power_symbols_are_limited_to_asserted_rails(tmp_path, timer):
    engine = NativeSchematicEngine.__new__(NativeSchematicEngine)
    engine.design = timer[0]
    engine.power_symbol_rails = True
    with pytest.raises(ValueError, match="asserted power nets"):
        engine.apply(
            tmp_path / "Design.kicad_sch",
            tmp_path / "candidate",
            [UsePowerSymbols(operation="use_power_symbols", net="OUT")],
        )


def test_review_contract_accepts_use_power_symbols():
    review = SchematicReview.model_validate(
        {
            "base_revision": "sha256:" + "0" * 64,
            "decision": "revise",
            "issues": ["VCC is joined only by labels"],
            "actions": [{"operation": "use_power_symbols", "net": "VCC"}],
            "rationale": "Draw the supply with power symbols.",
        }
    )
    assert isinstance(review.actions[0], UsePowerSymbols)


def test_v3_brief_schema_matches_typed_contract():
    schema = json.loads(SCHEMA_V3.read_text())
    expected = SchematicReviewBriefV3.model_json_schema()
    expected["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    expected["$id"] = "https://ai-kicad-designer.local/schemas/schematic-review-brief.v3.json"
    assert schema == expected


def test_v3_brief_requires_rail_presentation_and_clearance_gates():
    brief = json.loads(BRIEF_V3.read_text())
    rails = next(
        item for item in brief["criteria"] if item["criterion_id"] == "visible_local_rails"
    )
    assert {item["check_id"] for item in rails["measurements"]} >= {
        "rail_presentation",
        "power_symbol_clearance",
    }
    rails["measurements"] = [
        item for item in rails["measurements"] if item["check_id"] != "power_symbol_clearance"
    ]
    with pytest.raises(ValueError, match="power-symbol clearance"):
        SchematicReviewBriefV3.model_validate(brief)


def test_only_the_v3_brief_enables_power_symbol_rails():
    assert isinstance(load_review_brief(BRIEF_V3), SchematicReviewBriefV3)
    assert brief_allows_power_symbol_rails(BRIEF_V3)
    assert not brief_allows_power_symbol_rails(BRIEF_V2)
    assert not brief_allows_power_symbol_rails(None)


def test_repeating_use_power_symbols_replaces_only_crowded_symbols(timer):
    _design, text, inventory, context = timer
    converted = convert(text, inventory, context, RAILS)
    vcc = [item for item in power_symbols.power_symbols(parse(converted)) if item["net"] == "VCC"]
    target = vcc[0]
    # A later edit drops another net's label onto one VCC glyph.
    x, y = target["point"]
    crowded = power_symbols._append_forms(
        converted,
        [
            f'(label "OTHER" (at {x / 1e6:.2f} {(y - 1_270_000) / 1e6:.2f} 0) '
            '(effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "crowd"))'
        ],
    )
    assert power_symbol_collisions(crowded)
    repaired = use_power_symbols_text(
        crowded, "VCC", inventory, context["VCC"]["flags"], context["VCC"]["local_pairs"]
    )
    tree = parse(repaired)
    assert power_symbol_collisions(repaired) == []
    assert rail_presentation(tree, inventory, RAILS) == []
    untouched = {item["reference"] for item in vcc[1:]}
    after = {item["reference"]: item for item in power_symbols.power_symbols(tree)}
    assert all(
        after[reference]["point"] in {item["point"] for item in vcc} for reference in untouched
    )


def test_repeating_use_power_symbols_without_crowding_is_no_change(timer):
    _design, text, inventory, context = timer
    converted = convert(text, inventory, context, RAILS)
    with pytest.raises(ValueError, match="made no change"):
        use_power_symbols_text(
            converted, "VCC", inventory, context["VCC"]["flags"], context["VCC"]["local_pairs"]
        )


def test_blocked_power_symbol_is_refused_with_the_blocking_rail_named(tmp_path):
    from ai_kicad.pivot.schematic_review_native import connect_rail_text

    # In the reference 555, a wired REF run passes beside R1's VCC pin.
    _design, text, inventory, context = compiled("reference_555_led_flasher_v8", tmp_path)
    wired = connect_rail_text(text, "REF", inventory)
    with pytest.raises(ValueError, match=r"wiring of \['REF'\].*use_power_symbols for it first"):
        use_power_symbols_text(
            wired, "VCC", inventory, context["VCC"]["flags"], context["VCC"]["local_pairs"]
        )
    # Following the advice draws both rails cleanly.
    converted = convert(wired, inventory, context, ["REF", "VCC"])
    assert power_symbol_collisions(converted) == []
    assert rail_presentation(parse(converted), inventory, RAILS) == []
