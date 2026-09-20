"""Independent M2a identity and semantic-layout qualification."""

import copy
import os
from pathlib import Path
import subprocess

import pytest

from ai_kicad.ir import InputError
from ai_kicad.kicad import run_headless, validate_toolchain
from ai_kicad.m2a import (
    ROOT,
    _extract_symbol,
    _mm,
    compare,
    check_observed_layout,
    emit,
    fixture,
    layout,
    load_assets,
    observe,
    validate,
)


@pytest.fixture(scope="module")
def qualified(tmp_path_factory):
    directory = tmp_path_factory.mktemp("m2a_positive")
    design = fixture()
    assets = load_assets()
    scene = layout(validate(design, assets), assets)
    schematic = emit(design, assets, scene, directory)
    launcher = validate_toolchain(
        ROOT / "fixtures/m1a/toolchain.lock.json", ROOT / "requirements.lock"
    )
    netlist, erc, svgs = run_headless(
        schematic, launcher, directory, ROOT / "fixtures/m2a/sym-lib-table"
    )
    return design, assets, scene, schematic, netlist, erc, svgs, launcher


def _form(source: str, start: int) -> str:
    depth = 0
    quoted = False
    escape = False
    for position in range(start, len(source)):
        char = source[position]
        if quoted:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return source[start : position + 1]
    raise AssertionError("unterminated test mutation form")


def _op_occurrence(source: str, unit: int) -> str:
    needle = '(symbol (lib_id "Amplifier_Operational:NE5532")'
    occurrences = []
    start = 0
    while (start := source.find(needle, start)) >= 0:
        occurrences.append(_form(source, start))
        start += len(needle)
    return next(item for item in occurrences if f"(unit {unit})" in item)


def _fresh_xml(schematic: Path, launcher: Path, target: Path) -> Path:
    config = target / "config/kicad/10.0"
    config.mkdir(parents=True)
    (config / "sym-lib-table").write_bytes((ROOT / "fixtures/m2a/sym-lib-table").read_bytes())
    xml = target / "observed.xml"
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
    assert xml.is_file() and xml.stat().st_size
    return xml


def _mutation_result(qualified, tmp_path, mutated: str) -> dict:
    design, _, _, original, _, _, _, launcher = qualified
    schematic = tmp_path / original.name
    schematic.write_text(mutated)
    xml = _fresh_xml(schematic, launcher, tmp_path)
    return compare(design, observe(schematic, xml))


def test_real_multi_unit_positive(qualified):
    design, _, scene, schematic, xml, erc, svgs, _ = qualified
    observed = observe(schematic, xml)
    result = compare(design, observed)
    assert check_observed_layout(observed)["actual_pin_endpoint_match"]
    assert result["status"] == "pass", result["diagnostics"]
    assert [("U1", n) for n in (1, 2, 3)] == [
        tuple(item) for item in result["observed_units"] if item[0] == "U1"
    ]
    assert set(
        next(c for c in design["components"] if c["id"] == "amp")["functions"][2]["pins"].values()
    ) == {"4", "8"}
    assert erc.is_file() and svgs[0].read_text().startswith("<?xml")
    assert scene.metrics["body_overlap_count"] == 0
    assert scene.metrics["wire_through_body_count"] == 0
    assert scene.metrics["unrelated_wire_crossing_count"] == 0
    assert scene.metrics["unrouted_pin_count"] == 0
    assert scene.metrics["page_margin_pass"]
    assert scene.metrics["feedback_local_span_mm"] < 40


@pytest.mark.parametrize("unit", [2, 3])
def test_missing_required_unit_rejected(qualified, tmp_path, unit):
    source = qualified[3].read_text()
    mutated = source.replace(_op_occurrence(source, unit), "", 1)
    result = _mutation_result(qualified, tmp_path, mutated)
    assert result["status"] == "fail"
    assert "occurrence identity" in " ".join(result["diagnostics"])


def test_actual_plus_minus_swap_rejected(qualified, tmp_path):
    source = qualified[3].read_text()
    unit = _extract_symbol(source, "NE5532_1_1")
    altered = unit.replace('(number "2"', '(number "temporary"', 1)
    altered = altered.replace('(number "3"', '(number "2"', 1)
    altered = altered.replace('(number "temporary"', '(number "3"', 1)
    result = _mutation_result(qualified, tmp_path, source.replace(unit, altered, 1))
    assert result["status"] == "fail"
    assert any("polarity" in error or "connectivity" in error for error in result["diagnostics"])


def test_actual_physical_pin_number_rejected(qualified, tmp_path):
    source = qualified[3].read_text()
    unit = _extract_symbol(source, "NE5532_1_1")
    altered = unit.replace('(number "1"', '(number "9"', 1)
    first = _op_occurrence(source, 1)
    changed_occurrence = first.replace('(pin "1"', '(pin "9"', 1)
    source = source.replace(unit, altered, 1).replace(first, changed_occurrence, 1)
    result = _mutation_result(qualified, tmp_path, source)
    assert result["status"] == "fail"
    assert "physical pin inventory" in " ".join(result["diagnostics"])


