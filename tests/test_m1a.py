"""The M1a divider and independent real-KiCad mutation experiment."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from ai_kicad.__main__ import build
from ai_kicad.ir import InputError, load_json, validate
from ai_kicad.kicad import ToolFailure, run_headless, validate_toolchain
from ai_kicad.verify import observe_electrical, verify_electrical


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/m1a"


def _args(out: Path) -> argparse.Namespace:
    return argparse.Namespace(
        design=FIXTURE / "divider.json",
        target="schematic",
        assets_lock=FIXTURE / "assets.lock.json",
        toolchain_lock=FIXTURE / "toolchain.lock.json",
        policy_lock=FIXTURE / "policy.lock.json",
        out=out,
    )


@pytest.fixture(scope="module")
def accepted(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("m1a") / "divider"
    assert build(_args(out)) == 0
    return out


def test_exact_divider_and_real_kicad(accepted: Path) -> None:
    report = json.loads((accepted / "reports/electrical.json").read_text())
    assert report["status"] == "pass"
    assert report["observed_nets"] == {
        "/VIN": [["J1", "1"], ["R1", "1"]],
        "/SENSE": [["J1", "2"], ["R1", "2"], ["R2", "1"]],
        "/0V": [["J1", "3"], ["R2", "2"]],
    }
    erc = json.loads((accepted / "reports/erc.json").read_text())
    assert erc["kicad_version"] == "10.0.6"
    assert all(not sheet["violations"] for sheet in erc["sheets"])
    assert (accepted / "project/DividerDemo.kicad_pro").is_file()
    assert (accepted / "renders/schematic/DividerDemo.svg").stat().st_size > 0


def test_detached_branch_is_observed_independently(accepted: Path, tmp_path: Path) -> None:
    mutated = tmp_path / "detached"
    shutil.copytree(accepted, mutated)
    schematic = mutated / "project/DividerDemo.kicad_sch"
    original = schematic.read_text()
    # Remove the *actual* branch from divider tap to R2.1. No IR, asset,
    # generator metadata, or comparator input is modified.
    lines = original.splitlines(keepends=True)
    branch = [
        line for line in lines if line.lstrip().startswith("(wire ") and "(xy 101.6 97.79)" in line
    ]
    assert len(branch) == 1
    schematic.write_text(original.replace(branch[0], ""))
    manifest = accepted / "reports/manifest.json"
    assert (
        hashlib.sha256(manifest.read_bytes()).digest()
        == hashlib.sha256((mutated / "reports/manifest.json").read_bytes()).digest()
    )
    expected = load_json(FIXTURE / "divider.json")
    launcher = validate_toolchain(FIXTURE / "toolchain.lock.json", ROOT / "requirements.lock")
    with pytest.raises(ToolFailure, match="ERC returned"):
        run_headless(schematic, launcher, mutated)
    observed = observe_electrical(schematic, mutated / "reports/netlist.xml")
    result = verify_electrical(expected, observed)
    assert result["status"] == "fail"
    assert result["observed_nets"] != result["expected_nets"]
    assert any("SENSE" in message and "R2" in message for message in result["diagnostics"])
    (mutated / "reports/electrical.json").write_text(json.dumps(result, indent=2) + "\n")


def test_strict_profile_rejects_extra_and_duplicate_membership() -> None:
    reference = load_json(FIXTURE / "divider.json")
    invalid = json.loads(json.dumps(reference))
    invalid["logical"]["buses"] = [{"id": "unsupported"}]
    with pytest.raises(InputError, match="unsupported"):
        validate(invalid, reference)
    invalid = json.loads(json.dumps(reference))
    invalid["logical"]["nets"][0]["members"].append({"component": "r.upper", "terminal": "p1"})
    with pytest.raises(InputError):
        validate(invalid, reference)


def test_rejected_output_is_not_accepted(tmp_path: Path) -> None:
    broken = tmp_path / "invalid.json"
    data = load_json(FIXTURE / "divider.json")
    data["pcb"] = {"profile": "unsupported"}
    broken.write_text(json.dumps(data))
    args = _args(tmp_path / "bad")
    args.design = broken
    assert build(args) == 2
    assert not args.out.exists()
    assert (tmp_path / "bad.failed/reports/failure.json").is_file()
