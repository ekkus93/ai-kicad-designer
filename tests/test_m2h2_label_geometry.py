"""Emitted-label negatives for physical readability."""

import json
from pathlib import Path

import pytest

from ai_kicad.ir import InputError
from ai_kicad.m2a import ROOT
from ai_kicad.m2b import assets, check_observed_layout, validate
from ai_kicad.m2_fragments import fragment_variants
from ai_kicad.m2_semantics import semantic_plan


@pytest.mark.parametrize("obstacle", ["body", "label"])
def test_emitted_net_label_overlap_is_rejected_independently(tmp_path: Path, obstacle: str):
    schematic = tmp_path / "mutated.kicad_sch"
    schematic.write_text(
        "(kicad_sch "
        '(lib_symbols (symbol "Example:Block" '
        '(symbol "Block_1_1" (rectangle (start -1 1) (end 1 -1))))) '
        '(symbol (lib_id "Example:Block") (at 50 50 0) (unit 1) '
        '(property "Reference" "U1" (at 80 30 0)) '
        '(property "Value" "Active" (at 80 32.54 0))))'
    )
    point = (50_000_000, 50_000_000) if obstacle == "body" else (80_000_000, 70_000_000)
    labels = [("SUPPLY", point)]
    if obstacle == "label":
        labels.append(("RETURN", (point[0] + 1_270_000, point[1])))
    with pytest.raises(InputError, match="observed net label overlaps body/label"):
        check_observed_layout(
            schematic,
            {
                "labels": labels,
                "wires": [],
                "pin_positions": {},
                "nets": {},
                "occurrences": {},
            },
            {"components": [], "relationships": [], "nets": []},
        )


@pytest.mark.parametrize(
    "case",
    ["i3/three_amplifier_one_band", "i5/c2_s3plus", "i5/c3_s1_2"],
)
def test_connector_access_labels_clear_owned_physical_bodies(case: str):
    resolved = assets()
    design = validate(
        json.loads((ROOT / f"fixtures/m2h2/interaction/{case}.json").read_text()),
        resolved,
    )
    variants = fragment_variants(design, resolved, semantic_plan(design, resolved))
    downward = []
    for choices in variants.values():
        for variant in choices:
            if variant.block.kind != "interface":
                continue
            bodies = [item.rect for item in variant.occupied_geometry if item.kind == "body"]
            for net, (x, y) in variant.labels:
                # The serialized label is left-justified above its anchor. A
                # connector's pin exit does not imply that this text is clear.
                box = (x, y - 1_270_000, x + max(635_000, len(net) * 890_000), y)
                assert all(
                    max(box[0], body[0]) >= min(box[2], body[2])
                    or max(box[1], body[1]) >= min(box[3], body[3])
                    for body in bodies
                ), (variant.id, net, box, bodies)
            downward.extend(
                gateway for gateway in variant.gateways if gateway.escape_direction == "down"
            )
    assert downward, "the regression must exercise downward connector alternatives"