def test_graphical_unit_wrong_package_rejected(qualified, tmp_path):
    source = qualified[3].read_text()
    unit = _op_occurrence(source, 2)
    altered = unit.replace('(property "Reference" "U1"', '(property "Reference" "U2"', 1)
    altered = altered.replace('(reference "U1")', '(reference "U2")', 1)
    result = _mutation_result(qualified, tmp_path, source.replace(unit, altered, 1))
    assert result["status"] == "fail"
    assert "occurrence identity" in " ".join(result["diagnostics"])


def test_actual_connection_mutation_rejected(qualified, tmp_path):
    source = qualified[3].read_text()
    scene = qualified[2]
    pin = next(
        a
        for a, b in scene.wires
        if scene.wire_nets[scene.wires.index((a, b))] == "IN" and a[0] > 100_000_000
    )
    old = f"(wire (pts (xy {_mm(pin[0])} {_mm(pin[1])})"
    changed = f"(wire (pts (xy {_mm(pin[0] - 1_270_000)} {_mm(pin[1])})"
    assert old in source
    result = _mutation_result(qualified, tmp_path, source.replace(old, changed, 1))
    assert result["status"] == "fail"
    assert "connectivity" in " ".join(result["diagnostics"])


def test_semantic_layout_is_reference_and_order_independent(tmp_path):
    assets = load_assets()
    canonical = validate(fixture(), assets)
    reordered = validate(fixture(reverse=True), assets)
    a = emit(canonical, assets, layout(canonical, assets), tmp_path / "a")
    b = emit(reordered, assets, layout(reordered, assets), tmp_path / "b")
    assert a.read_bytes() == b.read_bytes()
    renamed = validate(fixture("U17"), assets)
    assert layout(renamed, assets).positions == layout(canonical, assets).positions
    assert layout(renamed, assets).wires == layout(canonical, assets).wires


def test_unsupported_future_capability_fails():
    assets = load_assets()
    design = fixture()
    design["hierarchy"] = {"sheets": []}
    with pytest.raises(InputError):
        validate(design, assets)
    bad = copy.deepcopy(fixture())
    bad["nets"][0]["members"].pop()
    with pytest.raises(InputError):
        validate(bad, assets)


def test_hidden_or_stacked_embedded_pins_rejected(qualified, tmp_path):
    source = qualified[3].read_text()
    unit = _extract_symbol(source, "NE5532_1_1")
    altered = unit.replace("(pin input line", "(pin input line (hide yes)", 1)
    schematic = tmp_path / "hidden.kicad_sch"
    schematic.write_text(source.replace(unit, altered, 1))
    with pytest.raises(InputError, match="hidden or stacked"):
        observe(schematic, qualified[4])
    altered = unit.replace('(number "2"', '(number "1"', 1)
    schematic.write_text(source.replace(unit, altered, 1))
    with pytest.raises(InputError, match="hidden or stacked"):
        observe(schematic, qualified[4])


def test_real_tool_reproducibility(qualified, tmp_path):
    import re

    design, assets, _, original, xml, _, svgs, launcher = qualified
    scene = layout(validate(fixture(reverse=True), assets), assets)
    second = emit(design, assets, scene, tmp_path / "second path")
    second_xml, _, second_svgs = run_headless(
        second, launcher, tmp_path / "second path", ROOT / "fixtures/m2a/sym-lib-table"
    )
    assert original.read_bytes() == second.read_bytes()
    assert (
        original.with_suffix(".kicad_pro").read_bytes()
        == second.with_suffix(".kicad_pro").read_bytes()
    )
    assert compare(design, observe(original, xml)) == compare(design, observe(second, second_xml))

    def normalize(source: str) -> str:
        return re.sub(r"<title>.*?</title>", "<title/>", source)

    assert normalize(svgs[0].read_text()) == normalize(second_svgs[0].read_text())


def test_non_ascii_output_basename_uses_locked_c_locale(tmp_path):
    import argparse

    from ai_kicad.m2a_build import build

    out = tmp_path / "buffer β"
    args = argparse.Namespace(
        design=ROOT / "fixtures/m2a/dual_buffer.json",
        target="schematic",
        assets_lock=ROOT / "fixtures/m2a/assets.lock.json",
        toolchain_lock=ROOT / "fixtures/m1a/toolchain.lock.json",
        policy_lock=ROOT / "fixtures/m1a/policy.lock.json",
        out=out,
    )
    assert build(args) == 0
    assert (out / "project/DualBuffer.kicad_sch").is_file()
    assert (out / "reports/electrical.json").is_file()
