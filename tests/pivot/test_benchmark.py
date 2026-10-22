"""Benchmark records retain reproducibility and capability distinctions."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_kicad.pivot.benchmark import (
    BenchmarkGate,
    BenchmarkGateStatus,
    BenchmarkTrial,
    score_gates,
    score_reference_inspection,
)
from ai_kicad.pivot.evidence import EvidenceStatus
from tools.pivot.benchmark_runner import _error_class, _guard_paths, _validate_dispatch

ROOT = Path(__file__).resolve().parents[2]


def test_unsupported_gate_is_not_counted_as_an_incorrect_result() -> None:
    gates = [
        BenchmarkGate(
            gate_id="erc",
            status=BenchmarkGateStatus.PASS,
            summary="ERC passed",
            independent=True,
            evidence_paths=["erc.json"],
        ),
        BenchmarkGate(
            gate_id="rollback",
            status=BenchmarkGateStatus.UNSUPPORTED,
            summary="Backend does not expose rollback",
            independent=True,
            evidence_paths=["capabilities.json"],
        ),
        BenchmarkGate(
            gate_id="pad-map",
            status=BenchmarkGateStatus.FAIL,
            summary="Pin 2 was mapped to pad 3",
            independent=True,
            evidence_paths=["mapping.json"],
        ),
    ]
    score = score_gates(gates)
    assert score == {
        "pass": 1,
        "fail": 1,
        "unsupported": 1,
        "inconclusive": 0,
        "accuracy": 0.5,
        "eligible": 2,
    }


def test_benchmark_suite_is_bound_to_the_reference_fixture_and_has_unique_tasks() -> None:
    suite = json.loads((ROOT / "fixtures/pivot/benchmark_suite_v1.json").read_text())
    manifest = ROOT / suite["fixture_manifest"]
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == suite["fixture_manifest_sha256"]
    task_ids = [task["task_id"] for task in suite["tasks"]]
    assert len(task_ids) == len(set(task_ids))
    assert all(task["success_checks"] for task in suite["tasks"])


def test_ollama_reference_review_is_scored_independently() -> None:
    fixture = ROOT / "fixtures/pivot/reference_555_led_flasher_v1"
    experiment = json.loads(
        (
            ROOT / "fixtures/pivot/experiments/ollama_reference_review_2026-10-21_run1.json"
        ).read_text()
    )
    gates = score_reference_inspection(
        json.loads(experiment["model_output"]),
        json.loads((fixture / "design.json").read_text()),
        json.loads((fixture / "expected_behavior.json").read_text()),
        evidence_path="fixtures/pivot/experiments/ollama_reference_review_2026-10-21_run1.json",
    )
    outcomes = {gate.gate_id: gate.status for gate in gates}
    assert outcomes["native_pin_net_map"] is BenchmarkGateStatus.FAIL
    assert outcomes["timing_calculation"] is BenchmarkGateStatus.FAIL
    assert outcomes["led_current_bounds"] is BenchmarkGateStatus.FAIL


def test_ollama_trial_record_preserves_failure_and_exact_model_identity() -> None:
    trial = BenchmarkTrial.model_validate_json(
        (
            ROOT / "fixtures/pivot/experiments/benchmark_trial_ollama_direct_2026-10-21_run1.json"
        ).read_text()
    )
    assert trial.status is EvidenceStatus.FAIL
    assert trial.model.digest == "56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90"
    assert {gate.status for gate in trial.gates} == {BenchmarkGateStatus.FAIL}


def test_mcp_benchmark_rejects_paths_outside_isolated_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "run" / "workspace"
    workspace.mkdir(parents=True)
    protected = tmp_path / "fixtures/m2h2/source.kicad_sch"
    protected.parent.mkdir(parents=True)
    protected.touch()
    workspace_link = workspace / "escape.kicad_sch"
    workspace_link.symlink_to(protected)
    assert _guard_paths({"schematic": str(protected)}, workspace)
    assert _guard_paths({"output": "../../fixtures/m2h2/result.json"}, workspace)
    assert _guard_paths({"schematic": str(workspace_link)}, workspace)
    assert _guard_paths({"schematic": str(workspace / "board.kicad_sch")}, workspace) is None


def test_dispatch_rejects_forged_hidden_tool_and_invalid_arguments(tmp_path: Path) -> None:
    workspace = tmp_path / "run" / "workspace"
    workspace.mkdir(parents=True)
    allowed = {"list_schematic_components"}
    assert _validate_dispatch("export_gerbers", {}, allowed, workspace) == "INVALID_TOOL_CALL"
    assert _validate_dispatch("list_schematic_components", [], allowed, workspace)
    assert _validate_dispatch("list_schematic_components", {}, allowed, workspace) is None


def test_trial_requires_explicit_failure_gates_for_exceeded_budgets() -> None:
    base = {
        "schema_version": "pivot-benchmark.v1",
        "trial_id": "trial-001",
        "task_id": "read-reference-circuit",
        "fixture_sha256": "a" * 64,
        "recorded_at_utc": datetime(2026, 10, 21, tzinfo=timezone.utc),
        "model": {
            "provider": "ollama",
            "model": "qwen3.5:9b",
            "digest": "b" * 64,
            "settings": {"temperature": 0},
        },
        "backend": {
            "name": "direct-baseline",
            "version": "1",
            "build_id": "git:abc",
            "mode": "direct",
        },
        "time_limit_seconds": 60,
        "token_limit": 1000,
        "tool_call_limit": 2,
        "elapsed_seconds": 2.5,
        "token_count": 50,
        "tool_calls": [],
        "gates": [],
        "artifacts": [],
        "status": EvidenceStatus.INCONCLUSIVE,
    }
    assert BenchmarkTrial.model_validate(base).trial_id == "trial-001"
    base["token_count"] = 1001
    with pytest.raises(ValidationError, match="without a failing budget gate"):
        BenchmarkTrial.model_validate(base)
    base["gates"] = [
        {
            "gate_id": "token_budget",
            "status": BenchmarkGateStatus.FAIL,
            "summary": "The token budget was exceeded.",
            "independent": False,
            "evidence_paths": [],
        }
    ]
    assert BenchmarkTrial.model_validate(base).token_count == 1001
    base["token_count"] = 50
    base["elapsed_seconds"] = 61
    with pytest.raises(ValidationError, match="without a failing budget gate"):
        BenchmarkTrial.model_validate(base)
    base["elapsed_seconds"] = 2.5
    base["tool_calls"] = [
        {"tool_name": f"tool-{index}", "duration_ms": 1, "valid": True} for index in range(3)
    ]
    with pytest.raises(ValidationError, match="without a failing budget gate"):
        BenchmarkTrial.model_validate(base)


def test_backend_errors_are_normalized_to_declared_error_taxonomy() -> None:
    taxonomy = set(
        json.loads((ROOT / "fixtures/pivot/benchmark_suite_v1.json").read_text())["error_taxonomy"]
    )
    assert _error_class("UNSUPPORTED operation", taxonomy) == "UNSUPPORTED_CAPABILITY"
    assert _error_class("path is INVALID", taxonomy) == "INVALID_INPUT"
    assert _error_class("surprise", taxonomy) == "UNKNOWN_TOOL_ERROR"
