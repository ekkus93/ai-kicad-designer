"""Generic invariants for the M2e1 instance-based composition architecture."""

from __future__ import annotations

import copy
from dataclasses import replace
import json
from pathlib import Path
import re

import pytest

from ai_kicad.ir import InputError
from ai_kicad.m2a import ROOT
from ai_kicad.m2_fragments import fragment_variants
from ai_kicad.m2_pack import LEFT, TOP, pack_fragments
from ai_kicad.m2_route import route_between_fragments
from ai_kicad.m2_semantics import semantic_plan
from ai_kicad.m2b import assets, validate
from ai_kicad.m2_compose import compose_layout


PROBES = ROOT / "fixtures/m2e1/ir"


def _load(path: Path) -> dict:
    return validate(json.loads(path.read_text()), assets())


def _known(name: str) -> dict:
    return _load(ROOT / "fixtures/m2blind_v3/ir" / f"{name}.json")


def _duplicate(base: dict) -> dict:
    """Make two electrically independent copies for repeated-instance tests."""
    copies = []
    for index, prefix in enumerate(("first", "second"), 1):
        item = copy.deepcopy(base)
        component_map = {c["id"]: f"{prefix}_{c['id']}" for c in item["components"]}
        net_map = {n["id"]: f"{prefix}_{n['id']}" for n in item["nets"]}
        for component in item["components"]:
            component["id"] = component_map[component["id"]]
            match = re.fullmatch(r"([A-Z]+)([0-9]+)", component["refdes"])
            component["refdes"] = f"{match.group(1)}{int(match.group(2)) + index * 40}"
        for net in item["nets"]:
            net["id"] = net_map[net["id"]]
            net["members"] = [[component_map[cid], pin] for cid, pin in net["members"]]

        def renamed(value):
            if isinstance(value, str):
                return component_map.get(value, net_map.get(value, value))
            if isinstance(value, list):
                return [renamed(member) for member in value]
            if isinstance(value, dict):
                return {key: renamed(member) for key, member in value.items()}
            return value

        item["relationships"] = [renamed(relation) for relation in item["relationships"]]
        for relation in item["relationships"]:
            relation["id"] = f"{prefix}.{relation['id']}"
        item["power_assertions"] = [renamed(flag) for flag in item["power_assertions"]]
        for flag_index, flag in enumerate(item["power_assertions"], 1):
            flag["id"] = f"{prefix}.{flag['id']}"
            flag["refdes"] = f"#FLG{index}{flag_index:02d}"
        copies.append(item)
    return validate(
        {
            "profile": "m2b.1",
            "id": "repeated_instances",
            "name": "RepeatedInstances",
            "components": copies[0]["components"] + copies[1]["components"],
            "nets": copies[0]["nets"] + copies[1]["nets"],
            "relationships": copies[0]["relationships"] + copies[1]["relationships"],
            "no_connects": [],
            "power_assertions": copies[0]["power_assertions"] + copies[1]["power_assertions"],
        },
        assets(),
    )


def test_repeated_regulators_timers_and_packages_are_enumerated():
    resolved = assets()
    for design, kind, count in (
        (_duplicate(_known("V3-2")), "power_stage", 2),
        (_load(PROBES / "dual_timer_led.json"), "timer", 2),
        (_duplicate(_known("V3-4")), "package_power", 2),
    ):
        plan = semantic_plan(design, resolved)
        assert sum(block.kind == kind for block in plan.blocks) == count
        assert len(plan.owners) == len(set(plan.owners))


def test_internal_ports_do_not_depend_on_connectors():
    resolved = assets()
    for name in ("V3-2", "V3-8"):
        plan = semantic_plan(_known(name), resolved)
        regulator = next(block for block in plan.blocks if block.kind == "power_stage")
        assert {port.id.rsplit(".", 1)[-1] for port in regulator.ports} == {
            "input",
            "output",
            "reference",
        }
        assert not any("interface" in occurrence[0] for occurrence in regulator.occurrences)


def test_multiunit_functions_are_independent_from_package_power():
    resolved = assets()
    design = _known("V3-4")
    plan = semantic_plan(design, resolved)
    functions = [block for block in plan.blocks if block.function]
    package = next(block for block in plan.blocks if block.kind == "package_power")
    assert {block.function for block in functions} == {("amp", "a"), ("amp", "b")}
    assert {block.kind for block in functions} == {
        "noninverting_amplifier",
        "inverting_amplifier",
    }
    assert package.occurrences & {("amp", 3)}
    assert all(("amp", 3) not in block.occurrences for block in functions)

    unused = copy.deepcopy(_load(ROOT / "fixtures/m2b/dual_buffer.json"))
    for relation in unused["relationships"]:
        if relation["kind"] == "amplifier":
            relation["unused"] = True
    assert sum(block.unused for block in semantic_plan(unused, resolved).blocks) == 2


