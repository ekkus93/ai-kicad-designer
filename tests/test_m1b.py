"""M1b qualification against real pinned KiCad artifacts and report failures."""

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

import pytest

from ai_kicad.__main__ import build
from ai_kicad.ir import InputError, load_json, validate
from ai_kicad.kicad import ToolFailure, run_headless, validate_toolchain
from ai_kicad.sexpr import ParseError, children, one, parse
from ai_kicad.verify import observe_electrical, verify_electrical


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/m1a"


def args(out: Path, nc: bool = False) -> argparse.Namespace:
    return argparse.Namespace(
        design=FIXTURE / ("divider_nc.json" if nc else "divider.json"),
        target="schematic",
        assets_lock=FIXTURE / ("assets_nc.lock.json" if nc else "assets.lock.json"),
        toolchain_lock=FIXTURE / "toolchain.lock.json",
        policy_lock=FIXTURE / "policy.lock.json",
        out=out,
    )


@pytest.fixture(scope="module")
def positives(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    base = tmp_path_factory.mktemp("m1b")
    divider, nc = base / "divider", base / "nc"
    assert build(args(divider)) == 0
    assert build(args(nc, True)) == 0
    return divider, nc


def _replace_wire(text: str, coordinate: str, replacement: str = "") -> str:
    lines = text.splitlines(keepends=True)
    found = [line for line in lines if line.lstrip().startswith("(wire ") and coordinate in line]
    assert len(found) == 1
    return text.replace(found[0], replacement)


def _remove_instance(text: str, ref: str) -> str:
    lines = text.splitlines(keepends=True)
    found = [i for i, line in enumerate(lines) if f'(property "Reference" "{ref}"' in line]
    assert len(found) == 1
    start = found[0] - 1
    while not lines[start].lstrip().startswith("(symbol (lib_id "):
        start -= 1
    end = found[0]
    while "(instances " not in lines[end]:
        end += 1
    return "".join(lines[:start] + lines[end + 1 :])


def _wire(a: tuple[str, str], b: tuple[str, str], index: int) -> str:
    return (
        f"  (wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) "
        f'(stroke (width 0) (type default)) (uuid "00000000-0000-5000-8000-{index:012d}") )\n'
    )


def _crossing_control(text: str) -> str:
    old_route = (
        "55.88 88.9) (xy 45.72 88.9",
        "45.72 88.9) (xy 45.72 115.57",
        "45.72 115.57) (xy 101.6 115.57",
        "101.6 115.57) (xy 101.6 105.41",
    )
    lines = text.splitlines(keepends=True)
    assert sum(any(segment in line for segment in old_route) for line in lines) == 4
    text = "".join(line for line in lines if not any(segment in line for segment in old_route))
    path = [
        (("55.88", "88.9"), ("76.2", "88.9")),
        (("76.2", "88.9"), ("76.2", "80.01")),
        (("76.2", "80.01"), ("81.28", "80.01")),
        (("81.28", "80.01"), ("81.28", "115.57")),
        (("81.28", "115.57"), ("101.6", "115.57")),
        (("101.6", "115.57"), ("101.6", "105.41")),
    ]
    return text.replace(
        "  (junction ",
        "".join(_wire(a, b, i) for i, (a, b) in enumerate(path, 1)) + "  (junction ",
        1,
    )


def _mutate(text: str, kind: str) -> str:
    if kind == "branch":
        return _replace_wire(text, "(xy 101.6 97.79)")
    if kind == "off_pin":
        return text.replace("(xy 55.88 83.82)", "(xy 54.61 83.82)", 1)
    if kind == "pin_number":
        return text.replace('(number "3"', '(number "9"', 1).replace(
            '(pin "3" (uuid', '(pin "9" (uuid', 1
        )
    if kind == "pin_map":
        first, second = "(at -5.08 2.54 0)", "(at -5.08 0 0)"
        assert text.count(first) == 1 and text.count(second) == 1
        return (
            text.replace(first, "__PIN_ONE__", 1)
            .replace(second, first, 1)
            .replace("__PIN_ONE__", second, 1)
        )
    if kind == "nc_marker":
        return "".join(
            line
            for line in text.splitlines(keepends=True)
            if not line.lstrip().startswith("(no_connect ")
        )
    if kind == "nc_connected":
        return text.replace(
            "  (junction ", _wire(("55.88", "88.9"), ("55.88", "91.44"), 99) + "  (junction ", 1
        )
    if kind == "symbol":
        return _remove_instance(text, "R2")
    if kind == "junction":
        control = _crossing_control(text)
        return control.replace(
            "  (junction ",
            "  (junction (at 76.2 86.36) (diameter 0) (color 0 0 0 0) "
            '(uuid "00000000-0000-5000-8000-000000000100"))\n  (junction ',
            1,
        )
    raise AssertionError(kind)


def _experiment(source: Path, out: Path, kind: str, nc: bool) -> tuple[str, str]:
    shutil.copytree(source, out)
    schematic = out / "project/DividerDemo.kicad_sch"
    schematic.write_text(_mutate(schematic.read_text(), kind))
    expected = load_json(FIXTURE / ("divider_nc.json" if nc else "divider.json"))
    launcher = validate_toolchain(FIXTURE / "toolchain.lock.json", ROOT / "requirements.lock")
    try:
        run_headless(schematic, launcher, out)
        tool_result = "pass"
    except ToolFailure as exc:
        tool_result = str(exc)
    assert (out / "reports/netlist.xml").is_file(), tool_result
    try:
        observed = observe_electrical(schematic, out / "reports/netlist.xml")
    except (ParseError, ET.ParseError) as exc:
        return tool_result, str(exc)
    result = verify_electrical(expected, observed)
    return tool_result, "; ".join(result["diagnostics"]) if result["status"] == "fail" else "pass"


def test_positive_inventory_nc_and_erc(positives: tuple[Path, Path]) -> None:
    divider, nc = positives
    for out, expected_nc in ((divider, []), (nc, [["J1", "4"]])):
        electrical = load_json(out / "reports/electrical.json")
        assert electrical["status"] == "pass"
        assert electrical["observed_nc"] == expected_nc
        assert len(electrical["observed_nets"]) == 3
        erc = load_json(out / "reports/erc.json")
        assert erc["kicad_version"] == "10.0.6"
        assert all(not sheet["violations"] for sheet in erc["sheets"])
        assert (out / "renders/schematic/DividerDemo.svg").stat().st_size > 1000
    assert "(no_connect " in (nc / "project/DividerDemo.kicad_sch").read_text()


def test_svg_review_text_and_local_wiring(positives: tuple[Path, Path]) -> None:
    for out, connector_value in zip(positives, ("Conn_01x03", "Conn_01x04"), strict=True):
        svg = ET.parse(out / "renders/schematic/DividerDemo.svg").getroot()
        text = {
            (element.text or "").strip()
            for element in svg.iter()
            if element.tag.rsplit("}", 1)[-1] == "text"
        }
        assert {"J1", "R1", "R2", "10k", connector_value, "VIN", "SENSE", "0V"} <= text
        assert {"1", "2", "3"} <= text
        if connector_value.endswith("04"):
            assert "4" in text
        schematic = parse((out / "project/DividerDemo.kicad_sch").read_text())
        wires = []
        for wire in children(schematic, "wire"):
            points = children(one(wire, "pts"), "xy")
            assert len(points) == 2
            a, b = ((float(point[1]), float(point[2])) for point in points)
            assert a[0] == b[0] or a[1] == b[1]
            wires.append((a, b))
        assert len(wires) == 11
        assert len(children(schematic, "junction")) == 1
        for index, (a, b) in enumerate(wires):
            for c, d in wires[index + 1 :]:
                horizontal, vertical = None, None
                if a[1] == b[1] and c[0] == d[0]:
                    horizontal, vertical = (a, b), (c, d)
                elif a[0] == b[0] and c[1] == d[1]:
                    horizontal, vertical = (c, d), (a, b)
                if horizontal and vertical:
                    y = horizontal[0][1]
                    x = vertical[0][0]
                    interior_horizontal = (
                        min(horizontal[0][0], horizontal[1][0])
                        < x
                        < max(horizontal[0][0], horizontal[1][0])
                    )
                    interior_vertical = (
                        min(vertical[0][1], vertical[1][1])
                        < y
                        < max(vertical[0][1], vertical[1][1])
                    )
                    assert not (interior_horizontal and interior_vertical)


@pytest.mark.parametrize(
    ("kind", "nc", "diagnostic"),
    [
        ("branch", False, "SENSE"),
        ("off_pin", False, "VIN"),
        ("junction", False, "expected"),
        ("pin_number", False, "pin"),
        ("pin_map", False, "expected"),
        ("nc_marker", True, "NC"),
        ("nc_connected", True, "NC"),
        ("symbol", False, "component inventory"),
    ],
)
def test_real_artifact_mutations(
    positives: tuple[Path, Path], tmp_path: Path, kind: str, nc: bool, diagnostic: str
) -> None:
    source = positives[1 if nc else 0]
    original_manifest = hashlib.sha256((source / "reports/manifest.json").read_bytes()).digest()
    tool, observation = _experiment(source, tmp_path / kind, kind, nc)
    assert observation != "pass", (kind, tool, observation)
    assert diagnostic.lower() in observation.lower(), (kind, tool, observation)
    assert (
        hashlib.sha256((tmp_path / kind / "reports/manifest.json").read_bytes()).digest()
        == original_manifest
    )


def test_crossing_without_junction_is_legal(positives: tuple[Path, Path], tmp_path: Path) -> None:
    source = positives[0]
    out = tmp_path / "crossing"
    shutil.copytree(source, out)
    schematic = out / "project/DividerDemo.kicad_sch"
    schematic.write_text(_crossing_control(schematic.read_text()))
    launcher = validate_toolchain(FIXTURE / "toolchain.lock.json", ROOT / "requirements.lock")
    run_headless(schematic, launcher, out)
    result = verify_electrical(
        load_json(FIXTURE / "divider.json"),
        observe_electrical(schematic, out / "reports/netlist.xml"),
    )
    assert result["status"] == "pass", result["diagnostics"]


@pytest.mark.parametrize(
    "change", ["duplicate", "unknown_asset", "wrong_map", "bus", "missing_nc", "bad_reason"]
)
def test_input_failures(change: str) -> None:
    raw = load_json(FIXTURE / "divider_nc.json")
    if change == "duplicate":
        raw["logical"]["nets"][0]["members"].append({"component": "j.io", "terminal": "p4"})
    elif change == "unknown_asset":
        raw["assets"][1]["library_id"] = "Connector_Generic:Conn_01x05"
    elif change == "wrong_map":
        raw["schematic"]["symbols"][2]["pin_map"]["4"] = "p3"
    elif change == "bus":
        raw["logical"]["buses"] = [{"id": "future"}]
    elif change == "missing_nc":
        raw["logical"]["no_connects"] = []
    elif change == "bad_reason":
        raw["logical"]["no_connects"][0]["reason"] = ""
    with pytest.raises(InputError):
        validate(raw)


def test_unordered_input_and_connection_fingerprint(
    positives: tuple[Path, Path], tmp_path: Path
) -> None:
    raw = load_json(FIXTURE / "divider.json")
    permuted = copy.deepcopy(raw)
    for key in ("assets", "evidence"):
        permuted[key].reverse()
    for key in ("components", "nets", "blocks", "domains", "relationships"):
        permuted["logical"][key].reverse()
    for component in permuted["logical"]["components"]:
        component["terminals"].reverse()
    for net in permuted["logical"]["nets"]:
        net["members"].reverse()
    permuted["schematic"]["symbols"].reverse()
    path = tmp_path / "permuted.json"
    path.write_text(json.dumps(permuted))
    out = tmp_path / "permuted"
    build_args = args(out)
    build_args.design = path
    assert build(build_args) == 0
    source = positives[0]
    for suffix in (".kicad_sch", ".kicad_pro"):
        assert (source / f"project/DividerDemo{suffix}").read_bytes() == (
            out / f"project/DividerDemo{suffix}"
        ).read_bytes()
    assert (
        load_json(source / "reports/manifest.json")["build_key"]
        == load_json(out / "reports/manifest.json")["build_key"]
    )
    altered = copy.deepcopy(raw)
    altered["logical"]["nets"][0]["members"][1]["terminal"] = "p2"

    def digest(value: dict) -> str:
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

    assert digest(raw) != digest(altered)
    with pytest.raises(InputError):
        validate(altered)


@pytest.mark.parametrize(
    ("fault", "reason"),
    [
        ("missing", "report missing"),
        ("empty", "report missing"),
        ("stale", "report missing"),
        ("malformed", "malformed ERC"),
        ("contradictory", "contradicts"),
        ("stdout_mismatch", "contradicts"),
        ("malformed_svg", "malformed SVG"),
    ],
)
def test_tool_report_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    positives: tuple[Path, Path],
    fault: str,
    reason: str,
) -> None:
    source = positives[0]
    erc_good = (source / "reports/erc.json").read_text()
    xml_good = (source / "reports/netlist.xml").read_text()
    svg_good = (source / "renders/schematic/DividerDemo.svg").read_text()

    def fake_run(argv: list[str], **_: object) -> subprocess.CompletedProcess:
        label = "erc" if "erc" in argv else "svg" if "svg" in argv else "netlist"
        target = Path(argv[argv.index("-o") + 1])
        if label == "netlist":
            target.write_text(xml_good)
        elif label == "erc":
            if fault != "missing":
                target.write_text(
                    "" if fault == "empty" else "{" if fault == "malformed" else erc_good
                )
                if fault == "stale":
                    os.utime(target, ns=(1, 1))
        else:
            (target / "DividerDemo.svg").write_text(
                "<svg" if fault == "malformed_svg" else svg_good
            )
        stdout = (
            "Found 1 violations\n"
            if fault == "stdout_mismatch" and label == "erc"
            else "Found 0 violations\n"
            if label == "erc"
            else ""
        )
        return subprocess.CompletedProcess(
            argv, 5 if fault == "contradictory" and label == "erc" else 0, stdout, ""
        )

    monkeypatch.setattr("ai_kicad.kicad.subprocess.run", fake_run)
    with pytest.raises(ToolFailure, match=reason):
        run_headless(
            source / "project/DividerDemo.kicad_sch", Path("/tmp/AppDir/AppRun"), tmp_path / fault
        )


