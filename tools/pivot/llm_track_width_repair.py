"""Run a local-model, one-track-width repair against the immutable 555 PCB fixture.

Example::

    PYTHONPATH=.:src python tools/pivot/llm_track_width_repair.py \
      --kicad-cli /path/to/KiCad.AppImage --experiment-id llm_repair_run1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path

from ai_kicad.pivot.cli import _model_from_fixture
from ai_kicad.pivot.native import inspect_board
from ai_kicad.pivot.repair import OllamaRepairProvider, llm_bounded_repair
from ai_kicad.sexpr import children, parse
from tools.pivot.experiment_paths import create_experiment_dir


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/pivot/reference_555_led_flasher_v1"
BOARD_NAME = "Reference555LedFlasher.kicad_pcb"


def _segment_span(source: str, target_uuid: str) -> tuple[int, int, str]:
    depth = 0
    start = None
    quoted = False
    escaped = False
    for index, char in enumerate(source):
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "(":
            if depth == 1 and re.match(r"\(segment(?:\s|\))", source[index:]):
                start = index
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 1 and start is not None:
                block = source[start : index + 1]
                tree = parse(block)
                identities = children(tree, "uuid")
                if len(identities) == 1 and identities[0][1] == target_uuid:
                    return start, index + 1, block
                start = None
    raise ValueError("target segment is absent or ambiguous")


def _replace_width(source: str, track_uuid: str, width_mm: float) -> str:
    start, end, block = _segment_span(source, track_uuid)
    match = re.search(r"\(width\s+[-+0-9.eE]+\s*\)", block)
    if not match:
        raise ValueError("target segment has no parseable width")
    block = block[: match.start()] + f"(width {width_mm:.6f})" + block[match.end() :]
    return source[:start] + block + source[end:]


def _drc_report(launcher: list[str], board: Path, report: Path) -> dict:
    result = subprocess.run(
        [
            *launcher,
            "pcb",
            "drc",
            "--format",
            "json",
            "--severity-all",
            "--output",
            str(report),
            str(board),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode:
        raise RuntimeError("KiCad DRC failed to run: " + result.stderr[-1000:])
    return json.loads(report.read_text())


def _model_digest() -> dict:
    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as response:
        return json.loads(response.read())


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _track_snapshot(board: Path) -> dict[str, dict]:
    root = parse(board.read_text())
    snapshot = {}
    for segment in children(root, "segment"):
        uuid = children(segment, "uuid")[0][1]
        snapshot[uuid] = {
            "start": tuple(children(segment, "start")[0][1:]),
            "end": tuple(children(segment, "end")[0][1:]),
            "width_mm": float(children(segment, "width")[0][1]),
            "layer": children(segment, "layer")[0][1],
            "net": children(segment, "net")[0][-1],
        }
    return snapshot


def run(
    *,
    kicad_cli: Path,
    experiment_id: str,
    model_name: str,
    limit: int,
    fault_width_mm: float,
) -> dict:
    if not kicad_cli.is_file() or fault_width_mm <= 0:
        raise ValueError("KiCad launcher file and positive injected width are required")
    experiment = create_experiment_dir(ROOT, experiment_id)
    inputs = experiment / "inputs"
    workspace = experiment / "workspace"
    reports = experiment / "reports"
    for directory in (inputs, workspace, reports):
        directory.mkdir()
    source_board = FIXTURE / "native_project" / BOARD_NAME
    known_good = inputs / BOARD_NAME
    shutil.copy2(source_board, known_good)
    shutil.copy2(
        FIXTURE / "native_project" / "Reference555LedFlasher.kicad_pro",
        workspace / "Reference555LedFlasher.kicad_pro",
    )
    source = known_good.read_text()
    source_tree = parse(source)
    segments = children(source_tree, "segment")
    if not segments:
        raise ValueError("reference board contains no tracks")
    segment = segments[0]
    track_uuid = children(segment, "uuid")[0][1]
    native_net_name = children(segment, "net")[0][-1]
    original_width_mm = float(children(segment, "width")[0][1])
    if fault_width_mm >= original_width_mm:
        raise ValueError("fault injection must reduce the selected track width")
    fault_board = workspace / "Reference555LedFlasher_fault.kicad_pcb"
    fault_board.write_text(_replace_width(source, track_uuid, fault_width_mm))

    model = _model_from_fixture(FIXTURE)
    known_observation = inspect_board(model, known_good)
    if known_observation["status"] != "PASS":
        raise RuntimeError("known-good reference board fails independent connectivity inspection")

    launcher = [str(kicad_cli), "kicad-cli"]
    report_counter = 0
    report_paths: list[Path] = []

    def inspect(candidate: Path) -> dict:
        nonlocal report_counter
        report_counter += 1
        report_path = reports / f"drc-{report_counter:02d}.json"
        data = _drc_report(launcher, candidate, report_path)
        report_paths.append(report_path)
        tree = parse(candidate.read_text())
        tracks = {
            children(track, "uuid")[0][1]: track
            for track in children(tree, "segment")
            if children(track, "uuid")
        }
        violations = []
        for violation in data["violations"]:
            if violation.get("severity") != "error":
                continue
            item_rows = []
            for item in violation.get("items", []):
                row = dict(item)
                track = tracks.get(item.get("uuid"))
                if track is not None:
                    row["net_name"] = children(track, "net")[0][-1]
                    row["width_mm"] = float(children(track, "width")[0][1])
                item_rows.append(row)
            violations.append({**violation, "items": item_rows})
        return {
            "kicad_version": data["kicad_version"],
            "violations": violations,
            "unconnected_items": data["unconnected_items"],
        }

    def validate(candidate: Path) -> tuple[bool, str]:
        drc = inspect(candidate)
        observation = inspect_board(model, candidate)
        partitions_preserved = (
            observation["net_name_mapping_by_terminal_partition"]
            == known_observation["net_name_mapping_by_terminal_partition"]
        )
        copper_preserved = (
            observation["copper_connectivity"] == known_observation["copper_connectivity"]
        )
        passed = (
            not drc["violations"]
            and not drc["unconnected_items"]
            and observation["status"] == "PASS"
            and partitions_preserved
            and copper_preserved
        )
        return passed, json.dumps(
            {
                "native_drc_errors": len(drc["violations"]),
                "native_unconnected_items": len(drc["unconnected_items"]),
                "independent_board_status": observation["status"],
                "pin_pad_net_partitions_preserved": partitions_preserved,
                "copper_connectivity_preserved": copper_preserved,
            },
            sort_keys=True,
        )

    provider = OllamaRepairProvider(model_name)
    result = llm_bounded_repair(
        fault_board,
        experiment / "attempts",
        provider,
        inspect,
        validate,
        limit=limit,
        maximum_width_mm=0.5,
    )
    if result.status != "PASS" or result.accepted is None:
        raise RuntimeError("bounded LLM repair did not pass: " + "; ".join(result.diagnostics))
    repaired = workspace / "Reference555LedFlasher_repaired.kicad_pcb"
    shutil.copy2(result.accepted, repaired)
    fault_snapshot = _track_snapshot(fault_board)
    repaired_snapshot = _track_snapshot(repaired)
    changed_tracks = [
        uuid for uuid, before in fault_snapshot.items() if before != repaired_snapshot.get(uuid)
    ]
    if (
        set(fault_snapshot) != set(repaired_snapshot)
        or changed_tracks != [track_uuid]
        or any(
            fault_snapshot[track_uuid][key] != repaired_snapshot[track_uuid][key]
            for key in ("start", "end", "layer", "net")
        )
    ):
        raise RuntimeError("repaired candidate changed track identity or more than one width")
    tags = _model_digest()
    model_entry = next(item for item in tags["models"] if item["name"] == model_name)
    assessment = {
        "schema_version": "llm-drc-repair-assessment.v1",
        "experiment_id": experiment.name,
        "source_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip(),
        "implementation_sha256": hashlib.sha256(
            (ROOT / "src/ai_kicad/pivot/repair.py").read_bytes()
        ).hexdigest(),
        "provider": provider.provider_id,
        "model_digest": model_entry["digest"],
        "model_bytes": model_entry["size"],
        "ollama_version": subprocess.run(
            ["ollama", "--version"], capture_output=True, text=True, check=True
        ).stdout.strip(),
        "kicad_version": subprocess.run(
            [*launcher, "version"], capture_output=True, text=True, check=True
        ).stdout.strip(),
        "kicad_launcher_sha256": _file_sha256(kicad_cli),
        "kicad_cli_binary_sha256": _file_sha256(kicad_cli.parent / "shared/bin/kicad-cli"),
        "host": {
            "system": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "source_board_sha256": hashlib.sha256(known_good.read_bytes()).hexdigest(),
        "faulty_board_sha256": hashlib.sha256(fault_board.read_bytes()).hexdigest(),
        "fault_injected": {
            "type": "track_width",
            "track_uuid": track_uuid,
            "net_name": native_net_name,
            "width_before_mm": original_width_mm,
            "width_fault_mm": fault_width_mm,
        },
        "status": result.status,
        "attempts": result.attempts,
        "proposals": result.proposals,
        "diagnostics": result.diagnostics,
        "repaired_board_sha256": hashlib.sha256(repaired.read_bytes()).hexdigest(),
        "edit_scope_check": {
            "changed_track_uuids": changed_tracks,
            "only_width_changed": True,
            "fault_width_mm": fault_snapshot[track_uuid]["width_mm"],
            "repaired_width_mm": repaired_snapshot[track_uuid]["width_mm"],
        },
        "drc_reports": [
            {
                "path": str(path.relative_to(experiment)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "errors": [
                    violation["type"]
                    for violation in json.loads(path.read_text())["violations"]
                    if violation.get("severity") == "error"
                ],
            }
            for path in report_paths
        ],
        "independent_connectivity": (
            "PASS: pin-pad-net partitions and copper connectivity match known-good board"
        ),
        "known_good_unchanged": known_good.read_bytes() == source_board.read_bytes(),
        "scope": (
            "One deliberately injected track-width DRC error on the locked reference board; "
            "does not establish repair quality for other DRC classes."
        ),
    }
    (experiment / "assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")
    return assessment


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", type=Path, required=True, help="KiCad AppImage AppRun")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--model", default="qwen2.5:0.5b")
    parser.add_argument("--limit", type=int, default=2)
    parser.add_argument("--fault-width-mm", type=float, default=0.1)
    args = parser.parse_args()
    assessment = run(
        kicad_cli=args.kicad_cli,
        experiment_id=args.experiment_id,
        model_name=args.model,
        limit=args.limit,
        fault_width_mm=args.fault_width_mm,
    )
    print(json.dumps(assessment, indent=2))


if __name__ == "__main__":
    main()
