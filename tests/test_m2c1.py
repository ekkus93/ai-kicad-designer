"""M2c1 tuning qualification and independent layout counterexamples."""

import argparse
import copy
import json
import os
import re
import subprocess

import pytest

from ai_kicad.assets import _extract_symbol, sha256
from ai_kicad.ir import InputError
from ai_kicad.kicad import validate_toolchain
from ai_kicad.m2a import ROOT, observe
from ai_kicad.m2b import (
    LOCKED_PIN_ROLES,
    active_layout,
    assets,
    check_observed_layout,
    compare,
    passive_layout,
    power_stage_layout,
    timing_layout,
    validate,
)
from ai_kicad.m2b_build import build

FIX = ROOT / "fixtures/m2b"
TUNING = (
    "led_series",
    "led_reverse_supply",
    "rc_lowpass",
    "rc_highpass",
    "dual_buffer",
    "noninverting_gain",
    "inverting_gain",
    "rc_to_buffer",
    "dual_rail_reference",
    "sallen_key",
    "linear_regulator",
    "timer_astable",
)


def design(case):
    return validate(json.loads((FIX / f"{case}.json").read_text()), assets())


def checked(case):
    folder = FIX / "qualification" / case
    schematic = next((folder / "project").glob("*.kicad_sch"))
    return schematic, observe(schematic, folder / "reports/netlist.xml"), design(case)


def arguments(case, out):
    return argparse.Namespace(
        design=FIX / f"{case}.json",
        target="schematic",
        assets_lock=FIX / "assets.lock.json",
        toolchain_lock=ROOT / "fixtures/m1a/toolchain.lock.json",
        policy_lock=ROOT / "fixtures/m1a/policy.lock.json",
        out=out,
    )


def layout(intended, resolved):
    kinds = {relation["kind"] for relation in intended["relationships"]}
    if "timer" in kinds:
        return timing_layout(intended, resolved)
    if "power_stage" in kinds:
        return power_stage_layout(intended, resolved)
    if "amplifier" in kinds:
        return active_layout(intended, resolved)
    return passive_layout(intended, resolved)


@pytest.mark.parametrize(
    "case",
    (
        "led_reverse_supply",
        "rc_highpass",
        "dual_rail_reference",
        "sallen_key",
        "linear_regulator",
        "timer_astable",
    ),
)
def test_new_layouts_ignore_reference_designators_and_set_order(case):
    resolved = assets()
    baseline = design(case)
    original = layout(baseline, resolved)
    changed = copy.deepcopy(baseline)
    for key in ("components", "nets", "relationships", "power_assertions"):
        changed[key].reverse()
    for net in changed["nets"]:
        net["members"].reverse()
    for component in changed["components"]:
        if "functions" in component:
            component["functions"].reverse()
        match = re.fullmatch(r"([A-Z]+)([0-9]+)", component["refdes"])
        component["refdes"] = f"{match.group(1)}{int(match.group(2)) + 10}"
    altered = layout(validate(changed, resolved), resolved)
    assert (altered.positions, altered.wires, altered.labels, altered.angles) == (
        original.positions,
        original.wires,
        original.labels,
        original.angles,
    )