def _svg_geometry(path: Path) -> tuple:
    root = ET.parse(path).getroot()

    def visit(node: ET.Element) -> tuple | None:
        tag = node.tag.rsplit("}", 1)[-1]
        if tag in {"title", "desc"}:
            return None
        attributes = tuple(
            sorted(
                (key.rsplit("}", 1)[-1], value)
                for key, value in node.attrib.items()
                if key.rsplit("}", 1)[-1] != "id"
            )
        )
        content = (node.text or "").strip()
        children = tuple(part for child in node if (part := visit(child)) is not None)
        return tag, attributes, content, children

    return visit(root)


@pytest.mark.parametrize("nc", [False, True])
def test_three_clean_reproducible_builds(tmp_path: Path, nc: bool) -> None:
    outputs = [tmp_path / "a" / "first", tmp_path / "a" / "second", tmp_path / "b" / "third"]
    for out in outputs:
        out.parent.mkdir(exist_ok=True)
        assert build(args(out, nc)) == 0
    for first, other in ((outputs[0], outputs[1]), (outputs[0], outputs[2])):
        for suffix in (".kicad_pro", ".kicad_sch"):
            assert (first / f"project/DividerDemo{suffix}").read_bytes() == (
                other / f"project/DividerDemo{suffix}"
            ).read_bytes()
        first_electrical = load_json(first / "reports/electrical.json")
        other_electrical = load_json(other / "reports/electrical.json")
        assert first_electrical == other_electrical
        assert _svg_geometry(first / "renders/schematic/DividerDemo.svg") == _svg_geometry(
            other / "renders/schematic/DividerDemo.svg"
        )
        first_manifest, other_manifest = (
            load_json(out / "reports/manifest.json") for out in (first, other)
        )
        for key in (
            "build_key",
            "design_digest",
            "compiler_digest",
            "lock_digests",
            "stages",
            "readiness",
        ):
            assert first_manifest[key] == other_manifest[key]
        assert [(check["id"], check["status"]) for check in first_manifest["checks"]] == [
            (check["id"], check["status"]) for check in other_manifest["checks"]
        ]
        assert (
            first_manifest["checks"][0]["artifact_digests"]
            == other_manifest["checks"][0]["artifact_digests"]
        )
        assert [
            a["sha256"]
            for a in first_manifest["artifacts"]
            if a["producer_stage"] == "emit_schematic"
        ] == [
            a["sha256"]
            for a in other_manifest["artifacts"]
            if a["producer_stage"] == "emit_schematic"
        ]
        for out in (first, other):
            erc = load_json(out / "reports/erc.json")
            assert erc["kicad_version"] == "10.0.6"
            assert all(not sheet["violations"] for sheet in erc["sheets"])


