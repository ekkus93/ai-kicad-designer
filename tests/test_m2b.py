"""M2b semantic generalization and real KiCad artifact qualification."""

import argparse
import copy
import json
import os
from pathlib import Path
import re
import subprocess

import pytest

from ai_kicad.assets import _extract_symbol, sha256
from ai_kicad.ir import InputError, load_json
from ai_kicad.kicad import run_headless, validate_toolchain
from ai_kicad.m2a import ROOT, _mm, emit, observe
from ai_kicad.m2b import (
    active_layout,
    assets,
    check_observed_layout,
    compare,
    passive_layout,
    validate,
)
from ai_kicad.m2b_build import build

FIX = ROOT / "fixtures/m2b"
CASES = (
    "led_series",
    "rc_lowpass",
    "dual_buffer",
    "noninverting_gain",
    "inverting_gain",
    "rc_to_buffer",
    "led_long_text",
)


def design(case: str, resolved=None):
    return validate(load_json(FIX / f"{case}.json"), resolved or assets())


def scene(case: str, resolved=None):
    resolved = resolved or assets()
    d = design(case, resolved)
    return (
        active_layout
        if any(r["kind"] == "amplifier" for r in d["relationships"])
        else passive_layout
    )(d, resolved)


def args(case: str, out: Path):
    return argparse.Namespace(
        design=FIX / f"{case}.json",
        target="schematic",
        assets_lock=FIX / "assets.lock.json",
        toolchain_lock=ROOT / "fixtures/m1a/toolchain.lock.json",
        policy_lock=ROOT / "fixtures/m1a/policy.lock.json",
        out=out,
    )


def test_corpus_is_frozen_and_split():
    raw = (FIX / "corpus.v1.json").read_bytes()
    expected = (FIX / "corpus.v1.sha256").read_text().split()[0]
    assert sha256(raw) == expected
    corpus = json.loads(raw)
    assert corpus["schema_version"] == "m2-corpus.1"
    ids = [item["id"] for item in corpus["circuits"]]
    assert len(ids) == len(set(ids)) == 20
    assert sum(x["split"] == "tuning" for x in corpus["circuits"]) == 12
    assert sum(x["split"] == "holdout" for x in corpus["circuits"]) == 8
    assert set(CASES) <= set(ids)
    assert next(x for x in corpus["circuits"] if x["id"] == "led_long_text")["split"] == "holdout"


@pytest.mark.parametrize("case", CASES)
def test_qualified_real_build(case, tmp_path):
    out = tmp_path / case
    assert build(args(case, out)) == 0
    manifest = load_json(out / "reports/manifest.json")
    electrical = load_json(out / "reports/electrical.json")
    layout = load_json(out / "reports/layout.json")
    erc = load_json(out / "reports/erc.json")
    assert manifest["checks"] == {
        "electrical": "pass",
        "erc": "pass",
        "svg": "pass",
        "layout": "pass",
    }
    assert electrical["status"] == "pass"
    assert all(not sheet["violations"] for sheet in erc["sheets"])
    assert layout["observed_body_overlap_count"] == 0
    assert layout["observed_wire_through_text_count"] == 0
    assert layout["observed_unrelated_wire_crossing_count"] == 0
    assert layout["unrouted_pin_count"] == 0
    assert layout["observed_page_margin_pass"]
    project = out / "project" / f"{design(case)['name']}.kicad_sch"
    assert project.is_file() and project.with_suffix(".kicad_pro").is_file()
    assert list((out / "renders/schematic").glob("*.svg"))
    checked = FIX / "qualification" / case
    assert project.read_bytes() == (checked / "project" / project.name).read_bytes()
    svg = next((out / "renders/schematic").glob("*.svg"))
    checked_svg = checked / "renders/schematic" / svg.name
    assert re.sub(r"<title>.*?</title>", "<title/>", svg.read_text()) == re.sub(
        r"<title>.*?</title>", "<title/>", checked_svg.read_text()
    )
    assert load_json(out / "reports/layout.json") == load_json(checked / "reports/layout.json")
    assert load_json(out / "reports/electrical.json") == load_json(
        checked / "reports/electrical.json"
    )
    assert compare(design(case), observe(project, out / "reports/netlist.xml"))["status"] == "pass"
    assert check_observed_layout(
        project, observe(project, out / "reports/netlist.xml"), design(case)
    )


