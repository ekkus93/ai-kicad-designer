"""Composition regressions after the frozen M2c2 evaluation."""

import copy
import json
import re

import pytest

from ai_kicad.ir import InputError
from ai_kicad.m2a import ROOT
from ai_kicad.m2b import assets, validate
from ai_kicad.m2_compose import compose_layout, stage_graph


def _case(number, resolved):
    path = ROOT / "fixtures/m2blind/ir" / f"H{number}.json"
    return validate(json.loads(path.read_text()), resolved)


@pytest.mark.parametrize("number", range(1, 9))
def test_known_compositions_have_one_geometry_per_occurrence(number):
    resolved = assets()
    design = _case(number, resolved)
    scene = compose_layout(design, resolved)
    expected = {
        (component["id"], unit)
        for component in design["components"]
        for unit in resolved[component["asset"]].units
    }
    assert expected <= set(scene.positions)
    assert scene.metrics["body_overlap_count"] == 0
    assert scene.metrics["unrelated_wire_crossing_count"] == 0
    assert stage_graph(design).order


def test_dual_active_functions_share_one_package_and_power_occurrence():
    resolved = assets()
    design = _case(4, resolved)
    scene = compose_layout(design, resolved)
    package = next(c for c in design["components"] if c["asset"].endswith("NE5532"))
    assert {(package["id"], unit) for unit in (1, 2, 3)} <= set(scene.positions)
    assert sum(key[0] == package["id"] for key in scene.positions) == 3
    assert scene.positions[(package["id"], 1)][0] < scene.positions[(package["id"], 2)][0]


@pytest.mark.parametrize("number", (1, 4, 5, 6, 7, 8))
def test_set_permutation_and_refdes_renaming_preserve_compiler_geometry(number):
    resolved = assets()
    original = _case(number, resolved)
    baseline = compose_layout(original, resolved)
    changed = copy.deepcopy(original)
    for key in ("components", "nets", "relationships", "power_assertions"):
        changed[key].reverse()
    for net in changed["nets"]:
        net["members"].reverse()
    for component in changed["components"]:
        if "functions" in component:
            component["functions"].reverse()
        match = re.fullmatch(r"([A-Z]+)([0-9]+)", component["refdes"])
        component["refdes"] = f"{match.group(1)}{int(match.group(2)) + 20}"
    altered = compose_layout(validate(changed, resolved), resolved)
    assert (
        altered.positions,
        altered.wires,
        altered.wire_nets,
        altered.labels,
        altered.angles,
    ) == (
        baseline.positions,
        baseline.wires,
        baseline.wire_nets,
        baseline.labels,
        baseline.angles,
    )


def test_regulator_rc_probe_is_a_distinct_non_v2_composition():
    resolved = assets()
    path = ROOT / "fixtures/m2d1/regulated_rc_probe.json"
    design = validate(json.loads(path.read_text()), resolved)
    scene = compose_layout(design, resolved)
    assert ("post_resistor", 1) in scene.positions
    assert ("post_capacitor", 1) in scene.positions
    assert ("stage", 1) in scene.positions
    assert ("conversion", "post.series", "VOUT") in stage_graph(design).edges


def test_unmatched_relationship_reports_semantic_id():
    resolved = assets()
    design = _case(1, resolved)
    design["relationships"] = [r for r in design["relationships"] if r["kind"] != "polarity"]
    with pytest.raises(InputError, match="SEMANTIC_OWNER_INCOMPLETE.*load_led"):
        compose_layout(design, resolved)


def test_stage_cycle_reports_conflicting_relationships():
    design = {
        "relationships": [
            {"id": "a", "kind": "series", "input": "N1", "output": "N2"},
            {"id": "b", "kind": "series", "input": "N2", "output": "N1"},
        ]
    }
    with pytest.raises(InputError, match="unsupported stage graph cycle: \\['a', 'b'\\]"):
        stage_graph(design)