@pytest.mark.parametrize("case", TUNING)
def test_tuning_electrical_layout_and_clean_reruns(case, tmp_path):
    corpus = json.loads((FIX / "corpus.v1.json").read_text())
    assert next(c for c in corpus["circuits"] if c["id"] == case)["split"] == "tuning"
    outputs = []
    for index in range(2):
        out = tmp_path / f"build-{index}" / case
        out.parent.mkdir()
        assert build(arguments(case, out)) == 0
        outputs.append(out)
    a, b = outputs
    name = design(case)["name"]
    for rel in (f"project/{name}.kicad_sch", f"project/{name}.kicad_pro"):
        assert (a / rel).read_bytes() == (b / rel).read_bytes()
    for report in ("electrical", "layout"):
        rel = f"reports/{report}.json"
        left = json.loads((a / rel).read_text())
        right = json.loads((b / rel).read_text())
        assert left == right
    erc = json.loads((a / "reports/erc.json").read_text())
    assert all(not sheet["violations"] for sheet in erc["sheets"])
    manifest = json.loads((a / "reports/manifest.json").read_text())
    assert set(manifest["checks"].values()) == {"pass"}
    assert manifest["corpus_manifest_sha256"] == sha256((FIX / "corpus.v1.json").read_bytes())
    svg_rel = f"renders/schematic/{name}.svg"

    def normalize(raw):
        return re.sub(r"<title>.*?</title>", "<title/>", raw.decode())

    assert normalize((a / svg_rel).read_bytes()) == normalize((b / svg_rel).read_bytes())
    schematic = a / "project" / f"{name}.kicad_sch"
    observed = observe(schematic, a / "reports/netlist.xml")
    assert compare(design(case), observed)["status"] == "pass"
    assert (
        check_observed_layout(schematic, observed, design(case))[
            "observed_stage_order_reversal_count"
        ]
        == 0
    )


def test_new_assets_are_locked_to_real_physical_roles():
    resolved = assets()
    lock = json.loads((FIX / "assets.lock.json").read_text())
    for asset, stem in (("Regulator_Linear:L7805", "L7805"), ("Timer:NE555D", "NE555D")):
        assert sha256((FIX / f"{stem}.kicad_sym").read_bytes()) == lock["assets"][stem]
        assert {p.number: p.name for p in resolved[asset].units[1]} == LOCKED_PIN_ROLES[asset]


def test_declared_power_polarity_and_timer_roles_cannot_disagree_with_assets():
    resolved = assets()
    regulator = design("linear_regulator")
    next(r for r in regulator["relationships"] if r["kind"] == "power_stage")["polarity"] = (
        "negative"
    )
    with pytest.raises(InputError, match="physical power-stage polarity"):
        validate(regulator, resolved)
    timer = design("timer_astable")
    pins = next(r for r in timer["relationships"] if r["kind"] == "timer")["pins"]
    pins["trigger"], pins["threshold"] = pins["threshold"], pins["trigger"]
    with pytest.raises(InputError, match="timer actual physical pin roles"):
        validate(timer, resolved)


def test_label_every_terminal_cannot_hide_local_led_path():
    schematic, observed, intended = checked("led_series")
    observed["labels"] = [
        (net, observed["pin_positions"][member])
        for net, members in observed["nets"].items()
        for member in members
    ]
    observed["wires"] = []
    with pytest.raises(InputError, match="explicit wire path"):
        check_observed_layout(schematic, observed, intended)


def test_reversed_series_stage_order_is_rejected():
    schematic, observed, intended = checked("sallen_key")
    for number in ("1", "2"):
        key = ("R1", number)
        x, y = observed["pin_positions"][key]
        observed["pin_positions"][key] = (x + 100_000_000, y)
    with pytest.raises(InputError, match="stage order reversal"):
        check_observed_layout(schematic, observed, intended)


def test_electrically_labeled_but_detached_feedback_is_rejected():
    schematic, observed, intended = checked("noninverting_gain")
    sense = observed["pin_positions"][("U1", "2")]
    net = next(name for name, members in observed["nets"].items() if ("U1", "2") in members)
    observed["wires"] = [wire for wire in observed["wires"] if sense not in wire]
    observed["labels"].append((net, sense))
    with pytest.raises(InputError, match="feedback sense"):
        check_observed_layout(schematic, observed, intended)


def test_distant_decoupling_is_rejected():
    schematic, observed, intended = checked("linear_regulator")
    for number in ("1", "2"):
        key = ("C1", number)
        x, y = observed["pin_positions"][key]
        observed["pin_positions"][key] = (x + 75_000_000, y)
        net = next(name for name, members in observed["nets"].items() if key in members)
        observed["labels"].append((net, observed["pin_positions"][key]))
    with pytest.raises(InputError, match="decoupling"):
        check_observed_layout(schematic, observed, intended)