@pytest.mark.parametrize("case", CASES)
def test_reference_renaming_and_set_order_do_not_move_geometry(case, tmp_path):
    resolved = assets()
    baseline = design(case, resolved)
    permuted = copy.deepcopy(baseline)
    for key in ("components", "nets", "relationships", "power_assertions"):
        permuted[key].reverse()
    for net in permuted["nets"]:
        net["members"].reverse()
    for c in permuted["components"]:
        if "functions" in c:
            c["functions"].reverse()
    assert validate(permuted, resolved) == baseline
    original = scene(case, resolved)
    normalized = validate(permuted, resolved)
    left = emit(baseline, resolved, original, tmp_path / "original")
    right = emit(
        normalized,
        resolved,
        (
            active_layout
            if any(r["kind"] == "amplifier" for r in normalized["relationships"])
            else passive_layout
        )(normalized, resolved),
        tmp_path / "permuted",
    )
    assert left.read_bytes() == right.read_bytes()
    renamed = copy.deepcopy(baseline)
    for c in renamed["components"]:
        prefix = c["refdes"].rstrip("0123456789")
        number = int(c["refdes"][len(prefix) :])
        c["refdes"] = f"{prefix}{number + 10}"
    changed = (
        active_layout
        if any(r["kind"] == "amplifier" for r in baseline["relationships"])
        else passive_layout
    )(validate(renamed, resolved), resolved)
    assert changed.positions == original.positions
    assert changed.wires == original.wires
    assert changed.labels == original.labels
    assert changed.angles == original.angles


def test_semantic_and_electrical_mutations_are_explicit():
    resolved = assets()
    led = design("led_series", resolved)
    wrong = copy.deepcopy(led)
    next(r for r in wrong["relationships"] if r["kind"] == "polarity")["anode"] = "REF"
    with pytest.raises(InputError, match="polarity"):
        validate(wrong, resolved)
    bad = copy.deepcopy(led)
    bad["relationships"].append({"id": "future", "kind": "timer"})
    with pytest.raises(InputError, match="unsupported relationship"):
        validate(bad, resolved)
    rc = design("rc_lowpass", resolved)
    changed = copy.deepcopy(rc)
    old = next(n for n in changed["nets"] if n["id"] == "OUT")
    ref = next(n for n in changed["nets"] if n["id"] == "REF")
    old["members"].remove(["output", "1"])
    ref["members"].append(["output", "1"])
    assert {frozenset(map(tuple, n["members"])) for n in changed["nets"]} != {
        frozenset(map(tuple, n["members"])) for n in rc["nets"]
    }
    with pytest.raises(InputError):
        passive_layout(validate(changed, resolved), resolved)
    amp = design("noninverting_gain", resolved)
    altered = copy.deepcopy(amp)
    next(r for r in altered["relationships"] if r["id"] == "loop.a")["polarity"] = "positive"
    with pytest.raises(InputError, match="feedback"):
        validate(altered, resolved)
    altered = copy.deepcopy(amp)
    altered["relationships"] = [r for r in altered["relationships"] if r["id"] != "bypass.plus"]
    with pytest.raises(InputError, match="relation inventory"):
        active_layout(validate(altered, resolved), resolved)


def test_changed_physical_membership_changes_real_kicad_result(tmp_path, launcher):
    resolved = assets()
    original = design("led_series", resolved)
    changed = copy.deepcopy(original)
    supply = next(net for net in changed["nets"] if net["id"] == "VPLUS")
    reference = next(net for net in changed["nets"] if net["id"] == "REF")
    supply["members"].remove(["source", "1"])
    reference["members"].remove(["return", "1"])
    supply["members"].append(["return", "1"])
    reference["members"].append(["source", "1"])
    changed = validate(changed, resolved)
    stage = tmp_path / "different-membership"
    schematic = emit(changed, resolved, passive_layout(changed, resolved), stage)
    xml, _, _ = run_headless(schematic, launcher, stage, ROOT / "fixtures/m2a/sym-lib-table")
    observed = observe(schematic, xml)
    assert compare(changed, observed, resolved)["status"] == "pass"
    original_report = load_json(FIX / "qualification/led_series/reports/electrical.json")
    assert (
        compare(changed, observed, resolved)["observed_partitions"]
        != original_report["observed_partitions"]
    )