@pytest.mark.parametrize(
    "lock_kind", ["asset_hash", "asset_path", "tool_library", "tool_cpu", "policy_hash"]
)
def test_mismatched_locks_rejected(tmp_path: Path, lock_kind: str) -> None:
    build_args = args(tmp_path / lock_kind)
    if lock_kind.startswith("asset"):
        shutil.copytree(FIXTURE / "assets", tmp_path / "assets")
        data = load_json(build_args.assets_lock)
        data["assets"][0]["file_sha256" if lock_kind == "asset_hash" else "path"] = (
            "0" * 64 if lock_kind == "asset_hash" else "../outside.kicad_sym"
        )
        path = tmp_path / "assets.json"
        path.write_text(json.dumps(data))
        build_args.assets_lock = path
    elif lock_kind.startswith("tool"):
        data = load_json(build_args.toolchain_lock)
        if lock_kind == "tool_library":
            data["libraries"][0]["file_sha256"] = "0" * 64
        else:
            data["platform"]["cpu_model"] = "unknown CPU"
        path = tmp_path / "toolchain.json"
        path.write_text(json.dumps(data))
        build_args.toolchain_lock = path
    else:
        shutil.copy2(FIXTURE / "drafting.v1.json", tmp_path / "drafting.v1.json")
        data = load_json(build_args.policy_lock)
        data["profiles"][0]["sha256"] = "0" * 64
        path = tmp_path / "policy.json"
        path.write_text(json.dumps(data))
        build_args.policy_lock = path
    assert build(build_args) == 2
    assert not build_args.out.exists()
    assert (tmp_path / f"{lock_kind}.failed/reports/failure.json").is_file()
