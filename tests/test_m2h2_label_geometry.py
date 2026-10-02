"""Emitted-label negatives for physical readability."""

from pathlib import Path

import pytest

from ai_kicad.ir import InputError
from ai_kicad.m2b import check_observed_layout


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
        check_observed_layout(schematic, {"labels": labels}, {})