def test_page_scale_spread_is_rejected():
    schematic, observed, intended = checked("led_series")
    first = observed["pin_positions"][("J1", "1")]
    last = observed["pin_positions"][("J2", "1")]
    observed["wires"] += [
        (first, (20_320_000, first[1])),
        (last, (276_680_000, last[1])),
    ]
    with pytest.raises(InputError, match="spreads unnecessarily"):
        check_observed_layout(schematic, observed, intended)


@pytest.mark.parametrize("field", ("Reference", "Value"))
def test_required_text_cannot_be_hidden_or_missing(field, tmp_path):
    schematic, _, intended = checked("led_series")
    source = schematic.read_text()
    needle = f'(property "{field}" "D1"' if field == "Reference" else '(property "Value" "LED"'
    assert needle in source
    mutated = source.rsplit(needle, 1)
    hidden = tmp_path / "hidden.kicad_sch"
    hidden.write_text(mutated[0] + needle + " (hide yes)" + mutated[1])
    with pytest.raises(InputError, match="hidden"):
        check_observed_layout(
            hidden, observe(hidden, schematic.parent.parent / "reports/netlist.xml"), intended
        )
    missing = tmp_path / "missing.kicad_sch"
    # Remove only the occurrence property, preserving its embedded library definition.
    fragment = source.rsplit(needle, 1)
    remainder = fragment[1]
    depth = 1
    offset = 0
    while depth:
        char = remainder[offset]
        depth += (char == "(") - (char == ")")
        offset += 1
    missing.write_text(fragment[0] + remainder[offset:])
    with pytest.raises(InputError, match="required.*text missing"):
        check_observed_layout(
            missing, observe(missing, schematic.parent.parent / "reports/netlist.xml"), intended
        )


def test_shorter_wire_does_not_waive_unrelated_crossing():
    schematic, observed, intended = checked("rc_lowpass")
    baseline = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in observed["wires"])
    observed["wires"].pop(5)
    start = (140 * 1_270_000, 60 * 1_270_000)
    end = (140 * 1_270_000, 70 * 1_270_000)
    observed["wires"].append((start, end))
    observed["labels"].append(("REF", start))
    shortened = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in observed["wires"])
    assert shortened < baseline
    with pytest.raises(InputError, match="unrelated wire crossing"):
        check_observed_layout(schematic, observed, intended)


@pytest.mark.parametrize(
    "case,unit,first,second",
    (
        ("linear_regulator", "L7805_1_1", "IN", "OUT"),
        ("timer_astable", "NE555D_1_1", "TRIG", "THRES"),
    ),
)
def test_actual_regulator_and_timer_pin_roles_cannot_validate_themselves(
    case, unit, first, second, tmp_path
):
    schematic, _, intended = checked(case)
    source = schematic.read_text()
    unit_source = _extract_symbol(source, unit)
    altered = (
        unit_source.replace(f'(name "{first}"', '(name "temporary"', 1)
        .replace(f'(name "{second}"', f'(name "{first}"', 1)
        .replace('(name "temporary"', f'(name "{second}"', 1)
    )
    mutated = tmp_path / f"{intended['name']}.kicad_sch"
    mutated.write_text(source.replace(unit_source, altered, 1))
    launcher = validate_toolchain(
        ROOT / "fixtures/m1a/toolchain.lock.json", ROOT / "requirements.lock"
    )
    xml = tmp_path / "netlist.xml"
    config = tmp_path / "config/kicad/10.0"
    config.mkdir(parents=True)
    (config / "sym-lib-table").write_bytes((ROOT / "fixtures/m2a/sym-lib-table").read_bytes())
    env = os.environ.copy()
    env.update({"LC_ALL": "C", "TZ": "UTC", "XDG_CONFIG_HOME": str(tmp_path / "config")})
    run = subprocess.run(
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
            str(mutated),
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=90,
    )
    assert run.returncode == 0, run.stderr
    observed = observe(mutated, xml)
    result = compare(intended, observed)
    assert result["status"] == "fail"
    assert "physical pin roles" in " ".join(result["diagnostics"])