@pytest.fixture(scope="module")
def launcher():
    return validate_toolchain(ROOT / "fixtures/m1a/toolchain.lock.json", ROOT / "requirements.lock")


def fresh_observation(case: str, source: str, tmp_path: Path, launcher: Path):
    target = tmp_path / case
    target.mkdir()
    schematic = target / f"{design(case)['name']}.kicad_sch"
    schematic.write_text(source)
    config = target / "config/kicad/10.0"
    config.mkdir(parents=True)
    (config / "sym-lib-table").write_bytes((ROOT / "fixtures/m2a/sym-lib-table").read_bytes())
    xml = target / "netlist.xml"
    env = os.environ.copy()
    env.update({"LC_ALL": "C", "TZ": "UTC", "XDG_CONFIG_HOME": str(target / "config")})
    result = subprocess.run(
        [
            str(launcher),
            "kicad-cli",
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "-o",
            str(xml),
            str(schematic),
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=90,
    )
    assert result.returncode == 0, result.stderr
    return observe(schematic, xml)


def source_for(case: str) -> str:
    name = design(case)["name"]
    return (FIX / "qualification" / case / "project" / f"{name}.kicad_sch").read_text()


def detach_wire(case: str, component: str, pin: str) -> str:
    d = design(case)
    s = scene(case)
    c = next(c for c in d["components"] if c["id"] == component)
    unit, p = next(
        (u, p) for u, pins in assets()[c["asset"]].units.items() for p in pins if p.number == pin
    )
    x, y = s.positions[(component, unit)]
    from ai_kicad.m2b import _turn

    dx, dy = _turn(p, s.angles.get((component, unit), 0))
    point = (x + dx, y + dy)
    wire = next((a, b) for a, b in s.wires if point in (a, b))
    old = f"(wire (pts (xy {_mm(wire[0][0])} {_mm(wire[0][1])}) (xy {_mm(wire[1][0])} {_mm(wire[1][1])}))"
    altered = list(wire)
    index = altered.index(point)
    altered[index] = (point[0] + 1_270_000, point[1])
    new = f"(wire (pts (xy {_mm(altered[0][0])} {_mm(altered[0][1])}) (xy {_mm(altered[1][0])} {_mm(altered[1][1])}))"
    source = source_for(case)
    assert old in source
    return source.replace(old, new, 1)


@pytest.mark.parametrize(
    "case,component,pin",
    [
        ("rc_lowpass", "filter_c", "1"),
        ("noninverting_gain", "rf", "1"),
        ("dual_buffer", "cpos", "1"),
    ],
)
def test_detached_artifact_branch_rejected(case, component, pin, tmp_path, launcher):
    observed = fresh_observation(case, detach_wire(case, component, pin), tmp_path, launcher)
    assert compare(design(case), observed)["status"] == "fail"


def test_actual_led_polarity_swap_rejected(tmp_path, launcher):
    source = source_for("led_series")
    unit = _extract_symbol(source, "LED_1_1")
    altered = (
        unit.replace('(number "1"', '(number "temporary"', 1)
        .replace('(number "2"', '(number "1"', 1)
        .replace('(number "temporary"', '(number "2"', 1)
    )
    observed = fresh_observation("led_series", source.replace(unit, altered, 1), tmp_path, launcher)
    result = compare(design("led_series"), observed)
    assert result["status"] == "fail"
    assert "polarity" in " ".join(result["diagnostics"])


def test_actual_amplifier_input_swap_rejected(tmp_path, launcher):
    source = source_for("noninverting_gain")
    unit = _extract_symbol(source, "NE5532_1_1")
    altered = (
        unit.replace('(number "2"', '(number "temporary"', 1)
        .replace('(number "3"', '(number "2"', 1)
        .replace('(number "temporary"', '(number "3"', 1)
    )
    observed = fresh_observation(
        "noninverting_gain", source.replace(unit, altered, 1), tmp_path, launcher
    )
    assert compare(design("noninverting_gain"), observed)["status"] == "fail"
