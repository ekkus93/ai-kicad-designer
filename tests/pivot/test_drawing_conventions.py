"""Drawing conventions under brief v11 (spec R7.5, task P6-011q)."""

import glob
import json
from pathlib import Path

import pytest

from ai_kicad.pivot.supply_blocks import power_block_directions
from tools.pivot.run_review_loop_corpus import CORPUS

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "fixtures/pivot/experiments/text_clearance_v11_2026-11-17_run1"
FILES = {(p.parent.name if p.name == "design.json" else p.stem): p for p in CORPUS}


def _text(name: str) -> str:
    return Path(glob.glob(str(RUN / name / "project/*.kicad_sch"))[0]).read_text()


@pytest.mark.parametrize("name", ["timer_astable", "timer_astable_gnd"])
def test_ic_return_symbols_point_down(name):
    """B10 and B15: the ground/REF symbol under U1 pointed right in v10; every return
    symbol of the power block now points down."""
    design = json.loads(FILES[name].read_text())
    returns = [r for r in power_block_directions(design, _text(name)) if r["role"] == "return"]
    assert returns and all(tuple(r["direction"]) == (0, 1) for r in returns), returns