def test_typed_power_signal_reference_and_support_projections():
    plan = semantic_plan(_known("V3-8"), assets())
    assert any(
        edge.kind == "power"
        and edge.source.startswith("power_stage")
        and edge.target.startswith("timer")
        for edge in plan.edges
    )
    assert any(edge.kind == "branch" and edge.source.startswith("timer") for edge in plan.edges)
    assert not any(
        edge.kind == "signal" and edge.source.startswith("power_stage") for edge in plan.edges
    )
    assert {edge.kind for edge in plan.edges} >= {"power", "branch", "reference", "support"}


def test_support_ownership_is_consumer_local_and_overlap_has_one_owner():
    plan = semantic_plan(_duplicate(_known("V3-2")), assets())
    regulators = [block for block in plan.blocks if block.kind == "power_stage"]
    assert len(regulators) == 2
    assert not (regulators[0].occurrences & regulators[1].occurrences)
    sallen = semantic_plan(_known("V3-5"), assets())
    active = next(block for block in sallen.blocks if block.kind == "sallen_key")
    origins = set(active.relationships)
    assert {"filter_series", "filter_shunt", "reactive.feedback", "loop.a"} <= origins
    assert all(sallen.owners[occurrence] == active.id for occurrence in active.occurrences)


def test_fragments_are_local_measured_and_translated():
    resolved = assets()
    normalized = []
    for name in ("V3-5", "V3-7"):
        design = _known(name)
        plan = semantic_plan(design, resolved)
        fragment = next(
            choices[0]
            for choices in fragment_variants(design, resolved, plan).values()
            if choices[0].block.kind == "sallen_key"
        )
        origin = min(fragment.positions.values())
        normalized.append(
            sorted(
                (key, (point[0] - origin[0], point[1] - origin[1]))
                for key, point in fragment.positions.items()
            )
        )
        assert fragment.obstacles and fragment.protected_wires
        assert all(
            fragment.envelope[0] <= p.point[0] <= fragment.envelope[2] for p in fragment.ports
        )
    assert normalized[0] == normalized[1]


def test_packer_uses_real_envelopes_and_tries_finite_alternate():
    resolved = assets()
    design = _known("V3-2")
    plan = semantic_plan(design, resolved)
    variants = fragment_variants(design, resolved, plan)
    key = next(iter(sorted(variants)))
    good = variants[key][0]
    bad = replace(good, id=good.id + ".oversize", envelope=(0, 0, 400_000_000, 20_000_000))
    variants[key] = (bad, good)
    packed = pack_fragments(plan, variants)
    assert any(item.fragment.id == good.id for item in packed.fragments)
    assert packed.attempts[0].startswith("candidate-1:")
    assert min(item.envelope[0] for item in packed.fragments) >= LEFT
    assert min(item.envelope[1] for item in packed.fragments) >= TOP


def test_route_fanout_is_one_deterministic_tree():
    resolved = assets()
    design = _load(PROBES / "regulator_parallel_rc.json")
    plan = semantic_plan(design, resolved)
    packing = pack_fragments(plan, fragment_variants(design, resolved, plan))
    first = route_between_fragments(plan, packing.fragments)
    second = route_between_fragments(plan, packing.fragments)
    assert first == second
    tree = next(tree for tree in first if tree.net == "VOUT")
    assert len(tree.edges) == 2
    assert tree.junctions
    assert all(a[0] == b[0] or a[1] == b[1] for a, b in tree.segments)


@pytest.mark.parametrize("path", sorted(PROBES.glob("*.json")))
def test_development_probe_passes_independent_preflight(path):
    design = _load(path)
    scene = compose_layout(design, assets())
    assert scene.metrics["body_overlap_count"] == 0
    assert scene.metrics["wire_through_body_count"] == 0
    assert scene.metrics["unrelated_wire_crossing_count"] == 0
    assert scene.metrics["page_margin_pass"] is True


def test_wrong_consumer_support_reports_origins():
    design = _known("V3-2")
    relation = next(r for r in design["relationships"] if r["kind"] == "decoupling")
    relation["consumer"][1] = "2"
    with pytest.raises(
        InputError, match="SEMANTIC_POWER_SUPPORT_CONFLICT.*bypass.input.*bypass.output"
    ):
        semantic_plan(design, assets())
